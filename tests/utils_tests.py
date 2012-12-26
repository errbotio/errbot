# coding=utf-8
from datetime import timedelta
import unittest
from nose.tools import raises
from xmpp import Message as XMPPMessage
from errbot.utils import *
from errbot.storage import StoreMixin
from errbot.backends.base import build_message
from errbot.backends.base import Message as BaseMessage


class TestUtils(unittest.TestCase):
    def test_formattimedelta(self):
        td = timedelta(0, 60 * 60 + 13 * 60)
        self.assertEqual('1 hours and 13 minutes', format_timedelta(td))

    def test_drawbar(self):
        self.assertEqual(drawbar(5, 10), u'[████████▒▒▒▒▒▒▒]')
        self.assertEqual(drawbar(0, 10), u'[▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒]')
        self.assertEqual(drawbar(10, 10), u'[███████████████]')

    def test_XMPP_participant_jid_from_MUC_message_hipchat(self):
        # Real message from Hipchat MUC
        msg_txt = """
                <message xmlns="jabber:client" to="24926_143886@chat.hipchat.com/HipchatBot" type="groupchat" from="24926_err@conf.hipchat.com/Guillaume BINET">
                   <body>test</body>
                   <x xmlns="http://hipchat.com"><sender>24926_143884@chat.hipchat.com</sender></x>
                </message>"""

        message = XMPPMessage(node=msg_txt)
        self.assertEqual(str(get_jid_from_message(message)), "24926_143884@chat.hipchat.com")

    def test_XMPP_participant_jid_from_MUC_message_normal(self):
        # Real message from Hipchat MUC
        msg_txt = """
                <message xmlns="jabber:client" to="24926_143886@chat.hipchat.com/HipchatBot" type="groupchat" from="24926_err@conf.hipchat.com/Guillaume BINET">
                   <body>test</body>
                </message>"""

        message = XMPPMessage(node=msg_txt)

        self.assertEqual(str(message.getFrom()), "24926_err@conf.hipchat.com/Guillaume BINET")
        self.assertEqual(str(get_jid_from_message(message)), "24926_err@conf.hipchat.com/Guillaume BINET")

    def test_storage(self):
        class MyPersistentClass(StoreMixin):
            pass

        from config import BOT_DATA_DIR

        persistent_object = MyPersistentClass()
        persistent_object.open_storage(BOT_DATA_DIR + os.path.sep + 'test.db')
        persistent_object['tést'] = 'à value'
        self.assertEquals(persistent_object['tést'], 'à value')
        self.assertIn('tést', persistent_object)
        del persistent_object['tést']
        self.assertNotIn('tést', persistent_object)
        self.assertEquals(len(persistent_object), 0)

    @raises(SystemExit)
    def test_pid(self):
        from platform import system
        from config import BOT_DATA_DIR

        if system() != 'Windows':
            pid_path = BOT_DATA_DIR + os.path.sep + 'err_test.pid'

            from errbot.pid import PidFile

            pidfile1 = PidFile(pid_path)
            pidfile2 = PidFile(pid_path)

            with pidfile1:
                logging.debug('ok locked the pid')
                with pidfile2:
                    logging.fatal('Should never execute')

    def test_unicode_xhtml(self):
        txt = u"""<!-- look here to see what is supported : http://xmpp.org/extensions/xep-0071.html -->
        <html xmlns='http://jabber.org/protocol/xhtml-im'>
        <body>
        <p style='margin-top: 0; margin-bottom: 0; font-weight:bold'>Interpreted your query as ts:[63491946525039405 TO 63491946825039405]</p>
        <p style='margin-top: 0; margin-bottom: 0;'>2012-12-24 11:50:12 frigg : VERSION</p>
        <p style='margin-top: 0; margin-bottom: 0;'>2012-12-24 11:50:25 #err : !translate he en מחשב</p>
        <p style='margin-top: 0; margin-bottom: 0;'>2012-12-24 11:51:01 gbin : !echo é</p>
        <p style='margin-top: 0; margin-bottom: 0;'>2012-12-24 11:52:58 24926_143884 : !echo へようこそ </p>
        <p style='margin-top: 0; margin-bottom: 0;'>2012-12-24 11:53:26 24926_143884 : !status</p>
        <p style='margin-top: 0; margin-bottom: 0;'>2012-12-24 11:53:38 24926_143884 : !help TimeMachine</p>
        </body>
        </html>"""
        pure_expected_text = u'Interpreted your query as ts:[63491946525039405 TO 63491946825039405]\n' \
            u'        2012-12-24 11:50:12 frigg : *VERSION*\n        2012-12-24 11:50:25 #err : !translate he en \u05de\u05d7\u05e9\u05d1\n' \
            u'        2012-12-24 11:51:01 gbin : !echo \xe9\n        2012-12-24 11:52:58 24926_143884 : !echo \u3078\u3088\u3046\u3053\u305d \n' \
            u'        2012-12-24 11:53:26 24926_143884 : !status\n        2012-12-24 11:53:38 24926_143884 : !help TimeMachine'
        expected_clean_unicode = u"""<html xmlns="http://jabber.org/protocol/xhtml-im">
        <body>
        <p style="margin-top: 0; margin-bottom: 0; font-weight:bold">Interpreted your query as ts:[63491946525039405 TO 63491946825039405]</p>
        <p style="margin-top: 0; margin-bottom: 0;">2012-12-24 11:50:12 frigg : *VERSION*</p>
        <p style="margin-top: 0; margin-bottom: 0;">2012-12-24 11:50:25 #err : !translate he en מחשב</p>
        <p style="margin-top: 0; margin-bottom: 0;">2012-12-24 11:51:01 gbin : !echo é</p>
        <p style="margin-top: 0; margin-bottom: 0;">2012-12-24 11:52:58 24926_143884 : !echo へようこそ </p>
        <p style="margin-top: 0; margin-bottom: 0;">2012-12-24 11:53:26 24926_143884 : !status</p>
        <p style="margin-top: 0; margin-bottom: 0;">2012-12-24 11:53:38 24926_143884 : !help TimeMachine</p>
        </body>
        </html>"""

        self.maxDiff = None
        msg1 = build_message(txt, XMPPMessage)
        self.assertEquals(msg1.getBody(), pure_expected_text)
        #self.assertEquals(msg1.getNode('html'), txt)

        msg2 = build_message(txt, BaseMessage)
        self.assertEquals(msg2.getBody(), pure_expected_text)
        self.assertEquals(msg2.getHTML(), expected_clean_unicode)

    def test_recurse_check_structure_valid(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string="Foobar", list=["Foo", "Bar", "Bas"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        recurse_check_structure(sample, to_check)

    @raises(ValidationException)
    def test_recurse_check_structure_missingitem(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True)
        recurse_check_structure(sample, to_check)

    @raises(ValidationException)
    def test_recurse_check_structure_extrasubitem(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string="Foobar", list=["Foo", "Bar", "Bas"], dict={'foo': "Bar", 'Bar': "Foo"}, none=None, true=True, false=False)
        recurse_check_structure(sample, to_check)

    @raises(ValidationException)
    def test_recurse_check_structure_missingsubitem(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string="Foobar", list=["Foo", "Bar", "Bas"], dict={}, none=None, true=True, false=False)
        recurse_check_structure(sample, to_check)

    @raises(ValidationException)
    def test_recurse_check_structure_wrongtype_1(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string=None, list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        recurse_check_structure(sample, to_check)

    @raises(ValidationException)
    def test_recurse_check_structure_wrongtype_2(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string="Foobar", list={'foo': "Bar"}, dict={'foo': "Bar"}, none=None, true=True, false=False)
        recurse_check_structure(sample, to_check)

    @raises(ValidationException)
    def test_recurse_check_structure_wrongtype_3(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string="Foobar", list=["Foo", "Bar"], dict=["Foo", "Bar"], none=None, true=True, false=False)
        recurse_check_structure(sample, to_check)
