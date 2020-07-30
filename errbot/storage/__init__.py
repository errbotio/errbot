import types
from collections.abc import MutableMapping
from contextlib import contextmanager
import logging
log = logging.getLogger(__name__)


class StoreException(Exception):
    pass


class StoreAlreadyOpenError(StoreException):
    pass


class StoreNotOpenError(StoreException):
    pass


class StoreMixin(MutableMapping):
    """
     This class handle the basic needs of bot plugins and core like loading, unloading and creating a storage
    """

    def __init__(self):
        self._store = None
        self.namespace = None

    def open_storage(self, storage_plugin, namespace):
        if hasattr(self, 'store') and self._store is not None:
            raise StoreAlreadyOpenError("Storage appears to be opened already")
        log.debug("Opening storage '%s'", namespace)
        self._store = storage_plugin.open(namespace)
        self.namespace = namespace

    def close_storage(self):
        if not hasattr(self, '_store') or self._store is None:
            raise StoreNotOpenError("Storage does not appear to have been opened yet")
        self._store.close()
        self._store = None
        log.debug("Closed storage '%s'", self.namespace)

    # those are the minimal things to behave like a dictionary with the UserDict.DictMixin
    def __getitem__(self, key):
        return self._store.get(key)

    @contextmanager
    def mutable(self, key, default=None):
        try:
            obj = self._store.get(key)
        except KeyError:
            obj = default
        yield obj
        # implements autosave for a plugin persistent entry
        # with self['foo'] as f:
        #     f[4] = 2
        # saves the entry !
        self._store.set(key, obj)

    def __setitem__(self, key, item):
        return self._store.set(key, item)

    def __delitem__(self, key):
        return self._store.remove(key)

    def keys(self):
        return self._store.keys()

    def __len__(self):
        return self._store.len()

    def __iter__(self):
        for i in self._store.keys():
            yield i

    def __contains__(self, x):
        try:
            self._store.get(x)
            return True
        except KeyError:
            return False

    # compatibility with with
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close_storage()
