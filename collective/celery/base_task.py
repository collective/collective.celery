from celery import result
from celery import states
from celery import Task
from collective.celery.utils import _serialize_arg
from collective.celery.utils import getCelery
from kombu.utils import uuid
from plone import api
from transaction.interfaces import ISynchronizer
from zope.interface import implementer

import transaction


class EagerResult(result.EagerResult):

    def ready(self):
        return self._state in states.READY_STATES


@implementer(ISynchronizer)
class CelerySynchronizer(object):
    """Handles communication with celery at transaction boundaries.
    We previously used after-commit hooks, but the transaction package
    swallows exceptions in commit hooks.
    """

    def beforeCompletion(self, txn):
        pass

    def afterCompletion(self, txn):
        """Called after commit or abort
        """
        # Skip if running tests
        import collective.celery
        if collective.celery.TESTING:
            return False
        if txn.status == transaction._transaction.Status.COMMITTED:
            tasks = getattr(txn, '_celery_tasks', [])
            executed = []
            for args, kw, task, task_id, options in tasks:
                if (args, kw, options, task.name) in executed:
                    # make sure task was not sent multiple times
                    # by ignoring tasks with exact same args.
                    continue
                executed.append((args, kw, options, task.name))
                super(AfterCommitTask, task).apply_async(
                    args=args,
                    kwargs=kw,
                    task_id=task_id,
                    **options
                )

    def newTransaction(self, txn):
        pass


celery_synch = CelerySynchronizer()


def queue_task_after_commit(args, kw, task, task_id, options):
    transaction.manager.registerSynch(celery_synch)

    txn = transaction.get()
    if not hasattr(txn, '_celery_tasks'):
        txn._celery_tasks = []
    txn._celery_tasks.append((args, kw, task, task_id, options))


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
    def apply_async(self, args, kwargs, **options):
        args, kw = self.serialize_args(args, kwargs)
        kw['site_path'] = '/'.join(api.portal.get().getPhysicalPath())
        kw['authorized_userid'] = api.user.get_current().getId()

        without_transaction = options.pop('without_transaction', False)

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
        if celery.conf.task_always_eager:
            result_ = EagerResult(task_id, None, states.PENDING, None)
        else:
            result_ = result.AsyncResult(task_id)

        # Note: one might be tempted to turn this into a datamanager.
        # This would result in two wrong things happening:
        # * A "commit within a commit" triggered by the function runner
        #   when CELERY_TASK_ALWAYS_EAGER is set,
        #   leading to the first invoked commit cleanup failing
        #   because the inner commit already cleaned up.
        # * An async task failing in eager mode would also rollback
        #   the whole transaction, which is not desiderable.
        #   Consider the case where the syncronous code constructs an object
        #   and the async task updates it, if we roll back everything
        #   then also the original content construction goes away
        #   (even if, in and by itself, worked)
        if without_transaction or celery.conf.task_always_eager:
            return self._apply_async(args, kw, result_, celery, task_id, options)
        else:
            queue_task_after_commit(args, kw, self, task_id, options)
            # Return the "fake" result ID
            return result_

    def _apply_async(self, args, kw, result_, celery, task_id, options):
        effective_result = super(AfterCommitTask, self).apply_async(
            args=args,
            kwargs=kw,
            task_id=task_id,
            **options
        )
        if celery.conf.task_always_eager:
            result_._state = effective_result._state
            result_._result = effective_result._result
            result_._traceback = effective_result._traceback
            celery.backend.store_result(
                task_id,
                effective_result._result,
                effective_result._state,
                traceback=result_.traceback,
                request=self.request
            )
            return result_
        return effective_result
