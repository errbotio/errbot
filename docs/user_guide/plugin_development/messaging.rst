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


Sending a message to a specific user or room
--------------------------------------------

Sometimes, you may wish to send a message to a specific user or a
groupchat, for example from pollers or on webhook events. You can do
this with :func:`~errbot.botplugin.BotPlugin.send`:

.. code-block:: python

    self.send(
        self.build_identifier("user@host.tld/resource"),
        "Boo! Bet you weren't expecting me, were you?",
    )

:func:`~errbot.botplugin.BotPlugin.send` requires a valid
:class:`~errbot.backends.base.Identifier` instance to send to.
:func:`~errbot.botplugin.BotPlugin.build_identifier`
can be used to build such an identifier.
The format(s) supported by `build_identifier` will differ depending on which backend you are using.
For example, on Slack it may support `#channel` and `@user`,
for XMPP it includes `user@host.tld/resource`, etc.


Templating
----------

It's possible to send `Markdown
<http://daringfireball.net/projects/markdown/>`_ responses using `Jinja2
<http://jinja.pocoo.org/>`_ templates.

To do this, first create a directory called *templates* in the
directory that also holds your plugin's *.plug* file.

Inside this directory, you can place Markdown templates (with a
*.md* extension) in place of the content you wish to show. For
example this *hello.md*:

.. code-block:: python

    Hello, {{name}}!

.. note::
    See the Jinja2 `Template Designer Documentation
    <http://jinja.pocoo.org/docs/templates/>`_ for more information on
    the available template syntax.

Next, tell Errbot which template to use by specifying the `template`
parameter to :func:`~errbot.decorators.botcmd` (leaving off the
*.md* suffix).

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

    class Hello(BotPlugin):
        @botcmd(template="hello")
        def hello(self, msg, args):
            """Say hello to someone"""
            response = self.get_template('hello.md').render(name=args)
            self.send(msg.frm, response)


Cards
-----

Errbot cards are a canned format for notifications. It is possible to use this format to map to some native format in
backends like Slack (Attachment) or Hipchat (Cards).

Similar to a `self.send()` you can use :func:`~errbot.botplugin.BotPlugin.send_card` to send a card.

The following code demonstrate the various available fields.

.. code-block:: python

    from errbot import BotPlugin, botcmd

    class Travel(BotPlugin):
        @botcmd
        def send_card(self, msg, args):
            """Say a card in the chatroom."""
            self.send_card(title='Title + Body',
                           body='text body to put in the card',
                           thumbnail='https://raw.githubusercontent.com/errbotio/errbot/master/docs/_static/err.png',
                           image='https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png',
                           link='http://www.google.com',
                           fields=(('First Key','Value1'), ('Second Key','Value2')),
                           color='red',
                           in_reply_to=msg)

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
                    mess.frm,
                    "What what somebody said cookie!?",
                )
