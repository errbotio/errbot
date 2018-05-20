import logging

import pytest
from errbot.core import ErrBot
from errbot.bootstrap import CORE_BACKENDS
from errbot.backend_plugin_manager import BackendPluginManager

logging.basicConfig(level=logging.DEBUG)

backends_to_check = ['Text', 'Test', 'Null']


@pytest.mark.parametrize('backend_name', backends_to_check)
def test_builtins(backend_name):
    bpm = BackendPluginManager({}, 'errbot.backends', backend_name, ErrBot, CORE_BACKENDS)
    assert bpm.plugin_info.name == backend_name
