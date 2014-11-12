from plone import api
from collective.celery.tests.base import BaseTestCase
from collective.celery.utils import _serialize_arg, _deserialize_arg

__author__ = 'benc'


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