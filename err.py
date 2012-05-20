#!/usr/bin/python
import logging
import os

from config import BOT_IDENTITY,BOT_LOG_LEVEL,BOT_DATA_DIR
from utils import PLUGINS_SUBDIR
logging.basicConfig(format='%(levelname)s:%(message)s')
logging.getLogger('').setLevel(BOT_LOG_LEVEL)

d = os.path.dirname(BOT_DATA_DIR)
if not os.path.exists(d):
    raise Exception('The data directory %s for the bot does not exist')
if not os.access(BOT_DATA_DIR, os.W_OK):
    raise Exception('The data directory %s should be writable for the bot')

# make the plugins subdir to store the plugin shelves
d = BOT_DATA_DIR + os.sep + PLUGINS_SUBDIR
if not os.path.exists(d):
   os.makedirs(d)

from errBot import ErrBot
from botplugin import BotPlugin

__author__ = 'gbin'


# Set the class to extend in the BotPlugin (trick to avoid weird circular dependencies)
BotPlugin.botbase_class = ErrBot

bot = ErrBot(**BOT_IDENTITY)

bot.serve_forever()
