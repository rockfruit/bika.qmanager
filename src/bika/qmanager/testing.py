# -*- coding: utf-8 -*-
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import (
    applyProfile,
    FunctionalTesting,
    IntegrationTesting,
    PloneSandboxLayer,
)
from plone.testing import z2

import bika.qmanager


class BikaQmanagerLayer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        import plone.restapi
        self.loadZCML(package=plone.restapi)
        self.loadZCML(package=bika.qmanager)

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'bika.qmanager:default')


BIKA_QMANAGER_FIXTURE = BikaQmanagerLayer()


BIKA_QMANAGER_INTEGRATION_TESTING = IntegrationTesting(
    bases=(BIKA_QMANAGER_FIXTURE,),
    name='BikaQmanagerLayer:IntegrationTesting',
)


BIKA_QMANAGER_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(BIKA_QMANAGER_FIXTURE,),
    name='BikaQmanagerLayer:FunctionalTesting',
)


BIKA_QMANAGER_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        BIKA_QMANAGER_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE,
    ),
    name='BikaQmanagerLayer:AcceptanceTesting',
)
