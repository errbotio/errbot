Configuration
=============

Plugin configuration through the built-in `!config` command
-----------------------------------------------------------

Err can keep a simple python object for the configuration of your
plugin. This avoids the need for admins to configure settings in
some kind of configuration file, instead allowing configuration to
happen directly through chat commands.

In order to enable this feature, you need to provide a configuration
template (ie. a config example) by overriding the
:meth:`~errbot.botplugin.BotPlugin.get_configuration_template`
method. For example, a plugin might request a dictionary with 2
entries:

.. code-block:: python

    from errbot import BotPlugin

    class PluginExample(BotPlugin):
        def get_configuration_template(self):
            return {'ID_TOKEN': '00112233445566778899aabbccddeeff',
                    'USERNAME':'changeme'}

With this in place, an admin will be able to request the default
configuration template with `!config PluginExample`. He or she could
then give the command
`!config PluginExample {'ID_TOKEN' : '00112233445566778899aabbccddeeff', 'USERNAME':'changeme'}`
to enable that configuration.

It will also be possible to recall the configuration template, as
well as the config that is actually set, by issuing `!config
PluginExample` again.

Within your code, the config that is set will be in `self.config`:

.. code-block:: python

    @botcmd
    def mycommand(self, mess, args):
        # oh I need my TOKEN !
        token = self.config['ID_TOKEN']

.. warning::
    If there is no configuration set yet, `self.config` will be
    `None`.


Using custom configuration checks
---------------------------------

By default, Err will check the supplied configuration against the
configuration template, and raise an error if the structure of the
two doesn't match.

You need to override the :meth:`~errbot.botplugin.BotPlugin.check_configuration`
method if you wish do some other form of configuration validation.
This method will be called automatically when an admin configures
your plugin with the `!config` command.


.. warning::
    If there is no configuration set yet, it will pass `None` as
    parameter. Be mindful of this situation.
