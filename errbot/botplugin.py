import logging
import os
import shlex
from threading import Timer, current_thread
from types import ModuleType
from typing import Tuple, Callable, Mapping, Any, Sequence
from io import IOBase

from .utils import PLUGINS_SUBDIR, recurse_check_structure
from .storage import StoreMixin, StoreNotOpenError
from errbot.backends.base import Message, Presence, Stream, MUCRoom, Identifier, ONLINE

log = logging.getLogger(__name__)


# noinspection PyAbstractClass
class BotPluginBase(StoreMixin):
    """
     This class handle the basic needs of bot plugins like loading, unloading and creating a storage
     It is the main contract between the plugins and the bot
    """

    def __init__(self, bot):
        self.is_activated = False
        self.current_pollers = []
        self.current_timers = []
        self.log = logging.getLogger("errbot.plugins.%s" % self.__class__.__name__)
        if bot is not None:
            self._load_bot(bot)
        super().__init__()

    def _load_bot(self, bot):
        """ This should be eventually moved back to __init__ once plugin will forward correctly their params.
        """
        self._bot = bot
        self.plugin_dir = bot.plugin_manager.plugin_dir

    @property
    def mode(self) -> str:
        """
        Get the current active backend.

        :return: the mode like 'tox', 'xmpp' etc...
        """
        return self._bot.mode

    @property
    def bot_config(self) -> ModuleType:
        """
        Get the bot configuration from config.py.
        For exemple you can access:
        self.bot_config.BOT_DATA_DIR
        """
        # if BOT_ADMINS is just an unique string make it a tuple for backwards
        # compatibility
        if isinstance(self._bot.bot_config.BOT_ADMINS, str):
            self._bot.bot_config.BOT_ADMINS = (self._bot.bot_config.BOT_ADMINS,)
        return self._bot.bot_config

    @property
    def bot_identifier(self) -> Identifier:
        """
        Get bot identifier on current active backend.

        :return Identifier
        """
        return self._bot.bot_identifier

    def init_storage(self) -> None:
        classname = self.__class__.__name__
        log.debug('Init storage for %s' % classname)
        self.open_storage(self._bot.storage_plugin, classname)

    def activate(self) -> None:
        """
            Override if you want to do something at initialization phase (don't forget to
            super(Gnagna, self).activate())
        """
        self.init_storage()
        self._bot.inject_commands_from(self)
        self._bot.inject_command_filters_from(self)
        self.is_activated = True

    def deactivate(self) -> None:
        """
            Override if you want to do something at tear down phase (don't forget to super(Gnagna, self).deactivate())
        """
        if self.current_pollers:
            log.debug('You still have active pollers at deactivation stage, I cleaned them up for you.')
            self.current_pollers = []
            for timer in self.current_timers:
                timer.cancel()

        try:
            self.close_storage()
        except StoreNotOpenError:
            pass
        self._bot.remove_command_filters_from(self)
        self._bot.remove_commands_from(self)
        self.is_activated = False

    def start_poller(self,
                     interval: float,
                     method: Callable[..., None],
                     args: Tuple=None,
                     kwargs: Mapping=None):
        """ Starts a poller that will be called at a regular interval

        :param interval: interval in seconds
        :param method: targetted method
        :param args: args for the targetted method
        :param kwargs: kwargs for the targetting method
        """
        if not kwargs:
            kwargs = {}
        if not args:
            args = []

        log.debug('Programming the polling of %s every %i seconds with args %s and kwargs %s' % (
            method.__name__, interval, str(args), str(kwargs))
        )
        # noinspection PyBroadException
        try:
            self.current_pollers.append((method, args, kwargs))
            self.program_next_poll(interval, method, args, kwargs)
        except Exception:
            log.exception('failed')

    def stop_poller(self,
                    method: Callable[..., None],
                    args: Tuple=None,
                    kwargs: Mapping=None):
        if not kwargs:
            kwargs = {}
        if not args:
            args = []
        log.debug('Stop polling of %s with args %s and kwargs %s' % (method, args, kwargs))
        self.current_pollers.remove((method, args, kwargs))

    def program_next_poll(self,
                          interval: float,
                          method: Callable[..., None],
                          args: Tuple=None,
                          kwargs: Mapping=None):
        t = Timer(interval=interval, function=self.poller,
                  kwargs={'interval': interval, 'method': method, 'args': args, 'kwargs': kwargs})
        self.current_timers.append(t)  # save the timer to be able to kill it
        t.setName('Poller thread for %s' % type(method.__self__).__name__)
        t.setDaemon(True)  # so it is not locking on exit
        t.start()

    def poller(self,
               interval: float,
               method: Callable[..., None],
               args: Tuple=None,
               kwargs: Mapping=None):
        previous_timer = current_thread()
        if previous_timer in self.current_timers:
            log.debug('Previous timer found and removed')
            self.current_timers.remove(previous_timer)

        if (method, args, kwargs) in self.current_pollers:
            # noinspection PyBroadException
            try:
                method(*args, **kwargs)
            except Exception:
                log.exception('A poller crashed')
            self.program_next_poll(interval, method, args, kwargs)


# noinspection PyAbstractClass
class BotPlugin(BotPluginBase):
    @property
    def min_err_version(self) -> str:
        """
        DEPRECATED: see :doc:`/user_guide/plugin_development/plugin_compatibility_settings.html`
        If your plugin has a minimum version of err it needs to be on in order to run,
        please override accordingly this method, returning a string with the dotted
        minimum version. It MUST be in a 3 dotted numbers format or None

        For example: "1.2.2"
        """
        return None

    @property
    def max_err_version(self) -> str:
        """
        DEPRECATED: see :doc:`/user_guide/plugin_development/plugin_compatibility_settings.html`
        If your plugin has a maximal version of err it needs to be on in order to run,
        please override accordingly this method, returning a string with the dotted
        maximal version. It MUST be in a 3 dotted numbers format or None

        For example: "1.2.2"
        """
        return None

    def get_configuration_template(self) -> Mapping:
        """
        If your plugin needs a configuration, override this method and return
        a configuration template.

        For example a dictionary like:
        return {'LOGIN' : 'example@example.com', 'PASSWORD' : 'password'}

        Note: if this method returns None, the plugin won't be configured
        """
        return None

    def check_configuration(self, configuration: Mapping) -> None:
        """
        By default, this method will do only a BASIC check. You need to override
        it if you want to do more complex checks. It will be called before the
        configure callback. Note if the config_template is None, it will never
        be called.

        It means recusively:
        1. in case of a dictionary, it will check if all the entries and from
           the same type are there and not more.
        2. in case of an array or tuple, it will assume array members of the
           same type of first element of the template (no mix typed is supported)

        In case of validation error it should raise a errbot.utils.ValidationException
        :param configuration: the configuration to be checked.
        """
        recurse_check_structure(self.get_configuration_template(), configuration)  # default behavior

    def configure(self, configuration: Mapping) -> None:
        """
        By default, it will just store the current configuration in the self.config
        field of your plugin. If this plugin has no configuration yet, the framework
        will call this function anyway with None.

        This method will be called before activation so don't expect to be activated
        at that point.
        :param configuration: injected configuration for the plugin.
        """
        self.config = configuration

    def activate(self) -> None:
        """
            Triggered on plugin activation.

            Override this method if you want to do something at initialization phase
            (don't forget to `super().activate()`).
        """
        super().activate()

    def deactivate(self) -> None:
        """
            Triggered on plugin deactivation.

            Override this method if you want to do something at tear-down phase
            (don't forget to `super().deactivate()`).
        """
        super().deactivate()

    def callback_connect(self) -> None:
        """
            Triggered when the bot has successfully connected to the chat network.

            Override this method to get notified when the bot is connected.
        """
        pass

    def callback_message(self, message: Message) -> None:
        """
            Triggered on every message not coming from the bot itself.

            Override this method to get notified on *ANY* message.

            :param message:
                representing the message that was received.
        """
        pass

    def callback_mention(self, message: Message, mentioned_people: Sequence[Identifier]) -> None:
        """
            Triggered if there are mentioned people in message.

            Override this method to get notified when someone was mentioned in message.
            [Note: This might not be implemented by all backends.]

            :param message:
                representing the messige that was received.
            :param mentioned_people:
                all mentioned people in this message.
        """
        pass

    def callback_presence(self, presence: Presence) -> None:
        """
            Triggered on every presence change.

            :param presence:
                An instance of :class:`~errbot.backends.base.Presence`
                representing the new presence state that was received.
        """
        pass

    def callback_stream(self, stream: Stream) -> None:
        """
            Triggered asynchronously (in a different thread context) on every incoming stream
            request or file transfert requests.
            You can block this call until you are done with the stream.
            To signal that you accept / reject the file, simply call stream.accept()
            or stream.reject() and return.
            :param stream:
                the incoming stream request.
        """
        stream.reject()  # by default, reject the file as the plugin doesn't want it.

    def callback_botmessage(self, message: Message):
        """
            Triggered on every message coming from the bot itself.

            Override this method to get notified on all messages coming from
            the bot itself (including those from other plugins).

            :param message:
                An instance of :class:`~errbot.backends.base.Message`
                representing the message that was received.
        """
        pass

    def callback_room_joined(self, room: MUCRoom):
        """
            Triggered when the bot has joined a MUC.

            :param room:
                An instance of :class:`~errbot.backends.base.MUCRoom`
                representing the room that was joined.
        """
        pass

    def callback_room_left(self, room: MUCRoom):
        """
            Triggered when the bot has left a MUC.

            :param room:
                An instance of :class:`~errbot.backends.base.MUCRoom`
                representing the room that was left.
        """
        pass

    def callback_room_topic(self, room: MUCRoom):
        """
            Triggered when the topic in a MUC changes.

            :param room:
                An instance of :class:`~errbot.backends.base.MUCRoom`
                representing the room for which the topic changed.
        """
        pass

    # Proxyfy some useful tools from the motherbot
    # this is basically the contract between the plugins and the main bot

    def warn_admins(self, warning: str) -> None:
        """
            Sends a warning to the administrators of the bot
            :param warning: mardown formatted text of the warning.
        """
        self._bot.warn_admins(warning)

    def send(self,
             user: object,
             text: str,
             in_reply_to: Message=None,
             message_type: str='chat',
             groupchat_nick_reply: bool=False) -> None:
        """
            Sends asynchronously a message to a room or a user.
             if it is a room message_type needs to by 'groupchat' and user the room.
             :param groupchat_nick_reply: if True it will mention the user in the chatroom.
             :param message_type: 'chat' or 'groupchat'
             :param in_reply_to: optionally, the original message this message is the answer to.
             :param text: markdown formatted text to send to the user.
             :param user: identifier of the user to which you want to send a message to. see build_identifier.
        """
        return self._bot.send(user, text, in_reply_to, message_type, groupchat_nick_reply)

    def change_presence(self, status: str = ONLINE, message: str = '') -> None:
        """
            Changes the presence/status of the bot.

        :param status: One of the constant defined in base.py : ONLINE, OFFLINE, DND,...
        :param message: Additional message
        :return: None
        """
        self._bot.change_presence(status, message)

    def send_templated(self,
                       user: Identifier,
                       template_name: str,
                       template_parameters: Mapping,
                       in_reply_to: Message=None,
                       message_type: str='chat',
                       groupchat_nick_reply: bool=False) -> None:
        """
            Sends asynchronously a message to a room or a user.
            Same as send but passing a template name and parameters instead of directly the markdown text.
             if it is a room message_type needs to by 'groupchat' and user the room.
             :param template_parameters: arguments for the template.
             :param template_name: name of the template to use.
             :param groupchat_nick_reply: if True it will mention the user in the chatroom.
             :param message_type: 'chat' or 'groupchat'
             :param in_reply_to: optionally, the original message this message is the answer to.
             :param text: markdown formatted text to send to the user.
             :param user: identifier of the user to which you want to send a message to. see build_identifier.
        """
        return self._bot.send_templated(user, template_name, template_parameters, in_reply_to, message_type,
                                        groupchat_nick_reply)

    def build_identifier(self, txtrep: str):
        """
           Transform a textual representation of a user or room identifier to the correct
           Identifier object you can set in Message.to and Message.frm.
           :param txtrep: the textual representation of the identifier (it is backend dependent).
        """
        return self._bot.build_identifier(txtrep)

    def send_stream_request(self,
                            user: Identifier,
                            fsource: IOBase,
                            name: str=None,
                            size: int=None,
                            stream_type: str=None):
        """
            Sends asynchronously a stream/file to a user.
            :param user: is the identifier of the person you want to send it to.
            :param fsource: is a file object you want to send.
            :param name: is an optional filename for it.
            :param size: is optional and is the espected size for it.
            :param stream_type: is optional for the mime_type of the content.

            It will return a Stream object on which you can monitor the progress of it.
        """
        return self._bot.send_stream_request(user, fsource, name, size, stream_type)

    def join_room(self, room: str, username: str=None, password: str=None):
        """
        Join a room (MUC).

        :param room:
            The JID/identifier of the room to join.
        :param username:
            An optional username to use.
        :param password:
            An optional password to use (for password-protected rooms).
        """
        return self._bot.join_room(room, username, password)

    def rooms(self) -> Sequence[MUCRoom]:
        """
        The list of rooms the bot is currently in.
        """
        return self._bot.rooms()

    def query_room(self, room: str) -> MUCRoom:
        """
        Query a room for information.

        :param room:
            The JID/identifier of the room to query for.
        :returns:
            An instance of :class:`~errbot.backends.base.MUCRoom`.
        :raises:
            :class:`~errbot.backends.base.RoomDoesNotExistError` if the room doesn't exist.
        """
        return self._bot.query_room(room=room)

    def get_installed_plugin_repos(self) -> Mapping:
        """
            Get the current installed plugin repos in a dictionary of name / url
        """
        return self._bot.get_installed_plugin_repos()

    def start_poller(self,
                     interval: float,
                     method: Callable[..., None],
                     args: Tuple=None,
                     kwargs: Mapping=None):
        """
            Start to poll a method at specific interval in seconds.

            Note: it will call the method with the initial interval delay for the first time
            Also, you can program
            for example : self.program_poller(self, 30, fetch_stuff)
            where you have def fetch_stuff(self) in your plugin
            :param kwargs: kwargs for the method to callback.
            :param args: args for the method to callback.
            :param method: method to callback.
            :param interval: interval in seconds.

        """
        super().start_poller(interval, method, args, kwargs)

    def stop_poller(self,
                    method: Callable[..., None],
                    args: Tuple=None,
                    kwargs: Mapping=None):
        """
            stop poller(s).

            If the method equals None -> it stops all the pollers
            you need to regive the same parameters as the original start_poller to match a specific poller to stop
            :param kwargs: The initial kwargs you gave to start_poller.
            :param args: The initial args you gave to start_poller.
            :param method: The initial method you passed to start_poller.

        """
        super().stop_poller(method, args, kwargs)


class ArgParserBase(object):
    """
    The `ArgSplitterBase` class defines the API which is used for argument
    splitting (used by the `split_args_with` parameter on
    :func:`~errbot.decorators.botcmd`).
    """

    def parse_args(self, args: str):
        """
        This method takes a string of un-split arguments and parses it,
        returning a list that is the result of splitting.

        If splitting fails for any reason it should return an exception
        of some kind.
        :param args: string to parse
        """
        raise NotImplementedError()


class SeparatorArgParser(ArgParserBase):
    """
    This argument splitter splits args on a given separator, like
    :func:`str.split` does.
    """

    def __init__(self, separator: str=None, maxsplit: int=-1):
        """
        :param separator:
            The separator on which arguments should be split. If sep is
            None, any whitespace string is a separator and empty strings
            are removed from the result.
        :param maxsplit:
            If given, do at most this many splits.
        """
        self.separator = separator
        self.maxsplit = maxsplit

    def parse_args(self, args: str):
        return args.split(self.separator, self.maxsplit)


class ShlexArgParser(ArgParserBase):
    """
    This argument splitter splits args using posix shell quoting rules,
    like :func:`shlex.split` does.
    """

    def parse_args(self, args):
        return shlex.split(args)
