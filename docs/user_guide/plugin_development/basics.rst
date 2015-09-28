Hello, world!
=============

On the :doc:`homepage </index>`, we showed you the following *"Hello
world!"* plugin as an example:

.. code-block:: python

    from errbot import BotPlugin, botcmd

    class HelloWorld(BotPlugin):
        """Example 'Hello, world!' plugin for Err"""

        @botcmd
        def hello(self, msg, args):
            """Say hello to the world"""
            return "Hello, world!"

In this chapter, you will learn exactly how this plugin works.

I will assume you've configured the `BOT_EXTRA_PLUGIN_DIR` as
described in the previous chapter. To get started, create a new,
empty directory named `HelloWorld` inside this directory.

Create a new file called `helloworld.py` inside the `HelloWorld`
directory you just created. This file contains all the logic for your
plugin, so copy and paste the above example code into it.

Anatomy of a BotPlugin
----------------------

Although this plugin is only 9 lines long, there is already a lot of
interesting stuff going on here. Lets go through it step by step.

.. code-block:: python

    from errbot import BotPlugin, botcmd

This should be pretty self-explanatory. Here we import the
:class:`~errbot.botplugin.BotPlugin` class and the
:func:`~errbot.decorators.botcmd` decorator. These let us build a
class that can be loaded as a plugin and allow us to mark methods of
that class as bot commands.

.. code-block:: python

    class HelloWorld(BotPlugin):
        """Example 'Hello, world!' plugin for Err"""

Here we define the class that makes up our plugin. The name of your
class, `HelloWorld` in this case, is what will make up the name of
your plugin. This name will be used in commands such as `!status`,
`!load` and `!unload`

The class' docstring is used to automatically populate the built-in
command documentation. It will be visible when issuing the `!help`
command.

.. warning::
    A plugin should only ever contain a single class inheriting from  :class:`~errbot.botplugin.BotPlugin`

.. code-block:: python

        @botcmd
        def hello(self, msg, args):
            """Say hello to the world"""
            return "Hello, world!"

This method, `hello`, is turned into a bot command which can be
executed because it is decorated with the
:func:`~errbot.decorators.botcmd` decorator. Just as with the class
docstring above, the docstring here is used to populate the `!help`
command.

The name of the method, `hello` in this case, will be used as the
name of the command. That means this method creates the `!hello`
command.

.. note::
    The method name must comply with the usual Python naming
    conventions for `identifiers <https://docs.python.org/release/2.7.8/reference/lexical_analysis.html#identifiers>`_ 
    , that is, they may not begin with a digit (like ``911`` but only with a letter or underscore, so ``_911`` would work)
    and cannot be any of the `reserved keywords <https://docs.python.org/release/2.7.8/reference/lexical_analysis.html#keywords>`_
    such as ``pass`` (instead use ``password``) etc.

.. note::
    Should multiple plugins define the same command, they will be
    dynamically renamed (by prefixing them with the plugin name) so
    that they no longer clash with each other.

If we look at the function definition, we see it takes two parameters,
`msg` and `args`. The first is a :class:`~errbot.backends.base.Message`
object, which represents the full message object received by Err. The
second is a string (or a list, if using the `split_args_with`
parameter of :func:`~errbot.decorators.botcmd`) with the arguments
passed to the command.

For example, if a user were to say `!hello Mister Err`, `args` would
be the string `"Mister Err"`.

Finally, you can see we return with the string `Hello, world!`. This
defines the response that Err should give. In this case, it makes all
executions of the `!hello` command return the message *Hello, world!*.

.. note::
    If you return `None`, Err will not respond with any kind of
    message when executing the command.


Plugin metadata
---------------

We have our plugin itself ready, but if you start the bot now, you'll
see it still won't load your plugin. What gives?

As it turns out, you need to supply a file with some meta-data
alongside your actual plugin file. This is a file that ends with the
extension `.plug` and it is used by Err to identify and load plugins.

Lets go ahead and create ours. Place the following in a file called
`helloworld.plug`:

.. code-block:: ini

    [Core]
    Name = HelloWorld
    Module = helloworld

    [Python]
    Version = 2+

    [Documentation]
    Description = Example "Hello, world!" plugin

.. note::
    This INI-style file is parsed using the Python `configparser
    <https://docs.python.org/3/library/configparser.html>`_ class.
    Make sure to use a `valid
    <https://docs.python.org/3/library/configparser.html#supported-ini-file-structure>`_
    file structure.

Lets look at what this does. We see three sections, `[Core]` ,
`[Python]` and `[Documentation]`. The `[Core]` section is what tells
Err where it can actually find the code for this plugin.

The key `Module` should point to a module that Python can find and
import. Typically, this is the name of the file you placed your code
in with the `.py` suffix removed.

The key `Name` should be identical to the name you gave to the class
in your plugin file, which in our case was `HelloWorld`. While these
names can differ, doing so is not recommended.

.. note::
    If you're wondering why you have to specify it when it should be
    the same as the class name anyway, this has to do with technical
    limitations that we won't go into here.

While the items from the `[Core]` section tell Err where to find the
code, the `[Python]` section tells Err which versions of Python your
plugin is compatible with. As you are probably aware, Err runs on
both 2.7 and 3.\ *x* versions of Python, but maintaining compatibilty
to both can take some time and effort however. Effort you might not
want to put into your own plugins.

The `Version` key allows you to specify which versions of Python your
plugin works on. Supported values are `2` for Python 2, `3` for
Python 3 and `2+` for both Python 2 and 3.

The `[Documentation]` section will be explained in more detail
further on in this guide, but you should make sure to at least have
the `Description` item here with a short description of your plugin.

Wrapping up
-----------

If you've followed along so far, you should now have a working
*Hello, world!* plugin for Err. If you start your bot, it should load
your plugin automatically. 

You can verify this by giving the `!status` command, which should
respond with something like the following::

    Yes I am alive...
    With these plugins (A=Activated, D=Deactivated, B=Blacklisted, C=Needs to be configured):
    [A] ChatRoom
    [A] HelloWorld
    [A] VersionChecker
    [A] Webserver

If you don't see your plugin listed or it shows up as unloaded, make
sure to start your bot with *DEBUG*-level logging enabled and pay
close attention to what it reports. You will most likely see an error
being reported somewhere along the way while Err starts up.


Next steps
----------

You now know enough to create very simple plugins, but we have barely
scratched the surface of what Err can do. The rest of this guide will
be a recipe-style set of topics that cover all the advanced features
Err has to offer.
