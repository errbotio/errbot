from collections import MutableMapping
import logging
import shelve

from errbot import PY2

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
        log.info('Init storage of %s' % self.__class__.__name__)
        self.store = None

    def open_storage(self, storage_plugin, namespace):
        if hasattr(self, 'store') and self.store is not None:
            raise StoreAlreadyOpenError("Storage appears to be opened already")
        log.debug("Opening storage %s" % namespace)
        self.store = storage_plugin.open(namespace)

    def close_storage(self):
        if not hasattr(self, 'store') or self.store is None:
            raise StoreNotOpenError("Storage does not appear to have been opened yet")
        self.store.close()
        self.store = None
        log.debug('Closed store of %s' % self.__class__.__name__)

    # those are the minimal things to behave like a dictionary with the UserDict.DictMixin
    def __getitem__(self, key):
        return self.store.get(key)

    def __setitem__(self, key, item):
        return self.store.set(key, item)

    def __delitem__(self, key):
        return self.store.remove(key)

    def keys(self):
        keys = self.store.keys()
        if PY2:
            keys = [key.decode('utf-8') for key in keys]
        return keys

    def __len__(self):
        return self.store.len()

    def __iter__(self):
        for i in self.store.keys():
            yield i

    def __contains__(self, x):
        try:
            self.store.get(x)
            return True
        except KeyError:
            return False
