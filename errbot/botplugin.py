import UserDict
import inspect
import logging
import os
import shelve
from config import BOT_DATA_DIR
from errbot.utils import PLUGINS_SUBDIR
from errbot import holder

def unicode_filter(key):
    if type(key) == unicode:
        return key.encode('utf-8')
    return key

class BotPlugin(object, UserDict.DictMixin):
    """
     This class handle the basic needs of bot plugins like loading, unloading and creating a storage
     It is the main contract between the plugins and the bot
    """
    is_activated = False

    # those are the minimal things to behave like a dictionary with the UserDict.DictMixin
    def __getitem__(self, key):
        return self.shelf.__getitem__(unicode_filter(key))

    def __setitem__(self, key, item):
        return self.shelf.__setitem__(unicode_filter(key), item)

    def __delitem__(self, key):
        return self.shelf.__delitem__(unicode_filter(key))

    def keys(self):
        keys = []
        for key in self.shelf.keys():
            if type(key) == str:
                keys.append(key.decode('utf-8'))
        return keys

    @property
    def min_err_version(self):
        """ If your plugin has a minimum version of err it needs to be on in order to run, please override accordingly this method.
        returning a string with the dotted minimum version. it MUST be in a 3 dotted numbers format or None
        for example: "1.2.2"
        """
        return None

    @property
    def max_err_version(self):
        """ If your plugin has a maximal version of err it needs to be on in order to run, please override accordingly this method.
        returning a string with the dotted maximal version. it MUST be in a 3 dotted numbers format or None
        for example: "1.2.2"
        """
        return None

    def activate(self):
        """
            Override if you want to do something at initialization phase (don't forget to super(Gnagna, self).activate())
        """
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
        """
            Override if you want to do something at tear down phase (don't forget to super(Gnagna, self).deactivate())
        """
        logging.debug('Closing shelf %s' % self.shelf)
        self.shelf.close()
        for name, value in inspect.getmembers(self, inspect.ismethod):
            if getattr(value, '_jabberbot_command', False):
                name = getattr(value, '_jabberbot_command_name')
                del(holder.bot.commands[name])
        self.is_activated = False

    def callback_connect(self):
        """
            Override to get a notified when the bot is connected
        """
        pass

    def callback_message(self, conn, mess):
        """
            Override to get a notified on *ANY* XMPP message.
            If you are interested only by chatting message you can filter for example mess.getType() in ('groupchat', 'chat')
        """
        pass

    # Proxyfy some useful tools from the motherbot
    # this is basically the contract between the plugins and the main bot

    def send(self, user, text, in_reply_to=None, message_type='chat'):
        """
            Sends asynchronously a message a room or a user.
             if it is a room message_type needs to by 'groupchat' and user the room.
        """
        # small hack to send back to the correct jid in case of chatroom
        if message_type=='groupchat':
            user = str(user).split('/')[0] # strip the precise user in the chatroom
        return holder.bot.send(user, text, in_reply_to, message_type)

    def bare_send(self, xmppy_msg):
        """
            A bypass to send directly a crafted xmppy message.
              Usefull to extend to bot in not forseen ways.
        """
        c = holder.bot.connect()
        if c:
            return c.send(xmppy_msg)
        logging.warning('Ignored a message as the bot is not connected yet')
        return None # the bot is not connected yet


    def join_room(self, room, username=None, password=None):
        """
            Make the bot join a room
        """
        return holder.bot.join_room(room, username, password)

    def get_installed_plugin_repos(self):
        """
            Get the current installed plugin repos in a dictionary of name / url
        """
        return holder.bot.get_installed_plugin_repos()

