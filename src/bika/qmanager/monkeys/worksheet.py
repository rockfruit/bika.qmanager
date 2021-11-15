from bika.lims import api as _api
from bika.lims.interfaces.analysis import IRequestAnalysis
from bika.lims.workflow import ActionHandlerPool
from bika.qmanager import is_installed
from plone import api as ploneapi
from senaite.api import get_object
from senaite.queue import api


def addAnalyses(self, analyses):  # noqa non-lowercase func name
    """Adds a collection of analyses to the Worksheet at once
    """
    if not is_installed():
        # original content of function here.  This is run when the package
        # is present in buildout, but not activated in current site:
        actions_pool = ActionHandlerPool.get_instance()
        actions_pool.queue_pool()
        for analysis in analyses:
            self.addAnalysis(get_object(analysis))
        actions_pool.resume()
        return
    to_queue = list()
    queue_enabled = api.is_queue_ready("task_assign_analyses")
    worksheet_analyses = ploneapi.portal.get_registry_record(
        "senaite.queue.worksheet_analyses"
    )
    if worksheet_analyses > len(analyses):
        queue_enabled = False

    for num, analysis in enumerate(analyses):
        analysis = _api.get_object(analysis)
        if not queue_enabled:
            self.addAnalysis(analysis)
        elif not IRequestAnalysis.providedBy(analysis):
            self.addAnalysis(analysis)
        else:
            to_queue.append(analysis)

    # Add them to the queue
    if to_queue:
        api.add_assign_task(self, analyses=to_queue)
