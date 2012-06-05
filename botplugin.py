import inspect
import logging
import os
import shelve
from config import BOT_DATA_DIR
from utils import PLUGINS_SUBDIR
import holder

# this class handle the basic needs of bot plugins like loading, unloading and creating a storage
class BotPlugin(object):

    def __init__(self):
        self.is_activated = False

    def activate(self):
        classname = self.__class__.__name__
        logging.debug('Init shelf for %s' % classname)
        filename = BOT_DATA_DIR + os.sep + PLUGINS_SUBDIR + os.sep + classname + '.db'
        logging.debug('Loading %s' % filename)

        self.shelf = shelve.DbfilenameShelf(filename)
        for name, value in inspect.getmembers(self, inspect.ismethod):
            if getattr(value, '_jabberbot_command', False):
                name = getattr(value, '_jabberbot_command_name')
                logging.debug('Adding command to %s : %s -> %s' % (holder.bot, name, value))
                holder.bot.commands[name] = value
        self.is_activated = True


    def deactivate(self):
        logging.debug('Closing shelf %s' % self.shelf)
        self.shelf.close()
        for name, value in inspect.getmembers(self, inspect.ismethod):
            if getattr(value, '_jabberbot_command', False):
                name = getattr(value, '_jabberbot_command_name')
                del(holder.bot.commands[name])
        self.is_activated = False

    # Proxyfy some useful tools from the motherbot
    def send(self, user, text, in_reply_to=None, message_type='chat'):
        return holder.bot.send(user, text, in_reply_to, message_type)

    def connect(self):
        return holder.bot.connect()

    def join_room(self, room, username=None, password=None):
        return holder.bot.join_room(room, username, password)


