import logging
import sys
from time import sleep
from os.path import exists, join

from errbot.errBot import ErrBot
from config import BOT_DATA_DIR
from errbot.backends.base import Message, Connection, Identifier
from errbot.backends.base import Message, build_message, build_text_html_message_pair

try:
    from tox import Tox
except ImportError:
    logging.exception("Could not start the tox")
    logging.fatal("""
    If you intend to use the Tox backend please install tox:
    pip install PyTox
    """)
    sys.exit(-1)

# TODO load that from a bootstrap address or a config
SERVER = ["54.199.139.199", 33445, "7F9C31FE850E97CEFD4C4591DF93FC757C7C12549DDD55F8EEAECC34FE76C029"]

# Tox mapping to Err Identifier :

# TOX id -> node
# TOX name -> resource
# as the id is the real identifier


TOX_STATEFILE = join(BOT_DATA_DIR, 'tox.state')

class ToxConnection(Tox, Connection):
    def __init__(self, callback, name):
        super(ToxConnection, self).__init__()
        self.callback = callback
        if exists(TOX_STATEFILE):
            self.load_from_file(TOX_STATEFILE)
        self.set_name(name)

        logging.info('TOX: ID %s' % self.get_address())

    rooms = {}  # keep track of joined room so we can send messages directly to them

    def connect(self):
        logging.info('TOX: connecting...')
        self.bootstrap_from_address(SERVER[0], SERVER[1], SERVER[2])

    def send_message(self, mess):
        body = mess.getBody()
        number = int(mess.getTo().getNode())
        if mess.getType() == 'groupchat':
           logging.debug('TOX: sending to group number %i', number)
           super(ToxConnection, self).group_message_send(number, body)
        else:
           logging.debug('TOX: sending to friend number %i', number)
           # yup this is an horrible clash on names !
           super(ToxConnection, self).send_message(number, body)
    
    def on_friend_request(self, friend_pk, message):
        logging.info('TOX: Friend request from %s: %s' % (friend_pk, message))
        self.add_friend_norequest(friend_pk)
    
    def on_group_invite(self, friend_number, group_pk):
        logging.info('TOX: Group invite from %s : %s' % (self.get_name(friend_number), group_pk))

        # FIXME: block groups not from the admin users
        self.join_groupchat(friend_number, group_pk)

    def on_friend_message(self, friend_number, message):
        name = self.get_name(friend_number)
        # friendId is just a local ordinal as int
        friend = Identifier(node=str(friend_number), resource=name)
        logging.debug('TOX: %s: %s' % (name, message))
        msg = Message(message)
        msg.setFrom(friend)
        msg.setTo(self.callback.jid)
        self.callback.callback_message(self, msg)
    
    def on_group_message(self, group_number, friend_group_number, message):
        logging.debug('TOX: Group-%i User-%i: %s' % (group_number, friend_group_number, message))
        fr = Identifier(node=str(group_number), resource=str(friend_group_number))
        msg = Message(message, typ='groupchat')
        msg.setFrom(fr)
        msg.setTo(self.callback.jid)
        logging.debug('TOX: callback with type = %s' % msg.getType())
        self.callback.callback_message(self, msg)

class ToxBackend(ErrBot):

    def __init__(self, username):
        super(ToxBackend, self).__init__()
        self.conn = ToxConnection(self, username)
        self.jid = Identifier(str(self.conn.get_address()), resource = username)

    def serve_forever(self):
        checked = False
 
        try:
            while True:
                status = self.conn.isconnected()

                if not checked and status:
                    logging.info('TOX: Connected to DHT.')
                    checked = True
                    self.connect_callback()  # notify that the connection occured

                if checked and not status:
                    logging.info('TOX: Disconnected from DHT.')
                    self.conn.connect()
                    checked = False

                self.conn.do()
                sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.conn.save_to_file(TOX_STATEFILE)
            self.disconnect_callback()
            self.shutdown()

    def connect(self):
        if not self.conn.isconnected():
            self.conn.connect()
        return self.conn

    def error_callback(self, error, room):
        logging.error("Stream STOPPED due to ERROR: %s in room %s" % (error, room))

    def join_room(self, room, username=None, password=None):
        self.conn.join_room(room, self.msg_callback, self.error_callback)

    def build_message(self, text):
        return build_message(text, Message)

    def build_reply(self, mess, text=None, private=False):
        # Tox doesn't support private message in chatrooms
        return super(ToxBackend, self).build_reply(mess, text, False)

    @property
    def mode(self):
        return 'tox'
