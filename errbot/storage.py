from collections import MutableMapping
import logging
import shelve

from errbot import PY2


class StoreMixin(MutableMapping):
    """
     This class handle the basic needs of bot plugins and core like loading, unloading and creating a storage
    """

    def open_storage(self, path):
        logging.info("Try to open db file %s" % path)
        self.shelf = shelve.DbfilenameShelf(path, protocol=2)
        logging.debug('Opened shelf of %s' % self.__class__.__name__)

    def close_storage(self):
        if not hasattr(self, 'shelf'):
            # One possible cause for this is a plugin's activate method triggering an exception
            logging.debug("Cannot close storage of %s because the shelf doesn't exist." % self.__class__.__name__)
            return
        self.shelf.close()
        logging.debug('Closed shelf of %s' % self.__class__.__name__)

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
