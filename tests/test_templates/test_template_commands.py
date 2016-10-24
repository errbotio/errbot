from os import path
from errbot.backends.test import testbot

# This is to test end2end i18n behavior.

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), '..', 'template_plugin')


def test_templates_1(testbot):
    assert 'ok' in testbot.exec_command('!test template1')


def test_templates_2(testbot):
    assert 'ok' in testbot.exec_command('!test template2')
