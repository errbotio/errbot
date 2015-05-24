Err - the pluggable chatbot
===========================

*Err is a GPL3-licensed chat-bot designed to be easily deployable, extensible
and maintainable. Our goal is to make it easy for you to write your own plugins
so you can make it do whatever you want.*

Simple to build upon
--------------------

Extending Err and adding your own commands can be done by creating a plugin, which
is merely a Python module containing a class derived from
:class:`~errbot.botplugin.BotPlugin`::

    from errbot import BotPlugin, botcmd

    class HelloWorld(BotPlugin):
        """Example 'Hello, world!' plugin for Err"""

        @botcmd
        def hello(self, msg, args):
            """Say hello to the world"""
            return "Hello, world!"

By default, Err looks at your docstrings to automatically document commands for the
built-in :ref:`\!help <builtin_help_function>` command. It will use the class' docstring as the description of
your plugin and use the method docstrings as documentation for the bot commands.

Batteries included
------------------

We aim to give you all the tools you need to build the bot you want, without
having to worry about basic functionality. As such, Err comes with a wealth of
features out of the box.

.. toctree::
  :maxdepth: 2

  features

Sharing
-------

One of the principal goals of Err is to make it easy to not only create your own
plugins with little effort, but to make it easy to share them with others as well.

Err features a built-in *repositories command* (`!repos`) which can be used to
install, uninstall and update plugins made available by the community. Making your
plugin available through this command only requires you to publish it as a publicly
available Git repository and letting us know the URL so we can add it.

Currently, we're also working on a web interface lightly inspired by Hubot's
`script catalog <http://hubot-script-catalog.herokuapp.com/>`_, which should make
this process even easier in the future.

Screenshots
-----------

.. raw:: html

    <div class="screenshots">
        <a href="_static/screenshots/help.png" class="fancybox" title="Showing output of the built-in help command">
            <img src="_static/screenshots/thumb_help.png" width="155" height="150" alt="Showing output of the built-in help command" />
        </a>
        <a href="_static/screenshots/quota.png" class="fancybox" title="Err running on HipChat, showing off a (businesss-specific) command to get and set the disk quotas for mail accounts">
            <img src="_static/screenshots/thumb_quota.png" width="268" height= "150" alt="Err running on HipChat, showing off a (businesss-specific) command to get and set the disk quotas for mail accounts" />
        </a>
        <a href="_static/screenshots/basecamp.png" class="fancybox" title="An older version of Err, running on Basecamp">
            <img src="_static/screenshots/thumb_basecamp.png" width="181" height= "150" alt="An older version of Err, running on Basecamp" />
        </a>
    </div>

Community
---------

Err has a `Google plus community`_, which is the best place to go for help and ask
questions, discuss anything related to Err as well as promote your own creations.
This is also the place where you will find announcements of new versions and other
news related to the project.

Getting involved
----------------

.. toctree::
  :maxdepth: 3

  contributing

User guide
----------

.. toctree::
  :maxdepth: 2

  user_guide/setup
  user_guide/interaction
  user_guide/plugin_development/index
  user_guide/sentry

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

Err is free software, available under the GPL-3 license. Please refer to the
:download:`full license text <gpl-3.0.txt>` for more details.

.. _`Google plus community`: https://plus.google.com/communities/117050256560830486288
.. _`GitHub page`: http://github.com/gbin/err/
