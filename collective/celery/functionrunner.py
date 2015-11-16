import logging
import traceback

from .base_task import AfterCommitTask
from .utils import _deserialize_arg
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from Testing.makerequest import makerequest
from ZODB.POSException import ConflictError
from celery.exceptions import Retry
from collective.celery.utils import getApp
from plone import api
import transaction
from zope.app.publication.interfaces import BeforeTraverseEvent
from zope.component.hooks import setSite
from zope.event import notify
from zope.globalrequest import setRequest
from zope.globalrequest import clearRequest

logger = logging.getLogger('collective.celery')


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

        return args, kw

    def authorize(self):
        pass

    def __call__(self):
        self.app = makerequest(getApp())
        setRequest(self.app.REQUEST)
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
                raise Retry(exc=e)
            except:
                logger.warn('Error running task: %s' % traceback.format_exc())
                transaction.abort()
                raise
        finally:
            noSecurityManager()
            setSite(None)
            self.app._p_jar.close()
            clearRequest()

        return result


class AuthorizedFunctionRunner(FunctionRunner):

    def authorize(self):
        notify(BeforeTraverseEvent(self.site, self.site.REQUEST))
        setSite(self.site)

        # set up user
        # TODO: using plone.api.get_user().getUser()
        # somehow makes the test fail, probably because the whole setRoles
        # and login() don't do everything.
        user = api.user.get(userid=self.userid).getUser()
        newSecurityManager(None, user)


class AdminFunctionRunner(AuthorizedFunctionRunner):

    def authorize(self):
        notify(BeforeTraverseEvent(self.site, self.site.REQUEST))
        setSite(self.site)

        # set up admin user
        # XXX need to search for an admin like user otherwise?
        user = api.user.get(userid='admin').getUser()
        if user:
            newSecurityManager(None, user)
