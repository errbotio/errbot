IRC backend configuration
=========================

This backend lets you connect to any IRC server.
To select this backend,
set `BACKEND = 'IRC'`.


Account setup
-------------

Configure the account by setting up `BOT_IDENTITY` as follows::

    BOT_IDENTITY = {
        'nickname' : 'err-chatbot',
        # 'username' : 'err-chatbot',    # optional, defaults to nickname if omitted
        # 'password' : None,             # optional
        'server' : 'irc.freenode.net',
        # 'port': 6667,                  # optional
        # 'ssl': False,                  # optional
        # 'ipv6': False,                 # optional
        # 'nickserv_password': None,     # optional

        ## Optional: Specify an IP address or hostname (vhost), and a
        ## port, to use when making the connection. Leave port at 0
        ## if you have no source port preference.
        ##    example: 'bind_address': ('my-errbot.io', 0)
        # 'bind_address': ('localhost', 0),
    }

You will at a minimum need to set the correct values for `nickname` and `server` above.
The rest of the options can be left commented,
but you may wish to set some of them.


Bot admins
----------

You can set `BOT_ADMINS` to configure which IRC users are bot administrators.
For example: `BOT_ADMINS = ('gbin!gbin@*', '*!*@trusted.host.com')`

.. note::

    The default syntax for users on IRC is `{nick}!{user}@{host}` but this can
    be changed by adjusting the `IRC_ACL_PATTERN` setting.


Channels
--------

If you want the bot to join a certain channel when it starts up
then set `CHATROOM_PRESENCE` with a list of channels to join.
For example: `CHATROOM_PRESENCE = ('#errbotio',)`

.. note::

    You may leave the value for `CHATROOM_FN` at its default
    as it is ignored by this backend.


Flood protection
----------------

Many IRC servers have floop protection enabled,
which means the bot will get kicked out of a channel
when sending too many messages
in too short a time.

Errbot has a built-in message ratelimiter to avoid this situation.
You can enable it by setting `IRC_CHANNEL_RATE` and `IRC_PRIVATE_RATE`
to ratelimit channel and private messages, respectively.

The value for these options is a (floating-point) number of seconds to wait
between each message it sends.


Rejoin on kick/disconnect
-------------------------

Errbot won't rejoin a channel by default
when getting kicked out of one.
If you want the bot to rejoin channels on kick,
you can set `IRC_RECONNECT_ON_KICK = 5`
(to join again after waiting 5 seconds).

Similarly, to rejoin channels after being disconnected from the server
you may set `IRC_RECONNECT_ON_DISCONNECT = 5`.
