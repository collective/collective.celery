from celery.exceptions import ImproperlyConfigured
from celery.result import AsyncResult
from collective.celery import getCelery
from collective.celery.backends import zodb as zodb_module
from collective.celery.backends.zodb import Record
from collective.celery.backends.zodb import ROOT_KEY
from collective.celery.backends.zodb import ZODBBackend
from collective.celery.testing import COLLECTIVE_CELERY_FUNCTIONAL_TESTING
from collective.celery.utils import _getCelery
from collective.celery.utils import setApp
from unittest import mock
from ZODB.POSException import ConflictError

import celery.app.backends
import time
import transaction
import unittest
import Zope2


def _set_backend_cache(cache, local):
    app = getCelery()
    app._backend_cache = cache
    app._local.backend = local


class TestZODBBackend(unittest.TestCase):

    layer = COLLECTIVE_CELERY_FUNCTIONAL_TESTING

    def setUp(self):
        app = getCelery()
        conf = app.conf
        # Keep the SQLite backend objects. A new in-memory SQLite backend
        # has no tables.
        self._saved = (
            app._backend_cache, getattr(app._local, 'backend', None))
        _set_backend_cache(None, None)
        conf['broker_url'] = 'sqla+sqlite://'
        conf['result_backend'] = 'zodb://'
        conf['task_always_eager'] = True
        conf['task_store_eager_result'] = True
        _getCelery()
        setApp(self.layer['app'])
        self.portal = self.layer['portal']
        self.backend = ZODBBackend(app=getCelery(), url='zodb://')

    def tearDown(self):
        getCelery().conf['result_backend'] = 'db+sqlite://'
        _set_backend_cache(*self._saved)
        _getCelery()

    def _open(self):
        """Open a connection with its own transaction manager."""
        return Zope2.DB.open(
            transaction_manager=transaction.TransactionManager())

    def _tree(self):
        conn = self._open()
        try:
            return dict(conn.root()[ROOT_KEY].items())
        finally:
            conn.transaction_manager.abort()
            conn.close()

    def test_set_and_get(self):
        self.backend.set('key', b'value')
        self.assertEqual(self.backend.get('key'), b'value')
        # A second connection sees the committed record.
        conn = self._open()
        try:
            self.assertEqual(conn.root()[ROOT_KEY]['key'].payload, b'value')
        finally:
            conn.transaction_manager.abort()
            conn.close()

    def test_get_missing_and_mget(self):
        self.assertIsNone(self.backend.get('missing'))
        self.assertEqual(self.backend.mget(['a', 'b']), [None, None])
        self.backend.set('a', b'1')
        self.backend.set('c', b'3')
        self.assertEqual(
            self.backend.mget(['a', 'b', 'c']), [b'1', None, b'3'])

    def test_global_transaction_untouched(self):
        transaction.begin()
        self.portal.title = 'Changed'
        self.assertIsNone(self.backend.get('key'))
        self.backend.set('key', b'value')
        self.assertTrue(self.portal._p_changed)
        self.assertEqual(transaction.get().status, 'Active')
        transaction.abort()
        self.assertNotEqual(self.portal.title, 'Changed')

    def test_delete(self):
        self.backend.set('key', b'value')
        self.backend.delete('key')
        self.assertIsNone(self.backend.get('key'))
        self.backend.delete('key')
        self.assertIsNone(self.backend.get('key'))

    def test_set_updates_record_in_place(self):
        self.backend.set('key', b'one')
        conn = self._open()
        try:
            first = conn.root()[ROOT_KEY]['key']
            first_oid = first._p_oid
        finally:
            conn.transaction_manager.abort()
            conn.close()
        self.backend.set('key', b'two')
        conn = self._open()
        try:
            second = conn.root()[ROOT_KEY]['key']
            self.assertEqual(second._p_oid, first_oid)
            self.assertEqual(second.payload, b'two')
            self.assertEqual(len(conn.root()[ROOT_KEY]), 1)
        finally:
            conn.transaction_manager.abort()
            conn.close()

    def test_cleanup(self):
        self.backend.expires = 10
        self.backend.set('fresh', b'1')
        conn = self._open()
        try:
            tree = conn.root()[ROOT_KEY]
            tree['old'] = Record(time.time() - 100, b'2')
            conn.transaction_manager.commit()
        finally:
            conn.close()
        self.backend.cleanup()
        self.assertEqual(list(self._tree()), ['fresh'])

    def test_cleanup_batches(self):
        self.backend.expires = 10
        self.backend.set('fresh', b'1')
        conn = self._open()
        try:
            tree = conn.root()[ROOT_KEY]
            past = time.time() - 100
            for number in range(1200):
                tree['old-%s' % number] = Record(past, b'x')
            conn.transaction_manager.commit()
        finally:
            conn.close()
        self.backend.cleanup()
        self.assertEqual(list(self._tree()), ['fresh'])

    def test_cleanup_without_expires(self):
        self.backend.set('key', b'1')
        conn = self._open()
        try:
            conn.root()[ROOT_KEY]['key'].stamp = time.time() - 100000
            conn.transaction_manager.commit()
        finally:
            conn.close()
        self.backend.expires = None
        self.backend.cleanup()
        self.assertEqual(list(self._tree()), ['key'])

    def test_conflict_retry(self):
        calls = []

        class FailingTransactionManager(transaction.TransactionManager):
            def commit(self):
                calls.append(1)
                if len(calls) == 1:
                    raise ConflictError()
                return super().commit()

        with mock.patch.object(
                zodb_module, 'TransactionManager',
                FailingTransactionManager):
            self.backend.set('key', b'value')
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.backend.get('key'), b'value')

    def test_url_with_host_is_refused(self):
        with self.assertRaises(ImproperlyConfigured):
            ZODBBackend(app=getCelery(), url='zodb://celery')

    def test_entry_point_resolution(self):
        cls, url = celery.app.backends.by_url('zodb://')
        self.assertIs(cls, ZODBBackend)

    def test_eager_task_stores_success(self):
        from .test_task import echo
        result = echo.delay('foo')
        fresh = AsyncResult(
            result.id, backend=ZODBBackend(app=getCelery(), url='zodb://'))
        self.assertEqual(fresh.state, 'SUCCESS')
        self.assertEqual(fresh.result, 'foo')
