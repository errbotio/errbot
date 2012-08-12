import UserDict
import inspect
import logging
import os
import shelve
from threading import Timer, current_thread
from config import BOT_DATA_DIR
from errbot.utils import PLUGINS_SUBDIR, recurse_check_structure
from errbot import holder

def unicode_filter(key):
    if type(key) == unicode:
        return key.encode('utf-8')
    return key

class BotPluginBase(object, UserDict.DictMixin):
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

                if name in holder.bot.commands:
                    f = holder.bot.commands[name]
                    new_name = (classname + '-' + name).lower()
                    holder.bot.warn_admins('%s.%s clashes with %s.%s so it has been renamed %s' % (classname, name, f.im_class.__name__, f.__name__, new_name ))
                    name = new_name
                logging.debug('Adding command : %s -> %s' % (name, value.__name__))
                holder.bot.commands[name] = value
        self.is_activated = True

    current_pollers = []
    current_timers = []

    def deactivate(self):
        """
            Override if you want to do something at tear down phase (don't forget to super(Gnagna, self).deactivate())
        """
        if self.current_pollers:
            logging.debug('You still have active pollers at deactivation stage, I cleaned them up for you.')
            self.current_pollers = []
            for timer in self.current_timers:
                timer.cancel()

        logging.debug('Closing shelf %s' % self.shelf)
        self.shelf.close()
        for name, value in inspect.getmembers(self, inspect.ismethod):
            if getattr(value, '_jabberbot_command', False):
                name = getattr(value, '_jabberbot_command_name')
                del(holder.bot.commands[name])
        self.is_activated = False

    def start_poller(self, interval, method, args=None, kwargs=None):
        if not kwargs: kwargs = {}
        if not args: args = []

        logging.debug('Programming the polling of %s every %i seconds with args %s and kwargs %s' % (method.__name__, interval, str(args), str(kwargs)))
        try:
            self.current_pollers.append((method, args, kwargs))
            self.program_next_poll(interval, method, args, kwargs)
        except Exception, e:
            logging.exception('failed')

    def stop_poller(self, method, args=None, kwargs=None):
        if not kwargs: kwargs = {}
        if not args: args = []
        logging.debug('Stop polling of %s with args %s and kwargs %s' % (method, args, kwargs))
        self.current_pollers.remove((method, args, kwargs))

    def program_next_poll(self, interval, method, args, kwargs):
        t = Timer(interval=interval, function=self.poller, kwargs={'interval': interval, 'method': method, 'args': args, 'kwargs': kwargs})
        self.current_timers.append(t) # save the timer to be able to kill it
        t.setDaemon(True) # so it is not locking on exit
        t.start()

    def poller(self, interval, method, args, kwargs):
        previous_timer = current_thread()
        if previous_timer in self.current_timers:
            logging.debug('Previous timer found and removed')
            self.current_timers.remove(previous_timer)

        if (method, args, kwargs) in self.current_pollers:
            try:
                method(*args, **kwargs)
            except Exception as e:
                logging.exception('A poller crashed')
            self.program_next_poll(interval, method, args, kwargs)


class BotPlugin(BotPluginBase):
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

    def get_configuration_template(self):
        """ If your plugin needs a configuration, override this method and return a configuration template.
        for example a dictionary like:
        return {'LOGIN' : 'example@example.com', 'PASSWORD' : 'password'}
        Note : if this method returns None, the plugin won't be configured
        """
        return None

    def check_configuration(self, configuration):
        """ By default, this method will do only a BASIC check. You need to override it if you want to do more complex checks.
        It will be called before the configure callback. Note if the config_template is None, it will never be called
        It means recusively:
        1. in case of a dictionary, it will check if all the entries and from the same type are there and not more
        2. in case of an array or tuple, it will assume array members of the same type of first element of the template (no mix typed is supported)

        In case of validation error it should raise a errbot.utils.ValidationException

        """
        recurse_check_structure(self.get_configuration_template(), configuration) # default behavior

    def configure(self, configuration):
        """ By default, it will just store the current configuation in the self.config field of your plugin
        If this plugin has no configuration yet, the framework will call this function anyway with None
        This method will be called before activation so don't expect to be activated at that point
        """
        self.config = configuration

    def activate(self):
        """
            Override if you want to do something at initialization phase (don't forget to super(Gnagna, self).activate())
        """
        super(BotPlugin, self).activate()


    def deactivate(self):
        """
            Override if you want to do something at tear down phase (don't forget to super(Gnagna, self).deactivate())
        """
        super(BotPlugin, self).deactivate()

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

    def warn_admins(self, warning):
        """
            Sends a warning to the administrators of the bot
        """
        return holder.bot.warn_admins(warning)

    def send(self, user, text, in_reply_to=None, message_type='chat'):
        """
            Sends asynchronously a message a room or a user.
             if it is a room message_type needs to by 'groupchat' and user the room.
        """
        # small hack to send back to the correct jid in case of chatroom
        if message_type == 'groupchat':
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

    def start_poller(self, interval, method, args=None, kwargs=None):
        """
            Start to poll a method at specific interval in seconds.
            Note : it will call the method with the initial interval delay for the first time
            Also, you can program
            for example : self.program_poller(self,30, fetch_stuff)
            where you have def fetch_stuff(self) in your plugin
        """
        super(BotPlugin, self).start_poller(interval, method, args, kwargs)

    def stop_poller(self, method=None, args=None, kwargs=None):
        """
            stop poller(s).
            if the method equals None -> it stops all the pollers
            you need to regive the same parameters as the original start_poller to match a specific poller to stop
        """
        super(BotPlugin, self).stop_poller(method, args, kwargs)