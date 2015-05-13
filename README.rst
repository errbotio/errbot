
.. image:: https://travis-ci.org/gbin/err.png?branch=master
   :target: https://travis-ci.org/gbin/err/

.. image:: https://pypip.in/version/err/badge.png?style=flat
   :target: https://pypi.python.org/pypi/err
   :alt: Latest Version

.. image:: https://pypip.in/download/err/badge.png?style=flat
   :target: https://pypi.python.org/pypi/err
   :alt: Downloads

.. image:: https://pypip.in/py_versions/err/badge.png?style=flat
   :target: https://pypi.python.org/pypi/err
   :alt: Python Version

.. image:: https://pypip.in/license/err/badge.png?style=flat
   :target: https://pypi.python.org/pypi/err
   :alt: License

|
|

.. image:: http://gbin.github.io/err/_static/err_speech.png
   :target: http://errbot.net


Err - the pluggable chatbot
===========================

Err is a plugin based chatbot designed to be easily deployable, extensible and
maintainable. It allows you to start scripts interactively from your chatrooms
for any reason: random humour, starting a build, monitoring commits, triggering
alerts... The possibilities are endless.

It is written and extensible in Python, and, where possible, uses external
libraries instead of reinventing the wheel.

Err is available as open source software under the GPL3 license.

Community behind the project
----------------------------

Err has a `google plus community`_, please feel free to mention it with +err if
you need support, have any questions or wish to share some of your creations. If
you have a bug to report or wish to request a feature, please log these on it's
github_ page.

We strongly encourage you to share your creations. The only thing you have to do
to make your new plugin available to Err installations is to provide a Git url pointing to it.
Or, if you feel your new feature could fit as a part of an existing
plugin, please feel free to open a pull request for it on github_.

Features
--------

Chatting server support:

- XMPP: Tested with Google Talk, Hipchat_, Openfire_ and Jabber but should be compatible with any standard XMPP server
- CampFire_
- TOX_ (Peer to peer encrypted network)
- IRC

Main features:

- Powerful plugin architecture: Bot admins can install/uninstall/update/enable/disable plugins dynamically just by chatting with the bot
- Multi User Chatroom (MUC) support
- Webhook callbacks
- Advanced security/access control features (see below)

Included:

- A !help command that dynamically generates documentation for commands using the docstrings in the plugin source code
- A per-user command history system where users can recall previous commands
- The ability to proxy and route one-to-one messages to MUC so it can enable simpler XMPP notifiers to be MUC compatible (for example the Jira XMPP notifier)
- Local text and graphical consoles for testing and development

Administration and Security:

- Can be setup to a restricted list of people have administrative rights
- Fine-grained access controls may be defined which allow all or just specific commands to be limited to specific users and/or rooms
- Plugins may be hosted publicly or privately and dynamically installed (by admins) via their Git url
- Plugins can be configured directly from chat (no need to change setup files for every plugin)
- Configs can be exported and imported again with two commands (!export and !import respectively)
- Technical logs can be logged to file and inspected from the chat or optionally be `logged to Sentry`_

An extensive framework for writing custom plugins:

- Writing new plugins has a really low learning curve (see below)
- Graphical and text development consoles allow for fast development roundtrips
- Plugins get out of the box support for subcommands
- We provide an automatic persistence store per plugin
- There's really simple webhooks integration
- polling support for plugins
- custom configuration support per plugin
- end to end test backend for plugins
- templating framework for html responses

.. _Hipchat: http://www.hipchat.org/
.. _Openfire: http://www.igniterealtime.org/projects/openfire/
.. _jabberbot: http://thp.io/2007/python-jabberbot/
.. _yapsy: http://yapsy.sourceforge.net/
.. _jinja2: http://jinja.pocoo.org/
.. _bottle: http://bottlepy.org/
.. _rocket: https://pypi.python.org/pypi/rocket
.. _sleekxmpp: http://sleekxmpp.com/
.. _irc: https://pypi.python.org/pypi/irc/
.. _campfire: https://campfirenow.com/
.. _TOX: https://tox.im/
.. _`google plus community`: https://plus.google.com/b/101905029512356212669/communities/117050256560830486288
.. _github: http://github.com/gbin/err/
.. _`logged to Sentry`: https://github.com/gbin/err/wiki/Logging-with-Sentry

Prerequisites
-------------

Err runs under Python 3.3+ and Python 2.7 on Linux, Windows and Mac.

You need to have registered a user for the bot to use on the XMPP or IRC server that you wish to run Err on. A lot of plugins use multi user chatrooms (MUC) as well, so it is recommended (but not required) to have a least one MUC for Err to use as well.

Installation
------------

Err may be installed directly from PyPi using pip (easy_install works too) by issuing::

    pip install err

Or if you wish to try out the latest, bleeding edge version::

    pip install https://github.com/gbin/err/archive/master.zip

However, in these cases, installing into a dedicated `virtualenv`_ is recommended.

On some distributions, Err is available as a package via your usual package manager.
In these cases, it is generally recommended to use your distribution's package instead
of installing from PyPi.

**Extra dependencies**

requirements.txt lists only the bare minimum list of dependencies needed to run Err.
Depending on the backend you choose, additional requirements need to be installed.

For the XMPP based backends you must also install::

    sleekxmpp
    pyasn1
    pyasn1-modules
    dnspython3  # dnspython for Python 2.7

For the TOX backend, you must install::

    PyTox

For the IRC backend, you must install::

    irc

**Configuration**

After installing Err, you must create a data directory somewhere on your system where
config and data may be stored. Find the installation directory of Err, then copy the
file <install_directory>/errbot/config-template.py to your data directory as config.py

(If you installed Err via pip, the installation directory will most likely be
/usr/lib64/python<python_version_number>/site-packages/errbot)

Read the documentation within this file and edit the values as needed so the bot can
connect to your chosen XMPP or IRC server.

**Starting the daemon**

The first time you start Err, it is recommended to run it in foreground mode. This can
be done with::

    <path_to_install_directory>/scripts/err.py

In many cases, just typing err.py will be enough as it is generally added to the PATH
automatically. Please pass -h or --help to err.py to get a list of supported parameters.
Depending on your situation, you may need to pass --config or --backend when starting
Err.

If all that worked, you can now use the -d (or --daemon) parameter to run it in a
detached mode::

    <path_to_install_directory>/scripts/err.py --daemon

If you are going to run your bot all the time then using some process control system
such as `supervisor`_ is highly recommended. Installing and configuring such a system
is outside the scope of this document however.

**Hacking on Err's code directly**

It's important to know that as of version 2.0, Err is written for Python 3. In order
to run under Python 2.7 the code is run through 3to2 at install time. This means that
while it is possible to run Err under Python 3.3+ directly from a source checkout, it
is not possible to do so with Python 2.7. If you wish to develop or test with Err's
code under 2.7, you must run::

    python setup.py install

Alternatively, you can also look into the --editable parameter of pip install.

.. _virtualenv: https://pypi.python.org/pypi/virtualenv
.. _supervisor: http://supervisord.org/

Interacting with the Bot
------------------------

After starting Err, you should add the bot to your buddy list if you haven't already.
You can now send commands directly to the bot, or issue commands in a chatroom that
the bot has also joined.

To get a list of all available commands, you can issue::

    !help full

If you just wish to know more about a specific command you can issue::

    !help command

**Managing plugins**

To get a list of public plugin repos you can issue::

    !repos

To install a plugin from this list, issue::

    !repos install <name of plugin>

You can always uninstall a plugin again with::

    !repos uninstall <plugin>

You will probably want to update your plugins periodically. This can be done with::

    !repos update all

Note: Please pay attention when you install a plugin, it may have additional
dependencies. If the plugin contains a requirements.txt then Err wil automatically
check them and warn you when you are missing dependencies.

Writing plugins
---------------

Writing your own plugins is extremely simple. As an example, this is all it takes
to create a "Hello, world!" plugin for Err::

    from errbot import BotPlugin, botcmd

    class Hello(BotPlugin):
        """Example 'Hello, world!' plugin for Err"""

        @botcmd
        def hello(self, msg, args):
            """Return the phrase "Hello, world!" to you"""
            return "Hello, world!"

This plugin will create the command "!hello" which, when issued, returns "Hello, world!"
to you. For more info on everything you can do with plugins, see the
`plugin development guide <http://errbot.net/user_guide/plugin_development/>`_.



.. image:: https://badges.gitter.im/Join%20Chat.svg
   :alt: Join the chat at https://gitter.im/gbin/err
   :target: https://gitter.im/gbin/err?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge