import logging
import sys
import warnings

from errbot.backends.base import (
    Message, MUCRoom, MUCOccupant, Presence, RoomNotJoinedError,
    build_message,
    Identifier)
from errbot.backends.base import ONLINE, OFFLINE, AWAY, DND
from errbot.errBot import ErrBot
from threading import Thread
from time import sleep
from errbot.utils import parse_jid

log = logging.getLogger(__name__)

try:
    from sleekxmpp import ClientXMPP
    from sleekxmpp.xmlstream import resolver, cert
except ImportError as _:
    log.exception("Could not start the XMPP backend")
    log.fatal("""
    If you intend to use the XMPP backend please install the python sleekxmpp package:
    -> On debian-like systems
    sudo apt-get install python-software-properties
    sudo apt-get update
    sudo apt-get install python-sleekxmpp
    -> On Gentoo
    sudo layman -a laurentb
    sudo emerge -av dev-python/sleekxmpp
    -> Generic
    pip install sleekxmpp
    """)
    sys.exit(-1)


def verify_gtalk_cert(xmpp_client):
    """
        Hack specific for google apps domains with SRV entries.
        It needs to fid the SSL certificate of google and not the one for your domain
    """

    hosts = resolver.get_SRV(xmpp_client.boundjid.server, 5222,
                             xmpp_client.dns_service,
                             resolver=resolver.default_resolver())
    it_is_google = False
    for host, _ in hosts:
        if host.lower().find('google.com') > -1:
            it_is_google = True

    if it_is_google:
        raw_cert = xmpp_client.socket.getpeercert(binary_form=True)
        try:
            if cert.verify('talk.google.com', raw_cert):
                log.info('google cert found for %s', xmpp_client.boundjid.server)
                return
        except cert.CertificateError:
            pass

    log.error("invalid cert received for %s", xmpp_client.boundjid.server)

class XMPPIdentifier(Identifier):
    """
    This class is the parent and the basic contract of all the ways the backends
    are identifying a person on their system.
    """

    def __init__(self, jid=None, node='', domain='', resource=''):
        if jid:
            self._node, self._domain, self._resource = parse_jid(jid)
        else:
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
    def stripped(self):
        if self._domain:
            return self._node + '@' + self._domain
        return self._node  # if the backend has no domain notion

    def bare_match(self, other):
        """ checks if 2 identifiers are equal, ignoring the resource """
        return other.stripped == self.stripped

    def __str__(self):
        answer = self.stripped
        if self._resource:
            answer += '/' + self._resource
        return answer

    def __unicode__(self):
        return str(self.__str__())


class XMPPMUCRoom(MUCRoom):
    def __init__(self, *args, **kwargs):
        super(XMPPMUCRoom, self).__init__(*args, **kwargs)
        self.xep0045 = self._bot.conn.client.plugin['xep_0045']

    def join(self, username=None, password=None):
        """
        Join the room.

        If the room does not exist yet, this will automatically call
        :meth:`create` on it first.
        """
        room = str(self)
        self.xep0045.joinMUC(str(self), username, password=password, wait=True)
        self._bot.conn.add_event_handler(
            "muc::{}::got_online".format(room),
            self._bot.user_joined_chat
        )
        self._bot.conn.add_event_handler(
            "muc::{}::got_offline".format(room),
            self._bot.user_left_chat
        )
        # Room configuration can only be done once a MUC presence stanza
        # has been received from the server. This HAS to take place in a
        # separate thread because of how SleekXMPP processes these stanzas.
        t = Thread(target=self.configure)
        t.setDaemon(True)
        t.start()
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
        try:
            self.xep0045.leaveMUC(room=room, nick=self.xep0045.ourNicks[room], msg=reason)

            self._bot.conn.del_event_handler(
                "muc::{}::got_online".format(room),
                self._bot.user_joined_chat
            )
            self._bot.conn.del_event_handler(
                "muc::{}::got_offline".format(room),
                self._bot.user_left_chat
            )
            log.info("Left room {}".format(room))
            self._bot.callback_room_left(self)
        except KeyError:
            log.debug("Trying to leave {} while not in this room".format(room))

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
        log.info("Destroyed room {!s}".format(self))

    @property
    def exists(self):
        """
        Boolean indicating whether this room already exists or not.

        :getter:
            Returns `True` if the room exists, `False` otherwise.
        """
        logging.warning(
            "XMPP back-end does not support determining if a room exists. "
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
                occupant = occupant.copy()
                for attr in ("node", "domain", "resource"):
                    occupant.pop(attr, None)
                occupants.append(XMPPMUCOccupant(jid=str(occupant.pop("jid")), **occupant))
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
            log.info("Invited {} to {}".format(jid, room))

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
            log.debug("Configuring room {} because we have owner affiliation".format(room))
            form = self.xep0045.getRoomConfig(room)
            self.xep0045.configureRoom(room, form)
        else:
            log.debug("Not configuring room {} because we don't have owner affiliation (affiliation={})"
                      .format(room, affiliation))


class XMPPMUCOccupant(MUCOccupant):
    def __init__(self, **kwargs):
        super(XMPPMUCOccupant, self).__init__(jid=kwargs.pop("jid"))

        for k, v in kwargs.items():
            # Ensure existing attributes can't be overridden, either accidentally
            # or maliciously by a rogue server.
            if not hasattr(self, k):
                setattr(self, k, v)


class XMPPConnection(object):
    def __init__(self, jid, password, feature=None, keepalive=None, ca_cert=None, server=None, bot=None):
        if feature is not None:
            feature = {}
        self._bot = bot
        self.connected = False
        self.server = server

        self.client = ClientXMPP(str(jid), password, plugin_config={'feature_mechanisms': feature})
        self.client.register_plugin('xep_0030')  # Service Discovery
        self.client.register_plugin('xep_0045')  # Multi-User Chat
        self.client.register_plugin('xep_0004')  # Multi-User Chat backward compability (necessary for join room)
        self.client.register_plugin('xep_0199')  # XMPP Ping
        self.client.register_plugin('xep_0203')  # XMPP Delayed messages
        self.client.register_plugin('xep_0249')  # XMPP direct MUC invites

        if keepalive is not None:
            self.client.whitespace_keepalive = True  # Just in case SleekXMPP's default changes to False in the future
            self.client.whitespace_keepalive_interval = keepalive

        self.client.ca_certs = ca_cert  # Used for TLS certificate validation

        self.client.add_event_handler("session_start", self.session_start)
        self.client.add_event_handler("ssl_invalid_cert", self.ssl_invalid_cert)

    def session_start(self, _):
        self.client.send_presence()
        self.client.get_roster()

    def ssl_invalid_cert(self, _):
        # Special quirk for google domains
        verify_gtalk_cert(self.client)

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

    def join_room(self, room, username, password):
        """
        Attempt to join the given MUC

        .. deprecated:: 2.2.0
            Use the methods on :class:`XMPPMUCRoom` instead.
        """
        warnings.warn(
            "Using join_room is deprecated, use join from the "
            "MUCRoom class instead.",
            DeprecationWarning
        )
        self._bot.query_room(room).join(username=username, password=password)

    def configure_room(self, room):
        """
        Configure the given MUC

        Currently this simply sets the default room configuration as
        received by the server. May be extended in the future to set
        a custom room configuration instead.

        .. deprecated:: 2.2.0
            Use the methods on :class:`XMPPMUCRoom` instead.
        """
        warnings.warn(
            "Using configure_room is deprecated, use configure from the "
            "MUCRoom class instead.",
            DeprecationWarning
        )
        self._bot.query_room(room).configure()

    def invite_in_room(self, room, jids_to_invite):
        """
        .. deprecated:: 2.2.0
            Use the methods on :class:`XMPPMUCRoom` instead.
        """
        warnings.warn(
            "Using invite_in_room is deprecated, use invite from the "
            "MUCRoom class instead.",
            DeprecationWarning,
        )
        self._bot.query_room(room).invite(jids_to_invite)

XMPP_TO_ERR_STATUS = {'available': ONLINE,
                      'away': AWAY,
                      'dnd': DND,
                      'unavailable': OFFLINE}


class XMPPBackend(ErrBot):

    def __init__(self, config):
        super(XMPPBackend, self).__init__(config)
        identity = config.BOT_IDENTITY

        self.jid = XMPPIdentifier(identity['username'])
        self.password = identity['password']
        self.server = identity.get('server', None)
        self.feature = config.__dict__.get('XMPP_FEATURE_MECHANISMS', {})
        self.keepalive = config.__dict__.get('XMPP_KEEPALIVE_INTERVAL', None)
        self.ca_cert = config.__dict__.get('XMPP_CA_CERT_FILE', '/etc/ssl/certs/ca-certificates.crt')

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

    def create_connection(self):
        return XMPPConnection(
            jid=self.jid,
            password=self.password,
            feature=self.feature,
            keepalive=self.keepalive,
            ca_cert=self.ca_cert,
            server=self.server,
            bot=self
        )

    def incoming_message(self, xmppmsg):
        """Callback for message events"""
        msg = Message(xmppmsg['body'])
        if 'html' in xmppmsg.keys():
            msg.html = xmppmsg['html']
        msg.frm = xmppmsg['from'].full
        msg.to = xmppmsg['to'].full
        msg.type = xmppmsg['type']
        msg.nick = xmppmsg['mucnick']
        msg.delayed = bool(xmppmsg['delay']._get_attr('stamp'))  # this is a bug in sleekxmpp it should be ['from']
        self.callback_message(msg)

    def contact_online(self, event):
        log.debug("contact_online %s" % event)
        p = Presence(identifier=XMPPIdentifier(str(event['from'])),
                     status=ONLINE)
        self.callback_presence(p)

    def contact_offline(self, event):
        log.debug("contact_offline %s" % event)
        p = Presence(identifier=XMPPIdentifier(str(event['from'])),
                     status=OFFLINE)
        self.callback_presence(p)

    def user_joined_chat(self, event):
        log.debug("user_join_chat %s" % event)
        idd = XMPPIdentifier(str(event['from']))
        p = Presence(chatroom=idd,
                     nick=idd.resource,
                     status=ONLINE)
        self.callback_presence(p)

    def user_left_chat(self, event):
        log.debug("user_left_chat %s" % event)
        idd = XMPPIdentifier(str(event['from']))
        p = Presence(chatroom=idd,
                     nick=idd.resource,
                     status=OFFLINE)
        self.callback_presence(p)

    def chat_topic(self, event):
        log.debug("chat_topic %s" % event)
        room = event.values['mucroom']
        topic = event.values['subject']
        if topic == "":
            topic = None
        self._room_topics[room] = topic
        room = XMPPMUCRoom(event.values['mucroom'])
        self.callback_room_topic(room)

    def user_changed_status(self, event):
        log.debug("user_changed_status %s" % event)
        errstatus = XMPP_TO_ERR_STATUS.get(event['type'], None)
        message = event['status']
        if not errstatus:
            errstatus = event['type']

        p = Presence(identifier=XMPPIdentifier(str(event['from'])),
                     status=errstatus, message=message)
        self.callback_presence(p)

    def connected(self, data):
        """Callback for connection events"""
        self.connect_callback()

    def disconnected(self, data):
        """Callback for disconnection events"""
        self.disconnect_callback()

    def send_message(self, mess):
        super(XMPPBackend, self).send_message(mess)
        self.conn.client.send_message(mto=mess.to,
                                      mbody=mess.body,
                                      mtype=mess.type,
                                      mhtml=mess.html)

    def serve_forever(self):
        self.conn.connect()

        try:
            self.conn.serve_forever()
        finally:
            log.debug("Trigger disconnect callback")
            self.disconnect_callback()
            log.debug("Trigger shutdown")
            self.shutdown()

    def build_message(self, text):
        return build_message(text, Message)

    def invite_in_room(self, room, jids_to_invite):
        """
        .. deprecated:: 2.2.0
            Use the methods on :class:`XMPPMUCRoom` instead.
        """
        warnings.warn(
            "Using invite_in_room is deprecated, use invite from the "
            "MUCRoom class instead.",
            DeprecationWarning,
        )
        self.query_room(room).invite(jids_to_invite)

    @property
    def mode(self):
        return 'xmpp'

    def rooms(self):
        """
        Return a list of rooms the bot is currently in.

        :returns:
            A list of :class:`~errbot.backends.base.XMPPMUCRoom` instances.
        """
        xep0045 = self.client.plugin['xep_0045']
        return [XMPPMUCRoom(room, bot=self) for room in xep0045.getJoinedRooms()]

    def query_room(self, room):
        """
        Query a room for information.

        :param room:
            The JID/identifier of the room to query for.
        :returns:
            An instance of :class:`~XMPPMUCRoom`.
        """
        return XMPPMUCRoom(room, bot=self)

    def groupchat_reply_format(self):
        return '@{0} {1}'
