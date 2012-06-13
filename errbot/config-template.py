# NOTICE : adapt this file and rename it to config.py

import logging

# the verbosity of the log, they are the standard python ones : DEBUG, INFO, ERROR ...
BOT_LOG_LEVEL = logging.DEBUG

# set the log file, None = console only, be sure the user of the bot can write there
BOT_LOG_FILE = '/var/log/err/err.log'

# Base configuration
BOT_IDENTITY = {
    'username' : 'err@localhost', # JID of the user you have created for the bot
    'password' : 'err' # password of the bot user
}

BOT_ADMINS = ('gbin@localhost',) # only those JIDs will have access to admin commands
BOT_DATA_DIR = '/var/lib/r2' # Point this to a writeable directory by the system user running the bot
BOT_EXTRA_PLUGIN_DIR = None # Add this directory to the plugin discovery (useful to develop a new plugin locally)

# ---- Chatrooms configuration (used by the chatroom plugin)
_TEST_ROOM = 'test@conference.localhost'

# CHATROOM_ PRESENCE
# it must be an iterable of names of rooms you want the bot to join at startup
CHATROOM_PRESENCE = (_TEST_ROOM,)

# CHATROOM_RELAY
# can be used to relay one to one message from specific users to the bot to MUCs
# it can be useful when XMPP notifiers like the standard Altassian Jira one doesn't support MUC
CHATROOM_RELAY = {'gbin@localhost' : (_TEST_ROOM,)}

# CHATROOM_FN
# Some XMPP implementations like HipChat are super picky on the fullname you join with for a MUC
# If you use HipChat, make sure to exactly match the fullname you set for the bot user
CHATROOM_FN = 'bot'

HIPCHAT_MODE = False