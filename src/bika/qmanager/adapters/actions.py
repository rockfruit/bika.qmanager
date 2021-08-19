# -*- coding: utf-8 -*-
from senaite.queue import api
from senaite.queue.adapters.actions import WorkflowActionGenericAdapter


class WorkflowActionGenericQueueAdapter(WorkflowActionGenericAdapter):
    """Adapter in charge of adding a transition/action to be performed for a
    single object or multiple objects to the queue
    """

    def do_action(self, action, objects):

        # import pdb; pdb.set_trace()
        # Check context: if context is worksheet

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
