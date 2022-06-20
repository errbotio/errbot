Administration
==============

This document describes how to configure, administer and interact with errbot.


Configuration
-------------

There is a split between two types of configuration within errbot.
On the one hand there is "setup" information,
such as the (chat network) backend to use, storage selection
and other settings related to how errbot should run.
These settings are all configured through the `config.py` configuration file as explained in
:ref:`configuration <configuration>`.

The other type of configuration is the "runtime" configuration such as the plugin settings.
Plugins can be dynamically configured through chatting with the bot by using the :code:`!plugin config <plugin name>` command.

There are a few other commands which adjust the runtime configuration,
such as the :code:`!plugin blacklist <plugin>` command to unload and blacklist a specific plugin.

You can view a list of all these commands and their help documentation by using the built-in help function.


.. _builtin_help_function:

The built-in help function
^^^^^^^^^^^^^^^^^^^^^^^^^^

To get a list of all available commands, you can issue::

    !help

If you just wish to know more about a specific command you can issue::

    !help <command>


Installing plugins
------------------

Errbot plugins are typically published to and installed from `GitHub <http://github.com/>`_.
We periodically crawl GitHub for errbot plugin repositories and `publish the results <https://github.com/errbotio/errbot/wiki>`_ for people to browse.

You can have your bot display the same list of repos by issuing::

    !repos

Searching can be done by specifying one or more keywords,
for example::

    !repos search hello

To install a plugin from the list, issue::

    !repos install <name of plugin>

You aren't limited to installing public plugins though.
You can install plugins from any git repository you have access to,
whether public or private, hosted on GitHub, BitBucket or elsewhere.
The `!repos install` command can take any git URI as argument.

If you're unhappy with a plugin and no longer want it,
you can always uninstall a plugin again with::

    !repos uninstall <plugin>

You will probably also want to update your plugins periodically.
This can be done with::

    !repos update all


Dependencies
^^^^^^^^^^^^

Please pay attention when you install a plugin as it may have additional dependencies.
If the plugin contains a `requirements.txt` file then Errbot will automatically check the requirements listed within and warn you when you are missing any.

Additionally, if you set :code:`AUTOINSTALL_DEPS` to :code:`True` in your **config.py**, Errbot will use pip to install any missing dependencies automatically.
If you have installed Errbot in a virtualenv, this will run the equivalent of :code:`pip install -r requirements.txt`.
If no virtualenv is detected, the equivalent of :code:`pip install --user -r requirements.txt` is used to ensure the package(s) is/are only installed for the user running Err.


Extra plugin directory
^^^^^^^^^^^^^^^^^^^^^^

Plugins installed via the :code:`!repos` command are managed by errbot itself and stored inside the `BOT_DATA_DIR` you set in `config.py`.
If you want to manage your plugins manually for any reason then errbot allows you to load additional plugins from a directory you specify.
You can do so by specifying the setting `BOT_EXTRA_PLUGIN_DIR` in your `config.py` file.
See the :download:`config-template.py` file for more details.


.. _disabling_plugins:

Disabling plugins
-----------------

You have a number of options available to you if you need to disable a plugin for any reason.
Plugins can be temporarily disabled by using the :code:`!plugin deactivate <plugin name>` command, which deactivates the plugin until the bot is restarted (or activated again via :code:`!plugin activate <plugin name>`.

If you want to prevent a plugin from being loaded at all during bot startup, the :code:`!plugin blacklist <plugin name>` command may be used.

It's also possible to strip errbot down even further by disabling some of its core plugins which are otherwise activated by default.
You may for example want to this if you're building a very specialized bot for a specific purpose.

Disabling core plugins can be done by setting the `CORE_PLUGINS` setting in `config.py`.
For example, setting `CORE_PLUGINS = ()` would disable all of the core plugins which even removes the plugin and repository management commands described above.


.. _access_controls:

Restricting access
------------------

Errbot features a number of options to limit and restrict access to commands of your bot.
All of these are configured through the `config.py` file as explained in
:ref:`configuration <configuration>`.

The first of these is `BOT_ADMINS`, which sets up the administrators for your bot.
Some commands are hardcoded to be admin-only so the people listed here will be given access to those commands
(the users listed here will also receive warning messages generated by the :func:`~errbot.botplugin.BotPlugin.warn_admins` plugin function).

More advanced access controls can be set up using the `ACCESS_CONTROLS` and `ACCESS_CONTROLS_DEFAULT` options which allow you to set up sophisticated rules.

Access controls, allowing commands to be restricted to specific users/rooms.
Available filters (you can omit a filter or set it to None to disable it):

* `allowusers`: Allow command from these users only
* `denyusers`: Deny command from these users
* `allowrooms`: Allow command only in these rooms (and direct messages)
* `denyrooms`: Deny command in these rooms
* `allowargs`: Allow a command's argument from these users only
* `denyargs`: Deny a command's argument from these users
* `allowprivate`: Allow command from direct messages to the bot
* `allowmuc`: Allow command inside rooms

Rules listed in `ACCESS_CONTROLS_DEFAULT` are applied by default and merged with any commands found in `ACCESS_CONTROLS`.

The options allowusers, denyusers, allowrooms and denyrooms, allowargs, denyargs support unix-style globbing similar to `BOT_ADMINS`.

Command names also support unix-style globs and can optionally be restricted to a specific plugin by prefixing the command with the name of a plugin, separated by a colon. For example, `Health:status` will match the `!status` command of the `Health` plugin and `Health:*` will match all commands defined by the `Health` plugin.

.. note::
    The first command match found will be used so if you have overlapping patterns you must used an OrderedDict instead of a regular dict: https://docs.python.org/3/library/collections.html#collections.OrderedDict

Example::

    ACCESS_CONTROLS_DEFAULT = {} # Allow everyone access by default
    ACCESS_CONTROLS = {
        "status": {
            "allowrooms": ("someroom@conference.localhost",)
        },
        "about": {
            "denyusers": ("*@evilhost",),
            "allowrooms": ("room1@conference.localhost", "room2@conference.localhost")
        },
        "uptime": {"allowusers": BOT_ADMINS},
        "help": {"allowmuc": False},
        "ChatRoom:*": {"allowusers": BOT_ADMINS},
    }

The example :download:`config.py <config-template.py>` file contains this information about the format of these options.

If you don't like encoding access controls into the config file, a member of the errbot community has also created a `dynamic ACL module <https://github.com/shengis/err-profiles>`_ which can be administered through chat commands instead.

Another community solution allows LDAP groups to be checked for membership before allowing the command to be executed.  `LDAP ACL module <https://github.com/marksull/err-ldap>`_ is practical for managing large groups.  This module functions by decorating bot commands directly in the plugin code, which differs from configuration based ACLs.

.. note::
    Different backends have different formats to identify users.
    Refer to the backend-specific notes at the end of the :ref:`configuration <configuration>` chapter to see which format you should use.


Command filters
---------------

If our built-in access controls don't fit your needs, you can always create your own easily using *command filters*.
Command filters are functions which are called automatically by errbot whenever a user executes a command.
They allow the command to be allowed, blocked or even modified based on logic you implement yourself.
In fact, the restrictions enforced by `BOT_ADMINS` and `ACCESS_CONTROLS` above are implemented using a command filter themselves
so they can serve as a good :mod:`example <errbot.core_plugins.acls>` (be sure to view the module source).

You can add command filters to your bot by including them as part of any regular errbot plugin,
it will find and register them automatically when your plugin is loaded.
Any method in your plugin which is decorated by :func:`~errbot.cmdfilter` will then act as a command filter.


Overriding CommandNotFoundFilter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In some cases, it may be necessary to run other filters before the `CommandNotFoundFilter`.  Since the `CommandNotFoundFilter` is part of the core plugin list loaded by errbot, it can not be directly overridden from another plugin.
Instead, to prevent `CommandNotFoundFilter` from being called before other filters, exclude the `CommandNotFoundFilter` plugin in the `CORE_PLUGINS` setting in `config.py` and explicitly call the `CommandNotFoundFilter` function from the overriding filter.
