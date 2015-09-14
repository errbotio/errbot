Persistence
===========

Persistence describes the ability for the plugins to persist data even
if Errbot is restarted.

How to use it
-------------

You plugin *is* the store, simply use self as a dictionary.

Here is a simple example storing are retreiving value from the store.

.. code-block:: python

    from errbot import BotPlugin, botcmd

    class PluginExample(BotPlugin):
        @botcmd
        def remember(self, msg, args):
            self['TODO'] = args

        @botcmd
        def recall(self, msg, args):
            return self['TODO']

Caveats
-------

The storing occurs when you *assign the key*. So for example:

.. code-block:: python

    # THIS WON'T WORK
    d = {}
    self['FOO'] = d
    d['subkey'] = 'NONONONONONO'

You need to do that instead:

.. code-block:: python

    # THIS WORKS
    d = {}
    self['FOO'] = d

    # later ...
    d['subkey'] = 'NONONONONONO'
    self['FOO'] = d  # restore the full key if something changed in memory.
