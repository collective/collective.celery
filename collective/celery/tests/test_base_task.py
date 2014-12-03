from plone import api
from ..base_task import EagerResult, AfterCommitTask
from .base import BaseTestCase

__author__ = 'benc'


class TestEagerResult(BaseTestCase):

    def test_ready(self):
        result = EagerResult('1234', 'Done', 'SUCCESS')
        self.assertTrue(result.ready())


class TestAfterCommitTask(BaseTestCase):

    def setUp(self):
        super(TestAfterCommitTask, self).setUp()
        self.login_as_portal_owner()
        self.doc1 = api.content.create(
            self.portal,
            'Document',
            'doc1'
        )
        self.doc2 = api.content.create(
            self.portal,
            'Document',
            'doc2'
        )
        self.task = AfterCommitTask()

    def test_serialize_args(self):
        args = [self.doc1]
        kwargs = {'doc': self.doc2}
        result = self.task.serialize_args(args, kwargs)
        expected = (['object:///plone/doc1'], {'doc': 'object:///plone/doc2'})
        self.assertEqual(
            result,
            expected,
            'AfterCommitTask.serialize_args return value not expected'
        )

    def test_apply_async(self):
        pass