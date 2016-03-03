[Advanced] Storage Plugin development
=====================================

A storage plugin is a glue code that tell Errbot how to store the persistent data the
plugins and the bot itself are producing.
Starting with Errbot 3.3.0, storage plugins can be developed out of the main repository.
This documentation is there to guide you making a new storage plugin so you can connect
Errbot to your favorite database.


Architecture
------------

Storage plugin are instanciated in 2 stages.

The first stage is similar to the normal bot plugins:

* Errbot scans errbot/storage and config.BOT_EXTRA_STORAGE_PLUGINS_DIR for .plug pointing
  to plugins implementing :class:`~errbot.storage.base.StoragePluginBase`
* Once the correct plugin from config.STORAGE is found, it is built with the bot config as its __init__ parameter.
* By calling super().__init__ on :class:`~errbot.storage.base.StoragePluginBase` it will populate self._storage_config
  from config.STORAGE_CONFIG. This configuration should contain the custom parameters needed by your plugin to be able
  to connect to your database/storage ie. url, port, path, credentials ... You need to document them clearly so your
  users can set config.STORAGE_CONFIG correctly.
* As you can see in StoragePluginBase, you just have to implement the open method there.

The second stage is the open itself:

* various parts of Errbot can need separate key/value storage, the open method has a namespace to track those.
  For example the internal BotPluginManager will open the namespace 'core' to store the botplugins and their config,
  the installed repos etc.
* open needs to return a :class:`~errbot.storage.base.StorageBase` which exposes the various actions the Errbot can
  call on the storage (set, get, ...).
* you don't need to track the lifecycle of the storage, it will be enforced externally
  (no double close, double open, get after close etc.).

Plugins are :class:`collections.MutableMapping` and uses :class:`~errbot.storage.StoreMixin` as an adapter from the
mapping accessors to the :class:`~errbot.storage.base.StorageBase` implementation.


Testing
-------

Those plugins are completely independent from Errbot itself, it should be easy to instanciate and test them externally.


Example
-------

You can have a look at the internal shelf implementation :class:`~errbot.storage.shelf.ShelfStorage`
