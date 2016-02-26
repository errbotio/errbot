# coding=utf-8
import sys
import logging
from tempfile import mkdtemp
from os.path import sep
from errbot.errBot import bot_config_defaults

import unittest  # noqa
import os  # noqa
import re  # noqa
from queue import Queue, Empty  # noqa
from mock import patch  # noqa
from errbot.errBot import ErrBot
from errbot.backends.base import Message, MUCRoom, Identifier, ONLINE
from errbot.backends.test import TestIdentifier, TestMUCOccupant
from errbot import botcmd, re_botcmd, arg_botcmd, templating  # noqa
from errbot.main import CORE_STORAGE
from errbot.plugin_manager import BotPluginManager
from errbot.rendering import text
from errbot.core_plugins.acls import ACLS
from errbot.repo_manager import BotRepoManager
from errbot.specific_plugin_manager import SpecificPluginManager
from errbot.storage.base import StoragePluginBase
from errbot.utils import PLUGINS_SUBDIR

LONG_TEXT_STRING = "This is a relatively long line of output, but I am repeated multiple times.\n"

logging.basicConfig(level=logging.DEBUG)


class DummyBackend(ErrBot):
    def change_presence(self, status: str = ONLINE, message: str = '') -> None:
        pass

    def prefix_groupchat_reply(self, message: Message, identifier: Identifier):
        pass

    def query_room(self, room: str) -> MUCRoom:
        pass

    def __init__(self, extra_config=None):
        self.outgoing_message_queue = Queue()
        if extra_config is None:
            extra_config = {}
        # make up a config.
        tempdir = mkdtemp()
        # reset the config every time
        sys.modules.pop('errbot.config-template', None)
        __import__('errbot.config-template')
        config = sys.modules['errbot.config-template']
        bot_config_defaults(config)
        config.BOT_DATA_DIR = tempdir
        config.BOT_LOG_FILE = tempdir + sep + 'log.txt'
        config.BOT_EXTRA_PLUGIN_DIR = []
        config.BOT_LOG_LEVEL = logging.DEBUG
        config.BOT_IDENTITY = {'username': 'err@localhost'}
        config.BOT_ASYNC = False
        config.BOT_PREFIX = '!'
        config.CHATROOM_FN = 'blah'

        for key in extra_config:
            setattr(config, key, extra_config[key])
        super().__init__(config)
        self.bot_identifier = self.build_identifier('err')
        self.md = text()  # We just want simple text for testing purposes

        # setup a memory based storage
        spm = SpecificPluginManager(config, 'storage', StoragePluginBase, CORE_STORAGE, None)
        storage_plugin = spm.get_plugin_by_name('Memory')

        # setup the plugin_manager just internally
        botplugins_dir = os.path.join(config.BOT_DATA_DIR, PLUGINS_SUBDIR)
        if not os.path.exists(botplugins_dir):
            os.makedirs(botplugins_dir, mode=0o755)

        repo_manager = BotRepoManager(storage_plugin, botplugins_dir)
        self.attach_storage_plugin(storage_plugin)
        self.attach_repo_manager(repo_manager)
        self.attach_plugin_manager(BotPluginManager(storage_plugin,
                                                    repo_manager,
                                                    config.BOT_EXTRA_PLUGIN_DIR,
                                                    config.AUTOINSTALL_DEPS,
                                                    getattr(config, 'CORE_PLUGINS', None)))
        self.inject_commands_from(self)
        self.inject_command_filters_from(ACLS(self))

    def build_identifier(self, text_representation):
        return TestIdentifier(text_representation)

    def build_reply(self, mess, text=None, private=False):
        msg = self.build_message(text)
        msg.frm = self.bot_identifier
        msg.to = mess.frm
        return msg

    def send_message(self, mess):
        mess._body = self.md.convert(mess.body)
        self.outgoing_message_queue.put(mess)

    def pop_message(self, timeout=3, block=True):
        return self.outgoing_message_queue.get(timeout=timeout, block=block)

    @botcmd
    def command(self, mess, args):
        return "Regular command"

    @botcmd(admin_only=True)
    def admin_command(self, mess, args):
        return "Admin command"

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

    @botcmd(template='args_as_md')
    def return_args_as_md(self, mess, args):
        return {'args': args}

    @botcmd
    def send_args_as_md(self, mess, args):
        self.send_templated(mess.frm, 'args_as_md', {'args': args})

    @botcmd
    def raises_exception(self, mess, args):
        raise Exception("Kaboom!")

    @botcmd
    def yield_args_as_str(self, mess, args):
        for arg in args:
            yield arg

    @botcmd(template='args_as_md')
    def yield_args_as_md(self, mess, args):
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
    def yields_first_name_last_name(self, mess, first_name=None, last_name=None):
        yield "%s %s" % (first_name, last_name)

    @arg_botcmd('--first-name', dest='first_name')
    @arg_botcmd('--last-name', dest='last_name')
    def returns_first_name_last_name(self, mess, first_name=None, last_name=None):
        return "%s %s" % (first_name, last_name)

    @arg_botcmd('--first-name', dest='first_name')
    @arg_botcmd('--last-name', dest='last_name', unpack_args=False)
    def returns_first_name_last_name_without_unpacking(self, mess, args):
        return "%s %s" % (args.first_name, args.last_name)

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

    def test_buildreply(self):
        dummy = self.dummy

        m = dummy.build_message('Content')
        m.frm = dummy.build_identifier('user')
        m.to = dummy.build_identifier('somewhere')
        resp = dummy.build_reply(m, 'Response')

        self.assertEqual(str(resp.to), 'user')
        self.assertEqual(str(resp.frm), 'err')
        self.assertEqual(str(resp.body), 'Response')


class TestBaseConfig(unittest.TestCase):
    def setUp(self):
        self.dummy = DummyBackend(extra_config={'BOT_ADMINS': 'err@localhost'})

    def test_BOT_ADMINS_unique_string(self):
        dummy = self.dummy

        self.assertEqual(dummy.bot_config.BOT_ADMINS, ('err@localhost',))


class TestExecuteAndSend(unittest.TestCase):
    def setUp(self):
        self.dummy = DummyBackend()
        self.example_message = self.dummy.build_message('some_message')
        self.example_message.frm = self.dummy.build_identifier('noterr')
        self.example_message.to = self.dummy.build_identifier('err')

        assets_path = os.path.join(os.path.dirname(__file__), 'assets')
        templating.template_path.append(templating.make_templates_path(assets_path))
        templating.env = templating.Environment(loader=templating.FileSystemLoader(templating.template_path))

    def test_commands_can_return_string(self):
        dummy = self.dummy
        m = self.example_message

        dummy._execute_and_send(cmd='return_args_as_str', args=['foo', 'bar'], match=None, mess=m,
                                template_name=dummy.return_args_as_str._err_command_template)
        self.assertEqual("foobar", dummy.pop_message().body)

    def test_commands_can_return_md(self):
        dummy = self.dummy
        m = self.example_message

        dummy._execute_and_send(cmd='return_args_as_md', args=['foo', 'bar'], match=None, mess=m,
                                template_name=dummy.return_args_as_md._err_command_template)
        response = dummy.pop_message()
        self.assertEqual("foobar", response.body)

    def test_commands_can_send_templated(self):
        dummy = self.dummy
        m = self.example_message
        dummy._execute_and_send(cmd='send_args_as_md', args=['foo', 'bar'], match=None, mess=m,
                                template_name=dummy.return_args_as_md._err_command_template)
        response = dummy.pop_message()
        self.assertEqual("foobar", response.body)

    def test_exception_is_caught_and_shows_error_message(self):
        dummy = self.dummy
        m = self.example_message

        dummy._execute_and_send(cmd='raises_exception', args=[], match=None, mess=m,
                                template_name=dummy.raises_exception._err_command_template)
        self.assertIn(dummy.MSG_ERROR_OCCURRED, dummy.pop_message().body)

        dummy._execute_and_send(cmd='yields_str_then_raises_exception', args=[], match=None, mess=m,
                                template_name=dummy.yields_str_then_raises_exception._err_command_template)
        self.assertEqual("foobar", dummy.pop_message().body)
        self.assertIn(dummy.MSG_ERROR_OCCURRED, dummy.pop_message().body)

    def test_commands_can_yield_strings(self):
        dummy = self.dummy
        m = self.example_message

        dummy._execute_and_send(cmd='yield_args_as_str', args=['foo', 'bar'], match=None, mess=m,
                                template_name=dummy.yield_args_as_str._err_command_template)
        self.assertEqual("foo", dummy.pop_message().body)
        self.assertEqual("bar", dummy.pop_message().body)

    def test_commands_can_yield_md(self):
        dummy = self.dummy
        m = self.example_message

        dummy._execute_and_send(cmd='yield_args_as_md', args=['foo', 'bar'], match=None, mess=m,
                                template_name=dummy.yield_args_as_md._err_command_template)
        self.assertEqual("foo", dummy.pop_message().body)
        self.assertEqual("bar", dummy.pop_message().body)

    def test_output_longer_than_max_message_size_is_split_into_multiple_messages_when_returned(self):
        dummy = self.dummy
        m = self.example_message
        self.dummy.bot_config.MESSAGE_SIZE_LIMIT = len(LONG_TEXT_STRING)

        dummy._execute_and_send(cmd='return_long_output', args=['foo', 'bar'], match=None, mess=m,
                                template_name=dummy.return_long_output._err_command_template)
        for i in range(3):  # return_long_output outputs a string that's 3x longer than the size limit
            self.assertEqual(LONG_TEXT_STRING.strip(), dummy.pop_message().body)
        self.assertRaises(Empty, dummy.pop_message, *[], **{'block': False})

    def test_output_longer_than_max_message_size_is_split_into_multiple_messages_when_yielded(self):
        dummy = self.dummy
        m = self.example_message
        self.dummy.bot_config.MESSAGE_SIZE_LIMIT = len(LONG_TEXT_STRING)

        dummy._execute_and_send(cmd='yield_long_output', args=['foo', 'bar'], match=None, mess=m,
                                template_name=dummy.yield_long_output._err_command_template)
        for i in range(6):  # yields_long_output yields 2 strings that are 3x longer than the size limit
            self.assertEqual(LONG_TEXT_STRING.strip(), dummy.pop_message().body)
        self.assertRaises(Empty, dummy.pop_message, *[], **{'block': False})


class BotCmds(unittest.TestCase):
    def setUp(self):
        self.dummy = DummyBackend()

    def makemessage(self, message, from_=None, to=None, type="chat"):
        if not from_:
            from_ = self.dummy.build_identifier("noterr")
        if not to:
            to = self.dummy.build_identifier("noterr")
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
        m.frm = TestMUCOccupant("someone", "room")
        self.dummy.callback_message(m)
        self.assertRaises(Empty, self.dummy.pop_message, *[], **{'block': False})

        m = self.makemessage("!return_args_as_str one two",
                             from_=TestMUCOccupant("someone", "room"),
                             type="groupchat")
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
                self.makemessage(
                        "!returns_first_name_last_name --first-name=%s --last-name=%s" % (first_name, last_name))
        )
        self.assertEquals("%s %s" % (first_name, last_name), self.dummy.pop_message().body)

    def test_arg_botcmd_yields_first_name_last_name(self):
        first_name = 'Err'
        last_name = 'Bot'
        self.dummy.callback_message(
                self.makemessage(
                        "!yields_first_name_last_name --first-name=%s --last-name=%s" % (first_name, last_name))
        )
        self.assertEquals("%s %s" % (first_name, last_name), self.dummy.pop_message().body)

    def test_arg_botcmd_returns_value_repeated_count_times(self):
        value = "Foo"
        count = 5
        self.dummy.callback_message(
                self.makemessage("!returns_value_repeated_count_times %s --count %s" % (value, count))
        )
        self.assertEquals(value * count, self.dummy.pop_message().body)

    def test_arg_botcmd_doesnt_raise_systemerror(self):
        self.dummy.callback_message(self.makemessage("!returns_first_name_last_name --invalid-parameter"))

    def test_arg_botcdm_returns_errors_as_chat(self):
        self.dummy.callback_message(self.makemessage("!returns_first_name_last_name --invalid-parameter"))
        self.assertIn(
                "I'm sorry, I couldn't parse that; unrecognized arguments: --invalid-parameter",
                self.dummy.pop_message().body
        )

    def test_arg_botcmd_returns_help_message_as_chat(self):
        self.dummy.callback_message(self.makemessage("!returns_first_name_last_name --help"))
        self.assertIn(
                "usage: returns_first_name_last_name [-h] [--last-name LAST_NAME]",
                self.dummy.pop_message().body
        )

    def test_arg_botcmd_undoes_fancy_unicode_dash_conversion(self):
        first_name = 'Err'
        last_name = 'Bot'
        self.dummy.callback_message(
                self.makemessage("!returns_first_name_last_name —first-name=%s —last-name=%s" % (first_name, last_name))
        )
        self.assertEquals("%s %s" % (first_name, last_name), self.dummy.pop_message().body)

    def test_arg_botcmd_without_argument_unpacking(self):
        first_name = 'Err'
        last_name = 'Bot'
        self.dummy.callback_message(
                self.makemessage("!returns_first_name_last_name_without_unpacking --first-name=%s --last-name=%s"
                                 % (first_name, last_name))
        )
        self.assertEquals("%s %s" % (first_name, last_name), self.dummy.pop_message().body)

    def test_access_controls(self):
        tests = [
            # BOT_ADMINS scenarios
            dict(
                message=self.makemessage("!admin_command"),
                bot_admins=('noterr'),
                expected_response="Admin command",
            ),
            dict(
                message=self.makemessage("!admin_command"),
                bot_admins=(),
                expected_response="This command requires bot-admin privileges",
            ),
            dict(
                message=self.makemessage("!admin_command"),
                bot_admins=('*err'),
                expected_response="Admin command",
            ),

            # ACCESS_CONTROLS scenarios
            dict(
                    message=self.makemessage("!command"),
                    expected_response="Regular command"
            ),
            dict(
                    message=self.makemessage("!regex command with prefix"),
                    expected_response="Regex command"
            ),
            dict(
                    message=self.makemessage("!command"),
                    acl_default={'allowmuc': False, 'allowprivate': False},
                    expected_response="You're not allowed to access this command via private message to me"
            ),
            dict(
                    message=self.makemessage("regex command without prefix"),
                    acl_default={'allowmuc': False, 'allowprivate': False},
                    expected_response="You're not allowed to access this command via private message to me"
            ),
            dict(
                    message=self.makemessage("!command"),
                    acl_default={'allowmuc': True, 'allowprivate': False},
                    expected_response="You're not allowed to access this command via private message to me"
            ),
            dict(
                    message=self.makemessage("!command"),
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
                    message=self.makemessage("!command", type="groupchat", from_=TestMUCOccupant("someone", "room")),
                    acl={'command': {'allowrooms': ('room',)}},
                    expected_response="Regular command"
            ),
            dict(
                message=self.makemessage("!command", type="groupchat", from_=TestMUCOccupant("someone", "room_1")),
                acl={'command': {'allowrooms': ('room_*',)}},
                expected_response="Regular command"
            ),
            dict(
                    message=self.makemessage("!command", type="groupchat", from_=TestMUCOccupant("someone", "room")),
                    acl={'command': {'allowrooms': ('anotherroom@localhost',)}},
                    expected_response="You're not allowed to access this command from this room",
            ),
            dict(
                    message=self.makemessage("!command", type="groupchat", from_=TestMUCOccupant("someone", "room")),
                    acl={'command': {'denyrooms': ('room',)}},
                    expected_response="You're not allowed to access this command from this room",
            ),
            dict(
                message=self.makemessage("!command", type="groupchat", from_=TestMUCOccupant("someone", "room")),
                acl={'command': {'denyrooms': ('*',)}},
                expected_response="You're not allowed to access this command from this room",
            ),
            dict(
                    message=self.makemessage("!command", type="groupchat", from_=TestMUCOccupant("someone", "room")),
                    acl={'command': {'denyrooms': ('anotherroom',)}},
                    expected_response="Regular command"
            ),
            dict(
                message=self.makemessage("!command"),
                acl={'command': {'allowusers': ('noterr',)}},
                expected_response="Regular command"
            ),
            dict(
                message=self.makemessage("!command"),
                acl={'command': {'allowusers': ('err',)}},
                expected_response="You're not allowed to access this command from this user",
            ),
            dict(
                message=self.makemessage("!command"),
                acl={'command': {'allowusers': ('*err',)}},
                expected_response="Regular command"
            ),
            dict(
                message=self.makemessage("!command"),
                acl={'command': {'denyusers': ('err',)}},
                expected_response="Regular command"
            ),
            dict(
                message=self.makemessage("!command"),
                acl={'command': {'denyusers': ('noterr',)}},
                expected_response="You're not allowed to access this command from this user"
            ),
            dict(
                message=self.makemessage("!command"),
                acl={'command': {'denyusers': ('*err',)}},
                expected_response="You're not allowed to access this command from this user"
            ),
        ]

        for test in tests:
            self.dummy.bot_config.ACCESS_CONTROLS_DEFAULT = test.get('acl_default', {})
            self.dummy.bot_config.ACCESS_CONTROLS = test.get('acl', {})
            self.dummy.bot_config.BOT_ADMINS = test.get('bot_admins', ())
            logger = logging.getLogger(__name__)
            logger.info("** message: {}".format(test['message'].body))
            logger.info("** bot_admins: {}".format(self.dummy.bot_config.BOT_ADMINS))
            logger.info("** acl: {!r}".format(self.dummy.bot_config.ACCESS_CONTROLS))
            logger.info("** acl_default: {!r}".format(self.dummy.bot_config.ACCESS_CONTROLS_DEFAULT))
            self.dummy.callback_message(test['message'])
            self.assertEqual(
                    test['expected_response'],
                    self.dummy.pop_message().body
            )
