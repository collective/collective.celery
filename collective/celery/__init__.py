"""
This is all pulled out of David Glick's gist on github
https://gist.githubusercontent.com/davisagli/5824662/raw/de6ac44c1992ead62d7d98be96ad1b55ed4884af/gistfile1.py  # noqa
"""

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from Testing.makerequest import makerequest
from ZODB.POSException import ConflictError
from celery import Task
from zope.app.publication.interfaces import BeforeTraverseEvent
from zope.component.hooks import setSite
from zope.event import notify
import transaction
import logging
from collective.celery.utils import getCelery, getApp
from OFS.interfaces import IItem
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot
from plone import api


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

        def hook(success):
            if success:
                super(AfterCommitTask, self).apply_async(args=args, kwargs=kw)
        transaction.get().addAfterCommitHook(hook)


class FunctionRunner(object):

    base_task = AfterCommitTask

    def __init__(self, func, new_func, orig_args, orig_kw):
        self.orig_args = orig_args
        self.orig_kw = orig_kw
        self.func = func
        self.new_func = new_func
        self.userid = None

    def serialize_args(self, app, orig_args, orig_kw):
        args = []
        kw = {}
        for arg in orig_args:
            args.append(_serialize_arg(arg))
        for key, value in orig_kw.items():
            kw[key] = _serialize_arg(value)

        self.userid = kw.pop('authorized_userid')
        if len(args) == 0 or not IPloneSiteRoot.providedBy(args[0]):
            site = app.unrestrictedTraverse(kw.pop('site_path'))
            args = [site] + args
        else:
            kw.pop('site_path')
        return args, kw

    def before_run(self, app, args, kw):
        pass

    def after_run(self, app):
        pass

    def __call__(self):
        app = makerequest(getApp())
        transaction.begin()
        try:
            try:
                args, kw = self.serialize_args(app, self.orig_args, self.orig_kw)  # noqa
                self.before_run(app, args, kw)
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
            self.after_run(app)
            app._p_jar.close()

        return result


class AuthorizedFunctionRunner(FunctionRunner):

    def before_run(self, app, args, kw):
        site = args[0]
        notify(BeforeTraverseEvent(site, site.REQUEST))
        setSite(site)

        # set up admin user
        user = site.acl_users.getUserById(self.userid)
        newSecurityManager(None, user)

    def after_run(self, app):
        noSecurityManager()
        setSite(None)


class AdminFunctionRunner(AuthorizedFunctionRunner):

    def before_run(self, app, args, kw):
        site = args[0]
        notify(BeforeTraverseEvent(site, site.REQUEST))
        setSite(site)

        # set up admin user
        user = app.acl_users.getUserById('admin')
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

    def authorized(self, func, **task_kw):
        def new_func(*args, **kw):
            runner = AuthorizedFunctionRunner(func, new_func, args, kw)
            return runner()
        new_func.__name__ = func.__name__
        return getCelery().task(base=AfterCommitTask, **task_kw)(new_func)

    def as_admin(self, func, **task_kw):
        def new_func(*args, **kw):
            runner = AdminFunctionRunner(func, new_func, args, kw)
            return runner()
        new_func.__name__ = func.__name__
        return getCelery().task(base=AfterCommitTask, **task_kw)(new_func)

task = _task()
