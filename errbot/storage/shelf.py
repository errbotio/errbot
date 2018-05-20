import logging
from typing import Any
import shelve
import os

import shutil

from errbot.storage.base import StorageBase, StoragePluginBase

log = logging.getLogger('errbot.storage.shelf')


class ShelfStorage(StorageBase):
    def __init__(self, path):
        log.debug('Open shelf storage %s', path)
        self.shelf = shelve.DbfilenameShelf(path, protocol=2)

    def get(self, key: str) -> Any:
        return self.shelf[key]

    def remove(self, key: str):
        if key not in self.shelf:
            raise KeyError(f"{key} doesn't exist.")
        del self.shelf[key]

    def set(self, key: str, value: Any) -> None:
        self.shelf[key] = value

    def len(self):
        return len(self.shelf)

    def keys(self):
        return self.shelf.keys()

    def close(self) -> None:
        self.shelf.close()
        self.shelf = None


class ShelfStoragePlugin(StoragePluginBase):
    def __init__(self, bot_config):
        super().__init__(bot_config)
        if 'basedir' not in self._storage_config:
            self._storage_config['basedir'] = bot_config.BOT_DATA_DIR

    def open(self, namespace: str) -> StorageBase:
        config = self._storage_config
        # Hack to port move old DBs to the new location.
        new_spot = os.path.join(config['basedir'], namespace + '.db')
        old_spot = os.path.join(config['basedir'], 'plugins', namespace + '.db')
        if os.path.isfile(old_spot):
            if os.path.isfile(new_spot):
                log.warning('You have an old v3 DB at %s and a duplicate new one at %s.', old_spot, new_spot)
                log.warning('You need to either remove the old one or move it in place of the new one manually.')
            else:
                log.info('Moving your old v3 DB from %s to %s.', old_spot, new_spot)
                shutil.move(old_spot, new_spot)

        return ShelfStorage(new_spot)
