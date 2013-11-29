# coding=utf-8
from ast import literal_eval

# create a mock configuration
from errbot.backends.test import FullStackTest, pushMessage, popMessage
from queue import Empty

class TestCommands(FullStackTest):

    def test_root_help(self):
        pushMessage('!help')
        self.assertIn('Available help', popMessage())

    def test_help(self):
        pushMessage('!help ErrBot')
        response = popMessage()
        self.assertIn('Available commands for ErrBot', response)
        self.assertIn('!about', response)

        pushMessage('!help beurk')
        self.assertEqual('That command is not defined.', popMessage())

    def test_about(self):
        pushMessage('!about')
        self.assertIn('Err version', popMessage())

    def test_uptime(self):
        pushMessage('!uptime')
        self.assertIn('I\'ve been up for', popMessage())

    def test_status(self):
        pushMessage('!status')
        self.assertIn('Yes I am alive', popMessage())

    def test_config_cycle(self):
        # test the full configuration cycle help, get set and export, import
        pushMessage('!zap configs')
        self.assertIn('Done', popMessage())

        pushMessage('!config Webserver')
        self.assertIn('Copy paste and adapt', popMessage())

        pushMessage("!config Webserver {'HOST': 'localhost', 'PORT': 3141, 'SSL':  None}")
        self.assertIn('Plugin configuration done.', popMessage())

        pushMessage('!config Webserver')
        self.assertIn('localhost', popMessage())

        pushMessage('!export configs')
        configs = popMessage()
        self.assertIn('localhost', configs)
        obj = literal_eval(configs)  # be sure it is parseable
        obj['Webserver']['HOST'] = 'localhost'

        pushMessage('!import configs ' + repr(obj))
        self.assertIn('Import is done correctly', popMessage())

        pushMessage('!config Webserver')
        self.assertIn('localhost', popMessage())

    def test_apropos(self):
        pushMessage('!apropos about')
        self.assertIn('!about: Returns some', popMessage())

    def test_logtail(self):
        pushMessage('!log tail')
        self.assertIn('DEBUG', popMessage())

    def test_history(self):
        from errbot.holder import bot

        pushMessage('!uptime')
        popMessage()
        pushMessage('!history')
        self.assertIn('uptime', popMessage())

        orig_sender = bot.sender
        try:
            # Pretend to be someone else. History should be empty
            bot.sender = 'non_default_person@localhost'
            pushMessage('!history')
            self.assertRaises(Empty, popMessage, block=False)
            pushMessage('!echo should be seperate history')
            popMessage()
            pushMessage('!history')
            self.assertIn('should be seperate history', popMessage())
        finally:
            bot.sender = orig_sender
        # Pretend to be the original person again. History should still contain uptime
        pushMessage('!history')
        self.assertIn('uptime', popMessage())

    def test_plugin_cycle(self):
        pushMessage('!repos install git://github.com/gbin/err-helloworld.git')
        self.assertIn('err-helloworld', popMessage())
        self.assertIn('reload', popMessage())

        pushMessage('!repos export')  # should appear in the export
        self.assertEqual("{'err-helloworld': 'git://github.com/gbin/err-helloworld.git'}", popMessage())

        pushMessage('!help hello')  # should appear in the help
        self.assertEqual("this command says hello", popMessage())

        pushMessage('!hello')  # should respond
        self.assertEqual('Hello World !', popMessage())

        pushMessage('!reload HelloWorld')
        self.assertEqual('Plugin HelloWorld deactivated', popMessage())
        self.assertEqual('Plugin HelloWorld activated', popMessage())

        pushMessage('!hello')  # should still respond
        self.assertEqual('Hello World !', popMessage())

        pushMessage('!unload HelloWorld')
        self.assertEqual('Plugin HelloWorld deactivated', popMessage())

        pushMessage('!hello')  # should not respond
        self.assertIn('Command "hello" not found', popMessage())

        pushMessage('!load HelloWorld')
        self.assertEqual('Plugin HelloWorld activated', popMessage())

        pushMessage('!hello')  # should respond back
        self.assertEqual('Hello World !', popMessage())

        pushMessage('!repos uninstall err-helloworld')
        self.assertEqual('/me is unloading plugin HelloWorld', popMessage())
        self.assertEqual('Plugins unloaded and repo err-helloworld removed', popMessage())

        pushMessage('!hello')  # should not respond
        self.assertIn('Command "hello" not found', popMessage())

    def test_encoding_preservation(self):
        pushMessage('!echo へようこそ')
        self.assertEquals('へようこそ', popMessage())

    def test_webserver_webhook_test(self):
        self.assertCommand("!webhook test /echo/ toto", 'Status code : 200')

    def test_reload(self):
        pushMessage('!reload')
        m = popMessage()
        self.assertIn('Please tell me which of the following plugins to reload', m)
        self.assertIn('ChatRoom', m)

        pushMessage('!reload nosuchplugin')
        m = popMessage()
        self.assertIn("nosuchplugin isn't a valid plugin name. Currently loaded plugins are", m)
        self.assertIn('ChatRoom', m)

        pushMessage('!reload ChatRoom')
        self.assertEqual('Plugin ChatRoom deactivated', popMessage())
        self.assertEqual('Plugin ChatRoom activated', popMessage())

        pushMessage('!unload ChatRoom')
        self.assertEqual("Plugin ChatRoom deactivated", popMessage())
        pushMessage('!reload ChatRoom')
        self.assertEqual('Removed ChatRoom from the blacklist', popMessage())
        self.assertEqual('Plugin ChatRoom not in active list', popMessage())
        self.assertEqual('Plugin ChatRoom activated', popMessage())

    def test_unload_and_load(self):
        pushMessage('!unload nosuchplugin')
        m = popMessage()
        self.assertIn("nosuchplugin isn't a valid plugin name. Currently loaded plugins are", m)
        self.assertIn('ChatRoom', m)

        pushMessage('!load nosuchplugin')
        m = popMessage()
        self.assertIn("nosuchplugin isn't a valid plugin name. Currently loaded plugins are", m)
        self.assertIn('ChatRoom', m)

        pushMessage('!load ChatRoom')
        self.assertEqual('ChatRoom is already active', popMessage())

        pushMessage('!unload ChatRoom')
        self.assertEqual('Plugin ChatRoom deactivated', popMessage())

        pushMessage('!unload ChatRoom')
        self.assertEqual('ChatRoom is not an active plugin', popMessage())

        pushMessage('!load ChatRoom')
        self.assertEqual('Plugin ChatRoom activated', popMessage())
