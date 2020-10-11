v6.1.5 (2020-10-10)
-------------------

features:

- XMPP: Replace sleekxmpp with slixmpp (#1430)
- New callback for reaction events (#1292)
- Added email property foriPerson object on all backends (#1186, #1456)
- chore: Add github actions (#1455)

fixes:

- Slack: Deprecated method calls (#1432, #1438)
- Slack: Increase message size limit. (#1333)
- docs: Remove Matrix backend link (#1445)
- SlackRTM: Missing 'id_' in argument (#1443)
- docs: fixed rendering with double hyphens (#1452)
- cli: merging configs via `--storage-merge` option (#1450)


v6.1.4 (2020-05-15)
-------------------

fixes:

- 403 error when fetching plugin repos index (#1425)

v6.1.3 (2020-04-19)
-------------------

features:

- Add security linter (#1314)
- Serve version.json on errbot.io and update version checker plugin (#1400)
- Serve repos.json on errbot.io (#1403, #1406)
- Include SlackRTM backend (beta) (#1416)

fixes:

- Make plugin name clashes deterministic (#1282)
- Fix error with Flows missing descriptions (#1405)
- Fix `!repos update` object attribute error (#1410)
- Fix updating remove repos using `!repos update` (#1413)
- Fix deprecation warning (#1423)
- Varios documentation fixes (#1404, #1411, #1415)


v6.1.2 (2019-12-15)
-------------------

fixes:

-  Add ability to re-run --init safely (#1390)
-  fix #1375 by managing errors on lack of version endpoint.
-  Fixed a deprecation warning for 3.9 on Mapping.
-  removing the intermediate domain requiring a certificate.
-  Fix package name for sentry-sdk flask integration
-  Add support to sentry FlaskIntegration
-  Migrate from raven (deprecated) to new sentry-sdk
-  fix: Log errors when present
-  Make chatroom log more descriptive
-  Set admin check log as debug
-  Add admin warnings to log
-  Fix: Advanced loop graph does not reflect the image
-  make the TestBot start timeout parameterized
-  errbot/plugin_manager: only check for /proc/1/cgroup if path exists to fix warning
-  removed (c) Apple asset we completely missed.
-  fix double threading in slack backend if DIVERT_TO_THREAD is used
-  pop up the timeout for travis
-  Makes the timeout feedback better on tests. (#1366)
-  Move all tox environments to use py37 (#1342)
-  Remove empty "text" body on Slack send_card (#1336)
-  Load class source in reloading plugins (#1347)
-  test: Rename assertCommand -> assertInCommand (#1351)
-  Enforce BOT_EXTRA_BACKEND_DIR is a list type. (#1358)
-  Fix #1360 Cast pathlib.Path objects to strings for use with sys.path (#1361)

v6.1.1 (2019-06-22)
-------------------

fixes:

- Installation using wheel distribution on python 3.6 or older

v6.1.0 (2019-06-16)
-------------------

features:

- Use python git instead of system git binary (#1296)

fixes:

- `errbot -l` cli error (#1315)
- Slack backend by pinning slackclient to supported version (#1343)
- Make --storage-merge merge configs (#1311)
- Exporting values in backup command (#1328)
- Rename Spark to Webex Teams (#1323)
- Various documentation fixes (#1310, #1327, #1331)

v6.0.0 (2019-03-23)
-------------------

features:

- TestBot: Implement inject_mocks method (#1235)
- TestBot: Add multi-line command test support (#1238)
- Added optional room arg to inroom
- Adds ability to go back to a previous room
- Pass telegram message id to the callback

fixes:

- Remove extra spaces in uptime output
- Fix/backend import error messages (#1248)
- Add docker support for installing package dependencies (#1245)
- variable name typo (#1244)
- Fix invalid variable name (#1241)
- sanitize comma quotation marks too (#1236)
- Fix missing string formatting in "Command not found" output (#1259)
- Fix webhook test to not call fixture directly
- fix: arg_botcmd decorator now can be used as plain method
- setup: removing dnspython
- pin markdown <3.0 because safe is deprecated

v6.0.0-alpha (2018-06-10)
-------------------------

major refactoring:

- Removed Yapsy dependency
- Replaced back Bottle and Rocket by Flask
- new Pep8 compliance
- added Python 3.7 support
- removed Python 3.5 support
- removed old compatibility cruft
- ported formats and % str ops to f-strings
- Started to add field types to improve type visibility across the codebase
- removed cross dependencies between PluginManager & RepoManager

fixes:

- Use sys.executable explicitly instead of just 'pip' (thx Bruno Oliveira)
- Pycodestyle fixes (thx Nitanshu)
- Help: don't add bot prefix to non-prefixed re cmds (#1199) (thx Robin Gloster)
- split_string_after: fix empty string handling (thx Robin Gloster)
- Escaping bug in dynamic plugins
- botmatch is now visible from the errbot module (fp to Guillaume Binet)
- flows: hint boolean was not forwarded
- Fix possible event without bot_id (#1073) (thx Roi Dayan)
- decorators were working only if kwargs were empty
- Message.clone was ignoring partial and flows


features:

- partial boolean to flag partial mesages (thx Meet Mangukiya)
- Slack: room joined callback (thx Jeremy Kenyon)
- XMPP: real_jid to get the jid the users logged in (thx Robin Gloster)
- The callback order set in the config is not globally respected
- Added a default parameter to the storage context manager


v5.2.0 (2018-04-04)
-------------------

fixes:

- backup fix : SyntaxError: literal_eval on file with statements (thx Bruno Oliveira)
- plugin_manager: skip plugins not in CORE_PLUGIN entirely (thx Dylan Page)
- repository search fix (thx Sijis)
- Text: mentions in the Text backend (thx Sijis)
- Text: double @ in replies (thx Sijis)
- Slack: Support breaking messages body attachment
- Slack: Add channelname to Slackroom (thx Davis Garana Pena)

features:

- Enable split arguments on room_join so you can use " (thx Robert Honig)
- Add support for specifying a custom log formatter (Thx Oz Linden)
- Add Sentry transport support (thx Dylan Page)
- File transfert support (send_stream_request) on the Hipchat backend (thx Brad Payne)
- Show user where they are in a flow (thx Elijah Roberts)
- Help commands are sorted alphabetically (thx Fabian Chong)
- Proxy support for Slack (thx deferato)


v5.1.3 (2017-10-15)
-------------------

fixes:

- Default --init config is now compatible with Text backend requirements.
- Windows: Config directories as raw string (Thx defAnfaenger)
- Windows: Repo Manager first time update (Thx Jake Shadle)
- Slack: fix Slack identities to be hashable
- Hipchat: fix HicpChat Server XMPP namespace (Thx Antti Palsola)
- Hipchat: more aggressive cashing of user list to avoid API quota exceeds (thx Roman)

v5.1.2 (2017-08-26)
-------------------

fixes:

- Text: BOT_IDENTITY to stay optional in config.py
- Hipchat: send_card fix for room name lookup (thx Jason Kincl)
- Hipchat: ACL in rooms

v5.1.1 (2017-08-12)
-------------------

fixes:

- allows spaces in BOT_PREFIX.
- Text: ACLs were not working (@user vs user inconsistency).

v5.1.0 (2017-07-24)
-------------------

fixes:

- allow webhook receivers on / (tx Robin Gloster)
- force utf-8 to release changes (thx Robert Krambovitis)
- don't generate an errbot section if no version is specified in plugin gen (thx Meet Mangukiya)
- callback on all unknown commands filters
- user friendly message when a room is not found
- webhook with no uri but kwargs now work as intended
- Slack: support for Enterprise Grid (thx Jasper)
- Hipchat: fix room str repr. (thx Roman)
- XMPP: fix for MUC users with @ in their names (thx Joon Guillen)
- certificate generation was failing under some conditions

features:

- Support for threaded messages (Slack initially but API is done for other backends to use)
- Text: now the text backend can emulate an inroom/inperson or asuser/asadmin behavior
- Text: autocomplete of command is now supported
- Text: multiline messages are now supported
- start_poller can now be restricted to a number of execution (thx Marek Suppa)
- recurse_check_structure back to public API (thx Alex Sheluchin)
- better flow status (thx lijah Roberts)
- !about returns a git tag instead of just 9.9.9 as version for a git checkout. (thx Sven)
- admin notifications can be set up to a set of users (thx Sijis Aviles)
- logs can be colorized with drak, light or nocolor as preference.

v5.0.1 (2017-05-08)
-------------------
hotfixes for v5.0.0.

fixes:
- fix crash for SUPPRESS_CMD_NOT_FOUND=True (thx Romuald Texier-Marcadé!)

breaking / API cleanups:
- Missed patch for 5.0.0: now the name of a plugin is defined by its name in .plug and not its class name.



v5.0.0 (2017-04-23)
-------------------

features:

- Add support for cascaded subcommands (cmd_sub1_sub2_sub3) (thx Jeremiah Lowin)
- You can now use symbolic links for your plugins
- Telegram: send_stream_request support added (thx Alexandre Manhaes Savio)
- Callback to unhandled messages (thx tamarin)
- flows: New option to disable the next step hint (thx Aviv Laufer)
- IRC: Added Notice support (bot can listen to them)
- Slack: Original slack event message is attached to Message (Thx Bryan Shelton)
- Slack: Added reaction support and Message.extras['url'] (Thx Tomer Chachamu)
- Text backend: readline support (thx Robert Coup)
- Test backend: stream requests support (thx Thomas Lee)

fixes:

- When a templated cmd crashes, it was crashing in the handling of the error.
- Slack: no more crash if a message only contains attachments
- Slack: fix for some corner case links (Thx Tomer Chachamu)
- Slack: fixed LRU for better performance on large teams
- Slack: fix for undefined key 'username' when the bot doesn't have one (thx Octavio Antonelli)

other:

- Tests: use conftest module to specify testbot fixture location (thx Pavel Savchenko)
- Python 3.6.x added to travis.
- Ported the yield tests to pytest 4.0
- Removed a deprecated dependency for the threadpool, now uses the standard one (thx Muri Nicanor)

breaking / API cleanups:

- removed deprecated presence attributes (nick and occupant)
- removed deprecated type from messages.
- utils.ValidationException has moved to errbot.ValidationException and is fully part of the API.
- {utils, errbot}.get_class_that_defined_method is now _bot.get_plugin_class_from_method
- utils.utf8 has been removed, it was a leftover for python 2 compat.
- utils.compat_str has been removed, it was a vestige for python 2 too.


v4.3.7 (2017-02-08)
-------------------

fixes:

- slack: compatibility  with slackclient > 1.0.5.
- render test fix (thx Sandeep Shantharam)

v4.3.6 (2017-01-28)
-------------------

fixes:

- regression with Markdown 2.6.8.

v4.3.5 (2016-12-21)
-------------------

fixes:

- slack: compatibility with slackclient > 1.0.2
- slack: block on reads on RTM (better response time) (Thx Tomer Chachamu)
- slack: fix link names (")
- slack: ignore channel_topic messages (thx Mikhail Sobolev)
- slack: Match ACLs for bots on integration ID
- slack: Process messages from webhook users
- slack: don't crash when unable to look up alternate prefix
- slack: trm_read refactoring (thx Chris Niemira)
- telegram: fix telegram ID test against ACLs
- telegram: ID as strings intead of ints (thx Pmoranga)
- fixed path to the config template in the startup error message (Thx Ondrej Skopek)

v4.3.4 (2016-10-05)
-------------------

features:

- Slack: Stream (files) uploads are now supported
- Hipchat: Supports for self-signed server certificates.

fixes:

- Card emulation support for links (Thx Robin Gloster)
- IRC: Character limits fix (Thx lqaz)
- Dependency check fix.


v4.3.3 (2016-09-09)
-------------------

fixes:

- err references leftovers
- requirements.txt is now standard (you can use git+https:// for example)

v4.3.2 (2016-09-04)
-------------------

hotfix:

- removed the hard dependency on pytest for the Text backend

v4.3.1 (2016-09-03)
-------------------

features:

- now the threadpool is of size 10 by default and added a configuration.

fixes:

- fixed imporlib/use pip as process (#835)  (thx Raphael Wouters)
- if pip is not found, don't crash errbot
- build_identifier to send message to IRC channels (thx mr Shu)


v4.3.0 (2016-08-10)
-------------------

v4.3 features
~~~~~~~~~~~~~

- `DependsOn:` entry in .plug and `self.get_plugin(...)` allowing you to make a plugin dependent from another.
- New entry in config.py: PLUGINS_CALLBACK_ORDER allows you to force a callback order on your installed plugins.
- Flows can be shared by a room if you build the flow with `FlowRoot(room_flow=True)`  (thx Tobias Wilken)
- New construct for persistence: `with self.mutable(key) as value:` that allows you to change by side
  effect value without bothering to save value back.

v4.3 Miscellaneous changes
~~~~~~~~~~~~~~~~~~~~~~~~~~

- This version work only on Python 3.4+ (see 4.2 announcement)
- Presence.nick is deprecated, simply use presence.identifier.nick instead.
- Slack: Bot identity is automatically added to BOT_ALT_PREFIXES
- The version checker now reports your Python version to be sure to not upgrade Python 2 users to 4.3
- Moved testing to Tox. We used to use a custom script, this improves a lot the local testing setup etc.
  (Thx Pedro Rodrigues)


v4.3 fixes
~~~~~~~~~~

- IRC: fixed IRC_ACL_PATTERN
- Slack: Mention callback improvements (Thx Ash Caire)
- Encoding error report was inconsistent with the value checked (Thx Steve Jarvis)
- core: better support for all the types of virtualenvs (Thx Raphael Wouters)


v4.2.2 (2016-06-24)
-------------------

fixes:

- send_templated fix
- CHATROOM_RELAY fix
- Blacklisting feedback message corrected

v4.2.1 (2016-06-10)
-------------------
Hotfix

- packaging failure under python2
- better README

v4.2.0 (2016-06-10)
-------------------

v4.2 Announcement
~~~~~~~~~~~~~~~~~

- Bye bye Python 2 ! This 4.2 branch will be the last to support Python 2. We will maintain bug fixes on it for at least
  the end of 2016 so you can transition nicely, but please start now !

  Python 3 has been released 8 years ago, now all the major distributions finally have it available, the ecosystem has
  moved on too. This was not the case at all when we started to port Errbot to Python 3.

  This will clean up *a lot* of code with ugly `if PY2`, unicode hacks, 3to2 reverse hacks all over the place and
  packaging tricks.
  But most of all it will finally unite the Errbot ecosystem under one language and open up new possibilities as we
  refrained from using py3 only features.

- A clarification on Errbot's license has been accepted. The contributors never intended to have the GPL licence
  be enforced for external plugins. Even if it was not clear it would apply, our new licence exception makes sure
  it isn't.
  Big big thanks for the amazing turnout on this one !


v4.2 New features
~~~~~~~~~~~~~~~~~

- Errbot initial installation. The initial installation has been drastically simplified::

    $ pip install errbot
    $ mkdir errbot; cd errbot
    $ errbot --init
    $ errbot -T
    >>>     <- You are game !!

  Not only that but it also install a development directory in there so it now takes only seconds to have an Errbot
  development environment.

- Part of this change, we also made most of the config.py entries with sane defaults, a lot of those settings were
  not even relevant for most users.

- cards are now supported on the graphic backend with a nice rendering (errbot -G)

- Hipchat: mentions are now supported.


v4.2 Miscellaneous changes
~~~~~~~~~~~~~~~~~~~~~~~~~~

- Documentation improvements
- Reorganization and rename of the startup files. Those were historically the first ones to be created and their meaning
  drifted over the years. We had err.py, main.py and errBot.py, it was really not clear what were their functions and
  why one has been violating the python module naming convention for so long :)
  They are now bootstrap.py (everything about configuring errbot), cli.py (everything about the errbot command line)
  and finally core.py (everything about the commands, and dispatching etc...).
- setup.py cleanup. The hacks in there were incorrect.

v4.2 fixes
~~~~~~~~~~

- core: excpetion formatting was failing on some plugin load failures.
- core: When replacing the prefix `!` from the doctrings only real commands get replaced (thx Raphael Boidol)
- core: empty lines on plugins requirements.txt does crash errbot anymore
- core: Better error message in case of malformed .plug file
- Text: fix on build_identifier (thx Pawet Adamcak)
- Slack: several fixes for identifiers parsing, the backend is fully compliant with Errbot's
  contract now (thx Raphael Boidol and Samuel Loretan)
- Hipchat: fix on room occupants (thx Roman Forkosh)
- Hipchat: fix for organizations with more than 100 rooms. (thx Naman Bharadwaj)
- Hipchat: fixed a crash on build_identifier

v4.1.3 (2016-05-10)
-------------------

hotfixes:

- Slack: regression on build_identifier
- Hipchat: regression on build_identifier (query for room is not supported)

v4.1.2 (2016-05-10)
-------------------

fixes:

- cards for hipchat and slack were not merged.

v4.1.1 (2016-05-09)
-------------------

fixes:

- Python 2.7 conversion error on err.py.

v4.1.0 (2016-05-09)
-------------------

v4.1 features
~~~~~~~~~~~~~

- Conversation flows: Errbot can now keep track of conversations with its users and
  automate part of the interactions in a state machine manageable from chat.
  see `the flows documentation <http://errbot.io/en/master/user_guide/flow_development/index.html>`_
  for more information.

- Cards API: Various backends have a "canned" type of formatted response.
  We now support that for a better native integration with Slack and Hipchat.

- Dynamic Plugins API: Errbot has now an official API to build plugins at runtime (on the fly).
  see `the dynamic plugins doc <http://errbot.io/en/master/user_guide/plugin_development/dynaplugs.html>`_

- Storage command line interface: It is now possible to provision any persistent setting from the command line.
  It is helpful if you want to automate end to end the deployment of your chatbot.
  see `provisioning doc <http://errbot.io/en/master/user_guide/provisioning.html>`_

v4.1 Miscellaneous changes
~~~~~~~~~~~~~~~~~~~~~~~~~~

- Now if no [python] section is set in the .plug file, we assume Python 3 instead of Python 2.
- Slack: identifier.person now gives its username instead of slack id
- IRC: Topic change callback fixed. Thx Ezequiel Brizuela.
- Text/Test: Makes the identifier behave more like a real backend.
- Text: new TEXT_DEMO_MODE that removes the logs once the chat is started: it is made for presentations / demos.
- XMPP: build_identifier can now resolve a Room (it will eventually be available on other backends)
- Graphic Test backend: renders way better the chat, TEXT_DEMO_MODE makes it full screen for your presentations.
- ACLs: We now allow a simple string as an entry with only one element.
- Unit Tests are now all pure py.test instead of a mix of (py.test, nose and unittest)

v4.1 fixed
~~~~~~~~~~

- Better resillience on concurrent modifications of the commands structures.
- Allow multiline table cells. Thx Ilya Figotin.
- Plugin template was incorrectly showing how to check config. Thx Christian Weiske.
- Slack: DIVERT_TO_PRIVATE fix.
- Plugin Activate was not reporting correctly some errors.
- tar.gz packaged plugins are working again.


v4.0.3 (2016-03-17)
-------------------

fixes:

- XMPP backend compatibility with python 2.7
- Telegram startup error
- daemonize regression
- UTF-8 detection

v4.0.2 (2016-03-15)
-------------------

hotfixes:

- configparser needs to be pinned to a 3.5.0b2 beta
- Hipchat regression on Identifiers
- Slack: avoid URI expansion.

v4.0.1 (2016-03-14)
-------------------

hotfixes:

- v4 doesn't migrate plugin repos entries from v3.
- py2 compatibility.

v4.0.0 (2016-03-13)
-------------------

This is the next major release of errbot with significant changes under the hood.


v4.0 New features
~~~~~~~~~~~~~~~~~

- Storage is now implemented as a plugin as well, similar to command plugins and backends.
  This means you can now select different storage implementations or even write your own.

The following storage backends are currently available:

  + The traditional Python `shelf` storage.
  + In-memory storage for tests or ephemeral storage.
  + `SQL storage <https://github.com/errbotio/err-storage-sql>`_ which supports relational databases such as MySQL, Postgres, Redshift etc.
  + `Firebase storage <https://github.com/errbotio/err-storage-firebase>`_ for the Google Firebase DB.
  + `Redis storage <https://github.com/errbotio/err-storage-redis>`_ (thanks Sijis Aviles!) which uses the Redis in-memory data structure store.

- Unix-style glob support in `BOT_ADMINS` and `ACCESS_CONTROLS` (see the updated `config-template.py` for documentation).

- The ability to apply ACLs to all commands exposed by a plugin (see the updated `config-template.py` for documentation).

- The mention_callcack() on IRC (mr. Shu).

- A new (externally maintained) `Skype backend <https://github.com/errbotio/errbot-backend-skype>`_.

- The ability to disable core plugins (such as `!help`, `!status`, etc) from loading (see `CORE_PLUGINS` in the updated `config-template.py`).

- Added a `--new-plugin` flag to `errbot` which can create an emply plugin skeleton for you.

- IPv6 configuration support on IRC (Mike Burke)

- More flexible access controls on IRC based on nickmasks (in part thanks to Marcus Carlsson).
  IRC users, see the new `IRC_ACL_PATTERN` in `config-template.py`.

- A new `callback_mention()` for plugins (not available on all backends).

- Admins are now notified about plugin startup errors which happen during bot startup

- The repos listed by the `!repos` command are now fetched from a public index and can be
  queried with `!repos query [keyword]`. Additionally, it is now possible to add your own
  index(es) to this list as well in case you wish to maintain a private index (special
  thanks to Sijis Aviles for the initial proof-of-concept implementation).


v4.0 fixed
~~~~~~~~~~

- IRC backend no longer crashes on invalid UTF-8 characters but instead replaces
  them (mr. Shu).

- Fixed joining password-protected rooms (Mikko Lehto)

- Compatibility to API changes introduced in slackclient-1.0.0 (used by the Slack backend).

- Corrected room joining on IRC (Ezequiel Hector Brizuela).

- Fixed *"team_join event handler raised an exception"* on Slack.

- Fixed `DIVERT_TO_PRIVATE` on HipChat.

- Fixed `DIVERT_TO_PRIVATE` on Slack.

- Fixed `GROUPCHAT_NICK_PREFIXED` not prefixing the user on regular commands.

- Fixed `HIDE_RESTRICTED_ACCESS` from accidentally sending messages when issuing `!help`.

- Fixed `DIVERT_TO_PRIVATE` on IRC.

- Fixed markdown rendering breaking with `GROUPCHAT_NICK_PREFIXED` enabled.

- Fixed `AttributeError` with `AUTOINSTALL_DEPS` enabled.

- IRC backend now cleanly disconnects from IRC servers instead of just cutting the connection.

- Text mode now displays the prompt beneath the log output

- Plugins which fail to install no longer remain behind, obstructing a new installation attempt


v4.0 Breaking changes
~~~~~~~~~~~~~~~~~~~~~

- The underlying implementation of Identifiers has been drastically refactored
  to be more clear and correct. This makes it a lot easier to construct Identifiers
  and send messages to specific people or rooms.

- The file format for `--backup` and `--restore` has changed between 3.x and 4.0
  On the v3.2 branch, backup can now backup using the new v4 format with `!backupv4` to
  make it possible to use with `--restore` on errbot 4.0.

A number of features which had previously been deprecated have now been removed.
These include:

- `configure_room` and `invite_in_room` in `XMPPBackend` (use the
  equivalent functions on the `XMPPRoom` object instead)

- The `--xmpp`, `--hipchat`, `--slack` and `--irc` command-line options
  from `errbot` (set a proper `BACKEND` in `config.py` instead).


v 4.0 Miscellaneous changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Version information is now specified in plugin `.plug` files instead of in
  the Python class of the plugin.

- Updated `!help` output, more similar to Hubot's help output (James O'Beirne and Sijis Aviles).

- XHTML-IM output can now be enabled on XMPP again.

- New `--version` flag on `errbot` (mr. Shu).

- Made `!log tail` admin only (Nicolas Sebrecht).

- Made the version checker asynchronous, improving startup times.

- Optionally allow bot configuration from groupchat

- `Message.type` is now deprecated in favor of `Message.is_direct` and `Message.is_group`.

- Some bundled dependencies have been refactored out into external dependencies.

- Many improvements have been made to the documention, both in docstrings internally as well
  as the user guide on the website at http://errbot.io.


Further info on identifier changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Person, RoomOccupant and Room are now all equal and can be used as-is to send a message
  to a person, a person in a Room or a Room itself.

The relationship is as follow:

.. image:: https://raw.githubusercontent.com/errbotio/errbot/master/docs/_static/arch/identifiers.png
   :target: https://github.com/errbotio/errbot/blob/master/errbot/backends/base.py

For example: A Message sent from a room will have a RoomOccupant as frm and a Room as to.

This means that you can now do things like:

- `self.send(msg.frm, "Message")`
- `self.send(self.query_room("#general"), "Hello everyone")`



.. v9.9.9 (leave that there so master doesn't complain)
