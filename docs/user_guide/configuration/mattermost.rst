Mattermost Backend
==================

Requirements
------------
- Mattermost with APIv4
- Python >= 3.4
- websockets 3.2
- `mattermostdriver <https://github.com/Vaelor/python-mattermost-driver>`_ greater than version 4.0

Installation
------------

- ``git clone https://github.com/errbotio/err-backend-mattermost``
- Create an account for the bot on the server.
- Install the requirements.
- Open errbot's config.py:

.. code: none
    BACKEND = "Mattermost"
    BOT_EXTRA_BACKEND_DIR = "/path/to/backends"

    BOT_ADMINS = ("@yourname") # Names need the @ in front!

    BOT_IDENTITY = {
        # Required
        "team": "nameoftheteam",
        "server": "mattermost.server.com",
        # For the login, either
        "login": "bot@email.de",
        "password": "botpassword",
        # Or, if you have a personal access token
        "token": "YourPersonalAccessToken",
        # Optional
        "insecure": False, # Default = False. Set to true for self signed certificates
        "scheme": "https", # Default = https
        "port": 8065, # Default = 8065
        "timeout": 30, # Default = 30. If the webserver disconnects idle connections later/earlier change this value
        "cards_hook": "incomingWebhookId" # Needed for cards/attachments
    }


- If the bot has problems doing some actions, you should make it system admin, some actions won't work otherwise.

Cards/Attachments
-----------------
Cards are called attachments in Mattermost.
If you want to send attachments, you need to create an incoming Webhook in Mattermost
and add the webhook id to your errbot `config.py` in `BOT_IDENTITY`.
This is not an ideal solution, but AFAIK Mattermost does not support sending attachments
over the api like slack does.

APIv3
-----
Use the APIv3 branch for that. It is no longer supported and not guaranteed to work!

**Attention**: The `BOT_IDENTITY` config options are different for V3 and V4!

Known issues
------------

- Channelmentions in messages aren't accounted for (this is a possible issue but is unconfirmed)

FAQ
----

The Bot does not answer my direct messages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have multiple teams, check that you are both members of the same team!

Acknowledgements
----------------

**Thanks** to http://errbot.io and all the contributors to the bot.
Most of this code was build with help from the already existing backends,
especially: ``https://github.com/errbotio/errbot/blob/master/errbot/backends/slack.py``
