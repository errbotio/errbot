import io
import logging
import random
import time
from typing import Any, Mapping, BinaryIO, List, Sequence, Tuple
from abc import ABC, abstractmethod
from collections import deque, defaultdict

log = logging.getLogger(__name__)


class Identifier(ABC):
    """This is just use for type hinting representing the Identifier contract,
    NEVER TRY TO SUBCLASS IT OUTSIDE OF A BACKEND, it is just here to show you what you can expect from an Identifier.
    To get an instance of a real identifier, always use the properties from Message (to, from) or self.build_identifier
     to make an identifier from a String.

     The semantics is anything you can talk to: Person, Room, RoomOccupant etc.
    """
    pass


class Person(Identifier):
    """This is just use for type hinting representing the Identifier contract,
    NEVER TRY TO SUBCLASS IT OUTSIDE OF A BACKEND, it is just here to show you what you can expect from an Identifier.
    To get an instance of a real identifier, always use the properties from Message (to, from) or self.build_identifier
     to make an identifier from a String.
    """

    @property
    @abstractmethod
    def person(self) -> str:
        """
        :return: a backend specific unique identifier representing the person you are talking to.
        """
        pass

    @property
    @abstractmethod
    def client(self) -> str:
        """
        :return: a backend specific unique identifier representing the device or client the person is using to talk.
        """
        pass

    @property
    @abstractmethod
    def nick(self) -> str:
        """
        :return: a backend specific nick returning the nickname of this person if available.
        """
        pass

    @property
    @abstractmethod
    def aclattr(self) -> str:
        """
        :return: returns the unique identifier that will be used for ACL matches.
        """
        pass

    @property
    @abstractmethod
    def fullname(self) -> str:
        """
        Some backends have the full name of a user.

        :return: the fullname of this user if available.
        """
        pass


class RoomOccupant(Identifier):
    @property
    @abstractmethod
    def room(self) -> Any:  # this is oom defined below
        """
        Some backends have the full name of a user.

        :return: the fullname of this user if available.
        """
        pass


class Room(Identifier):
    """
    This class represents a Multi-User Chatroom.
    """

    def join(self, username: str = None, password: str = None) -> None:
        """
        Join the room.

        If the room does not exist yet, this will automatically call
        :meth:`create` on it first.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def leave(self, reason: str = None) -> None:
        """
        Leave the room.

        :param reason:
            An optional string explaining the reason for leaving the room.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def create(self) -> None:
        """
        Create the room.

        Calling this on an already existing room is a no-op.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def destroy(self) -> None:
        """
        Destroy the room.

        Calling this on a non-existing room is a no-op.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    @property
    def exists(self) -> bool:
        """
        Boolean indicating whether this room already exists or not.

        :getter:
            Returns `True` if the room exists, `False` otherwise.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    @property
    def joined(self) -> bool:
        """
        Boolean indicating whether this room has already been joined.

        :getter:
            Returns `True` if the room has been joined, `False` otherwise.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    @property
    def topic(self) -> str:
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
    def topic(self, topic: str) -> None:
        """
        Set the room's topic.

        :param topic:
            The topic to set.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    @property
    def occupants(self) -> List[RoomOccupant]:
        """
        The room's occupants.

        :getter:
            Returns a list of occupant identities.
        :raises:
            :class:`~MUCNotJoinedError` if the room has not yet been joined.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def invite(self, *args) -> None:
        """
        Invite one or more people into the room.

        :*args:
            One or more identifiers to invite into the room.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")


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
    the bot.
    """

    def __init__(self,
                 body: str = '',
                 frm: Identifier = None,
                 to: Identifier = None,
                 parent: 'Message' = None,
                 delayed: bool = False,
                 partial: bool = False,
                 extras: Mapping = None,
                 flow=None):
        """
        :param body:
            The markdown body of the message.
        :param extras:
            Extra data attached by a backend
        :param flow:
            The flow in which this message has been triggered.
        :param parent:
            The parent message of this message in a thread. (Not supported by all backends)
        :param partial:
            Indicates whether the message was obtained by breaking down the message to fit
            the ``MESSAGE_SIZE_LIMIT``.
        """
        self._body = body
        self._from = frm
        self._to = to
        self._parent = parent
        self._delayed = delayed
        self._extras = extras or dict()
        self._flow = flow
        self._partial = partial

        # Convenience shortcut to the flow context
        if flow:
            self.ctx = flow.ctx
        else:
            self.ctx = {}

    def clone(self):
        return Message(body=self._body, frm=self._from, to=self._to, parent=self._parent,
                       delayed=self._delayed, partial=self._partial, extras=self._extras, flow=self._flow)

    @property
    def to(self) -> Identifier:
        """
        Get the recipient of the message.

        :returns:
            A backend specific identifier representing the recipient.
        """
        return self._to

    @to.setter
    def to(self, to: Identifier):
        """
        Set the recipient of the message.

        :param to:
            An identifier from for example build_identifier().
        """
        self._to = to

    @property
    def frm(self) -> Identifier:
        """
        Get the sender of the message.

        :returns:
            An :class:`~errbot.backends.base.Identifier` identifying
            the sender.
        """
        return self._from

    @frm.setter
    def frm(self, from_: Identifier):
        """
        Set the sender of the message.

        :param from_:
            An identifier from build_identifier.
        """
        self._from = from_

    @property
    def body(self) -> str:
        """
        Get the plaintext body of the message.

        :returns:
            The body as a string.
        """
        return self._body

    @body.setter
    def body(self, body: str):
        self._body = body

    @property
    def delayed(self) -> bool:
        return self._delayed

    @delayed.setter
    def delayed(self, delayed: bool):
        self._delayed = delayed

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent: 'Message'):
        self._parent = parent

    @property
    def extras(self) -> Mapping:
        return self._extras

    @property
    def flow(self):
        """
        Get the conversation flow for this message.

        :returns:
            A :class:`~errbot.Flow`
        """
        return self._from

    def __str__(self):
        return self._body

    @property
    def is_direct(self) -> bool:
        return isinstance(self.to, Person)

    @property
    def is_group(self) -> bool:
        return isinstance(self.to, Room)

    @property
    def is_threaded(self) -> bool:
        return self._parent is not None

    @property
    def partial(self) -> bool:
        return self._partial

    @partial.setter
    def partial(self, partial):
        self._partial = partial


class Card(Message):
    """
        Card is a special type of preformatted message. If it matches with a backend similar concept like on
        Slack or Hipchat it will be rendered natively, otherwise it will be sent as a regular message formatted with
        the card.md template.
    """

    def __init__(self,
                 body: str = '',
                 frm: Identifier = None,
                 to: Identifier = None,
                 parent: Message = None,
                 summary: str = None,
                 title: str = '',
                 link: str = None,
                 image: str = None,
                 thumbnail: str = None,
                 color: str = None,
                 fields: Tuple[Tuple[str, str]] = ()):
        """
        Creates a Card.
        :param body: main text of the card in markdown.
        :param frm: the card is sent from this identifier.
        :param to: the card is sent to this identifier (Room, RoomOccupant, Person...).
        :param parent: the parent message this card replies to. (threads the message if the backend supports it).
        :param summary: (optional) One liner summary of the card, possibly collapsed to it.
        :param title: (optional) Title possibly linking.
        :param link: (optional) url the title link is pointing to.
        :param image: (optional) link to the main image of the card.
        :param thumbnail: (optional) link to an icon / thumbnail.
        :param color: (optional) background color or color indicator.
        :param fields: (optional) a tuple of (key, value) pairs.
        """
        super().__init__(body=body, frm=frm, to=to, parent=parent)
        self._summary = summary
        self._title = title
        self._link = link
        self._image = image
        self._thumbnail = thumbnail
        self._color = color
        self._fields = fields

    @property
    def summary(self):
        return self._summary

    @property
    def title(self):
        return self._title

    @property
    def link(self):
        return self._link

    @property
    def image(self):
        return self._image

    @property
    def thumbnail(self):
        return self._thumbnail

    @property
    def color(self):
        return self._color

    @property
    def text_color(self):
        if self._color in ('black', 'blue'):
            return 'white'
        return 'black'

    @property
    def fields(self):
        return self._fields


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

    def __init__(self,
                 identifier: Identifier,
                 status: str = None,
                 message: str = None):
        if identifier is None:
            raise ValueError('Presence: identifiers is None')
        if status is None and message is None:
            raise ValueError('Presence: at least a new status or a new status message mustbe present')
        self._identifier = identifier
        self._status = status
        self._message = message

    @property
    def identifier(self) -> Identifier:
        """
        Identifier for whom its status changed. It can be a RoomOccupant or a Person.
        :return: the person or roomOccupant
        """
        return self._identifier

    @property
    def status(self) -> str:
        """ Returns the status of the presence change.
            It can be one of the constants ONLINE, OFFLINE, AWAY, DND, but
            can also be custom statuses depending on backends.
            It can be None if it is just an update of the status message (see get_message)
        """
        return self._status

    @property
    def message(self) -> str:
        """ Returns a human readable message associated with the status if any.
            like : "BRB, washing the dishes"
            It can be None if it is only a general status update (see get_status)
        """
        return self._message

    def __str__(self):
        response = ''
        if self._identifier:
            response += f'identifier: "{self._identifier}" '
        if self._status:
            response += f'status: "{self._status}" '
        if self._message:
            response += f'message: "{self._message}" '
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

    def __init__(self,
                 identifier: Identifier,
                 fsource: BinaryIO,
                 name: str = None,
                 size: int = None,
                 stream_type: str = None):
        super().__init__(fsource)
        self._identifier = identifier
        self._name = name
        self._size = size
        self._stream_type = stream_type
        self._status = STREAM_WAITING_TO_START
        self._reason = DEFAULT_REASON
        self._transfered = 0

    @property
    def identifier(self) -> Identifier:
        """
           The identity the stream is coming from if it is an incoming request
           or to if it is an outgoing request.
        """
        return self._identifier

    @property
    def name(self) -> str:
        """
            The name of the stream/file if it has one or None otherwise.
            !! Be carefull of injections if you are using this name directly as a filename.
        """
        return self._name

    @property
    def size(self) -> int:
        """
            The expected size in bytes of the stream if it is known or None.
        """
        return self._size

    @property
    def transfered(self) -> int:
        """
            The currently transfered size.
        """
        return self._transfered

    @property
    def stream_type(self) -> str:
        """
            The mimetype of the stream if it is known or None.
        """
        return self._stream_type

    @property
    def status(self) -> str:
        """
            The status for this stream.
        """
        return self._status

    def accept(self) -> None:
        """
            Signal that the stream has been accepted.
        """
        if self._status != STREAM_WAITING_TO_START:
            raise ValueError("Invalid state, the stream is not pending.")
        self._status = STREAM_TRANSFER_IN_PROGRESS

    def reject(self) -> None:
        """
            Signal that the stream has been rejected.
        """
        if self._status != STREAM_WAITING_TO_START:
            raise ValueError("Invalid state, the stream is not pending.")
        self._status = STREAM_REJECTED

    def error(self, reason=DEFAULT_REASON) -> None:
        """
            An internal plugin error prevented the transfer.
        """
        self._status = STREAM_ERROR
        self._reason = reason

    def success(self) -> None:
        """
            The streaming finished normally.
        """
        if self._status != STREAM_TRANSFER_IN_PROGRESS:
            raise ValueError("Invalid state, the stream is not in progress.")
        self._status = STREAM_SUCCESSFULLY_TRANSFERED

    def clone(self, new_fsource: BinaryIO) -> 'Stream':
        """
            Creates a clone and with an alternative stream
        """
        return Stream(self._identifier, new_fsource, self._name, self._size, self._stream_type)

    def ack_data(self, length: int) -> None:
        """ Acknowledge data has been transfered. """
        self._transfered = length


class Backend(ABC):
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
        self._reconnection_count = 0  # Increments with each failed (re)connection
        self._reconnection_delay = 1  # Amount of seconds the bot will sleep on the
        #                                     # next reconnection attempt
        self._reconnection_max_delay = 600  # Maximum delay between reconnection attempts
        self._reconnection_multiplier = 1.75  # Delay multiplier
        self._reconnection_jitter = (0, 3)  # Random jitter added to delay (min, max)

    @abstractmethod
    def send_message(self, msg: Message) -> None:
        """Should be overridden by backends with a super().send_message() call."""

    @abstractmethod
    def change_presence(self, status: str = ONLINE, message: str = '') -> None:
        """Signal a presence change for the bot. Should be overridden by backends with a super().send_message() call."""

    @abstractmethod
    def build_reply(self, msg: Message, text: str = None, private: bool = False, threaded: bool = False):
        """ Should be implemented by the backend """

    @abstractmethod
    def callback_presence(self, presence: Presence) -> None:
        """ Implemented by errBot. """
        pass

    @abstractmethod
    def callback_room_joined(self, room: Room) -> None:
        """ See :class:`~errbot.errBot.ErrBot` """
        pass

    @abstractmethod
    def callback_room_left(self, room: Room) -> None:
        """ See :class:`~errbot.errBot.ErrBot` """
        pass

    @abstractmethod
    def callback_room_topic(self, room: Room) -> None:
        """ See :class:`~errbot.errBot.ErrBot` """
        pass

    def serve_forever(self) -> None:
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
                log.info('Interrupt received, shutting down..')
                break
            except Exception:
                log.exception('Exception occurred in serve_once:')

            log.info('Reconnecting in %d seconds (%d attempted reconnections so far).', self._reconnection_delay,
                     self._reconnection_count)
            try:
                self._delay_reconnect()
                self._reconnection_count += 1
            except KeyboardInterrupt:
                log.info('Interrupt received, shutting down..')
                break

        log.info('Trigger shutdown')
        self.shutdown()

    def _delay_reconnect(self):
        """Delay next reconnection attempt until a suitable back-off time has passed"""
        time.sleep(self._reconnection_delay)

        self._reconnection_delay *= self._reconnection_multiplier
        if self._reconnection_delay > self._reconnection_max_delay:
            self._reconnection_delay = self._reconnection_max_delay
        self._reconnection_delay += random.uniform(*self._reconnection_jitter)  # nosec

    def reset_reconnection_count(self) -> None:
        """
        Reset the reconnection count. Back-ends should call this after
        successfully connecting.
        """
        self._reconnection_count = 0
        self._reconnection_delay = 1

    def build_message(self, text: str) -> Message:
        """ You might want to override this one depending on your backend """
        return Message(body=text)

    # ##### HERE ARE THE SPECIFICS TO IMPLEMENT PER BACKEND

    @abstractmethod
    def prefix_groupchat_reply(self, message: Message, identifier: Identifier):
        """ Patches message with the conventional prefix to ping the specific contact
        For example:
        @gbin, you forgot the milk !
        """

    @abstractmethod
    def build_identifier(self, text_representation: str) -> Identifier:
        pass

    def is_from_self(self, msg: Message) -> bool:
        """
        Needs to be overridden to check if the incoming message is from the bot itself.

        :param msg: The incoming message.
        :return: True if the message is coming from the bot.
        """
        # Default implementation (XMPP-like check using an extra config).
        # Most of the backends should have a better way to determine this.
        return (msg.is_direct and msg.frm == self.bot_identifier) or \
               (msg.is_group and msg.frm.nick == self.bot_config.CHATROOM_FN)

    def serve_once(self) -> None:
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

    def connect(self) -> Any:
        """Connects the bot to server or returns current connection """

    @abstractmethod
    def query_room(self, room: str) -> Room:
        """
        Query a room for information.

        :param room:
            The room to query for.
        :returns:
            An instance of :class:`~Room`.
        """

    @abstractmethod
    def connect_callback(self) -> None:
        pass

    @abstractmethod
    def disconnect_callback(self) -> None:
        pass

    @property
    @abstractmethod
    def mode(self) -> str:
        pass

    @property
    @abstractmethod
    def rooms(self) -> Sequence[Room]:
        """
        Return a list of rooms the bot is currently in.

        :returns:
            A list of :class:`~errbot.backends.base.Room` instances.
        """
