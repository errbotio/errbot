from os import path
from errbot.backends.test import testbot

# This is to test the pytestfixtures pattern.

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), 'dummy_plugin')


def test_push_pull(testbot):
    testbot.push_message('!about')
    assert "Err version" in testbot.pop_message()


def test_assertCommand(testbot):
    testbot.assertCommand('!about', 'Err version')


def test_extra_plugin_dir(testbot):
    testbot.assertCommand('!foo', 'bar')
