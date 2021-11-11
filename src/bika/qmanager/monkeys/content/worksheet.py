# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.QUEUE.
#
# SENAITE.QUEUE is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright 2019-2021 by it's authors.
# Some rights reserved, see README and LICENSE.

from plone import api as ploneapi
from senaite.queue import api
from senaite.queue import logger

from bika.lims import api as _api
from bika.lims.catalog import CATALOG_ANALYSIS_LISTING
from bika.lims.interfaces.analysis import IRequestAnalysis


def addAnalyses(self, analyses):  # noqa non-lowercase func name
    """Adds a collection of analyses to the Worksheet at once
    """
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
