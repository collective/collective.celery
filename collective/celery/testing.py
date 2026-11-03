from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.testing.zope import installProduct
from plone.testing.zope import uninstallProduct
from zope.configuration import xmlconfig


class CollectiveCeleryLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import collective.celery

        xmlconfig.file(
            "configure.zcml", collective.celery, context=configurationContext
        )
        installProduct(app, "collective.celery")

    def tearDownZope(self, app):
        uninstallProduct(app, "collective.celery")

    def setUpPloneSite(self, portal):
        # Install into Plone site using portal_setup
        applyProfile(portal, "plone.app.contenttypes:default")


COLLECTIVE_CELERY_FIXTURE = CollectiveCeleryLayer()

COLLECTIVE_CELERY_INTEGRATION_TESTING = IntegrationTesting(
    bases=(COLLECTIVE_CELERY_FIXTURE,), name="CollectiveCeleryLayer:Integration"
)

COLLECTIVE_CELERY_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(COLLECTIVE_CELERY_FIXTURE,), name="CollectiveCeleryLayer:Functional"
)
