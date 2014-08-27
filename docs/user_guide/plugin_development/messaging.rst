Messaging
=========


Returning multiple responses
----------------------------

Often, with commands that take a long time to run, you may want to
be able to send some feedback to the user that the command is
progressing. Instead of using a single `return` statement you can
use `yield` statements for every line of output you wish to send to
the user.

For example, in the following example, the output will be "Going to
sleep", followed by a 10 second wait, followed by "Waking up".

.. code-block:: python

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

Sometimes, you may wish to send a message to a specific user or a
groupchat, for example from pollers or on webhook events. You can do
this with :func:`~errbot.botplugin.BotPlugin.send`:

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


Templating
----------

It's possible to send `XHTML-IM
<http://xmpp.org/extensions/xep-0071.html>`_ responses using `Jinja2
<http://jinja.pocoo.org/>`_ templates.

To do this, first create a directory called *templates* in the
directory that also holds your plugin's *.plug* file.

Inside this directory, you can place XHTML-IM templates (with a
*.html* extension) that extend `base.html` and contain a block
called `body` in place of the content you wish to show. For example
this *hello.html*:

.. code-block:: html

    {% extends "base.html" %}
    {% block body %}
    <p style='font-weight:bold'>Hello, {{name}}!</p>
    {% endblock %}

.. note::
    See the Jinja2 `Template Designer Documentation
    <http://jinja.pocoo.org/docs/templates/>`_ for more information on
    the available template syntax.

Next, tell Err which template to use by specifying the `template`
parameter to :func:`~errbot.decorators.botcmd` (leaving off the
*.html* suffix).

Finally, instead of returning a string, return a dictionary where
the keys refer to the variables you're substituting inside the
template (`{{name}}` in the above template example):

.. code-block:: python

    from errbot import BotPlugin, botcmd

    class Hello(BotPlugin):
        @botcmd(template="hello")
        def hello(self, msg, args):
            """Say hello to someone"""
            return {'name': args}

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
            response = tenv().get_template('hello.html').render(name=args)
            self.send(msg.frm, response, message_type=msg.type)

.. note::
    In both cases a plain-text version of your template is automatically
    generated for clients and back-ends that do not support XHTML-IM.


Trigger a callback with every message received
----------------------------------------------

It's possible to add a callback that will be called on every message
sent either directly to the bot, or to a chatroom that the bot is
in:

.. code-block:: python

    from errbot import BotPlugin

    class PluginExample(BotPlugin):
        def callback_message(self, mess):
            if mess.body.find('cookie') != -1:
                self.send(
                    mess.from,
                    "What what somebody said cookie!?",
                    message_type=mess.type
                )
