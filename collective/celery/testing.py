from plone.testing import Layer
from collective.celery.utils import getCelery


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
