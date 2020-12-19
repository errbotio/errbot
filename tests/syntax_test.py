from os import path

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), "syntax_plugin")


def test_nosyntax(testbot):
    assert testbot.bot.commands["foo_nosyntax"]._err_command_syntax is None


def test_syntax(testbot):
    assert testbot.bot.commands["foo"]._err_command_syntax == "[optional] <mandatory>"


def test_re_syntax(testbot):
    assert testbot.bot.re_commands["re_foo"]._err_command_syntax == ".*"


def test_arg_syntax(testbot):
    assert (
        testbot.bot.commands["arg_foo"]._err_command_syntax
        == "[-h] [--repeat-count REPEAT] value"
    )
