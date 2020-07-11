HipChat backend configuration
=============================

This backend lets you connect to the
`HipChat <https://hipchat.com/>`_ messaging service.
To select this backend,
set `BACKEND = 'Hipchat'`.

Extra Dependencies
------------------

You need to install this dependency before using Errbot with Hipchat::

    pip install slixmpp pyasn1 pyasn1-modules hypchat


Account setup
-------------

You will first need to create a regular user account for the bot to use.
Once you have an account for errbot to use,
login at HipChat and go into the account settings for the user.

You will need to create an API token under **API access**.
Make sure it has all available scopes
otherwise some functionality will be unavailable,
which may prevent the bot from working correctly at all.

With the API token created,
continue on to **XMPP/Jabber info**.
You will be needing the `Jabber ID` which is listed here.

You can now configure the account by setting up `BOT_IDENTITY` as follows::

    BOT_IDENTITY = {
        'username' : '12345_123456@chat.hipchat.com',
        'password' : 'changeme',
        # Group admins can create/view tokens on the settings page after logging
        # in on HipChat's website
        'token'    : 'ed4b74d62833267d98aa99f312ff04',
        # If you're using HipChat server (self-hosted HipChat) then you should set
        # the endpoint below. If you don't use HipChat server but use the hosted version
        # of HipChat then you may leave this commented out.
        # 'endpoint' : 'https://api.hipchat.com',
        # If your self-hosted Hipchat server is using SSL, and your certificate
        # is self-signed, set verify to False or hypchat will fail
        # 'verify': False,

Bot admins
----------

You can set `BOT_ADMINS` to configure which Hipchat users are bot administrators.
Make sure to include the `@` sign.
For example: `BOT_ADMINS = ('@gbin', '@zoni')`


Rooms
-----

You can let the bot join rooms (that it has access to) by setting up `CHATROOM_PRESENCE`.
For example: `CHATROOM_PRESENCE = ('General', 'Another room')`

You must also set the correct value for `CHATROOM_FN`.
This **must** be set to the value of `Room nickname`
which can be found in the HipChat account settings under **XMPP/Jabber info**.


@mentions
---------

To make the bot respond when it is mentioned (such as with *"@errbot status"*)
we recommend also setting `BOT_ALT_PREFIXES = ('@errbot',)`
(assuming `errbot` is the username of the account you're using for the bot).
