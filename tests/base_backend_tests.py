# coding=utf-8
import sys
import logging
from tempfile import mkdtemp
from os.path import sep
from errbot.errBot import bot_config_defaults

__import__('errbot.config-template')
config_module = sys.modules['errbot.config-template']
sys.modules['config'] = config_module

tempdir = mkdtemp()
config_module.BOT_DATA_DIR = tempdir
config_module.BOT_LOG_FILE = tempdir + sep + 'log.txt'
config_module.BOT_EXTRA_PLUGIN_DIR = []
config_module.BOT_LOG_LEVEL = logging.DEBUG

import unittest  # noqa
import os  # noqa
import re  # noqa
from queue import Queue, Empty  # noqa
from mock import patch  # noqa
from errbot.backends import SimpleIdentifier  # noqa
from errbot.backends.base import Backend, Message  # noqa
from errbot.backends.base import build_message, build_text_html_message_pair  # noqa
from errbot import botcmd, re_botcmd, arg_botcmd, templating  # noqa
from errbot.utils import mess_2_embeddablehtml  # noqa

LONG_TEXT_STRING = "This is a relatively long line of output, but I am repeated multiple times.\n"


class Config:
    BOT_IDENTITY = {'username': 'err@localhost'}
    BOT_ASYNC = False
    BOT_PREFIX = '!'
    CHATROOM_FN = 'blah'


class DummyBackend(Backend):
    outgoing_message_queue = Queue()
    jid = SimpleIdentifier('err')

    def __init__(self, extra_config={}):
        self.bot_config = Config()
        for key in extra_config:
            setattr(self.bot_config, key, extra_config[key])
        bot_config_defaults(self.bot_config)
        super(DummyBackend, self).__init__(self.bot_config)
        self.inject_commands_from(self)

    def build_message(self, text):
        return build_message(text, Message)

    def send_message(self, mess):
        self.outgoing_message_queue.put(mess)

    def pop_message(self, timeout=3, block=True):
        return self.outgoing_message_queue.get(timeout=timeout, block=block)

    @botcmd
    def command(self, mess, args):
        return "Regular command"

    @re_botcmd(pattern=r'^regex command with prefix$', prefixed=True)
    def regex_command_with_prefix(self, mess, match):
        return "Regex command"

    @re_botcmd(pattern=r'^regex command without prefix$', prefixed=False)
    def regex_command_without_prefix(self, mess, match):
        return "Regex command"

    @re_botcmd(pattern=r'regex command with capture group: (?P<capture>.*)', prefixed=False)
    def regex_command_with_capture_group(self, mess, match):
        return match.group('capture')

    @re_botcmd(pattern=r'matched by two commands')
    def double_regex_command_one(self, mess, match):
        return "one"

    @re_botcmd(pattern=r'matched by two commands', flags=re.IGNORECASE)
    def double_regex_command_two(self, mess, match):
        return "two"

    @re_botcmd(pattern=r'match_here', matchall=True)
    def regex_command_with_matchall(self, mess, matches):
        return len(matches)

    @botcmd
    def return_args_as_str(self, mess, args):
        return "".join(args)

    @botcmd(template='args_as_html')
    def return_args_as_html(self, mess, args):
        return {'args': args}

    @botcmd
    def raises_exception(self, mess, args):
        raise Exception("Kaboom!")

    @botcmd
    def yield_args_as_str(self, mess, args):
        for arg in args:
            yield arg

    @botcmd(template='args_as_html')
    def yield_args_as_html(self, mess, args):
        for arg in args:
            yield {'args': [arg]}

    @botcmd
    def yields_str_then_raises_exception(self, mess, args):
        yield 'foobar'
        raise Exception('Kaboom!')

    @botcmd
    def return_long_output(self, mess, args):
        return LONG_TEXT_STRING * 3

    @botcmd
    def yield_long_output(self, mess, args):
        for i in range(2):
            yield LONG_TEXT_STRING * 3

    ##
    # arg_botcmd test commands
    ##

    @arg_botcmd('--first-name', dest='first_name')
    @arg_botcmd('--last-name', dest='last_name')
    def returns_first_name_last_name(self, mess, first_name=None, last_name=None):
        return "%s %s" % (first_name, last_name)

    @arg_botcmd('value', type=str)
    @arg_botcmd('--count', dest='count', type=int)
    def returns_value_repeated_count_times(self, mess, value=None, count=None):
        # str * int gives a repeated string
        return value * count

    @property
    def mode(self):
        return "Dummy"

    @property
    def rooms(self):
        return []


class TestBase(unittest.TestCase):
    def setUp(self):
        self.dummy = DummyBackend()

    def test_xhtmlparsing_and_textify(self):
        text_plain, node = build_text_html_message_pair('<html><body>Message</body></html>')
        self.assertEqual(text_plain, 'Message')
        self.assertEqual(node.tag, 'html')
        self.assertEqual(node.getchildren()[0].tag, 'body')
        self.assertEqual(node.getchildren()[0].text, 'Message')

    def test_buildreply(self):
        dummy = self.dummy

        m = dummy.build_message('Content')
        m.frm = 'from@fromdomain.net/fromresource'
        m.to = 'to@todomain.net/toresource'
        resp = dummy.build_reply(m, 'Response')

        self.assertEqual(str(resp.to), 'from@fromdomain.net/fromresource')
        self.assertEqual(str(resp.frm), 'err@localhost/err')
        self.assertEqual(str(resp.body), 'Response')


class TestExecuteAndSend(unittest.TestCase):
    def setUp(self):
        self.dummy = DummyBackend()
        self.example_message = self.dummy.build_message('some_message')
        self.example_message.frm = SimpleIdentifier('noterr@localhost/resource')
        self.example_message.to = SimpleIdentifier('err@localhost/resource')

        assets_path = os.path.join(os.path.dirname(__file__), 'assets')
        templating.template_path.append(templating.make_templates_path(assets_path))
        templating.env = templating.Environment(loader=templating.FileSystemLoader(templating.template_path))

    def test_commands_can_return_string(self):
        dummy = self.dummy
        m = self.example_message

        dummy._execute_and_send(cmd='return_args_as_str', args=['foo', 'bar'], match=None, mess=m,
                                jid='noterr@localhost', template_name=dummy.return_args_as_str._err_command_template)
        self.assertEqual("foobar", dummy.pop_message().body)

    def test_commands_can_return_html(self):
        dummy = self.dummy
        m = self.example_message

        dummy._execute_and_send(cmd='return_args_as_html', args=['foo', 'bar'], match=None, mess=m,
                                jid='noterr@localhost', template_name=dummy.return_args_as_html._err_command_template)
        response = dummy.pop_message()
        self.assertEqual("foobar", response.body)
        self.assertEqual('<strong xmlns:ns0="http://jabber.org/protocol/xhtml-im">foo</strong>'
                         '<em xmlns:ns0="http://jabber.org/protocol/xhtml-im">bar</em>\n\n',
                         mess_2_embeddablehtml(response)[0])

    def test_exception_is_caught_and_shows_error_message(self):
        dummy = self.dummy
        m = self.example_message

        dummy._execute_and_send(cmd='raises_exception', args=[], match=None, mess=m, jid='noterr@localhost',
                                template_name=dummy.raises_exception._err_command_template)
        self.assertIn(dummy.MSG_ERROR_OCCURRED, dummy.pop_message().body)

        dummy._execute_and_send(cmd='yields_str_then_raises_exception', args=[], match=None, mess=m,
                                jid='noterr@localhost',
                                template_name=dummy.yields_str_then_raises_exception._err_command_template)
        self.assertEqual("foobar", dummy.pop_message().body)
        self.assertIn(dummy.MSG_ERROR_OCCURRED, dummy.pop_message().body)

    def test_commands_can_yield_strings(self):
        dummy = self.dummy
        m = self.example_message

        dummy._execute_and_send(cmd='yield_args_as_str', args=['foo', 'bar'], match=None, mess=m,
                                jid='noterr@localhost', template_name=dummy.yield_args_as_str._err_command_template)
        self.assertEqual("foo", dummy.pop_message().body)
        self.assertEqual("bar", dummy.pop_message().body)

    def test_commands_can_yield_html(self):
        dummy = self.dummy
        m = self.example_message

        dummy._execute_and_send(cmd='yield_args_as_html', args=['foo', 'bar'], match=None, mess=m,
                                jid='noterr@localhost', template_name=dummy.yield_args_as_html._err_command_template)
        response1 = dummy.pop_message()
        response2 = dummy.pop_message()
        self.assertEqual("foo", response1.body)
        self.assertEqual('<strong xmlns:ns0="http://jabber.org/protocol/xhtml-im">foo</strong>\n\n',
                         mess_2_embeddablehtml(response1)[0])
        self.assertEqual("bar", response2.body)
        self.assertEqual('<strong xmlns:ns0="http://jabber.org/protocol/xhtml-im">bar</strong>\n\n',
                         mess_2_embeddablehtml(response2)[0])

    def test_output_longer_than_max_message_size_is_split_into_multiple_messages_when_returned(self):
        dummy = self.dummy
        m = self.example_message
        self.dummy.bot_config.MESSAGE_SIZE_LIMIT = len(LONG_TEXT_STRING)

        dummy._execute_and_send(cmd='return_long_output', args=['foo', 'bar'], match=None, mess=m,
                                jid='noterr@localhost', template_name=dummy.return_long_output._err_command_template)
        for i in range(3):  # return_long_output outputs a string that's 3x longer than the size limit
            self.assertEqual(LONG_TEXT_STRING, dummy.pop_message().body)
        self.assertRaises(Empty, dummy.pop_message, *[], **{'block': False})

    def test_output_longer_than_max_message_size_is_split_into_multiple_messages_when_yielded(self):
        dummy = self.dummy
        m = self.example_message
        self.dummy.bot_config.MESSAGE_SIZE_LIMIT = len(LONG_TEXT_STRING)

        dummy._execute_and_send(cmd='yield_long_output', args=['foo', 'bar'], match=None, mess=m,
                                jid='noterr@localhost', template_name=dummy.yield_long_output._err_command_template)
        for i in range(6):  # yields_long_output yields 2 strings that are 3x longer than the size limit
            self.assertEqual(LONG_TEXT_STRING, dummy.pop_message().body)
        self.assertRaises(Empty, dummy.pop_message, *[], **{'block': False})


class BotCmds(unittest.TestCase):
    def setUp(self):
        self.dummy = DummyBackend()

    def makemessage(self, message, from_="noterr@localhost/resource", to="noterr@localhost/resource", type="chat"):
        m = self.dummy.build_message(message)
        m.frm = from_
        m.to = to
        m.type = type
        return m

    def test_inject_skips_methods_without_botcmd_decorator(self):
        self.assertTrue('build_message' not in self.dummy.commands)

    def test_inject_and_remove_botcmd(self):
        self.assertTrue('command' in self.dummy.commands)
        self.dummy.remove_commands_from(self.dummy)
        self.assertFalse(len(self.dummy.commands))

    def test_inject_and_remove_re_botcmd(self):
        self.assertTrue('regex_command_with_prefix' in self.dummy.re_commands)
        self.dummy.remove_commands_from(self.dummy)
        self.assertFalse(len(self.dummy.re_commands))

    def test_callback_message(self):
        self.dummy.callback_message(self.makemessage("!return_args_as_str one two"))
        self.assertEquals("one two", self.dummy.pop_message().body)

    def test_callback_message_with_prefix_optional(self):
        self.dummy = DummyBackend({'BOT_PREFIX_OPTIONAL_ON_CHAT': True})
        m = self.makemessage("return_args_as_str one two")
        self.dummy.callback_message(m)
        self.assertEquals("one two", self.dummy.pop_message().body)

        # Groupchat should still require the prefix
        m.type = "groupchat"
        self.dummy.callback_message(m)
        self.assertRaises(Empty, self.dummy.pop_message, *[], **{'block': False})

        m = self.makemessage("!return_args_as_str one two", type="groupchat")
        self.dummy.callback_message(m)
        self.assertEquals("one two", self.dummy.pop_message().body)

    def test_callback_message_with_bot_alt_prefixes(self):
        self.dummy = DummyBackend({'BOT_ALT_PREFIXES': ('Err',), 'BOT_ALT_PREFIX_SEPARATORS': (',', ';')})
        self.dummy.callback_message(self.makemessage("Err return_args_as_str one two"))
        self.assertEquals("one two", self.dummy.pop_message().body)
        self.dummy.callback_message(self.makemessage("Err, return_args_as_str one two"))
        self.assertEquals("one two", self.dummy.pop_message().body)

    def test_callback_message_with_re_botcmd(self):
        self.dummy.callback_message(self.makemessage("!regex command with prefix"))
        self.assertEquals("Regex command", self.dummy.pop_message().body)
        self.dummy.callback_message(self.makemessage("regex command without prefix"))
        self.assertEquals("Regex command", self.dummy.pop_message().body)
        self.dummy.callback_message(self.makemessage("!regex command with capture group: Captured text"))
        self.assertEquals("Captured text", self.dummy.pop_message().body)
        self.dummy.callback_message(self.makemessage("regex command with capture group: Captured text"))
        self.assertEquals("Captured text", self.dummy.pop_message().body)
        self.dummy.callback_message(self.makemessage(
            "This command also allows extra text in front - regex command with capture group: Captured text"))
        self.assertEquals("Captured text", self.dummy.pop_message().body)

    def test_callback_message_with_re_botcmd_and_alt_prefixes(self):
        self.dummy = DummyBackend({'BOT_ALT_PREFIXES': ('Err',), 'BOT_ALT_PREFIX_SEPARATORS': (',', ';')})
        self.dummy.callback_message(self.makemessage("!regex command with prefix"))
        self.assertEquals("Regex command", self.dummy.pop_message().body)
        self.dummy.callback_message(self.makemessage("Err regex command with prefix"))
        self.assertEquals("Regex command", self.dummy.pop_message().body)
        self.dummy.callback_message(self.makemessage("Err, regex command with prefix"))
        self.assertEquals("Regex command", self.dummy.pop_message().body)
        self.dummy.callback_message(self.makemessage("regex command without prefix"))
        self.assertEquals("Regex command", self.dummy.pop_message().body)
        self.dummy.callback_message(self.makemessage("!regex command with capture group: Captured text"))
        self.assertEquals("Captured text", self.dummy.pop_message().body)
        self.dummy.callback_message(self.makemessage("regex command with capture group: Captured text"))
        self.assertEquals("Captured text", self.dummy.pop_message().body)
        self.dummy.callback_message(self.makemessage(
            "This command also allows extra text in front - regex command with capture group: Captured text"))
        self.assertEquals("Captured text", self.dummy.pop_message().body)
        self.dummy.callback_message(self.makemessage("Err, regex command with capture group: Captured text"))
        self.assertEquals("Captured text", self.dummy.pop_message().body)
        self.dummy.callback_message(self.makemessage(
            "Err This command also allows extra text in front - regex command with capture group: Captured text"))
        self.assertEquals("Captured text", self.dummy.pop_message().body)
        self.dummy.callback_message(self.makemessage("!match_here"))
        self.assertEquals("1", self.dummy.pop_message().body)
        self.dummy.callback_message(self.makemessage("!match_here match_here match_here"))
        self.assertEquals("3", self.dummy.pop_message().body)

    def test_regex_commands_can_overlap(self):
        self.dummy.callback_message(self.makemessage("!matched by two commands"))
        response = (self.dummy.pop_message().body, self.dummy.pop_message().body)
        self.assertTrue(response == ("one", "two") or response == ("two", "one"))

    def test_regex_commands_allow_passing_re_flags(self):
        self.dummy.callback_message(self.makemessage("!MaTcHeD By TwO cOmMaNdS"))
        self.assertEquals("two", self.dummy.pop_message().body)
        self.assertRaises(Empty, self.dummy.pop_message, **{'timeout': 1})

    def test_arg_botcmd_returns_first_name_last_name(self):
        first_name = 'Err'
        last_name = 'Bot'
        self.dummy.callback_message(
            self.makemessage("!returns_first_name_last_name --first-name=%s --last-name=%s" % (first_name, last_name))
        )
        self.assertEquals("%s %s" % (first_name, last_name), self.dummy.pop_message().body)

    def test_arg_botcmd_returns_value_repeated_count_times(self):
        value = "Foo"
        count = 5
        self.dummy.callback_message(
            self.makemessage("!returns_value_repeated_count_times %s --count %s" % (value, count))
        )
        self.assertEquals(value * count, self.dummy.pop_message().body)

    def test_access_controls(self):
        tests = [
            dict(
                message=self.makemessage("!command"),
                acl={},
                acl_default={},
                expected_response="Regular command"
            ),
            dict(
                message=self.makemessage("!regex command with prefix"),
                acl={},
                acl_default={},
                expected_response="Regex command"
            ),
            dict(
                message=self.makemessage("!command"),
                acl={},
                acl_default={'allowmuc': False, 'allowprivate': False},
                expected_response="You're not allowed to access this command via private message to me"
            ),
            dict(
                message=self.makemessage("regex command without prefix"),
                acl={},
                acl_default={'allowmuc': False, 'allowprivate': False},
                expected_response="You're not allowed to access this command via private message to me"
            ),
            dict(
                message=self.makemessage("!command"),
                acl={},
                acl_default={'allowmuc': True, 'allowprivate': False},
                expected_response="You're not allowed to access this command via private message to me"
            ),
            dict(
                message=self.makemessage("!command"),
                acl={},
                acl_default={'allowmuc': False, 'allowprivate': True},
                expected_response="Regular command"
            ),
            dict(
                message=self.makemessage("!command"),
                acl={'command': {'allowprivate': True}},
                acl_default={'allowmuc': False, 'allowprivate': False},
                expected_response="Regular command"
            ),
            dict(
                message=self.makemessage("!command", type="groupchat", from_="room@localhost/err"),
                acl={'command': {'allowrooms': ('room@localhost',)}},
                acl_default={},
                expected_response="Regular command"
            ),
            dict(
                message=self.makemessage("!command", type="groupchat", from_="room@localhost/err"),
                acl={'command': {'allowrooms': ('anotherroom@localhost',)}},
                acl_default={},
                expected_response="You're not allowed to access this command from this room",
            ),
            dict(
                message=self.makemessage("!command", type="groupchat", from_="room@localhost/err"),
                acl={'command': {'denyrooms': ('room@localhost',)}},
                acl_default={},
                expected_response="You're not allowed to access this command from this room",
            ),
            dict(
                message=self.makemessage("!command", type="groupchat", from_="room@localhost/err"),
                acl={'command': {'denyrooms': ('anotherroom@localhost',)}},
                acl_default={},
                expected_response="Regular command"
            ),
        ]

        for test in tests:
            self.dummy.bot_config.ACCESS_CONTROLS_DEFAULT = test['acl_default']
            self.dummy.bot_config.ACCESS_CONTROLS = test['acl']
            logger = logging.getLogger(__name__)
            logger.info("** message: {}".format(test['message'].body))
            logger.info("** acl: {!r}".format(test['acl']))
            logger.info("** acl_default: {!r}".format(test['acl_default']))
            self.dummy.callback_message(test['message'])
            self.assertEqual(
                test['expected_response'],
                self.dummy.pop_message().body
            )
