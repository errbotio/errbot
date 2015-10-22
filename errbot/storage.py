from collections import MutableMapping
import logging
import shelve
import json

from .utils import PY2
log = logging.getLogger(__name__)

try:
    import redis
except ImportError:
    log.debug("Unable to load `redis`.")
    redis = None


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


class RedisStore():
    """
    A storage mechanism backed by Redis, namespaced per-plugin by a key.

    """
    def __init__(self, redis_client, key_prefix):
        """
        Args:
            redis_client (redis.Redis)
            key_prefix (str):

        """
        self.client = redis_client
        self.key_prefix = key_prefix

    @classmethod
    def for_plugin(cls, redis_client, plugin):
        """
        Instantiate a `RedisStore` instance for use by a `BotPlugin` instance.

        """
        return cls(redis_client, "%s::" % plugin.__class__.__name__)

    def get(self, key):
        """
        Args:
            key (str)

        Returns:
            object. deserialized from str by json.loads

        """
        pkey = self.key_prefix + key
        got = self.client.get(pkey)

        if not got:
            return None

        return json.loads(self._py3_compat_decode(got))

    def set(self, key, val, ttl=None):
        """
        Args:
            key (str)
            val (object): must be jsonable

        Kwargs:
            ttl (int): in seconds

        Returns:
            bool. if set

        """
        pkey = self.key_prefix + key
        try:
            ttl and int(ttl)
        except Exception:
            raise ValueError("ttl must be int-like or None")

        return self.client.set(pkey, json.dumps(val), ex=ttl)

    def _py3_compat_decode(self, item_out_of_redis):
        """Py3 redis returns bytes, so we must handle the decode."""
        if not isinstance(item_out_of_redis, str):
            return item_out_of_redis.decode('utf-8')
        return item_out_of_redis


def get_redis_client(host, port, db):
    """
    If we can import redis, return a client. If not, return None.

    """
    if not redis:
        log.info("Can't use redis -- we don't have `redis` installed")
        return None

    return redis.Redis(host=host, port=port, db=db)
