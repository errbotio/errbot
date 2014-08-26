import logging
import sys
from time import sleep
from os.path import exists, join

from errbot.errBot import ErrBot
import config
from errbot.backends.base import Message, Connection, Identifier, Presence
from errbot.backends.base import ONLINE, OFFLINE, AWAY, DND
from errbot.backends.base import build_message, build_text_html_message_pair

try:
    from tox import Tox
except ImportError:
    logging.exception("Could not start the tox")
    logging.fatal("""
    If you intend to use the Tox backend please install tox:
    pip install PyTox
    """)
    sys.exit(-1)

try:
    from config import TOX_BOOTSTRAP_SERVER
except ImportError:
    logging.fatal("""
    You need to provide a server to bootstrap from in config.TOX_BOOTSTRAP_SERVER.
    for example :
    TOX_BOOTSTRAP_SERVER = ["54.199.139.199", 33445, "7F9C31FE850E97CEFD4C4591DF93FC757C7C12549DDD55F8EEAECC34FE76C029"]

    You can find currently active public ones on :
    https://wiki.tox.im/Nodes """)
    sys.exit(-1)

# Backend notes
#
# TOX mapping to Err Identifier :
# TOX friend number -> node
# TOX name -> resource


TOX_STATEFILE = join(config.BOT_DATA_DIR, 'tox.state')
TOX_MAX_MESS_LENGTH = 1368

NOT_ADMIN = "You are not recognized as an administrator of this bot"

TOX_TO_ERR_STATUS = {
        Tox.USERSTATUS_NONE: ONLINE,
        Tox.USERSTATUS_AWAY: AWAY,
        Tox.USERSTATUS_BUSY: DND,
        }

TOX_GROUP_TO_ERR_STATUS = {
        Tox.CHAT_CHANGE_PEER_ADD: ONLINE,
        Tox.CHAT_CHANGE_PEER_DEL: AWAY,
        Tox.CHAT_CHANGE_PEER_NAME: None,
        }


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
        self.bootstrap_from_address(*TOX_BOOTSTRAP_SERVER)

    def send_message(self, mess):
        body = mess.getBody()
        number = int(mess.getTo().getNode())
        subparts = [body[i:i+TOX_MAX_MESS_LENGTH] for i in range(0, len(body), TOX_MAX_MESS_LENGTH)]
        if mess.getType() == 'groupchat':
            logging.debug('TOX: sending to group number %i', number)
            for subpart in subparts:
                super(ToxConnection, self).group_message_send(number, subpart)
                sleep(0.5)  # antiflood
        else:
            logging.debug('TOX: sending to friend number %i', number)
            for subpart in subparts:
                # yup this is an horrible clash on names !
                super(ToxConnection, self).send_message(number, subpart)
                sleep(0.5)  # antiflood

    def on_friend_request(self, friend_pk, message):
        logging.info('TOX: Friend request from %s: %s' % (friend_pk, message))
        self.add_friend_norequest(friend_pk)

    def on_group_invite(self, friend_number, group_pk):
        logging.info('TOX: Group invite from %s : %s' % (self.get_name(friend_number), group_pk))

        if not self.callback.is_admin(friend_number):
            super(ToxConnection, self).send_message(friend_number, NOT_ADMIN)
            return
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
    
    def on_group_namelist_change(self, group_number, friend_group_number, change):
        logging.debug("TOX: user %s changed state in group %s" % (friend_group_number, group_number))
        newstatus = TOX_GROUP_TO_ERR_STATUS[change]
        if newstatus:
            chatroom = Identifier(node=str(group_number), resource=str(friend_group_number))
            pres = Presence(nick=self.group_peername(group_number, friend_group_number),
                            status = newstatus,
                            chatroom = chatroom)
            self.callback.callback_presence(self, pres)

    def on_user_status(self, friend_number, kind):
        logging.debug("TOX: user %s changed state", friend_number)
        pres = Presence(identifier=Identifier(node=str(friend_number), resource=self.get_name(friend_number)), 
                        status=TOX_TO_ERR_STATUS[kind])
        self.callback.callback_presence(self, pres)
   

    def on_status_message(self, friend_number, message):
        pres = Presence(identifier=Identifier(node=str(friend_number), resource=self.get_name(friend_number)), 
                        message=message)
        self.callback.callback_presence(self, pres)
 
    def on_connection_status(self, friend_number, status):
        logging.debug("TOX: user %s changed connection status", friend_number)
        pres = Presence(identifier=Identifier(node=str(friend_number), resource=self.get_name(friend_number)), 
                        status=ONLINE if status else OFFLINE)
        self.callback.callback_presence(self, pres)
 

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
        self.jid = Identifier(str(self.conn.get_address()), resource=username)

    def is_admin(self, friend_number):
        pk = self.conn.get_client_id(int(friend_number))
        logging.debug("Check if %s is admin" % pk)
        return any(pka.startswith(pk) for pka in config.BOT_ADMINS)

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

    def build_message(self, text):
        return build_message(text, Message)

    def build_reply(self, mess, text=None, private=False):
        # Tox doesn't support private message in chatrooms
        return super(ToxBackend, self).build_reply(mess, text, False)

    @property
    def mode(self):
        return 'tox'
