from os import path
from errbot.backends.test import testbot

# This is to test end2end i18n behavior.

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), 'i18n_plugin')


def test_i18n_return(testbot):
    testbot.assertCommand('!i18n 1', 'язы́к')


def test_i18n_simple_name(testbot):
    testbot.assertCommand('!ру́сский', 'OK')


def test_i18n_prefix(testbot):
    testbot.assertCommand('!prefix_ру́сский', 'OK')
    testbot.assertCommand('!prefix ру́сский', 'OK')


def test_i18n_suffix(testbot):
    testbot.assertCommand('!ру́сский_suffix', 'OK')
    testbot.assertCommand('!ру́сский suffix', 'OK')
