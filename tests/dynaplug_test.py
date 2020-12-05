from os import path

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), "dyna_plugin")


def test_simple(testbot):
    assert "added" in testbot.exec_command("!add_simple")
    assert "yep" in testbot.exec_command("!say_yep")
    assert "foo" in testbot.exec_command("!say_foo")
    assert "documented" in testbot.exec_command("!help")
    assert "removed" in testbot.exec_command("!remove_simple")
    assert 'Command "say_foo" not found' in testbot.exec_command("!say_foo")


def test_arg(testbot):
    assert "added" in testbot.exec_command("!add_arg")
    assert "string to echo is string_to_echo" in testbot.exec_command(
        "!echo_to_me string_to_echo"
    )
    assert "removed" in testbot.exec_command("!remove_arg")
    assert (
        'Command "echo_to_me" / "echo_to_me string_to_echo" not found'
        in testbot.exec_command("!echo_to_me string_to_echo")
    )


def test_re(testbot):
    assert "added" in testbot.exec_command("!add_re")
    assert "fffound" in testbot.exec_command("I said cheese")
    assert "removed" in testbot.exec_command("!remove_re")


def test_saw(testbot):
    assert "added" in testbot.exec_command("!add_saw")
    assert "foo+bar+baz" in testbot.exec_command("!splitme foo,bar,baz")
    assert "removed" in testbot.exec_command("!remove_saw")


def test_clashing(testbot):
    assert "original" in testbot.exec_command("!clash")
    assert (
        "clashing.clash clashes with Dyna.clash so it has been renamed clashing-clash"
        in testbot.exec_command("!add_clashing")
    )
    assert "added" in testbot.pop_message()
    assert "original" in testbot.exec_command("!clash")
    assert "dynamic" in testbot.exec_command("!clashing-clash")
    assert "removed" in testbot.exec_command("!remove_clashing")
    assert "original" in testbot.exec_command("!clash")
    assert "not found" in testbot.exec_command("!clashing-clash")
