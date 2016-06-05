Telegram backend configuration
==============================

This backend lets you connect to
`Telegram Messenger <https://telegram.org/>`_.
To select this backend,
set `BACKEND = 'Telegram'`.

Extra Dependencies
------------------

You need to install this dependency before using Errbot with Telegram::

      pip install python-telegram-bot

Account setup
-------------

You will first need to create a bot account on Telegram
for errbot to use.
You can do this by talking to `@BotFather <https://telegram.me/botfather>`_
(see also: `BotFather <https://core.telegram.org/bots#botfather>`_).
Make sure you take note of the token you receive,
you'll need it later.

Once you have created a bot account on Telegram
you may configure the account in errbot
by setting up `BOT_IDENTITY` as follows::

    BOT_IDENTITY = {
        'token': '103419016:AAbcd1234...',
    }


Bot admins
----------

You can setup `BOT_ADMINS` to designate which users are bot admins,
but on Telegram this is a little more difficult to do.
In order to configure a user here
you will have to obtain their user ID.

The easiest way to do this is to start the bot with no `BOT_ADMINS` defined.
Then, have the user for which you want to obtain the user ID message the bot
and send it the `!whoami` command.

This will print some info about the user, including the following:
`string representation is '123669037'`.
It is this number that needs to be filled in for `BOT_ADMINS`.
For example: `BOT_ADMINS = (123669037,)`


Rooms
-----

Telegram does not expose any room management to bots.
As a group admin, you will have to add a bot to a groupchat
at which point it will automatically join.

By default the bot will not receive any messages
which makes interacting with it in a groupchat difficult.

To give the bot access to all messages in a groupchat,
you can use the `/setprivacy` command when talking to
`@BotFather <https://core.telegram.org/bots#botfather>`_.

.. note::

    Because Telegram does not support room management,
    you must set `CHATROOM_PRESENCE = ()`
    otherwise you will see errors.


Slash commands
--------------

Telegram treats messages which
`start with a / <https://core.telegram.org/bots#commands>`_
differently,
which is designed specifically for interacting with bots.

We therefor suggest setting `BOT_PREFIX = '/'` to take advantage of this.
