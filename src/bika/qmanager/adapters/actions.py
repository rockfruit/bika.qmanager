# -*- coding: utf-8 -*-

import ast
import base64
import json
import transaction

from DateTime import DateTime
from Products.Archetypes.interfaces.base import IBaseObject
from Products.CMFPlone.utils import _createObjectByType
from Products.CMFCore.WorkflowCore import WorkflowException
from plone import api as ploneapi
from plone.memoize import view as viewcache
from plone.namedfile.file import NamedBlobFile
from zope.interface import implements
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.component import getAdapter

from bika.lims import api as bika_api
from bika.lims import logger
from bika.lims.utils import tmpID
from bika.lims.utils.analysisrequest import create_analysisrequest as crar

from senaite.app.supermodel.interfaces import ISuperModel
from senaite.impress.interfaces import IPdfReportStorage
from senaite.impress.publisher import Publisher

from senaite.queue import api
from senaite.queue.adapters.actions import WorkflowActionGenericAdapter
from senaite.queue.interfaces import IQueuedTaskAdapter
from senaite.queue.queue import get_chunks, get_chunk_size, get_chunks_for


def get_chunks_for_registration(task, items=None):
    """Returns the items splitted into a list. The first element contains the
    first chunk and the second element contains the rest of the items
    """
    if items is None:
        records = task.get("records", [])
        items = records
        # records contain Samples and a Sample contains analyses UIDs
        # if the total number of analyses is greater than the Samples
        # then do 1 Sample at a time
        analyses = 0
        for rec in records:
            analyses += len(rec['Analyses'])
        if analyses > len(records):
            chunk_size = 1
            return get_chunks(records, chunk_size)

    chunk_size = get_chunk_size(task.name)
    return get_chunks(items, chunk_size)


class WorkflowActionGenericQueueAdapter(WorkflowActionGenericAdapter):
    """Adapter in charge of adding a transition/action to be performed for a
    single object or multiple objects to the queue
    """

    def do_action(self, action, objects):

        do_queue = True
        # samples folder
        if self.context.portal_type == "Samples":
            samples_analyses = ploneapi.portal.get_registry_record(
                "senaite.queue.samples_analyses"
            )
            objs = []
            for obj in objects:
                analyses = obj.getAnalyses()
                objs.extend(analyses)
            if samples_analyses > len(objs):
                do_queue = False

        # worksheets
        if self.context.portal_type == "Worksheet":
            worksheet_analyses = ploneapi.portal.get_registry_record(
                "senaite.queue.worksheet_analyses"
            )
            if worksheet_analyses > len(objects):
                do_queue = False
        if not do_queue:
            return super(WorkflowActionGenericQueueAdapter, self).do_action(
                action, objects
            )

        # samples_analyses, worksheet_analyses
        # Delegate to base do_action
        # check here
        if api.is_queue_ready(action):
            # Add to the queue
            kwargs = {"unique": True}
            api.add_action_task(objects, action, self.context, **kwargs)
            return objects

        # Delegate to base do_action
        return super(WorkflowActionGenericQueueAdapter, self).do_action(action, objects)


class RegisterQueuedTaskAdapter(object):
    """Adapter for register transition
    """

    implements(IQueuedTaskAdapter)
    adapts(IBaseObject)

    def __init__(self, context):
        self.context = context

    def process(self, task):
        """Process the objects from the task
        """
        # If there are too many objects to process, split them in chunks to
        chunks = get_chunks_for_registration(task)

        # Process the first chunk
        map(self.create_ars, chunks[0])

        # Add remaining objects to the queue
        if chunks[1]:
            params = {"records": chunks[1]}
            api.add_task("bika.qmanager.create_ars", self.context, **params)

    def create_ars(self, record):
        """Generates a dispatch report for this sample
        """
        client_uid = record.get("Client")
        client = self.get_object_by_uid(client_uid)

        if not client:
            raise RuntimeError("No client found")

        # Create the Analysis Request
        try:
            ar = crar(client, self.context, record,)
        except (KeyError, RuntimeError) as e:
            errors = {"message": e.message}
            return {"errors": errors}

        for rec in record["attachments"]:
            att = _createObjectByType("Attachment", client, tmpID())
            data = base64.b64decode(json.loads(rec)["file"]["data"].encode())
            filename = json.loads(rec)["file"]["filename"]
            content_type = json.loads(rec)["file"]["content-type"]
            blob_data = NamedBlobFile(data, filename=filename)
            att.AttachmentFile.blob = blob_data
            att.AttachmentFile.blob.contentType = content_type
            att.AttachmentFile.setFilename(filename)
            att.AttachmentFile.setContentType(content_type)
            att.setContentType(content_type)
            att.processForm()
            ar.addAttachment(att)

    # N.B.: We are caching here persistent objects!
    #       It should be safe to do this but only on the view object,
    #       because it get recreated per request (transaction border).

    @viewcache.memoize
    def get_object_by_uid(self, uid):
        """Get the object by UID
        """
        logger.debug("get_object_by_uid::UID={}".format(uid))
        obj = bika_api.get_object_by_uid(uid, None)
        if obj is None:
            logger.warn("!! No object found for UID #{} !!")
        return obj


class PublishQueuedTaskAdapter(object):
    """Adapter for publish transition
    """

    implements(IQueuedTaskAdapter)
    adapts(IBaseObject)

    def __init__(self, context):
        self.context = context

    def process(self, task):
        """Process the objects from the task
        """
        # If there are too many objects to process, split them in chunks to
        chunks = get_chunks_for(task)

        # Process the first chunk
        map(self.publish_samples, chunks[0])

        # Add remaining objects to the queue
        if chunks[1]:
            params = {"uids": chunks[1]}
            api.add_task("bika.qmanager.publish_samples", self.context, **params)

    def publish_samples(self, data):
        """Generates a dispatch report for this sample
        """

        data = ast.literal_eval(data)
        # get the selected paperformat
        ajax_publish_view = getMultiAdapter((self.context, bika_api.get_request()), name=u'ajax_publish')
        paperformat = data.get("format")
        # get the selected orientation
        orientation = data.get("orientation", "portrait")
        # Generate the print CSS with the set format/orientation
        css = ajax_publish_view.get_print_css(
            paperformat=paperformat, orientation=orientation)
        logger.info(u"Print CSS: {}".format(css))
        # get the publisher instance
        publisher = Publisher()
        # add the generated CSS to the publisher
        publisher.add_inline_css(css)
        # This is the html after it was rendered by the client browser and
        # eventually extended by JavaScript, e.g. Barcodes or Graphs added etc.
        # NOTE: It might also contain multiple reports!
        html = data.get("html")
        # get COA number
        parser = publisher.get_parser(html)
        coa_num = parser.find_all(attrs={'name': 'coa_num'})
        coa_num = coa_num.pop()
        coa_num = coa_num.text.strip()

        # adding to queue start here
        # split the html per report
        # NOTE: each report is an instance of <bs4.Tag>
        html_reports = publisher.parse_reports(html)

        # generate a PDF for each HTML report
        pdf_reports = map(publisher.write_pdf, html_reports)

        # extract the UIDs of each HTML report
        # NOTE: UIDs are injected in `.analysisrequest.reportview.render`
        report_uids = map(
            lambda report: report.get("uids", "").split(","), html_reports)

        # generate a CSV for each report_uids
        samples = []
        for sample in data['items']:
            sample = getAdapter(sample, ISuperModel)
            samples.append(sample)

        # get the selected template
        template = data.get("template")
        csv_reports = []
        publish_view = getMultiAdapter((self.context, bika_api.get_request()), name=u'publish')

        is_multi_template = publish_view.is_multi_template(template)
        if is_multi_template:
            csv_report = ajax_publish_view.create_csv_reports(samples)
            csv_reports = [csv_report for i in range(len(pdf_reports))]
        else:
            for sample_csv in samples:
                csv_report = ajax_publish_view.create_csv_report(sample_csv)
                csv_reports.append(csv_report)

        # prepare some metadata
        metadata = {
            "template": template,
            "paperformat": paperformat,
            "orientation": orientation,
            "timestamp": DateTime().ISO8601(),
        }

        # Create PDFs and HTML
        # get the storage multi-adapter to save the generated PDFs
        storage = getMultiAdapter(
            (self.context, bika_api.get_request()), IPdfReportStorage)

        for pdf, html, csv_text, uids in zip(pdf_reports, html_reports, csv_reports, report_uids):
            # ensure we have valid UIDs here
            uids = filter(bika_api.is_uid, uids)
            # convert the bs4.Tag back to pure HTML
            html = publisher.to_html(html)
            # BBB: inject contained UIDs into metadata
            metadata["contained_requests"] = uids
            # store the report(s)
            storage.store(pdf, html, uids, metadata=metadata, csv_text=csv_text, coa_num=coa_num)

        # publish all samples
        for sample in samples:
            self.publish(sample)

    def publish(self, sample):
        """Set status to prepublished/published/republished
        """
        wf = bika_api.get_tool("portal_workflow")
        obj = sample.brain.getObject()
        status = wf.getInfoFor(obj, "review_state")
        transitions = {"verified": "publish",
                       "published": "republish"}
        transition = transitions.get(status, "prepublish")
        logger.info("Transitioning sample {}: {} -> {}".format(
            bika_api.get_id(sample), status, transition))
        try:
            # Manually update the view on the database to avoid conflict errors
            sample.getClient()._p_jar.sync()
            # Perform WF transition
            wf.doActionFor(obj, transition)
            # Commit the changes
            transaction.commit()
        except WorkflowException as e:
            logger.error(e)
