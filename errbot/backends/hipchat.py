import json
import logging
from urllib import urlencode
from pyexpat import ExpatError
from xmpp.client import DBG_CLIENT
from xmpp.simplexml import XML2Node
from xmpp.protocol import Message
from errbot.backends.jabber import JabberBot
from urllib2 import urlopen, Request
from xmpp import Client
from config import CHATROOM_FN
from errbot.utils import xhtml2hipchat, utf8, xhtml2txt


HIPCHAT_MESSAGE_URL = 'https://api.hipchat.com/v1/rooms/message'


class HipchatClient(Client):
    def __init__(self, *args, **kwargs):
        self.token = kwargs.pop('token')
        self.Namespace, self.DBG = 'jabber:client', DBG_CLIENT  # DAAAAAAAAAAH -> see the CommonClient class, it introspects it descendents to determine that
        Client.__init__(self, *args, **kwargs)

    def send_api_message(self, room_id, fr, message, message_format='html'):
        base = {'format': 'json', 'auth_token': self.token}
        red_data = {'room_id': room_id, 'from': fr, 'message': utf8(message), 'message_format': message_format}
        req = Request(url=HIPCHAT_MESSAGE_URL + '?' + urlencode(base), data=urlencode(red_data))
        return json.load(urlopen(req))

    def send_message(self, mess):
        if self.token and mess.name == 'message' and mess.getType() == 'groupchat' and mess.getTag('html'):
            logging.debug('Message intercepted for Hipchat API')
            content = u''.join((unicode(child) for child in mess.getTag('html').getTag('body').getChildren()))
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

    def build_message(self, text):
        """Builds an xhtml message without attributes.
        If input is not valid xhtml-im fallback to normal."""
        message = None  # keeps the compiler happy
        try:
            text = utf8(text)
            XML2Node(text)  # test if is it xml
            # yes, ok epurate it for hipchat
            hipchat_html = xhtml2hipchat(text)
            try:
                node = XML2Node(hipchat_html)
                message = Message(body=xhtml2txt(text))
                message.addChild(node=node)
            except ExpatError as ee:
                logging.error('Error translating to hipchat [%s] Parsing error = [%s]' % (hipchat_html, ee))
        except ExpatError as ee:
            if text.strip():  # avoids keep alive pollution
                logging.debug('Determined that [%s] is not XHTML-IM (%s)' % (text, ee))
            message = Message(body=text)
        return message

    @property
    def mode(self):
        return 'hipchat'
