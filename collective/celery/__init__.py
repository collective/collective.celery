# -*- encoding: utf-8 -*-
# This is all pulled out of David Glick's gist on github
# https://gist.githubusercontent.com/davisagli/5824662/raw/de6ac44c1992ead62d7d98be96ad1b55ed4884af/gistfile1.py
from .base_task import AfterCommitTask
from celery import current_app
from celery.signals import after_task_publish
from collective.celery.functionrunner import AdminFunctionRunner
from collective.celery.functionrunner import AuthorizedFunctionRunner
from collective.celery.utils import getCelery


TESTING = False


def initialize(context):
    pass


class _task(object):
    """Decorator of celery tasks that should be run in a Zope context.

    The decorator function takes a path as a first argument,
    and will take care of traversing to it and passing it
    (presumably a portal) as the first argument to the decorated function.

    Also takes care of initializing the Zope environment,
    running the task within a transaction, and retrying on
    ZODB conflict errors.
    """

    def __call__(self, **task_kw):
        def decorator(func):
            def new_func(*args, **kw):
                runner = AuthorizedFunctionRunner(func, new_func, args, kw, task_kw)  # noqa
                return runner()
            new_func.__name__ = func.__name__
            return getCelery().task(base=AfterCommitTask, **task_kw)(new_func)
        return decorator

    def as_admin(self, **task_kw):
        def decorator(func):
            def new_func(*args, **kw):
                runner = AdminFunctionRunner(func, new_func, args, kw, task_kw)
                return runner()
            new_func.__name__ = func.__name__
            return getCelery().task(base=AfterCommitTask, **task_kw)(new_func)
        return decorator

task = _task()
task.__doc__ = """This decorator "wraps" the celery task decorator
:py:meth:`celery.app.base.Celery.task`.

It can be used the same way::

    @task()
    def mytask():
        pass

or through the additional ``as_admin()`` method::

    @task.as_admin()
    def mytask():
        pass

Which will execute the task in an unrestricted environment.
"""


@after_task_publish.connect
def update_sent_state(sender=None, body=None, **kwargs):
    """so we can know if a task was scheduled"""
    task = current_app.tasks.get(sender)
    task.update_state(task_id=kwargs['headers']['id'], state="SENT")
