from plone.app.testing import PloneSandboxLayer, PLONE_FIXTURE, \
    IntegrationTesting
from plone.testing import z2
from zope.configuration import xmlconfig


class CollectiveCeleryLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import collective.celery
        xmlconfig.file(
            'configure.zcml',
            collective.celery,
            context=configurationContext
        )
        z2.installProduct(app, 'collective.celery')

    def tearDownZope(self, app):
        z2.uninstallProduct(app, 'collective.celery')


COLLECTIVE_CELERY_FIXTURE = CollectiveCeleryLayer()

COLLECTIVE_CELERY_INTEGRATION_TESTING = IntegrationTesting(
    bases=(COLLECTIVE_CELERY_FIXTURE,),
    name="CollectiveCeleryLayer:Integration"
)
