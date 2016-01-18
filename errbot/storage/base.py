from abc import abstractmethod
from typing import Mapping, Any


class StorageBase(object):
    """
    Contract to implemement a storage.
    """
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        Atomically set the key to the given value.
        The caller of set will protect against set on non open.

        :param key: string as key
        :param value: pickalable python object
        """
        pass

    @abstractmethod
    def get(self, key: str) -> Any:
        """
        Get the value stored for key. Raises KeyError if the key doesn't exist.
        The caller of get will protect against get on non open.

        :param key: the key
        :return: the value
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Sync and close the storage.
        The caller of close will protect against close on non open and double close.
        """
        pass


class StoragePluginBase(object):
    """
    Base to implement a storage plugin.
    This is a factory for the namespaces.
    """
    @abstractmethod
    def open(self, namespace: str, config: Mapping[str, Any]) -> StorageBase:
        """
        Open the storage with the given namespace (core, or plugin name) and config.
        The caller of open will protect against double opens.

        :param namespace: a namespace to isolate the plugin storages.
        :param config: the implementation dependent configuration.
        :return:
        """
        pass
