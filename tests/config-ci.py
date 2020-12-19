# config for continus integration testing.
# Don't use this for sensible defaults
import logging

BOT_DATA_DIR = "/tmp"
BOT_EXTRA_PLUGIN_DIR = None
AUTOINSTALL_DEPS = True
BOT_LOG_FILE = "/tmp/err.log"
BOT_LOG_LEVEL = logging.DEBUG
BOT_LOG_SENTRY = False
SENTRY_DSN = ""
SENTRY_LOGLEVEL = BOT_LOG_LEVEL
BOT_ASYNC = True
BOT_IDENTITY = {
    "username": "err@localhost",
    "password": "changeme",
}

BOT_ADMINS = ("gbin@localhost",)
CHATROOM_PRESENCE = ()
CHATROOM_FN = "Err"
BOT_PREFIX = "!"
DIVERT_TO_PRIVATE = ()
CHATROOM_RELAY = {}
REVERSE_CHATROOM_RELAY = {}
