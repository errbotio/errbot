# -*- coding=utf-8 -*-
from os import path
# This is to test end2end i18n behavior.

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), 'i18n_plugin')


def test_i18n_return(testbot):
    assert 'язы́к' in testbot.exec_command('!i18n 1')


def test_i18n_simple_name(testbot):
    assert 'OK' in testbot.exec_command('!ру́сский')


def test_i18n_prefix(testbot):
    assert 'OK' in testbot.exec_command('!prefix_ру́сский')
    assert 'OK' in testbot.exec_command('!prefix ру́сский')


def test_i18n_suffix(testbot):
    assert 'OK' in testbot.exec_command('!ру́сский_suffix')
    assert 'OK' in testbot.exec_command('!ру́сский suffix')
