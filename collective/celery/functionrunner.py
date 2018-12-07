import traceback

import transaction
from AccessControl.SecurityManagement import (newSecurityManager,
                                              noSecurityManager)
from celery.exceptions import Retry
from celery.utils.log import get_task_logger
from collective.celery.base_task import AfterCommitTask
from collective.celery.utils import _deserialize_arg, getApp, getCelery
from plone import api
from Testing.makerequest import makerequest
from ZODB.POSException import ConflictError
from zope.component.hooks import setSite
from zope.event import notify
from zope.globalrequest import clearRequest, setRequest
from zope.traversing.interfaces import BeforeTraverseEvent

logger = get_task_logger(__name__)


class FunctionRunner(object):

    base_task = AfterCommitTask
    app = None
    eager = False

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
            args.append(_deserialize_arg(self.site, arg))
        for key, value in self.orig_kw.items():
            kw[key] = _deserialize_arg(self.site, value)

        return args, kw

    def authorize(self):
        pass

    def _run(self):
        self.userid = self.orig_kw.pop('authorized_userid')
        site_path = self.orig_kw.pop('site_path')
        try:
            self.site = api.portal.get()
        except api.exc.CannotGetPortalError:
            pass
        if self.site is None:
            self.site = self.app.unrestrictedTraverse(site_path)
        self.authorize()
        args, kw = self.deserialize_args()  # noqa
        # run the task
        return self.func(*args, **kw)

    def __call__(self):
        celery = getCelery()
        if celery.conf.task_always_eager:
            self.eager = True
            # dive out of setup, this is not run in a celery task runner
            self.app = getApp()
            return self._run()

        self.app = makerequest(getApp())
        self.app.REQUEST['PARENTS'] = [self.app]
        setRequest(self.app.REQUEST)

        transaction.begin()
        try:
            try:
                result = self._run()
                # commit transaction
                transaction.commit()
                return result
            except ConflictError as e:
                # On ZODB conflicts, retry using celery's mechanism
                transaction.abort()
                raise Retry(exc=e)
            except Exception:
                logger.warn('Error running task: %s' % traceback.format_exc())
                transaction.abort()
                raise
        finally:
            noSecurityManager()
            setSite(None)
            self.app._p_jar.close()
            clearRequest()


class AuthorizedFunctionRunner(FunctionRunner):

    def authorize(self):
        if self.eager:
            # ignore, run as current user
            return

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
        if self.eager:
            # ignore, run as current user
            return

        notify(BeforeTraverseEvent(self.site, self.site.REQUEST))
        setSite(self.site)

        # set up admin user
        # XXX need to search for an admin like user otherwise?
        user = api.user.get(userid='admin').getUser()
        if user:
            newSecurityManager(None, user)
