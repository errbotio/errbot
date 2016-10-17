.. _templates_advanced:

Advanced Template Usage
-----------------------

Override templates
==================

It's possible to specify custom templates for your installed plugins. This is
useful if you are installing a plugin from a remote repo and then want to only
change how it's messages are rendered in some way.

First set the directory where your custom templates are located:

.. code-block:: python

    TEMPLATES_EXTRA_DIR = '/var/lib/my-err-templates'

Inside this directory, add a sub-dir for each plugin you with to override, and
in this sub-dir place the templates you wish to override. Follow the target plugin
template naming to override a template:

.. code-block:: bash

    $ tree some_plugin
    some_plugin
    ├── templates
    │   └── hello.md
    ├── some_plugin.py
    └── some_plugin.plug

    $ tree /var/lib/my-err-templates
    my-err-templates
    └── SomePlugin
        └── hello.md


Manually sending messages
=========================

Instead of specifying the template in the ``botcmd` decorator, you can
call the :func:`~errbot.botplugin.BotPlugin.send_templated` method directly
to send the rendered template

.. code-block:: python

    from errbot import BotPlugin, botcmd
    from errbot.templating import tenv

    class Hello(BotPlugin):
        @botcmd
        def hello(self, msg, args):
            """Say hello to someone"""
            self.send_templated(msg.frm, 'hello', {'name': args})

It's also possible to use templates when using `self.send()`, but in
this case you will have to do the template rendering step yourself,
like so:

.. code-block:: python

    from errbot import BotPlugin, botcmd
    from errbot.templating import tenv

    class Hello(BotPlugin):
        @botcmd(template="hello")
        def hello(self, msg, args):
            """Say hello to someone"""
            response = tenv().get_template('hello.md').render(name=args)
            self.send(msg.frm, response)
