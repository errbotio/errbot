from __future__ import absolute_import
import logging
import sys
import warnings
import threading
import subprocess
import struct

from errbot.backends import DeprecationBridgeIdentifier
from errbot.backends.base import Message, MUCRoom, RoomError, RoomNotJoinedError, Stream
from errbot.errBot import ErrBot
from errbot.utils import RateLimited
from errbot.rendering.ansi import AnsiExtension, enable_format, CharacterTable, NSC

from markdown import Markdown
from markdown.extensions.extra import ExtraExtension

log = logging.getLogger(__name__)

IRC_CHRS = CharacterTable(fg_black=NSC('\x0301'),
                          fg_red=NSC('\x0304'),
                          fg_green=NSC('\x0303'),
                          fg_yellow=NSC('\x0308'),
                          fg_blue=NSC('\x0302'),
                          fg_magenta=NSC('\x0306'),
                          fg_cyan=NSC('\x0310'),
                          fg_white=NSC('\x0300'),
                          fg_default=NSC('\x03'),
                          bg_black=NSC('\x03,01'),
                          bg_red=NSC('\x03,04'),
                          bg_green=NSC('\x03,03'),
                          bg_yellow=NSC('\x03,08'),
                          bg_blue=NSC('\x03,02'),
                          bg_magenta=NSC('\x03,06'),
                          bg_cyan=NSC('\x03,10'),
                          bg_white=NSC('\x03,00'),
                          bg_default=NSC('\x03,'),
                          fx_reset=NSC('\x03'),
                          fx_bold=NSC('\x02'),
                          fx_italic=NSC('\x1D'),
                          fx_underline=NSC('\x1F'),
                          fx_not_italic=NSC('\x0F'),
                          fx_not_underline=NSC('\x0F'),
                          fx_normal=NSC('\x0F'),
                          fixed_width='',
                          end_fixed_width='')

enable_format('irc', IRC_CHRS)

try:
    import irc.connection
    from irc.client import ServerNotConnectedError
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


def irc_md():
    """This makes a converter from markdown to mirc color format.
    """
    md = Markdown(output_format='irc', extensions=[ExtraExtension(), AnsiExtension()])
    md.stripTopLevelTags = False
    return md


class IRCIdentifier(DeprecationBridgeIdentifier):
    # TODO(gbin): remove the deprecation warnings at one point.

    def __init__(self, nick, domain=None):
        self._nick = nick
        self._domain = domain

    @property
    def nick(self):
        return self._nick

    @property
    def domain(self):
        return self._domain

    # generic compatibility
    person = nick

    @property
    def fullname(self):
        # TODO: this should be possible to get
        return None

    def __unicode__(self):
        return "%s!%s" % (self._nick, self._domain)

    def __str__(self):
        return self.__unicode__()


class IRCMUCOccupant(IRCIdentifier):
    def __init__(self, nick, room):
        super().__init__(nick)
        self._room = room

    @property
    def room(self):
        return self._room

    def __unicode__(self):
        return "%s!%s %s" % (self._nick, self._domain, self._room)

    def __str__(self):
        return self.__unicode__()


class IRCMUCRoom(MUCRoom):
    def __init__(self, room, bot):
        self._bot = bot
        self.room = room
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

        self.connection.join(self.room, key=password)
        self._bot.callback_room_joined(self)
        log.info("Joined room {}".format(self.room))

    def leave(self, reason=None):
        """
        Leave the room.

        :param reason:
            An optional string explaining the reason for leaving the room
        """
        if reason is None:
            reason = ""

        self.connection.part(self.room, reason)
        log.info("Left room {}".format(self.room))
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
        return self.room in self._bot.conn.channels.keys()

    @property
    def topic(self):
        """
        The room topic.

        :getter:
            Returns the topic (a string) if one is set, `None` if no
            topic has been set at all.
        """
        return self.connection.topic(self.room)

    @topic.setter
    def topic(self, topic):
        """
        Set the room's topic.

        :param topic:
            The topic to set.
        """
        self.connection.topic(self.room, topic)

    @property
    def occupants(self):
        """
        The room's occupants.

        :getter:
            Returns a list of occupants.
            :raises:
            :class:`~MUCNotJoinedError` if the room has not yet been joined.
        """
        occupants = []
        try:
            for nick in self._bot.conn.channels[self.room].users():
                occupants.append(IRCMUCOccupant(nick=nick))
        except KeyError:
            raise RoomNotJoinedError("Must be in a room in order to see occupants.")
        return occupants

    def invite(self, *args):
        """
        Invite one or more people into the room.

        :*args:
            One or more nicks to invite into the room.
        """
        for nick in args:
            self.connection.invite(nick, self.room)
            log.info("Invited {} to {}".format(nick, self.room))


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
                 channel_rate=1,
                 reconnect_on_kick=5,
                 reconnect_on_disconnect=5):
        self.use_ssl = ssl
        self.callback = callback
        # manually decorate functions
        if private_rate:
            self.send_private_message = RateLimited(private_rate)(self.send_private_message)

        if channel_rate:
            self.send_public_message = RateLimited(channel_rate)(self.send_public_message)
        self._reconnect_on_kick = reconnect_on_kick
        self._pending_transfers = {}

        if username is None:
            username = nickname
        self.transfers = {}
        super().__init__([(server, port, password)], nickname, username, reconnection_interval=reconnect_on_disconnect)

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
        nick = e.source.split('!')[0]
        room = e.target
        if room[0] != '#' and room[0] != '$':
            raise Exception('[%s] is not a room' % room)
        msg.frm = IRCMUCOccupant(nick, room)
        msg.to = self.callback.bot_identifier
        msg.nick = nick  # FIXME find the real nick in the channel
        self.callback.callback_message(msg)

    def on_privmsg(self, _, e):
        msg = Message(e.arguments[0])
        msg.frm = IRCIdentifier(e.source.split('!')[0])
        msg.to = IRCIdentifier(e.target)
        self.callback.callback_message(msg)

    def on_kick(self, _, e):
        if not self._reconnect_on_kick:
            log.info("RECONNECT_ON_KICK is 0 or None, won't try to reconnect")
            return
        log.info("Got kicked out of %s... reconnect in %d seconds... " % (e.target, self._reconnect_on_kick))

        def reconnect_channel(name):
            log.info("Reconnecting to %s after having beeing kicked" % name)
            self.callback.query_room(name).join()
        t = threading.Timer(self._reconnect_on_kick, reconnect_channel, [e.target, ])
        t.daemon = True
        t.start()

    def send_private_message(self, to, line):
        try:
            self.connection.privmsg(to, line)
        except ServerNotConnectedError:
            pass  # the message will be lost

    def send_public_message(self, to, line):
        try:
            self.connection.privmsg(to, line)
        except ServerNotConnectedError:
            pass  # the message will be lost

    def on_disconnect(self, _, e):
        self.callback.disconnect_callback()

    def send_stream_request(self, identifier, fsource, name=None, size=None, stream_type=None):
        # Creates a new connection
        dcc = self.dcc_listen("raw")
        msg_parts = map(str, (
            'SEND',
            name,
            irc.client.ip_quad_to_numstr(dcc.localaddress),
            dcc.localport,
            size,
        ))
        msg = subprocess.list2cmdline(msg_parts)
        self.connection.ctcp("DCC", identifier.nick, msg)
        stream = Stream(identifier, fsource, name, size, stream_type)
        self.transfers[dcc] = stream

        return stream

    def on_dcc_connect(self, dcc, event):
        stream = self.transfers.get(dcc, None)
        if stream is None:
            log.error("DCC connect on a none registered connection")
            return
        log.debug("Start transfer for %s" % stream.identifier)
        stream.accept()
        self.send_chunk(stream, dcc)

    def on_dcc_disconnect(self, dcc, event):
        self.transfers.pop(dcc)

    def send_chunk(self, stream, dcc):
        data = stream.read(4096)
        dcc.send_bytes(data)
        stream.ack_data(len(data))

    def on_dccmsg(self, dcc, event):
        stream = self.transfers.get(dcc, None)
        if stream is None:
            log.error("DCC connect on a none registered connection")
            return
        acked = struct.unpack("!I", event.arguments[0])[0]
        if acked == stream.size:
            log.info("File %s successfully transfered to %s" % (stream.name, stream.identifier))
            dcc.disconnect()
            self.transfers.pop(dcc)
        elif acked == stream.transfered:
            log.debug("Chunk for file %s successfully transfered to %s (%d/%d)  " %
                      (stream.name, stream.identifier, stream.transfered, stream.size))
            self.send_chunk(stream, dcc)
        else:
            log.debug("Partial chunk for file %s successfully transfered to %s (%d/%d), wait for more" %
                      (stream.name, stream.identifier, stream.transfered, stream.size))


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
        reconnect_on_kick = config.__dict__.get('IRC_RECONNECT_ON_KICK', 5)
        reconnect_on_disconnect = config.__dict__.get('IRC_RECONNECT_ON_DISCONNECT', 5)

        self.bot_identifier = IRCIdentifier(nickname, server)
        super().__init__(config)
        self.conn = IRCConnection(self,
                                  nickname,
                                  server,
                                  port,
                                  ssl,
                                  password,
                                  username,
                                  private_rate,
                                  channel_rate,
                                  reconnect_on_kick,
                                  reconnect_on_disconnect)
        self.md = irc_md()

    def send_message(self, mess):
        super(IRCBackend, self).send_message(mess)
        if mess.type == 'chat':
            msg_func = self.conn.send_private_message
            msg_to = mess.to.person
        else:
            msg_func = self.conn.send_public_message
            msg_to = mess.to.room

        body = self.md.convert(mess.body)
        for line in body.split('\n'):
            msg_func(msg_to, line)

    def send_stream_request(self, identifier, fsource, name=None, size=None, stream_type=None):
        return self.conn.send_stream_request(identifier, fsource, name, size, stream_type)

    def build_reply(self, mess, text=None, private=False):
        log.debug("Build reply.")
        log.debug("Orig From %s" % mess.frm)
        log.debug("Orig To %s" % mess.to)
        log.debug("Orig Type %s" % mess.type)

        msg_type = mess.type
        response = self.build_message(text)

        response.frm = self.bot_identifier
        response.to = mess.frm
        response.type = 'chat' if private else msg_type

        log.debug("Response From %s" % response.frm)
        log.debug("Response To %s" % response.to)
        log.debug("Response Type %s" % response.type)

        return response

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
        text = text.replace('', '*')  # there is a weird chr IRC is sending that we need to filter out
        return super().build_message(text)

    def build_identifier(self, txtrep):
        log.debug("Build identifier from [%s]" % txtrep)
        if txtrep.startswith('#'):
            return IRCMUCOccupant(None, txtrep)

        if '!' in txtrep:
            nick, domain = txtrep.split('!')
            return IRCIdentifier(nick, domain)

        return IRCIdentifier(txtrep)

    def shutdown(self):
        super().shutdown()

    def query_room(self, room):
        """
        Query a room for information.

        :param room:
            The channel name to query for.
        :returns:
            An instance of :class:`~IRCMUCRoom`.
        """
        return IRCMUCRoom(room, bot=self)

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
        return [IRCMUCRoom(channel, self) for channel in channels]

    def groupchat_reply_format(self):
        return '{0}: {1}'
