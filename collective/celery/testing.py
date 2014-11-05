import os
from plone.testing import Layer
from collective.celery.utils import getCelery

class CeleryTestLayer(Layer):

    def setUp(self):
        getCelery().conf['CELERY_ALWAYS_EAGER'] = 'True'
        

CELERY = CeleryTestLayer()