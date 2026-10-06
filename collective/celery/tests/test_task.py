from collective.celery import task
from zope.component.hooks import getSite
from zope.component.hooks import setSite

from .base import BaseTestCase


@task()
def echo(value):
    """Return the value."""
    return value


class TestTask(BaseTestCase):

    def test_task_name(self):
        self.assertEqual(
            echo.name, 'collective.celery.tests.test_task.echo')
        self.assertEqual(echo.__doc__, 'Return the value.')

    def test_apply_async_outside_zope(self):
        site = getSite()
        setSite(None)
        try:
            result = echo.apply_async(
                ('foo', ), {'site_path': '/'.join(self.portal.getPhysicalPath())})
        finally:
            setSite(site)
        self.assertEqual(result.result, 'foo')

    def test_apply_async_outside_zope_needs_site_path(self):
        site = getSite()
        setSite(None)
        try:
            with self.assertRaises(ValueError):
                echo.apply_async(('foo', ), {})
        finally:
            setSite(site)
