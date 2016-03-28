# coding=utf-8
import re
import logging
from errbot.backends.test import FullStackTest
from flaky import flaky
from os import path, mkdir
from queue import Empty
from shutil import rmtree


@flaky
class TestCommands(FullStackTest):

    def setUp(self, *args, **kwargs):
        kwargs['extra_plugin_dir'] = path.join(path.dirname(
            path.realpath(__file__)), 'syntax_plugin')

        super().setUp(*args, **kwargs)

    def test_nosyntax(self):
        self.assertIsNone(self.bot.commands['foo_nosyntax']._err_command_syntax)

    def test_syntax(self):
        self.assertEquals(self.bot.commands['foo']._err_command_syntax, '[optional] <mandatory>')

    def test_re_syntax(self):
        self.assertEquals(self.bot.re_commands['re_foo']._err_command_syntax, '.*')

    def test_arg_syntax(self):
        self.assertEquals(self.bot.commands['arg_foo']._err_command_syntax, '[-h] [--repeat-count REPEAT] value')
