Dynamic plugins (advanced)
==========================

Sometimes the list of commands the bot wants to expose is not known at
plugin development time.

For example, you have a remote service with commands that can
be set externally.

This feature allows you to define and update on the fly plugins and their
available commands.


Defining new commands
---------------------

You can create a commands from scratch with :class:`~errbot.Command`. By default it will be a :func:`~errbot.botcmd`.

.. code-block:: python

    # from a lambda
    my_command1 = Command(lambda plugin, msg, args: 'received %s' % msg, name='my_command', doc='documentation of my_command')

    # or from a function
    def my_command(plugin, msg, args):
        """
        documentation of my_command.
        """
        return 'received %s' % msg

    my_command2 = Command(my_command)

.. note::
    the function will by annotated by a border effect, be sure to use a local function if you want to derive commands
    for the same underlying function.


Registering the new plugin
--------------------------

Once you have your series of Commands defined, you can package them in a plugin and expose them on errbot with :func:`~errbot.BotPlugin.create_dynamic_plugin`.

.. code-block:: python

    # from activate, another bot command, poll etc.
    self.create_dynamic_plugin('my_plugin', (my_command1, my_command2))

.. note::
    It will still respond to !basket_add and !basket_remove as well.


Refreshing a plugin
-------------------

You need to detroy and recreate the plugin to refresh its commands.

.. code-block:: python

    self.destroy_dynamic_plugin('my_plugin')
    self.create_dynamic_plugin('my_plugin', (my_command1, my_command2, my_command3))


Customizing the type of commands and parameters
-----------------------------------------------

You can use other type of commands by specifying cmd_type and pass them parameters with cmd_args and cmd_kwargs.

.. code-block:: python

    # for example a botmatch
    re1 = Command(lambda plugin, msg, match: 'fffound',
                  name='ffound',
                  cmd_type=botmatch,
                  cmd_args=(r'^.*cheese.*$',)) 

    # or a split_args_with
    saw = Command(lambda plugin, msg, args: '+'.join(args),
                  name='splitme',
                  cmd_kwargs={'split_args_with': ','})
