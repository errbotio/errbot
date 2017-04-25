# coding=utf-8
from os import path

import pytest

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), 'matchall_plugin')


def test_botmatch_correct(testbot):
    assert 'Works!' in testbot.exec_command('hi hi hi')


def test_botmatch(testbot):
    assert 'Works!' in testbot.exec_command('123123')
