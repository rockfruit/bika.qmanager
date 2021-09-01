# -*- coding: utf-8 -*-
from senaite.queue import api
from plone import api as ploneapi
from senaite.queue.adapters.actions import WorkflowActionGenericAdapter


class WorkflowActionGenericQueueAdapter(WorkflowActionGenericAdapter):
    """Adapter in charge of adding a transition/action to be performed for a
    single object or multiple objects to the queue
    """

    def do_action(self, action, objects):

        do_queue = True
        # samples folder
        if self.context.portal_type == 'Samples':
            samples_analyses = ploneapi.portal.get_registry_record('senaite.queue.samples_analyses')
            if samples_analyses > len(objects):
                do_queue = False

        # worksheets
        if self.context.portal_type == 'Worksheet':
            worksheet_analyses = ploneapi.portal.get_registry_record('senaite.queue.worksheet_analyses')
            if worksheet_analyses > len(objects):
                do_queue = False
        if not do_queue:
            return super(WorkflowActionGenericQueueAdapter, self).do_action(
                action, objects)

        # samples_analyses, worksheet_analyses, coa_publication
        # Delegate to base do_action
        # check here
        if api.is_queue_ready(action):
            # Add to the queue
            kwargs = {"unique": True}
            api.add_action_task(objects, action, self.context, **kwargs)
            return objects

        # Delegate to base do_action
        return super(WorkflowActionGenericQueueAdapter, self).do_action(
            action, objects)
