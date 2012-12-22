# coding=utf-8
from ast import literal_eval
import json
from threading import Thread
import unittest

from tests import TestBackend, outgoing_message_queue, incoming_message_queue, QUIT_MESSAGE
from errbot.main import main
import logging


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
    bot_thread = Thread(target=main, name='Test Bot Thread', args=(TestBackend, logger))

    def setUp(self):
        zapQueues()

    def tearDown(self):
        zapQueues()

    @classmethod
    def setUpClass(cls):
        cls.bot_thread.setDaemon(True)
        cls.bot_thread.start()

    def test_root_help(self):
        pushMessage('!help')
        self.assertIn('Available help', popMessage())

    def test_help(self):
        # AssertionError: !history: display the command history\n\t!import configs: Restore the configs from an export from !export configs\n\t!load: load a plugin\n\t!log tail: Display a tail of the log of n lines or 40 by default\n\t!reload: reload a plugin\n\t!repos export: Returns all the repos in form of a string you can backup\n\t!repos install: install a plugin repository from the given source or a known public repo (see !repos to find those).\n\t!repos uninstall: uninstall a plugin repository by name.\n\t!repos update: update the bot and/or plugins\n\t!repos: list the current active plugin repositories\n\t!restart: restart the bot\n\t!status: If I am alive I should be able to respond to this one\n\t!unload: unload a plugin\n\t!uptime: Return the uptime of the bot\n\t!zap configs: WARNING : Deletes all the configuration of all the plugins'
        pushMessage('!help ErrBot')
        response = popMessage()
        self.assertIn('Available commands for ErrBot', response)
        self.assertIn('!about', response)

    def test_about(self):
        pushMessage('!about')
        self.assertIn('Err version', popMessage())

    def test_uptime(self):
        pushMessage('!uptime')
        self.assertIn('I up for', popMessage())

    def test_status(self):
        pushMessage('!status')
        self.assertIn('Yes I am alive', popMessage())

    def test_config_cycle(self):
        # test the full configuration cycle help, get set and export, import
        pushMessage('!zap configs')
        self.assertIn('Done', popMessage())

        pushMessage('!config Webserver')
        self.assertIn('Copy paste and adapt', popMessage())

        pushMessage("!config Webserver {'EXTRA_FLASK_CONFIG': None, 'HOST': '127.0.3.4', 'PORT': 3141, 'WEBCHAT': False}")
        self.assertIn('Plugin configuration done.', popMessage())

        pushMessage('!config Webserver')
        self.assertIn('127.0.3.4', popMessage())

        pushMessage('!export configs')
        configs = popMessage()
        self.assertIn('127.0.3.4', configs)
        obj = literal_eval(configs)  # be sure it is parseable
        obj['Webserver']['HOST'] = '127.0.3.5'

        pushMessage('!import configs ' + repr(obj))
        self.assertIn('Import is done correctly', popMessage())

        pushMessage('!config Webserver')
        self.assertIn('127.0.3.5', popMessage())

    def test_apropos(self):
        pushMessage('!apropos about')
        self.assertIn('!about: Returns some', popMessage())

    @classmethod
    def tearDownClass(cls):
        pushMessage(QUIT_MESSAGE)
        cls.bot_thread.join()
        logging.info("Main bot thread quits")