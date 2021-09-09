# -*- coding: utf-8 -*-

import itertools
from plone.app.layout.viewlets import ViewletBase
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.queue import api


class QueuedSamplesSampleViewlet(ViewletBase):
    """Prints a viewlet to display a message stating there are some analyses
    that are in queue to be assigned to a worksheet
    """
    index = ViewPageTemplateFile("templates/queued_samples_sample_viewlet.pt")

    def __init__(self, context, request, view, manager=None):
        super(QueuedSamplesSampleViewlet, self).__init__(
            context, request, view, manager=manager)
        self.context = context
        self.request = request
        self.view = view

    def get_num_analyses_pending(self):
        if not api.is_queue_enabled():
            return 0

        # We are only interested in tasks with uids
        queue = api.get_queue()
        records = map(lambda t: t.get("records"), queue.get_tasks_for(self.context))
        if records:
            count = 0
            for i in records:
                for y in i:
                    count += len(y['Analyses'])
            return count

        uids = map(lambda t: t.get("uids"), queue.get_tasks_for(self.context))
        uids = filter(None, list(itertools.chain.from_iterable(uids)))
        return len(set(uids))
