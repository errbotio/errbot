Release history
===============

Version 1.1.2 (2012-06-)
--------------------------
Don't nag the user for irrelevant settings from the setting-template
Added a message size security in the framework to avoid getting banned from servers when a plugin spills too much
Added subcommands supports like the function log_tail will match !log tail [args]
Added a test mode (-t) to ease plugin development (no need to have XMPP client / server to install and connect to in order to test the bot)

Version 1.1.1 (2012-06-12)
--------------------------

Fixed the problem updating the core + restart
Greatly improved the reporting in case of configuration mistakes.
Patched the presence for a better Hipchat interop.

Version 1.1.0 (2012-06-10)
--------------------------

Added the !uptime command
!uninstall doesn't require a full restart anymore
!update a plugin doesn't require a full restart anymore
Simplified the usage of the asynchronous self.send() by stripping the last part of the JID for chatrooms
Improved the !restart feature so err.py is standalone now (no need to have a err.sh anymore)
err.py now takes 2 optional parameters : -d to daemonize it and -c to specify the location of the config file

Version 1.0.4 (2012-06-08)
--------------------------

First real release, fixups for Pypi compliance.
