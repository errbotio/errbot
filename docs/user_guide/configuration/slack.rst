Slack backend configuration
===========================

This backend lets you connect to the
`Slack <https://slack.com/>`_ messaging service.
To select this backend,
set `BACKEND = 'Slack'`.


Account setup
-------------

You will need to have an account at Slack for the bot to use,
either a bot account (recommended) or a regular user account.

We will assume you're using a bot account for errbot,
which `may be created here <https://my.slack.com/services/new/bot>`_.
Make note of the **API Token** you receive as you will need it next.

With the bot account created on Slack,
you may configure the account in errbot
by setting up `BOT_IDENTITY` as follows::

    BOT_IDENTITY = {
        'token': 'xoxb-4426949411-aEM7...',
    }


Bot admins
----------

You can set `BOT_ADMINS` to configure which Slack users are bot administrators.
Make sure to include the `@` sign.
For example: `BOT_ADMINS = ('@gbin', '@zoni')`

Bot mentions using @
--------------------

To enable using the bot's name in `BOT_ALT_PREFIXES` for @mentions in Slack, you must use the bot's SlackID.

1. Find the bot's Slack ID. You can obtain this using Slack's [API tester](https://api.slack.com/methods/users.list) or by inspecting the errbot debug logs (by setting `BOT_LOG_LEVEL = logging.DEBUG`). It should look like `U023BECGF`.
2. Enter this ID in `BOT_ALT_PREFIXES` in the form: `<@ID_NUMBER>`. For the example above it would be `<@U023BECGF>`.

Channels/groups
---------------

If you're using a bot account you should set `CHATROOM_PRESENCE = ()`.
Bot accounts on Slack are not allowed to join/leave channels on their own
(they must be invited by a user instead)
so having any rooms setup in `CHATROOM_PRESENCE` will result in an error.

If you are using a regular user account for the bot
then you can set `CHATROOM_PRESENCE` to a list of channels and groups to join.

.. note::

    You may leave the value for `CHATROOM_FN` at its default
    as it is ignored by this backend.
