from plone.testing import Layer
from collective.celery.utils import getCelery, _getCelery


class CeleryTestLayer(Layer):

    def setUp(self):
        getCelery().conf['CELERY_ALWAYS_EAGER'] = 'True'
        # use in-memory sqlite
        getCelery().conf['BROKER_URL'] = "sqla+sqlite://"
        getCelery().conf['CELERY_RESULT_BACKEND'] = "db+sqlite://"
        # refresh cached properties
        _getCelery()
        

CELERY = CeleryTestLayer()