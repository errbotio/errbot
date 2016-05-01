Setup
=====

Prerequisites
-------------

Errbot runs under Python 2.7 as well as Python 3.2+ on Linux, Windows and Mac.

You need to have registered a user for the bot to use on the XMPP or IRC server that
you wish to run Errbot on. A lot of plugins use multi user chatrooms (MUC) as well, so
it is recommended (but not required) to have a least one MUC for Errbot to use as well.

Installation
------------

Errbot may be installed directly from PyPi using `pip`_ by issuing::

    pip install errbot

Or if you wish to try out the latest, bleeding edge version::

    pip install https://github.com/errbotio/errbot/archive/master.zip

However, installing into a `virtualenv`_ is **strongly** recommended.
If you have virtualenv installed,
you could instead do::

    # Create the virtualenv
    virtualenv --python /usr/bin/python3 /path/to/my/virtualenv
    # Use pip from the virtualenv instead of the global pip
    # to install errbot
    /path/to/my/virtualenv/bin/pip install errbot

On some distributions,
Errbot is also available as a package
via your usual package manager.
In these cases, it is generally recommended to use your distribution's package
instead of installing from PyPi
but note that the version packaged with your distribution
may be a few versions behind.


Extra dependencies
^^^^^^^^^^^^^^^^^^

Errbot's default dependency list
contains only the bare minimum list of dependencies
needed to run Errbot.
Depending on the backend you choose,
additional requirements need to be installed.

This means that you will need to install some extra dependencies
to make use of the backend suitable for the chat network you are using.

* For XMPP servers::

      pip install sleekxmpp pyasn1 pyasn1-modules

* For IRC servers::

      pip install irc

* For HipChat::

      pip install sleekxmpp pyasn1 pyasn1-modules hypchat

* For Slack::

      pip install slackclient

* For Telegram messenger::

      pip install python-telegram-bot


Configuration
-------------

Once you have installed errbot,
you will have to configure it to connect to your desired chat network.
First, create a directory somewhere on your system
where errbot may store its configuration and data.

Once you have created the directory,
change into it and copy the default configuration file into place.
There are two ways to do this:

1. You can generate it directly from your errbot installation with:

    `python -c "import errbot;import os;import shutil;shutil.copyfile(os.path.dirname(errbot.__file__) + os.path.sep + 'config-template.py', 'config.py')"`

2. Or you can download the template manually from `GitHub <https://raw.githubusercontent.com/errbotio/errbot/master/errbot/config-template.py>`_ and save it as `config.py`.

   You could also do this on the command-line with the following command:
    `curl -o config.py https://raw.githubusercontent.com/errbotio/errbot/master/errbot/config-template.py`

You will have to edit the values in this file to setup the desired configuration for the bot.
The example configuration comes with extensive documenation of all the various options
so we won't go into too much detail here,
but we'll go through the options that you absolutely must change now
so that you can quickly get started
and make further tweaks to the configuration later on.

Please open `config.py` in your favorite editor now.
The first setting we must change is `BOT_DATA_DIR`.
This is the directory where the bot will store configuration data.
Set this to the directory you created earlier.

The default value for `BOT_LOG_FILE` likely points to a directory
which doesn't exist on your system,
so you must change this as well.
One suggestion is to set the value as `BOT_LOG_FILE = BOT_DATA_DIR + '/errbot.log'`.
This will make it write a file `errbot.log` in the same data directory
that you configured above.

The final configuration we absolutely must do is setting up a correct `BACKEND`
and configuring `BOT_IDENTITY` with the details of the account that you wish to use.

The configuration for these settings differs depending on which chat network you wish to connect to,
so please refer to the documentation for your desired network
from the following list:

.. toctree::
  :maxdepth: 1

  configuration/xmpp
  configuration/irc
  configuration/hipchat
  configuration/slack
  configuration/telegram


Starting the daemon
-------------------

The first time you start Errbot, it is recommended to run it in foreground mode. This can
be done with::

    errbot

If you installed errbot into a virtualenv (as recommended),
call it by prefixing the virtualenv `bin/` directory::

    /path/to/my/virtualenv/bin/errbot

Please pass -h or --help to errbot to get a list of supported parameters.
Depending on your situation,
you may need to pass --config (or -c)
pointing to the directory holding your `config.py`
when starting Errbot.

If all that worked out,
you can now use the -d (or --daemon) parameter to run it in a detached mode::

    errbot --daemon

If you are going to run your bot all the time then using some process control system
such as `supervisor`_ is highly recommended. Installing and configuring such a system
is outside the scope of this document however.


Upgrading
---------

Errbot comes bundled with a plugin which automatically performs a periodic update check.
Whenever there is a new release on PyPI,
this plugin will notify the users set in `BOT_ADMINS` about the new version.

Assuming you originally installed errbot using pip (see `installation`_),
you can upgrade errbot in much the same way.
If you used a virtualenv::

    /path/to/my/virtualenv/bin/pip install --upgrade errbot

Or if you used pip without virtualenv::

    pip install --upgrade errbot

It's recommended that you review the changelog before performing an upgrade
in case backwards-incompatible changes have been introduced in the new version.
The changelog for the release you will be installing can always be found
on `PyPI <https://pypi.python.org/pypi/errbot>`_.


Hacking on Errbot's code directly
---------------------------------

Errbot is written for Python 3. In order to run under Python 2.7 the code is run through
3to2 at install time. This means that while it is possible to run Errbot under Python 3.3+
directly from a source checkout, it is not possible to do so with Python 2.7.
If you wish to develop or test with Errbot's code under 2.7, you must run::

    python setup.py install

Alternatively, you can also look into the `--editable` parameter of pip install.


Provisioning (advanced)
-----------------------
.. toctree::
  :maxdepth: 1

  configuration/provisioning
 
.. _virtualenv: https://virtualenv.pypa.io/en/latest/
.. _pip: https://pip.pypa.io/en/stable/
.. _supervisor: http://supervisord.org/
