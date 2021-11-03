# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from bika.qmanager.testing import SimpleTestCase  # noqa: E501


try:
    from Products.CMFPlone.utils import get_installer
except ImportError:
    get_installer = None


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(SimpleTestCase))
    return suite
