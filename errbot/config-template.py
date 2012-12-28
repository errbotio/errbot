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
    'username': 'err@localhost',  # JID of the user you have created for the bot
    'password': 'changeme'  # password of the bot user
}

BOT_ASYNC = False  # If true, the bot will handle the commands asynchronously [EXPERIMENTAL]

# Influence the security methods used on connection. Default is to try anything:
# XMPP_FEATURE_MECHANISMS = {}
# To use only unencrypted plain auth:
# XMPP_FEATURE_MECHANISMS =  {'use_mech': 'PLAIN', 'unencrypted_plain': True, 'encrypted_plain': False}

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

# Extra optional parameters for IRC
# IRC_CHANNEL_RATE = 1 # Rate limiter in seconds between 2 messages in a channel, put None for no limit
# IRC_PRIVATE_RATE = 1 # Rate limiter in seconds between 2 private messages, put None for no limit

BOT_ADMINS = ('gbin@localhost',)  # only those JIDs will have access to admin commands

# CAMPFIRE it should be the full name
# BOT_ADMINS = ('Guillaume Binet',) # only those JIDs will have access to admin commands

BOT_DATA_DIR = '/var/lib/err'  # Point this to a writeable directory by the system user running the bot
BOT_EXTRA_PLUGIN_DIR = None  # Add this directory to the plugin discovery (useful to develop a new plugin locally)

# Prefix used for commands. Note that in help strings, you should still use the
# default '!'. If the prefix is changed from the default, the help strings will
# be automatically adjusted.
BOT_PREFIX = '!'

# Uncomment the following and set it to True if you want the prefix to be optional for normal chat
# (Meaning messages sent directly to the bot as opposed to within a MUC)
#BOT_PREFIX_OPTIONAL_ON_CHAT = False

# You might wish to have your bot respond by being called with certain names, rather
# than the BOT_PREFIX above. This option allows you to specify alternative prefixes
# the bot will respond to in addition to the prefix above.
#BOT_ALT_PREFIXES = ('Err',)

# If you use alternative prefixes, you might want to allow users to insert separators
# like , and ; between the prefix and the command itself. This allows users to refer
# to your bot like this (Assuming 'Err' is in your BOT_ALT_PREFIXES):
# "Err, status" or "Err: status"
# Note: There's no need to add spaces to the separators here
#BOT_ALT_PREFIX_SEPARATORS = (':', ',', ';')

# Continuing on this theme, you might want to permit your users to be lazy and not
# require correct capitalization, so they can do 'Err', 'err' or even 'ERR'.
#BOT_ALT_PREFIX_CASEINSENSITIVE = True

# Access controls, allowing commands to be restricted to specific users/rooms.
# Available filters (you can omit a filter or set it to None to disable it):
#   allowusers: Allow command from these users only
#   denyusers: Deny command from these users
#   allowrooms: Allow command only in these rooms (and direct messages)
#   denyrooms: Deny command in these rooms
#   allowprivate: Allow command from direct messages to the bot
#   allowmuc: Allow command inside rooms
# Rules listed in ACCESS_CONTROLS_DEFAULT are applied when a command cannot 
# be found inside ACCESS_CONTROLS
#
# Example:
#ACCESS_CONTROLS_DEFAULT = {} # Allow everyone access by default
#ACCESS_CONTROLS = {'status': {'allowrooms': ('someroom@conference.localhost',)},
#                   'about': {'denyusers': ('baduser@localhost',), 'allowrooms': ('room1@conference.localhost', 'room2@conference.localhost')},
#                   'uptime': {'allowusers': BOT_ADMINS},
#                   'help': {'allowmuc': False},
#                  }

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

# DIVERT_TO_PRIVATE
# An iterable of commands which should be responded to in private, even if the command was given
# in a MUC. For example: DIVERT_TO_PRIVATE = ('help', 'about', 'status')
DIVERT_TO_PRIVATE = ()
