Introduction
============

This package aims to bring celery integration into plone.

Much of the code here is based off of David Glick's gists, Asko's work and pyramid_celery.


Configuration
-------------

Add the python package to your buildout eggs section::

    eggs =
        ...
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
    interpreter = zopepy
    scripts = zopepy pcelery


Finally, configure celery by setting environment-vars on your client configuration. All
variables defined there are passed on to celery configuration::

    environment-vars =
        ...
    # CELERY_TASKS is required to load your tasks correctly for your project
        CELERY_TASKS my.package.tasks
    # basic example just using sqlalchemy
        BROKER_URL sqla+sqlite:///${buildout:directory}/celerydb.sqlite?timeout=30
        CELERY_RESULT_BACKEND db+sqlite:///${buildout:directory}/celeryresults.sqlite?timeout=30
        ...


Creating tasks
--------------

This package comes with two decorators to use for creating tasks.

as_admin
  run the task as an admin
authorized
  run the task as the user who created the task


Example::

    from collective.celery import tasks
    @task.as_admin
    def do_something(portal, arg1, foo='bar'):
        pass

And to schedule the taks::

    do_something.delay('something', foo='bar')

You do not need to specify the portal object as it'll automatically be applied for you.


Starting the task runner
------------------------

The package simply provides a wrapper around the default task runner script which takes
an additional zope config parameter::

    ./bin/pcelery worker parts/client2/etc/zope.conf
