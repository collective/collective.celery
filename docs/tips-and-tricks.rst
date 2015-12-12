Tips and tricks
===============

.. _usage-always-eager:

Usage of ``CELERY_ALWAYS_EAGER``
--------------------------------

The ``CELERY_ALWAYS_EAGER`` setting is very useful when developing, and also the only available option to test your tasks without going mad [#]_.

In a nutshell, it works by completely skipping the whole "enqueing the task and letting the worker run it" part of Celery and directly executing the task when you "queue" it.

But since we do always delay the actual execution after the transaction has committed (see :ref:`execution-model`) this doesn't go as simply as stated.

While the testing layer sets up evrything for you without you having to worry about these nasty details (see :ref:`developing-and-testing`) when you are developing with ``CELERY_ALWAYS_EAGER`` enabled you **must** provide a result backend for celery to use (else retrieving tasks result will break horribly).

There are two backends that you can use:

 #. The safest option is the SQLite backend used in :ref:`developing-and-testing`
 #. The in-memory result backend (the test default), which involves also setting the ``CELERY_CACHE_BACKEND`` to ``memory://``. Note that this backend, while thread safe, absolutely does not work across different processes. Therefore it isn't recommended.

Tests
-----

When you are testing a product that relies on ``collective.celery``, yopu have two options available: call the task directly, or call it indirectly.

In the first, you get an :py:class:`~celery.result.EagerResult` back, and therefore you can immediately see its return value::

  import unittest
  import transaction
  from collective.celery import task
  # Make sure has collective.celery.testing.COLLECTIVE_CELERY_FIXTURE as base
  from ..testing import MY_LAYER


  @task()
  def sum_all(*args):
      return sum(args)


  class TestSum(unittest.TestCase):

      layer = MY_LAYER

      def test_sum_all(self):
          result = sum_all.delay(1,2,3)
          transaction.commit() # Up until here, it is not executed
          self.assertEqual(result, 6)

In more complex cases, like a robot test, where you might have a browserview that polls the result backend, everything should work smoothly as long as you have :py:data:`collective.celery.testing.COLLECTIVE_CELERY_FIXTURE` within your layer's bases.


.. [#]: Citation needed
