from __future__ import absolute_import
import logging
import sys
import config
from errbot.backends.base import Message, build_message, build_text_html_message_pair
from errbot.errBot import ErrBot
from errbot.utils import RateLimited

try:
    import irc.connection
    from irc.bot import SingleServerIRCBot
except ImportError as _:
    logging.exception("Could not start the IRC backend")
    logging.fatal("""
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


class IRCConnection(SingleServerIRCBot):
    def __init__(self, callback, nickname, server, port=6667, ssl=False, password=None, username=None):
        self.use_ssl = ssl
        self.callback = callback
        if username is None:
            username = nickname
        super().__init__([(server, port, password)], nickname, username)

    def _dispatcher(self, c, e):
        super()._dispatcher(c, e)

    def connect(self, *args, **kwargs):
        if self.use_ssl:
            import ssl
            ssl_factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
            self.connection.connect(*args, connect_factory=ssl_factory, **kwargs)
        else:
            self.connection.connect(*args, **kwargs)

    def on_welcome(self, c, e):
        logging.info("IRC welcome %s" % e)
        self.callback.connect_callback()

    def on_pubmsg(self, c, e):
        msg = Message(e.arguments[0])
        msg.setFrom(e.target)
        msg.setTo(self.callback.jid)
        msg.setMuckNick(e.source.split('!')[0])  # FIXME find the real nick in the channel
        msg.setType('groupchat')
        self.callback.callback_message(self, msg)

    def on_privmsg(self, c, e):
        msg = Message(e.arguments[0])
        msg.setFrom(e.source.split('!')[0])
        msg.setTo(e.target)
        msg.setType('chat')
        self.callback.callback_message(self, msg)

    def send_message(self, mess):
        msg_func = self.send_private_message if mess.typ == 'chat' else self.send_public_message
        # If this is a response in private of a public message take the recipient in
        # the resource instead of the incoming chatroom
        if mess.typ == 'chat' and mess.getTo().resource:
            to = mess.getTo().resource
        else:
            to = mess.getTo().node
        for line in build_text_html_message_pair(mess.getBody())[0].split('\n'):
            msg_func(to, line)

    @RateLimited(config.__dict__.get('IRC_PRIVATE_RATE', 1))
    def send_private_message(self, to, line):
        self.connection.privmsg(to, line)

    @RateLimited(config.__dict__.get('IRC_CHANNEL_RATE', 1))
    def send_public_message(self, to, line):
        self.connection.privmsg(to, line)


class IRCBackend(ErrBot):
    def __init__(self, nickname, server, port=6667, password=None, ssl=False, username=None):
        self.jid = Identifier(node = nickname, domain = server)
        super(IRCBackend, self).__init__()
        self.conn = IRCConnection(self, nickname, server, port, ssl, password, username)

    def serve_forever(self):
        try:
            self.conn.start()
        finally:
            logging.debug("Trigger disconnect callback")
            self.disconnect_callback()
            logging.debug("Trigger shutdown")
            self.shutdown()

    def connect(self):
        return self.conn

    def build_message(self, text):
        return build_message(text, Message)

    def shutdown(self):
        super().shutdown()

    def join_room(self, room, username=None, password=None):
        self.conn.connection.join(room)

    @property
    def mode(self):
        return 'irc'
