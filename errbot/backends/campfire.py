import logging
import sys
from pyexpat import ExpatError
from xmpp.simplexml import XML2Node
from errbot.backends.base import Identifier, Message, Connection
from errbot.errBot import ErrBot
from errbot.utils import xhtml2txt
from threading import Condition
import pyfire



class CampfireConnection(Connection, pyfire.Campfire):
    rooms = {} # keep track of joined room so we can send messages directly to them

    def send(self, mess):
        for (name, (room, stream)) in self.rooms.iteritems():
            room.speak(mess.getBody()) # Basic text support for the moment

    def join_room(self, name, msg_callback, error_callback):
        room = self.get_room_by_name(name)
        room.join()
        stream = room.get_stream(error_callback=error_callback)
        stream.attach(msg_callback).start()
        self.rooms[name] = (room, stream)

ENCODING_INPUT = sys.stdin.encoding

class CampfireBackend(ErrBot):
    exit_lock = Condition()

    def __init__(self, subdomain, username, password, ssl=True):
        super(CampfireBackend, self).__init__()
        self.jid = Identifier(node = username)
        self.conn = None
        self.subdomain = subdomain
        self.username = username
        self.password = password
        self.ssl = ssl

    def serve_forever(self):
        self.exit_lock.acquire()
        self.connect() # be sure we are "connected" before the first command
        self.connect_callback() # notify that the connection occured
        try:
            logging.info("Campfire connected.")
            self.exit_lock.wait()
        except KeyboardInterrupt as ki:
            pass
        finally:
            self.exit_lock.release()
            self.disconnect_callback()
            self.shutdown()

    def connect(self):
        if not self.conn:
            self.conn = CampfireConnection(self.subdomain, self.username, self.password, self.ssl)
        return self.conn

    def build_message(self, text):
        return Message(text)

    def shutdown(self):
        super(CampfireBackend, self).shutdown()

    def msg_callback(self, message):
        logging.debug('Incoming message [%s]' % message)
        user = ""
        if message.user:
            user = message.user.name
        if message.is_text():
            msg = Message(message.body)
            msg.setFrom(Identifier(node = user))
            self.callback_message(self.conn, msg)

    def error_callback(self, error):
        logging.error("Stream STOPPED due to ERROR: %s" % error)
        self.exit_lock.acquire()
        self.exit_lock.notify()
        self.exit_lock.release()

    def join_room(self, room, username=None, password=None):
        self.conn.join_room(room, self.msg_callback, self.error_callback)

    def build_message(self, text):
        """Builds an xhtml message without attributes.
        If input is not valid xhtml-im fallback to normal."""
        try:
            node = XML2Node(text)
            # logging.debug('This message is XML : %s' % text)
            text_plain = xhtml2txt(text)
            logging.debug('Plain Text translation from XHTML-IM:\n%s' % text_plain)
            message = Message(body=text_plain)
            # message.addChild(node = node) TODO see if campfire supports that
        except ExpatError as ee:
            if text.strip(): # avoids keep alive pollution
                logging.debug('Could not parse [%s] as XHTML-IM, assume pure text Parsing error = [%s]' % (text, ee))
            message = Message(body=text)
        return message
