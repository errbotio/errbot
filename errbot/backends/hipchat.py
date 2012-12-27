import json
import logging
from urllib import urlencode

from urllib2 import urlopen, Request
from config import CHATROOM_FN
from errbot.backends.xmpp import XMPPBackend, XMPPConnection
from errbot.backends.base import build_message
from errbot.utils import utf8, REMOVE_EOL
import re

from sleekxmpp import JID, Message
from sleekxmpp.xmlstream import ElementBase

# Parses the hipchat element like : "<x xmlns='http://hipchat.com'><sender>15585_60268@chat.hipchat.com</sender></x>"

from sleekxmpp.plugins.base import base_plugin, register_plugin
from sleekxmpp.xmlstream import register_stanza_plugin


class HipchatMUCSender(ElementBase):
    name = 'x'
    namespace = 'http://hipchat.com'
    plugin_attrib = 'sender'
    interfaces = {'sender'}
    sub_interfaces = interfaces

class HipchatPlugin(base_plugin):
    name = 'hipchat'
    dependencies = {'xep_0045'}
    description = "Hipchat compatibility"

    def plugin_init(self):
        register_stanza_plugin(Message, HipchatMUCSender)


register_plugin(HipchatPlugin)

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


class HipchatClient(XMPPConnection):
    def __init__(self, *args, **kwargs):
        self.token = kwargs.pop('token')
        self.debug = kwargs.pop('debug')
        super(HipchatClient, self).__init__(*args, **kwargs)
        self.client.register_plugin('hipchat', module=self.__module__)

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
            super(HipchatClient, self).send_message(mess)

# It is just a different mode for the moment
class HipchatBackend(XMPPBackend):
    def __init__(self, username, password, token=None):
        self.api_token = token
        self.password = password
        super(HipchatBackend, self).__init__(username, password)

    def create_connection(self):
        return HipchatClient(self.jid, password=self.password, debug=[], token=self.api_token)

    @property
    def mode(self):
        return 'hipchat'
