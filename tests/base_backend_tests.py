# coding=utf-8
import unittest
from errbot.backends.base import Identifier, Backend, Message, build_text_html_message_pair


class TestBase(unittest.TestCase):
    def test_identifier_parsing(self):
        id1 = Identifier(jid="gbin@gootz.net/toto")
        self.assertEqual(id1.getNode(), "gbin")
        self.assertEqual(id1.getDomain(), "gootz.net")
        self.assertEqual(id1.getResource(), "toto")

        id2 = Identifier(jid="gbin@gootz.net")
        self.assertEqual(id2.getNode(), "gbin")
        self.assertEqual(id2.getDomain(), "gootz.net")
        try:
            self.assertIsNone(id2.getResource())
        except AttributeError:
            # assertIsNone didn't exist until python 3.1, don't fail if we're operating earlier than that
            pass

    def test_identifier_matching(self):
        id1 = Identifier(jid="gbin@gootz.net/toto")
        id2 = Identifier(jid="gbin@gootz.net/titi")
        id3 = Identifier(jid="gbin@giitz.net/titi")
        self.assertTrue(id1.bareMatch(id2))
        self.assertFalse(id2.bareMatch(id3))

    def test_identifier_stripping(self):
        id1 = Identifier(jid="gbin@gootz.net/toto")
        self.assertEqual(id1.getStripped(), "gbin@gootz.net")

    def test_identifier_str_rep(self):
        self.assertEqual(str(Identifier(jid="gbin@gootz.net/toto")), "gbin@gootz.net/toto")
        self.assertEqual(str(Identifier(jid="gbin@gootz.net")), "gbin@gootz.net")

    def test_xhtmlparsing_and_textify(self):
        text_plain, node = build_text_html_message_pair("<html><body>Message</body></html>")
        self.assertEqual(text_plain, "Message")
        self.assertEqual(node.name, "html")
        self.assertEqual(node.getChildren()[0].name, "body")
        self.assertEqual(node.getChildren()[0].data, [u'Message'])

    def test_identifier_double_at_parsing(self):
        id1 = Identifier(jid="gbin@titi.net@gootz.net/toto")
        self.assertEqual(id1.getNode(), "gbin@titi.net")
        self.assertEqual(id1.getDomain(), "gootz.net")
        self.assertEqual(id1.getResource(), "toto")

    def test_buildreply(self):
        class DummyBackend(Backend):
            def build_message(self, text):
                return Message(text)

        be = DummyBackend()
        be.jid = Identifier("bot@here.com/metal")
        m = be.build_message("Content")
        m.setFrom("from@fromdomain.net/fromresource")
        m.setTo("to@todomain.net/toresource")

        resp = be.build_reply(m, "Response")
        self.assertEqual(str(resp.getTo()), "from@fromdomain.net")
        self.assertEqual(str(resp.getFrom()), "bot@here.com/metal")
        self.assertEqual(str(resp.getBody()), "Response")
