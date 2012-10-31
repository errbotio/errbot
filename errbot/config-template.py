# NOTICE : adapt this file and rename it to config.py
import logging

# the verbosity of the log, they are the standard python ones : DEBUG, INFO, ERROR ...
# Before reporting a problem, please try capture your logs with BOT_LOG_LEVEL = logging.DEBUG
BOT_LOG_LEVEL = logging.INFO

# set the log file, None = console only, be sure the user of the bot can write there
BOT_LOG_FILE = '/var/log/err/err.log'

# Enable logging to sentry (find out more about sentry at www.getsentry.com).
BOT_LOG_SENTRY = False
SENTRY_DSN = ''
SENTRY_LOGLEVEL = BOT_LOG_LEVEL

# Base configuration (Jabber mode)
BOT_IDENTITY = {
    'username' : 'err@localhost', # JID of the user you have created for the bot
    'password' : 'changeme' # password of the bot user
}

BOT_ASYNC = False # If true, the bot will handle the commands asynchronously [EXPERIMENTAL]

# HIPCHAT template
#BOT_IDENTITY = {
#    'username' : '12345_123456@chat.hipchat.com',
#    'password' : 'changeme',
#    'token' : 'ed4b74d62833267d98aa99f312ff04'
#}

# CAMPFIRE template
#BOT_IDENTITY = {
#    'subdomain': 'yatta',
#    'username' : 'errbot',
#    'password' : 'changeme'
#}

# IRC template
# BOT_IDENTITY = {
#    'nickname' : 'err-chatbot',
#    'password' : None, # optional
#    'server' : 'irc.freenode.net',
#    'port': 6667, # optional
#    'ssl': False,  # optional
#}

BOT_ADMINS = ('gbin@localhost',) # only those JIDs will have access to admin commands

# CAMPFIRE it should be the full name
# BOT_ADMINS = ('Guillaume Binet',) # only those JIDs will have access to admin commands

BOT_DATA_DIR = '/var/lib/err' # Point this to a writeable directory by the system user running the bot
BOT_EXTRA_PLUGIN_DIR = None # Add this directory to the plugin discovery (useful to develop a new plugin locally)

# Prefix used for commands. Note that in help strings, you should still use the
# default '!'. If the prefix is changed from the default, the help strings will
# be automatically adjusted.
BOT_PREFIX = '!'

# Separators that could separate the prefix from the command. If you end up
# using a nickname for the BOT_PREFIX, some people may use either a comma (,)
# or a colon (:) between the name and the command. Note: the code already
# checks for spaces, so do not add one here. Defaults to (':', ',')
# IE: err, echo hi
# BOT_PREFIX_SEPARATORS = (':', ',')

# Depending on your BOT_PREFIX, you may want help messages to insert a space
# between the BOT_PREFIX and the command. Defaults to False
# INSERT_SPACE = False

# Access controls, allowing commands to be restricted to specific users/rooms.
# Available filters (you can omit a filter or set it to None to disable it):
#   allowusers: Allow command from these users only
#   denyusers: Deny command from these users
#   allowrooms: Allow command only in these rooms (and direct messages)
#   denyrooms: Deny command in these rooms
#   allowprivate: Allow command from direct messages to the bot
#   allowmuc: Allow command inside rooms
# Example:
#ACCESS_CONTROLS = {'status': {'allowrooms': ('someroom@conference.localhost',)},
#                   'about': {'denyusers': ('baduser@localhost',), 'allowrooms': ('room1@conference.localhost', 'room2@conference.localhost')},
#                   'uptime': {'allowusers': BOT_ADMINS},
#                   'help': {'allowmuc': False},
#                  }
ACCESS_CONTROLS = {}

# ---- Chatrooms configuration (used by the chatroom plugin)
# it is a standard python file so you can reuse variables...
# For example: _TEST_ROOM = 'test@conference.localhost

# CHATROOM_ PRESENCE
# it must be an iterable of names of rooms you want the bot to join at startup
# for example : CHATROOM_PRESENCE = (_TEST_ROOM,)
# for IRC you can name them with their # like #err_chatroom
# for XMPP MUC with passwords you can add tuples in the form (ROOM, PASSWORD)
CHATROOM_PRESENCE = ()

# CHATROOM_RELAY
# can be used to relay one to one message from specific users to the bot to MUCs
# it can be useful when XMPP notifiers like the standard Altassian Jira one doesn't support MUC
# for example : CHATROOM_RELAY = {'gbin@localhost' : (_TEST_ROOM,)}
CHATROOM_RELAY = {}

# REVERSE_CHATROOM_RELAY
# this feature forward whatever is said to a specific JID
# it can be useful if you client like gtalk doesn't support MUC correctly !
# for example REVERSE_CHATROOM_RELAY = {_TEST_ROOM : ('gbin@localhost',)}
REVERSE_CHATROOM_RELAY = {}

# CHATROOM_FN
# Some XMPP implementations like HipChat are super picky on the fullname you join with for a MUC
# If you use HipChat, make sure to exactly match the fullname you set for the bot user
CHATROOM_FN = 'bot'

# RESPOND_TO_FULLNAME
# By setting this to True, the bot will respond to the it's name (as
# specified in CHATROOM_FN. Default is False
# RESPOND_TO_FULLNAME = False

# DIVERT_TO_PRIVATE
# An iterable of commands which should be responded to in private, even if the command was given
# in a MUC. For example: DIVERT_TO_PRIVATE = ('help', 'about', 'status')
DIVERT_TO_PRIVATE = ()

