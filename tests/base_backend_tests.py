# coding=utf-8
import unittest
import os
from queue import Queue
from errbot.backends.base import Identifier, Backend, Message, build_text_html_message_pair
from errbot import botcmd, templating

class DummyBackend(Backend):
    outgoing_message_queue = Queue()
    jid = Identifier('err@localhost/err')

    def build_message(self, text):
        return Message(text)

    def send_message(self, mess):
        self.outgoing_message_queue.put(mess)

    def pop_message(self, timeout=3, block=True):
        return self.outgoing_message_queue.get(timeout=timeout, block=block)


class TestBase(unittest.TestCase):
    def setUp(self):
        self.dummy = DummyBackend()

        assets_path = os.path.dirname(__file__) + os.sep + "assets"
        template_path = [templating.make_templates_path(assets_path)]
        templating.env = templating.Environment(loader=templating.FileSystemLoader(template_path))

    def test_identifier_parsing(self):
        id1 = Identifier(jid="gbin@gootz.net/toto")
        self.assertEqual(id1.getNode(), "gbin")
        self.assertEqual(id1.getDomain(), "gootz.net")
        self.assertEqual(id1.getResource(), "toto")

        id2 = Identifier(jid="gbin@gootz.net")
        self.assertEqual(id2.getNode(), "gbin")
        self.assertEqual(id2.getDomain(), "gootz.net")
        self.assertIsNone(id2.getResource())

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

    def test_identifier_unicode_rep(self):
        self.assertEqual(str(Identifier(jid="gbin@gootz.net/へようこそ")), "gbin@gootz.net/へようこそ")

    def test_xhtmlparsing_and_textify(self):
        text_plain, node = build_text_html_message_pair("<html><body>Message</body></html>")
        self.assertEqual(text_plain, "Message")
        self.assertEqual(node.tag, "html")
        self.assertEqual(node.getchildren()[0].tag, "body")
        self.assertEqual(node.getchildren()[0].text, 'Message')

    def test_identifier_double_at_parsing(self):
        id1 = Identifier(jid="gbin@titi.net@gootz.net/toto")
        self.assertEqual(id1.getNode(), "gbin@titi.net")
        self.assertEqual(id1.getDomain(), "gootz.net")
        self.assertEqual(id1.getResource(), "toto")

    def test_buildreply(self):
        dummy = self.dummy

        m = dummy.build_message("Content")
        m.setFrom("from@fromdomain.net/fromresource")
        m.setTo("to@todomain.net/toresource")
        resp = dummy.build_reply(m, "Response")

        self.assertEqual(str(resp.getTo()), "from@fromdomain.net")
        self.assertEqual(str(resp.getFrom()), "err@localhost/err")
        self.assertEqual(str(resp.getBody()), "Response")

    def test_execute_and_send(self):
        @botcmd
        def return_args_as_str(mess, args):
            return "".join(args)

        @botcmd(template='return_args_as_html')
        def return_args_as_html(mess, args):
            return {'args': args}

        @botcmd
        def raises_exception(mess, args):
            raise Exception("Kaboom!")

        dummy = self.dummy
        dummy.commands['return_args_as_str'] = return_args_as_str
        dummy.commands['return_args_as_html'] = return_args_as_html
        dummy.commands['raises_exception'] = raises_exception

        m = dummy.build_message("some_message")
        m.setFrom("noterr@localhost/resource")
        m.setTo("err@localhost/resource")

        dummy._execute_and_send(cmd='return_args_as_str', args=['foo', 'bar'], mess=m, jid='noterr@localhost', template_name=return_args_as_str._err_command_template)
        self.assertEqual("foobar", dummy.pop_message().getBody())

        dummy._execute_and_send(cmd='return_args_as_html', args=['foo', 'bar'], mess=m, jid='noterr@localhost', template_name=return_args_as_html._err_command_template)
        self.assertEqual("<strong>foo</strong><em>bar</em>", dummy.pop_message().getBody())

        dummy._execute_and_send(cmd='raises_exception', args=[], mess=m, jid='noterr@localhost', template_name=raises_exception._err_command_template)
        self.assertIn(dummy.MSG_ERROR_OCCURRED, dummy.pop_message().getBody())
