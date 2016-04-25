# coding=utf-8
from errbot.backends.test import FullStackTest
from flaky import flaky
from os import path


@flaky
class TestDynaPlugins(FullStackTest):

    def setUp(self, *args, **kwargs):
        kwargs['extra_plugin_dir'] = path.join(path.dirname(
            path.realpath(__file__)), 'dyna_plugin')

        super().setUp(*args, **kwargs)

    def test_simple(self):
        self.assertCommand('!add_simple', 'added')
        self.assertCommand('!say_yep', 'yep')
        self.assertCommand('!say_foo', 'foo')
        self.assertCommand('!help', 'documented')
        self.assertCommand('!remove_simple', 'removed')
        self.assertCommand('!say_foo', 'Command "say_foo" not found')

    def test_re(self):
        self.assertCommand('!add_re', 'added')
        self.assertCommand('I said cheese', 'fffound')
        self.assertCommand('!remove_re', 'removed')

    def test_saw(self):
        self.assertCommand('!add_saw', 'added')
        self.assertCommand('!splitme foo,bar,baz', 'foo+bar+baz')
        self.assertCommand('!remove_saw', 'removed')

    def test_clashing(self):
        self.assertCommand('!clash', 'original')
        self.assertCommand('!add_clashing',
                           'clashing.clash clashes with Dyna.clash so it has been renamed clashing-clash')
        self.assertIn('added', self.bot.pop_message())
        self.assertCommand('!clash', 'original')
        self.assertCommand('!clashing-clash', 'dynamic')
        self.assertCommand('!remove_clashing', 'removed')
        self.assertCommand('!clash', 'original')
        self.assertCommand('!clashing-clash', 'not found')
