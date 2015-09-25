Introduction
============

``collective.celery`` provides the necessary bits to use `Celery <http://celery.readthedocs.org/en/latest/>`_ within `Plone <http://plone.org/>`_.

Much of the code here is based off of David Glick's gists, Asko's work and `pyramid_celery <https://pypi.python.org/pypi/pyramid_celery/>`_.


Configuration
=============

Add the python package to your buildout eggs section::

    eggs =
        ...
    # Change this to celery[redis] or celery[librabbitmq] if you want to use Redis or RabbitMQ respectively.
        celery[sqlalchemy]
        collective.celery
        ...


You'll also need to configure buildout to include the celery script in your bin directory::

    parts =
        ...
        scripts
        ...

    [scripts]
    recipe = zc.recipe.egg
    eggs = ${buildout:eggs}
    scripts = pcelery

.. note::
   If you already have a ``scripts`` section, just make sure it also generates pcelery and that the eggs are correct.

Finally, configure celery by setting ``environment-vars`` on your client configuration.
All variables defined there are passed on to celery configuration::

    environment-vars =
        ...
    # CELERY_IMPORTS is required to load your tasks correctly for your project
        CELERY_IMPORTS ('my.package.tasks',)
    # basic example just using sqlalchemy
        BROKER_URL sqla+sqlite:///${buildout:directory}/celerydb.sqlite?timeout=30
        CELERY_RESULT_BACKEND db+sqlite:///${buildout:directory}/celeryresults.sqlite?timeout=30
        ...

Creating tasks
==============

This package comes with two decorators to use for creating tasks.

``default``
    run the task as the user who created the task
``as_admin``
    run the task as an admin

Example::

    from collective.celery import task

    @task()
    def do_something(context, arg1, foo='bar'):
        pass

    @task.as_admin()
    def do_something_as_admin(context, arg1, foo='bar'):
        pass


And to schedule the taks::

    my_content_object = self.context
    do_something.delay(my_content_object, 'something', foo='bar')

Or alternatively::

    my_content_object = self.context
    do_something.apply_async((my_content_object, 'something'), {'foo': 'bar'})

Check out :ref:`calliung tasks <celery:calling-guide>` in the celery documentation for more details.

.. note::
   You do not need to specify a context object if you don't use it for anything meaningful in the task: the system will already set up the correct site and if you just need that you can obtain it easily (maybe via ``plone.api``).


Registering Tasks
=================

If you don't want to need to set the ``CELERY_IMPORTS`` environment value,
you can use package entry points to load tasks.

Example setup.py::

    entry_points="""
      # -*- Entry points: -*-
      [celery_tasks]
      mypackage = mypackage.tasks
      """


Starting the task runner
========================

The package simply provides a wrapper around the default task runner script which takes an additional zope config parameter::

    $ bin/pcelery worker parts/instance/etc/zope.conf

.. note::
   In order for the worker to start correctly, you should have a ZEO server setup. Else the worker will fail stating it cannot obtain a lock on the database.

.. note::
   You can change the log verbosity::

    $ bin/pcelery worker parts/instance/etc/zope.conf --loglevel=DEBUG

.. _developing-and-testing:

Developing and testing
======================

If you are developing, and do not want the hassle of setting up a ZEO server and run the worker, you can set the following in your instance ``environment-vars``::

    environment-vars =
        ...
        CELERY_ALWAYS_EAGER True
    # CELERY_IMPORTS is required to load your tasks correctly for your project
        CELERY_IMPORTS ('my.package.tasks',)
    # basic example just using sqlalchemy
        BROKER_URL sqla+sqlite:///${buildout:directory}/celerydb.sqlite?timeout=30
        CELERY_RESULT_BACKEND db+sqlite:///${buildout:directory}/celeryresults.sqlite?timeout=30
        ...

In this way, thanks to the `CELERY_ALWAYS_EAGER setting <http://celery.readthedocs.org/en/latest/configuration.html#celery-always-eager>`_, celery will not send the task to the worker at all but execute immediately when ``delay`` or ``apply_async`` are called.

Similarly, in tests, we provide a layer that does the following:

 #. Set ``CELERY_ALWAYS_EAGER`` for you, so any function you are testing that calls an asyncroinous function will have that function executed after commit (see :doc:`execution-model`)
 #. Use a simple, in-memory SQLite database to store results

To use it, your package should depend, in its ``test`` extra requirement, from ``collective.celery[test]``::

  # setup.py
  ...
  setup(name='my.package',
      ...
      extras_require={
          ...
          'test': [
              'collective.celery[test]',
          ],
          ...
      },
  ...

And then, in your ``testing.py``::

  ...
  from collective.celery.testing import CELERY
  ...

  class MyLayer(PloneSandboxLayer):

      defaultBases = (PLONE_FIXTURE, CELERY, ...)

  ...
