from __future__ import absolute_import
import logging
import sys
import warnings

from errbot.backends.base import (
    Message, MUCOccupant, MUCRoom, RoomError, RoomNotJoinedError,
    build_message, build_text_html_message_pair,
)
from errbot.errBot import ErrBot
from errbot.utils import RateLimited

log = logging.getLogger(__name__)

try:
    import irc.connection
    from irc.bot import SingleServerIRCBot
except ImportError as _:
    log.exception("Could not start the IRC backend")
    log.fatal("""
    If you intend to use the IRC backend please install the python irc package:
    -> On debian-like systems
    sudo apt-get install python-software-properties
    sudo apt-get update
    sudo apt-get install python-irc
    -> On Gentoo
    sudo emerge -av dev-python/irc
    -> Generic
    pip install irc
    """)
    sys.exit(-1)


class IRCIdentifier(object):
    def __init__(self, nick, domain):
        self._nick = nick
        self._domain = domain

    @property
    def nick(self):
        return self._nick

    @property
    def domain(self):
        return self._domain

    def __unicode__(self):
        return "{}!{}" % (self._nick, self._domain)


class IRCMUCRoom(MUCRoom):
    def __init__(self, *args, **kwargs):
        super(IRCMUCRoom, self).__init__(*args, **kwargs)
        self.connection = self._bot.conn.connection

    def join(self, username=None, password=None):
        """
        Join the room.

        If the room does not exist yet, this will automatically call
        :meth:`create` on it first.
        """
        if username is not None:
            log.debug("Ignored username parameter on join(), it is unsupported on this back-end.")
        if password is None:
            password = ""
        room = str(self)

        self.connection.join(room, key=password)
        self._bot.callback_room_joined(self)
        log.info("Joined room {}".format(room))

    def leave(self, reason=None):
        """
        Leave the room.

        :param reason:
            An optional string explaining the reason for leaving the room
        """
        if reason is None:
            reason = ""
        room = str(self)

        self.connection.part(room, reason)
        log.info("Left room {}".format(room))
        self._bot.callback_room_left(self)

    def create(self):
        """
        Not supported on this back-end. Will join the room to ensure it exists, instead.
        """
        logging.warning(
            "IRC back-end does not support explicit creation, joining room "
            "instead to ensure it exists."
        )
        self.join()

    def destroy(self):
        """
        Not supported on IRC, will raise :class:`~errbot.backends.base.RoomError`.
        """
        raise RoomError("IRC back-end does not support destroying rooms.")

    @property
    def exists(self):
        """
        Boolean indicating whether this room already exists or not.

        :getter:
            Returns `True` if the room exists, `False` otherwise.
        """
        logging.warning(
            "IRC back-end does not support determining if a room exists. "
            "Returning the result of joined instead."
        )
        return self.joined

    @property
    def joined(self):
        """
        Boolean indicating whether this room has already been joined.

        :getter:
            Returns `True` if the room has been joined, `False` otherwise.
        """
        return str(self) in self._bot.conn.channels.keys()

    @property
    def topic(self):
        """
        The room topic.

        :getter:
            Returns the topic (a string) if one is set, `None` if no
            topic has been set at all.
        """
        return self.connection.topic(str(self))

    @topic.setter
    def topic(self, topic):
        """
        Set the room's topic.

        :param topic:
            The topic to set.
        """
        self.connection.topic(str(self), topic)

    @property
    def occupants(self):
        """
        The room's occupants.

        :getter:
            Returns a list of :class:`~errbot.backends.base.MUCOccupant` instances.
        :raises:
            :class:`~MUCNotJoinedError` if the room has not yet been joined.
        """
        occupants = []
        try:
            for nick in self._bot.conn.channels[str(self)].users():
                occupants.append(MUCOccupant(node=nick))
        except KeyError:
            raise RoomNotJoinedError("Must be in a room in order to see occupants.")
        return occupants

    def invite(self, *args):
        """
        Invite one or more people into the room.

        :*args:
            One or more nicks to invite into the room.
        """
        room = str(self)
        for nick in args:
            self.connection.invite(nick, room)
            log.info("Invited {} to {}".format(nick, room))


class IRCConnection(SingleServerIRCBot):
    def __init__(self,
                 callback,
                 nickname,
                 server,
                 port=6667,
                 ssl=False,
                 password=None,
                 username=None,
                 private_rate=1,
                 channel_rate=1):
        self.use_ssl = ssl
        self.callback = callback
        # manually decorate functions
        self.send_private_message = RateLimited(private_rate)(self.send_private_message)
        self.send_public_message = RateLimited(channel_rate)(self.send_private_message)

        if username is None:
            username = nickname
        super().__init__([(server, port, password)], nickname, username)

    def connect(self, *args, **kwargs):
        if self.use_ssl:
            import ssl
            ssl_factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
            self.connection.connect(*args, connect_factory=ssl_factory, **kwargs)
        else:
            self.connection.connect(*args, **kwargs)

    def on_welcome(self, _, e):
        log.info("IRC welcome %s" % e)
        self.callback.connect_callback()

    def on_pubmsg(self, _, e):
        msg = Message(e.arguments[0], type_='groupchat')
        msg.frm = self.callback.build_identifier(e.target)
        msg.to = self.callback.jid
        msg.nick = e.source.split('!')[0]  # FIXME find the real nick in the channel
        self.callback.callback_message(msg)

    def on_privmsg(self, _, e):
        msg = Message(e.arguments[0])
        msg.frm = e.source.split('!')[0]
        msg.to = e.target
        self.callback.callback_message(msg)

    def send_private_message(self, to, line):
        self.connection.privmsg(to, line)

    def send_public_message(self, to, line):
        self.connection.privmsg(to, line)


class IRCBackend(ErrBot):
    def __init__(self, config):

        identity = config.BOT_IDENTITY
        nickname = identity['nickname']
        server = identity['server']
        port = identity.get('port', 6667)
        password = identity.get('password', None)
        ssl = identity.get('ssl', False)
        username = identity.get('username', None)

        private_rate = config.__dict__.get('IRC_PRIVATE_RATE', 1)
        channel_rate = config.__dict__.get('IRC_CHANNEL_RATE', 1)

        self.jid = Identifier(node=nickname, domain=server)
        super(IRCBackend, self).__init__(config)
        self.conn = IRCConnection(self, nickname, server, port, ssl, password, username, private_rate, channel_rate)

    def send_message(self, mess):
        super(IRCBackend, self).send_message(mess)
        msg_func = self.conn.send_private_message if mess.type == 'chat' else self.conn.send_public_message
        # If this is a response in private of a public message take the recipient in
        # the resource instead of the incoming chatroom
        if mess.type == 'chat' and mess.to.resource:
            to = mess.to.resource
        else:
            to = mess.to.node
        for line in build_text_html_message_pair(mess.body)[0].split('\n'):
            msg_func(to, line)

    def serve_forever(self):
        try:
            self.conn.start()
        finally:
            log.debug("Trigger disconnect callback")
            self.disconnect_callback()
            log.debug("Trigger shutdown")
            self.shutdown()

    def connect(self):
        return self.conn

    def build_message(self, text):
        return build_message(text, Message)

    def build_identifier(self, txtrep):
        nick, domain = txtrep.split('!')
        return IRCIdentifier(nick, domain)

    def shutdown(self):
        super().shutdown()

    def join_room(self, room, username=None, password=None):
        """
        .. deprecated:: 2.2.0
            Use the methods on :class:`IRCMUCRoom` instead.
        """
        warnings.warn(
            "Using join_room is deprecated, use join from the "
            "MUCRoom class instead.",
            DeprecationWarning
        )
        self.query_room(room).join(username=username, password=password)

    def query_room(self, room):
        """
        Query a room for information.

        :param room:
            The channel name to query for.
        :returns:
            An instance of :class:`~IRCMUCRoom`.
        """
        return IRCMUCRoom(node=room, bot=self)

    @property
    def mode(self):
        return 'irc'

    def rooms(self):
        """
        Return a list of rooms the bot is currently in.

        :returns:
            A list of :class:`~IRCMUCRoom` instances.
        """

        channels = self.conn.channels.keys()
        return [IRCMUCRoom(node=channel) for channel in channels]

    def groupchat_reply_format(self):
        return '{0}: {1}'
