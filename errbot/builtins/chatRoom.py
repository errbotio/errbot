import logging
import xmpp
from errbot import BotPlugin
from errbot.utils import get_jid_from_message
from errbot.version import VERSION
from errbot.holder import bot

__author__ = 'gbin'
from config import CHATROOM_PRESENCE, CHATROOM_FN, CHATROOM_RELAY, REVERSE_CHATROOM_RELAY


class ChatRoom(BotPlugin):
    min_err_version = VERSION  # don't copy paste that for your plugin, it is just because it is a bundled plugin !
    max_err_version = VERSION

    connected = False

    def callback_connect(self):
        logging.info('Callback_connect')
        if not self.connected:
            self.connected = True
            for room in CHATROOM_PRESENCE:
                logging.info('Join room ' + unicode(room))
                if isinstance(room, basestring):
                    self.join_room(room, CHATROOM_FN)
                else:
                    self.join_room(room[0], password=room[1])

    def deactivate(self):
        self.connected = False
        super(ChatRoom, self).deactivate()

    def callback_message(self, conn, mess):
        if bot.mode != 'campfire':  # no relay support in campfire
            try:
                mess_type = mess.getType()
                if mess_type == 'chat':
                    username = get_jid_from_message(mess)
                    if username in CHATROOM_RELAY:
                        logging.debug('Message to relay from %s.' % username)
                        body = mess.getBody()
                        rooms = CHATROOM_RELAY[username]
                        for room in rooms:
                            self.send(room, body, message_type='groupchat')
                elif mess_type == 'groupchat':
                    fr = mess.getFrom()
                    chat_room = fr.node + '@' + fr.domain if fr.domain else fr.node  # some backends has no domain notion
                    if chat_room in REVERSE_CHATROOM_RELAY:
                        users_to_relay_to = REVERSE_CHATROOM_RELAY[chat_room]
                        logging.debug('Message to relay to %s.' % users_to_relay_to)
                        body = '[%s] %s' % (fr.resource, mess.getBody())
                        for user in users_to_relay_to:
                            self.send(user, body, message_type='chat')
            except Exception as e:
                logging.exception('crashed in callback_message %s' % e)
