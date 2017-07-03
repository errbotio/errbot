import sys
import logging
import os
from tempfile import mkdtemp
from mock import MagicMock
import pytest

from errbot.bootstrap import bot_config_defaults
from errbot.backends.base import Message

log = logging.getLogger(__name__)

try:
    from errbot.backends import telegram_messenger

except SystemExit:
    log.exception("Can't import backends.telegram_messenger for testing")
    telegram_messenger = None


@pytest.fixture
def config():
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
    config.BOT_IDENTITY = {'username': 1234567890, 'token': '___'}
    config.BOT_ASYNC = False
    config.BOT_PREFIX = '/'
    config.CHATROOM_FN = 'blah'
    return config


@pytest.fixture
def text_config(config):
    # we default to markdown parse_mode, so unset it
    config.TELEGRAM_DEFAULT_SEND_OPTIONS = dict(parse_mode=None)
    return config


def get_telegram_backend(config=config):
    class TestTelegramBackend(telegram_messenger.TelegramBackend):
        pass

    telegram_backend = TestTelegramBackend(config=config)
    telegram_backend.telegram = MagicMock()
    telegram_backend.plugin_manager = MagicMock()

    return telegram_backend


@pytest.fixture
def backend_md(config):
    if telegram_messenger:
        return get_telegram_backend(config=config)


@pytest.fixture
def backend_text(text_config):
    if telegram_messenger:
        return get_telegram_backend(config=text_config)


def test_send_message_options(backend_md, backend_text):
    convert = backend_md.md_converter.convert
    text = "• test unicod string"  # a unicode string
    assert convert(text) == (text)
    msg = Message(text, frm=telegram_messenger.TelegramPerson(1), to=telegram_messenger.TelegramPerson(2))

    backend_md.send_message(msg)
    backend_md.telegram.sendMessage.assert_called_once_with(2, text, parse_mode='Markdown')
    backend_text.send_message(msg)
    backend_text.telegram.sendMessage.assert_called_once_with(2, text, parse_mode=None)
