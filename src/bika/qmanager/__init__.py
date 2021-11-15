# -*- coding: utf-8 -*-
"""Init and utils."""
from zope.i18nmessageid import MessageFactory

from senaite.api import get_request
from bika.qmanager.interfaces import IBikaQmanagerLayer


def is_installed():
    """Returns whether the product is installed or not
    """
    request = get_request()
    return IBikaQmanagerLayer.providedBy(request)


_ = MessageFactory('bika.qmanager')
