.. image:: https://errbot.readthedocs.org/en/latest/_static/err_speech.png
   :target: http://errbot.io

|

.. image:: https://img.shields.io/travis/errbotio/errbot/master.svg
   :target: https://travis-ci.org/errbotio/errbot/

.. image:: https://img.shields.io/pypi/v/errbot.svg
   :target: https://pypi.python.org/pypi/errbot
   :alt: Latest Version

.. image:: https://img.shields.io/pypi/dm/errbot.svg
   :target: https://pypi.python.org/pypi/errbot
   :alt: Downloads

.. image:: https://img.shields.io/badge/License-GPLv3-green.svg
   :target: https://pypi.python.org/pypi/errbot
   :alt: License

.. image:: https://img.shields.io/badge/gitter-join%20chat%20%E2%86%92-brightgreen.svg
   :target: https://gitter.im/errbotio/errbot?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge
   :alt: Join the chat at https://gitter.im/errbotio/errbot

|

.. image:: https://graphs.waffle.io/errbotio/errbot/throughput.svg
   :target: https://waffle.io/errbotio/errbot/
   :alt: 'Throughput Graph'


Errbot
======

Errbot is a chatbot. It allows you to start scripts interactively from your chatrooms
for any reason: random humour, chatops, starting a build, monitoring commits, triggering
alerts...

It is written and easily extensible in Python.

Errbot is available as open source software and released under the GPL v3 license.


Features
--------

**Chat servers support**

- `Slack support <https://slack.com/>`_ (built-in)
- `Hipchat support <http://www.hipchat.com/>`_ (built-in)
- `Telegram support <https://www.telegram.org/>`_ (built-in)
- `XMPP support <http://xmpp.org>`_ (built-in support)
- IRC support (built-in)
- `Gitter support <https://gitter.im/>`_ (Follow `gitter instructions <https://github.com/errbotio/err-backend-gitter>`_ to install it)
- `CampFire <https://campfirenow.com/>`_ (Follow `campfire instructions <https://github.com/errbotio/err-backend-campfire>`_ to install it)
- `TOX <https://tox.im/>`_ (Follow the `tox instructions <https://github.com/errbotio/err-backend-tox>`_ to install it)
- `Skype <https://www.skype.com/>`_ (Follow the `skype instructions <https://github.com/errbotio/errbot-backend-skype>`_ to install it)

**Administration**

After the initial installation and security setup, Err can be administered by just chatting to the bot.

- install/uninstall/update/enable/disable private or public plugins hosted on git
- plugins can be configured from chat
- direct the bot to join/leave Multi User Chatrooms (MUC)
- Security: ACL control feature (admin/user rights per command)
- backup: an integrated command !backup creates a full export of persisted data.
- logs: can be inspected from chat or streamed to Sentry.

**Developer features**

- Presetup storage for every plugin i.e. ``self['foo'] = 'bar'`` persists the value.
- Conversation flows to track conversation states from users.
- Webhook callbacks support
- supports `markdown extras <https://pythonhosted.org/Markdown/extensions/extra.html>`_ formatting with tables, embedded images, links etc.
- configuration helper to allow your plugin to be configured by chat
- Graphical and text development/debug consoles
- Self-documenting: your docstrings becomes help automatically
- subcommands and various arg parsing options are available (re, command line type)
- polling support: your can setup a plugin to periodically do something
- end to end test backend
- card rendering under Slack and Hipchat.

Community and support
---------------------

If you have a question or want to share your latest plugin creation: feel free to join the chat at `errbotio/errbot on Gitter <https://gitter.im/errbotio/errbot>`_. Errbot has also a `google plus community <https://plus.google.com/b/101905029512356212669/communities/117050256560830486288>`_. You can ping us on Twitter with the hashtag ``#errbot``. 
If you have a bug to report or wish to request a feature, please log them on our `github project page <https://github.com/errbotio/errbot/issues>`_.

Contributions
-------------

Feel free to fork and propose changes on `github <https://www.github.com/errbotio/errbot>`_

Prerequisites
-------------

Errbot runs under Python 3.3+ and Python 2.7 on Linux, Windows and Mac. For some chatting systems you'll need a key or a login for your bot to access it.

Installation
------------

If you can, we recommend to setup a `virtualenv <https://pypi.python.org/pypi/virtualenv>`_.

Errbot may be installed directly from PyPi using pip by issuing:

.. code:: bash

    pip install errbot

Or if you wish to try out the latest, bleeding edge version:

.. code:: bash

    pip install https://github.com/errbotio/errbot/archive/master.zip


**Extra dependencies**

setup.py only installs the bare minimum dependencies needed to run Errbot.
Depending on the backend you choose, additional requirements need to be installed.

+------------+------------------------------------+
| Backend    | Extra dependencies                 |
+============+====================================+
| Slack      | - ``slackclient``                  |
+------------+------------------------------------+
| XMPP       | - ``sleekxmpp``                    |
|            | - ``pyasn1``                       |
|            | - ``pyasn1-modules``               |
|            | - ``dnspython3`` (py3)             |
|            | - ``dnspython``  (py2)             |
+------------+------------------------------------+
| Hipchat    | XMPP + ``hypchat``                 |
+------------+------------------------------------+
| irc        | - ``irc``                          |
+------------+------------------------------------+
| external   | See their ``requirements.txt``     |
+------------+------------------------------------+

**Configuration**

After installing Errbot, you must create a data directory somewhere on your system where
config and data may be stored. Then you'll need a `config.py` file.

You create a template of the file with:

.. code:: python

    python -c "import errbot;import os;import shutil;shutil.copyfile(os.path.dirname(errbot.__file__) + os.path.sep + 'config-template.py', 'config.py')"

Or you can download it directly from github from `config.py <https://raw.githubusercontent.com/errbotio/errbot/master/errbot/config-template.py>`_.

Read the documentation within this file and edit the values as needed so the bot can
connect to your chosen backend (XMPP, Hipchat, Slack ...) server.

**Starting the daemon**

The first time you start Errbot, it is recommended to run it in foreground mode. This can
be done with:

.. code:: bash

    errbot

In many cases, just using ``errbot`` will be enough as it is generally added to the ``$PATH``
automatically. Please pass -h or --help to ``errbot`` to get a list of supported parameters.
Depending on your situation, you may need to pass --config or --backend when starting
Errbot.

If all that worked, you can now use the -d (or --daemon) parameter to run it in a
detached mode:

.. code:: bash

    errbot --daemon

**Hacking on Errbot's code directly**

It's important to know that Errbot is written for Python 3 but can run under 2.7. In order
to run it under Python 2.7 the code is run through 3to2 at install time. This means that
while it is possible to run Errbot under Python 3.3+ directly from a source checkout, it
is not possible to do so with Python 2.7. If you wish to develop or test with Errbot's
code under 2.7, you must run:

.. code:: bash

    python setup.py develop

If you want to test your bot instance without havign to connect to a chat service, you can run it in text mode with:

.. code:: bash

   errbot -T
   
Or in graphical mode (you'll need to install the dependency pyside for that):

.. code:: bash

   errbot -G

Interacting with the Bot
------------------------

After starting Errbot, you should add the bot to your buddy list if you haven't already.
You can now send commands directly to the bot, or issue commands in a chatroom that
the bot has also joined.

To get a list of all available commands, you can issue:

.. code:: bash

    !help full

If you just wish to know more about a specific command you can issue:

.. code:: bash

    !help command

**Managing plugins**

To get a list of public plugin repos you can issue:

.. code:: bash

    !repos

To install a plugin from this list, issue:

.. code:: bash

    !repos install <name of plugin>

You can always uninstall a plugin again with:

.. code:: bash

    !repos uninstall <plugin>

You will probably want to update your plugins periodically. This can be done with:

.. code:: bash

    !repos update all

Note: Please pay attention when you install a plugin, it may have additional
dependencies. If the plugin contains a requirements.txt then Errbot will automatically
check them and warn you when you are missing dependencies.

Writing plugins
---------------

Writing your own plugins is extremely simple. As an example, this is all it takes
to create a "Hello, world!" plugin for Errbot:

.. code:: python

   from errbot import BotPlugin, botcmd
   
    class Hello(BotPlugin):
        """Example 'Hello, world!' plugin for Errbot"""
   
        @botcmd
        def hello(self, msg, args):
            """Return the phrase "Hello, world!" to you"""
            return "Hello, world!"

This plugin will create the command "!hello" which, when issued, returns "Hello, world!"
to you. For more info on everything you can do with plugins, see the
`plugin development guide <http://errbot.io/user_guide/plugin_development/>`_.
