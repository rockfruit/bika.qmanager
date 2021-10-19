import csv
from plone import api as ploneapi
from bika.coa.ajax import AjaxPublishView as BCAP
from bika.lims import api
from DateTime import DateTime
from senaite.app.supermodel.interfaces import ISuperModel
from senaite.impress.interfaces import IPdfReportStorage
from senaite.impress.interfaces import ITemplateFinder
from senaite.queue import api as q_api
from zope.component import getMultiAdapter
from zope.component import getAdapter
from zope.component import getUtility


class AjaxPublishView(BCAP):
    def ajax_save_reports(self):
        """Render all reports as PDFs and store them as AR Reports
        """
        # Data sent via async ajax call as JSON data from the frontend
        # NOTE: What to do if there's no frontend..?
        coa_publication = ploneapi.portal.get_registry_record(
            "senaite.queue.coa_publication"
        )
        if coa_publication is False:
            return super(AjaxPublishView, self).ajax_save_reports()

        data = self.get_json()
        params = {"uids": [data]}
        q_api.add_task("bika.qmanager.publish_samples", self.context, **params)
        return self.context.absolute_url()
