<p align="center">
  <img src="https://raw.githubusercontent.com/IMIO/collective.celery/master/docs/collective-celery.svg" alt="collective.celery" width="620">
</p>

<p align="center">
  <a href="https://www.python.org/"><img alt="Python 3.10 or later" src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white"></a>
  <a href="https://plone.org/"><img alt="Plone 6.0, 6.1 and 6.2" src="https://img.shields.io/badge/Plone-6.0%20%7C%206.1%20%7C%206.2-009AD1"></a>
  <a href="https://docs.celeryq.dev/"><img alt="Celery 5" src="https://img.shields.io/badge/Celery-5-37814A?logo=celery&logoColor=white"></a>
  <a href="LICENSE.txt"><img alt="License GPL 2.0" src="https://img.shields.io/badge/license-GPL--2.0-lightgrey"></a>
</p>

# collective.celery

collective.celery runs [Celery](https://docs.celeryq.dev/) tasks inside a Plone site. A task queued from a browser view runs later in a Celery worker, in its own ZODB transaction, as the user who queued it. The worker is a thin wrapper around the Celery command line that starts Zope first, so tasks can use `plone.api`, the catalog and any other Plone API.

Version 2, in this repository, targets Plone 6.0, 6.1 and 6.2 on Python 3.10 or later, with Celery 5. The 1.x releases on PyPI target Plone 4 and 5 on Python 2.

## How it works

Tasks are sent after the transaction commits. Calling `delay()` or `apply_async()` inside a request does not send the task right away. The task is attached to the current transaction and sent when that transaction commits. If the transaction is aborted, the task is never sent. This avoids a race where the worker starts before the objects the task needs are in the database. The task id is generated in advance, so the caller still gets an `AsyncResult`.

Each task runs in its own transaction. The worker opens the ZODB, traverses to the Plone site, begins a transaction, runs the function and commits. An exception aborts the transaction and is re-raised, so Celery logs it and marks the task as failed. A ZODB `ConflictError` aborts the transaction and retries the task through the Celery retry mechanism.

Tasks run as the user who queued them. The user id travels with the task, and the worker logs that user in before it runs the function. With `@task.as_admin()` the task runs as the user whose id is `admin` instead. That user must exist in the site or in the Zope root.

Content objects are passed as paths. Arguments that are Zope content (objects that provide `OFS.interfaces.IItem`) are serialized as `object://<path>` and looked up again in the worker. All other arguments go through the Celery serializer, pickle by default (see [Configuration](#configuration)). Do not pass other persistent objects, such as a field value or an attribute of a content object: they would be pickled by value and the worker would get a disconnected copy.

## Requirements

* Python 3.10 or later.
* Plone 6.0, 6.1 or 6.2.
* Celery 5 and a broker it supports, such as RabbitMQ or Redis.
* A database setup that accepts several clients at the same time, such as ZEO or RelStorage. The worker opens its own connection to the database. With a plain `Data.fs`, the worker fails because the Zope instance already holds the lock on the file.

## Installation

Version 2 is not on PyPI yet. Check it out from this repository, for example with mr.developer:

```ini
[buildout]
extensions = mr.developer
auto-checkout = collective.celery

[sources]
collective.celery = git https://github.com/IMIO/collective.celery.git
```

Or with pip:

```
pip install git+https://github.com/IMIO/collective.celery.git
```

Then add the package to the instance and generate the `pcelery` script:

```ini
[buildout]
parts =
    zeoserver
    instance
    celery

[zeoserver]
recipe = plone.recipe.zeoserver
zeo-address = 8100

[instance]
recipe = plone.recipe.zope2instance
zeo-client = true
zeo-address = ${zeoserver:zeo-address}
eggs =
    Plone
    celery
    collective.celery
    my.package
environment-vars =
    CELERY_BROKER_URL amqp://guest:guest@localhost:5672//
    CELERY_RESULT_BACKEND rpc://
    CELERY_TASKS my.package.tasks

[celery]
recipe = zc.recipe.egg
eggs =
    ${instance:eggs}
    ZEO
scripts = pcelery
```

## Configuration

Celery reads its settings from the environment of the Zope instance. collective.celery passes every variable of the `environment-vars` option (the `<environment>` section of `zope.conf`) and of the process environment to the Celery configuration. The `zope.conf` values win over the process environment.

The variable names are translated as follows.

| Environment variable | Celery setting | Example |
| --- | --- | --- |
| `CELERY_<NAME>` | `<name>`, in lower case | `CELERY_BROKER_URL` sets `broker_url` |
| `CELERYBEAT_<NAME>` | `beat_<name>` | `CELERYBEAT_SCHEDULE_FILENAME` sets `beat_schedule_filename` |
| `CELERYD_<NAME>` | `worker_<name>` | `CELERYD_CONCURRENCY` sets `worker_concurrency` |

Values are converted to the type of the Celery setting: `true` and `false` for booleans, numbers for integers and floats, and Python literals for lists, tuples and dictionaries. Double quotes are removed from strings.

Two variables are specific to collective.celery.

* `CELERY_TASKS` is a space separated list of modules that the worker imports, so that their tasks are registered. The `celery_tasks` entry point described below is the alternative.
* `CELERY_TASK_ALWAYS_EAGER` runs tasks in the calling process instead of sending them to a worker. See [Development and testing](#development-and-testing).

collective.celery sets three defaults: `task_serializer` and `result_serializer` are `pickle`, and `accept_content` accepts `application/json` and `application/x-python-serialize`. Pickle is needed to pass arbitrary Python objects as arguments.

Any other Celery setting works the same way, for example:

```ini
environment-vars =
    CELERY_BROKER_URL amqp://guest:guest@localhost:5672//
    CELERY_RESULT_BACKEND rpc://
    CELERY_TASKS my.package.tasks
    CELERY_WORKER_CONCURRENCY 2
    CELERY_TASK_DEFAULT_QUEUE default
    CELERY_TASK_ROUTES {'my.package.tasks.rebuild_index': {'queue': 'slow'}}
    CELERYBEAT_SCHEDULE_FILENAME ${buildout:directory}/var/celerybeat-schedule
```

## Writing tasks

The `task` decorator comes in two forms.

```python
from collective.celery import task
from plone import api


@task()
def reindex(container, recursive=False):
    """Run as the user who queued the task."""
    for brain in api.content.find(context=container):
        brain.getObject().reindexObject()


@task.as_admin()
def purge_old_drafts():
    """Run as the admin user."""
    ...
```

The task name is the dotted name of the function, here `my.package.tasks.reindex`.

Queue a task from a view with `delay()` or `apply_async()`. `apply_async()` takes the positional arguments as a tuple and the keyword arguments as a dictionary, and accepts the usual Celery options:

```python
reindex.delay(self.context, recursive=True)

result = reindex.apply_async((self.context,), {"recursive": True}, queue="slow")
result.id
```

The task is sent when the current transaction commits. Pass `without_transaction=True` to send it right away.

### Queueing tasks outside of Zope

Celery beat, a script or a custom consumer has no current site. Give the path of the site with the `site_path` keyword argument. The task is sent at once, because there is no Zope transaction to wait for.

```python
purge_old_drafts.apply_async((), {"site_path": "/Plone"})
```

Without `site_path`, `apply_async()` raises a `ValueError`.

### Loading tasks in the worker

The worker must import the modules that define the tasks. Either list the modules in `CELERY_TASKS`, or declare a `celery_tasks` entry point in the `setup.py` of the package:

```python
entry_points="""
[celery_tasks]
my.package = my.package.tasks
"""
```

A tasks module can define a function `extra_config(startup)`. The worker calls it after Zope has started, with the result of `Zope2.Startup.run.configure_wsgi`.

### Class based tasks

Custom task classes must inherit from `collective.celery.base_task.AfterCommitTask`, which implements the after-commit queueing:

```python
from collective.celery import task
from collective.celery.base_task import AfterCommitTask


class LoudTask(AfterCommitTask):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        notify_operators(exc, task_id, args, kwargs, einfo)


@task(base=LoudTask)
def fails_loudly(*args):
    return sum(args)
```

The Celery application is available through `collective.celery.utils.getCelery()`.

## Running the worker

`pcelery` wraps the `celery` command. It takes one extra argument, the Zope configuration file. The argument that ends with `.conf` is used to start Zope (configuration, database connection, ZCML) before the Celery command runs. All other arguments are passed to Celery unchanged.

```
bin/pcelery worker parts/instance/etc/zope.conf --loglevel=INFO
bin/pcelery worker parts/instance/etc/zope.conf -Q default,slow -n slow@%h
bin/pcelery beat parts/instance/etc/zope.conf
bin/pcelery inspect active parts/instance/etc/zope.conf
```

The configuration file must be the one of a ZEO or RelStorage client. The worker shares the database with the Zope instance, and the ZEO server must run before the worker starts.

A worker only consumes the queues given with `-Q`. Tasks routed to a queue that no worker consumes stay in the broker.

## Periodic tasks

Celery beat runs outside of Zope. Set `beat_schedule` on the Celery application in a tasks module, give `site_path` in the kwargs of each entry, and use `@task.as_admin()`, because there is no user to run the task as.

```python
from celery.schedules import crontab
from collective.celery import task
from collective.celery.utils import getCelery


@task.as_admin()
def purge_old_drafts():
    ...


getCelery().conf.beat_schedule = {
    "purge-old-drafts": {
        "task": purge_old_drafts.name,
        "schedule": crontab(hour=3, minute=0),
        "kwargs": {"site_path": "/Plone"},
    },
}
```

Start beat with `bin/pcelery beat parts/instance/etc/zope.conf`. Set `CELERYBEAT_SCHEDULE_FILENAME` to keep the schedule state file out of the current directory.

## Development and testing

### Eager mode

Set `CELERY_TASK_ALWAYS_EAGER true` in the `environment-vars` of a development instance to work without a broker and a worker. Tasks then run at once, in the calling process, inside the current transaction and as the current user. The `as_admin` switch is skipped. `delay()` and `apply_async()` return an `EagerResult` that already holds the return value.

### Test layer

`collective.celery.testing` provides `COLLECTIVE_CELERY_FIXTURE`, a `PloneSandboxLayer` that loads the ZCML of the package, installs it and applies the `plone.app.contenttypes:default` profile. `COLLECTIVE_CELERY_INTEGRATION_TESTING` is the matching integration layer. Use the fixture as a base of your own layer, and depend on `collective.celery[test]` in the `test` extra of your package.

The fixture does not switch Celery to eager mode. Do it in `setUp()`, and give the function runner the test application with `setApp()`:

```python
import unittest

from collective.celery.utils import getCelery
from collective.celery.utils import setApp
from my.package.testing import MY_PACKAGE_INTEGRATION_TESTING
from my.package.tasks import reindex


class TestTasks(unittest.TestCase):

    layer = MY_PACKAGE_INTEGRATION_TESTING

    def setUp(self):
        getCelery().conf["task_always_eager"] = True
        setApp(self.layer["app"])
        self.portal = self.layer["portal"]

    def test_reindex(self):
        result = reindex.delay(self.portal)
        self.assertTrue(result.successful())
```

### Running the tests of this package

With a buildout that has a test runner part for `collective.celery[test]`:

```
bin/test -s collective.celery
```

## Broker notes

RabbitMQ 4 refuses transient queues that are not exclusive. Celery declares its remote control and event queues that way by default, and the worker cannot start. Make them durable:

```ini
environment-vars =
    CELERY_CONTROL_QUEUE_DURABLE true
    CELERY_EVENT_QUEUE_DURABLE true
```

With the `rpc://` result backend, only the process that sent a task can read its result, and only one time. A browser view that polls task states from another process needs a database or cache backend.

## Troubleshooting

* `LockError: Couldn't lock '.../Data.fs.lock'` when the worker starts: the worker opens the ZODB. Use ZEO or RelStorage, and give the worker the configuration file of a client.
* `No site found. Give a site_path keyword argument to queue the task ...`: the task is queued outside of a request. Add `site_path` to the keyword arguments.
* The worker logs `Received unregistered task`: the module that defines the task is not imported in the worker. Add it to `CELERY_TASKS` or declare the `celery_tasks` entry point.
* A task queued from a view never runs: the transaction was aborted after the task was queued, or no worker consumes the queue it was routed to. Check the queue in the broker.

## Changelog

See [docs/CHANGES.rst](docs/CHANGES.rst).

## Credits and license

collective.celery was written by Nathan Van Gheem for the [Plone collective](https://github.com/collective/collective.celery), based on gists by David Glick, work by Asko Soukka and [pyramid_celery](https://pypi.org/project/pyramid-celery/). This fork, maintained by [iMio](https://www.imio.be/), carries the Plone 6 port.

The package is released under the GNU General Public License, version 2. See [LICENSE.txt](LICENSE.txt).
