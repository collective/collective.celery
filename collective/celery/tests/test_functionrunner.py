from celery.app.task import TaskType
from plone.app.testing import SITE_OWNER_NAME
from zope.component import eventtesting

from .base import BaseTestCase
from ..functionrunner import FunctionRunner, AuthorizedFunctionRunner, AdminFunctionRunner


class BaseFunctionRunnerTestCase(BaseTestCase):

    def setUp(self):
        super(BaseFunctionRunnerTestCase, self).setUp()
        eventtesting.setUp()

        def dummy_func(*args, **kwargs):
            return 'Bar'

        self.dummy_func = dummy_func
        self.args = ['foo', 'bar']
        self.kwargs = {
            'authorized_userid': SITE_OWNER_NAME,
            'site_path': '/plone',
        }
        self.task_kwargs={'baz': 1}
        self.frunner = FunctionRunner(
            func=self.dummy_func,
            new_func=self.dummy_func,
            orig_args=self.args,
            orig_kw=self.kwargs,
            task_kw=self.task_kwargs,
        )


class TestFunctionRunner(BaseFunctionRunnerTestCase):

    def test__init(self):
        self.assertIsInstance(self.frunner.base_task, TaskType)
        self.assertIs(self.frunner.func, self.dummy_func)
        self.assertIs(self.frunner.new_func, self.dummy_func)
        self.assertEqual(self.frunner.orig_args, self.args)
        self.assertEqual(self.frunner.orig_kw, self.kwargs)
        self.assertEqual(self.frunner.task_kw, self.task_kwargs)
        self.assertIsNone(self.frunner.userid)
        self.assertIsNone(self.frunner.site)
        self.assertIsNone(self.frunner.app)

    def test__call(self):
        self.assertIs(self.frunner(), self.dummy_func())

    def test_deserialize_args(self):
        self.frunner()
        result = self.frunner.deserialize_args()
        self.assertEqual(result[0], self.args)
        self.assertEqual(result[1], self.kwargs)

    def test_authorize(self):
        self.assertIsNone(self.frunner.authorize())


class TestAuthorizedFunctionRunner(BaseFunctionRunnerTestCase):

    def setUp(self):
        super(TestAuthorizedFunctionRunner, self).setUp()
        self.frunner = AuthorizedFunctionRunner(
            func=self.dummy_func,
            new_func=self.dummy_func,
            orig_args=self.args,
            orig_kw=self.kwargs,
            task_kw=self.task_kwargs,
        )

    def test_authorize(self):
        # TODO: This is code does not work due to the fact we're starting a
        # Zope instance within a zope instance
        # self.frunner()
        # eventtesting.clearEvents()
        # self.frunner.authorize()
        # events = eventtesting.getEvents()
        # self.assertGreater(len(events), 0)
        pass


class TestAdminFunctionRunner(BaseFunctionRunnerTestCase):

    def setUp(self):
        super(TestAdminFunctionRunner, self).setUp()
        self.frunner = AdminFunctionRunner(
            func=self.dummy_func,
            new_func=self.dummy_func,
            orig_args=self.args,
            orig_kw=self.kwargs,
            task_kw=self.task_kwargs,
        )

    def test_authorize(self):
        # TODO: This is code does not work due to the fact we're starting a
        # Zope instance within a zope instance
        # self.frunner()
        # eventtesting.clearEvents()
        # self.frunner.authorize()
        # events = eventtesting.getEvents()
        # self.assertGreater(len(events), 0)
        pass