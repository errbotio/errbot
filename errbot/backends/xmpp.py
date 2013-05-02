import logging
import sys

from errbot.backends.base import Message, build_message, Connection
from errbot.errBot import ErrBot

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
        self.client = ClientXMPP(jid, password, plugin_config={'feature_mechanisms': XMPP_FEATURE_MECHANISMS})
        self.client.register_plugin('xep_0030')  # Service Discovery
        self.client.register_plugin('xep_0045')  # Multi-User Chat
        self.client.register_plugin('old_0004')  # Multi-User Chat backward compability (necessary for join room)
        self.client.register_plugin('xep_0199')  # XMPP Ping
        self.client.register_plugin('xep_0203')  # XMPP Delayed messages
        self.client.register_plugin('xep_0249')  # XMPP direct MUC invites

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

    def join_room(self, room, username, password):
        muc = self.client.plugin['xep_0045']
        muc.joinMUC(room,
                    username,
                    password=password,
                    wait=True)
        form = muc.getRoomForm(room)
        if form:
            muc.configureRoom(room, form)
        else:
            logging.error("Error configuring the MUC Room %s" % room)

    def invite_in_room(self, room, jids_to_invite):
        muc = self.client.plugin['xep_0045']
        for jid in jids_to_invite:
            logging.debug("Inviting %s to %s..." % (jid, room))
            muc.invite(room, jid)



class XMPPBackend(ErrBot):
    def __init__(self, username, password, *args, **kwargs):
        super(XMPPBackend, self).__init__(*args, **kwargs)
        self.jid = username
        self.password = password
        self.conn = self.create_connection()
        self.conn.add_event_handler("message", self.incoming_message)
        self.conn.add_event_handler("session_start", self.connected)
        self.conn.add_event_handler("disconnected", self.disconnected)

    def create_connection(self):
        return XMPPConnection(self.jid, self.password)

    def incoming_message(self, xmppmsg):
        msg = Message(xmppmsg['body'])
        if 'html' in xmppmsg.keys():
            msg.setHTML(xmppmsg['html'])
        msg.setFrom(xmppmsg['from'].full)
        msg.setTo(xmppmsg['to'].full)
        msg.setType(xmppmsg['type'])
        msg.setMuckNick(xmppmsg['mucnick'])
        msg.setDelayed(bool(xmppmsg['delay']._get_attr('stamp')))  # this is a bug in sleekxmpp it should be ['from']
        self.callback_message(self.conn, msg)

    def connected(self, data):
        self.connect_callback()  # notify that the connection occured

    def disconnected(self, data):
        self.disconnect_callback()  # notify plugins that the disconnect occurred

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
