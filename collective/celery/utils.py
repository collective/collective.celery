import os
import logging
import sys
from celery.app import defaults
try:
    from celery import registry
except ImportError:
    # Celery >= 3.1
    from celery import current_app as registry

from App.config import getConfiguration
from celery import current_app as celery
import threading
import Zope2


_local = threading.local()

logger = logging.getLogger('collective.celery')


def _bool(term, table={"false": False, "no": False, "0": False,
                       "true": True, "yes": True, "1": True}):
    try:
        return table[term.lower()]
    except KeyError:
        raise TypeError("Can't coerce %r to type bool" % (term, ))


_types = {
    'any': (object, None),
    'bool': (bool, _bool),
    'dict': (dict, eval),
    'float': (float, float),
    'int': (int, int),
    'list': (list, eval),
    'tuple': (tuple, eval),
    'string': (str, str),
}

_options = dict(
    (key, _types[opt.type])
    for key, opt in defaults.flatten(defaults.NAMESPACES)
)


def getCeleryOptions():
    zconfig = getConfiguration()
    if hasattr(zconfig, 'environment'):
        environ = zconfig.environment.items()
    else:
        # sort of for testing...
        environ = os.environ.items()

    config = {}
    for key, value in environ:
        opt_type = _options.get(key)
        if opt_type:
            if opt_type[0] == str:
                value = value.replace('"', '')
            elif opt_type[0] is object:
                try:
                    value = eval(value)
                except:
                    pass  # any can be anything; even a string
            elif not isinstance(value, opt_type[0]):
                value = opt_type[1](value)
        config[key] = value
    return config


def _getCelery():
    celery.add_defaults(getCeleryOptions())
    # delete cached property in order to get them reloaded from the new conf
    del(celery.backend)
    for name, task in registry.tasks.items():
        # ensure that every already registed tasks doens use an unconfigured
        # backend.
        task.backend = celery.backend
    return celery


def getCelery():
    if not hasattr(_local, 'celery'):
        _local.celery = _getCelery()
    return _local.celery


def getApp(*args, **kwargs):
    if Zope2.bobo_application is None:
        orig_argv = sys.argv
        sys.argv = ['']
        res = Zope2.app(*args, **kwargs)
        sys.argv = orig_argv
        return res
    # should set bobo_application
    # man, freaking zope2 is weird
    return Zope2.bobo_application(*args, **kwargs)
