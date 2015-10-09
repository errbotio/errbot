import sys
import unittest
import logging
import os
from tempfile import mkdtemp

from errbot.errBot import bot_config_defaults

log = logging.getLogger(__name__)

try:
    from errbot.backends import slack
except SystemExit:
    log.exception("Can't import backends.slack for testing")
    slack = None


@unittest.skipIf(not slack, "package slackclient not installed")
class SlackTests(unittest.TestCase):
    def setUp(self):
        # make up a config.
        tempdir = mkdtemp()
        # reset the config every time
        sys.modules.pop('errbot.config-template', None)
        __import__('errbot.config-template')
        config = sys.modules['errbot.config-template']
        bot_config_defaults(config)
        config.BOT_DATA_DIR = tempdir
        config.BOT_LOG_FILE = os.path.join(tempdir, 'log.txt')
        config.BOT_EXTRA_PLUGIN_DIR = []
        config.BOT_LOG_LEVEL = logging.DEBUG
        config.BOT_IDENTITY = {'username': 'err@localhost', 'token': '___'}
        config.BOT_ASYNC = False
        config.BOT_PREFIX = '!'
        config.CHATROOM_FN = 'blah'

        self.slack = slack.SlackBackend(config)

    def testSlackMessage(self):
        m = slack.SlackMessage(
            'foobar', type_='groupchat', attachments={1: 1})
        assert m.attachments == {1: 1}

        m = slack.SlackMessage('foobar2', type_='groupchat')
        assert m.attachments is None

    def testPrepareMessageBody(self):
        test_body = """
        hey, this is some code:
            ```
            foobar
            ```
        """
        parts = self.slack.prepare_message_body(test_body, 10000)
        assert parts == [test_body]

        test_body = """this block is unclosed: ``` foobar """
        parts = self.slack.prepare_message_body(test_body, 10000)
        assert parts == [test_body + "\n```\n"]

        test_body = """``` foobar """
        parts = self.slack.prepare_message_body(test_body, 10000)
        assert parts == [test_body + "\n```\n"]

        test_body = """closed ``` foobar ``` not closed ```"""
        # ---------------------------------^ 21st char
        parts = self.slack.prepare_message_body(test_body, 21)
        assert len(parts) == 2
        assert parts[0].count('```') == 2
        assert parts[0].endswith('```')
        assert parts[1].count('```') == 2
        assert parts[1].endswith('```\n')
