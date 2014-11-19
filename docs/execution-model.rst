.. _execution-model:

The execution model
===================

``collective.celery`` doesn't queue tasks immediately when you call ``delay`` or ``apply_async``, but rather waits after the current transaction is committed (via an after commit hook) to do so.

This is to avoid a problem where the task depends on some objects that are being added in the current transaction: should we send the task immediately, it might be executed before the transaction is committed and therefore might not find some objects [#]_.

This is implemented by adding an "after-commit hook" to the transaction that will queue the task after the current transaction has safely committed, but has a number of implications:

 #. The task id has to be pre-generated in order to return a :py:class:`~celery.result.AsyncResult`. That is done by using the same udnerlying function that Celery uses, :py:func:`kombu.utils.uuid`
 #. In the case an eager result was requested (see :ref:`usage-always-eager`), a special wrapped result is constructed that will mimick the Celery API, while assuring consistent usage (unlike with standard Celery, we insert the eventual result into the result backend even if we are in eager mode)

Authorization
-------------

When the task is run, unless you use the :py:meth:`~collective.celery._task.as_admin` method, it will be run with the user security context (i.e. the same user) as the one who queued the task. So if our user Alice queues the task ``foo`` (by .e.g. invoking a browser view) that task will be run as if Alice has invoked it directly.

Exception handling
------------------

Tasks are run wrapped into their own transaction: a transaction is begun before the task is run in the worker, and committed if the task runs without failure, or else it will be rollbacked.

If the exception raised is a :py:class:`~ZODB:POSException.ConflictError`, the task will be retried using the Celery retry mechanism (substantially requeued and executed again as soon as possible).

Any other exception will be reraised after rollbacking the transaction and therefore catched by the celery worker logging.

Argument serialization
----------------------

Each argument to the task will be serialized before being sent to the task. The serialization folows the standard Celery mechanism (i.e. nothing special is done) with the exception of content objects (those implementing :py:class:`OFS.interfaces.IItem`).

These objects are serialized to a string with the format ``object://<path-to-object>`` where ``path-to-object`` is the object path (obtained via ``getPhysicalPath``).

.. warning::
   It is therefore quite insecure to pass as arguments any objects residing in the ZODB which are not "content objects", such as for example single field or object attribute.
   In general, you should only pass safely pickleable objects (pickleable by the tandrad pickler) and "content objects" as arguments

The custom worker
-----------------

In order to render our tasks capable of executing properly, ``collective.celery`` comes with a custom worker: this worker basically just wraps the standard worker by doing the initial Zope setup (reading configuration, connecting to the ZODB, pulling up ZCML).

This is why you have to pass a zope configuration file to the worker, and why you have to use ZEO or an equivalent architecture (the worker does connect to the database).


.. [#] See http://celery.readthedocs.org/en/latest/userguide/tasks.html#database-transactions
