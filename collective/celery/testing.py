from plone.app.testing import PloneSandboxLayer, PLONE_FIXTURE, \
    IntegrationTesting
from plone.testing import z2, Layer
from zope.configuration import xmlconfig
from .utils import getCelery


class CeleryTestLayer(Layer):

    def setUp(self):
        celery = getCelery()
        celery.conf.CELERY_ALWAYS_EAGER = True
        # use in-memory sqlite
        celery.conf.CELERY_RESULT_BACKEND = 'cache'
        celery.conf.CELERY_CACHE_BACKEND = "memory://"
        # refresh cached properties
        del(celery.backend)
        for name, task in celery.tasks.items():
            task.backend = celery.backend


CELERY = CeleryTestLayer()


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

    #def setUpPloneSite(self, portal):

COLLECTIVE_CELERY_FIXTURE = CollectiveCeleryLayer()

COLLECTIVE_CELERY_INTEGRATION_TESTING = IntegrationTesting(
    bases=(COLLECTIVE_CELERY_FIXTURE,),
    name="CollectiveCeleryLayer:Integration"
)
