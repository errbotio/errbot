import logging
import sys

try:
    import pyfire
except ImportError:
    logging.exception("Could not start the campfire backend")
    logging.error("""
    If you intend to use the campfire backend please install pyfire:
    pip install pyfire
    """)
    sys.exit(-1)

from pyexpat import ExpatError
from xmpp.simplexml import XML2Node
from errbot.backends.base import Message, Connection
from errbot.errBot import ErrBot
from errbot.utils import xhtml2txt, utf8
from threading import Condition
from config import CHATROOM_PRESENCE


class CampfireConnection(Connection, pyfire.Campfire):
    rooms = {}  # keep track of joined room so we can send messages directly to them

    def send_message(self, mess):
        to_identity = mess.getTo()
        room_name = to_identity.getDomain()  # we only reply to rooms in reality in campfire
        room = self.rooms[room_name][0]
        room.speak(mess.getBody())  # Basic text support for the moment

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

        self.conn = None
        self.subdomain = subdomain
        self.username = username
        self.password = password
        self.ssl = ssl

    def serve_forever(self):
        self.exit_lock.acquire()
        self.connect()  # be sure we are "connected" before the first command
        self.connect_callback()  # notify that the connection occured
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
            if not CHATROOM_PRESENCE:
                raise Exception('Your bot needs to join at least one room, please set CHATROOM_PRESENCE in your config')
            self.conn = CampfireConnection(self.subdomain, self.username, self.password, self.ssl)
            self.jid = self.username + '@' + str(self.conn.get_room_by_name(CHATROOM_PRESENCE[0])) + '/' + self.username
            # put us by default in the first room
            # resource emulates the XMPP behavior in chatrooms
        return self.conn

    def build_message(self, text):
        return Message(text, typ='groupchat')  # it is always a groupchat in campfire

    def shutdown(self):
        super(CampfireBackend, self).shutdown()

    def msg_callback(self, message):
        logging.debug('Incoming message [%s]' % message)
        user = ""
        if message.user:
            user = message.user.name
        if message.is_text():
            msg = Message(message.body, typ='groupchat')  # it is always a groupchat in campfire
            msg.setFrom(user + '@' + message.room.get_data()['name'] + '/' + user)
            msg.setTo(self.jid)  # assume it is for me
            self.callback_message(self.conn, msg)

    def error_callback(self, error, room):
        logging.error("Stream STOPPED due to ERROR: %s in room %s" % (error, room))
        self.exit_lock.acquire()
        self.exit_lock.notify()
        self.exit_lock.release()

    def join_room(self, room, username=None, password=None):
        self.conn.join_room(room, self.msg_callback, self.error_callback)

    def build_message(self, text):
        try:
            node = XML2Node(utf8(text))
            text_plain = xhtml2txt(text)
            logging.debug('Plain Text translation from XHTML-IM:\n%s' % text_plain)
            message = Message(body=utf8(text_plain))
        except ExpatError as ee:
            if text.strip():  # avoids keep alive pollution
                logging.debug('Determined that [%s] is not XHTML-IM (%s)' % (text, ee))
            message = Message(body=utf8(text))
        return message

    def send_simple_reply(self, mess, text, private=False):
        """Total hack to avoid stripping of rooms"""
        self.send_message(self.build_reply(mess, text, True))

    @property
    def mode(self):
        return 'campfire'
