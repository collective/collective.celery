from BTrees.OOBTree import OOBTree
from celery.backends.base import KeyValueStoreBackend
from celery.exceptions import ImproperlyConfigured
from celery.utils.log import get_logger
from kombu.utils.encoding import bytes_to_str
from kombu.utils.encoding import ensure_bytes
from persistent import Persistent
from transaction import TransactionManager
from ZODB.POSException import ConflictError

import time
import Zope2

logger = get_logger(__name__)

ROOT_KEY = "collective.celery"
MAX_ATTEMPTS = 3
BATCH_SIZE = 500


class Record(Persistent):
    """One stored result.

    stamp is the time of the last write. payload is the serialized
    result as bytes.
    """

    def __init__(self, stamp, payload):
        self.stamp = stamp
        self.payload = payload


class ZODBBackend(KeyValueStoreBackend):
    """Store task states and results in the ZODB.

    Every call uses its own connection and its own transaction manager.
    The global transaction of the caller stays untouched.
    """

    # An OOBTree needs keys of one type.
    key_t = bytes_to_str

    def __init__(self, url=None, *args, **kwargs):
        if url is not None and url != "zodb://":
            raise ImproperlyConfigured('The ZODB result backend URL must be "zodb://".')
        super().__init__(*args, **kwargs)
        self.url = url

    def __reduce__(self, args=(), kwargs=None):
        kwargs = {} if not kwargs else kwargs
        return super().__reduce__(args, {**kwargs, "url": self.url})

    def _run(self, func, write):
        """Call func(tree) in a private connection and transaction.

        On a read, tree is None when no result exists yet. A write
        commits and retries on ConflictError. A read aborts.
        """
        if Zope2.DB is None:
            # Celery beat and the worker main process do not open the app.
            Zope2.startup_wsgi()
        attempts = MAX_ATTEMPTS if write else 1
        for attempt in range(1, attempts + 1):
            tm = TransactionManager()
            conn = Zope2.DB.open(transaction_manager=tm)
            try:
                root = conn.root()
                tree = root.get(ROOT_KEY)
                if tree is None and write:
                    tree = root[ROOT_KEY] = OOBTree()
                result = func(tree)
                if write:
                    tm.commit()
                else:
                    tm.abort()
                return result
            except ConflictError:
                tm.abort()
                if attempt == attempts:
                    raise
                logger.warning(
                    "ZODB result backend: conflict, retry %s of %s",
                    attempt,
                    attempts - 1,
                )
                time.sleep(0.05 * attempt)
            except Exception:
                tm.abort()
                raise
            finally:
                conn.close()

    def get(self, key):
        def read(tree):
            record = None if tree is None else tree.get(key)
            return None if record is None else record.payload

        return self._run(read, write=False)

    def mget(self, keys):
        def read(tree):
            records = [None if tree is None else tree.get(k) for k in keys]
            return [None if r is None else r.payload for r in records]

        return self._run(read, write=False)

    def set(self, key, value):
        value = ensure_bytes(value)

        def store(tree):
            record = tree.get(key)
            if record is None:
                tree[key] = Record(time.time(), value)
            else:
                record.stamp = time.time()
                record.payload = value

        self._run(store, write=True)

    def delete(self, key):
        def remove(tree):
            tree.pop(key, None)

        self._run(remove, write=True)

    def cleanup(self):
        """Delete the records older than result_expires."""
        if not self.expires:
            return
        cutoff = time.time() - self.expires

        def collect(tree):
            if tree is None:
                return []
            return [k for k, r in tree.items() if r.stamp < cutoff]

        expired = self._run(collect, write=False)

        def purge(batch):
            def remove(tree):
                count = 0
                for key in batch:
                    record = tree.get(key)
                    # A newer write keeps the record.
                    if record is not None and record.stamp < cutoff:
                        del tree[key]
                        count += 1
                return count

            return remove

        deleted = 0
        for start in range(0, len(expired), BATCH_SIZE):
            batch = expired[start : start + BATCH_SIZE]
            deleted += self._run(purge(batch), write=True)
        logger.info("ZODB result backend: deleted %s expired records", deleted)

    def exception_safe_to_retry(self, exc):
        return isinstance(exc, ConflictError)
