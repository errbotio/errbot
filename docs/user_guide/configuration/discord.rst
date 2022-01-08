# Errbot - Discord

This is a [Discord](http://discordapp.com) back-end for [Errbot](http://errbot.io).  It allows you to use Errbot from Discord to execute commands.

[![Updates](https://pyup.io/repos/github/gbin/err-backend-discord/shield.svg)](https://pyup.io/repos/github/gbin/err-backend-discord/)
[ ~ Dependencies scanned by PyUp.io ~ ]

## News

**⚠️ This backend uses the [discord.py](https://github.com/Rapptz/discord.py) python module which has been discontinued.  Support of this backend will continue on a best effort basis. ⚠️**

## Installation
An Errbot instance is required to install the discord back-end.  See the Errbot installation [documentation](http://errbot.io/en/latest/user_guide/setup.html#option-2-installing-errbot-in-a-virtualenv-preferred) for details.

### Requirements
 * Python 3.6 or later
 * Discord.py 1.7.3 or later

### Virtual Environment
The steps below are to install the discord back-end in Errbot's virtual environment.  In the examples below, the virtual environment was set to `/opt/errbot/virtualenv` and Errbot initialised in `/opt/errbot`.  The "extra" back-end directory is set to `/opt/errbot/backend`.


1. If not already set, set Errbot's `BOT_EXTRA_BACKEND_DIR` variable in `/opt/errbot/config.py` to the directory you will use to place additional back-ends.
```
BOT_EXTRA_BACKEND_DIR=/opt/errbot/backend
```
2. Set the back-end to use `Discord`.
```
BACKEND = 'Discord'
```
3. Clone repository to your Errbot back-end directory.
```
cd /opt/errbot/backend
git clone https://github.com/gbin/err-backend-discord.git
```
4. Install back-end dependencies (Errbot's virtual environment must be activated to install the dependencies into it).
```
source /opt/errbot/virtualenv/bin/activate
cd err-backend-discord
pip install -r requirements.txt
deactivate
```
5. Set the bot's token (see _Create a discord application_ for information on how to get the token).
```
BOT_IDENTITY = {
 'token' : 'changeme'
}
```
6. Enable *SERVER MEMBERS INTENT* for your bot on the Discord website.  See [here](https://discordpy.readthedocs.io/en/latest/intents.html?highlight=intents#privileged-intents) for the required steps.

## Create a discord application
For further information about getting a bot user into a server please see: https://discordapp.com/developers/docs/topics/oauth2. You can use [this tool](https://discordapi.com/permissions.html) to generate a proper invitation link.
The reactiflux community have written a quick start guide to [creating a discord bot and getting a token](https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token)


## Acknowledgements

This backend gratefully uses the invaluable `discord.py` python module.

## Contributing

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D
