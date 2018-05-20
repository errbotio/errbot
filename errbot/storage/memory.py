from typing import Any

from errbot.storage.base import StorageBase, StoragePluginBase

ROOTS = {}  # make a little bit of an emulated persistence.


class MemoryStorage(StorageBase):

    def __init__(self, namespace):
        self.namespace = namespace
        self.root = ROOTS.get(namespace, {})

    def get(self, key: str) -> Any:
        if key not in self.root:
            raise KeyError(f"{key} doesn't exist.")
        return self.root[key]

    def set(self, key: str, value: Any) -> None:
        self.root[key] = value

    def remove(self, key: str):
        if key not in self.root:
            raise KeyError(f"{key} doesn't exist.")
        del self.root[key]

    def len(self):
        return len(self.root)

    def keys(self):
        return self.root.keys()

    def close(self) -> None:
        ROOTS[self.namespace] = self.root


class MemoryStoragePlugin(StoragePluginBase):

    def open(self, namespace: str) -> StorageBase:
        return MemoryStorage(namespace)
