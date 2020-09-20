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

You can set `BOT_ADMINS` to configure which Slack users are bot administrators,
using either Slack user IDs, or usernames.

User IDs are strongly encouraged as they are immutable and unique per user. You
can find a given user's user ID by opening their profile, and then clicking on
"More" and then "Copy member ID." User IDs always begin with the letter 'U'::

    BOT_ADMINS = ('U01AKS5RT1T', 'U01A872QUQP')

Alternatively, you can use usernames for convenience. Be aware that Slack users
can change their usernames, and it's even possible for multiple users to have
the same username, making them less secure then user IDs. Make sure to include
the `@` sign::

    BOT_ADMINS = ('@gbin', '@zoni')

Note that you cannot mix user IDs and usernames. They must all be of the same
type as determined by the first admin user::

    BOT_ADMINS = ('U01AKS5RT1T', '@gbin') # Throws exception


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
