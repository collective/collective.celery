# -*- encoding: utf-8 -*-
# This is all pulled out of David Glick's gist on github
# https://gist.githubusercontent.com/davisagli/5824662/raw/de6ac44c1992ead62d7d98be96ad1b55ed4884af/gistfile1.py

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from Testing.makerequest import makerequest
from ZODB.POSException import ConflictError
from celery import Task
from celery import result
from celery import states
from kombu.utils import uuid
from zope.app.publication.interfaces import BeforeTraverseEvent
from zope.component.hooks import setSite
from zope.event import notify
import transaction
import logging
from collective.celery.utils import getCelery, getApp
from OFS.interfaces import IItem
from plone import api
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot


logger = logging.getLogger('collective.celery')


def initialize(context):
    pass


_object_marker = 'object://'


def _serialize_arg(val):
    if IItem.providedBy(val):
        val = '%s%s' % (
            _object_marker,
            '/'.join(val.getPhysicalPath()))
    return val


def _deserialize_arg(app, val):
    if isinstance(val, basestring):
        if val.startswith(_object_marker):
            val = val[len(_object_marker):]
            val = app.restrictedTraverse(val)
    return val


class EagerResult(result.EagerResult):

    def ready(self):
        return self._state in states.READY_STATES


class AfterCommitTask(Task):
    """Base for tasks that queue themselves after commit.

    This is intended for tasks scheduled from inside Zope.
    """
    abstract = True

    def serialize_args(self, orig_args, orig_kw):
        args = []
        kw = {}
        for arg in orig_args:
            args.append(_serialize_arg(arg))
        for key, value in orig_kw.items():
            kw[key] = _serialize_arg(value)
        return args, kw

    # Override apply_async to register an after-commit hook
    # instead of queueing the task right away and to
    # set object paths instead of objects
    def apply_async(self, args, kwargs):
        args, kw = self.serialize_args(args, kwargs)
        kw['site_path'] = '/'.join(api.portal.get().getPhysicalPath())
        kw['authorized_userid'] = api.user.get_current().getId()
        celery = getCelery()
        # Here we cheat a little: since we will not start the task
        # up until the transaction is done,
        # we cannot give back to whoever called apply_async
        # its much beloved AsyncResult.
        # But we can actually pass the task a specific task_id
        # (although it's not very documented)
        # and an AsyncResult at this point is just that id, basically.
        task_id = uuid()

        # Construct a fake result
        if celery.conf.CELERY_ALWAYS_EAGER:
            result_ = EagerResult(task_id, None, states.PENDING, None)
        else:
            result_ = result.AsyncResult(task_id)

        # Note: one might be tempted to turn this into a datamanager.
        # This would result in two wrong things happening:
        # * A "commit within a commit" triggered by the function runner
        #   when CELERY_ALWAYS_EAGER is set,
        #   leading to the first invoked commit cleanup failing
        #   because the inner commit already cleaned up.
        # * An async task failing in eager mode would also rollback
        #   the whole transaction, which is not desiderable.
        #   Consider the case where the syncronous code constructs an object
        #   and the async task updates it, if we roll back everything
        #   then also the original content construction goes away
        #   (even if, in and by itself, worked)
        def hook(success):
            if success:
                effective_result = super(AfterCommitTask, self).apply_async(
                    args=args,
                    kwargs=kw,
                    task_id=task_id
                )
                if celery.conf.CELERY_ALWAYS_EAGER:
                    result_._state = effective_result._state
                    result_._result = effective_result._result
                    result_._traceback = effective_result._traceback
        transaction.get().addAfterCommitHook(hook)
        # Return the "fake" result ID
        return result_


class FunctionRunner(object):

    base_task = AfterCommitTask

    def __init__(self, func, new_func, orig_args, orig_kw, task_kw):
        self.orig_args = orig_args
        self.orig_kw = orig_kw
        self.func = func
        self.new_func = new_func
        self.userid = None
        self.site = None
        self.app = None
        self.task_kw = task_kw

    def deserialize_args(self):
        args = []
        kw = {}
        for arg in self.orig_args:
            args.append(_deserialize_arg(self.app, arg))
        for key, value in self.orig_kw.items():
            kw[key] = _deserialize_arg(self.app, value)

        # TO BE DISCUSSED: why do we need to pass site object here ?
        # site_pos = 0
        # if self.task_kw.get('bind'):
        #     site_pos = 1
        # if len(args) == site_pos or not IPloneSiteRoot.providedBy(args[site_pos]):  # noqa
        #     args.insert(site_pos, self.site)
        return args, kw

    def authorize(self):
        pass

    def __call__(self):
        self.app = makerequest(getApp())
        transaction.begin()
        try:
            try:
                self.userid = self.orig_kw.pop('authorized_userid')
                self.site = self.app.unrestrictedTraverse(self.orig_kw.pop('site_path'))  # noqa
                self.authorize()
                args, kw = self.deserialize_args()  # noqa
                # run the task
                result = self.func(*args, **kw)
                # commit transaction
                transaction.commit()
            except ConflictError, e:
                # On ZODB conflicts, retry using celery's mechanism
                transaction.abort()
                raise self.new_func.retry(exc=e)
            except:
                transaction.abort()
                raise
        finally:
            noSecurityManager()
            setSite(None)
            self.app._p_jar.close()

        return result


class AuthorizedFunctionRunner(FunctionRunner):

    def authorize(self):
        notify(BeforeTraverseEvent(self.site, self.site.REQUEST))
        setSite(self.site)

        # set up user
        # TODO: using plone.api.get_user().getUser()
        # somehow makes the test fail, probably because the whole setRoles
        # and login() don't do everything.
        user = self.site['acl_users'].getUserById(self.userid)
        newSecurityManager(None, user)


class AdminFunctionRunner(AuthorizedFunctionRunner):

    def authorize(self):
        notify(BeforeTraverseEvent(self.site, self.site.REQUEST))
        setSite(self.site)

        # set up admin user
        # XXX need to search for an admin like user otherwise?
        user = self.site['acl_users'].getUserById('admin')
        if user:
            newSecurityManager(None, user)


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
