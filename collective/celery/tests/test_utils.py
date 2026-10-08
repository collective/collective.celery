from ..utils import _bool
from ..utils import _deserialize_arg
from ..utils import _serialize_arg
from ..utils import getApp
from ..utils import getCeleryOptions
from .base import BaseTestCase
from plone import api

import OFS
import os


class TestHelpers(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.login_as_portal_owner()
        self.doc = api.content.create(self.portal, "Document", "doc")

    def test__serialize_arg(self):
        result = _serialize_arg(self.doc)
        expected = "object:///plone/doc"
        self.assertEqual(result, expected, "Serializer not returning expected output")

    def test__deserialize_arg(self):
        result = _deserialize_arg(self.portal, "object:///plone/doc")
        self.assertEqual(
            result, self.doc, "Did not get the expected object when deserializing"
        )

    def test__bool(self):
        self.assertTrue(_bool("1"))
        self.assertTrue(_bool("true"))
        self.assertTrue(_bool("yes"))
        self.assertFalse(_bool("0"))
        self.assertFalse(_bool("false"))
        self.assertFalse(_bool("no"))

    def test_getCeleryOptions(self):
        os.environ["CELERY_TEST"] = "True"
        result = getCeleryOptions()
        self.assertIn("test", result)

    def test_getApp(self):
        app = getApp()
        self.assertIsInstance(app, OFS.Application.Application)
