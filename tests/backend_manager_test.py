import logging

import pytest
from errbot.backend_plugin_manager import BackendPluginManager
from errbot.bootstrap import CORE_BACKENDS, CORE_STORAGE
from errbot.core import ErrBot
from errbot.plugin_info import PluginInfo
from errbot.storage.base import StoragePluginBase

logging.basicConfig(level=logging.DEBUG)

backends_to_check = ['Text', 'Test', 'Null']
storage_to_check = ['Shelf', 'Memory']


@pytest.mark.parametrize('backend_name', backends_to_check)
def test_builtins(backend_name):
    bpm = BackendPluginManager({}, 'errbot.backends', backend_name, ErrBot, CORE_BACKENDS)
    assert bpm.plugin_info.name == backend_name


@pytest.mark.parametrize('backend_name', backends_to_check)
def test_list_plugins(backend_name):
    bpm = BackendPluginManager({}, 'errbot.backends', backend_name, ErrBot, CORE_BACKENDS)
    assert isinstance(bpm.list_plugins(), list)
    for backend in bpm.list_plugins():
        assert isinstance(backend, PluginInfo)


@pytest.mark.parametrize('backend_name', backends_to_check)
def test_list_plugins_backend(backend_name):
    bpm = BackendPluginManager({}, 'errbot.backends', backend_name, ErrBot, CORE_BACKENDS)
    assert backend_name in [x.name for x in bpm.list_plugins()]


@pytest.mark.parametrize('storage_name', storage_to_check)
def test_list_plugins_storage(storage_name):
    spm = BackendPluginManager({}, 'errbot.storage', storage_name, StoragePluginBase, CORE_STORAGE)
    assert storage_name in [x.name for x in spm.list_plugins()]
