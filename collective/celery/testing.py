import os
from plone.testing import Layer

class CeleryTestLayer(Layer):

    def setUp(self):
        os.environ['CELERY_ALWAYS_EAGER'] = 'True'

CELERY = CeleryTestLayer()