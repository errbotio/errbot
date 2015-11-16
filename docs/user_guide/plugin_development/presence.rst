Presence
========

Presence describes the concept of a person's availability state, such as
*online* or *away*, possibly with an optional message.


Callbacks for presence changes
------------------------------

Plugins may override :meth:`~errbot.botplugin.BotPlugin.callback_presence`
in order to receive notifications of presence changes. You will receive
a :class:`~errbot.backends.base.Presence` object for every presence change
received by Errbot.

Here's an example which simply logs each presence change to the log
when it includes a status message:

.. code-block:: python

    from errbot import BotPlugin

    class PluginExample(BotPlugin):
        def callback_presence(self, presence):
            if presence.get_message() is not None:
                self.log.info(presence)

Change the presence/status of the bot
-------------------------------------

You can also, depending on the backend you use, change the current status of
the bot. This allows you to make a moody bot that leaves the room when it is
in a bad mood ;)


.. code-block:: python

    from errbot import BotPlugin, botcmd, ONLINE, AWAY

    class PluginExample(BotPlugin):
        @botcmd
        def grumpy(self, mess, args):
            self.change_presence(AWAY, 'I am tired of you all!')

        @botcmd
        def happy(self, mess, args):
            self.change_presence(ONLINE, 'I am back and so happy to see you!')


