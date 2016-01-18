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

    def set(self, key: str, value: Any) -> None:
        self.shelf[key] = value

    def close(self) -> None:
        self.shelf.close()
        self.shelf = None
        log.debug('Closed shelf of %s' % self.__class__.__name__)


class ShelfStoragePlugin(StoragePluginBase):
    def open(self, namespace: str, config: Mapping[str, Any]) -> StorageBase:
        if 'basedir' not in config:
            raise Exception('no basedir specified in the shelfstorage config.')
        if 'compatibilitymode' in config and config['compatibilitymode']:
            # originally errbot stores plugins per dir.
            return ShelfStorage(os.path.join(config['basedir'], namespace, namespace))

        return ShelfStorage(os.path.join(config['basedir'], namespace))
