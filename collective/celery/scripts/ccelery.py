# a lot of this pulled out of pyramid_celery
from App.config import getConfiguration
from celery import VERSION as celery_version
from celery.bin.celery import CeleryCommand
from celery.utils.log import get_task_logger
from collective.celery.utils import getCelery
from importlib import import_module
from importlib.metadata import entry_points

import os
import sys

logger = get_task_logger(__name__)


class CommandMixin:
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

    # find the index of the conf file in the args
    conf_index = 2
    for idx, arg in enumerate(sys.argv):
        if ".conf" in arg:
            conf_index = idx
            break
    filepath = sys.argv[conf_index]
    os.environ["ZOPE_CONFIG"] = filepath
    sys.argv = [""]
    from Zope2.Startup.run import configure_wsgi

    startup = configure_wsgi(os.environ["ZOPE_CONFIG"])

    # Fix for setuptools generated scripts, so that it will
    # work with multiprocessing fork emulation.
    # (see multiprocessing.forking.get_preparation_data())
    if __name__ != "__main__":
        sys.modules["__main__"] = sys.modules[__name__]

    # load entry point tasks up
    tasks = []
    for entry_point in entry_points(group="celery_tasks"):
        try:
            tasks.append((entry_point.name, entry_point.load()))
        except ImportError:
            logger.warning("error importing tasks: " + entry_point.name)
            raise
    tasks = dict(tasks)
    for name, task_list in tasks.items():
        logger.warning("importing tasks: " + name)
        extra_config = getattr(task_list, "extra_config", None)
        if extra_config is not None:
            logger.warning("Found additional Zope config.")
            extra_config(startup)

    # load env tasks up
    tasks = getConfiguration().environment.get("CELERY_TASKS")
    if tasks:
        for task_list in tasks.split():
            try:
                logger.warning("importing tasks: " + task_list)
                module = import_module(task_list)
                extra_config = getattr(module, "extra_config", None)
                if extra_config is not None:
                    logger.warning("Found additional Zope config.")
                    extra_config(startup)
            except ImportError:
                logger.warning("error importing tasks: " + task_list)
                raise
    argv.remove(filepath)
    # restore argv
    sys.argv = argv
    if celery_version.major >= 5:
        # Celery uses click in v5+
        getCelery().start(argv=argv[1:])
    else:
        Worker(app=getCelery()).execute_from_commandline()
