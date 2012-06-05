import logging
import xmpp
from botplugin import BotPlugin
from utils import get_jid_from_message
from threading import Timer
__author__ = 'gbin'
from config import CHATROOM_PRESENCE, CHATROOM_FN, CHATROOM_RELAY, HIPCHAT_MODE

class ChatRoom(BotPlugin):
    connected = False
    def keep_alive(self):
        logging.debug('Keep alive sent')
        if HIPCHAT_MODE:
            self.send('nobody', ' ', message_type='groupchat') # hack from hipchat itself
        else:
            pres = xmpp.Presence()
            self.connect().send(pres)

        self.t = Timer(60.0, self.keep_alive)
        self.t.setDaemon(True) # so it is not locking on exit
        self.t.start()

    def callback_connect(self):
        logging.info('Callback_connect')
        if not self.connected:
            self.connected = True
            for room in CHATROOM_PRESENCE:
                logging.info('Join room ' + room)
                self.join_room(room, CHATROOM_FN)

            logging.info('Start keep alive')
            self.keep_alive()

    def callback_message(self, conn, mess):
        #if mess.getBody():
        #    logging.debug(u'Received message %s' % mess.getBody())
        if mess.getType() in ('groupchat', 'chat'):
            try:
                username = get_jid_from_message(mess)
                if username in CHATROOM_RELAY:
                    logging.debug('Message to relay from %s.' % username)
                    body = mess.getBody()
                    rooms = CHATROOM_RELAY[username]
                    for room in rooms:
                        self.send(room, body, message_type='groupchat')
            except Exception, e:
                logging.exception('crashed in callback_message %s' % e)
