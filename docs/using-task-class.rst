Using class based tasks
=======================

If you need to do advanced things with tasks and you think you need a class-based task (see :ref:`celery:task-custom-classes`), you can do it, but you have to keep in mind two things:

 #. Always inherit from :py:class:`collective.celery.base_task.AfterCommitTask`
 #. If you're doing weird stuff during registration, remember that the default celery app is obtained via :py:func:`collective.celery.utils.getCelery`

Example
-------

Here's an example on how to create a custom base task class that vfails quite loudly::


  from collective.celery.base_task import AfterCommitTask
  from collective.celery import task

  class LoudBaseTask(AfterCommitTask):

      abstract = True

      def on_failure(self, exc, task_id, args, kwargs, einfo):
          # Send emails to people, ring bells, call 911
          yell_quite_loudly(exc, task_id, args, kwargs, einfo)

  @task(base=LoudBaseTask)
  def fails_loudly(*args):
      return sum(args)
