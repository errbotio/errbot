Release history
===============


Version 1.4.1 (2012-07-13)
--------------------------
Bugs:

- corrected a vicious bug when you use metaclasses on plugins with botcmd decorator generated with parameters
- don't call any callback message if the message is from the chat history
- dependency problem with dnspython, it fixes the compatibility with google apps [Thx to linux techie https://github.com/linuxtechie]
- on repos updates, err now recheck the dependencies (you never know if they changed after the update)

Features:

- Added a new check_configuration callback now by default the configuration check is basic and no implementation has to be done on plugin side
- Warn the admins in case of command name clashes and fix them by prefixing the name of the plugin + -
- A brand new graphical mode so you can debug with images displayed etc ... (command line option -G) it requires pyside [thx to Paul Labedan https://github.com/pol51]
- A new !apropos command that search a term into the help descriptions [thx to Ben Van Daele https://github.com/benvd]
- Now the bot reconnects in case of bad internet connectivity [Thx to linux techie https://github.com/linuxtechie]
- The bot now supports a "remote chatroom relay" (relay all messages from a MUC to a list of users) on top of a normal relay (from a user to a list of MUC) 
     With this you can emulate a partychat mode.
- err-music [thx to Ben Van Daele https://github.com/benvd and thx to Tali Petrover https://github.com/atalyad]

Version 1.4.0 (2012-07-09)
--------------------------
Bugs:

- improved the detection of own messages
- automatic rejection if the configuration failed so it the plugin restart with a virgin config

Features:

- send a close match tip if the command is not found
- added a polling facility for the plugins
- added loads of plugins to the official repos: 
  err-coderwall     [thx to glenbot https://github.com/glenbot]
  err-nettools
  err-topgunbot     [thx to krismolendyke https://github.com/krismolendyke]
  err-diehardbot    [thx to krismolendyke https://github.com/krismolendyke]
  err-devops_borat  [thx to Vincent Alsteen https://github.com/valsteen]
  err-social
  err-rssfeed       [thx to Tali Petrover https://github.com/atalyad]
  err-translate     [thx to Ben Van Daele https://github.com/benvd]
  err-tourney

Version 1.3.1 (2012-07-02)
--------------------------
Bugs:

- nicer warning message in case of public admin command

Features:

- added a warn_admins api for the plugins to warn the bot admins in case of serious problem
- added err-tv in the official repos list
- added an automatic version check so admins are warned if a new err is out
- now if a repo has a standard requirements.txt it will be checked upon to avoid admins having to dig in the logs (warning: it added setuptools as a new dependency for err itself)

Version 1.3.0 (2012-06-26)
--------------------------
Bugs:

- Security fix : the plugin directory permissions were too lax. Thx to Pinkbyte (Sergey Popov)
- Corrected a bug in the exit of test mode, the shelves could loose data
- Added a userfriendly git command check to notify if it is missing

Features:

- Added a version check: plugins can define min_err_version and max_err_version to notify their compatibility
- Added an online configuration of the plugins. No need to make your plugin users hack the config.py anymore ! just use the command !config
- Added a minimum Windows support.

Version 1.2.2 (2012-06-21)
--------------------------
Bugs:

- Corrected a problem when executing it from the dev tree with ./scripts/err.py
- Corrected the python-daemon dependency
- Corrected the encoding problem from the console to better match what the bot will gives to the plugins on a real XMPP server
- Corrected a bug in the python path for the BOT_EXTRA_PLUGIN_DIR setup parameter

Features:

- Added a dictionary mixin for the plugins themselves so you can access you data directly with self['entry']
- admin_only is now a simple parameter of @botcmd
- Implemented the history commands : !history !! !1 !2 !3

Version 1.2.1 (2012-06-16)
--------------------------
Bugs:

- Corrected a crash if the bot could not contact the server

Features:

- Added a split_args_with to the botcmd decorator to ease the burden of parsing args on the plugin side (see https://github.com/gbin/err/wiki/plugin-dev)
- Added the pid, uid, gid parameters to the daemon group to be able to package it on linux distributions


Version 1.2.0 (2012-06-14)
--------------------------
Bugs:

- Don't nag the user for irrelevant settings from the setting-template
- Added a message size security in the framework to avoid getting banned from servers when a plugin spills too much

Features:

- Added a test mode (-t) to ease plugin development (no need to have XMPP client / server to install and connect to in order to test the bot)
- Added err-reviewboard a new plugin by Glen Zangirolam https://github.com/glenbot to the repos list
- Added subcommands supports like the function log_tail will match !log tail [args]

Version 1.1.1 (2012-06-12)
--------------------------
Bugs:

- Fixed the problem updating the core + restart
- Greatly improved the reporting in case of configuration mistakes.
- Patched the presence for a better Hipchat interop.

Version 1.1.0 (2012-06-10)
--------------------------
Features:

- Added the !uptime command
- !uninstall doesn't require a full restart anymore
- !update a plugin doesn't require a full restart anymore
- Simplified the usage of the asynchronous self.send() by stripping the last part of the JID for chatrooms
- Improved the !restart feature so err.py is standalone now (no need to have a err.sh anymore)
- err.py now takes 2 optional parameters : -d to daemonize it and -c to specify the location of the config file

Version 1.0.4 (2012-06-08)
--------------------------
- First real release, fixups for Pypi compliance.
