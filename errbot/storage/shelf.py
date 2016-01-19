import logging
from typing import Any, Mapping
import shelve
import os

from errbot.storage.base import StorageBase, StoragePluginBase

log = logging.getLogger('errbot.storage.shelf')


class ShelfStorage(StorageBase):
    def __init__(self, path):
        log.debug('Open shelf storage %s' % path)
        self.shelf = shelve.DbfilenameShelf(path, protocol=2)

    def get(self, key: str) -> Any:
        return self.shelf[key]

    def remove(self, key: str):
        if key not in self.shelf:
            raise KeyError("%s doesn't exist." % key)
        del self.root[key]

    def set(self, key: str, value: Any) -> None:
        self.shelf[key] = value

    def len(self):
        return len(self.shelf)

    def close(self) -> None:
        self.shelf.close()
        self.shelf = None
        log.debug('Closed shelf of %s' % self.__class__.__name__)


class ShelfStoragePlugin(StoragePluginBase):
    def __init__(self, bot_config):
        super().__init__(bot_config)
        if 'basedir' not in self._storage_config:
            self._storage_config['basedir'] = d

    def open(self, namespace: str) -> StorageBase:
        config = self._storage_config
        return ShelfStorage(os.path.join(config['basedir'], namespace + '.db'))
