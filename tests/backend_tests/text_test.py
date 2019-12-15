import sys
from tempfile import mkdtemp

import pytest
import logging
import os

from errbot.backends.text import TextBackend
from errbot.bootstrap import bot_config_defaults


@pytest.fixture
def text_backend():
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
    config.BOT_PREFIX = '!'
    config.BOT_IDENTITY['username'] = '@testme'
    config.BOT_ADMINS = ['@test_admin']

    return TextBackend(config)


def test_change_presence(text_backend, caplog):
    with caplog.at_level(logging.DEBUG):
        text_backend.change_presence('online', "I'm online")
    assert len(caplog.messages) == 1
    a_message = caplog.messages[0]
    assert a_message.startswith('*** Changed presence')
