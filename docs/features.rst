Multiple server backends
^^^^^^^^^^^^^^^^^^^^^^^^

Errbot has support for a number of different networks and is architectured in a way
that makes it easy to write new backends in order to support more.
Currently, the following networks are supported:

  * XMPP *(Any standards-compliant XMPP/Jabber server should work - Google Talk/Hangouts included)*
  * Hipchat_
  * IRC
  * Slack_
  * Telegram_
  * `Bot Framework`_ (maintained `separately <https://github.com/vasilcovsky/errbot-backend-botframework>`__)
  * CampFire_ (maintained `separately <https://github.com/errbotio/err-backend-campfire>`__)
  * `Cisco Webex Teams`_ (maintained `separately <https://github.com/marksull/err-backend-cisco-webex-teams>`__)
  * Discord_ (maintained `separately <https://github.com/gbin/err-backend-discord>`__)
  * Gitter_ (maintained `separately <https://github.com/errbotio/err-backend-gitter>`__)
  * Mattermost_ (maintained `separately <https://github.com/Vaelor/errbot-mattermost-backend>`__)
  * Skype_ (maintained `separately <https://github.com/errbotio/errbot-backend-skype>`__)
  * Tox_ (maintained `separately <https://github.com/errbotio/err-backend-tox>`__)
  * VK_ (maintained `separately <https://github.com/Ax3Effect/errbot-vk>`__)
  * Zulip_ (maintained `separately <https://github.com/zulip/errbot-backend-zulip>`__)


Core features
^^^^^^^^^^^^^

* Multi User Chatroom (MUC) support
* A dynamic plugin architecture: Bot admins can install/uninstall/update/enable/disable plugins dynamically just by chatting with the bot
* Advanced security/access control features (see below)
* A `!help` command that dynamically generates documentation for commands using the docstrings in the plugin source code
* A per-user command history system where users can recall previous commands
* The ability to proxy and route one-to-one messages to MUC so it can enable simpler XMPP notifiers to be MUC compatible (for example the Jira XMPP notifier)


Built-in administration and security
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Can be setup so a restricted list of people have administrative rights
* Fine-grained :ref:`access controls <access_controls>` may be defined which allow all or just specific commands to be limited to specific users and/or rooms
* Plugins may be hosted publicly or privately and dynamically installed (by admins) via their Git url
* Plugins can be configured directly from chat (no need to change setup files for every plugin)
* Configs can be exported and imported again with two commands (!export and !import respectively)
* Technical logs can be logged to file, inspected from the chat or optionally
  :doc:`logged to Sentry <user_guide/sentry>`


Extensive plugin framework
^^^^^^^^^^^^^^^^^^^^^^^^^^

* Hooks and callbacks for various types of events, such as
  :func:`~errbot.botplugin.BotPlugin.callback_connect` for when the bot has connected
  or :func:`~errbot.botplugin.BotPlugin.callback_message` for when a message is received.
* Local text and graphical consoles for easy testing and development
* Plugins get out of the box support for subcommands
* We provide an automatic persistence store per plugin
* There's really simple webhooks integration
* As well as a polling framework for plugins
* An easy configuration framework
* A test backend for unittests for plugins which can make assertions about issued commands and their responses
* And a templating framework to display fancy HTML messages. Automatic conversion from HTML to plaintext when the backend doesn't support HTML means you don't have to make separate text and HTML versions of your command output yourself

.. _Bot Framework: https://botframework.com/
.. _Campfire: https://campfirenow.com/
.. _Cisco Webex Teams: https://www.webex.com/
.. _Discord: https://www.discordapp.com/
.. _Gitter: http://gitter.im/
.. _Hipchat: https://www.hipchat.com/
.. _Matrix: https://matrix.org/
.. _Mattermost: https://about.mattermost.com/
.. _Skype: http://www.skype.com/en/
.. _Slack: http://slack.com/
.. _Telegram: https://telegram.org/
.. _Tox: https://tox.im/
.. _VK: https://vk.com/
.. _Zulip: https://zulipchat.com/
.. _`logged to Sentry`: https://github.com/errbotio/errbot/wiki/Logging-with-Sentry
.. _irc: https://pypi.python.org/pypi/irc/
.. _jabberbot: http://thp.io/2007/python-jabberbot/
.. _jinja2: http://jinja.pocoo.org/
.. _six: https://pypi.python.org/pypi/six/
.. _slixmpp: https://slixmpp.readthedocs.io/
