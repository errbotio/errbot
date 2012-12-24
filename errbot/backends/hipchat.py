import json
import logging
from urllib import urlencode
from xmpp.client import DBG_CLIENT
from xmpp.protocol import Message
from errbot.backends.jabber import JabberBot
from urllib2 import urlopen, Request
from xmpp import Client
from config import CHATROOM_FN
from errbot.backends.base import build_message
from errbot.utils import utf8, REMOVE_EOL
import re

HIPCHAT_MESSAGE_URL = 'https://api.hipchat.com/v1/rooms/message'

HIPCHAT_FORCE_PRE = re.compile(r'<body>', re.I)
HIPCHAT_FORCE_SLASH_PRE = re.compile(r'</body>', re.I)
HIPCHAT_EOLS = re.compile(r'</p>|</li>', re.I)
HIPCHAT_BOLS = re.compile(r'<p [^>]+>|<li [^>]+>', re.I)


def xhtml2hipchat(xhtml):
    # Hipchat has a really limited html support
    retarded_hipchat_html_plain = REMOVE_EOL.sub('', xhtml)  # Ignore formatting
    retarded_hipchat_html_plain = HIPCHAT_EOLS.sub('<br/>', retarded_hipchat_html_plain)  # readd the \n where they probably fit best
    retarded_hipchat_html_plain = HIPCHAT_BOLS.sub('', retarded_hipchat_html_plain)  # zap every tag left
    retarded_hipchat_html_plain = HIPCHAT_FORCE_PRE.sub('<body><pre>', retarded_hipchat_html_plain)  # fixor pre
    retarded_hipchat_html_plain = HIPCHAT_FORCE_SLASH_PRE.sub('</pre></body>', retarded_hipchat_html_plain)  # fixor /pre
    return retarded_hipchat_html_plain


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
        return build_message(text, Message, xhtml2hipchat)

    @property
    def mode(self):
        return 'hipchat'
