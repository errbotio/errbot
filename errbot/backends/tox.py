import codecs
import logging
import sys
from time import sleep
import os
from os.path import exists, join
import io
from errbot.backends import base
from errbot.errBot import ErrBot
from errbot.backends.base import Message, Presence, Stream, MUCRoom
from errbot.backends.base import ONLINE, OFFLINE, AWAY, DND
from errbot.backends.base import build_message
from errbot.backends.base import STREAM_TRANSFER_IN_PROGRESS
from threading import Thread

log = logging.getLogger(__name__)

try:
    from pytox import Tox, OperationFailedError
except ImportError:
    log.exception("Could not start the tox")
    log.fatal("""
    If you intend to use the Tox backend please install tox:
    pip install PyTox
    """)
    sys.exit(-1)


TOX_MAX_MESS_LENGTH = 1368

NOT_ADMIN = "You are not recognized as an administrator of this bot"

TOX_TO_ERR_STATUS = {
    Tox.USER_STATUS_NONE: ONLINE,
    Tox.USER_STATUS_AWAY: AWAY,
    Tox.USER_STATUS_BUSY: DND,
}

TOX_GROUP_TO_ERR_STATUS = {
    Tox.CHAT_CHANGE_PEER_ADD: ONLINE,
    Tox.CHAT_CHANGE_PEER_DEL: AWAY,
    Tox.CHAT_CHANGE_PEER_NAME: None,
}


class ToxIdentifier(object):
    def __init__(self, client_id=None, group_number=None, friend_group_number=None, username=None):
        self._client_id = client_id
        self._group_number = group_number
        self._friend_group_number = friend_group_number
        self._username = username

    @property
    def person(self):
        return self._username

    @property
    def client(self):
        return None

    @property
    def nick(self):
        return self._username

    @property
    def fullname(self):
        return None


class ToxStreamer(io.BufferedRWPair):
    def __init__(self):
        r, w = os.pipe()
        self.r, self.w = io.open(r, 'rb'), io.open(w, 'wb')
        super(ToxStreamer, self).__init__(self.r, self.w)


class ToxConnection(Tox):
    def __init__(self, backend, name):
        super(ToxConnection, self).__init__()
        self.backend = backend
        self.incoming_streams = {}
        self.outgoing_streams = {}
        state_file = join(backend.bot_config.BOT_DATA_DIR, 'tox.state')
        if exists(state_file):
            self.load_from_file(state_file)
        self.set_name(name)
        self.rooms = set()  # keep track of joined room

        log.info('TOX: ID %s' % self.get_address())

    def connect(self, bootstrap_servers):
        log.info('TOX: connecting...')
        self.bootstrap_from_address(*bootstrap_servers)

    def friend_to_idd(self, friend_number):
        return ToxIdentifier(client_id=self.get_client_id(friend_number))

    def idd_to_friend(self, identifier, autoinvite=True, autoinvite_message='I am just a bot.'):
        """
        Returns the Tox friend number from the roster.

        :exception ValueError if the identifier is not a Tox one.
        :param identifier: an err identifier
        :param autoinvite: set to True if you want to invite this identifier if it is not in your roster.
        :return: the tox friend number from the roster, None if it could not be found.
        """
        if len(identifier.userid) > 76 or len(identifier.userid) < 64:
            raise ValueError("%s is not a valid Tox Identifier.")
        try:
            return self.get_friend_id(identifier.userid)
        except OperationFailedError:
            if autoinvite:
                return self.add_friend(identifier.userid, autoinvite_message)
            return None

    def on_friend_request(self, friend_pk, message):
        log.info('TOX: Friend request from %s: %s' % (friend_pk, message))
        self.add_friend_norequest(friend_pk)

    def on_group_invite(self, friend_number, type_, data):
        data_hex = codecs.encode(data, 'hex_codec')
        log.info('TOX: Group invite [type %s] from %s : %s' % (type_, self.get_name(friend_number), data_hex))
        if type_ == 1:
            super().send_message(friend_number, "Err tox backend doesn't support audio groupchat yet.")
            return
        if not self.backend.is_admin(friend_number):
            super().send_message(friend_number, NOT_ADMIN)
            return
        try:
            groupnumber = self.join_groupchat(friend_number, data)
            if groupnumber >= 0:
                self.rooms.add(TOXMUCRoom(self, groupnumber, bot=self.backend))
            else:
                log.error("Error joining room %s", data_hex)
        except OperationFailedError:
            log.exception("Error joining room %s", data_hex)

    def on_friend_message(self, friend_number, message):
        msg = Message(message)
        msg.frm = self.friend_to_idd(friend_number)
        log.debug('TOX: %s: %s' % (msg.frm, message))
        msg.to = self.backend.bot_identifier
        self.backend.callback_message(msg)

    def on_group_namelist_change(self, group_number, friend_group_number, change):
        log.debug("TOX: user %s changed state in group %s" % (friend_group_number, group_number))
        newstatus = TOX_GROUP_TO_ERR_STATUS[change]
        if newstatus:
            chatroom = ToxIdentifier(group_number=str(group_number), friend_group_number=str(friend_group_number))
            pres = Presence(nick=self.group_peername(group_number, friend_group_number),
                            status=newstatus,
                            chatroom=chatroom)
            self.backend.callback_presence(pres)

    def on_user_status(self, friend_number, kind):
        log.debug("TOX: user %s changed state", friend_number)
        pres = Presence(identifier=self.friend_to_idd(friend_number),
                        status=TOX_TO_ERR_STATUS[kind])
        self.backend.callback_presence(pres)

    def on_status_message(self, friend_number, message):
        pres = Presence(identifier=self.friend_to_idd(friend_number),
                        message=message)
        self.backend.callback_presence(pres)

    def on_connection_status(self, friend_number, status):
        log.debug("TOX: user %s changed connection status", friend_number)
        pres = Presence(identifier=self.friend_to_idd(friend_number),
                        status=ONLINE if status else OFFLINE)
        self.backend.callback_presence(pres)

    def on_group_message(self, group_number, friend_group_number, message):
        log.debug('TOX: Group-%i User-%i: %s' % (group_number, friend_group_number, message))
        msg = Message(message, type_='groupchat')
        msg.frm = ToxIdentifier(group_number=str(group_number), friend_group_number=str(friend_group_number))
        msg.to = self.backend.bot_identifier
        log.debug('TOX: callback with type = %s' % msg.type)
        self.backend.callback_message(msg)

    # File transfers
    def on_file_send_request(self, friend_number, file_number, file_size, filename):
        log.debug("TOX: incoming file transfer %s : %s", friend_number, filename)
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
        log.debug("TOX: file data received : %s, size : %d", friend_number, len(data))
        pipe, _ = self.incoming_streams[(friend_number, file_number)]
        pipe.write(data)

    def on_file_control(self, friend_number, receive_send, file_number, control_type, data):
        log.debug("TOX: file control received : %s, type : %d", friend_number, control_type)
        if receive_send == 0:
            pipe, stream = self.incoming_streams[(friend_number, file_number)]
            if control_type == Tox.FILECONTROL_KILL:
                stream.error("Other party killed the transfer")
                pipe.w.close()
            elif control_type == Tox.FILECONTROL_FINISHED:
                log.debug("Other party signal the end of transfer on %s:%s" % (friend_number, file_number))
                pipe.flush()
                pipe.w.close()
            log.debug("Receive file control %s", control_type)
        else:
            stream = self.outgoing_streams[(friend_number, file_number)]
            if control_type == Tox.FILECONTROL_ACCEPT:
                log.debug("TOX: file accepted by remote")
                Thread(target=self.send_stream, args=(friend_number, file_number)).start()
            elif control_type == Tox.FILECONTROL_KILL:
                stream.reject()
                stream.close()
            elif control_type == Tox.FILECONTROL_FINISHED:
                log.debug("TOX: cool other party signals the good reception")
                stream.success()
                stream.close()
            else:
                logging.warning("This control_type is not supported yet %s" % control_type)

    def send_stream(self, friend_number, file_number):
        stream = self.outgoing_streams[(friend_number, file_number)]
        try:
            stream.accept()
            chunk_size = self.file_data_size(friend_number)

            while True and stream.status == STREAM_TRANSFER_IN_PROGRESS:
                log.debug("TOX: read data")
                data = stream.read(chunk_size)
                if not data:
                    break
                log.debug("TOX: send %d bytes" % len(data))
                self.file_send_data(friend_number, file_number, data)
            log.debug("TOX: file transfert done")
            if stream.status == STREAM_TRANSFER_IN_PROGRESS:
                log.debug("TOX: send FILECONTROL_FINISHED")
                self.file_send_control(friend_number, 0, file_number, Tox.FILECONTROL_FINISHED)
        except Exception as e:
            log.exception("Error sending stream")
            stream.error(str(e))
            self.file_send_control(friend_number, 0, file_number, Tox.FILECONTROL_KILL)
        finally:
            stream.close()

    def send_stream_request(self, stream):
        friend_number = self.idd_to_friend(stream.identifier)
        log.debug("TOX: send file request %s %s %s",
                  friend_number,
                  stream.size if stream.size else -1,
                  stream.name)
        file_number = self.new_file_sender(friend_number, stream.size if stream.size else -1, stream.name)
        self.outgoing_streams[(friend_number, file_number)] = stream


class TOXMUCRoom(MUCRoom):
    def __init__(self, conn, group_number=None, bot=None):
        if group_number is not None:
            super().__init__(str(group_number), bot=bot)
        else:
            super().__init__(None, bot=bot)  # needed to properly initialize an identity.

        self.conn = conn

    @property
    def group_number(self):
        return int(self.node)

    def join(self, username=None, password=None):
        logging.warning("TOX: you need to be invited to be able to join a chatgroup.")

    def leave(self, reason=None):
        if reason:
            self.conn.group_message_send(self.group_number, "/me is leaving: " + reason)
        self.destroy()

    def create(self):
        if self.node:
            raise ValueError("Cannot create an already created chatgroup.")
        gid = self.conn.add_groupchat()
        if gid < 0:
            raise Exception("Error creating chatgroup")
        self.conn.rooms.add(self)
        self._node = str(gid)

    def destroy(self):
        if self.node is None:
            logging.warning("TOX: this chatgroup is already gone.")
            return
        self.conn.del_groupchat(self.group_number)
        self.conn.rooms.remove(self)
        self._node = None

    @property
    def exists(self):
        return self.node

    @property
    def joined(self):
        return self.node

    @property
    def topic(self):
        if self.joined:
            return self.conn.group_get_title(self.group_number)
        return "[Not Joined]"

    @topic.setter
    def topic(self, topic):
        if self.joined:
            self.conn.group_set_title(self.group_number, topic)

    @property
    def occupants(self):
        if self.joined:
            return [base.MUCOccupant(name) for name in self.conn.group_get_names(self.group_number)]
        return []

    def invite(self, *identifiers):
        if self.joined:
            for friend_id in identifiers:
                log.debug("Invite friend %i in group %i", int(friend_id), self.group_number)
                self.conn.invite_friend(int(friend_id), self.group_number)
        raise ValueError("This chatgroup is not joined, you cannot invite anybody.")

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        if self.joined:
            return "ChatRoom #%s: %s" % (self.node, self.topic)
        else:
            return "Unjoined Room"


class ToxBackend(ErrBot):
    def __init__(self, config):
        if not hasattr(config, 'TOX_BOOTSTRAP_SERVER'):
            log.fatal("""
            You need to provide a server to bootstrap from in config.TOX_BOOTSTRAP_SERVER.
            for example :
            TOX_BOOTSTRAP_SERVER = ["54.199.139.199", 33445,
                                    "7F9C31FE850E97CEFD4C4591DF93FC757C7C12549DDD55F8EEAECC34FE76C029"]

            You can find currently active public ones on :
            https://wiki.tox.im/Nodes """)
            sys.exit(-1)

        username = config.BOT_IDENTITY['username']
        super(ToxBackend, self).__init__(config)
        self.conn = ToxConnection(self, username)
        self.bot_identifier = ToxIdentifier(userid=str(self.conn.get_address()), username=username)

    def is_admin(self, friend_number):
        pk = self.conn.get_client_id(int(friend_number))
        log.debug("Check if %s is admin" % pk)
        return any(pka.startswith(pk) for pka in self.bot_config.BOT_ADMINS)

    def send_message(self, mess):
        super(ToxBackend, self).send_message(mess)
        body = mess.body

        subparts = [body[i:i + TOX_MAX_MESS_LENGTH] for i in range(0, len(body), TOX_MAX_MESS_LENGTH)]
        try:
            if mess.type == 'groupchat':
                number = int(mess.to.node)
                log.debug('TOX: sending to group number %i', number)
                for subpart in subparts:
                    self.conn.group_message_send(number, subpart)
                    sleep(0.5)  # antiflood
            else:
                number = self.conn.idd_to_friend(mess.to)
                log.debug('TOX: sending to friend number %i', number)
                for subpart in subparts:
                    self.conn.send_message(number, subpart)
                    sleep(0.5)  # antiflood
        except OperationFailedError as _:
            log.exception("TOX error.")

    def send_stream_request(self, identifier, fsource, name=None, size=None, stream_type=None):
        s = Stream(identifier, fsource, name, size, stream_type)
        self.conn.send_stream_request(s)
        return s

    def serve_forever(self):
        checked = False

        try:
            while True:
                status = self.conn.isconnected()

                if not checked and status:
                    log.info('TOX: Connected to DHT.')
                    checked = True
                    self.connect_callback()  # notify that the connection occured

                if checked and not status:
                    log.info('TOX: Disconnected from DHT.')
                    self.conn.connect(self.bot_config.TOX_BOOTSTRAP_SERVER)
                    checked = False

                self.conn.do()
                sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.conn.save_to_file(self.bot_config.TOX_STATEFILE)
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

    def rooms(self):
        return list(self.conn.rooms)

    def query_room(self, room):
        if room is None:
            return TOXMUCRoom(self.conn, bot=self)  # either it is a new room
        for gc in self.conn.rooms:  # or it must exist here.
            if gc.node == room:
                return gc
        return None

    def groupchat_reply_format(self):
        return '@{user} {reply}'
