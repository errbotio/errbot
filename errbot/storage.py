from collections import MutableMapping
import logging
import shelve

from errbot import PY2


class StoreMixin(MutableMapping):
    """
     This class handle the basic needs of bot plugins and core like loading, unloading and creating a storage
    """

    def remove_superfluous_file_extension(self, path):
        """
         look for .db.db file and move it to .db
        """
        import os
        if os.path.isfile(path + '.db.db'):
            logging.info("Moving file {0}.db.db to {0}.db".format(path))
            os.rename(path + '.db.db', path + '.db')

    def open_storage(self, path):
        logging.info("Try to open db file %s" % path + '.db')
        self.remove_superfluous_file_extension(path)
        self.shelf = shelve.DbfilenameShelf(path, protocol=2)
        logging.debug('Opened shelf of %s' % self.__class__.__name__)

    def close_storage(self):
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
