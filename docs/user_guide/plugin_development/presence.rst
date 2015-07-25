Presence
========

Presence describes the concept of a person's availability state, such as
*online* or *away*, possibly with an optional message.


Callbacks for presence changes
------------------------------

.. versionadded:: master
    This is not yet available in a public release.

Plugins may override :meth:`~errbot.botplugin.BotPlugin.callback_presence`
in order to receive notifications of presence changes. You will receive
a :class:`~errbot.backends.base.Presence` object for every presence change
received by Err.

Here's an example which simply logs each presence change to the log
when it includes a status message:

.. code-block:: python

    from errbot import BotPlugin

    class PluginExample(BotPlugin):
        def callback_presence(self, presence):
            if presence.get_message() is not None:
                self.log.info(presence)
