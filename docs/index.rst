Errbot
======

*Errbot is a chatbot, a daemon that connects to your favorite chat service and brings
your tools into the conversation.*

The goal of the project is to make it easy for you to write your own plugins so you
can make it do whatever you want: a deployment, retrieving some information online,
trigger a tool via an API, troll a co-worker,...

Errbot is being used in a lot of different contexts: chatops (tools for devops), chatroom engagement,
home security, socials platform (such as Slack, Discord, IRC), etc.

Screenshots
-----------

.. image:: _static/screenshots/thumb_slack.png
   :target: _static/screenshots/slack.png
   :alt: Showing output of the built-in help command in Slack

.. image:: _static/screenshots/thumb_telegram.png
   :target: _static/screenshots/telegram.png
   :alt: Errbot running on Telegram showing the !help command

Simple to build upon
--------------------

Extending Errbot and adding your own commands can be done by creating a plugin, which
is simply a class derived from :class:`~errbot.botplugin.BotPlugin`.
The docstrings will be automatically reused by the :ref:`\!help <builtin_help_function>`
command::

    from errbot import BotPlugin, botcmd

    class HelloWorld(BotPlugin):
        """Example 'Hello, world!' plugin for Errbot."""

        @botcmd
        def hello(self, msg, args):
            """Say hello to the world."""
            return "Hello, world!"

Once you said "!hello" in your chatroom, the bot will answer "Hello, world!".

Batteries included
------------------

We aim to give you all the tools you need to build a customized bot safely, without
having to worry about basic functionality. As such, Errbot comes with a wealth of
features out of the box.

.. toctree::
  :maxdepth: 2

  features


Sharing
-------

One of the main goals of Errbot is to make it easy to share your plugin with others as well.

Errbot features a built-in *repositories command* (`!repos`) which can be used to
install, uninstall and update plugins made available by the community. Making your
plugin available through this command only requires you to publish it as a publicly
available Git repository.

You may also discover plugins from the community on our `plugin list`_ that we update from plugins found on github.


Community
---------

You can interact directly with the community online from the "Open Chat"
button at the bottom of this page. Don't be shy and feel free to ask any question
there, we are more than happy to help you.

If you think you hit a bug or the documentation is not clear enough,
you can `open an issue`_ or even better, open a pull request.


User guide
----------

.. toctree::
  :maxdepth: 2

  user_guide/setup
  user_guide/administration
  user_guide/plugin_development/index
  user_guide/flow_development/index
  user_guide/backend_development/index
  user_guide/storage_development/index
  user_guide/sentry


Getting involved
----------------

.. toctree::
  :maxdepth: 3

  contributing


API documentation
-----------------

.. toctree::
  :maxdepth: 3

  errbot


Release history
---------------

.. toctree::
  :maxdepth: 2

  changes


License
-------

Errbot is free software, available under the GPL-3 license. Please refer to the
:download:`full license text <gpl-3.0.txt>` for more details.

.. _`GitHub page`: http://github.com/errbotio/errbot/
.. _`plugin list`: https://github.com/errbotio/errbot/wiki
.. _`open an issue`: https://github.com/errbotio/errbot/issues
