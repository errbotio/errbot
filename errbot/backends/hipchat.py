import httplib
import json
import logging
from urllib import urlencode
from xmpp.client import DBG_CLIENT
from errbot.backends.jabber import JabberBot
from urllib2 import urlopen, Request
from xmpp import Client
from config import CHATROOM_FN

HIPCHAT_MESSAGE_URL = 'https://api.hipchat.com/v1/rooms/message'

class HipchatClient(Client):
    def __init__(self, *args, **kwargs):
        self.token = kwargs.pop('token')
        self.Namespace, self.DBG = 'jabber:client', DBG_CLIENT # DAAAAAAAAAAH -> see the CommonClient class, it introspects it descendents to determine that
        Client.__init__(self, *args, **kwargs)

    def send_api_message(self, room_id, fr, message, message_format='html'):
        base = {'format': 'json', 'auth_token': self.token}
        red_data = {'room_id': room_id, 'from': fr, 'message': message, 'message_format': message_format}
        req = Request(url=HIPCHAT_MESSAGE_URL + '?' + urlencode(base), data=urlencode(red_data))
        return json.load(urlopen(req))


    def send_message(self, mess):
        if self.token and mess.name == 'message' and mess.getTag('html'):
            logging.debug('Message intercepted for Hipchat API')
            content = ''.join((str(child) for child in mess.getTag('html').getTag('body').getChildren()))
            room_jid = mess.getTo()
            self.send_api_message(room_jid.getNode().split('_')[1], CHATROOM_FN, content)
        else:
            self.send(mess)


# It is just a different mode for the moment
class HipchatBot(JabberBot):
    def __init__(self, username, password, token=None):
        super(HipchatBot, self).__init__(username, password)
        self.api_token = token

    def create_connection(self):
        return HipchatClient(self.jid.getDomain(), debug=[], token=self.api_token)

    @property
    def mode(self):
        return 'hipchat'

