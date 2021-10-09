# coding=utf-8
import logging
import os  # noqa
import re  # noqa
import sys
from collections import OrderedDict
from os.path import sep
from pathlib import Path
from queue import Empty, Queue  # noqa
from tempfile import mkdtemp

import pytest

from errbot import arg_botcmd, botcmd, re_botcmd, templating  # noqa
from errbot.backend_plugin_manager import BackendPluginManager
from errbot.backends.base import ONLINE, Identifier, Message, Room
from errbot.backends.test import ShallowConfig, TestOccupant, TestPerson, TestRoom
from errbot.bootstrap import CORE_STORAGE, bot_config_defaults
from errbot.core import ErrBot
from errbot.core_plugins.acls import ACLS
from errbot.plugin_manager import BotPluginManager
from errbot.rendering import text
from errbot.repo_manager import BotRepoManager
from errbot.storage.base import StoragePluginBase
from errbot.utils import PLUGINS_SUBDIR

LONG_TEXT_STRING = (
    "This is a relatively long line of output, but I am repeated multiple times.\n"
)

logging.basicConfig(level=logging.DEBUG)

SIMPLE_JSON_PLUGINS_INDEX = """
{"errbotio/err-helloworld":
    {"HelloWorld":
        {"path": "/helloWorld.plug",
         "documentation": "let's say hello!",
         "avatar_url": "https://avatars.githubusercontent.com/u/15802630?v=3",
         "name": "HelloWorld",
         "python": "2+",
         "repo": "https://github.com/errbotio/err-helloworld"
         }
    }
}
"""


class DummyBackend(ErrBot):
    def change_presence(self, status: str = ONLINE, message: str = "") -> None:
        pass

    def prefix_groupchat_reply(self, message: Message, identifier: Identifier):
        pass

    def query_room(self, room: str) -> Room:
        pass

    def __init__(self, extra_config=None):
        self.outgoing_message_queue = Queue()
        if extra_config is None:
            extra_config = {}
        # make up a config.
        tempdir = mkdtemp()
        # reset the config every time
        sys.modules.pop("errbot.config-template", None)
        __import__("errbot.config-template")
        config = ShallowConfig()
        config.__dict__.update(sys.modules["errbot.config-template"].__dict__)
        bot_config_defaults(config)

        # It injects itself as a plugin. Changed the name to be sure we distinguish it.
        self.name = "DummyBackendRealName"

        config.BOT_DATA_DIR = tempdir
        config.BOT_LOG_FILE = tempdir + sep + "log.txt"
        config.BOT_PLUGIN_INDEXES = tempdir + sep + "repos.json"
        config.BOT_EXTRA_PLUGIN_DIR = []
        config.BOT_LOG_LEVEL = logging.DEBUG
        config.BOT_IDENTITY = {"username": "err@localhost"}
        config.BOT_ASYNC = False
        config.BOT_PREFIX = "!"
        config.CHATROOM_FN = "blah"

        # Writeout the made up repos file
        with open(config.BOT_PLUGIN_INDEXES, "w") as index_file:
            index_file.write(SIMPLE_JSON_PLUGINS_INDEX)

        for key in extra_config:
            setattr(config, key, extra_config[key])
        super().__init__(config)
        self.bot_identifier = self.build_identifier("err")
        self.md = text()  # We just want simple text for testing purposes

        # setup a memory based storage
        spm = BackendPluginManager(
            config, "errbot.storage", "Memory", StoragePluginBase, CORE_STORAGE
        )
        storage_plugin = spm.load_plugin()

        # setup the plugin_manager just internally
        botplugins_dir = os.path.join(config.BOT_DATA_DIR, PLUGINS_SUBDIR)
        if not os.path.exists(botplugins_dir):
            os.makedirs(botplugins_dir, mode=0o755)

        # get it back from where we publish it.
        repo_index_paths = (
            os.path.join(
                os.path.dirname(__file__), "..", "docs", "_extra", "repos.json"
            ),
        )
        repo_manager = BotRepoManager(storage_plugin, botplugins_dir, repo_index_paths)
        self.attach_storage_plugin(storage_plugin)
        self.attach_repo_manager(repo_manager)
        self.attach_plugin_manager(
            BotPluginManager(
                storage_plugin,
                config.BOT_EXTRA_PLUGIN_DIR,
                config.AUTOINSTALL_DEPS,
                getattr(config, "CORE_PLUGINS", None),
                lambda name, clazz: clazz(self, name),
                getattr(config, "PLUGINS_CALLBACK_ORDER", (None,)),
            )
        )
        self.inject_commands_from(self)
        self.inject_command_filters_from(ACLS(self))

    def build_identifier(self, text_representation):
        return TestPerson(text_representation)

    def build_reply(self, msg, text=None, private=False, threaded=False):
        reply = self.build_message(text)
        reply.frm = self.bot_identifier
        reply.to = msg.frm
        if threaded:
            reply.parent = msg
        return reply

    def send_message(self, msg):
        msg._body = self.md.convert(msg.body)
        self.outgoing_message_queue.put(msg)

    def pop_message(self, timeout=3, block=True):
        return self.outgoing_message_queue.get(timeout=timeout, block=block)

    @botcmd
    def command(self, msg, args):
        return "Regular command"

    @botcmd(admin_only=True)
    def admin_command(self, msg, args):
        return "Admin command"

    @re_botcmd(pattern=r"^regex command with prefix$", prefixed=True)
    def regex_command_with_prefix(self, msg, match):
        return "Regex command"

    @re_botcmd(pattern=r"^regex command without prefix$", prefixed=False)
    def regex_command_without_prefix(self, msg, match):
        return "Regex command"

    @re_botcmd(
        pattern=r"regex command with capture group: (?P<capture>.*)", prefixed=False
    )
    def regex_command_with_capture_group(self, msg, match):
        return match.group("capture")

    @re_botcmd(pattern=r"matched by two commands")
    def double_regex_command_one(self, msg, match):
        return "one"

    @re_botcmd(pattern=r"matched by two commands", flags=re.IGNORECASE)
    def double_regex_command_two(self, msg, match):
        return "two"

    @re_botcmd(pattern=r"match_here", matchall=True)
    def regex_command_with_matchall(self, msg, matches):
        return len(matches)

    @botcmd
    def return_args_as_str(self, msg, args):
        return "".join(args)

    @botcmd(template="args_as_md")
    def return_args_as_md(self, msg, args):
        return {"args": args}

    @botcmd
    def send_args_as_md(self, msg, args):
        self.send_templated(msg.frm, "args_as_md", {"args": args})

    @botcmd
    def raises_exception(self, msg, args):
        raise Exception("Kaboom!")

    @botcmd
    def yield_args_as_str(self, msg, args):
        for arg in args:
            yield arg

    @botcmd(template="args_as_md")
    def yield_args_as_md(self, msg, args):
        for arg in args:
            yield {"args": [arg]}

    @botcmd
    def yields_str_then_raises_exception(self, msg, args):
        yield "foobar"
        raise Exception("Kaboom!")

    @botcmd
    def return_long_output(self, msg, args):
        return LONG_TEXT_STRING * 3

    @botcmd
    def yield_long_output(self, msg, args):
        for i in range(2):
            yield LONG_TEXT_STRING * 3

    ##
    # arg_botcmd test commands
    ##

    @arg_botcmd("--first-name", dest="first_name")
    @arg_botcmd("--last-name", dest="last_name")
    def yields_first_name_last_name(self, msg, first_name=None, last_name=None):
        yield "%s %s" % (first_name, last_name)

    @arg_botcmd("--first-name", dest="first_name")
    @arg_botcmd("--last-name", dest="last_name")
    def returns_first_name_last_name(self, msg, first_name=None, last_name=None):
        return "%s %s" % (first_name, last_name)

    @arg_botcmd("--first-name", dest="first_name")
    @arg_botcmd("--last-name", dest="last_name", unpack_args=False)
    def returns_first_name_last_name_without_unpacking(self, msg, args):
        return "%s %s" % (args.first_name, args.last_name)

    @arg_botcmd("value", type=str)
    @arg_botcmd("--count", dest="count", type=int)
    def returns_value_repeated_count_times(self, msg, value=None, count=None):
        # str * int gives a repeated string
        return value * count

    @property
    def mode(self):
        return "Dummy"

    @property
    def rooms(self):
        return []


@pytest.fixture
def dummy_backend():
    return DummyBackend()


def test_buildreply(dummy_backend):
    m = dummy_backend.build_message("Content")
    m.frm = dummy_backend.build_identifier("user")
    m.to = dummy_backend.build_identifier("somewhere")
    resp = dummy_backend.build_reply(m, "Response")

    assert str(resp.to) == "user"
    assert str(resp.frm) == "err"
    assert str(resp.body) == "Response"
    assert resp.parent is None


def test_buildreply_with_parent(dummy_backend):
    m = dummy_backend.build_message("Content")
    m.frm = dummy_backend.build_identifier("user")
    m.to = dummy_backend.build_identifier("somewhere")
    resp = dummy_backend.build_reply(m, "Response", threaded=True)

    assert resp.parent is not None


def test_all_command_private():
    dummy_backend = DummyBackend(extra_config={"DIVERT_TO_PRIVATE": ("ALL_COMMANDS",)})
    m = dummy_backend.build_message("Content")
    m.frm = dummy_backend.build_identifier("user")
    m.to = dummy_backend.build_identifier("somewhere")
    resp = dummy_backend.build_reply(m, "Response", threaded=True)
    assert "ALL_COMMANDS" in dummy_backend.bot_config.DIVERT_TO_PRIVATE
    assert resp is not None


def test_bot_admins_unique_string():
    dummy = DummyBackend(extra_config={"BOT_ADMINS": "err@localhost"})
    assert dummy.bot_config.BOT_ADMINS == ("err@localhost",)


@pytest.fixture
def dummy_execute_and_send():
    dummy = DummyBackend()
    example_message = dummy.build_message("some_message")
    example_message.frm = dummy.build_identifier("noterr")
    example_message.to = dummy.build_identifier("err")

    assets_path = os.path.join(os.path.dirname(__file__), "assets")
    templating.template_path.append(
        str(templating.make_templates_path(Path(assets_path)))
    )
    templating.env = templating.Environment(
        loader=templating.FileSystemLoader(templating.template_path)
    )
    return dummy, example_message


def test_commands_can_return_string(dummy_execute_and_send):
    dummy, m = dummy_execute_and_send

    dummy._execute_and_send(
        cmd="return_args_as_str",
        args=["foo", "bar"],
        match=None,
        msg=m,
        template_name=dummy.return_args_as_str._err_command_template,
    )
    assert "foobar" == dummy.pop_message().body


def test_commands_can_return_md(dummy_execute_and_send):
    dummy, m = dummy_execute_and_send
    dummy._execute_and_send(
        cmd="return_args_as_md",
        args=["foo", "bar"],
        match=None,
        msg=m,
        template_name=dummy.return_args_as_md._err_command_template,
    )
    response = dummy.pop_message()
    assert "foobar" == response.body


def test_commands_can_send_templated(dummy_execute_and_send):
    dummy, m = dummy_execute_and_send
    dummy._execute_and_send(
        cmd="send_args_as_md",
        args=["foo", "bar"],
        match=None,
        msg=m,
        template_name=dummy.return_args_as_md._err_command_template,
    )
    response = dummy.pop_message()
    assert "foobar" == response.body


def test_exception_is_caught_and_shows_error_message(dummy_execute_and_send):
    dummy, m = dummy_execute_and_send
    dummy._execute_and_send(
        cmd="raises_exception",
        args=[],
        match=None,
        msg=m,
        template_name=dummy.raises_exception._err_command_template,
    )
    assert dummy.MSG_ERROR_OCCURRED in dummy.pop_message().body

    dummy._execute_and_send(
        cmd="yields_str_then_raises_exception",
        args=[],
        match=None,
        msg=m,
        template_name=dummy.yields_str_then_raises_exception._err_command_template,
    )
    assert "foobar" == dummy.pop_message().body
    assert dummy.MSG_ERROR_OCCURRED in dummy.pop_message().body


def test_commands_can_yield_strings(dummy_execute_and_send):
    dummy, m = dummy_execute_and_send
    dummy._execute_and_send(
        cmd="yield_args_as_str",
        args=["foo", "bar"],
        match=None,
        msg=m,
        template_name=dummy.yield_args_as_str._err_command_template,
    )
    assert "foo" == dummy.pop_message().body
    assert "bar" == dummy.pop_message().body


def test_commands_can_yield_md(dummy_execute_and_send):
    dummy, m = dummy_execute_and_send
    dummy._execute_and_send(
        cmd="yield_args_as_md",
        args=["foo", "bar"],
        match=None,
        msg=m,
        template_name=dummy.yield_args_as_md._err_command_template,
    )
    assert "foo" == dummy.pop_message().body
    assert "bar" == dummy.pop_message().body


def test_output_longer_than_max_msg_size_is_split_into_multiple_msgs_when_returned(
    dummy_execute_and_send,
):
    dummy, m = dummy_execute_and_send
    dummy.bot_config.MESSAGE_SIZE_LIMIT = len(LONG_TEXT_STRING)

    dummy._execute_and_send(
        cmd="return_long_output",
        args=["foo", "bar"],
        match=None,
        msg=m,
        template_name=dummy.return_long_output._err_command_template,
    )
    for i in range(
        3
    ):  # return_long_output outputs a string that's 3x longer than the size limit
        assert LONG_TEXT_STRING.strip() == dummy.pop_message().body

    with pytest.raises(Empty):
        dummy.pop_message(block=False)


def test_output_longer_than_max_msg_size_is_split_into_multiple_msgs_when_yielded(
    dummy_execute_and_send,
):
    dummy, m = dummy_execute_and_send
    dummy.bot_config.MESSAGE_SIZE_LIMIT = len(LONG_TEXT_STRING)

    dummy._execute_and_send(
        cmd="yield_long_output",
        args=["foo", "bar"],
        match=None,
        msg=m,
        template_name=dummy.yield_long_output._err_command_template,
    )
    for i in range(
        6
    ):  # yields_long_output yields 2 strings that are 3x longer than the size limit
        assert LONG_TEXT_STRING.strip() == dummy.pop_message().body
    with pytest.raises(Empty):
        dummy.pop_message(block=False)


def makemessage(dummy, message, from_=None, to=None):
    if not from_:
        from_ = dummy.build_identifier("noterr")
    if not to:
        to = dummy.build_identifier("noterr")
    m = dummy.build_message(message)
    m.frm = from_
    m.to = to
    return m


def test_inject_skips_methods_without_botcmd_decorator(dummy_backend):
    assert "build_message" not in dummy_backend.commands


def test_inject_and_remove_botcmd(dummy_backend):
    assert "command" in dummy_backend.commands
    dummy_backend.remove_commands_from(dummy_backend)
    assert len(dummy_backend.commands) == 0


def test_inject_and_remove_re_botcmd(dummy_backend):
    assert "regex_command_with_prefix" in dummy_backend.re_commands
    dummy_backend.remove_commands_from(dummy_backend)
    assert len(dummy_backend.re_commands) == 0


def test_callback_message(dummy_backend):
    dummy_backend.callback_message(
        makemessage(dummy_backend, "!return_args_as_str one two")
    )
    assert "one two" == dummy_backend.pop_message().body


def test_callback_message_with_prefix_optional():
    dummy = DummyBackend({"BOT_PREFIX_OPTIONAL_ON_CHAT": True})
    m = makemessage(dummy, "return_args_as_str one two")
    dummy.callback_message(m)
    assert "one two" == dummy.pop_message().body

    # Groupchat should still require the prefix
    m.frm = TestOccupant("someone", "room")
    room = TestRoom("room", bot=dummy)
    m.to = room
    dummy.callback_message(m)

    with pytest.raises(Empty):
        dummy.pop_message(block=False)

    m = makemessage(
        dummy,
        "!return_args_as_str one two",
        from_=TestOccupant("someone", "room"),
        to=room,
    )
    dummy.callback_message(m)
    assert "one two" == dummy.pop_message().body


def test_callback_message_with_bot_alt_prefixes():
    dummy = DummyBackend(
        {"BOT_ALT_PREFIXES": ("Err",), "BOT_ALT_PREFIX_SEPARATORS": (",", ";")}
    )
    dummy.callback_message(makemessage(dummy, "Err return_args_as_str one two"))
    assert "one two" == dummy.pop_message().body
    dummy.callback_message(makemessage(dummy, "Err, return_args_as_str one two"))
    assert "one two" == dummy.pop_message().body


def test_callback_message_with_re_botcmd(dummy_backend):
    dummy_backend.callback_message(
        makemessage(dummy_backend, "!regex command with prefix")
    )
    assert "Regex command" == dummy_backend.pop_message().body
    dummy_backend.callback_message(
        makemessage(dummy_backend, "regex command without prefix")
    )
    assert "Regex command" == dummy_backend.pop_message().body
    dummy_backend.callback_message(
        makemessage(dummy_backend, "!regex command with capture group: Captured text")
    )
    assert "Captured text" == dummy_backend.pop_message().body
    dummy_backend.callback_message(
        makemessage(dummy_backend, "regex command with capture group: Captured text")
    )
    assert "Captured text" == dummy_backend.pop_message().body
    dummy_backend.callback_message(
        makemessage(
            dummy_backend,
            "This command also allows extra text in front - regex "
            "command with capture group: Captured text",
        )
    )
    assert "Captured text" == dummy_backend.pop_message().body


def test_callback_message_with_re_botcmd_and_alt_prefixes():
    dummy_backend = DummyBackend(
        {"BOT_ALT_PREFIXES": ("Err",), "BOT_ALT_PREFIX_SEPARATORS": (",", ";")}
    )
    dummy_backend.callback_message(
        makemessage(dummy_backend, "!regex command with prefix")
    )
    assert "Regex command" == dummy_backend.pop_message().body
    dummy_backend.callback_message(
        makemessage(dummy_backend, "Err regex command with prefix")
    )
    assert "Regex command" == dummy_backend.pop_message().body
    dummy_backend.callback_message(
        makemessage(dummy_backend, "Err, regex command with prefix")
    )
    assert "Regex command" == dummy_backend.pop_message().body
    dummy_backend.callback_message(
        makemessage(dummy_backend, "regex command without prefix")
    )
    assert "Regex command" == dummy_backend.pop_message().body
    dummy_backend.callback_message(
        makemessage(dummy_backend, "!regex command with capture group: Captured text")
    )
    assert "Captured text" == dummy_backend.pop_message().body
    dummy_backend.callback_message(
        makemessage(dummy_backend, "regex command with capture group: Captured text")
    )
    assert "Captured text" == dummy_backend.pop_message().body
    dummy_backend.callback_message(
        makemessage(
            dummy_backend,
            "This command also allows extra text in front - "
            "regex command with capture group: Captured text",
        )
    )
    assert "Captured text" == dummy_backend.pop_message().body
    dummy_backend.callback_message(
        makemessage(
            dummy_backend, "Err, regex command with capture group: Captured text"
        )
    )
    assert "Captured text" == dummy_backend.pop_message().body
    dummy_backend.callback_message(
        makemessage(
            dummy_backend,
            "Err This command also allows extra text in front - "
            "regex command with capture group: Captured text",
        )
    )
    assert "Captured text" == dummy_backend.pop_message().body
    dummy_backend.callback_message(makemessage(dummy_backend, "!match_here"))
    assert "1" == dummy_backend.pop_message().body
    dummy_backend.callback_message(
        makemessage(dummy_backend, "!match_here match_here match_here")
    )
    assert "3" == dummy_backend.pop_message().body


def test_regex_commands_can_overlap(dummy_backend):
    dummy_backend.callback_message(
        makemessage(dummy_backend, "!matched by two commands")
    )
    response = (dummy_backend.pop_message().body, dummy_backend.pop_message().body)
    assert response == ("one", "two") or response == ("two", "one")


def test_regex_commands_allow_passing_re_flags(dummy_backend):
    dummy_backend.callback_message(
        makemessage(dummy_backend, "!MaTcHeD By TwO cOmMaNdS")
    )
    assert "two" == dummy_backend.pop_message().body
    with pytest.raises(Empty):
        dummy_backend.pop_message(timeout=1)


def test_arg_botcmd_returns_first_name_last_name(dummy_backend):
    dummy_backend.callback_message(
        makemessage(
            dummy_backend,
            "!returns_first_name_last_name --first-name=Err --last-name=Bot",
        )
    )
    assert "Err Bot"


def test_arg_botcmd_returns_with_escaping(dummy_backend):
    first_name = 'Err\\"'
    last_name = "Bot"
    dummy_backend.callback_message(
        makemessage(
            dummy_backend,
            "!returns_first_name_last_name --first-name=%s --last-name=%s"
            % (first_name, last_name),
        )
    )
    assert 'Err" Bot' == dummy_backend.pop_message().body


def test_arg_botcmd_returns_with_incorrect_escaping(dummy_backend):
    first_name = 'Err"'
    last_name = "Bot"
    dummy_backend.callback_message(
        makemessage(
            dummy_backend,
            "!returns_first_name_last_name --first-name=%s --last-name=%s"
            % (first_name, last_name),
        )
    )
    assert (
        "I couldn't parse this command; No closing quotation"
        in dummy_backend.pop_message().body
    )


def test_arg_botcmd_yields_first_name_last_name(dummy_backend):
    dummy_backend.callback_message(
        makemessage(
            dummy_backend,
            "!yields_first_name_last_name --first-name=Err --last-name=Bot",
        )
    )
    assert "Err Bot" == dummy_backend.pop_message().body


def test_arg_botcmd_returns_value_repeated_count_times(dummy_backend):
    dummy_backend.callback_message(
        makemessage(dummy_backend, "!returns_value_repeated_count_times Foo --count 5")
    )
    assert "FooFooFooFooFoo" == dummy_backend.pop_message().body


def test_arg_botcmd_doesnt_raise_systemerror(dummy_backend):
    dummy_backend.callback_message(
        makemessage(dummy_backend, "!returns_first_name_last_name --invalid-parameter")
    )


def test_arg_botcdm_returns_errors_as_chat(dummy_backend):
    dummy_backend.callback_message(
        makemessage(dummy_backend, "!returns_first_name_last_name --invalid-parameter")
    )
    assert (
        "I couldn't parse the arguments; unrecognized arguments: --invalid-parameter"
        in dummy_backend.pop_message().body
    )


def test_arg_botcmd_returns_help_message_as_chat(dummy_backend):
    dummy_backend.callback_message(
        makemessage(dummy_backend, "!returns_first_name_last_name --help")
    )
    assert (
        "usage: returns_first_name_last_name [-h] [--last-name LAST_NAME]"
        in dummy_backend.pop_message().body
    )


def test_arg_botcmd_undoes_fancy_unicode_dash_conversion(dummy_backend):
    dummy_backend.callback_message(
        makemessage(
            dummy_backend,
            "!returns_first_name_last_name —first-name=Err —last-name=Bot",
        )
    )
    assert "Err Bot" == dummy_backend.pop_message().body


def test_arg_botcmd_without_argument_unpacking(dummy_backend):
    dummy_backend.callback_message(
        makemessage(
            dummy_backend,
            "!returns_first_name_last_name_without_unpacking --first-name=Err --last-name=Bot",
        )
    )
    assert "Err Bot" == dummy_backend.pop_message().body


def test_access_controls(dummy_backend):
    testroom = TestRoom("room", bot=dummy_backend)
    tests = [
        # BOT_ADMINS scenarios
        dict(
            message=makemessage(dummy_backend, "!admin_command"),
            bot_admins=("noterr",),
            expected_response="Admin command",
        ),
        dict(
            message=makemessage(dummy_backend, "!admin_command"),
            bot_admins=(),
            expected_response="This command requires bot-admin privileges",
        ),
        dict(
            message=makemessage(dummy_backend, "!admin_command"),
            bot_admins=("*err",),
            expected_response="Admin command",
        ),
        # admin_only commands SHOULD be private-message only by default
        dict(
            message=makemessage(
                dummy_backend,
                "!admin_command",
                from_=TestOccupant("noterr", room=testroom),
                to=testroom,
            ),
            bot_admins=("noterr",),
            expected_response="This command may only be issued through a direct message",
        ),
        # But MAY be sent via groupchat IF 'allowmuc' is specifically set to True.
        dict(
            message=makemessage(
                dummy_backend,
                "!admin_command",
                from_=TestOccupant("noterr", room=testroom),
                to=testroom,
            ),
            bot_admins=("noterr",),
            acl={"admin_command": {"allowmuc": True}},
            expected_response="Admin command",
        ),
        # ACCESS_CONTROLS scenarios WITHOUT wildcards (<4.0 format)
        dict(
            message=makemessage(dummy_backend, "!command"),
            expected_response="Regular command",
        ),
        dict(
            message=makemessage(dummy_backend, "!regex command with prefix"),
            expected_response="Regex command",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl_default={"allowmuc": False, "allowprivate": False},
            expected_response="You're not allowed to access this command via private message to me",
        ),
        dict(
            message=makemessage(dummy_backend, "regex command without prefix"),
            acl_default={"allowmuc": False, "allowprivate": False},
            expected_response="You're not allowed to access this command via private message to me",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl_default={"allowmuc": True, "allowprivate": False},
            expected_response="You're not allowed to access this command via private message to me",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl_default={"allowmuc": False, "allowprivate": True},
            expected_response="Regular command",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl={"command": {"allowprivate": False}},
            acl_default={"allowmuc": False, "allowprivate": True},
            expected_response="You're not allowed to access this command via private message to me",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl={"command": {"allowmuc": True}},
            acl_default={"allowmuc": True, "allowprivate": False},
            expected_response="You're not allowed to access this command via private message to me",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl={"command": {"allowprivate": True}},
            acl_default={"allowmuc": False, "allowprivate": False},
            expected_response="Regular command",
        ),
        dict(
            message=makemessage(
                dummy_backend,
                "!command",
                from_=TestOccupant("someone", "room"),
                to=TestRoom("room", bot=dummy_backend),
            ),
            acl={"command": {"allowrooms": ("room",)}},
            expected_response="Regular command",
        ),
        dict(
            message=makemessage(
                dummy_backend,
                "!command",
                from_=TestOccupant("someone", "room_1"),
                to=TestRoom("room1", bot=dummy_backend),
            ),
            acl={"command": {"allowrooms": ("room_*",)}},
            expected_response="Regular command",
        ),
        dict(
            message=makemessage(
                dummy_backend,
                "!command",
                from_=TestOccupant("someone", "room"),
                to=TestRoom("room", bot=dummy_backend),
            ),
            acl={"command": {"allowrooms": ("anotherroom@localhost",)}},
            expected_response="You're not allowed to access this command from this room",
        ),
        dict(
            message=makemessage(
                dummy_backend,
                "!command",
                from_=TestOccupant("someone", "room"),
                to=TestRoom("room", bot=dummy_backend),
            ),
            acl={"command": {"denyrooms": ("room",)}},
            expected_response="You're not allowed to access this command from this room",
        ),
        dict(
            message=makemessage(
                dummy_backend,
                "!command",
                from_=TestOccupant("someone", "room"),
                to=TestRoom("room", bot=dummy_backend),
            ),
            acl={"command": {"denyrooms": ("*",)}},
            expected_response="You're not allowed to access this command from this room",
        ),
        dict(
            message=makemessage(
                dummy_backend,
                "!command",
                from_=TestOccupant("someone", "room"),
                to=TestRoom("room", bot=dummy_backend),
            ),
            acl={"command": {"denyrooms": ("anotherroom",)}},
            expected_response="Regular command",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl={"command": {"allowusers": ("noterr",)}},
            expected_response="Regular command",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl={"command": {"allowusers": "noterr"}},  # simple string instead of tuple
            expected_response="Regular command",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl={"command": {"allowusers": ("err",)}},
            expected_response="You're not allowed to access this command from this user",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl={"command": {"allowusers": ("*err",)}},
            expected_response="Regular command",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl={"command": {"denyusers": ("err",)}},
            expected_response="Regular command",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl={"command": {"denyusers": ("noterr",)}},
            expected_response="You're not allowed to access this command from this user",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl={"command": {"denyusers": "noterr"}},  # simple string instead of tuple
            expected_response="You're not allowed to access this command from this user",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl={"command": {"denyusers": ("*err",)}},
            expected_response="You're not allowed to access this command from this user",
        ),
        dict(
            message=makemessage(dummy_backend, "!command echo"),
            acl={"command": {"allowargs": ("echo",)}},
            expected_response="Regular command",
        ),
        dict(
            message=makemessage(dummy_backend, "!command notallowed"),
            acl={"command": {"allowargs": ("echo",)}},
            expected_response="You're not allowed to access this command using the provided arguments",
        ),
        dict(
            message=makemessage(dummy_backend, "!command echodeny"),
            acl={"command": {"denyargs": ("echodeny",)}},
            expected_response="You're not allowed to access this command using the provided arguments",
        ),
        dict(
            message=makemessage(dummy_backend, "!command echo"),
            acl={"command": {"denyargs": ("echodeny",)}},
            expected_response="Regular command",
        ),
        # ACCESS_CONTROLS scenarios WITH wildcards (>=4.0 format)
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl={"DummyBackendRealName:command": {"denyusers": ("noterr",)}},
            expected_response="You're not allowed to access this command from this user",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl={"*:command": {"denyusers": ("noterr",)}},
            expected_response="You're not allowed to access this command from this user",
        ),
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl={"DummyBackendRealName:*": {"denyusers": ("noterr",)}},
            expected_response="You're not allowed to access this command from this user",
        ),
        dict(
            message=makemessage(dummy_backend, "!command echo"),
            acl={"command": {"allowargs": ("ec*",)}},
            expected_response="Regular command",
        ),
        dict(
            message=makemessage(dummy_backend, "!command notallowed"),
            acl={"command": {"allowargs": ("e*",)}},
            expected_response="You're not allowed to access this command using the provided arguments",
        ),
        dict(
            message=makemessage(dummy_backend, "!command denied"),
            acl={"command": {"denyargs": ("den*",)}},
            expected_response="You're not allowed to access this command using the provided arguments",
        ),
        # Overlapping globs should use first match
        dict(
            message=makemessage(dummy_backend, "!command"),
            acl=OrderedDict(
                [
                    ("DummyBackendRealName:*", {"denyusers": ("noterr",)}),
                    ("DummyBackendRealName:command", {"denyusers": ()}),
                ]
            ),
            expected_response="You're not allowed to access this command from this user",
        ),
        # ACCESS_CONTROLS with numeric username as in telegram
        dict(
            message=makemessage(
                dummy_backend, "!command", from_=dummy_backend.build_identifier(1234)
            ),
            acl={"command": {"allowusers": (1234,)}},
            expected_response="Regular command",
        ),
    ]

    for test in tests:
        dummy_backend.bot_config.ACCESS_CONTROLS_DEFAULT = test.get("acl_default", {})
        dummy_backend.bot_config.ACCESS_CONTROLS = test.get("acl", {})
        dummy_backend.bot_config.BOT_ADMINS = test.get("bot_admins", ())
        logger = logging.getLogger(__name__)
        logger.info("** message: {}".format(test["message"].body))
        logger.info("** bot_admins: {}".format(dummy_backend.bot_config.BOT_ADMINS))
        logger.info("** acl: {!r}".format(dummy_backend.bot_config.ACCESS_CONTROLS))
        logger.info(
            "** acl_default: {!r}".format(
                dummy_backend.bot_config.ACCESS_CONTROLS_DEFAULT
            )
        )
        dummy_backend.callback_message(test["message"])
        assert test["expected_response"] == dummy_backend.pop_message().body
