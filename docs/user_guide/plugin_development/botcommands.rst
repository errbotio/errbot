Advanced bot commands
=====================


Automatic argument splitting
----------------------------

With the `split_args_with` argument to :func:`~errbot.decorators.botcmd`,
you can specify a delimiter of the arguments and it will give you an
array of strings instead of a string:

.. code-block:: python

    @botcmd(split_args_with=None)
    def action(self, mess, args):
        # if you send it !action one two three
        # args will be ['one', 'two', 'three']

.. note::
    `split_args_with` behaves exactly like :func:`str.split`, therefore
    the value `None` can be used to split on any type of whitespace, such
    as multiple spaces, tabs, etc. This is recommended over `' '` for
    general use cases but you're free to use whatever argument you see
    fit.


Subcommands
-----------

If you put an _ in the name of the function, Err will create what
looks like a subcommand for you. This is useful to group commands
that belong to each other together.

.. code-block:: python

    @botcmd
    def basket_add(self, mess, args):
        # Will respond to !basket add
        pass

    @botcmd
    def basket_remove(self, mess, args):
        # Will respond to !basket remove
        pass

.. note::
    It will still respond to !basket_add and !basket_remove as well.


Commands using regular expressions
----------------------------------

In addition to the fixed commands created with the :func:`~errbot.decorators.botcmd`
decorator, Err supports an alternative type of bot function which can be triggered
based on a regular expression. These are created using the
:func:`~errbot.decorators.re_botcmd` decorator. There are two forms these can be
used, with and without the usual bot prefix.

In both cases, your method will receive the message object same as with a regular
:func:`~errbot.decorators.botcmd`, but instead of an `args` parameter, it takes
a `match` parameter which will receive an :class:`re.MatchObject`.


With a bot prefix
~~~~~~~~~~~~~~~~~

You can define commands that trigger based on a regular expression, but still
require a bot prefix at the beginning of the line, in order to create more
flexible bot commands. Here's an example of a bot command that lets people
ask for cookies:

.. code-block:: python

    from errbot import BotPlugin, re_botcmd

    class CookieBot(BotPlugin):
        """A cookiemonster bot"""

        @re_botcmd(pattern=r"^(([Cc]an|[Mm]ay) I have a )?cookie please\?$")
        def hand_out_cookies(self, msg, match):
            """
            Gives cookies to people who ask me nicely.

            This command works especially nice if you have the following in
            your `config.py`:

            BOT_ALT_PREFIXES = ('Err',)
            BOT_ALT_PREFIX_SEPARATORS = (':', ',', ';')

            People are then able to say one of the following:

            Err, can I have a cookie please?
            Err: May I have a cookie please?
            Err; cookie please?
            """
            yield "Here's a cookie for you, {}".format(msg.frm)
            yield "/me hands out a cookie."


Without a bot prefix
~~~~~~~~~~~~~~~~~~~~

It's also possible to trigger commands even when no bot prefix is specified,
by passing `prefixed=False` to the :func:`~errbot.decorators.re_botcmd`
decorator. This is especially useful if you want to trigger on specific
keywords that could show up anywhere in a conversation:

.. code-block:: python

    import re
    from errbot import BotPlugin, re_botcmd

    class CookieBot(BotPlugin):
        """A cookiemonster bot"""

        @re_botcmd(pattern=r"(^| )cookies?( |$)", prefixed=False, flags=re.IGNORECASE)
        def listen_for_talk_of_cookies(self, msg, match):
            """Talk of cookies gives Err a craving..."""
            return "Somebody mentioned cookies? Om nom nom!"
