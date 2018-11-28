try:
    import unittest2 as unittest
except ImportError:
    import unittest
from plone.testing import z2
from plone.app.testing.interfaces import SITE_OWNER_NAME

from collective.celery import getCelery
from collective.celery.testing import COLLECTIVE_CELERY_INTEGRATION_TESTING
from collective.celery.utils import _getCelery
from collective.celery.utils import setApp


class BaseTestCase(unittest.TestCase):

    layer = COLLECTIVE_CELERY_INTEGRATION_TESTING

    def setUp(self):
        getCelery().conf['task_always_eager'] = True
        # use in-memory sqlite
        getCelery().conf['BROKER_URL'] = "sqla+sqlite://"
        getCelery().conf['CELERY_RESULT_BACKEND'] = "db+sqlite://"
        # refresh cached properties
        _getCelery()
        self.app = self.layer['app']
        self.portal = self.layer['portal']

        setApp(self.app)

    def login_as_portal_owner(self):
        """
        helper method to login as site admin
        """
        z2.login(self.app['acl_users'], SITE_OWNER_NAME)
