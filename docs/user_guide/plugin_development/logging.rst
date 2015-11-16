Logging
-------

Logging information on what your plugin is doing can be a tremendous asset when managing
your bot in production, especially when something is going wrong.

Errbot uses the standard Python `logging <https://docs.python.org/3/library/logging.html>`_
library to log messages internally and provides a logger for your own plugins to use as well as `self.log`.
You can use this logger to log status messages to the log like this:

.. code-block:: python

    from errbot import BotPlugin

    class PluginExample(BotPlugin):
        def callback_message(self, message):
            self.log.info("I just received a message!")
