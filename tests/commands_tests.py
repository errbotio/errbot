# coding=utf-8
from ast import literal_eval
from os.path import sep
from tempfile import mkdtemp
from threading import Thread
import unittest
import logging

# create a mock configuration
import sys

from errbot.main import main
from tests import TestBackend, outgoing_message_queue, incoming_message_queue, QUIT_MESSAGE


def popMessage():
    return outgoing_message_queue.get(timeout=5)


def pushMessage(msg):
    incoming_message_queue.put(msg, timeout=5)


def zapQueues():
    while not incoming_message_queue.empty():
        msg = incoming_message_queue.get(block=False)
        logging.error('Message left in the incoming queue during a test : %s' % msg)

    while not outgoing_message_queue.empty():
        msg = outgoing_message_queue.get(block=False)
        logging.error('Message left in the outgoing queue during a test : %s' % msg)


logging.basicConfig(format='%(levelname)s:%(message)s')
logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)


class TestCommands(unittest.TestCase):
    bot_thread = None

    def assertInPython2Safe(self, value, items):
        try:
            self.assertIn(value, items)
        except AttributeError:
            # assertIn wasn't added until Python 3.1
            pass

    def setUp(self):
        zapQueues()

    def tearDown(self):
        zapQueues()

    @classmethod
    def setUpClass(cls):
        cls.bot_thread = Thread(target=main, name='Test Bot Thread', args=(TestBackend, logger))
        cls.bot_thread.setDaemon(True)
        cls.bot_thread.start()

    @classmethod
    def tearDownClass(cls):
        pushMessage(QUIT_MESSAGE)
        cls.bot_thread.join()
        logging.info("Main bot thread quits")

    def test_root_help(self):
        pushMessage('!help')
        self.assertInPython2Safe('Available help', popMessage())

    def test_help(self):
        pushMessage('!help ErrBot')
        response = popMessage()
        self.assertInPython2Safe('Available commands for ErrBot', response)
        self.assertInPython2Safe('!about', response)

        pushMessage('!help beurk')
        self.assertEqual('That command is not defined.', popMessage())

    def test_about(self):
        pushMessage('!about')
        self.assertInPython2Safe('Err version', popMessage())

    def test_uptime(self):
        pushMessage('!uptime')
        self.assertInPython2Safe('I up for', popMessage())

    def test_status(self):
        pushMessage('!status')
        self.assertInPython2Safe('Yes I am alive', popMessage())

    def test_config_cycle(self):
        # test the full configuration cycle help, get set and export, import
        pushMessage('!zap configs')
        self.assertInPython2Safe('Done', popMessage())

        pushMessage('!config Webserver')
        self.assertInPython2Safe('Copy paste and adapt', popMessage())

        pushMessage("!config Webserver {'EXTRA_FLASK_CONFIG': None, 'HOST': '127.0.3.4', 'PORT': 3141, 'WEBCHAT': False}")
        self.assertInPython2Safe('Plugin configuration done.', popMessage())

        pushMessage('!config Webserver')
        self.assertInPython2Safe('127.0.3.4', popMessage())

        pushMessage('!export configs')
        configs = popMessage()
        self.assertInPython2Safe('127.0.3.4', configs)
        obj = literal_eval(configs)  # be sure it is parseable
        obj['Webserver']['HOST'] = '127.0.3.5'

        pushMessage('!import configs ' + repr(obj))
        self.assertInPython2Safe('Import is done correctly', popMessage())

        pushMessage('!config Webserver')
        self.assertInPython2Safe('127.0.3.5', popMessage())

    def test_apropos(self):
        pushMessage('!apropos about')
        self.assertInPython2Safe('!about: Returns some', popMessage())

    def test_logtail(self):
        pushMessage('!log tail')
        self.assertInPython2Safe('INFO', popMessage())

    def test_history(self):
        pushMessage('!uptime')
        popMessage()
        pushMessage('!history')
        self.assertInPython2Safe('uptime', popMessage())

    def test_plugin_cycle(self):
        pushMessage('!repos install git://github.com/gbin/err-helloworld.git')
        self.assertInPython2Safe('err-helloworld', popMessage())
        self.assertInPython2Safe('reload', popMessage())

        pushMessage('!repos export')  # should appear in the export
        self.assertEqual("{'err-helloworld': u'git://github.com/gbin/err-helloworld.git'}", popMessage())

        pushMessage('!help hello')  # should appear in the help
        self.assertEqual("this command says hello", popMessage())

        pushMessage('!hello')  # should respond
        self.assertEqual('Hello World !', popMessage())

        pushMessage('!reload HelloWorld')
        self.assertEqual('Plugin HelloWorld deactivated / Plugin HelloWorld activated', popMessage())

        pushMessage('!hello')  # should still respond
        self.assertEqual('Hello World !', popMessage())

        pushMessage('!unload HelloWorld')
        self.assertEqual('Plugin HelloWorld deactivated', popMessage())

        pushMessage('!hello')  # should not respond
        self.assertInPython2Safe('Command "hello" not found', popMessage())

        pushMessage('!load HelloWorld')
        self.assertEqual('Plugin HelloWorld activated', popMessage())

        pushMessage('!hello')  # should respond back
        self.assertEqual('Hello World !', popMessage())

        pushMessage('!repos uninstall err-helloworld')
        self.assertEqual('/me is unloading plugin HelloWorld', popMessage())
        self.assertEqual('Plugins unloaded and repo err-helloworld removed', popMessage())

        pushMessage('!hello')  # should not respond
        self.assertInPython2Safe('Command "hello" not found', popMessage())

    def test_encoding_preservation(self):
        pushMessage(u'!echo へようこそ')
        self.assertEquals(u'へようこそ', popMessage())
