# coding=utf-8
from datetime import timedelta
import unittest
from xmpp import Message
from errbot.utils import *

class TestUtils(unittest.TestCase):

    def test_formattimedelta(self):
        td = timedelta(0,60*60 + 13*60)
        self.assertEqual('1 hours and 13 minutes', format_timedelta(td))

    def test_drawbar(self):
        self.assertEqual(drawbar(5,10),u'[████████▒▒▒▒▒▒▒]')
        self.assertEqual(drawbar(0,10),u'[▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒]')
        self.assertEqual(drawbar(10,10),u'[███████████████]')

    def test_XMPP_participant_jid_from_MUC_message_hipchat(self):
        # Real message from Hipchat MUC
        msg_txt = """
                <message xmlns="jabber:client" to="24926_143886@chat.hipchat.com/HipchatBot" type="groupchat" from="24926_err@conf.hipchat.com/Guillaume BINET">
                   <body>test</body>
                   <x xmlns="http://hipchat.com"><sender>24926_143884@chat.hipchat.com</sender></x>
                </message>"""

        message = Message(node = msg_txt)
        self.assertEqual(str(get_jid_from_message(message)), "24926_143884@chat.hipchat.com")

    def test_XMPP_participant_jid_from_MUC_message_normal(self):
        # Real message from Hipchat MUC
        msg_txt = """
                <message xmlns="jabber:client" to="24926_143886@chat.hipchat.com/HipchatBot" type="groupchat" from="24926_err@conf.hipchat.com/Guillaume BINET">
                   <body>test</body>
                </message>"""

        message = Message(node = msg_txt)

        self.assertEqual(str(message.getFrom()), "24926_err@conf.hipchat.com/Guillaume BINET")
        self.assertEqual(str(get_jid_from_message(message)), "24926_err@conf.hipchat.com/Guillaume BINET")
