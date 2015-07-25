v3.0.0-beta
===========

New and noteworthy
------------------

- backends are now plugins too
- new Slack backend
- new Gitter backend (see http://www.github.com/gbin/err-backend-gitter for more info about installing it)
- completely revamped backup/restore feature.
- hipchat endpoint can be used (#348)
- XMPP server parameter can be overriden
- Identifiers are now generic (not tight to XMPP anymore)



Stuff that might break you
--------------------------

- XMPP properties .node, .domain and .resource on identifiers are deprecated, a backward compatibility layer has been added but we highly encourage you to not rely on those but use the generic ones from now on: .person, .client and for MUCOccupants .room on top of .person and .client.
- To create identifiers from a string (i.e. if you don't get it from the bot itself) you now have to use build_identifier(string) to make the backend parse it
- command line parameter -c needs to be the full path of your config file, it allows us to have different set of configs to test the bot.
- campfire and TOX backends are now external plugins: see http://www.github.com/gbin/err-backend-tox and http://www.github.com/gbin/err-backend-campfire for more info about installing them.

Bugs squashed
-------------

- import error at install time.
- IRC backend compatibility with gitter
- Better logging to debug plugin callbacks
- Better dependency requirements (setup.py vs requirements.txt)
- builtins are now named core_plugins (the plan is to move more there)
- a lot of refactoring around globals (it enabled the third party plugins)

