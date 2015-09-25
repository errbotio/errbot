# coding=utf-8
from queue import Empty
import re
import logging

from os import path, mkdir
from shutil import rmtree
from errbot.backends.test import FullStackTest


class TestCommands(FullStackTest):
    def test_root_help(self):
        self.assertCommand('!help', 'Available help')

    def test_help(self):
        self.assertCommand('!help Help', '!about')
        self.assertCommand('!help beurk', 'That command is not defined.')

    def test_about(self):
        self.assertCommand('!about', 'Err version')

    def test_uptime(self):
        self.assertCommand('!uptime', 'I\'ve been up for')

    def test_status(self):
        self.assertCommand('!status', 'Yes I am alive')

    def test_status_plugins(self):
        self.assertCommand('!status plugins', 'A = Activated, D = Deactivated')

    def test_status_load(self):
        self.assertCommand('!status load', 'Load ')

    def test_whoami(self):
        self.assertCommand('!whoami', 'person')
        self.assertCommand('!whoami', 'gbin@localhost')

    def test_echo(self):
        self.assertCommand('!echo foo', 'foo')

    def test_status_gc(self):
        self.assertCommand('!status gc', 'GC 0->')

    def test_config_cycle(self):
        self.bot.push_message('!plugin config Webserver')
        m = self.bot.pop_message()
        self.assertIn('Default configuration for this plugin (you can copy and paste this directly as a command)', m)
        self.assertNotIn('Current configuration', m)

        self.assertCommand("!plugin config Webserver {'HOST': 'localhost', 'PORT': 3141, 'SSL':  None}",
                           'Plugin configuration done.')

        self.assertCommand('!plugin config Webserver', 'Current configuration')
        self.assertCommand('!plugin config Webserver', 'localhost')

    def test_apropos(self):
        self.assertCommand('!apropos about', '!about: Returns some')

    def test_logtail(self):
        self.assertCommand('!log tail', 'DEBUG')

    def test_history(self):
        self.assertCommand('!uptime', 'up')
        self.assertCommand('!history', 'uptime')

        orig_sender = self.bot.sender
        try:
            # Pretend to be someone else. History should be empty
            self.bot.sender = self.bot.build_identifier('non_default_person')
            self.bot.push_message('!history')
            self.assertRaises(Empty, self.bot.pop_message, block=False)
            self.bot.push_message('!echo should be a separate history')
            self.bot.pop_message()
            self.assertCommand('!history', 'should be a separate history')
        finally:
            self.bot.sender = orig_sender
        # Pretend to be the original person again. History should still contain uptime
        self.assertCommand('!history', 'uptime')

    def test_plugin_cycle(self):
        self.assertCommand('!repos install git://github.com/gbin/err-helloworld.git',
                           'err-helloworld',
                           60)
        self.assertIn('reload', self.bot.pop_message())

        self.assertCommand('!help hello', 'this command says hello')
        self.assertCommand('!hello', 'Hello World !')

        self.bot.push_message('!plugin reload HelloWorld')
        self.assertEqual('Plugin HelloWorld reloaded.', self.bot.pop_message())

        self.bot.push_message('!hello')  # should still respond
        self.assertEqual('Hello World !', self.bot.pop_message())

        self.bot.push_message('!plugin blacklist HelloWorld')
        self.assertEqual('Plugin HelloWorld is now blacklisted', self.bot.pop_message())
        self.bot.push_message('!plugin deactivate HelloWorld')
        self.assertEqual('Plugin HelloWorld deactivated.', self.bot.pop_message())

        self.bot.push_message('!hello')  # should not respond
        self.assertIn('Command "hello" not found', self.bot.pop_message())

        self.bot.push_message('!plugin unblacklist HelloWorld')
        self.assertEqual('Plugin HelloWorld removed from blacklist', self.bot.pop_message())
        self.bot.push_message('!plugin activate HelloWorld')
        self.assertEqual('Plugin HelloWorld activated.', self.bot.pop_message())

        self.bot.push_message('!hello')  # should respond back
        self.assertEqual('Hello World !', self.bot.pop_message())

        self.bot.push_message('!repos uninstall err-helloworld')
        self.assertEqual('/me is unloading plugin HelloWorld', self.bot.pop_message())
        self.assertEqual('Plugins unloaded and repo err-helloworld removed', self.bot.pop_message())

        self.bot.push_message('!hello')  # should not respond
        self.assertIn('Command "hello" not found', self.bot.pop_message())

    def test_backup(self):
        self.bot.push_message('!repos install git://github.com/gbin/err-helloworld.git')
        self.assertIn('err-helloworld', self.bot.pop_message(timeout=60))
        self.assertIn('reload', self.bot.pop_message())
        self.bot.push_message('!backup')
        msg = self.bot.pop_message()
        self.assertIn('has been written in', msg)
        filename = re.search(r"'([A-Za-z0-9_\./\\-]*)'", msg).group(1)

        # At least the backup should mention the installed plugin
        self.assertIn('err-helloworld', open(filename).read())

        # Now try to clean the bot and restore
        plugins_dir = path.join(self.bot.bot_config.BOT_DATA_DIR, 'plugins')
        rmtree(plugins_dir)
        mkdir(plugins_dir)
        self.bot['repos'] = {}
        self.bot['configs'] = {}

        # emulates the restore environment
        log = logging.getLogger(__name__)  # noqa
        bot = self.bot  # noqa
        with open(filename) as f:
            exec(f.read())
        self.assertCommand('!hello', 'Hello World !')
        self.bot.push_message('!repos uninstall err-helloworld')

    def test_encoding_preservation(self):
        self.bot.push_message('!echo へようこそ')
        self.assertEquals('へようこそ', self.bot.pop_message())

    def test_webserver_webhook_test(self):
        self.bot.push_message("!plugin config Webserver {'HOST': 'localhost', 'PORT': 3141, 'SSL':  None}")
        self.assertIn('Plugin configuration done.', self.bot.pop_message())
        self.assertCommand("!webhook test /echo/ toto", 'Status code : 200')

    def test_activate_reload_and_deactivate(self):
        for command in ('activate', 'reload', 'deactivate'):
            self.bot.push_message("!plugin {}".format(command))
            m = self.bot.pop_message()
            self.assertIn('Please tell me which of the following plugins to', m)
            self.assertIn('ChatRoom', m)

            self.bot.push_message('!plugin {} nosuchplugin'.format(command))
            m = self.bot.pop_message()
            self.assertIn("nosuchplugin isn't a valid plugin name. The current plugins are", m)
            self.assertIn('ChatRoom', m)

        self.bot.push_message('!plugin reload ChatRoom')
        self.assertEqual('Plugin ChatRoom reloaded.', self.bot.pop_message())

        self.bot.push_message("!status plugins")
        self.assertIn("A      │ ChatRoom", self.bot.pop_message())

        self.bot.push_message('!plugin deactivate ChatRoom')
        self.assertEqual('Plugin ChatRoom deactivated.', self.bot.pop_message())

        self.bot.push_message("!status plugins")
        self.assertIn("D      │ ChatRoom", self.bot.pop_message())

        self.bot.push_message('!plugin deactivate ChatRoom')
        self.assertEqual('ChatRoom is already deactivated.', self.bot.pop_message())

        self.bot.push_message('!plugin activate ChatRoom')
        self.assertEqual('Plugin ChatRoom activated.', self.bot.pop_message())

        self.bot.push_message("!status plugins")
        self.assertIn("A      │ ChatRoom", self.bot.pop_message())

        self.bot.push_message('!plugin activate ChatRoom')
        self.assertEqual('ChatRoom is already activated.', self.bot.pop_message())

        self.bot.push_message('!plugin deactivate ChatRoom')
        self.assertEqual('Plugin ChatRoom deactivated.', self.bot.pop_message())
        self.bot.push_message('!plugin reload ChatRoom')
        self.assertEqual('Warning: plugin ChatRoom is currently not activated. ' +
                         'Use !plugin activate ChatRoom to activate it.',
                         self.bot.pop_message())
        self.assertEqual('Plugin ChatRoom reloaded.', self.bot.pop_message())

        self.bot.push_message('!plugin blacklist ChatRoom')
        self.assertEqual("Plugin ChatRoom is now blacklisted", self.bot.pop_message())

        self.bot.push_message("!status plugins")
        self.assertIn("B,D    │ ChatRoom", self.bot.pop_message())

        # Needed else configuration for this plugin gets saved which screws up
        # other tests
        self.bot.push_message('!plugin unblacklist ChatRoom')
        self.bot.pop_message()

    def test_unblacklist_and_blacklist(self):
        self.bot.push_message('!plugin unblacklist nosuchplugin')
        m = self.bot.pop_message()
        self.assertIn("nosuchplugin isn't a valid plugin name. The current plugins are", m)
        self.assertIn('ChatRoom', m)

        self.bot.push_message('!plugin blacklist nosuchplugin')
        m = self.bot.pop_message()
        self.assertIn("nosuchplugin isn't a valid plugin name. The current plugins are", m)
        self.assertIn('ChatRoom', m)

        self.bot.push_message('!plugin blacklist ChatRoom')
        self.assertEqual("Plugin ChatRoom is now blacklisted", self.bot.pop_message())

        self.bot.push_message('!plugin blacklist ChatRoom')
        self.assertEqual("Plugin ChatRoom is already blacklisted", self.bot.pop_message())

        self.bot.push_message("!status plugins")
        self.assertIn("B,A    │ ChatRoom", self.bot.pop_message())

        self.bot.push_message('!plugin unblacklist ChatRoom')
        self.assertEqual('Plugin ChatRoom removed from blacklist', self.bot.pop_message())

        self.bot.push_message('!plugin unblacklist ChatRoom')
        self.assertEqual('Plugin ChatRoom is not blacklisted', self.bot.pop_message())

        self.bot.push_message("!status plugins")
        self.assertIn("A      │ ChatRoom", self.bot.pop_message())
