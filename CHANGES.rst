v6.1.7 (unreleased)
-------------------

features:

- core: Add support for python3.9 (#1477)
- chore: Allow dependabot to check GitHub actions weekly (#1464)
- chore: Add Dockerfile (#1482)

fixes:

- core: AttributeError on Blacklisted plugins (#1369)
- chore: Remove travis configuration (#1478)
- chore: minor code cleanup (#1465)
- chore: Use black codestyle (#1457, #1485)
- chore: Use twine to check dist (#1485)
- chore: remove codeclimate and eslint configs (#1490)

v6.1.6 (2020-11-16)
-------------------

features:

- core: Update code to support markdown 3 (#1473)

fixes:

- backends: Set email property as non-abstract (#1461)
- SlackRTM: username to userid method signature (#1458)
- backends: AttributeError in callback_reaction (#1467)
- docs: webhook examples (#1471)
- cli: merging configs with unknown keys (#1470)
- plugins: Fix error when plugin plug file is missing description (#1462)
- docs: typographical issues in setup guide (#1475)
- refactor: Split changelog by major versions (#1474)

v6.1.5 (2020-10-10)
-------------------

features:

-  XMPP: Replace sleekxmpp with slixmpp (#1430)
-  New callback for reaction events (#1292)
-  Added email property foriPerson object on all backends (#1186, #1456)
-  chore: Add github actions (#1455)

fixes:

-  Slack: Deprecated method calls (#1432, #1438)
-  Slack: Increase message size limit. (#1333)
-  docs: Remove Matrix backend link (#1445)
-  SlackRTM: Missing 'id\_' in argument (#1443)
-  docs: fixed rendering with double hyphens (#1452)
-  cli: merging configs via ``--storage-merge`` option (#1450)

v6.1.4 (2020-05-15)
-------------------

fixes:

-  403 error when fetching plugin repos index (#1425)

v6.1.3 (2020-04-19)
-------------------

features:

-  Add security linter (#1314)
-  Serve version.json on errbot.io and update version checker plugin (#1400)
-  Serve repos.json on errbot.io (#1403, #1406)
-  Include SlackRTM backend (beta) (#1416)

fixes:

-  Make plugin name clashes deterministic (#1282)
-  Fix error with Flows missing descriptions (#1405)
-  Fix ``!repos update`` object attribute error (#1410)
-  Fix updating remove repos using ``!repos update`` (#1413)
-  Fix deprecation warning (#1423)
-  Varios documentation fixes (#1404, #1411, #1415)

v6.1.2 (2019-12-15)
-------------------

fixes:

-  Add ability to re-run –init safely (#1390)
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
-  Fix #1360 Cast pathlib.Path objects to strings for use with sys.path
   (#1361)

v6.1.1 (2019-06-22)
-------------------

fixes:

-  Installation using wheel distribution on python 3.6 or older

v6.1.0 (2019-06-16)
-------------------

features:

-  Use python git instead of system git binary (#1296)

fixes:

-  ``errbot -l`` cli error (#1315)
-  Slack backend by pinning slackclient to supported version (#1343)
-  Make –storage-merge merge configs (#1311)
-  Exporting values in backup command (#1328)
-  Rename Spark to Webex Teams (#1323)
-  Various documentation fixes (#1310, #1327, #1331)

v6.0.0 (2019-03-23)
-------------------

features:

-  TestBot: Implement inject_mocks method (#1235)
-  TestBot: Add multi-line command test support (#1238)
-  Added optional room arg to inroom
-  Adds ability to go back to a previous room
-  Pass telegram message id to the callback

fixes:

-  Remove extra spaces in uptime output
-  Fix/backend import error messages (#1248)
-  Add docker support for installing package dependencies (#1245)
-  variable name typo (#1244)
-  Fix invalid variable name (#1241)
-  sanitize comma quotation marks too (#1236)
-  Fix missing string formatting in "Command not found" output (#1259)
-  Fix webhook test to not call fixture directly
-  fix: arg_botcmd decorator now can be used as plain method
-  setup: removing dnspython
-  pin markdown <3.0 because safe is deprecated

v6.0.0-alpha (2018-06-10)
-------------------------

major refactoring:

-  Removed Yapsy dependency
-  Replaced back Bottle and Rocket by Flask
-  new Pep8 compliance
-  added Python 3.7 support
-  removed Python 3.5 support
-  removed old compatibility cruft
-  ported formats and % str ops to f-strings
-  Started to add field types to improve type visibility across the codebase
-  removed cross dependencies between PluginManager & RepoManager

fixes:

-  Use sys.executable explicitly instead of just 'pip' (thx Bruno Oliveira)
-  Pycodestyle fixes (thx Nitanshu)
-  Help: don't add bot prefix to non-prefixed re cmds (#1199) (thx Robin Gloster)
-  split_string_after: fix empty string handling (thx Robin Gloster)
-  Escaping bug in dynamic plugins
-  botmatch is now visible from the errbot module (fp to Guillaume Binet)
-  flows: hint boolean was not forwarded
-  Fix possible event without bot_id (#1073) (thx Roi Dayan)
-  decorators were working only if kwargs were empty
-  Message.clone was ignoring partial and flows

features:

-  partial boolean to flag partial mesages (thx Meet Mangukiya)
-  Slack: room joined callback (thx Jeremy Kenyon)
-  XMPP: real_jid to get the jid the users logged in (thx Robin Gloster)
-  The callback order set in the config is not globally respected
-  Added a default parameter to the storage context manager

.. v9.9.9 (leave that there so master doesn't complain)
