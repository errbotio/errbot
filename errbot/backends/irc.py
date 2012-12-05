import logging
import sys
import threading
irc_message_lock = threading.Lock()
import config

try:
    from twisted.internet import protocol, reactor
    from twisted.words.protocols.irc import IRCClient
    from twisted.internet.protocol import ClientFactory
except ImportError:
    logging.exception("Could not start the IRC backend")
    logging.error("""
    If you intend to use the IRC backend please install Twisted Words:
    -> On debian-like systems
    sudo apt-get install python-twisted-words
    -> On Gentoo
    sudo emerge -av dev-python/twisted-words
    -> Generic
    pip install "Twisted Words"
    """)
    sys.exit(-1)

from errbot.backends.base import Message
from errbot.errBot import ErrBot
from errbot.utils import utf8

class IRCConnection(IRCClient, object):
    connected = False

    def __init__(self, callback, nickname='err', password=None):
        self.nickname = nickname
        self.callback = callback
        self.password = password
        config_dict = config.__dict__
        self.channel_rate = config_dict.get("IRC_CHANNEL_RATE", 1)
        self.private_rate = config_dict.get("IRC_PRIVATE_RATE", 1)

    #### Connection

    def send_message(self, mess):
        global irc_message_lock
        if self.connected:
            m = utf8(mess.getBody())
            if m[-1] != '\n':
                m+='\n'
            with irc_message_lock:
                to = mess.getTo().node.encode('ascii', 'replace')
                self.lineRate = self.channel_rate if to.startswith('#') else self.private_rate
                self.msg(to, m.encode('ascii', 'replace'))
        else:
            logging.debug("Zapped message because the backend is not connected yet %s" % mess.getBody())

    #### IRC Client duck typing
    def lineReceived(self, line):
        logging.debug('IRC line received : %s' % line)
        super(IRCConnection, self).lineReceived(line)

    def irc_PRIVMSG(self, prefix, params):
        fr, line = params
        if fr == self.nickname: # it is a private message
            fr = prefix.split('!')[0] # reextract the real from
            typ = 'chat'
        else:
            typ = 'groupchat'
        logging.debug('IRC message received from %s [%s]' % (fr, line))
        msg = Message(unicode(line, errors='replace'), typ=typ)
        msg.setFrom(unicode(fr, errors='replace')) # already a compatible format
        msg.setTo(unicode(params[0], errors='replace'))
        self.callback.callback_message(self, msg)


    def connectionMade(self):
        self.connected = True
        super(IRCConnection, self).connectionMade()
        self.callback.connect_callback() # notify that the connection occured
        logging.debug("IRC Connected")

    def clientConnectionLost(self, connection, reason):
        pass


class IRCFactory(ClientFactory):
    """
    Factory used for creating IRC protocol objects
    """

    protocol = IRCConnection

    def __init__(self, callback, nickname='err-chatbot', password=None):
        self.irc = IRCConnection(callback, nickname, password)

    def buildProtocol(self, addr=None):
        return self.irc

    def clientConnectionLost(self, conn, reason):
        pass


ENCODING_INPUT = sys.stdin.encoding

class IRCBackend(ErrBot):
    conn = None

    def __init__(self, nickname, server, port=6667, password=None, ssl=False):
        super(IRCBackend, self).__init__()
        self.nickname = nickname
        self.server = server
        self.port = port
        self.password = password
        self.ssl = ssl

        if ssl:
            try:
                from twisted.internet import ssl
            except ImportError:
                logging.exception("Could not start the IRC backend")
                logging.error("""
If you intend to use SSL with the IRC backend please install pyopenssl:
-> On debian-like systems
sudo apt-get install python-openssl
-> On Gentoo
sudo emerge -av dev-python/pyopenssl
-> Generic
pip install pyopenssl
                """)
                sys.exit(-1)


    def serve_forever(self):
        self.jid = self.nickname + '@localhost'
        self.connect() # be sure we are "connected" before the first command
        try:
            reactor.run()
        finally:
            logging.debug("Trigger disconnect callback")
            self.disconnect_callback()
            logging.debug("Trigger shutdown")
            self.shutdown()

    def connect(self):
        if not self.conn:
            ircFactory = IRCFactory(self, self.jid.split('@')[0], self.password)
            self.conn = ircFactory.irc
            if self.ssl:
                from twisted.internet import ssl
                reactor.connectSSL(self.server, self.port, ircFactory, ssl.ClientContextFactory())
            else:
                reactor.connectTCP(self.server, self.port, ircFactory)
        return self.conn

    def build_message(self, text):
        return Message((self.build_text_html_message_pair(text)[0]).encode('ascii', 'replace')) # 0 = Only retain pure text

    def shutdown(self):
        super(IRCBackend, self).shutdown()

    def join_room(self, room, username=None, password=None):
        self.conn.join(room)

    @property
    def mode(self):
        return 'IRC'
