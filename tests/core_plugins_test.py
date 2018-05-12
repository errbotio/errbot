import os

extra_plugin_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "room_plugin")
extra_config = {
    "CORE_PLUGINS": ("Help", "Utils", "CommandNotFoundFilter"), "BOT_ALT_PREFIXES": ("!",), "BOT_PREFIX": "$"
}


def test_help_is_still_here(testbot):
    assert "All commands" in testbot.exec_command("!help")


def test_backup_help_not_here(testbot):
    assert "That command is not defined." in testbot.exec_command("!help backup")


def test_backup_should_not_be_there(testbot):
    assert 'Command "backup" not found.' in testbot.exec_command("!backup")


def test_echo_still_here(testbot):
    assert "toto" in testbot.exec_command("!echo toto")


def test_bot_prefix_replaced(testbot):
    assert "$help - Returns a help string" in testbot.exec_command("$help")
