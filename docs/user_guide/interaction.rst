Interacting with the Bot
========================

After starting Err, you should add the bot to your buddy list if you haven't already.
You can now send commands directly to the bot, or issue commands in a chatroom that
the bot has also joined.

.. _builtin_help_function:

Accessing the built-in help function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To get a list of all available commands, you can issue::

    !help full

If you just wish to know more about a specific command you can issue::

    !help command

Managing plugins
^^^^^^^^^^^^^^^^^

To get a list of public plugin repos you can issue::

    !repos

To install a plugin from this list, issue::

    !repos install <name of plugin>

You can always uninstall a plugin again with::

    !repos uninstall <plugin>

You will probably want to update your plugins periodically. This can be done with::

    !repos update all

.. note::
    Please pay attention when you install a plugin, it may have additional
    dependencies. If the plugin contains a `requirements.txt` file then Err
    wil automatically check the requirements listed within and warn you when
    you are missing any.
