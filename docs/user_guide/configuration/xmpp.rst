XMPP backend configuration
==========================

This backend lets you connect to any Jabber/XMPP server.
To select this backend,
set `BACKEND = 'XMPP'`.


Account setup
-------------

You must manually register an XMPP account for the bot
on the server you wish to use.
Errbot does not support XMPP registration itself.

Configure the account by setting up `BOT_IDENTITY` as follows::

    BOT_IDENTITY = {
        'username': 'err@server.tld',  # The JID of the user you have created for the bot
        'password': 'changeme',        # The corresponding password for this user
        # 'server': ('host.domain.tld',5222), # server override
    }

By default errbot will query SRV records for the correct XMPP server and port,
which should work with a properly configured server.

If your chosen XMPP server does not have correct SRV records setup,
you can also set the `server` key to override this.

A random resource ID is assigned when errbot starts up.
You may fix the resource by appending it to the user name::

    BOT_IDENTITY = {
        'username': 'err@server.tld/resource',
    ...


Bot admins
----------

You can set `BOT_ADMINS` to configure which XMPP users are bot administrators.
For example: `BOT_ADMINS = ('gbin@someplace.com', 'zoni@somewhere.else.com')`


MUC rooms
---------

If you want the bot to join a certain chatroom when it starts up
then set `CHATROOM_PRESENCE` with a list of MUCs to join.
For example: `CHATROOM_PRESENCE = ('err@conference.server.tld',)`

You can configure the username errbot should use in chatrooms
by setting `CHATROOM_FN`.
