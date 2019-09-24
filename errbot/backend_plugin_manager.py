import logging
import sys

from pathlib import Path
from typing import Any, Type

from errbot.plugin_info import PluginInfo
from .utils import collect_roots

log = logging.getLogger(__name__)


class PluginNotFoundException(Exception):
    pass


def enumerate_backend_plugins(all_plugins_paths):
    plugin_places = [Path(root) for root in all_plugins_paths]
    for path in plugin_places:
        plugfiles = path.glob('**/*.plug')
        for plugfile in plugfiles:
            plugin_info = PluginInfo.load(plugfile)
            yield plugin_info


class BackendPluginManager:
    """
    This is a one shot plugin manager for Backends and Storage plugins.
    """
    def __init__(self, bot_config, base_module: str, plugin_name: str, base_class: Type,
                 base_search_dir, extra_search_dirs=()):
        self._config = bot_config
        self._base_module = base_module
        self._base_class = base_class

        self.plugin_info = None
        all_plugins_paths = collect_roots((base_search_dir, extra_search_dirs))

        for potential_plugin in enumerate_backend_plugins(all_plugins_paths):
            if potential_plugin.name == plugin_name:
                self.plugin_info = potential_plugin
                return
        raise PluginNotFoundException(f'Could not find the plugin named {plugin_name} in {all_plugins_paths}.')

    def load_plugin(self) -> Any:
        plugin_path = self.plugin_info.location.parent
        if plugin_path not in sys.path:
            # Cast pathlib.Path objects to string type for compatibility with sys.path
            sys.path.append(str(plugin_path))
        plugin_classes = self.plugin_info.load_plugin_classes(self._base_module, self._base_class)
        if len(plugin_classes) != 1:
            raise PluginNotFoundException(f'Found more that one plugin for {self._base_class}.')

        _, clazz = plugin_classes[0]
        return clazz(self._config)
