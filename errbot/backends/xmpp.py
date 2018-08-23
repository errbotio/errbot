import logging
import sys
from functools import lru_cache

from threading import Thread
from time import sleep

from errbot.backends.base import Message, Room, Presence, RoomNotJoinedError, Identifier, RoomOccupant, Person
from errbot.backends.base import ONLINE, OFFLINE, AWAY, DND
from errbot.core import ErrBot
from errbot.rendering import text, xhtml, xhtmlim

log = logging.getLogger(__name__)

try:
    from sleekxmpp import ClientXMPP
    from sleekxmpp.xmlstream import resolver, cert
    from sleekxmpp import JID
    from sleekxmpp.exceptions import IqError

except ImportError:
    log.exception("Could not start the XMPP backend")
    log.fatal("""
    If you intend to use the XMPP backend please install the support for XMPP with:
    pip install errbot[XMPP]
    """)
    sys.exit(-1)

# LRU to cache the JID queries.
IDENTIFIERS_LRU = 1024


class XMPPIdentifier(Identifier):
    """
    This class is the parent and the basic contract of all the ways the backends
    are identifying a person on their system.
    """

    def __init__(self, node, domain, resource):
        if not node:
            raise Exception('An XMPPIdentifier needs to have a node.')
        if not domain:
            raise Exception('An XMPPIdentifier needs to have a domain.')
        self._node = node
        self._domain = domain
        self._resource = resource

    @property
    def node(self):
        return self._node

    @property
    def domain(self):
        return self._domain

    @property
    def resource(self):
        return self._resource

    @property
    def person(self):
        return self._node + '@' + self._domain

    @property
    def nick(self):
        return self._node

    @property
    def fullname(self):
        return None  # Not supported by default on XMPP.

    @property
    def client(self):
        return self._resource

    def __str__(self):
        answer = self._node + '@' + self._domain  # don't call .person: see below
        if self._resource:
            answer += '/' + self._resource
        return answer

    def __unicode__(self):
        return str(self.__str__())

    def __eq__(self, other):
        if not isinstance(other, XMPPIdentifier):
            log.debug("Weird, you are comparing an XMPPIdentifier to a %s", type(other))
            return False
        return self._domain == other._domain and self._node == other._node and self._resource == other._resource


class XMPPPerson(XMPPIdentifier, Person):
    aclattr = XMPPIdentifier.person

    def __eq__(self, other):
        if not isinstance(other, XMPPPerson):
            log.debug("Weird, you are comparing an XMPPPerson to a %s", type(other))
            return False
        return self._domain == other._domain and self._node == other._node


class XMPPRoom(XMPPIdentifier, Room):
    def __init__(self, room_jid, bot):
        self._bot = bot
        self.xep0045 = self._bot.conn.client.plugin['xep_0045']
        node, domain, resource = split_identifier(room_jid)
        super().__init__(node, domain, resource)

    def join(self, username=None, password=None):
        """
        Join the room.

        If the room does not exist yet, this will automatically call
        :meth:`create` on it first.
        """
        room = str(self)
        self.xep0045.joinMUC(room, username, password=password, wait=True)
        self._bot.conn.add_event_handler(f'muc::{room}::got_online', self._bot.user_joined_chat)
        self._bot.conn.add_event_handler(f'muc::{room}::got_offline', self._bot.user_left_chat)
        # Room configuration can only be done once a MUC presence stanza
        # has been received from the server. This HAS to take place in a
        # separate thread because of how SleekXMPP processes these stanzas.
        t = Thread(target=self.configure)
        t.setDaemon(True)
        t.start()
        self._bot.callback_room_joined(self)
        log.info('Joined room %s.', room)

    def leave(self, reason=None):
        """
        Leave the room.

        :param reason:
            An optional string explaining the reason for leaving the room
        """
        if reason is None:
            reason = ""
        room = str(self)
        try:
            self.xep0045.leaveMUC(room=room, nick=self.xep0045.ourNicks[room], msg=reason)

            self._bot.conn.del_event_handler(f'muc::{room}::got_online', self._bot.user_joined_chat)
            self._bot.conn.del_event_handler(f'muc::{room}::got_offline', self._bot.user_left_chat)
            log.info('Left room %s.', room)
            self._bot.callback_room_left(self)
        except KeyError:
            log.debug('Trying to leave %s while not in this room.', room)

    def create(self):
        """
        Not supported on this back-end (SleekXMPP doesn't support it).
        Will join the room to ensure it exists, instead.
        """
        logging.warning(
            "XMPP back-end does not support explicit creation, joining room "
            "instead to ensure it exists."
        )
        self.join(username=str(self))

    def destroy(self):
        """
        Destroy the room.

        Calling this on a non-existing room is a no-op.
        """
        self.xep0045.destroy(str(self))
        log.info('Destroyed room %s.', self)

    @property
    def exists(self):
        """
        Boolean indicating whether this room already exists or not.

        :getter:
            Returns `True` if the room exists, `False` otherwise.
        """
        logging.warning(
            'XMPP back-end does not support determining if a room exists. Returning the result of joined instead.')
        return self.joined

    @property
    def joined(self):
        """
        Boolean indicating whether this room has already been joined.

        :getter:
            Returns `True` if the room has been joined, `False` otherwise.
        """
        return str(self) in self.xep0045.getJoinedRooms()

    @property
    def topic(self):
        """
        The room topic.

        :getter:
            Returns the topic (a string) if one is set, `None` if no
            topic has been set at all.
        :raises:
            :class:`~RoomNotJoinedError` if the room has not yet been joined.
        """
        if not self.joined:
            raise RoomNotJoinedError("Must be in a room in order to see the topic.")
        try:
            return self._bot._room_topics[str(self)]
        except KeyError:
            return None

    @topic.setter
    def topic(self, topic):
        """
        Set the room's topic.

        :param topic:
            The topic to set.
        """
        # Not supported by SleekXMPP at the moment :(
        raise NotImplementedError("Setting the topic is not supported on this back-end.")

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
            for occupant in self.xep0045.rooms[str(self)].values():
                room_node, room_domain, _ = split_identifier(occupant['room'])
                nick = occupant['nick']
                occupants.append(XMPPRoomOccupant(room_node, room_domain, nick, self))
        except KeyError:
            raise RoomNotJoinedError("Must be in a room in order to see occupants.")
        return occupants

    def invite(self, *args):
        """
        Invite one or more people into the room.

        :*args:
            One or more JID's to invite into the room.
        """
        room = str(self)
        for jid in args:
            self.xep0045.invite(room, jid)
            log.info('Invited %s to %s.', jid, room)

    def configure(self):
        """
        Configure the room.

        Currently this simply sets the default room configuration as
        received by the server. May be extended in the future to set
        a custom room configuration instead.
        """
        room = str(self)
        affiliation = None
        while affiliation is None:
            sleep(0.5)
            affiliation = self.xep0045.getJidProperty(
                room=room,
                nick=self.xep0045.ourNicks[room],
                jidProperty='affiliation'
            )

        if affiliation == "owner":
            log.debug('Configuring room %s: we have owner affiliation.', room)
            form = self.xep0045.getRoomConfig(room)
            self.xep0045.configureRoom(room, form)
        else:
            log.debug("Not configuring room %s: we don't have owner affiliation (affiliation=%s)", room, affiliation)


class XMPPRoomOccupant(XMPPPerson, RoomOccupant):
    def __init__(self, node, domain, resource, room):
        super().__init__(node, domain, resource)
        self._room = room

    @property
    def person(self):
        return str(self)  # this is the full identifier.

    @property
    def real_jid(self):
        """
        The JID of the room occupant, they used to login.
        Will only work if the errbot is moderator in the MUC or it is not anonymous.
        """
        room_jid = self._node + '@' + self._domain
        jid = JID(self._room.xep0045.getJidProperty(room_jid, self.resource, 'jid'))
        return jid.bare

    @property
    def room(self):
        return self._room

    nick = XMPPPerson.resource


class XMPPConnection(object):
    def __init__(self, jid, password, feature=None, keepalive=None, ca_cert=None, server=None, use_ipv6=None, bot=None):
        if feature is None:
            feature = {}
        self._bot = bot
        self.connected = False
        self.server = server
        self.client = ClientXMPP(jid, password, plugin_config={'feature_mechanisms': feature})
        self.client.register_plugin('xep_0030')  # Service Discovery
        self.client.register_plugin('xep_0045')  # Multi-User Chat
        self.client.register_plugin('xep_0199')  # XMPP Ping
        self.client.register_plugin('xep_0203')  # XMPP Delayed messages
        self.client.register_plugin('xep_0249')  # XMPP direct MUC invites

        if keepalive is not None:
            self.client.whitespace_keepalive = True  # Just in case SleekXMPP's default changes to False in the future
            self.client.whitespace_keepalive_interval = keepalive

        if use_ipv6 is not None:
            self.client.use_ipv6 = use_ipv6

        self.client.ca_certs = ca_cert  # Used for TLS certificate validation

        self.client.add_event_handler("session_start", self.session_start)

    def session_start(self, _):
        self.client.send_presence()
        self.client.get_roster()

    def connect(self):
        if not self.connected:
            if self.server is not None:
                self.client.connect(self.server)
            else:
                self.client.connect()
            self.connected = True
        return self

    def disconnect(self):
        self.client.disconnect(wait=True)
        self.connected = False

    def serve_forever(self):
        self.client.process(block=True)

    def add_event_handler(self, name, cb):
        self.client.add_event_handler(name, cb)

    def del_event_handler(self, name, cb):
        self.client.del_event_handler(name, cb)


XMPP_TO_ERR_STATUS = {'available': ONLINE,
                      'away': AWAY,
                      'dnd': DND,
                      'unavailable': OFFLINE}


def split_identifier(txtrep):
    split_jid = txtrep.split('@', 1)
    node, domain = '@'.join(split_jid[:-1]), split_jid[-1]
    if domain.find('/') != -1:
        domain, resource = domain.split('/', 1)
    else:
        resource = None

    return node, domain, resource


class XMPPBackend(ErrBot):
    room_factory = XMPPRoom
    roomoccupant_factory = XMPPRoomOccupant

    def __init__(self, config):
        super().__init__(config)
        identity = config.BOT_IDENTITY

        self.jid = identity['username']  # backward compatibility
        self.password = identity['password']
        self.server = identity.get('server', None)
        self.feature = config.__dict__.get('XMPP_FEATURE_MECHANISMS', {})
        self.keepalive = config.__dict__.get('XMPP_KEEPALIVE_INTERVAL', None)
        self.ca_cert = config.__dict__.get('XMPP_CA_CERT_FILE', '/etc/ssl/certs/ca-certificates.crt')
        self.xhtmlim = config.__dict__.get('XMPP_XHTML_IM', False)
        self.use_ipv6 = config.__dict__.get('XMPP_USE_IPV6', None)

        # generic backend compatibility
        self.bot_identifier = self._build_person(self.jid)

        self.conn = self.create_connection()
        self.conn.add_event_handler("message", self.incoming_message)
        self.conn.add_event_handler("session_start", self.connected)
        self.conn.add_event_handler("disconnected", self.disconnected)
        # presence related handlers
        self.conn.add_event_handler("got_online", self.contact_online)
        self.conn.add_event_handler("got_offline", self.contact_offline)
        self.conn.add_event_handler("changed_status", self.user_changed_status)
        # MUC subject events
        self.conn.add_event_handler("groupchat_subject", self.chat_topic)
        self._room_topics = {}
        self.md_xhtml = xhtml()
        self.md_text = text()

    def create_connection(self):
        return XMPPConnection(
            jid=self.jid,  # textual and original representation
            password=self.password,
            feature=self.feature,
            keepalive=self.keepalive,
            ca_cert=self.ca_cert,
            server=self.server,
            use_ipv6=self.use_ipv6,
            bot=self
        )

    def _build_room_occupant(self, txtrep):
        node, domain, resource = split_identifier(txtrep)
        return self.roomoccupant_factory(node, domain, resource, self.query_room(node + '@' + domain))

    def _build_person(self, txtrep):
        return XMPPPerson(*split_identifier(txtrep))

    def incoming_message(self, xmppmsg):
        """Callback for message events"""
        if xmppmsg['type'] == "error":
            log.warning("Received error message: %s", xmppmsg)
            return

        msg = Message(xmppmsg['body'])
        if 'html' in xmppmsg.keys():
            msg.html = xmppmsg['html']
        log.debug("incoming_message from: %s", msg.frm)
        if xmppmsg['type'] == 'groupchat':
            msg.frm = self._build_room_occupant(xmppmsg['from'].full)
            msg.to = msg.frm.room
        else:
            msg.frm = self._build_person(xmppmsg['from'].full)
            msg.to = self._build_person(xmppmsg['to'].full)

        msg.nick = xmppmsg['mucnick']
        msg.delayed = bool(xmppmsg['delay']._get_attr('stamp'))  # this is a bug in sleekxmpp it should be ['from']
        self.callback_message(msg)

    def _idd_from_event(self, event):
        txtrep = event['from'].full
        return self._build_room_occupant(txtrep) if 'muc' in event else self._build_person(txtrep)

    def contact_online(self, event):
        log.debug('contact_online %s.', event)
        self.callback_presence(Presence(identifier=self._idd_from_event(event), status=ONLINE))

    def contact_offline(self, event):
        log.debug('contact_offline %s.', event)
        self.callback_presence(Presence(identifier=self._idd_from_event(event), status=OFFLINE))

    def user_joined_chat(self, event):
        log.debug('user_join_chat %s', event)
        self.callback_presence(Presence(identifier=self._idd_from_event(event), status=ONLINE))

    def user_left_chat(self, event):
        log.debug('user_left_chat %s', event)
        self.callback_presence(Presence(identifier=self._idd_from_event(event), status=OFFLINE))

    def chat_topic(self, event):
        log.debug("chat_topic %s.", event)
        room = event.values['mucroom']
        topic = event.values['subject']
        if topic == "":
            topic = None
        self._room_topics[room] = topic
        room = XMPPRoom(event.values['mucroom'], self)
        self.callback_room_topic(room)

    def user_changed_status(self, event):
        log.debug('user_changed_status %s.', event)
        errstatus = XMPP_TO_ERR_STATUS.get(event['type'], None)
        message = event['status']
        if not errstatus:
            errstatus = event['type']
        self.callback_presence(Presence(identifier=self._idd_from_event(event), status=errstatus, message=message))

    def connected(self, data):
        """Callback for connection events"""
        self.connect_callback()

    def disconnected(self, data):
        """Callback for disconnection events"""
        self.disconnect_callback()

    def send_message(self, msg):
        super().send_message(msg)

        log.debug('send_message to %s', msg.to)

        # We need to unescape the unicode characters (not the markup incompatible ones)
        mhtml = xhtmlim.unescape(self.md_xhtml.convert(msg.body)) if self.xhtmlim else None

        self.conn.client.send_message(mto=str(msg.to),
                                      mbody=self.md_text.convert(msg.body),
                                      mhtml=mhtml,
                                      mtype='chat' if msg.is_direct else 'groupchat')

    def change_presence(self, status: str = ONLINE, message: str = '') -> None:
        log.debug('Change bot status to %s, message %s.', status, message)
        self.conn.client.send_presence(pshow=status, pstatus=message)

    def serve_forever(self):
        self.conn.connect()

        try:
            self.conn.serve_forever()
        finally:
            log.debug("Trigger disconnect callback")
            self.disconnect_callback()
            log.debug("Trigger shutdown")
            self.shutdown()

    @lru_cache(IDENTIFIERS_LRU)
    def build_identifier(self, txtrep):
        log.debug('build identifier for %s', txtrep)
        try:
            xep0030 = self.conn.client.plugin['xep_0030']
            info = xep0030.get_info(jid=txtrep)
            disco_info = info['disco_info']
            if disco_info:  # Hipchat can return an empty response here.
                for category, typ, _, name in disco_info['identities']:
                    if category == 'conference':
                        log.debug('This is a room ! %s', txtrep)
                        return self.query_room(txtrep)
                    if category == 'client' and 'http://jabber.org/protocol/muc' in info['disco_info']['features']:
                        log.debug('This is room occupant ! %s', txtrep)
                        return self._build_room_occupant(txtrep)
        except IqError as iq:
            log.debug('xep_0030 is probably not implemented on this server. %s.', iq)
        log.debug('This is a person ! %s', txtrep)
        return self._build_person(txtrep)

    def build_reply(self, msg, text=None, private=False, threaded=False):
        response = self.build_message(text)
        response.frm = self.bot_identifier

        if msg.is_group and not private:
            # stripped returns the full bot@conference.domain.tld/chat_username
            # but in case of a groupchat, we should only try to send to the MUC address
            # itself (bot@conference.domain.tld)
            response.to = XMPPRoom(msg.frm.node + '@' + msg.frm.domain, self)
        elif msg.is_direct:
            # preserve from in case of a simple chat message.
            # it is either a user to user or user_in_chatroom to user case.
            # so we need resource.
            response.to = msg.frm
        elif hasattr(msg.to, 'person') and msg.to.person == self.bot_config.BOT_IDENTITY['username']:
            # This is a direct private message, not initiated through a MUC. Use
            # stripped to remove the resource so that the response goes to the
            # client with the highest priority
            response.to = XMPPPerson(msg.frm.node, msg.frm.domain, None)
        else:
            # This is a private message that was initiated through a MUC. Don't use
            # stripped here to retain the resource, else the XMPP server doesn't
            # know which user we're actually responding to.
            response.to = msg.frm
        return response

    @property
    def mode(self):
        return 'xmpp'

    def rooms(self):
        """
        Return a list of rooms the bot is currently in.

        :returns:
            A list of :class:`~errbot.backends.base.XMPPMUCRoom` instances.
        """
        xep0045 = self.conn.client.plugin['xep_0045']
        return [XMPPRoom(room, self) for room in xep0045.getJoinedRooms()]

    def query_room(self, room):
        """
        Query a room for information.

        :param room:
            The JID/identifier of the room to query for.
        :returns:
            An instance of :class:`~XMPPMUCRoom`.
        """
        return XMPPRoom(room, self)

    def prefix_groupchat_reply(self, message, identifier):
        super().prefix_groupchat_reply(message, identifier)
        message.body = f'@{identifier.nick} {message.body}'

    def __hash__(self):
        return 0
