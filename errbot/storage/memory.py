from typing import Any, Mapping

from errbot.storage.base import StorageBase, StoragePluginBase

ROOTS = {}  # make a little bit of an emulated persistence.


class MemoryStorage(StorageBase):

    def __init__(self, namespace):
        self.namespace = namespace
        self.root = ROOTS.get(namespace, {})

    def get(self, key: str) -> Any:
        if key in self.root:
            return self.root[key]
        raise KeyError("%s doesn't exist." % key)

    def set(self, key: str, value: Any) -> None:
        self.root[key] = value

    def close(self) -> None:
        ROOTS[self.namespace] = self.root


class MemoryStoragePlugin(StoragePluginBase):

    def open(self, namespace: str) -> StorageBase:
        return MemoryStorage(namespace)
