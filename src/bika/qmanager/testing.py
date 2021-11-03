# -*- coding: utf-8 -*-
import transaction
import unittest2 as unittest
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import (
    applyProfile,
    login,
    setRoles,
    FunctionalTesting,
    IntegrationTesting,
    PloneSandboxLayer,
    TEST_USER_ID,
    TEST_USER_NAME,
    TEST_USER_PASSWORD,
)
from plone.testing import z2
from plone.testing import zope
from plone.testing.z2 import Browser
from senaite.queue.tests.base import SIMPLE_TESTING


class BikaQmanagerLayer(PloneSandboxLayer):

    defaultBases = (SIMPLE_TESTING,)

    def setUpZope(self, app, configurationContext):
        super(BikaQmanagerLayer, self).setUpZope(app, configurationContext)

        import senaite.queue
        import bika.qmanager

        self.loadZCML(package=senaite.queue)
        self.loadZCML(package=bika.qmanager)

        zope.installProduct(app, "senaite.queue")
        zope.installProduct(app, "bika.qmanager")

    def setUpPloneSite(self, portal):
        super(BikaQmanagerLayer, self).setUpPloneSite(portal)

        applyProfile(portal, "senaite.queue:default")
        applyProfile(portal, "bika.qmanager:default")
        transaction.commit()


BIKA_QMANAGER_FIXTURE = BikaQmanagerLayer()

BIKA_QMANAGER_INTEGRATION_TESTING = IntegrationTesting(
    bases=(BIKA_QMANAGER_FIXTURE,), name="BikaQmanagerLayer:IntegrationTesting",
)


BIKA_QMANAGER_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(BIKA_QMANAGER_FIXTURE,), name="BikaQmanagerLayer:FunctionalTesting",
)


BIKA_QMANAGER_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(BIKA_QMANAGER_FIXTURE, REMOTE_LIBRARY_BUNDLE_FIXTURE, z2.ZSERVER_FIXTURE,),
    name="BikaQmanagerLayer:AcceptanceTesting",
)

BQM_SIMPLE_TESTING = FunctionalTesting(
    bases=(BIKA_QMANAGER_FIXTURE,), name="bika.qmanager:SimpleTesting"
)


class SimpleTestCase(unittest.TestCase):
    layer = BQM_SIMPLE_TESTING

    def setUp(self):
        super(SimpleTestCase, self).setUp()
        self.app = self.layer["app"]
        self.portal = self.layer["portal"]
        login(self.portal, TEST_USER_NAME)

        self.request = self.layer["request"]
        self.request["ACTUAL_URL"] = self.portal.absolute_url()
        setRoles(self.portal, TEST_USER_ID, ["LabManager", "Manager"])

    def getBrowser(
        self, username=TEST_USER_NAME, password=TEST_USER_PASSWORD, loggedIn=True
    ):

        # Instantiate and return a testbrowser for convenience
        browser = Browser(self.portal)
        browser.addHeader("Accept-Language", "en-US")
        browser.handleErrors = False
        if loggedIn:
            browser.open("{}{}".format(self.portal.absolute_url(), "/login"))
            browser.getControl("Login Name").value = username
            browser.getControl("Password").value = password
            browser.getControl("Log in").click()
            self.assertTrue("You are now logged in" in browser.contents)

        return browser
