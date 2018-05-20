from __future__ import absolute_import
import logging
import sys
import threading
import subprocess
import struct
import re

from markdown import Markdown
from markdown.extensions.extra import ExtraExtension

from errbot.backends.base import Message, Room, RoomError, \
    RoomNotJoinedError, Stream, \
    RoomOccupant, ONLINE, Person
from errbot.core import ErrBot
from errbot.utils import rate_limited
from errbot.rendering.ansiext import AnsiExtension, enable_format, \
    CharacterTable, NSC

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
                          end_fixed_width='',
                          inline_code='',
                          end_inline_code='')

IRC_NICK_REGEX = r'[a-zA-Z\[\]\\`_\^\{\|\}][a-zA-Z0-9\[\]\\`_\^\{\|\}-]+'
IRC_MESSAGE_SIZE_LIMIT = 510

try:
    import irc.connection
    from irc.client import ServerNotConnectedError, NickMask
    from irc.bot import SingleServerIRCBot
except ImportError:
    log.fatal("""You need the IRC support to use IRC, you can install it with:
    pip install errbot[IRC]
    """)
    sys.exit(-1)


def irc_md():
    """This makes a converter from markdown to mirc color format.
    """
    md = Markdown(output_format='irc', extensions=[ExtraExtension(), AnsiExtension()])
    md.stripTopLevelTags = False
    return md


class IRCPerson(Person):

    def __init__(self, mask):
        self._nickmask = NickMask(mask)

    @property
    def nick(self):
        return self._nickmask.nick

    @property
    def user(self):
        return self._nickmask.user

    @property
    def host(self):
        return self._nickmask.host

    # generic compatibility
    person = nick

    @property
    def client(self):
        return self._nickmask.userhost

    @property
    def fullname(self):
        # TODO: this should be possible to get
        return None

    @property
    def aclattr(self):
        return IRCBackend.aclpattern.format(nick=self._nickmask.nick,
                                            user=self._nickmask.user,
                                            host=self._nickmask.host)

    def __unicode__(self):
        return str(self._nickmask)

    def __str__(self):
        return self.__unicode__()

    def __eq__(self, other):
        if not isinstance(other, IRCPerson):
            log.warning("Weird you are comparing an IRCPerson to a %s.", type(other))
            return False
        return self.person == other.person


class IRCRoomOccupant(IRCPerson, RoomOccupant):

    def __init__(self, mask, room):
        super().__init__(mask)
        self._room = room

    @property
    def room(self):
        return self._room

    def __unicode__(self):
        return self._nickmask

    def __str__(self):
        return self.__unicode__()

    def __repr__(self):
        return f'<{self.__unicode__()} - {super().__repr__()}>'


class IRCRoom(Room):
    """
        Represent the specifics of a IRC Room/Channel.

        This lifecycle of this object is:
         - Created in IRCConnection.on_join
         - The joined status change in IRCConnection on_join/on_part
         - Deleted/destroyed in IRCConnection.on_disconnect
    """

    def __init__(self, room, bot):
        self._bot = bot
        self.room = room
        self.connection = self._bot.conn.connection
        self._topic_lock = threading.Lock()
        self._topic = None

    def __unicode__(self):
        return self.room

    def __str__(self):
        return self.__unicode__()

    def __repr__(self):
        return f"<{self.__unicode__()} - {super().__repr__()}>"

    def cb_set_topic(self, current_topic):
        """
        Store the current topic for this room.

        This method is called by the IRC backend when a `currenttopic`,
        `topic` or `notopic` IRC event is received to store the topic set for this channel.

        This function is not meant to be executed by regular plugins.
        To get or set
        """
        with self._topic_lock:
            self._topic = current_topic

    def join(self, username=None, password=None):
        """
        Join the room.

        If the room does not exist yet, this will automatically call
        :meth:`create` on it first.
        """
        if username is not None:
            log.debug("Ignored username parameter on join(), it is unsupported on this back-end.")
        if password is None:
            password = ""  # nosec

        self.connection.join(self.room, key=password)
        log.info('Joined room %s.', self.room)

    def leave(self, reason=None):
        """
        Leave the room.

        :param reason:
            An optional string explaining the reason for leaving the room
        """
        if reason is None:
            reason = ""

        self.connection.part(self.room, reason)
        log.info('Leaving room %s with reason %s.', self.room, reason if reason is not None else '')

    def create(self):
        """
        Not supported on this back-end. Will join the room to ensure it exists, instead.
        """
        logging.warning('IRC back-end does not support explicit creation, joining room instead to ensure it exists.')
        self.join()

    def destroy(self):
        """
        Not supported on IRC, will raise :class:`~errbot.backends.base.RoomError`.
        """
        raise RoomError('IRC back-end does not support destroying rooms.')

    @property
    def exists(self):
        """
        Boolean indicating whether this room already exists or not.

        :getter:
            Returns `True` if the room exists, `False` otherwise.
        """
        logging.warning('IRC back-end does not support determining if a room exists. '
                        'Returning the result of joined instead.')
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
        if not self.joined:
            raise RoomNotJoinedError('Must join the room to get the topic.')
        with self._topic_lock:
            return self._topic

    @topic.setter
    def topic(self, topic):
        """
        Set the room's topic.

        :param topic:
            The topic to set.
        """
        if not self.joined:
            raise RoomNotJoinedError('Must join the room to set the topic.')
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
                occupants.append(IRCRoomOccupant(nick, room=self.room))
        except KeyError:
            raise RoomNotJoinedError('Must be in a room in order to see occupants.')
        return occupants

    def invite(self, *args):
        """
        Invite one or more people into the room.

        :*args:
            One or more nicks to invite into the room.
        """
        for nick in args:
            self.connection.invite(nick, self.room)
            log.info('Invited %s to %s.', nick, self.room)

    def __eq__(self, other):
        if not isinstance(other, IRCRoom):
            log.warning('This is weird you are comparing an IRCRoom to a %s.', type(other))
            return False
        return self.room == other.room


class IRCConnection(SingleServerIRCBot):

    def __init__(self,
                 bot,
                 nickname,
                 server,
                 port=6667,
                 ssl=False,
                 bind_address=None,
                 ipv6=False,
                 password=None,
                 username=None,
                 nickserv_password=None,
                 private_rate=1,
                 channel_rate=1,
                 reconnect_on_kick=5,
                 reconnect_on_disconnect=5):
        self.use_ssl = ssl
        self.use_ipv6 = ipv6
        self.bind_address = bind_address
        self.bot = bot
        # manually decorate functions
        if private_rate:
            self.send_private_message = rate_limited(private_rate)(self.send_private_message)

        if channel_rate:
            self.send_public_message = rate_limited(channel_rate)(self.send_public_message)
        self._reconnect_on_kick = reconnect_on_kick
        self._pending_transfers = {}
        self._rooms_lock = threading.Lock()
        self._rooms = {}
        self._recently_joined_to = set()

        self.nickserv_password = nickserv_password
        if username is None:
            username = nickname
        self.transfers = {}
        super().__init__([(server, port, password)], nickname, username, reconnection_interval=reconnect_on_disconnect)

    def connect(self, *args, **kwargs):
        # Decode all input to UTF-8, but use a replacement character for
        # unrecognized byte sequences
        # (as described at https://pypi.python.org/pypi/irc)
        self.connection.buffer_class.errors = 'replace'

        connection_factory_kwargs = {}
        if self.use_ssl:
            import ssl
            connection_factory_kwargs['wrapper'] = ssl.wrap_socket
        if self.bind_address is not None:
            connection_factory_kwargs['bind_address'] = self.bind_address
        if self.use_ipv6:
            connection_factory_kwargs['ipv6'] = True

        connection_factory = irc.connection.Factory(**connection_factory_kwargs)
        self.connection.connect(*args, connect_factory=connection_factory, **kwargs)

    def on_welcome(self, _, e):
        log.info("IRC welcome %s", e)

        # try to identify with NickServ if there is a NickServ password in the
        # config
        if self.nickserv_password:
            msg = f'identify {self.nickserv_password}'
            self.send_private_message('NickServ', msg)

        # Must be done in a background thread, otherwise the join room
        # from the ChatRoom plugin joining channels from CHATROOM_PRESENCE
        # ends up blocking on connect.
        t = threading.Thread(target=self.bot.connect_callback)
        t.setDaemon(True)
        t.start()

    def _pubmsg(self, e, notice=False):
        msg = Message(e.arguments[0], extras={'notice': notice})
        room_name = e.target
        if room_name[0] != '#' and room_name[0] != '$':
            raise Exception(f'[{room_name}] is not a room')
        room = IRCRoom(room_name, self.bot)
        msg.frm = IRCRoomOccupant(e.source, room)
        msg.to = room
        msg.nick = msg.frm.nick  # FIXME find the real nick in the channel
        self.bot.callback_message(msg)

        possible_mentions = re.findall(IRC_NICK_REGEX, e.arguments[0])
        room_users = self.channels[room_name].users()
        mentions = filter(lambda x: x in room_users, possible_mentions)
        if mentions:
            mentions = [self.bot.build_identifier(mention) for mention in mentions]
            self.bot.callback_mention(msg, mentions)

    def _privmsg(self, e, notice=False):
        msg = Message(e.arguments[0], extras={'notice': notice})
        msg.frm = IRCPerson(e.source)
        msg.to = IRCPerson(e.target)
        self.bot.callback_message(msg)

    def on_pubmsg(self, _, e):
        self._pubmsg(e)

    def on_privmsg(self, _, e):
        self._privmsg(e)

    def on_pubnotice(self, _, e):
        self._pubmsg(e, True)

    def on_privnotice(self, _, e):
        self._privmsg(e, True)

    def on_kick(self, _, e):
        if not self._reconnect_on_kick:
            log.info("RECONNECT_ON_KICK is 0 or None, won't try to reconnect")
            return
        log.info('Got kicked out of %s... reconnect in %d seconds... ', e.target, self._reconnect_on_kick)

        def reconnect_channel(name):
            log.info('Reconnecting to %s after having beeing kicked.', name)
            self.bot.query_room(name).join()
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

    def on_disconnect(self, connection, event):
        self._rooms = {}
        self.bot.disconnect_callback()

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
            log.error('DCC connect on a none registered connection')
            return
        log.debug('Start transfer for %s.', stream.identifier)
        stream.accept()
        self.send_chunk(stream, dcc)

    def on_dcc_disconnect(self, dcc, event):
        self.transfers.pop(dcc)

    def on_part(self, connection, event):
        """
            Handler of the part IRC Message/event.

            The part message is sent to the client as a confirmation of a
            /PART command sent by someone in the room/channel.
            If the event.source contains the bot nickname then we need to fire
            the :meth:`~errbot.backends.base.Backend.callback_room_left` event on the bot.

            :param connection: Is an 'irc.client.ServerConnection' object

            :param event: Is an 'irc.client.Event' object
                The event.source contains the nickmask of the user that
                leave the room
                The event.target contains the channel name
        """
        leaving_nick = event.source.nick
        leaving_room = event.target
        if self.bot.bot_identifier.nick == leaving_nick:
            with self._rooms_lock:
                self.bot.callback_room_left(self._rooms[leaving_room])
            log.info('Left room {}.', leaving_room)

    def on_endofnames(self, connection, event):
        """
            Handler of the enfofnames IRC message/event.

            The endofnames message is sent to the client when the server finish
            to send the list of names of the room ocuppants.
            This usually happens when you join to the room.
            So in this case, we use this event to determine that our bot is
            finally joined to the room.

            :param connection: Is an 'irc.client.ServerConnection' object

            :param event: Is an 'irc.client.Event' object
                the event.arguments[0] contains the channel name
        """
        # The event.arguments[0] contains the channel name.
        # We filter that to avoid a misfire of the event.
        room_name = event.arguments[0]
        with self._rooms_lock:
            if room_name in self._recently_joined_to:
                self._recently_joined_to.remove(room_name)
                self.bot.callback_room_joined(self._rooms[room_name])

    def on_join(self, connection, event):
        """
            Handler of the join IRC message/event.
            Is in response of a /JOIN client message.

            :param connection: Is an 'irc.client.ServerConnection' object

            :param event: Is an 'irc.client.Event' object
                the event.target contains the channel name
        """
        # We can't fire the room_joined event yet,
        # because we don't have the occupants info.
        # We need to wait to endofnames message.
        room_name = event.target
        with self._rooms_lock:
            if room_name not in self._rooms:
                self._rooms[room_name] = IRCRoom(room_name, self.bot)
            self._recently_joined_to.add(room_name)

    def on_currenttopic(self, connection, event):
        """
            When you Join a room with a topic set this event fires up to
            with the topic information.
            If the room that you join don't have a topic set, nothing happens.
            Here is NOT the place to fire the :meth:`~errbot.backends.base.Backend.callback_room_topic` event for
            that case exist on_topic.

            :param connection: Is an 'irc.client.ServerConnection' object

            :param event: Is an 'irc.client.Event' object
                The event.arguments[0] contains the room name
                The event.arguments[1] contains the topic of the room.
        """
        room_name, current_topic = event.arguments
        with self._rooms_lock:
            self._rooms[room_name].cb_set_topic(current_topic)

    def on_topic(self, connection, event):
        """
            On response to the /TOPIC command if the room have a topic.
            If the room don't have a topic the event fired is on_notopic
            :param connection: Is an 'irc.client.ServerConnection' object

            :param event: Is an 'irc.client.Event' object
                The event.target contains the room name.
                The event.arguments[0] contains the topic name
        """
        room_name = event.target
        current_topic = event.arguments[0]
        with self._rooms_lock:
            self._rooms[room_name].cb_set_topic(current_topic)
            self.bot.callback_room_topic(self._rooms[room_name])

    def on_notopic(self, connection, event):
        """
            This event fires ip when there is no topic set on a room

            :param connection: Is an 'irc.client.ServerConnection' object

            :param event: Is an 'irc.client.Event' object
                The event.arguments[0] contains the room name
        """
        room_name = event.arguments[0]
        with self._rooms_lock:
            self._rooms[room_name].cb_set_topic(None)
            self.bot.callback_room_topic(self._rooms[room_name])

    @staticmethod
    def send_chunk(stream, dcc):
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
            log.info('File %s successfully transfered to %s', stream.name, stream.identifier)
            dcc.disconnect()
            self.transfers.pop(dcc)
        elif acked == stream.transfered:
            log.debug('Chunk for file %s successfully transfered to %s (%d/%d).',
                      stream.name, stream.identifier, stream.transfered, stream.size)
            self.send_chunk(stream, dcc)
        else:
            log.debug('Partial chunk for file %s successfully transfered to %s (%d/%d), wait for more',
                      stream.name, stream.identifier, stream.transfered, stream.size)

    def away(self, message=''):
        """
        Extend the original implementation to support AWAY.
        To set an away message, set message to something.
        To cancel an away message, leave message at empty string.
        """
        self.connection.send_raw(' '.join(['AWAY', message]).strip())


class IRCBackend(ErrBot):
    aclpattern = '{nick}!{user}@{host}'

    def __init__(self, config):
        if hasattr(config, 'IRC_ACL_PATTERN'):
            IRCBackend.aclpattern = config.IRC_ACL_PATTERN

        identity = config.BOT_IDENTITY
        nickname = identity['nickname']
        server = identity['server']
        port = identity.get('port', 6667)
        password = identity.get('password', None)
        ssl = identity.get('ssl', False)
        bind_address = identity.get('bind_address', None)
        ipv6 = identity.get('ipv6', False)
        username = identity.get('username', None)
        nickserv_password = identity.get('nickserv_password', None)

        compact = config.COMPACT_OUTPUT if hasattr(config, 'COMPACT_OUTPUT') else True
        enable_format('irc', IRC_CHRS, borders=not compact)

        private_rate = getattr(config, 'IRC_PRIVATE_RATE', 1)
        channel_rate = getattr(config, 'IRC_CHANNEL_RATE', 1)
        reconnect_on_kick = getattr(config, 'IRC_RECONNECT_ON_KICK', 5)
        reconnect_on_disconnect = getattr(config, 'IRC_RECONNECT_ON_DISCONNECT', 5)

        self.bot_identifier = IRCPerson(nickname + '!' + nickname + '@' + server)
        super().__init__(config)
        self.conn = IRCConnection(bot=self,
                                  nickname=nickname,
                                  server=server,
                                  port=port,
                                  ssl=ssl,
                                  bind_address=bind_address,
                                  ipv6=ipv6,
                                  password=password,
                                  username=username,
                                  nickserv_password=nickserv_password,
                                  private_rate=private_rate,
                                  channel_rate=channel_rate,
                                  reconnect_on_kick=reconnect_on_kick,
                                  reconnect_on_disconnect=reconnect_on_disconnect,
                                  )
        self.md = irc_md()
        config.MESSAGE_SIZE_LIMIT = IRC_MESSAGE_SIZE_LIMIT

    def send_message(self, msg):
        super().send_message(msg)
        if msg.is_direct:
            msg_func = self.conn.send_private_message
            msg_to = msg.to.person
        else:
            msg_func = self.conn.send_public_message
            msg_to = msg.to.room

        body = self.md.convert(msg.body)
        for line in body.split('\n'):
            msg_func(msg_to, line)

    def change_presence(self, status: str = ONLINE, message: str = '') -> None:
        if status == ONLINE:
            self.conn.away()  # cancels the away message
        else:
            self.conn.away(f'[{status}] {message}')

    def send_stream_request(self, identifier, fsource, name=None, size=None, stream_type=None):
        return self.conn.send_stream_request(identifier, fsource, name, size, stream_type)

    def build_reply(self, msg, text=None, private=False, threaded=False):
        response = self.build_message(text)
        if msg.is_group:
            if private:
                response.frm = self.bot_identifier
                response.to = IRCPerson(str(msg.frm))
            else:
                response.frm = IRCRoomOccupant(str(self.bot_identifier), msg.frm.room)
                response.to = msg.frm.room
        else:
            response.frm = self.bot_identifier
            response.to = msg.frm
        return response

    def serve_forever(self):
        try:
            self.conn.start()
        except KeyboardInterrupt:
            log.info("Interrupt received, shutting down")
        finally:
            self.conn.disconnect("Shutting down")
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
        log.debug('Build identifier from %s.', txtrep)
        # A textual representation starting with # means that we are talking
        # about an IRC channel -- IRCRoom in internal err-speak.
        if txtrep.startswith('#'):
            return IRCRoom(txtrep, self)

        # Occupants are represented as 2 lines, one is the IRC mask and the second is the Room.
        if '\n' in txtrep:
            m, r = txtrep.split('\n')
            return IRCRoomOccupant(m, IRCRoom(r, self))
        return IRCPerson(txtrep)

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
        with self.conn._rooms_lock:
            if room not in self.conn._rooms:
                self.conn._rooms[room] = IRCRoom(room, self)
            return self.conn._rooms[room]

    @property
    def mode(self):
        return 'irc'

    def rooms(self):
        """
        Return a list of rooms the bot is currently in.

        :returns:
            A list of :class:`~IRCMUCRoom` instances.
        """
        with self.conn._rooms_lock:
            return self.conn._rooms.values()

    def prefix_groupchat_reply(self, message, identifier):
        super().prefix_groupchat_reply(message, identifier)
        message.body = f'{identifier.nick}: {message.body}'
