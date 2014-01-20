Plugin development
==================

.. note::
    These docs are mostly a direct copy of the
    `old documentation <https://github.com/gbin/err/wiki/plugin-dev/>`_ up
    on the wiki. A new guide is being worked on, but isn't complete enough
    yet to be published at this time.

Tips before you get started
----------------------------

Before you get started, you may want to check out the next few tips which can help
you set up a more effective development environment/workflow. None of this is
required though, so please feel free to skip ahead.

Add a development directory in the plugin searchpath
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Make a directory to host your new plugin or plugins and set it in config.py::

    BOT_EXTRA_PLUGIN_DIR = '/home/path/to/plugin/root'

Start the bot in test mode (optional but it helps)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can start the bot with the "-T" command line parameter.
It runs the bot in test mode, a kind of single user mode on pure console (no XMPP server involved here).

It will prompt you::

    $ err.py -T
    [...]
    INFO:Plugin activation done.
    Talk to  me >> _

Then you can enter all the available commands and it will trust you as an admin.
Combine it with the debug mode of an IDE and you have a super snappy environment to try out and debug your code.

Use our plugin skeleton
^^^^^^^^^^^^^^^^^^^^^^^

We've written a `minimal plugin <https://github.com/zoni/err-skeleton>`_ which shows
the basic layout of a simple plugin. Save yourself some time by using this template
as a starting point.

Writing a simple plugin
-----------------------

Let say you want to make an helloWorld plugin.
First define a class implementing :class:`~errbot.botplugin.BotPlugin` with a method
decorated by `@botcmd` as follows (save this file as *helloworld.py*)::

    from errbot import BotPlugin, botcmd

    class Hello(BotPlugin):
        """Example 'Hello, world!' plugin for Err"""

        @botcmd
        def hello(self, msg, args):
            """Say hello to the world"""
            return "Hello, world!"

Then you need to put some metadescription in a *.plug* file. Save the next file as
*helloworld.plug*:

.. code-block:: ini

    [Core]
    Name = HelloWorld
    Module = helloWorld

    [Documentation]
    Description = let's say hello !

Start the bot or restart it if it is already live with the command `!restart`.

.. note::
    Module must match the name of the python module your main class is

That's it!
You can check if the plugin correctly load with the **!status** command.
Then you can check if the hello command is correctly bound with **!help**.
Then you can try it: **!hello**

If something goes wrong to can inspect the last lines of the log instantly with **!log tail**

Returning multiple responses
----------------------------

Often, with commands that take a long time to run, you may want to be able to send
some feedback to the user that the command is progressing. Instead of using a single
`return` statement you can use `yield` statements for every line of output you wish
to send to the user.

For example, in the following example, the output will be "Going to sleep", followed
by a 10 second wait, followed by "Waking up".
::

    from errbot import BotPlugin, botcmd
    from time import sleep

    class PluginExample(BotPlugin):
        @botcmd
        def longcompute(self, mess, args):
            yield "Going to sleep"
            sleep(10)
            yield "Waking up"

Sending a message to a specific user or MUC
-------------------------------------------

Sometimes, you may wish to send a message to a specific user or a groupchat, for
example from pollers or on webhook events. You can do this with
:func:`~errbot.botplugin.BotPlugin.send`:

.. code-block:: python

    # To send to a user
    self.send(
        "user@host.tld/resource",
        "Boo! Bet you weren't expecting me, were you?",
        message_type="chat"
    )

    # Or to send to a MUC
    self.send(
        "conference.host.tld/room",
        "Boo! Bet you weren't expecting me, were you?",
        message_type="groupchat"
    )

Make err split the arguments for you
------------------------------------

With the `split_args_with argument` to `botcmd`, you can specify a delimiter of the
arguments and it will give you an array of strings instead of a string:

.. code-block:: python

    @botcmd(split_args_with=' ')
    def action(self, mess, args):
        # if you send it !action one two three
        # args will be ['one', 'two', 'three']

Subcommands
-----------

If you put an _ in the name of the function, err will create for you a subcommand.
It is useful to categorize a feature:

.. code-block:: python

    @botcmd
    def basket_add(self, mess, args):
        # it will respond to !basket add

    @botcmd
    def basket_remove(self, mess, args):
        # it will respond to !basket remove

.. note::
    It will still respond to !basket_add and !basket_remove as well

Version checking
----------------

You can enforce a minimal and maximal version of err if you know that your plugin won't be compatible outside the range.
You just have to define min_err_version and/or max_err_version as a property or field::

    from errbot import BotPlugin

    class PluginExample(BotPlugin):
        min_err_version = '1.2.2'
        [...]

.. note::
    The version is inclusive.
    It **must** be defined as a string with 3 numbers dotted like '1.3.0'

Allow the admin to configure your plugin from the chat
------------------------------------------------------

Err can keep a simple python object for the configuration of your plugin.
I avoids asking for the admin to edit *config.py*, restart the bot...

In order to enable this feature, you need to give a configuration template
(ie. a config example) by overriding the get_configuration_template method,
for example a plugin requesting a dictionary with 2 entries in there:

.. code-block:: python

    from errbot import BotPlugin

    class PluginExample(BotPlugin):
        def get_configuration_template(self):
            return {'ID_TOKEN': '00112233445566778899aabbccddeeff',
                    'USERNAME':'changeme'}

Then from the admin you will be able to request the default template with `!config PluginExample`.
Then it will instruct you to do a
`!config PluginExample {'ID_TOKEN' : '00112233445566778899aabbccddeeff', 'USERNAME':'changeme'}`
with the real values in there.

You will be able to recall the config that is set by issuing `!config PluginExample` again.

From within your code, your config will be in `self.config`:

.. code-block:: python

    @botcmd
    def mycommand(self, mess, args):
        # oh I need my TOKEN !
        token = self.config['ID_TOKEN'] # <- Note: this is already a real
                                        #    python dict here

Now the framework will do by default a strict check on structure and types or the config:
by default it will do only a BASIC check. You need to override it if you want to do more complex checks.
it will be called before the configure callback. Note if the config_template is None, it will never be called

It means recursively:
1. in case of a dictionary, it will check if all the entries and from the same type
are there and not more
2. in case of an array or tuple, it will assume array members of the same type of
first element of the template (no mix typed is supported)

If you need a more complex validation you need to override check_configuration:

.. code-block:: python

    def check_configuration(self, configuration):
        # ... and here check the configuration received through the
        # `configuration` parameter.
        # If you encounter a validation error you should throw a
        # `errbot.util.ValidationException`.


But be careful, you might want to be more defensive towards the user input to be sure the plugin will run with it.
For that, override the method configure.

.. warning::
    If you have no configuration set yet, it will pass you None as parameter. Be
    mindful of this situation.

.. note::
    Don't forget to call super() otherwise the framework will not store it.

For example::

    from errbot import BotPlugin

    class PluginExample(BotPlugin):
        def configure(self, configuration):
            if configuration: # if it is not configured ignore
                if type(configuration) != dict:
                    raise Exception('Wrong configuration type')
                if not configuration.has_key('ID_TOKEN') or not configuration.has_key('USERNAME'):
                    raise Exception('Wrong configuration type, it should contain ID_TOKEN and USERNAME')
                if len(configuration) > 2:
                    raise Exception('What else did you try to insert in my config ?')
            super(PluginExample, self).configure(configuration)

Implementing a callback to listen to every message in the chatroom
------------------------------------------------------------------

You can add a specific callback that will be called on any message sent on the chatroom.
It is useful to react at specific keywords even the the bot is not called explicitely with the ! commands::

    from errbot import BotPlugin

    class PluginExample(BotPlugin):
        def callback_message(self, conn, mess):
            if mess.getBody().find('cookie') != -1:
                self.send(
                    mess.getFrom(),
                    "What what somebody said cookie!?",
                    message_type=mess.getType()
                )

Make the bot poll for a specific function
-----------------------------------------

Simply register your polling function at activation time::

    from errbot import BotPlugin
    import logging

    class PluginExample(BotPlugin):
        def my_callback(self):
            logging.debug('I am called every minute')

        def activate(self):
            super(PluginExample, self).activate()
            self.start_poller(60, self.my_callback)

This is the simplest case. See Botplugin for added parameters, starting several pollers, stopping pollers etc ...

Specify the python compatibility of a plugin
--------------------------------------------

Since v2.0.0 Err is Python 3 compatible so you need to be able to specify on which
version of python your plugin can run for forward and backward compatibility.

In your .plug file you need to add a section Python with the entry Version in it
like this:


.. code-block:: ini

    [Core]
    Name = HelloWorld
    Module = helloWorld

    [Documentation]
    Description = let's say hello !

    [Python]
    Version = 2

The value of Version can be:

- **2** for Python 2 only plugin
- **2+** for Python 2 and 3 plugin
- **3** for Python 3 plugin

It is highly recommended to make your plugin compatible with both 2 and 3 for the
time being. The library `six <https://pypi.python.org/pypi/six/>`_ may help you
do that.
