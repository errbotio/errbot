Slack backend configuration
===========================

This backend lets you connect to the
`Slack <https://slack.com/>`_ messaging service.
To select this backend,
set `BACKEND = 'Slack'`.

Extra Dependencies
------------------

You need to install this dependency before using Errbot with Slack::

      pip install slackclient

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


Proxy setup
-------------

In case you need to use a Proxy to connect to Slack,
you can set the proxies with the token config.

    BOT_IDENTITY = {
        'token': 'xoxb-4426949411-aEM7...',
        'proxies': {'http': 'some-http-proxy', 'https': 'some-https-proxy'}
    }


Bot admins
----------

You can set `BOT_ADMINS` to configure which Slack users are bot administrators.
Make sure to include the `@` sign::

    BOT_ADMINS = ('@gbin', '@zoni')


Bot mentions using @
--------------------

To enable using the bot's name in `BOT_ALT_PREFIXES` for @mentions in Slack, simply add the bot's name as follows::

    BOT_ALT_PREFIXES = ('@botname',)


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


Message size limit
------------------

As of the 12th August 2018 the Slack API has a message limit size of 40,000 characters.  Messages
larger than 40,000 will be truncated by Slack's API.  Errbot includes the functionality to split
messages larger than 40,000 characters into multiple parts.  To reduce the message limit size, set the
`MESSAGE_SIZE_LIMIT` variable in the configuration file.  Errbot will use the smallest value between
the default 40,000 and `MESSAGE_SIZE_LIMIT`.

#MESSAGE_SIZE_LIMIT = 1000
