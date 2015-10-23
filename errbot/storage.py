from collections import MutableMapping
import logging
import shelve

from .utils import PY2
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
        log.info('Init shelf of %s' % self.__class__.__name__)
        self.shelf = None

    def open_storage(self, path):
        if hasattr(self, 'shelf') and self.shelf is not None:
            raise StoreAlreadyOpenError("Storage appears to be opened already")
        log.debug("Opening storage file %s" % path)
        self.shelf = shelve.DbfilenameShelf(path, protocol=2)
        log.info('Opened shelf of %s at %s' % (self.__class__.__name__, path))

    def close_storage(self):
        if not hasattr(self, 'shelf') or self.shelf is None:
            raise StoreNotOpenError("Storage does not appear to have been opened yet")
        self.shelf.close()
        self.shelf = None
        log.debug('Closed shelf of %s' % self.__class__.__name__)

    # those are the minimal things to behave like a dictionary with the UserDict.DictMixin
    def __getitem__(self, key):
        return self.shelf.__getitem__(key)

    def __setitem__(self, key, item):
        answer = self.shelf.__setitem__(key, item)
        self.shelf.sync()
        return answer

    def __delitem__(self, key):
        answer = self.shelf.__delitem__(key)
        self.shelf.sync()
        return answer

    def keys(self):
        keys = self.shelf.keys()
        if PY2:
            keys = [key.decode('utf-8') for key in keys]
        return keys

    def __len__(self):
        return len(self.shelf)

    def __iter__(self):
        for i in self.shelf:
            yield i

    def __contains__(self, x):
        return x in self.shelf

