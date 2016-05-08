import os

from errbot.backends.test import testbot  # noqa

extra_plugin_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'room_tests')
extra_config = {'CORE_PLUGINS': ('Help', 'Utils')}


def test_help_is_still_here(testbot):
    assert 'All commands' in testbot.exec_command('!help')


def test_backup_help_not_here(testbot):
    assert 'That command is not defined.' in testbot.exec_command('!help backup')


def test_backup_should_not_be_there(testbot):
    assert 'Command "backup" not found.' in testbot.exec_command('!backup')


def test_echo_still_here(testbot):
    assert 'toto' in testbot.exec_command('!echo toto')
