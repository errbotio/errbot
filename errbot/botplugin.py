import logging
import shlex
from threading import Timer, current_thread
from types import ModuleType
from typing import Tuple, Callable, Mapping, Sequence
from io import IOBase
import re

from .storage import StoreMixin, StoreNotOpenError
from errbot.backends.base import Message, Presence, Stream, Room, Identifier, ONLINE, Card, Reaction

log = logging.getLogger(__name__)


class ValidationException(Exception):
    pass


def recurse_check_structure(sample, to_check):
    sample_type = type(sample)
    to_check_type = type(to_check)

    # Skip this check if the sample is None because it will always be something
    # other than NoneType when changed from the default. Raising ValidationException
    # would make no sense then because it would defeat the whole purpose of having
    # that key in the sample when it could only ever be None.
    if sample is not None and sample_type != to_check_type:
        raise ValidationException(f'{sample} [{sample_type}] is not the same type as {to_check} [{to_check_type}].')

    if sample_type in (list, tuple):
        for element in to_check:
            recurse_check_structure(sample[0], element)
        return

    if sample_type == dict:
        for key in sample:
            if key not in to_check:
                raise ValidationException(f'{to_check} doesn\'t contain the key {key}.')
        for key in to_check:
            if key not in sample:
                raise ValidationException(f'{to_check} contains an unknown key {key}.')
        for key in sample:
            recurse_check_structure(sample[key], to_check[key])
        return


class CommandError(Exception):
    """
    Use this class to report an error condition from your commands, the command
    did not proceed for a known "business" reason.
    """

    def __init__(self, reason: str, template: str = None):
        """
        :param reason: the reason for the error in the command.
        :param template: apply this specific template to report the error.
        """
        self.reason = reason
        self.template = template

    def __str__(self):
        return str(self.reason)


class Command(object):
    """
    This is a dynamic definition of an errbot command.
    """

    def __init__(self, function, cmd_type=None, cmd_args=None, cmd_kwargs=None, name=None, doc=None):
        """
        Create a Command definition.

        :param function:
            a function or a lambda with the correct signature for the type of command to inject for example `def
            mycmd(plugin, msg, args)` for a botcmd.  Note: the first parameter will be the plugin itself (equivalent to
            self).
        :param cmd_type:
            defaults to `botcmd` but can be any decorator function used for errbot commands.
        :param cmd_args: the parameters of the decorator.
        :param cmd_kwargs: the kwargs parameter of the decorator.
        :param name:
            defaults to the name of the function you are passing if it is a first class function or needs to be set if
            you use a lambda.
        :param doc:
            defaults to the doc of the given function if it is a first class function. It can be set for a lambda or
            overridden for a function with this.  """
        if cmd_type is None:
            from errbot import botcmd  # TODO refactor this out of __init__ so it can be reusable.
            cmd_type = botcmd
        if name is None:
            if function.__name__ == '<lambda>':
                raise ValueError('function is a lambda (anonymous), parameter name needs to be set.')
            name = function.__name__
        self.name = name
        if cmd_kwargs is None:
            cmd_kwargs = {}
        if cmd_args is None:
            cmd_args = ()
        function.__name__ = name
        if doc:
            function.__doc__ = doc
        self.definition = cmd_type(*((function,) + cmd_args), **cmd_kwargs)


# noinspection PyAbstractClass
class BotPluginBase(StoreMixin):
    """
     This class handle the basic needs of bot plugins like loading, unloading and creating a storage
     It is the main contract between the plugins and the bot
    """

    def __init__(self, bot, name=None):
        self.is_activated = False
        self.current_pollers = []
        self.current_timers = []
        self.dependencies = []
        self._dynamic_plugins = {}
        self.log = logging.getLogger(f'errbot.plugins.{name}')
        self.log.debug('Logger for plugin initialized...')
        self._bot = bot
        self.plugin_dir = bot.repo_manager.plugin_dir
        self._name = name
        super().__init__()

    @property
    def name(self) -> str:
        """
        Get the name of this plugin as described in its .plug file.

        :return: The plugin name.
        """
        return self._name

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
        For example you can access:
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
        log.debug(f'Init storage for {self.name}.')
        self.open_storage(self._bot.storage_plugin, self.name)

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

        for plugin in self._dynamic_plugins.values():
            self._bot.remove_command_filters_from(plugin)
            self._bot.remove_commands_from(plugin)

    def start_poller(self,
                     interval: float,
                     method: Callable[..., None],
                     times: int = None,
                     args: Tuple = None,
                     kwargs: Mapping = None):
        """ Starts a poller that will be called at a regular interval

        :param interval: interval in seconds
        :param method: targetted method
        :param times:
            number of times polling should happen (defaults to``None`` which
            causes the polling to happen indefinitely)
        :param args: args for the targetted method
        :param kwargs: kwargs for the targetting method
        """
        if not kwargs:
            kwargs = {}
        if not args:
            args = []

        log.debug(f'Programming the polling of {method.__name__} every {interval} seconds '
                  f'with args {str(args)} and kwargs {str(kwargs)}')
        # noinspection PyBroadException
        try:
            self.current_pollers.append((method, args, kwargs))
            self.program_next_poll(interval, method, times, args, kwargs)
        except Exception:
            log.exception('Poller programming failed.')

    def stop_poller(self,
                    method: Callable[..., None],
                    args: Tuple = None,
                    kwargs: Mapping = None):
        if not kwargs:
            kwargs = {}
        if not args:
            args = []
        log.debug(f'Stop polling of {method} with args {args} and kwargs {kwargs}')
        self.current_pollers.remove((method, args, kwargs))

    def program_next_poll(self,
                          interval: float,
                          method: Callable[..., None],
                          times: int = None,
                          args: Tuple = None,
                          kwargs: Mapping = None):
        if times is not None and times <= 0:
            return

        t = Timer(interval=interval, function=self.poller,
                  kwargs={'interval': interval, 'method': method,
                          'times': times, 'args': args, 'kwargs': kwargs})
        self.current_timers.append(t)  # save the timer to be able to kill it
        t.setName(f'Poller thread for {type(method.__self__).__name__}')
        t.setDaemon(True)  # so it is not locking on exit
        t.start()

    def poller(self,
               interval: float,
               method: Callable[..., None],
               times: int = None,
               args: Tuple = None,
               kwargs: Mapping = None):
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

            if times is not None:
                times -= 1

            self.program_next_poll(interval, method, times, args, kwargs)

    def create_dynamic_plugin(self, name: str, commands: Tuple[Command], doc: str = ''):
        """
            Creates a plugin dynamically and exposes its commands right away.

            :param name: name of the plugin.
            :param commands: a tuple of command definition.
            :param doc: the main documentation of the plugin.
        """
        if name in self._dynamic_plugins:
            raise ValueError('Dynamic plugin %s already created.')
        # cleans the name to be a valid python type.
        plugin_class = type(re.sub(r'\W|^(?=\d)', '_', name), (BotPlugin,),
                            {command.name: command.definition for command in commands})
        plugin_class.__errdoc__ = doc
        plugin = plugin_class(self._bot, name=name)
        self._dynamic_plugins[name] = plugin
        self._bot.inject_commands_from(plugin)

    def destroy_dynamic_plugin(self, name: str):
        """
            Reverse operation of create_dynamic_plugin.

            This allows you to dynamically refresh the list of commands for example.
            :param name: the name of the dynamic plugin given to create_dynamic_plugin.
        """
        if name not in self._dynamic_plugins:
            raise ValueError("Dynamic plugin %s doesn't exist.", name)
        plugin = self._dynamic_plugins[name]
        self._bot.remove_command_filters_from(plugin)
        self._bot.remove_commands_from(plugin)
        del self._dynamic_plugins[name]

    def get_plugin(self, name) -> 'BotPlugin':
        """
        Gets a plugin your plugin depends on. The name of the dependency needs to be listed in [Code] section
        key DependsOn of your plug file. This method can only be used after your plugin activation
        (or having called super().activate() from activate itself).
        It will return a plugin object.

        :param name: the name
        :return: the BotPlugin object requested.
        """
        if not self.is_activated:
            raise Exception('Plugin needs to be in activated state to be able to get its dependencies.')

        if name not in self.dependencies:
            raise Exception(f'Plugin dependency {name} needs to be listed in section [Core] key '
                            f'"DependsOn" to be used in get_plugin.')

        return self._bot.plugin_manager.get_plugin_obj_by_name(name)


# noinspection PyAbstractClass
class BotPlugin(BotPluginBase):

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

        In case of validation error it should raise a errbot.ValidationException

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
                representing the message that was received.
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

    def callback_reaction(self, reaction: Reaction) -> None:
        """
            Triggered on every reaction event.

            :param reaction:
                An instance of :class:`~errbot.backends.base.Reaction`
                representing the new reaction event that was received.
        """
        pass

    def callback_stream(self, stream: Stream) -> None:
        """
            Triggered asynchronously (in a different thread context) on every incoming stream
            request or file transfer request.
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

    def callback_room_joined(self, room: Room):
        """
            Triggered when the bot has joined a MUC.

            :param room:
                An instance of :class:`~errbot.backends.base.MUCRoom`
                representing the room that was joined.
        """
        pass

    def callback_room_left(self, room: Room):
        """
            Triggered when the bot has left a MUC.

            :param room:
                An instance of :class:`~errbot.backends.base.MUCRoom`
                representing the room that was left.
        """
        pass

    def callback_room_topic(self, room: Room):
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
        Send a warning to the administrators of the bot.

        :param warning: The markdown-formatted text of the message to send.
        """
        self._bot.warn_admins(warning)

    def send(self,
             identifier: Identifier,
             text: str,
             in_reply_to: Message = None,
             groupchat_nick_reply: bool = False) -> None:
        """
            Send a message to a room or a user.

            :param groupchat_nick_reply: if True the message will mention the user in the chatroom.
            :param in_reply_to: the original message this message is a reply to (optional).
                                In some backends it will start a thread.
            :param text: markdown formatted text to send to the user.
            :param identifier: An Identifier representing the user or room to message.
                               Identifiers may be created with :func:`build_identifier`.
        """
        if not isinstance(identifier, Identifier):
            raise ValueError("identifier needs to be of type Identifier, the old string behavior is not supported")
        return self._bot.send(identifier, text, in_reply_to, groupchat_nick_reply)

    def send_card(self,
                  body: str = '',
                  to: Identifier = None,
                  in_reply_to: Message = None,
                  summary: str = None,
                  title: str = '',
                  link: str = None,
                  image: str = None,
                  thumbnail: str = None,
                  color: str = 'green',
                  fields: Tuple[Tuple[str, str], ...] = ()) -> None:
        """
        Sends a card.

        A Card is a special type of preformatted message. If it matches with a backend similar concept like on
        Slack or Hipchat it will be rendered natively, otherwise it will be sent as a regular formatted message.

        :param body: main text of the card in markdown.
        :param to: the card is sent to this identifier (Room, RoomOccupant, Person...).
        :param in_reply_to: the original message this message is a reply to (optional).
        :param summary: (optional) One liner summary of the card, possibly collapsed to it.
        :param title: (optional) Title possibly linking.
        :param link: (optional) url the title link is pointing to.
        :param image: (optional) link to the main image of the card.
        :param thumbnail: (optional) link to an icon / thumbnail.
        :param color: (optional) background color or color indicator.
        :param fields: (optional) a tuple of (key, value) pairs.
        """
        frm = in_reply_to.to if in_reply_to else self.bot_identifier
        if to is None:
            if in_reply_to is None:
                raise ValueError('Either to or in_reply_to needs to be set.')
            to = in_reply_to.frm
        self._bot.send_card(Card(body, frm, to, in_reply_to, summary, title, link, image, thumbnail, color, fields))

    def change_presence(self, status: str = ONLINE, message: str = '') -> None:
        """
            Changes the presence/status of the bot.

        :param status: One of the constant defined in base.py : ONLINE, OFFLINE, DND,...
        :param message: Additional message
        :return: None
        """
        self._bot.change_presence(status, message)

    def send_templated(self,
                       identifier: Identifier,
                       template_name: str,
                       template_parameters: Mapping,
                       in_reply_to: Message = None,
                       groupchat_nick_reply: bool = False) -> None:
        """
        Sends asynchronously a message to a room or a user.

        Same as send but passing a template name and parameters instead of directly the markdown text.
        :param template_parameters: arguments for the template.
        :param template_name: name of the template to use.
        :param groupchat_nick_reply: if True it will mention the user in the chatroom.
        :param in_reply_to: optionally, the original message this message is the answer to.
        :param identifier: identifier of the user or room to which you want to send a message to.
        """
        return self._bot.send_templated(identifier=identifier,
                                        template_name=template_name,
                                        template_parameters=template_parameters,
                                        in_reply_to=in_reply_to,
                                        groupchat_nick_reply=groupchat_nick_reply)

    def build_identifier(self, txtrep: str) -> Identifier:
        """
           Transform a textual representation of a user identifier to the correct
           Identifier object you can set in Message.to and Message.frm.

           :param txtrep: the textual representation of the identifier (it is backend dependent).
           :return: a user identifier.
        """
        return self._bot.build_identifier(txtrep)

    def send_stream_request(self,
                            user: Identifier,
                            fsource: IOBase,
                            name: str = None,
                            size: int = None,
                            stream_type: str = None):
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

    def rooms(self) -> Sequence[Room]:
        """
        The list of rooms the bot is currently in.
        """
        return self._bot.rooms()

    def query_room(self, room: str) -> Room:
        """
        Query a room for information.

        :param room:
            The JID/identifier of the room to query for.
        :returns:
            An instance of :class:`~errbot.backends.base.MUCRoom`.
        :raises:
            :class:`~errbot.backends.base.RoomDoesNotExistError` if the room doesn't exist.
        """
        return self._bot.query_room(room)

    def start_poller(self,
                     interval: float,
                     method: Callable[..., None],
                     times: int = None,
                     args: Tuple = None,
                     kwargs: Mapping = None):
        """
            Start to poll a method at specific interval in seconds.

            Note: it will call the method with the initial interval delay for
            the first time

            Also, you can program
            for example : self.program_poller(self, 30, fetch_stuff)
            where you have def fetch_stuff(self) in your plugin

            :param interval: interval in seconds
            :param method: targetted method
            :param times:
                number of times polling should happen (defaults to``None``
                which causes the polling to happen indefinitely)
            :param args: args for the targetted method
            :param kwargs: kwargs for the targetting method

        """
        super().start_poller(interval, method, times, args, kwargs)

    def stop_poller(self,
                    method: Callable[..., None],
                    args: Tuple = None,
                    kwargs: Mapping = None):
        """
            stop poller(s).

            If the method equals None -> it stops all the pollers you need to
            regive the same parameters as the original start_poller to match a
            specific poller to stop

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

    def __init__(self, separator: str = None, maxsplit: int = -1):
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
