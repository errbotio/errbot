v3.0.0-rc1
==========

``Release date: 2015-07-24``

We have decided to promote this release as the v3 \\o/. This is the next version after 2.3.0-rc2.

This document includes all the changes since the last stable version (2.2.0).

If you have any difficulty using this new release, feel free to jump into our `dev room on gitter <https://gitter.im/gbin/err>`_.

New and noteworthy
------------------

- backends are now plugins too
- new Slack backend (see the `config template <https://github.com/gbin/err/blob/master/errbot/config-template.py#L118>`_ for details)
- new Gitter backend (see `the gitter backend repo <http://www.github.com/gbin/err-backend-gitter>`_ for more info about installing it)
- completely new rendering engine: now all text from either a plugin return or a template is **markdown extras**
- you can test the various formatting under your backend with the ``!render test`` command.
- the text backend exposes the original md, its html representation and ansi representation so plugin developers can anticipate what the rendering will look like under various backends
See the screenshots below: Slack_, Hipchat_, IRC_, Gitter_ and finally Text_.

- completely revamped backup/restore feature (see ``!help backup``).
- Identifiers are now generic (and not tight to XMPP anymore) with common notions of ``.person`` ``.room`` (for MUCIdentifiers) ``.client`` ``.nick`` and ``.displayname`` see `this doc <https://github.com/gbin/err/blob/master/docs/user_guide/backend_development/index.rst#identifiers>`_ for details.
- New ``!whoami`` command to debug identity problems for your plugins.
- New ``!killbot`` command to stop your bot remotely in case of emergency.
- IRC: file transfer from the bot is now supported (DCC)

Minor improvements
------------------

- hipchat endpoint can be used (#348)
- XMPP server parameter can be overriden
- deep internal reorganisation of the bot: the most visible change is that internal commands have been split into internal plugins.
- IRC backend: we have now a reconnection logic on disconnect and on kick (see ``IRC_RECONNECT_ON_DISCONNECT`` in the config file for example)

Stuff that might break you
--------------------------

- if you upgrade from a previous version, please install: ``pip install markdown ansi Pygments "pygments-markdown-lexer>=0.1.0.dev29"``
- you need to add the type of backend you use in your config file instead of the command like. i.e. ``BACKEND = 'XMPP'``
- XMPP properties ``.node``, ``.domain`` and ``.resource`` on identifiers are deprecated, a backward compatibility layer has been added but we highly encourage you to not rely on those but use the generic ones from now on: ``.person``, ``.client`` and for MUCOccupants ``.room`` on top of ``.person`` and ``.client``.
- To create identifiers from a string (i.e. if you don't get it from the bot itself) you now have to use ``build_identifier(string)`` to make the backend parse it
- command line parameter -c needs to be the full path of your config file, it allows us to have different set of configs to test the bot.
- campfire and TOX backends are now external plugins: see `the tox backend repo <http://www.github.com/gbin/err-backend-tox>`_ and `the campfire backend repo <http://www.github.com/gbin/err-backend-campfire>`_ for more info about installing them.
- any output from plugin is now considered markdown, it might break some of your output if you had any markup characters (\#, \-, \* ...).

Bugs squashed
-------------

- import error at install time.
- IRC backend compatibility with gitter
- Better logging to debug plugin callbacks
- Better dependency requirements (setup.py vs requirements.txt)
- builtins are now named core_plugins (the plan is to move more there)
- a lot of refactoring around globals (it enabled the third party plugins)
- git should now work under Windows
- None was documented as a valid value for the IRC rate limiter but was not.
- removed xep_0004 from the xmpp backend (it was deprecated)

Annex
-----

.. _Slack:

Rendering under **Slack**:

.. image:: docs/imgs/slack.png

.. _Hipchat:

Rendering under **Hipchat**:

.. image:: docs/imgs/hipchat.png

.. _IRC:

Rendering under **IRC**:

.. image:: docs/imgs/IRC.png

.. _Gitter:

Rendering under **Gitter**:

.. image:: docs/imgs/gitter.png

.. _Text:

Rendering under **Text** (for plugin development):

.. image:: docs/imgs/text.png
