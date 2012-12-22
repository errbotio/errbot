import UserDict
import logging
from utils import utf8
import shelve

class StoreMixin(UserDict.DictMixin):
    """
     This class handle the basic needs of bot plugins and core like loading, unloading and creating a storage
    """

    def open_storage(self, path):
        self.shelf = shelve.DbfilenameShelf(path, protocol = 2)
        logging.debug('Opened shelf of %s' % self.__class__.__name__)

    def close_storage(self):
        self.shelf.close()
        logging.debug('Closed shelf of %s' % self.__class__.__name__)

    # those are the minimal things to behave like a dictionary with the UserDict.DictMixin
    def __getitem__(self, key):
        return self.shelf.__getitem__(utf8(key))

    def __setitem__(self, key, item):
        answer = self.shelf.__setitem__(utf8(key), item)
        self.shelf.sync()
        return answer

    def __delitem__(self, key):
        answer = self.shelf.__delitem__(utf8(key))
        self.shelf.sync()
        return answer

    def keys(self):
        keys = []
        for key in self.shelf.keys():
            if type(key) == str:
                keys.append(key.decode('utf-8'))
        return keys
