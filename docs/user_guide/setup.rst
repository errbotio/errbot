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

Errbot may be installed directly from PyPi using `pip` (`easy_install` works too) by issuing::

    pip install errbot

Or if you wish to try out the latest, bleeding edge version::

    pip install https://github.com/errbotio/errbot/archive/master.zip

However, in these cases, installing into a dedicated `virtualenv`_ is recommended.

On some distributions, Errbot is available as a package via your usual package manager.
In these cases, it is generally recommended to use your distribution's package instead
of installing from PyPi.

Extra dependencies
^^^^^^^^^^^^^^^^^^

requirements.txt lists only the bare minimum list of dependencies needed to run Errbot.
Depending on the backend you choose, additional requirements need to be installed.

For the XMPP based backends you must also install::

    sleekxmpp
    pyasn1
    pyasn1-modules
    dnspython3  # dnspython for Python 2.7

For the IRC backend, you must install::

    irc

For the Hipchat backend you must install::

    hypchat

Configuration
-------------

After installing Errbot, you must create a data directory somewhere on your system where
config and data may be stored.

You need to create there a config.py file to setup the basic parameters of your bot.


Option 1: you can generate it directly from your errbot installation with::

    python -c "import errbot;import os;import shutil;shutil.copyfile(os.path.dirname(errbot.__file__) + os.path.sep + 'config-template.py', 'config.py')"

Option 2: You can download a template from `this link <https://raw.githubusercontent.com/errbotio/errbot/master/errbot/config-template.py>`_ 
and rename it `config.py`.

Option 3: Or you can download this same template from curl too::

    curl -o config.py https://raw.githubusercontent.com/errbotio/errbot/master/errbot/config-template.py


Read the documentation within this file and edit the values as needed so the bot can
connect to your favorite chat server.

Starting the daemon
-------------------

The first time you start Errbot, it is recommended to run it in foreground mode. This can
be done with::

    errbot

Please pass -h or --help to errbot to get a list of supported parameters.
Depending on your situation, you may need to pass --config (or -c) pointing to config.py
when starting Errbot.

If all that worked out, you can now use the -d (or --daemon) parameter to run it in a
detached mode::

    errbot --daemon

If you are going to run your bot all the time then using some process control system
such as `supervisor`_ is highly recommended. Installing and configuring such a system
is outside the scope of this document however.

Hacking on Errbot's code directly
---------------------------------

Errbot is written for Python 3. In order to run under Python 2.7 the code is run through
3to2 at install time. This means that while it is possible to run Errbot under Python 3.3+
directly from a source checkout, it is not possible to do so with Python 2.7.
If you wish to develop or test with Errbot's code under 2.7, you must run::

    python setup.py install

Alternatively, you can also look into the `--editable` parameter of pip install.

.. _virtualenv: https://pypi.python.org/pypi/virtualenv
.. _supervisor: http://supervisord.org/
