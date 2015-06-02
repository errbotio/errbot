import logging
import sys

from errbot.backends.base import Message, build_message, Identifier
from errbot.errBot import ErrBot
from threading import Condition

log = logging.getLogger(__name__)

try:
    import pyfire
except ImportError:
    log.exception("Could not start the campfire backend")
    log.fatal("""
    If you intend to use the campfire backend please install pyfire:
    pip install pyfire
    """)
    sys.exit(-1)


class CampfireConnection(pyfire.Campfire):
    rooms = {}  # keep track of joined room so we can send messages directly to them

    def join_room(self, name, msg_callback, error_callback):
        room = self.get_room_by_name(name)
        room.join()
        stream = room.get_stream(error_callback=error_callback)
        stream.attach(msg_callback).start()
        self.rooms[name] = (room, stream)


ENCODING_INPUT = sys.stdin.encoding


class CampfireIdentifier(Identifier):
    def __init__(self, s):
        self._user = s   # it is just one room for the moment

    @property
    def user(self):
        return self._user


class CampfireBackend(ErrBot):
    exit_lock = Condition()

    def __init__(self, config):
        super(CampfireBackend, self).__init__(config)
        identity = config.BOT_IDENTITY
        self.conn = None
        self.subdomain = identity['subdomain']
        self.username = identity['username']
        self.password = identity['password']
        if not hasattr(config, 'CHATROOM_PRESENCE') or len(config['CHATROOM_PRESENCE']) < 1:
            raise Exception('Your bot needs to join at least one room, please set'
                            ' CHATROOM_PRESENCE with at least a room in your config')
        self.chatroom = config.CHATROOM_PRESENCE[0]
        self.room = None
        self.ssl = identity['ssl'] if 'ssl' in identity else True
        self.jid = None

    def send_message(self, mess):
        super(CampfireBackend, self).send_message(mess)
        self.room.speak(mess.body)  # Basic text support for the moment

    def serve_forever(self):
        self.exit_lock.acquire()
        self.connect()  # be sure we are "connected" before the first command
        self.connect_callback()  # notify that the connection occured
        try:
            log.info("Campfire connected.")
            self.exit_lock.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.exit_lock.release()
            self.disconnect_callback()
            self.shutdown()

    def connect(self):
        if not self.conn:
            self.conn = CampfireConnection(self.subdomain, self.username, self.password, self.ssl)
            self.jid = Identifier(self.username)
            self.room = self.conn.get_room_by_name(self.chatroom).name
            # put us by default in the first room
            # resource emulates the XMPP behavior in chatrooms
        return self.conn

    def build_message(self, text):
        return Message(text, type_='groupchat')  # it is always a groupchat in campfire

    def shutdown(self):
        super(CampfireBackend, self).shutdown()

    def msg_callback(self, message):
        log.debug('Incoming message [%s]' % message)
        user = ""
        if message.user:
            user = message.user.name
        if message.is_text():
            msg = Message(message.body, type_='groupchat')  # it is always a groupchat in campfire
            msg.frm = CampfireIdentifier(user)
            msg.to = self.jid  # assume it is for me
            self.callback_message(msg)

    def error_callback(self, error, room):
        log.error("Stream STOPPED due to ERROR: %s in room %s" % (error, room))
        self.exit_lock.acquire()
        self.exit_lock.notify()
        self.exit_lock.release()

    def join_room(self, room, username=None, password=None):
        self.conn.join_room(room, self.msg_callback, self.error_callback)

    def build_message(self, text):
        return build_message(text, Message)

    def build_identifier(self, strrep):
        return CampfireIdentifier(strrep)

    def send_simple_reply(self, mess, text, private=False):
        """Total hack to avoid stripping of rooms"""
        self.send_message(self.build_reply(mess, text, True))

    @property
    def mode(self):
        return 'campfire'

    def groupchat_reply_format(self):
        return '@{0} {1}'
