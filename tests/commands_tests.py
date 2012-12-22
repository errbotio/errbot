# coding=utf-8
from threading import Thread
import unittest

from tests import TestBackend, outgoing_message_queue, incoming_message_queue, QUIT_MESSAGE
from errbot.main import main
import logging


class TestCommands(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(format='%(levelname)s:%(message)s')
        logger = logging.getLogger('')
        logger.setLevel(logging.DEBUG)

        self.bot_thread = Thread(target=main, name='Test Bot Thread', args=(TestBackend, logger))
        self.bot_thread.setDaemon(True)
        self.bot_thread.start()
        outgoing_message_queue.get() # wait for the started signal

    def test_root_help(self):
        incoming_message_queue.put('!help')
        self.assertIn('Available help', outgoing_message_queue.get())

    def test_help(self):
        # AssertionError: 'Available help' not found in 'Available commands for ErrBot:\n\n\t!about: Returns some information about this err instance\n\t!apropos: Returns a help string listing available options.\n\t!config: configure or get the configuration / configuration template for a specific plugin\n\t!echo: (undocumented)\n\t!export configs: Returns all the configs in form of a string you can backup\n\t!help: Returns a help string listing available options.\n\t!history: display the command history\n\t!import configs: Restore the configs from an export from !export configs\n\t!load: load a plugin\n\t!log tail: Display a tail of the log of n lines or 40 by default\n\t!reload: reload a plugin\n\t!repos export: Returns all the repos in form of a string you can backup\n\t!repos install: install a plugin repository from the given source or a known public repo (see !repos to find those).\n\t!repos uninstall: uninstall a plugin repository by name.\n\t!repos update: update the bot and/or plugins\n\t!repos: list the current active plugin repositories\n\t!restart: restart the bot\n\t!status: If I am alive I should be able to respond to this one\n\t!unload: unload a plugin\n\t!uptime: Return the uptime of the bot\n\t!zap configs: WARNING : Deletes all the configuration of all the plugins'
        incoming_message_queue.put('!help ErrBot')
        response = outgoing_message_queue.get()
        self.assertIn('Available commands for ErrBot', response)
        self.assertIn('!about', response)

    def test_about(self):
        incoming_message_queue.put('!about')
        self.assertIn('Err version', outgoing_message_queue.get())

    def test_uptime(self):
        incoming_message_queue.put('!uptime')
        self.assertIn('I up for', outgoing_message_queue.get())

    def test_status(self):
        incoming_message_queue.put('!status')
        self.assertIn('Yes I am alive', outgoing_message_queue.get())

    def test_config(self):
        incoming_message_queue.put('!config Webserver')
        self.assertIn('Copy paste and adapt of the following', outgoing_message_queue.get())

    def test_config_set_get(self):
        incoming_message_queue.put("!config Webserver {'EXTRA_FLASK_CONFIG': None, 'HOST': '127.0.3.4', 'PORT': 3141, 'WEBCHAT': False}")
        self.assertIn('Plugin configuration done.', outgoing_message_queue.get())
        incoming_message_queue.put('!config Webserver')
        self.assertIn('127.0.3.4', outgoing_message_queue.get())

    def tearDown(self):
        incoming_message_queue.put(QUIT_MESSAGE)
