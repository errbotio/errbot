import logging
from sleekxmpp import ClientXMPP
from errbot.backends.base import Message, build_message, Connection
from errbot.errBot import ErrBot


class XMPPConnection(Connection):
    def __init__(self, jid, password):
        self.connected = False
        self.client = ClientXMPP(jid, password, plugin_config={'feature_mechanisms': {'use_mech': 'PLAIN', 'unencrypted_plain': True, 'encrypted_plain': False}})
        self.client.register_plugin('xep_0030')  # Service Discovery
        self.client.register_plugin('xep_0045')  # Multi-User Chat
        self.client.register_plugin('xep_0199')  # XMPP Ping
        self.client.register_plugin('xep_0203')  # XMPP Delayed messages
        self.client.add_event_handler("session_start", self.session_start)

    def send_message(self, mess):
        self.client.send_message(mto=mess.getTo(),
                                 mbody=mess.getBody(),
                                 mtype=mess.getType(),
                                 mhtml=mess.getHTML())

    def session_start(self, event):
        self.client.send_presence()
        self.client.get_roster()

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


class XMPPBackend(ErrBot):
    def __init__(self, username, password, *args, **kwargs):
        super(XMPPBackend, self).__init__(*args, **kwargs)
        self.jid = username
        self.password = password
        self.conn = self.create_connection()
        self.conn.add_event_handler("message", self.incoming_message)
        self.conn.add_event_handler("session_start", self.connected)

    def create_connection(self):
        return XMPPConnection(self.jid, self.password)

    def incoming_message(self, xmppmsg):
        msg = Message(xmppmsg['body'])
        msg.setFrom(xmppmsg['from'].bare)
        msg.setTo(xmppmsg['to'].bare)
        msg.setType(xmppmsg['type'])
        msg.setMuckNick(xmppmsg['mucnick'])
        msg.setDelayed(bool(xmppmsg['delay']._get_attr('stamp')))  # this is a bug in sleekxmpp it should be ['from']
        self.callback_message(self.conn, msg)

    def connected(self, data):
        self.connect_callback()  # notify that the connection occured

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

    @property
    def mode(self):
        return 'xmpp'
