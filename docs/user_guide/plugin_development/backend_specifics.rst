Backend-specifics
=================

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
-------------------------

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
:class:`~errbot.backends.slack`               slack
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
----------------------------------------

Most of the backends use a third-party library in order to connect to their respective network.
These libraries often support additional features which Errbot doesn't expose in a generic
way so you may wish to make use of these in order to access advanced functionality.

Backends set their own attribute(s) to point to the underlying libraries' client instance(s).
The following table lists these attributes for the official backends, along with the library used by the backend:


============================================  =========================  ================================================
Backend                                       Library                    Attribute(s)
============================================  =========================  ================================================
:class:`~errbot.backends.irc`                 `irc`_                     ``self._bot.conn`` ``self._bot.conn.connection``
:class:`~errbot.backends.slack`               `slackclient`_             ``self._bot.sc``
:class:`~errbot.backends.telegram_messenger`  `telegram-python-bot`_     ``self._bot.telegram``
:class:`~errbot.backends.xmpp`                `slixmpp`_                 ``self._bot.conn``
============================================  =========================  ================================================

.. _hypchat: https://pypi.org/project/hypchat/
.. _irc: https://pypi.org/project/irc/
.. _`telegram-python-bot`: https://pypi.org/project/python-telegram-bot
.. _slackclient: https://pypi.org/project/slackclient/
.. _slixmpp: https://pypi.org/project/slixmpp
