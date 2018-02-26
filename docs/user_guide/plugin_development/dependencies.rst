Plugin Dependencies
===================

Sometimes you need to be able to share a plugin feature with another.
For example imagine you have a series of plugin configured the same way, you might
want to make them depend on a central plugin taking care of the configuration that would
share it with all the others.

Declaring dependencies
----------------------

If you want to be able to use a plugin from another, the later needs to be activated before the former.
You can ask Errbot to do so by adding a comma separated name list of the plugins your plugin is depending
on in the **Core** section of your plug file like this:

.. code-block:: ini

    [Core]
    Name = MyPlugin
    Module = myplugin
    DependsOn = OtherPlugin1, OtherPlugin2

Using dependencies
------------------

Once a dependent plugin has been declared, you can use it at soon as your plugin is activated.

.. code-block:: python

    from errbot import BotPlugin, botcmd

    class OtherPlugin1(BotPlugin):

        def activate(self):
            self.my_variable = 'hello'
            super().activate()


If you want to use it from MyPlugin:

.. code-block:: python

    from errbot import BotPlugin, botcmd

    class MyPlugin(BotPlugin):

        @botcmd
        def hello(self, msg, args):
            return self.get_plugin('OtherPlugin1').my_variable

Important to note: if you want to use a dependent plugin from within activate, you need to be in activated state, for example:

.. code-block:: python

    from errbot import BotPlugin, botcmd

    class MyPlugin(BotPlugin):

        def activate(self):
            super().activate()  # <-- needs to be *before* get_plugin
            self.other = self.get_plugin('OtherPlugin1')

        @botcmd
        def hello(self, msg, args):
            return self.other.my_variable


