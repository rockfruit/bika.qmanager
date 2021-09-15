# -*- coding: utf-8 -*-

import json
import base64
from Products.Archetypes.interfaces.base import IBaseObject
from plone import api as ploneapi
from senaite.queue import api
from bika.lims import api as bika_api
from senaite.queue.adapters.actions import WorkflowActionGenericAdapter
from senaite.queue.queue import get_chunks, get_chunk_size
from senaite.queue.interfaces import IQueuedTaskAdapter
from zope.interface import implements
from zope.component import adapts
from bika.lims.utils.analysisrequest import create_analysisrequest as crar
from bika.lims import logger
from plone.memoize import view as viewcache
from Products.CMFPlone.utils import _createObjectByType
from bika.lims.utils import tmpID
from plone.namedfile.file import NamedBlobFile


def get_chunks_for(task, items=None):
    """Returns the items splitted into a list. The first element contains the
    first chunk and the second element contains the rest of the items
    """
    if items is None:
        items = task.get("records", [])

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

        # samples_analyses, worksheet_analyses, coa_publication
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
        chunks = get_chunks_for(task)

        # Process the first chunk
        map(self.create_ars, chunks[0])

        # Add remaining objects to the queue
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
