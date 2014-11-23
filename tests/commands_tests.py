# coding=utf-8
from ast import literal_eval

# create a mock configuration
from errbot.backends.test import FullStackTest, push_message, pop_message
from queue import Empty


class TestCommands(FullStackTest):
    def test_root_help(self):
        push_message('!help')
        self.assertIn('Available help', pop_message())

    def test_help(self):
        push_message('!help ErrBot')
        response = pop_message()
        self.assertIn('Available commands for ErrBot', response)
        self.assertIn('!about', response)

        push_message('!help beurk')
        self.assertEqual('That command is not defined.', pop_message())

    def test_about(self):
        push_message('!about')
        self.assertIn('Err version', pop_message())

    def test_uptime(self):
        push_message('!uptime')
        self.assertIn('I\'ve been up for', pop_message())

    def test_status(self):
        push_message('!status')
        self.assertIn('Yes I am alive', pop_message())

    def test_status_plugins(self):
        push_message('!status plugins')
        self.assertIn('L=Loaded, U=Unloaded', pop_message())

    def test_status_load(self):
        push_message('!status load')
        self.assertIn('Load ', pop_message())

    def test_status_gc(self):
        push_message('!status gc')
        self.assertIn('GC 0->', pop_message())

    def test_config_cycle(self):
        # test the full configuration cycle help, get set and export, import
        push_message('!zap configs')
        self.assertIn('Done', pop_message())

        push_message('!config Webserver')
        m = pop_message()
        self.assertIn('Default configuration for this plugin (you can copy and paste this directly as a command)', m)
        self.assertNotIn('Current configuration', m)

        push_message("!config Webserver {'HOST': 'localhost', 'PORT': 3141, 'SSL':  None}")
        self.assertIn('Plugin configuration done.', pop_message())

        push_message('!config Webserver')
        m = pop_message()
        self.assertIn('Current configuration', m)
        self.assertIn('localhost', m)

        push_message('!export configs')
        configs = pop_message()
        self.assertIn('localhost', configs)
        obj = literal_eval(configs)  # be sure it is parseable
        obj['Webserver']['HOST'] = 'localhost'

        push_message('!import configs ' + repr(obj))
        self.assertIn('Import is done correctly', pop_message())

        push_message('!config Webserver')
        self.assertIn('localhost', pop_message())

    def test_apropos(self):
        push_message('!apropos about')
        self.assertIn('!about: Returns some', pop_message())

    def test_logtail(self):
        push_message('!log tail')
        self.assertIn('DEBUG', pop_message())

    def test_history(self):
        from errbot.holder import bot

        push_message('!uptime')
        pop_message()
        push_message('!history')
        self.assertIn('uptime', pop_message())

        orig_sender = bot.sender
        try:
            # Pretend to be someone else. History should be empty
            bot.sender = 'non_default_person@localhost'
            push_message('!history')
            self.assertRaises(Empty, pop_message, block=False)
            push_message('!echo should be seperate history')
            pop_message()
            push_message('!history')
            self.assertIn('should be seperate history', pop_message())
        finally:
            bot.sender = orig_sender
        # Pretend to be the original person again. History should still contain uptime
        push_message('!history')
        self.assertIn('uptime', pop_message())

    def test_plugin_cycle(self):
        push_message('!repos install git://github.com/gbin/err-helloworld.git')
        self.assertIn('err-helloworld', pop_message(timeout=60))
        self.assertIn('reload', pop_message())

        push_message('!repos export')  # should appear in the export
        self.assertEqual("{'err-helloworld': 'git://github.com/gbin/err-helloworld.git'}", pop_message())

        push_message('!help hello')  # should appear in the help
        self.assertEqual("this command says hello", pop_message())

        push_message('!hello')  # should respond
        self.assertEqual('Hello World !', pop_message())

        push_message('!reload HelloWorld')
        self.assertEqual('Plugin HelloWorld deactivated', pop_message())
        self.assertEqual('Plugin HelloWorld activated', pop_message())

        push_message('!hello')  # should still respond
        self.assertEqual('Hello World !', pop_message())

        push_message('!blacklist HelloWorld')
        self.assertEqual('Plugin HelloWorld is now blacklisted', pop_message())
        push_message('!unload HelloWorld')
        self.assertEqual('Plugin HelloWorld deactivated', pop_message())

        push_message('!hello')  # should not respond
        self.assertIn('Command "hello" not found', pop_message())

        push_message('!unblacklist HelloWorld')
        self.assertEqual('Plugin HelloWorld removed from blacklist', pop_message())
        push_message('!load HelloWorld')
        self.assertEqual('Plugin HelloWorld activated', pop_message())

        push_message('!hello')  # should respond back
        self.assertEqual('Hello World !', pop_message())

        push_message('!repos uninstall err-helloworld')
        self.assertEqual('/me is unloading plugin HelloWorld', pop_message())
        self.assertEqual('Plugins unloaded and repo err-helloworld removed', pop_message())

        push_message('!hello')  # should not respond
        self.assertIn('Command "hello" not found', pop_message())

    def test_encoding_preservation(self):
        push_message('!echo へようこそ')
        self.assertEquals('へようこそ', pop_message())

    def test_webserver_webhook_test(self):
        push_message("!config Webserver {'HOST': 'localhost', 'PORT': 3141, 'SSL':  None}")
        self.assertIn('Plugin configuration done.', pop_message())
        self.assertCommand("!webhook test /echo/ toto", 'Status code : 200')

    def test_load_reload_and_unload(self):
        for command in ('load', 'reload', 'unload'):
            push_message("!{}".format(command))
            m = pop_message()
            self.assertIn('Please tell me which of the following plugins to reload', m)
            self.assertIn('ChatRoom', m)

            push_message('!{} nosuchplugin'.format(command))
            m = pop_message()
            self.assertIn("nosuchplugin isn't a valid plugin name. The current plugins are", m)
            self.assertIn('ChatRoom', m)

        push_message('!reload ChatRoom')
        self.assertEqual('Plugin ChatRoom deactivated', pop_message())
        self.assertEqual('Plugin ChatRoom activated', pop_message())

        push_message("!status plugins")
        self.assertIn("[L] ChatRoom", pop_message())

        push_message('!unload ChatRoom')
        self.assertEqual('Plugin ChatRoom deactivated', pop_message())

        push_message("!status plugins")
        self.assertIn("[U] ChatRoom", pop_message())

        push_message('!unload ChatRoom')
        self.assertEqual('ChatRoom is not currently loaded', pop_message())

        push_message('!load ChatRoom')
        self.assertEqual('Plugin ChatRoom activated', pop_message())

        push_message("!status plugins")
        self.assertIn("[L] ChatRoom", pop_message())

        push_message('!load ChatRoom')
        self.assertEqual('ChatRoom is already loaded', pop_message())

        push_message('!unload ChatRoom')
        self.assertEqual('Plugin ChatRoom deactivated', pop_message())
        push_message('!reload ChatRoom')
        self.assertEqual('Plugin ChatRoom not in active list', pop_message())
        self.assertEqual('Plugin ChatRoom activated', pop_message())

        push_message('!blacklist ChatRoom')
        self.assertEqual("Plugin ChatRoom is now blacklisted", pop_message())

        push_message("!status plugins")
        self.assertIn("[BL] ChatRoom", pop_message())

        # Needed else configuration for this plugin gets saved which screws up
        # other tests
        push_message('!unblacklist ChatRoom')
        pop_message()

    def test_unblacklist_and_blacklist(self):
        push_message('!unblacklist nosuchplugin')
        m = pop_message()
        self.assertIn("nosuchplugin isn't a valid plugin name. The current plugins are", m)
        self.assertIn('ChatRoom', m)

        push_message('!blacklist nosuchplugin')
        m = pop_message()
        self.assertIn("nosuchplugin isn't a valid plugin name. The current plugins are", m)
        self.assertIn('ChatRoom', m)

        push_message('!blacklist ChatRoom')
        self.assertEqual("Plugin ChatRoom is now blacklisted", pop_message())

        push_message('!blacklist ChatRoom')
        self.assertEqual("Plugin ChatRoom is already blacklisted", pop_message())

        push_message("!status plugins")
        self.assertIn("[BL] ChatRoom", pop_message())

        push_message('!unblacklist ChatRoom')
        self.assertEqual('Plugin ChatRoom removed from blacklist', pop_message())

        push_message('!unblacklist ChatRoom')
        self.assertEqual('Plugin ChatRoom is not blacklisted', pop_message())

        push_message("!status plugins")
        self.assertIn("[L] ChatRoom", pop_message())
