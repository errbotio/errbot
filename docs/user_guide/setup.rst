Setup
=====

Prerequisites
-------------

Errbot runs under Python 3.3+ on Linux, Windows and Mac.

Installation
------------

Option 1: Use the package manager of your distribution (if available)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On some distributions, Errbot is also available as a package via your usual package manager.
In these cases, it is generally recommended to use your distribution's package instead of installing from PyPi but note
that the version packaged with your distribution may be a few versions behind.

Example of packaged versions of Errbot:

Gentoo: https://gpo.zugaina.org/net-im/errbot
Arch: https://aur.archlinux.org/packages/python-err/
Docker: https://hub.docker.com/r/rroemhild/errbot/
Juju: https://jujucharms.com/u/onlineservices-charmers/errbot


Option 2: Installing Errbot in a virtualenv (preferred)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Installing into a `virtualenv`_ is **strongly** recommended.
If you have virtualenv installed, you can do for example::

    virtualenv --python `which python3` ~/.errbot-ve
    ~/.errbot-ve/pip install errbot


If you have virtualenvwrapper installed it is even simpler::

    mkvirtualenv -p `which python3` errbot-ve
    pip install errbot


Option 3: Installing Errbot at the system level (not recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Errbot may be installed directly from PyPi using `pip`_ by issuing::

    pip3 install errbot


.. note::
    Some of errbot's dependencies need to build C extensions
    which means you need to have development headers for some libraries installed.
    On Debian/Ubuntu these may be installed with
    `apt-get install python3-dev libssl-dev libffi-dev`
    Package names may differ on other OS's.

.. _configuration:

First run
^^^^^^^^^

You can quickly configure Errbot by first creating a working directory and calling `errbot --init`::

    mkdir ~/errbot-root
    cd ~/errbot-root
    errbot --init

This will create a minimally working errbot in text (development) mode. You can try it right away::

    errbot
    [...]
    >>>


`>>>` is a prompt, you can talk to errbot directly. You can try::

    !tryme
    !help
    !about

Configuration
-------------

Once you have installed errbot and did `errbot --init`, you will have to tweak the generated `config.py` to connect
to your desired chat network.

You can use :download:`config-template.py` as a base for your `config.py`.

We'll go through the options that you absolutely must check now so that you can quickly get started
and make further tweaks to the configuration later on.

Open `config.py` in your favorite editor.
The first setting to check or change if `BOT_DATA_DIR` if correct.
This is the directory where the bot will store configuration data.

The first setting to check or change `BOT_LOG_FILE` to be sure it point to a writeable directory on your system.

The final configuration we absolutely must do is setting up a correct `BACKEND` which is set to `Text` by
`errbot --init` but you can change to the name of the chat system you want to connect to (see the template above
for valid values).

You absolutely need a `BOT_IDENTITY` entry to set the credentials Errbot will use to connect to the chat system.

You can find here more details about configuring Errbot for some specific chat systems:

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

.. note::
    There are two ways to gracefully shut down a running bot.

    You can use the :code:`!shutdown` command to do so via chat or you can send a `SIGINT` signal to the errbot process to do so from the commandline

    If you're running errbot in the foreground then pressing Ctrl+C is equivalent to sending `SIGINT`.


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

Provisioning (advanced)
-----------------------

See the `provisioning documentation <provisioning.html>`_

.. _virtualenv: https://virtualenv.pypa.io/en/latest/
.. _pip: https://pip.pypa.io/en/stable/
.. _supervisor: http://supervisord.org/
