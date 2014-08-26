import logging
import sys
import os.path

from errbot.backends.base import Message, Presence, build_message, Connection, Identifier
from errbot.backends.base import ONLINE, OFFLINE, AWAY, DND
from errbot.errBot import ErrBot
from threading import Thread
from time import sleep

try:
    from sleekxmpp import ClientXMPP
    from sleekxmpp.xmlstream import resolver, cert
except ImportError as _:
    logging.exception("Could not start the XMPP backend")
    logging.fatal("""
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

try:
    from config import XMPP_FEATURE_MECHANISMS
except ImportError:
    XMPP_FEATURE_MECHANISMS = {}
try:
    from config import XMPP_KEEPALIVE_INTERVAL
except ImportError:
    XMPP_KEEPALIVE_INTERVAL = None
try:
    from config import XMPP_CA_CERT_FILE
except ImportError:
    XMPP_CA_CERT_FILE = "/etc/ssl/certs/ca-certificates.crt"

if XMPP_CA_CERT_FILE is not None and not os.path.exists(XMPP_CA_CERT_FILE):
    logging.fatal("The CA certificate path set by XMPP_CA_CERT_FILE does not exist. "
                  "Please set XMPP_CA_CERT_FILE to a valid file, or disable certificate"
                  "validation by setting it to None (not recommended!).")
    sys.exit(-1)
try:
    from config import CHATROOM_PRESENCE
except ImportError:
    CHATROOM_PRESENCE = ()


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
                logging.info('google cert found for %s', xmpp_client.boundjid.server)
                return
        except cert.CertificateError:
            pass

    logging.error("invalid cert received for %s", xmpp_client.boundjid.server)


class XMPPConnection(Connection):
    def __init__(self, jid, password):
        self.connected = False
        self.client = ClientXMPP(str(jid), password, plugin_config={'feature_mechanisms': XMPP_FEATURE_MECHANISMS})
        self.client.register_plugin('xep_0030')  # Service Discovery
        self.client.register_plugin('xep_0045')  # Multi-User Chat
        self.client.register_plugin('xep_0004')  # Multi-User Chat backward compability (necessary for join room)
        self.client.register_plugin('xep_0199')  # XMPP Ping
        self.client.register_plugin('xep_0203')  # XMPP Delayed messages
        self.client.register_plugin('xep_0249')  # XMPP direct MUC invites

        if XMPP_KEEPALIVE_INTERVAL is not None:
            self.client.whitespace_keepalive = True  # Just in case SleekXMPP's default changes to False in the future
            self.client.whitespace_keepalive_interval = XMPP_KEEPALIVE_INTERVAL

        self.client.ca_certs = XMPP_CA_CERT_FILE  # Used for TLS certificate validation

        self.client.add_event_handler("session_start", self.session_start)
        self.client.add_event_handler("ssl_invalid_cert", self.ssl_invalid_cert)

    def send_message(self, mess):
        self.client.send_message(mto=mess.getTo(),
                                 mbody=mess.getBody(),
                                 mtype=mess.getType(),
                                 mhtml=mess.getHTML())

    def session_start(self, _):
        self.client.send_presence()
        self.client.get_roster()

    def ssl_invalid_cert(self, _):
        # Special quirk for google domains
        verify_gtalk_cert(self.client)

    def connect(self):
        if not self.connected:
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
        """Attempt to join the given MUC"""
        muc = self.client.plugin['xep_0045']
        muc.joinMUC(room,
                    username,
                    password=password,
                    wait=True)
        # Room configuration can only be done once a MUC presence stanza
        # has been received from the server. This HAS to take place in a
        # separate thread because of how SleekXMPP processes these stanzas.
        t = Thread(target=self.configure_room, args=[room])
        t.setDaemon(True)
        t.start()

    def configure_room(self, room):
        """
        Configure the given MUC

        Currently this simply sets the default room configuration as
        received by the server. May be extended in the future to set
        a custom room configuration instead.
        """
        muc = self.client.plugin['xep_0045']
        affiliation = None
        while affiliation is None:
            sleep(0.5)
            affiliation = muc.getJidProperty(
                room=room,
                nick=muc.ourNicks[room],
                jidProperty='affiliation'
            )

        if affiliation == "owner":
            logging.debug("Configuring room {} because we have owner affiliation".format(room))
            form = muc.getRoomConfig(room)
            muc.configureRoom(room, form)
        else:
            logging.debug("Not configuring room {} because we don't have owner affiliation (affiliation={})"
                          .format(room, affiliation))

    def invite_in_room(self, room, jids_to_invite):
        muc = self.client.plugin['xep_0045']
        for jid in jids_to_invite:
            logging.debug("Inviting %s to %s..." % (jid, room))
            muc.invite(room, jid)

XMPP_TO_ERR_STATUS = { 'available': ONLINE,
                       'away': AWAY,
                       'dnd': DND,
                       'unavailable': OFFLINE }

class XMPPBackend(ErrBot):
    def __init__(self, username, password, *args, **kwargs):
        super(XMPPBackend, self).__init__(*args, **kwargs)
        self.jid = Identifier(username)
        self.password = password
        self.conn = self.create_connection()
        self.conn.add_event_handler("message", self.incoming_message)
        self.conn.add_event_handler("session_start", self.connected)
        self.conn.add_event_handler("disconnected", self.disconnected)
        # presence related handlers
        self.conn.add_event_handler("got_online", self.contact_online)
        self.conn.add_event_handler("got_offline", self.contact_offline)
        self.conn.add_event_handler("changed_status", self.user_changed_status)
        # NOTE: for now we will register the handlers this way
        e_muc_online = "muc::{}::got_online"
        e_muc_offline = "muc::{}::got_offline"
        for room in CHATROOM_PRESENCE:
            # using string or first element of (room, passwd) tuple
            room = room if isinstance(room, str) else room[0]
            self.conn.add_event_handler(e_muc_online.format(room),
                                        self.user_joined_chat)
            self.conn.add_event_handler(e_muc_offline.format(room),
                                        self.user_left_chat)

    def create_connection(self):
        return XMPPConnection(self.jid, self.password)

    def incoming_message(self, xmppmsg):
        """Callback for message events"""
        msg = Message(xmppmsg['body'])
        if 'html' in xmppmsg.keys():
            msg.setHTML(xmppmsg['html'])
        msg.setFrom(xmppmsg['from'].full)
        msg.setTo(xmppmsg['to'].full)
        msg.setType(xmppmsg['type'])
        msg.setMuckNick(xmppmsg['mucnick'])
        msg.setDelayed(bool(xmppmsg['delay']._get_attr('stamp')))  # this is a bug in sleekxmpp it should be ['from']
        self.callback_message(self.conn, msg)

    def contact_online(self, event):
        logging.debug("contact_online %s" % event)
        p = Presence(identifier=Identifier(str(event['from'])),
                     status=ONLINE)
        self.callback_presence(self.conn, p)
           

    def contact_offline(self, event):
        logging.debug("contact_offline %s" % event)
        p = Presence(identifier=Identifier(str(event['from'])),
                     status=OFFLINE)
        self.callback_presence(self.conn, p)

    def user_joined_chat(self, event):
        logging.debug("user_join_chat %s" % event)
        idd = Identifier(str(event['from']))
        p = Presence(chatroom=idd,
                     nick=idd.getResource(),
                     status=ONLINE)
        self.callback_presence(self.conn, p)

    def user_left_chat(self, event):
        logging.debug("user_left_chat %s" % event)
        idd = Identifier(str(event['from']))
        p = Presence(chatroom=idd,
                     nick=idd.getResource(),
                     status=OFFLINE)
        self.callback_presence(self.conn, p)

    def user_changed_status(self, event):
        logging.debug("user_changed_status %s" % event)
        errstatus = XMPP_TO_ERR_STATUS.get(event['type'], None)
        message = event['status']
        if not errstatus:
            errstatus = event['type']
        
        p = Presence(identifier=Identifier(str(event['from'])),
                     status=errstatus, message=message)
        self.callback_presence(self.conn, p)

    def connected(self, data):
        """Callback for connection events"""
        self.connect_callback()

    def disconnected(self, data):
        """Callback for disconnection events"""
        self.disconnect_callback()

    def serve_forever(self):
        self.connect()  # be sure we are "connected" before the first command

        try:
            self.conn.serve_forever()
        finally:
            logging.debug("Trigger disconnect callback")
            self.disconnect_callback()
            logging.debug("Trigger shutdown")
            self.shutdown()

    def connect(self):
        return self.conn.connect()

    def build_message(self, text):
        return build_message(text, Message)

    def join_room(self, room, username=None, password=None):
        self.conn.join_room(room, username, password)

    def invite_in_room(self, room, jids_to_invite):
        self.conn.invite_in_room(room, jids_to_invite)

    @property
    def mode(self):
        return 'xmpp'
