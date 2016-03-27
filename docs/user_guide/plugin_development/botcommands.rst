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

If you put an _ in the name of the function, Errbot will create what
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


Argparse argument splitting
----------------------------

With the :func:`~errbot.decorators.arg_botcmd` decorator you can specify
a command's arguments in `argparse format`_. The decorator can be used multiple times, and each use adds a new argument to the command. The decorator can be passed any valid `add_arguments()`_ parameters.

.. _`argparse format`: https://docs.python.org/3/library/argparse.html
.. _`add_arguments()`: https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument

.. code-block:: python

    @arg_botcmd('first_name', type=str)
    @arg_botcmd('--last-name', dest='last_name', type=str)
    @arg_botcmd('--favorite', dest='favorite_number', type=int, default=42)
    def hello(self, mess, first_name=None, last_name=None, favorite_number=None):
        # if you send it !hello Err --last-name Bot
        # first_name will be 'Err'
        # last_name will be 'Bot'
        # favorite_number will be 42

.. note::
    * An argument's `dest` parameter is used as its kwargs key when your command is called.
    * `favorite_number` would be `None` if we removed `default=42` from the :func:`~errbot.decorators.arg_botcmd` call.



Commands using regular expressions
----------------------------------

In addition to the fixed commands created with the :func:`~errbot.decorators.botcmd`
decorator, Errbot supports an alternative type of bot function which can be triggered
based on a regular expression. These are created using the
:func:`~errbot.decorators.re_botcmd` decorator. There are two forms these can be
used, with and without the usual bot prefix.

In both cases, your method will receive the message object same as with a regular
:func:`~errbot.decorators.botcmd`, but instead of an `args` parameter, it takes
a `match` parameter which will receive an :class:`re.MatchObject`.

.. note::
    By default, only the first occurrence of a match is returned, even if it can
    match multiple parts of the message. If you specify `matchall=True`, you will
    instead get a list of :class:`re.MatchObject` items, containing all the
    non-overlapping matches that were found in the message.


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
            """Talk of cookies gives Errbot a craving..."""
            return "Somebody mentioned cookies? Om nom nom!"
