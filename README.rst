.. image:: http://gbin.github.com/err/images/err.png
    :align: right

.. image:: https://secure.travis-ci.org/gbin/err.png
    :target: https://travis-ci.org/gbin/err/

Err - the pluggable chatbot
===========================

Err is a plugin based chatbot designed to be easily deployable, extensible and maintainable.
It allows you to start scripts interactively from your chatrooms for any reason: random humour, starting a build, monitoring commits, triggering alerts ...

It is available as open source software under the GPL3 license.

Err is written and extensible in python, it's based on yapsy_ with an heavily adapted jabberbot_ for the XMPP backend.

Community behind the project
----------------------------
Err has a `google plus community`_, please feel free to mention it with +err if you need support, have any questions or wish to share some of your creations. If you have a bug to report or wish to request a feature, please log these on it's github_ page.

We strongly encourage you to share your creations, as you will see, a git url is all that you need to share so other people can try out your plugin from err.
If your feature could be interesting as a part of an existing plugin, feel free to fork it on github_ too.

Features
--------

Backends and main features :

- XMPP support: Tested with hipchat_, openfire_ and Jabber but should be compatible with any standard XMPP server
- CampFire support
- Basic IRC support
- Supports MUCs (chatrooms)
- Local graphical console (for testing/development)
- Local text console (for testing/development)

Included : 

- A !help command that generates documentation dynamically from the python docstrings of the commands
- A command history system where users can recall previous commands
- Can proxy and route one 2 one messages to MUC so it can enable simpler XMPP notifiers to be MUC compatible (for example the jira XMPP notifier)

Administration and Security :

- Can be setup so a restricted list of people have administrative rights (You can even limit specific commands to specific users and rooms)
- Dynamic plugin architecture : Bot admins can install/uninstall/update/enable/disable plugins dynamically just by chatting with the bot
- Plugins can be hosted publicly or privately on git
- Plugins can be configured directly from chat (no need to change setup files for every plugin)
- Configs can be exported and imported again with two commands (!export and !import respectively)
- Technical logs can be inspected from the chat or [logged to Sentry](https://github.com/gbin/err/wiki/Logging-with-Sentry)

Provides for Extensibility :  

- A really low learning curve for writing plugins (see example below)
- Graphical and text development consoles for superfast development roundtrips
- Out of the box support for subcommands in plugins
- An automatic persistence store per plugin
- Really simple webhooks integration
- A polling framework for plugins
- An easy configuration framework
- A templating framework to display fancy HTML messages
- Automatic conversion from HTML to plaintext when the backend doesn't support HTML (so you don't have to make text and HTML versions of your command output)


.. _hipchat: http://www.hipchat.org/
.. _openfire: http://www.igniterealtime.org/projects/openfire/
.. _jabberbot: http://thp.io/2007/python-jabberbot/
.. _yapsy: http://yapsy.sourceforge.net/
.. _`google plus community`: https://plus.google.com/b/101905029512356212669/communities/117050256560830486288
.. _github: http://github.com/gbin/err/

Prerequisites
-------------
It runs under Python 2.7.x or Python 3.2+ under Linux / Windows and Mac.

Create a user for the bot on your private XMPP server or on a public server like jabber.org.
Optionally you can create a MUC (also called conference room or chatroom) in which you can interact with the bot. 
Requires a user account on your private XMPP server or on a public server like jabber.org.
You can optionally create a MUC (also called conference room or chatroom) as well in which you can interact with the bot. 

Installation from source
------------------------

**Dependencies**

Python 2.7.x or Python 3.2+
And those python modules. The copy-paste for the lazy pip users but if you can have them from your standard distro it is better::

    pip install -r requirements.txt

Create a user for the bot in your XMPP server admin.

From the installation directory copy::

    cp errbot/config-template.py config.py

Read the inline documentation of the file and edit the values so the bot can connect to your XMPP server

**Starting the daemon**

For a one shot try, I would recommend to use::

    ./scripts/err.py

Then you can use the -d (or --daemon) parameter to run it in a detached mode.::

    ./script/err.py -d

so you can inspect the logs for an immediate feedback

Note that config.py needs to be at the root of the working directory of the bot by default.

You can override this behaviour with -c specifying the directory where your config.py is, for example::

    ./script/err.py -c /etc/err

More details on the bot admin features can be found on the wiki : https://github.com/gbin/err/wiki

Installation from pypi
----------------------

Pip will take care of installing err and the basic dependencies for you:
pip install err

Go to or create a working directory for it then copy there and adapt the configuration template::

    cp /usr/lib64/python2.7/site-packages/errbot/config-template.py config.py

(Replace 2.7 by you python version)

Then you can start and try your bot::

    err.py

Installation from gentoo
------------------------

It has been merged to the main tree.

So the standard way: ::

    emerge net-im/err

Interacting with the Bot
------------------------

- Invite the bot directly from your chat client.
- Send commands directly to the bot, or in a MUC the bot has joined. (Try sending _!help_, without the quotes)
- If you wish to know more about a specific command you can send _!help command_

More documentation is available on the wiki : https://github.com/gbin/err/wiki

Install/uninstalling public plugins
-----------------------------------

To get a list of public plugin repos you can do::

    !repos

Then pick one that you fancy, for example::

    !install err-pollbot

You should then instantly have a new poll service you can use to vote for where to go for lunch with your colleagues :)

You can always uninstall a plugin again with::

    !uninstall err-pollbot

Note: Please pay attention when you install a plugin, it may have additional dependencies

Tutorial to write a simple plugin
---------------------------------

Try it! It's super simple!

You can find a tutorial here : https://github.com/gbin/err/wiki/plugin-dev

