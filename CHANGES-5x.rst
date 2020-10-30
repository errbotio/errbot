v5.2.0 (2018-04-04)
-------------------

fixes:

-  backup fix : SyntaxError: literal_eval on file with statements (thx
   Bruno Oliveira)
-  plugin_manager: skip plugins not in CORE_PLUGIN entirely (thx Dylan
   Page)
-  repository search fix (thx Sijis)
-  Text: mentions in the Text backend (thx Sijis)
-  Text: double @ in replies (thx Sijis)
-  Slack: Support breaking messages body attachment
-  Slack: Add channelname to Slackroom (thx Davis Garana Pena)

features:

-  Enable split arguments on room_join so you can use " (thx Robert
   Honig)
-  Add support for specifying a custom log formatter (Thx Oz Linden)
-  Add Sentry transport support (thx Dylan Page)
-  File transfert support (send_stream_request) on the Hipchat backend
   (thx Brad Payne)
-  Show user where they are in a flow (thx Elijah Roberts)
-  Help commands are sorted alphabetically (thx Fabian Chong)
-  Proxy support for Slack (thx deferato)

v5.1.3 (2017-10-15)
-------------------

fixes:

-  Default –init config is now compatible with Text backend
   requirements.
-  Windows: Config directories as raw string (Thx defAnfaenger)
-  Windows: Repo Manager first time update (Thx Jake Shadle)
-  Slack: fix Slack identities to be hashable
-  Hipchat: fix HicpChat Server XMPP namespace (Thx Antti Palsola)
-  Hipchat: more aggressive cashing of user list to avoid API quota
   exceeds (thx Roman)

v5.1.2 (2017-08-26)
-------------------

fixes:

-  Text: BOT_IDENTITY to stay optional in config.py
-  Hipchat: send_card fix for room name lookup (thx Jason Kincl)
-  Hipchat: ACL in rooms

v5.1.1 (2017-08-12)
-------------------

fixes:

-  allows spaces in BOT_PREFIX.
-  Text: ACLs were not working (@user vs user inconsistency).

v5.1.0 (2017-07-24)
-------------------

fixes:

-  allow webhook receivers on / (tx Robin Gloster)
-  force utf-8 to release changes (thx Robert Krambovitis)
-  don't generate an errbot section if no version is specified in plugin
   gen (thx Meet Mangukiya)
-  callback on all unknown commands filters
-  user friendly message when a room is not found
-  webhook with no uri but kwargs now work as intended
-  Slack: support for Enterprise Grid (thx Jasper)
-  Hipchat: fix room str repr. (thx Roman)
-  XMPP: fix for MUC users with @ in their names (thx Joon Guillen)
-  certificate generation was failing under some conditions

features:

-  Support for threaded messages (Slack initially but API is done for
   other backends to use)
-  Text: now the text backend can emulate an inroom/inperson or
   asuser/asadmin behavior
-  Text: autocomplete of command is now supported
-  Text: multiline messages are now supported
-  start_poller can now be restricted to a number of execution (thx
   Marek Suppa)
-  recurse_check_structure back to public API (thx Alex Sheluchin)
-  better flow status (thx lijah Roberts)
-  !about returns a git tag instead of just 9.9.9 as version for a git
   checkout. (thx Sven)
-  admin notifications can be set up to a set of users (thx Sijis
   Aviles)
-  logs can be colorized with drak, light or nocolor as preference.

v5.0.1 (2017-05-08)
-------------------

hotfixes for v5.0.0.

fixes: - fix crash for SUPPRESS_CMD_NOT_FOUND=True (thx Romuald
Texier-Marcadé!)

breaking / API cleanups: - Missed patch for 5.0.0: now the name of a
plugin is defined by its name in .plug and not its class name.

v5.0.0 (2017-04-23)
-------------------

features:

-  Add support for cascaded subcommands (cmd_sub1_sub2_sub3) (thx
   Jeremiah Lowin)
-  You can now use symbolic links for your plugins
-  Telegram: send_stream_request support added (thx Alexandre Manhaes
   Savio)
-  Callback to unhandled messages (thx tamarin)
-  flows: New option to disable the next step hint (thx Aviv Laufer)
-  IRC: Added Notice support (bot can listen to them)
-  Slack: Original slack event message is attached to Message (Thx Bryan
   Shelton)
-  Slack: Added reaction support and Message.extras['url'] (Thx Tomer
   Chachamu)
-  Text backend: readline support (thx Robert Coup)
-  Test backend: stream requests support (thx Thomas Lee)

fixes:

-  When a templated cmd crashes, it was crashing in the handling of the
   error.
-  Slack: no more crash if a message only contains attachments
-  Slack: fix for some corner case links (Thx Tomer Chachamu)
-  Slack: fixed LRU for better performance on large teams
-  Slack: fix for undefined key 'username' when the bot doesn't have one
   (thx Octavio Antonelli)

other:

-  Tests: use conftest module to specify testbot fixture location (thx
   Pavel Savchenko)
-  Python 3.6.x added to travis.
-  Ported the yield tests to pytest 4.0
-  Removed a deprecated dependency for the threadpool, now uses the
   standard one (thx Muri Nicanor)

breaking / API cleanups:

-  removed deprecated presence attributes (nick and occupant)
-  removed deprecated type from messages.
-  utils.ValidationException has moved to errbot.ValidationException and
   is fully part of the API.
-  {utils, errbot}.get_class_that_defined_method is now
   \_bot.get_plugin_class_from_method
-  utils.utf8 has been removed, it was a leftover for python 2 compat.
-  utils.compat_str has been removed, it was a vestige for python 2 too.
