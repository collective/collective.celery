from collective.celery.task import EagerResult
from collective.celery.tests.base import BaseTestCase

__author__ = 'benc'


class TestEagerResult(BaseTestCase):

    def test_ready(self):
        result = EagerResult('1234', 'Done', 'SUCCESS')
        self.assertTrue(result.ready())