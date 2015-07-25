import io
import logging
import random
import time
import warnings

from collections import deque, defaultdict
from xml.etree import cElementTree as ET
from xml.etree.cElementTree import ParseError

from errbot import botcmd, PY2
from errbot.utils import get_sender_username, deprecated, compat_str

# Backward-compatibility in case there are plugins importing them from
# this module still. These were moved in Err 3.0.0 so this should be
# removed when 4.0.0 is released.
from errbot.exceptions import (
    ACLViolation, RoomError, RoomNotJoinedError, RoomDoesNotExistError,
    UserDoesNotExistError
)

log = logging.getLogger(__name__)


class Message(object):
    """
    A chat message.

    This class represents chat messages that are sent or received by
    the bot. It is modeled after XMPP messages so not all methods
    make sense in the context of other back-ends.
    """

    def __init__(self, body='', type_='chat', frm=None, to=None, delayed=False):
        """
        :param body:
            The plaintext body of the message.
        :param type_:
            The type of message (generally one of either 'chat' or 'groupchat').
        """
        self._body = compat_str(body)
        self._type = type_
        self._from = frm
        self._to = to
        self._delayed = delayed

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

    @body.setter
    def body(self, body):
        self._body = body

    @property
    def delayed(self):
        return self._delayed

    @delayed.setter
    def delayed(self, delayed):
        self._delayed = delayed

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

    @deprecated(delayed)
    def isDelayed(self):
        """ will be removed on the next version """

    @deprecated(delayed.fset)
    def setDelayed(self, delayed):
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
        self._transfered = 0

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
    def transfered(self):
        """
            The currently transfered size.
        """
        return self._transfered

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

    def ack_data(self, length):
        """ Acknowledge data has been transfered. """
        self._transfered = length


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
            One or more identifiers to invite into the room.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")


class Backend(object):
    """
    Implements the basic Bot logic (logic independent from the backend) and leaves
    you to implement the missing parts.
    """

    cmd_history = defaultdict(lambda: deque(maxlen=10))  # this will be a per user history

    MSG_ERROR_OCCURRED = 'Sorry for your inconvenience. ' \
                         'An unexpected error occurred.'

    def __init__(self, _):
        """ Those arguments will be directly those put in BOT_IDENTITY
        """
        log.debug("Backend init.")
        self._reconnection_count = 0          # Increments with each failed (re)connection
        self._reconnection_delay = 1          # Amount of seconds the bot will sleep on the
        #                                     # next reconnection attempt
        self._reconnection_max_delay = 600    # Maximum delay between reconnection attempts
        self._reconnection_multiplier = 1.75  # Delay multiplier
        self._reconnection_jitter = (0, 3)    # Random jitter added to delay (min, max)

    def send_message(self, mess):
        """Should be overridden by backends with a super().send_message() call."""

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

    def build_message(self, text):
        """ You might want to override this one depending on your backend """
        return Message(body=text)

    # ##### HERE ARE THE SPECIFICS TO IMPLEMENT PER BACKEND

    def prefix_groupchat_reply(self, message, identifier):
        """ Patches message with the conventional prefix to ping the specific contact
        For example:
        @gbin, you forgot the milk !
        """
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
            The identifier of the room to join.
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
