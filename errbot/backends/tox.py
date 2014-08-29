import logging
import sys
from time import sleep
from os import pipe, fdopen
from os.path import exists, join
from io import BufferedRWPair
from errbot.errBot import ErrBot
import config
from errbot.backends.base import Message, Identifier, Presence, Stream
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

class ToxStreamer(BufferedRWPair):
    def __init__(self):
        r, w = pipe()
        self.r, self.w = fdopen(r, 'rb'), fdopen(w, 'wb')
        super(ToxStreamer, self).__init__(self.r, self.w)


class ToxConnection(Tox):
    def __init__(self, backend, name):
        super(ToxConnection, self).__init__()
        self.backend = backend
        self.incoming_streams = {}
        if exists(TOX_STATEFILE):
            self.load_from_file(TOX_STATEFILE)
        self.set_name(name)

        logging.info('TOX: ID %s' % self.get_address())

    rooms = {}  # keep track of joined room so we can send messages directly to them

    def connect(self):
        logging.info('TOX: connecting...')
        self.bootstrap_from_address(*TOX_BOOTSTRAP_SERVER)

    def friend_to_idd(self, friend_number):
        return Identifier(node=str(friend_number), resource=self.get_name(friend_number))

    def on_friend_request(self, friend_pk, message):
        logging.info('TOX: Friend request from %s: %s' % (friend_pk, message))
        self.add_friend_norequest(friend_pk)

    def on_group_invite(self, friend_number, group_pk):
        logging.info('TOX: Group invite from %s : %s' % (self.get_name(friend_number), group_pk))

        if not self.backend.is_admin(friend_number):
            super(ToxConnection, self).send_message(friend_number, NOT_ADMIN)
            return
        self.join_groupchat(friend_number, group_pk)

    def on_friend_message(self, friend_number, message):
        msg = Message(message)
        msg.frm = self.friend_to_idd(friend_number)
        logging.debug('TOX: %s: %s' % (msg.frm, message))
        msg.to = self.backend.jid
        self.backend.callback_message(msg)

    def on_group_namelist_change(self, group_number, friend_group_number, change):
        logging.debug("TOX: user %s changed state in group %s" % (friend_group_number, group_number))
        newstatus = TOX_GROUP_TO_ERR_STATUS[change]
        if newstatus:
            chatroom = Identifier(node=str(group_number), resource=str(friend_group_number))
            pres = Presence(nick=self.group_peername(group_number, friend_group_number),
                            status=newstatus,
                            chatroom=chatroom)
            self.backend.callback_presence(pres)

    def on_user_status(self, friend_number, kind):
        logging.debug("TOX: user %s changed state", friend_number)
        pres = Presence(identifier=self.friend_to_idd(friend_number),
                        status=TOX_TO_ERR_STATUS[kind])
        self.backend.callback_presence(pres)

    def on_status_message(self, friend_number, message):
        pres = Presence(identifier=self.friend_to_idd(friend_number),
                        message=message)
        self.backend.callback_presence(pres)

    def on_connection_status(self, friend_number, status):
        logging.debug("TOX: user %s changed connection status", friend_number)
        pres = Presence(identifier=self.friend_to_idd(friend_number),
                        status=ONLINE if status else OFFLINE)
        self.backend.callback_presence(pres)

    def on_group_message(self, group_number, friend_group_number, message):
        logging.debug('TOX: Group-%i User-%i: %s' % (group_number, friend_group_number, message))
        msg = Message(message, typ='groupchat')
        msg.frm = Identifier(node=str(group_number), resource=str(friend_group_number))
        msg.to = self.callback.jid
        logging.debug('TOX: callback with type = %s' % msg.type)
        self.backend.callback_message(msg)

    #### File transfers
    def on_file_send_request(self, friend_number, file_number, file_size, filename):
        logging.debug("TOX: incoming file transfer %s : %s", friend_number, filename)
        # make a pipe on which we will be able to write from tox
        pipe = ToxStreamer()
        # make the original stream with all the info
        stream = Stream(self.friend_to_idd(friend_number), pipe, filename, file_size)
        # store it for tracking purposes
        self.incoming_streams[(friend_number, file_number)] = (pipe, stream)
        # callback err so it will duplicate the stream and send it to all the plugins
        self.backend.callback_stream(stream)
        # always say ok, and kill it later if finally we don't want it
        self.file_send_control(friend_number, 1, file_number, Tox.FILECONTROL_ACCEPT)

    def on_file_data(self, friend_number, file_number, data):
        logging.debug("TOX: file data received : %s, size : %d", friend_number, len(data))
        pipe, _ = self.incoming_streams[(friend_number, file_number)]
        pipe.write(data)

    def on_file_control(self, friend_number, receive_send, file_number, control_type, data):
        logging.debug("TOX: file control received : %s, type : %d", friend_number, control_type)
        if receive_send == 0:
            pipe, stream = self.incoming_streams[(friend_number, file_number)]
            if control_type == Tox.FILECONTROL_KILL:
                stream.error("Other party killed the transfer")
                pipe.w.close()
            elif control_type == Tox.FILECONTROL_FINISHED:
                logging.debug("Other party signal the end of transfer on %s:%s"%(friend_number,file_number))
                pipe.flush()
                pipe.w.close()
            logging.debug("Receive file control %s", control_type)
        else:
            logging.warn("Sending file is not supported yet")

class ToxBackend(ErrBot):

    def __init__(self, username):
        super(ToxBackend, self).__init__()
        self.conn = ToxConnection(self, username)
        self.jid = Identifier(str(self.conn.get_address()), resource=username)

    def is_admin(self, friend_number):
        pk = self.conn.get_client_id(int(friend_number))
        logging.debug("Check if %s is admin" % pk)
        return any(pka.startswith(pk) for pka in config.BOT_ADMINS)

    def send_message(self, mess):
        super(ToxBackend, self).send_message(mess)
        body = mess.body
        number = int(mess.to.node)
        subparts = [body[i:i+TOX_MAX_MESS_LENGTH] for i in range(0, len(body), TOX_MAX_MESS_LENGTH)]
        if mess.type == 'groupchat':
            logging.debug('TOX: sending to group number %i', number)
            for subpart in subparts:
                self.conn.group_message_send(number, subpart)
                sleep(0.5)  # antiflood
        else:
            logging.debug('TOX: sending to friend number %i', number)
            for subpart in subparts:
                self.conn.send_message(number, subpart)
                sleep(0.5)  # antiflood

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
