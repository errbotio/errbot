# coding=utf-8
from datetime import timedelta
import unittest
from nose.tools import raises
from xmpp import Message
from errbot.utils import *
from errbot.storage import StoreMixin


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

        message = Message(node=msg_txt)
        self.assertEqual(str(get_jid_from_message(message)), "24926_143884@chat.hipchat.com")

    def test_XMPP_participant_jid_from_MUC_message_normal(self):
        # Real message from Hipchat MUC
        msg_txt = """
                <message xmlns="jabber:client" to="24926_143886@chat.hipchat.com/HipchatBot" type="groupchat" from="24926_err@conf.hipchat.com/Guillaume BINET">
                   <body>test</body>
                </message>"""

        message = Message(node=msg_txt)

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
