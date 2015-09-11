# a lot of this pulled out of pyramid_celery
import logging
import os
import sys

from App.config import getConfiguration
from celery.bin.celery import CeleryCommand
from collective.celery.utils import getCelery
from pkg_resources import iter_entry_points

logger = logging.getLogger('collective.celery')


class CommandMixin(object):
    preload_options = ()

    def setup_app_from_commandline(self, argv):
        self.app = getCelery()
        return argv


class Worker(CommandMixin, CeleryCommand):
    pass


def main(argv=sys.argv):
    if len(sys.argv) < 3:
        raise Exception("must specify a zope config file and a celery command")
    argv = argv
    filepath = sys.argv[2]
    os.environ['ZOPE_CONFIG'] = filepath
    sys.argv = ['']
    from Zope2.Startup.run import configure
    configure(os.environ['ZOPE_CONFIG'])

    # Fix for setuptools generated scripts, so that it will
    # work with multiprocessing fork emulation.
    # (see multiprocessing.forking.get_preparation_data())
    if __name__ != "__main__":
        sys.modules["__main__"] = sys.modules[__name__]

    # load tasks up
    tasks = dict([(i.name, i.load()) for i in iter_entry_points(
                  group='celery_tasks', name=None)])

    tasks = getConfiguration().environment.get('CELERY_TASKS')
    if tasks:
        try:
            __import__(tasks)
        except ImportError:
            logger.warn('error importing tasks: ' + tasks)
    argv.remove(argv[2])
    # restore argv
    sys.argv = argv
    Worker(app=getCelery()).execute_from_commandline()
