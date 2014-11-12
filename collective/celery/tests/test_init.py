"""
Test all the things in collective.celery.__init__
"""
from plone import api
from collective.celery import _serialize_arg, _deserialize_arg, EagerResult
from collective.celery.tests.base import BaseTestCase


class TestHelpers(BaseTestCase):

    def setUp(self):
        super(TestHelpers, self).setUp()
        self.login_as_portal_owner()
        self.doc = api.content.create(
            self.portal,
            'Document',
            'doc'
        )

    def test__serialize_arg(self):
        result = _serialize_arg(self.doc)
        expected = 'object:///plone/doc'
        self.assertEqual(
            result,
            expected,
            'Serializer not returning expected output'
        )

    def test__deserialize_arg(self):
        result = _deserialize_arg(self.portal, 'object:///plone/doc')
        self.assertEqual(
            result,
            self.doc,
            'Did not get the expected object when deserializing'
        )


class TestEagerResult(BaseTestCase):

    def test_ready(self):
        result = EagerResult('1234', 'Done', 'SUCCESS')
        self.assertTrue(result.ready())


class TestAfterCommitTask(BaseTestCase):

    passc