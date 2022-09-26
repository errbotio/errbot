Backend-specifics
========================================================================

Errbot uses external libraries for most backends, which may offer additional
functionality not exposed by Errbot in a generic, backend-agnostic fashion.

It is possible to access the underlying client used by the backend you are
using in order to provide functionality that isn't otherwise available.
Additionally, interacting directly with the bot internals gives you the freedom
to control Errbot in highly specific ways that may not be officially supported.

.. warning::

    The following instructions describe how to interface directly with the underlying bot object and clients of backends.
    We offer no guarantees that these internal APIs are stable or that a given backend will continue to use a given client in the future.
    The following information is provided **as-is** without any official support.
    We can give **no** guarantees about API stability on the topics described below.


Getting to the bot object
------------------------------------------------------------------------

From within a plugin, you may access `self._bot` in order to get to the instance of the currently running bot class.
For example, with the Telegram backend this would be an instance of :class:`~errbot.backends.telegram.TelegramBackend`:

.. code-block:: python

    >>> type(self._bot)
    <class 'errbot.backends.TelegramBackend'>

To find out what methods each bot backend has, you can take a look at the documentation of the various backends in the :mod:`errbot.backends` package.

Plugins may use the `self._bot` object to offer tailored, backend-specific functionality on specific backends.
To determine which backend is being used, a plugin can inspect the `self._bot.mode` property.
The following table lists all the values for `mode` for the official backends:

============================================  ==========
Backend                                       Mode value
============================================  ==========
:class:`~errbot.backends.irc`                 irc
:class:`~errbot.backends.slackv3`             slackv3
:class:`~errbot.backends.telegram_messenger`  telegram
:class:`~errbot.backends.test`                test
:class:`~errbot.backends.text`                text
:class:`~errbot.backends.xmpp`                xmpp
============================================  ==========

Here's an example of using a backend-specific feature. In Slack, emoji reactions can be added to messages the bot
receives using the `add_reaction` and `remove_reaction` methods. For example, you could add an hourglass to messages
that will take a long time to reply fully to.

.. code-block:: python

    from errbot import BotPlugin, botcmd

    class PluginExample(BotPlugin):
        @botcmd
        def longcompute(self, mess, args):
            if self._bot.mode == "slack":
                self._bot.add_reaction(mess, "hourglass")
            else:
                yield "Finding the answer..."

            time.sleep(10)

            yield "The answer is: 42"
            if self._bot.mode == "slack":
                self._bot.remove_reaction(mess, "hourglass")


Getting to the underlying client library
------------------------------------------------------------------------

Most of the backends use a third-party library in order to connect to their respective network.
These libraries often support additional features which Errbot doesn't expose in a generic
way so you may wish to make use of these in order to access advanced functionality.

Backends set their own attribute(s) to point to the underlying libraries' client instance(s).
The following table lists these attributes for the official backends, along with the library used by the backend:


============================================  ===============================  ====================================================
Backend                                       Library                          Attribute(s)
============================================  ===============================  ====================================================
:class:`~errbot.backends.irc`                 `irc`_                           ``self._bot.conn`` ``self._bot.conn.connection``
:class:`~errbot.backends.slackv3`             `slacksdk`_, `_slackeventsapi`_  ``self._bot.slack_sdk`` ``self._bot.slackeventsapi``
:class:`~errbot.backends.telegram_messenger`  `telegram-python-bot`_           ``self._bot.telegram``
:class:`~errbot.backends.xmpp`                `slixmpp`_                       ``self._bot.conn``
============================================  ===============================  ====================================================

.. _irc: https://pypi.org/project/irc/
.. _`telegram-python-bot`: https://pypi.org/project/python-telegram-bot
.. _slacksdk: https://slack.dev/python-slack-sdk/
.. _slackeventsapi: https://github.com/slackapi/python-slack-events-api
.. _slixmpp: https://pypi.org/project/slixmpp


Slack v3 Backend
========================================================================

.. Note::

    Slack provides advanced features above and beyond simple text messaging in the form of Slack Applications and Workflows.  These features cross into the domain of application development and use
    specialised events and data structures.  Support for these features is asked for by plugin developers, and for good reasons as their ChatOps requirements grow.  It is at this level of sophistication
    that errbot's framework becomes a hinderance rather than a help because errbot's design goal is to be backend agnostic to ensure portability between chat service providers.  For advanced use cases
    as mentioned early, it is strongly recommended to use (Slack's Bolt Application Framework)[https://slack.dev/bolt-python/concepts] to write complex application/workflows in Slack.

The Slack v3 backend provides some advanced formatting through direct access to the underlying python module functionality.
Below are examples of how to make use of Slack specific features.

Slack attachments and block
------------------------------------------------------------------------

It is possible to pass additional payload data along with the message.  When this extra information is present, the slack python module will process it.
The below example shows how to send attachments (deprecated) or blocks for advanced text message formatting.

.. code-block:: python

    from slack_sdk.models.blocks import SectionBlock, TextObject
    from errbot.backends.base import Message

    @botcmd
    def hello(self, msg, args):
        """Say hello to someone"""
        msg.body = "Using the sent message to shorten the code example"
        msg.extras['attachments'] = [{
            'color': '5F4B48',
            'fallback': 'Help text for: Bot plugin',
            'footer': 'For these commands: `help Bot`',
            'text': 'General commands to do with the ChatOps bot',
            'title': 'Bot'
        },{
            'color': 'FAF5F5',
            'fallback': 'Help text for: Example plugin',
            'footer': 'For these commands: `help Example`',
            'text': 'This is a very basic plugin to try out your new installation and get you started.\n Feel free to tweak me to experiment with Errbot.\n You can find me in your init directory in the subdirectory plugins.',
            'title': 'Example'
        }]

        self._bot.send_message(msg)


        # Example with the blocks SDK
        msg = Message()
        msg.extras['blocks'] = [
            SectionBlock(
                text=TextObject(
                    text="Welcome to Slack! :wave: We're so glad you're here. :blush:\n\n",
                    type="mrkdwn"
                )
            ).to_dict()
        ]
        self._bot.send_message(msg)
