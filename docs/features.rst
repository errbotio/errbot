Multiple server back-ends
^^^^^^^^^^^^^^^^^^^^^^^^^

Err has support for a number of different networks, and is architectured in a way
that makes it relatively easy to write new back-ends in order to support more.
Currently, the following networks are supported:

  * XMPP *(Any standards-compliant XMPP/Jabber server should work - Google Talk/Hangouts included)*
  * Hipchat_
  * IRC
  * Slack_
  * Telegram_
  * Tox_ (maintained seperately)
  * Gitter_ (maintained seperately)
  * CampFire_ (maintained seperately)

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
* Fine-grained access controls may be defined which allow all or just specific commands to be limited to specific users and/or rooms
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
* And a templating framework to display fancy HTML messages. Automatic conversion from HTML to plaintext when the backend doesn't support HTML means you don't have to make seperate text and HTML versions of your command output yourself


.. _Hipchat: https://www.hipchat.com/
.. _Campfire: https://campfirenow.com/
.. _jabberbot: http://thp.io/2007/python-jabberbot/
.. _Slack: http://slack.com/
.. _Tox: https://tox.im/
.. _Telegram: https://telegram.org/
.. _Gitter: http://gitter.im/
.. _yapsy: http://yapsy.sourceforge.net/
.. _jinja2: http://jinja.pocoo.org/
.. _bottle: http://bottlepy.org/
.. _rocket: https://pypi.python.org/pypi/rocket
.. _sleekxmpp: http://sleekxmpp.com/
.. _irc: https://pypi.python.org/pypi/irc/
.. _six: https://pypi.python.org/pypi/six/
.. _`logged to Sentry`: https://github.com/gbin/err/wiki/Logging-with-Sentry
