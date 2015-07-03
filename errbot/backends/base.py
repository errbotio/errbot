import difflib
import inspect
import io
import logging
import random
import time
import traceback
import warnings

from collections import deque, defaultdict
from xml.etree import cElementTree as ET
from xml.etree.cElementTree import ParseError

from errbot import botcmd, PY2
from errbot.utils import get_sender_username, xhtml2txt, split_string_after, deprecated
from errbot.templating import tenv
from errbot.bundled.threadpool import ThreadPool, WorkRequest

log = logging.getLogger(__name__)


class ACLViolation(Exception):
    """Exceptions raised when user is not allowed to execute given command due to ACLs"""


class RoomError(Exception):
    """General exception class for MUC-related errors"""


class RoomNotJoinedError(RoomError):
    """Exception raised when performing MUC operations
    that require the bot to have joined the room"""


class RoomDoesNotExistError(RoomError):
    """Exception that is raised when performing an operation
    on a room that doesn't exist"""


class UserDoesNotExistError(Exception):
    """Exception that is raised when performing an operation
    on a user that doesn't exist"""


class Message(object):
    """
    A chat message.

    This class represents chat messages that are sent or received by
    the bot. It is modeled after XMPP messages so not all methods
    make sense in the context of other back-ends.
    """

    def __init__(self, body, type_='chat', html=None):
        """
        :param body:
            The plaintext body of the message.
        :param type_:
            The type of message (generally one of either 'chat' or 'groupchat').
        :param html:
            An optional HTML representation of the body.
        """
        # it is either unicode or assume it is utf-8
        if isinstance(body, str):
            self._body = body
        else:
            self._body = body.decode('utf-8')
        self._html = html
        self._type = type_
        self._from = None
        self._to = None
        self._delayed = False
        self._nick = None

    @property
    def to(self):
        """
        Get the recipient of the message.

        :returns:
            An :class:`~errbot.backends.base.Identifier` identifying
            the recipient.
        """
        return self._to

    @to.setter
    def to(self, to):
        """
        Set the recipient of the message.

        :param to:
            An identifier from for example build_identifier().
        """
        if not hasattr(to, 'person'):
            raise Exception('`to` not an Identifier as it misses ''the "person" property. `to` : %s (%s)'
                            % (to, to.__class__))
        self._to = to

    @property
    def type(self):
        """
        Get the type of the message.

        :returns:
            The message type as a string (generally one of either
            'chat' or 'groupchat')
        """
        return self._type

    @type.setter
    def type(self, type_):
        """
        Set the type of the message.

        :param type_:
            The message type (generally one of either 'chat'
            or 'groupchat').
        """
        self._type = type_

    @property
    def frm(self):
        """
        Get the sender of the message.

        :returns:
            An :class:`~errbot.backends.base.Identifier` identifying
            the sender.
        """
        return self._from

    @frm.setter
    def frm(self, from_):
        """
        Set the sender of the message.

        :param from_:
            An identifier from build_identifier.
        """
        if not hasattr(from_, 'person'):
            raise Exception('`from_` not an Identifier as it misses the "person" property. from_ : %s (%s)'
                            % (from_, from_.__class__))
        self._from = from_

    @property
    def body(self):
        """
        Get the plaintext body of the message.

        :returns:
            The body as a string.
        """
        return self._body

    @property
    def html(self):
        """
        Get the HTML representation of the message.

        :returns:
            A string containing the HTML message or `None` when there
            is none.
        """
        return self._html

    @html.setter
    def html(self, html):
        """
        Set the HTML representation of the message

        :param html:
            The HTML message.
        """
        self._html = html

    @property
    def delayed(self):
        return self._delayed

    @delayed.setter
    def delayed(self, delayed):
        self._delayed = delayed

    @property
    def nick(self):
        return self._nick

    @nick.setter
    def nick(self, nick):
        self._nick = nick

    def __str__(self):
        return self._body

    # deprecated stuff ...

    @deprecated(to)
    def getTo(self):
        """ will be removed on the next version """

    @deprecated(to.fset)
    def setTo(self, to):
        """ will be removed on the next version """

    @deprecated(type)
    def getType(self):
        """ will be removed on the next version """

    @deprecated(type.fset)
    def setType(self, type_):
        """ will be removed on the next version """

    @deprecated(frm)
    def getFrom(self):
        """ will be removed on the next version """

    @deprecated(frm.fset)
    def setFrom(self, from_):
        """ will be removed on the next version """

    @deprecated(body)
    def getBody(self):
        """ will be removed on the next version """

    @deprecated(html)
    def getHTML(self):
        """ will be removed on the next version """

    @deprecated(html.fset)
    def setHTML(self, html):
        """ will be removed on the next version """

    @deprecated(delayed)
    def isDelayed(self):
        """ will be removed on the next version """

    @deprecated(delayed.fset)
    def setDelayed(self, delayed):
        """ will be removed on the next version """

    @deprecated(nick)
    def setMuckNick(self, nick):
        """ will be removed on the next version """

    @deprecated(nick.fset)
    def getMuckNick(self):
        """ will be removed on the next version """


ONLINE = 'online'
OFFLINE = 'offline'
AWAY = 'away'
DND = 'dnd'


class Presence(object):
    """
       This class represents a presence change for a user or a user in a chatroom.

       Instances of this class are passed to :meth:`~errbot.botplugin.BotPlugin.callback_presence`
       when the presence of people changes.
    """

    def __init__(self, nick=None, identifier=None, status=None, chatroom=None, message=None):
        if nick is None and identifier is None:
            raise ValueError('Presence: nick and identifiers are both None')
        if nick is None and chatroom is not None:
            raise ValueError('Presence: nick is None when chatroom is not')
        if status is None and message is None:
            raise ValueError('Presence: at least a new status or a new status message mustbe present')
        self._nick = nick
        self._identifier = identifier
        self._chatroom = chatroom
        self._status = status
        self._message = message

    @property
    def chatroom(self):
        """ Returns the identifier pointing the room in which the event occurred.
            If it returns None, the event occurred outside of a chatroom.
        """
        return self._chatroom

    @property
    def nick(self):
        """ Returns a plain string of the presence nick.
            (In some chatroom implementations, you cannot know the real identifier
            of a person in it).
            Can return None but then identifier won't be None.
        """
        return self._nick

    @property
    def identifier(self):
        """ Returns the identifier of the event.
            Can be None *only* if chatroom is not None
        """
        return self._identifier

    @property
    def status(self):
        """ Returns the status of the presence change.
            It can be one of the constants ONLINE, OFFLINE, AWAY, DND, but
            can also be custom statuses depending on backends.
            It can be None if it is just an update of the status message (see get_message)
        """
        return self._status

    @property
    def message(self):
        """ Returns a human readable message associated with the status if any.
            like : "BRB, washing the dishes"
            It can be None if it is only a general status update (see get_status)
        """
        return self._message

    def __str__(self):
        response = ''
        if self._nick:
            response += 'Nick:%s ' % self._nick
        if self._identifier:
            response += 'Idd:%s ' % self._identifier
        if self._status:
            response += 'Status:%s ' % self._status
        if self._chatroom:
            response += 'Room:%s ' % self._chatroom
        if self._message:
            response += 'Msg:%s ' % self._message
        return response

    def __unicode__(self):
        return str(self.__str__())

STREAM_WAITING_TO_START = 'pending'
STREAM_TRANSFER_IN_PROGRESS = 'in progress'
STREAM_SUCCESSFULLY_TRANSFERED = 'success'
STREAM_PAUSED = 'paused'
STREAM_ERROR = 'error'
STREAM_REJECTED = 'rejected'

DEFAULT_REASON = 'unknown'


class Stream(io.BufferedReader):
    """
       This class represents a stream request.

       Instances of this class are passed to :meth:`~errbot.botplugin.BotPlugin.callback_stream`
       when an incoming stream is requested.
    """

    def __init__(self, identifier, fsource, name=None, size=None, stream_type=None):
        super(Stream, self).__init__(fsource)
        self._identifier = identifier
        self._name = name
        self._size = size
        self._stream_type = stream_type
        self._status = STREAM_WAITING_TO_START
        self._reason = DEFAULT_REASON

    @property
    def identifier(self):
        """
           The identity the stream is coming from if it is an incoming request
           or to if it is an outgoing request.
        """
        return self._identifier

    @property
    def name(self):
        """
            The name of the stream/file if it has one or None otherwise.
            !! Be carefull of injections if you are using this name directly as a filename.
        """
        return self._name

    @property
    def size(self):
        """
            The expected size in bytes of the stream if it is known or None.
        """
        return self._size

    @property
    def stream_type(self):
        """
            The mimetype of the stream if it is known or None.
        """
        return self._stream_type

    @property
    def status(self):
        """
            The status for this stream.
        """
        return self._status

    def accept(self):
        """
            Signal that the stream has been accepted.
        """
        if self._status != STREAM_WAITING_TO_START:
            raise ValueError("Invalid state, the stream is not pending.")
        self._status = STREAM_TRANSFER_IN_PROGRESS

    def reject(self):
        """
            Signal that the stream has been rejected.
        """
        if self._status != STREAM_WAITING_TO_START:
            raise ValueError("Invalid state, the stream is not pending.")
        self._status = STREAM_REJECTED

    def error(self, reason=DEFAULT_REASON):
        """
            An internal plugin error prevented the transfer.
        """
        self._status = STREAM_ERROR
        self._reason = reason

    def success(self):
        """
            The streaming finished normally.
        """
        if self._status != STREAM_TRANSFER_IN_PROGRESS:
            raise ValueError("Invalid state, the stream is not in progress.")
        self._status = STREAM_SUCCESSFULLY_TRANSFERED

    def clone(self, new_fsource):
        """
            Creates a clone and with an alternative stream
        """
        return Stream(self._identifier, new_fsource, self._name, self._size, self._stream_type)


class MUCRoom(object):
    """
    This class represents a Multi-User Chatroom.
    """

    def join(self, username=None, password=None):
        """
        Join the room.

        If the room does not exist yet, this will automatically call
        :meth:`create` on it first.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def leave(self, reason=None):
        """
        Leave the room.

        :param reason:
            An optional string explaining the reason for leaving the room.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def create(self):
        """
        Create the room.

        Calling this on an already existing room is a no-op.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def destroy(self):
        """
        Destroy the room.

        Calling this on a non-existing room is a no-op.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    @property
    def exists(self):
        """
        Boolean indicating whether this room already exists or not.

        :getter:
            Returns `True` if the room exists, `False` otherwise.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    @property
    def joined(self):
        """
        Boolean indicating whether this room has already been joined.

        :getter:
            Returns `True` if the room has been joined, `False` otherwise.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    @property
    def topic(self):
        """
        The room topic.

        :getter:
            Returns the topic (a string) if one is set, `None` if no
            topic has been set at all.

            .. note::
                Back-ends may return an empty string rather than `None`
                when no topic has been set as a network may not
                differentiate between no topic and an empty topic.
        :raises:
            :class:`~MUCNotJoinedError` if the room has not yet been joined.

        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    @topic.setter
    def topic(self, topic):
        """
        Set the room's topic.

        :param topic:
            The topic to set.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    @property
    def occupants(self):
        """
        The room's occupants.

        :getter:
            Returns a list of occupant identities.
        :raises:
            :class:`~MUCNotJoinedError` if the room has not yet been joined.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def invite(self, *args):
        """
        Invite one or more people into the room.

        :*args:
            One or more JID's to invite into the room.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")


def build_text_html_message_pair(source):
    node = None
    text_plain = None

    try:
        node = ET.XML(source)
        text_plain = xhtml2txt(source)
    except ParseError as ee:
        if source.strip():  # avoids keep alive pollution
            log.debug('Could not parse [%s] as XHTML-IM, assume pure text Parsing error = [%s]' % (source, ee))
            text_plain = source
    except UnicodeEncodeError:
        text_plain = source
    return text_plain, node


def build_message(text, message_class, conversion_function=None):
    """Builds an xhtml message without attributes.
    If input is not valid xhtml-im fallback to normal."""
    message = None  # keeps the compiler happy
    try:
        text = text.replace('', '*')  # there is a weird chr IRC is sending that we need to filter out
        if PY2:
            ET.XML(text.encode('utf-8'))  # test if is it xml
        else:
            ET.XML(text)

        edulcorated_html = conversion_function(text) if conversion_function else text
        try:
            text_plain, node = build_text_html_message_pair(edulcorated_html)
            message = message_class(body=text_plain)
            message.html = node
        except ET.ParseError as ee:
            log.error('Error translating to hipchat [%s] Parsing error = [%s]' % (edulcorated_html, ee))
    except ET.ParseError as ee:
        if text.strip():  # avoids keep alive pollution
            log.debug('Determined that [%s] is not XHTML-IM (%s)' % (text, ee))
        message = message_class(body=text)
    return message


class Backend(object):
    """
    Implements the basic Bot logic (logic independent from the backend) and leaves
    you to implement the missing parts
    """

    cmd_history = defaultdict(lambda: deque(maxlen=10))  # this will be a per user history

    MSG_ERROR_OCCURRED = 'Sorry for your inconvenience. ' \
                         'An unexpected error occurred.'

    MSG_HELP_TAIL = 'Type help <command name> to get more info ' \
                    'about that specific command.'
    MSG_HELP_UNDEFINED_COMMAND = 'That command is not defined.'

    def __init__(self, config):
        """ Those arguments will be directly those put in BOT_IDENTITY
        """
        self._reconnection_count = 0          # Increments with each failed (re)connection
        self._reconnection_delay = 1          # Amount of seconds the bot will sleep on the
        #                                     # next reconnection attempt
        self._reconnection_max_delay = 600    # Maximum delay between reconnection attempts
        self._reconnection_multiplier = 1.75  # Delay multiplier
        self._reconnection_jitter = (0, 3)    # Random jitter added to delay (min, max)

        if config.BOT_ASYNC:
            self.thread_pool = ThreadPool(3)
            log.debug('created the thread pool' + str(self.thread_pool))
        self.commands = {}  # the dynamically populated list of commands available on the bot
        self.re_commands = {}  # the dynamically populated list of regex-based commands available on the bot
        self.MSG_UNKNOWN_COMMAND = 'Unknown command: "%(command)s". ' \
                                   'Type "' + config.BOT_PREFIX + 'help" for available commands.'
        if config.BOT_ALT_PREFIX_CASEINSENSITIVE:
            self.bot_alt_prefixes = tuple(prefix.lower() for prefix in config.BOT_ALT_PREFIXES)
        else:
            self.bot_alt_prefixes = config.BOT_ALT_PREFIXES

    def send_message(self, mess):
        """Should be overridden by backends"""
        raise NotImplementedError("send_message should be implemented by the backend")

    def send_simple_reply(self, mess, text, private=False):
        """Send a simple response to a message"""
        self.send_message(self.build_reply(mess, text, private))

    def build_reply(self, mess, text=None, private=False):
        """ Should be implemented by the backend """
        raise NotImplementedError("build_reply should be implemented by the backend %s" % self.__class__)

    def callback_presence(self, presence):
        """
           Implemented by errBot.
        """
        pass

    def callback_room_joined(self, room):
        """
            See :class:`~errbot.errBot.ErrBot`
        """
        pass

    def callback_room_left(self, room):
        """
            See :class:`~errbot.errBot.ErrBot`
        """
        pass

    def callback_room_topic(self, room):
        """
            See :class:`~errbot.errBot.ErrBot`
        """
        pass

    def callback_message(self, mess):
        """
        Needs to return False if we want to stop further treatment
        """
        # Prepare to handle either private chats or group chats
        type_ = mess.type
        jid = mess.frm
        text = mess.body
        if not hasattr(mess.frm, 'person'):
            raise Exception('mess.frm not an Identifier as it misses the "person" property. Class of frm : %s'
                            % mess.frm.__class__)

        username = mess.frm.person
        user_cmd_history = self.cmd_history[username]

        if mess.delayed:
            log.debug("Message from history, ignore it")
            return False

        if type_ not in ("groupchat", "chat"):
            log.debug("unhandled message type %s" % mess)
            return False

        # Ignore messages from ourselves. Because it isn't always possible to get the
        # real JID from a MUC participant (including ourself), matching the JID against
        # ourselves isn't enough (see https://github.com/gbin/err/issues/90 for
        # background discussion on this). Matching against CHATROOM_FN isn't technically
        # correct in all cases because a MUC could give us another nickname, but it
        # covers 99% of the MUC cases, so it should suffice for the time being.
        if (jid.person == self.jid.person or
            type_ == "groupchat" and mess.nick == self.bot_config.CHATROOM_FN):  # noqa
                log.debug("Ignoring message from self")
                return False

        log.debug("*** jid = %s" % jid)
        log.debug("*** username = %s" % username)
        log.debug("*** type = %s" % type_)
        log.debug("*** text = %s" % text)

        # If a message format is not supported (eg. encrypted),
        # txt will be None
        if not text:
            return False

        surpress_cmd_not_found = False

        prefixed = False  # Keeps track whether text was prefixed with a bot prefix
        only_check_re_command = False  # Becomes true if text is determed to not be a regular command
        tomatch = text.lower() if self.bot_config.BOT_ALT_PREFIX_CASEINSENSITIVE else text
        if len(self.bot_config.BOT_ALT_PREFIXES) > 0 and tomatch.startswith(self.bot_alt_prefixes):
            # Yay! We were called by one of our alternate prefixes. Now we just have to find out
            # which one... (And find the longest matching, in case you have 'err' and 'errbot' and
            # someone uses 'errbot', which also matches 'err' but would leave 'bot' to be taken as
            # part of the called command in that case)
            prefixed = True
            longest = 0
            for prefix in self.bot_alt_prefixes:
                l = len(prefix)
                if tomatch.startswith(prefix) and l > longest:
                    longest = l
            log.debug("Called with alternate prefix '{}'".format(text[:longest]))
            text = text[longest:]

            # Now also remove the separator from the text
            for sep in self.bot_config.BOT_ALT_PREFIX_SEPARATORS:
                # While unlikely, one may have separators consisting of
                # more than one character
                l = len(sep)
                if text[:l] == sep:
                    text = text[l:]
        elif type_ == "chat" and self.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT:
            log.debug("Assuming '%s' to be a command because BOT_PREFIX_OPTIONAL_ON_CHAT is True" % text)
            # In order to keep noise down we surpress messages about the command
            # not being found, because it's possible a plugin will trigger on what
            # was said with trigger_message.
            surpress_cmd_not_found = True
        elif not text.startswith(self.bot_config.BOT_PREFIX):
            only_check_re_command = True
        if text.startswith(self.bot_config.BOT_PREFIX):
            text = text[len(self.bot_config.BOT_PREFIX):]
            prefixed = True

        text = text.strip()
        text_split = text.split(' ')
        cmd = None
        command = None
        args = ''
        if not only_check_re_command:
            if len(text_split) > 1:
                command = (text_split[0] + '_' + text_split[1]).lower()
                if command in self.commands:
                    cmd = command
                    args = ' '.join(text_split[2:])

            if not cmd:
                command = text_split[0].lower()
                args = ' '.join(text_split[1:])
                if command in self.commands:
                    cmd = command
                    if len(text_split) > 1:
                        args = ' '.join(text_split[1:])

            if command == self.bot_config.BOT_PREFIX:  # we did "!!" so recall the last command
                if len(user_cmd_history):
                    cmd, args = user_cmd_history[-1]
                else:
                    return False  # no command in history
            elif command.isdigit():  # we did "!#" so we recall the specified command
                index = int(command)
                if len(user_cmd_history) >= index:
                    cmd, args = user_cmd_history[-index]
                else:
                    return False  # no command in history

        # Try to match one of the regex commands if the regular commands produced no match
        matched_on_re_command = False
        if not cmd:
            if prefixed:
                commands = self.re_commands
            else:
                commands = {k: self.re_commands[k] for k in self.re_commands
                            if not self.re_commands[k]._err_command_prefix_required}

            for name, func in commands.items():
                if func._err_command_matchall:
                    match = list(func._err_command_re_pattern.finditer(text))
                else:
                    match = func._err_command_re_pattern.search(text)
                if match:
                    log.debug("Matching '{}' against '{}' produced a match"
                              .format(text, func._err_command_re_pattern.pattern))
                    matched_on_re_command = True
                    self._process_command(mess, name, text, match)
                else:
                    log.debug("Matching '{}' against '{}' produced no match"
                              .format(text, func._err_command_re_pattern.pattern))
        if matched_on_re_command:
            return True

        if cmd:
            self._process_command(mess, cmd, args, match=None)
        elif not only_check_re_command:
            log.debug("Command not found")
            if surpress_cmd_not_found:
                log.debug("Surpressing command not found feedback")
            else:
                reply = self.unknown_command(mess, command, args)
                if reply is None:
                    reply = self.MSG_UNKNOWN_COMMAND % {'command': command}
                if reply:
                    self.send_simple_reply(mess, reply)
        return True

    def _process_command(self, mess, cmd, args, match):
        """Process and execute a bot command"""

        jid = mess.frm
        username = jid.person
        user_cmd_history = self.cmd_history[username]

        log.info("Processing command '{}' with parameters '{}' from {}".format(cmd, args, jid))

        if (cmd, args) in user_cmd_history:
            user_cmd_history.remove((cmd, args))  # Avoids duplicate history items

        try:
            self.check_command_access(mess, cmd)
        except ACLViolation as e:
            if not self.bot_config.HIDE_RESTRICTED_ACCESS:
                self.send_simple_reply(mess, str(e))
            return

        f = self.re_commands[cmd] if match else self.commands[cmd]

        if f._err_command_admin_only and self.bot_config.BOT_ASYNC:
            # If it is an admin command, wait until the queue is completely depleted so
            # we don't have strange concurrency issues on load/unload/updates etc...
            self.thread_pool.wait()

        if f._err_command_historize:
            user_cmd_history.append((cmd, args))  # add it to the history only if it is authorized to be so

        # Don't check for None here as None can be a valid argument to str.split.
        # '' was chosen as default argument because this isn't a valid argument to str.split()
        if not match and f._err_command_split_args_with != '':
            try:
                if hasattr(f._err_command_split_args_with, "parse_args"):
                    args = f._err_command_split_args_with.parse_args(args)
                elif callable(f._err_command_split_args_with):
                    args = f._err_command_split_args_with(args)
                else:
                    args = args.split(f._err_command_split_args_with)
            except Exception as e:
                self.send_simple_reply(
                    mess,
                    "Sorry, I couldn't parse your arguments. {}".format(e)
                )
                return

        if self.bot_config.BOT_ASYNC:
            wr = WorkRequest(
                self._execute_and_send,
                [],
                {'cmd': cmd, 'args': args, 'match': match, 'mess': mess,
                 'template_name': f._err_command_template}
            )
            self.thread_pool.putRequest(wr)
            if f._err_command_admin_only:
                # Again, if it is an admin command, wait until the queue is completely
                # depleted so we don't have strange concurrency issues.
                self.thread_pool.wait()
        else:
            self._execute_and_send(cmd=cmd, args=args, match=match, mess=mess,
                                   template_name=f._err_command_template)

    def _execute_and_send(self, cmd, args, match, mess, template_name=None):
        """Execute a bot command and send output back to the caller

        cmd: The command that was given to the bot (after being expanded)
        args: Arguments given along with cmd
        match: A re.MatchObject if command is coming from a regex-based command, else None
        mess: The message object
        template_name: The name of the template which should be used to render
            html-im output, if any

        """
        def process_reply(reply_):
            # integrated templating
            if template_name:
                reply_ = tenv().get_template(template_name + '.html').render(**reply_)

            # Reply should be all text at this point (See https://github.com/gbin/err/issues/96)
            return str(reply_)

        def send_reply(reply_):
            for part in split_string_after(reply_, self.bot_config.MESSAGE_SIZE_LIMIT):
                self.send_simple_reply(mess, part, cmd in self.bot_config.DIVERT_TO_PRIVATE)

        commands = self.re_commands if match else self.commands
        try:
            if inspect.isgeneratorfunction(commands[cmd]):
                replies = commands[cmd](mess, match) if match else commands[cmd](mess, args)
                for reply in replies:
                    if reply:
                        send_reply(process_reply(reply))
            else:
                reply = commands[cmd](mess, match) if match else commands[cmd](mess, args)
                if reply:
                    send_reply(process_reply(reply))
        except Exception as e:
            tb = traceback.format_exc()
            log.exception('An error happened while processing '
                          'a message ("%s"): %s"' %
                          (mess.body, tb))
            send_reply(self.MSG_ERROR_OCCURRED + ':\n %s' % e)

    def is_admin(self, usr):
        """
        an overridable check to see if a user is an administrator
        """
        return usr in self.bot_config.BOT_ADMINS

    def check_command_access(self, mess, cmd):
        """
        Check command against ACL rules

        Raises ACLViolation() if the command may not be executed in the given context
        """
        usr = str(mess.frm.person)
        typ = mess.type

        if cmd not in self.bot_config.ACCESS_CONTROLS:
            self.bot_config.ACCESS_CONTROLS[cmd] = self.bot_config.ACCESS_CONTROLS_DEFAULT

        if ('allowusers' in self.bot_config.ACCESS_CONTROLS[cmd] and
           usr not in self.bot_config.ACCESS_CONTROLS[cmd]['allowusers']):
            raise ACLViolation("You're not allowed to access this command from this user")
        if ('denyusers' in self.bot_config.ACCESS_CONTROLS[cmd] and
           usr in self.bot_config.ACCESS_CONTROLS[cmd]['denyusers']):
            raise ACLViolation("You're not allowed to access this command from this user")
        if typ == 'groupchat':
            if not hasattr(mess.frm, 'room'):
                raise Exception('mess.frm is not a MUCIdentifier as it misses the "room" property. Class of frm : %s'
                                % mess.frm.__class__)
            room = str(mess.frm.room)
            if ('allowmuc' in self.bot_config.ACCESS_CONTROLS[cmd] and
               self.bot_config.ACCESS_CONTROLS[cmd]['allowmuc'] is False):
                raise ACLViolation("You're not allowed to access this command from a chatroom")
            if ('allowrooms' in self.bot_config.ACCESS_CONTROLS[cmd] and
               room not in self.bot_config.ACCESS_CONTROLS[cmd]['allowrooms']):
                raise ACLViolation("You're not allowed to access this command from this room")
            if ('denyrooms' in self.bot_config.ACCESS_CONTROLS[cmd] and
               room in self.bot_config.ACCESS_CONTROLS[cmd]['denyrooms']):
                raise ACLViolation("You're not allowed to access this command from this room")
        else:
            if ('allowprivate' in self.bot_config.ACCESS_CONTROLS[cmd] and
               self.bot_config.ACCESS_CONTROLS[cmd]['allowprivate'] is False):
                raise ACLViolation("You're not allowed to access this command via private message to me")

        f = self.commands[cmd] if cmd in self.commands else self.re_commands[cmd]

        if f._err_command_admin_only:
            if typ == 'groupchat':
                raise ACLViolation("You cannot administer the bot from a chatroom, message the bot directly")
            if not self.is_admin(usr):
                raise ACLViolation("This command requires bot-admin privileges")

    def unknown_command(self, _, cmd, args):
        """ Override the default unknown command behavior
        """
        full_cmd = cmd + ' ' + args.split(' ')[0] if args else None
        if full_cmd:
            part1 = 'Command "%s" / "%s" not found.' % (cmd, full_cmd)
        else:
            part1 = 'Command "%s" not found.' % cmd
        ununderscore_keys = [m.replace('_', ' ') for m in self.commands.keys()]
        matches = difflib.get_close_matches(cmd, ununderscore_keys)
        if full_cmd:
            matches.extend(difflib.get_close_matches(full_cmd, ununderscore_keys))
        matches = set(matches)
        if matches:
            return (part1 + '\n\nDid you mean "' + self.bot_config.BOT_PREFIX +
                    ('" or "' + self.bot_config.BOT_PREFIX).join(matches) + '" ?')
        else:
            return part1

    def inject_commands_from(self, instance_to_inject):
        classname = instance_to_inject.__class__.__name__
        for name, value in inspect.getmembers(instance_to_inject, inspect.ismethod):
            if getattr(value, '_err_command', False):
                commands = self.re_commands if getattr(value, '_err_re_command') else self.commands
                name = getattr(value, '_err_command_name')

                if name in commands:
                    f = commands[name]
                    new_name = (classname + '-' + name).lower()
                    self.warn_admins('%s.%s clashes with %s.%s so it has been renamed %s' % (
                        classname, name, type(f.__self__).__name__, f.__name__, new_name))
                    name = new_name
                commands[name] = value

                if getattr(value, '_err_re_command'):
                    log.debug('Adding regex command : %s -> %s' % (name, value.__name__))
                    self.re_commands = commands
                else:
                    log.debug('Adding command : %s -> %s' % (name, value.__name__))
                    self.commands = commands

    def remove_commands_from(self, instance_to_inject):
        for name, value in inspect.getmembers(instance_to_inject, inspect.ismethod):
            if getattr(value, '_err_command', False):
                name = getattr(value, '_err_command_name')
                if getattr(value, '_err_re_command') and name in self.re_commands:
                    del (self.re_commands[name])
                elif not getattr(value, '_err_re_command') and name in self.commands:
                    del (self.commands[name])

    def warn_admins(self, warning):
        for admin in self.bot_config.BOT_ADMINS:
            self.send(admin, warning)

    def top_of_help_message(self):
        """Returns a string that forms the top of the help message

        Override this method in derived class if you
        want to add additional help text at the
        beginning of the help message.
        """
        return ""

    def bottom_of_help_message(self):
        """Returns a string that forms the bottom of the help message

        Override this method in derived class if you
        want to add additional help text at the end
        of the help message.
        """
        return ""

    @botcmd
    def help(self, mess, args):
        """   Returns a help string listing available options.

        Automatically assigned to the "help" command."""
        if not args:
            if self.__doc__:
                description = self.__doc__.strip()
            else:
                description = 'Available commands:'

            usage = '\n'.join(sorted([
                self.bot_config.BOT_PREFIX + '%s: %s' % (name, (command.__doc__ or
                                                         '(undocumented)').strip().split('\n', 1)[0])
                for (name, command) in self.commands.items()
                if name != 'help' and not command._err_command_hidden
            ]))
            usage = '\n\n' + '\n\n'.join(filter(None, [usage, self.MSG_HELP_TAIL]))
        else:
            description = ''
            if args in self.commands:
                usage = (self.commands[args].__doc__ or
                         'undocumented').strip()
            else:
                usage = self.MSG_HELP_UNDEFINED_COMMAND

        top = self.top_of_help_message()
        bottom = self.bottom_of_help_message()
        return ''.join(filter(None, [top, description, usage, bottom]))

    def send(self, user, text, in_reply_to=None, message_type='chat', groupchat_nick_reply=False):
        """Sends a simple message to the specified user.
           user is a textual representation of its identity (backward compatibility).
        """

        nick_reply = self.bot_config.GROUPCHAT_NICK_PREFIXED

        if (message_type == 'groupchat' and in_reply_to and nick_reply and groupchat_nick_reply):
            reply_text = self.groupchat_reply_format().format(in_reply_to.nick, text)
        else:
            reply_text = text

        mess = self.build_message(reply_text)
        mess.to = self.build_identifier(user)

        if in_reply_to:
            mess.type = in_reply_to.type
            mess.frm = in_reply_to.to
        else:
            mess.type = message_type
            mess.frm = self.jid

        self.send_message(mess)

    def serve_forever(self):
        """
        Connect the back-end to the server and serve forever.

        Back-ends MAY choose to re-implement this method, in which case
        they are responsible for implementing reconnection logic themselves.

        Back-ends SHOULD trigger :func:`~connect_callback()` and
        :func:`~disconnect_callback()` themselves after connection/disconnection.
        """
        while True:
            try:
                if self.serve_once():
                    break  # Truth-y exit from serve_once means shutdown was requested
            except KeyboardInterrupt:
                log.info("Interrupt received, shutting down..")
                break
            except:
                log.exception("Exception occurred in serve_once:")

            log.info(
                "Reconnecting in {delay} seconds ({count} attempted reconnections so far)".format(
                    delay=self._reconnection_delay, count=self._reconnection_count)
            )
            try:
                self._delay_reconnect()
                self._reconnection_count += 1
            except KeyboardInterrupt:
                log.info("Interrupt received, shutting down..")
                break

        log.info("Trigger shutdown")
        self.shutdown()

    def _delay_reconnect(self):
        """Delay next reconnection attempt until a suitable back-off time has passed"""
        time.sleep(self._reconnection_delay)

        self._reconnection_delay *= self._reconnection_multiplier
        if self._reconnection_delay > self._reconnection_max_delay:
            self._reconnection_delay = self._reconnection_max_delay
        self._reconnection_delay += random.uniform(*self._reconnection_jitter)

    def reset_reconnection_count(self):
        """
        Reset the reconnection count. Back-ends should call this after
        successfully connecting.
        """
        self._reconnection_count = 0
        self._reconnection_delay = 1

    # ##### HERE ARE THE SPECIFICS TO IMPLEMENT PER BACKEND

    def groupchat_reply_format(self):
        raise NotImplementedError("It should be implemented specifically for your backend")

    def build_message(self, text):
        raise NotImplementedError("It should be implemented specifically for your backend")

    def build_identifier(self, text_representation):
        raise NotImplementedError("It should be implemented specifically for your backend")

    def serve_once(self):
        """
        Connect the back-end to the server and serve a connection once
        (meaning until disconnected for any reason).

        Back-ends MAY choose not to implement this method, IF they implement a custom
        :func:`~serve_forever`.

        This function SHOULD raise an exception or return a value that evaluates
        to False in order to signal something went wrong. A return value that
        evaluates to True will signal the bot that serving is done and a shut-down
        is requested.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def connect(self):
        """Connects the bot to server or returns current connection
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def join_room(self, room, username=None, password=None):
        """
        Join a room (MUC).

        :param room:
            The JID/identifier of the room to join.
        :param username:
            An optional username to use.
        :param password:
            An optional password to use (for password-protected rooms).

        .. deprecated:: 2.2.0
            Use the methods on :class:`MUCRoom` instead.
        """
        warnings.warn(
            "Using join_room is deprecated, use query_room and the join "
            "method on the resulting response instead.",
            DeprecationWarning
        )
        self.query_room(room).join(username=username, password=password)

    def query_room(self, room):
        """
        Query a room for information.

        :param room:
            The room to query for.
        :returns:
            An instance of :class:`~MUCRoom`.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def shutdown(self):
        pass

    def connect_callback(self):
        pass

    def disconnect_callback(self):
        pass

    @property
    def mode(self):
        raise NotImplementedError("It should be implemented specifically for your backend")

    def rooms(self):
        """
        Return a list of rooms the bot is currently in.

        :returns:
            A list of :class:`~errbot.backends.base.MUCRoom` instances.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")
