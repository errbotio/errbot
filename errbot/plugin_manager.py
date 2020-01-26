""" Logic related to plugin loading and lifecycle """
from copy import deepcopy
from importlib import machinery
import logging
import os
import subprocess
import sys
import traceback
from pathlib import Path

from typing import Tuple, Dict, Any, Type, Set, List, Optional, Callable

from errbot.flow import BotFlow, Flow
from errbot.repo_manager import check_dependencies
from errbot.storage.base import StoragePluginBase
from .botplugin import BotPlugin
from .plugin_info import PluginInfo
from .utils import version2tuple, collect_roots
from .templating import remove_plugin_templates_path, add_plugin_templates_path
from .version import VERSION
from .core_plugins.wsview import route
from .storage import StoreMixin

PluginInstanceCallback = Callable[[str, Type[BotPlugin]], BotPlugin]

log = logging.getLogger(__name__)

CORE_PLUGINS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core_plugins')


class PluginActivationException(Exception):
    pass


class IncompatiblePluginException(PluginActivationException):
    pass


class PluginConfigurationException(PluginActivationException):
    pass


def _ensure_sys_path_contains(paths):
    """ Ensure that os.path contains paths
       :param paths:
            a list of base paths to walk from
            elements can be a string or a list/tuple of strings
    """
    for entry in paths:
        if isinstance(entry, (list, tuple)):
            _ensure_sys_path_contains(entry)
        elif entry is not None and entry not in sys.path:
            sys.path.append(entry)


def populate_doc(plugin_object: BotPlugin, plugin_info: PluginInfo) -> None:
    plugin_class = type(plugin_object)
    plugin_class.__errdoc__ = plugin_class.__doc__ if plugin_class.__doc__ else plugin_info.doc


def install_packages(req_path: Path):
    """ Installs all the packages from the given requirements.txt

        Return an exc_info if it fails otherwise None.
    """
    def is_docker():
        if not os.path.exists('/proc/1/cgroup'):
            return false
        with open('/proc/1/cgroup') as d:
            return 'docker' in d.read()

    log.info('Installing packages from "%s".', req_path)
    # use sys.executable explicitly instead of just 'pip' because depending on how the bot is deployed
    # 'pip' might not be available on PATH: for example when installing errbot on a virtualenv and
    # starting it with systemclt pointing directly to the executable:
    # [Service]
    # ExecStart=/home/errbot/.env/bin/errbot
    pip_cmdline = [sys.executable, '-m', 'pip']
    # noinspection PyBroadException
    try:
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and (sys.base_prefix != sys.prefix)):
            # this is a virtualenv, so we can use it directly
            subprocess.check_call(pip_cmdline + ['install', '--requirement', str(req_path)])
        elif is_docker():
            # this is a docker container, so we can use it directly
            subprocess.check_call(pip_cmdline + ['install', '--requirement', str(req_path)])
        else:
            # otherwise only install it as a user package
            subprocess.check_call(pip_cmdline + ['install', '--user', '--requirement', str(req_path)])
    except Exception:
        log.exception('Failed to execute pip install for %s.', req_path)
        return sys.exc_info()


def check_python_plug_section(plugin_info: PluginInfo) -> bool:
    """ Checks if we have the correct version to run this plugin.
    Returns true if the plugin is loadable """
    version = plugin_info.python_version

    # if the plugin doesn't restric anything, assume it is ok and try to load it.
    if not version:
        return True

    sys_version = sys.version_info[:3]
    if version < (3, 0, 0):
        log.error('Plugin %s is made for python 2 only and Errbot is not compatible with Python 2 anymore.',
                  plugin_info.name)
        log.error('Please contact the plugin developer or try to contribute to port the plugin.')
        return False

    if version >= sys_version:
        log.error('Plugin %s requires python >= %s and this Errbot instance runs %s.',
                  plugin_info.name, '.'.join(str(v) for v in version), '.'.join(str(v) for v in sys_version))
        log.error('Upgrade your python interpreter if you want to use this plugin.')
        return False

    return True


def check_errbot_version(plugin_info: PluginInfo):
    """ Checks if a plugin version between min_version and max_version is ok
    for this errbot.
    Raises IncompatiblePluginException if not.
    """
    name, min_version, max_version = plugin_info.name, plugin_info.errbot_minversion, plugin_info.errbot_maxversion
    current_version = version2tuple(VERSION)
    if min_version and min_version > current_version:
        raise IncompatiblePluginException(f'The plugin {name} asks for Errbot with a minimal version of '
                                          f'{min_version} while Errbot is version {VERSION}.')

    if max_version and max_version < current_version:
        raise IncompatiblePluginException(f'The plugin {name} asks for Errbot with a maximum version of {max_version} '
                                          f'while Errbot is version {VERSION}')


# Storage names
CONFIGS = 'configs'
BL_PLUGINS = 'bl_plugins'


class BotPluginManager(StoreMixin):

    def __init__(self,
                 storage_plugin: StoragePluginBase,
                 extra_plugin_dir: Optional[str],
                 autoinstall_deps: bool,
                 core_plugins: Tuple[str, ...],
                 plugin_instance_callback: PluginInstanceCallback,
                 plugins_callback_order: Tuple[Optional[str], ...]):
        """
        Creates a Plugin manager
        :param storage_plugin: the plugin used to store to config for this manager
        :param extra_plugin_dir: an extra directory to search for plugins
        :param autoinstall_deps: if True, will install also the plugin deps from requirements.txt
        :param core_plugins: the list of core plugin that will be started
        :param plugin_instance_callback: the callback to instantiate a plugin (to inject the dependency on the bot)
        :param plugins_callback_order: the order on which the plugins will be callbacked
        """
        super().__init__()
        self.autoinstall_deps: bool = autoinstall_deps
        self._extra_plugin_dir: str = extra_plugin_dir
        self._plugin_instance_callback: PluginInstanceCallback = plugin_instance_callback
        self.core_plugins: Tuple[str, ...] = core_plugins
        # Make sure there is a 'None' entry in the callback order, to include
        # any plugin not explicitly ordered.
        self.plugins_callback_order = plugins_callback_order
        if None not in self.plugins_callback_order:
            self.plugins_callback_order += (None,)
        self.plugin_infos: Dict[str, PluginInfo] = {}
        self.plugins: Dict[str, BotPlugin] = {}
        self.flow_infos: Dict[str, PluginInfo] = {}
        self.flows: Dict[str, Flow] = {}
        self.plugin_places = []
        self.open_storage(storage_plugin, 'core')
        if CONFIGS not in self:
            self[CONFIGS] = {}

    def get_plugin_obj_by_name(self, name: str) -> BotPlugin:
        return self.plugins.get(name, None)

    def reload_plugin_by_name(self, name):
        """
        Completely reload the given plugin, including reloading of the module's code
        :throws PluginActivationException: needs to be taken care of by the callers.
        """
        plugin = self.plugins[name]
        plugin_info = self.plugin_infos[name]

        if plugin.is_activated:
            self.deactivate_plugin(name)

        base_name = '.'.join(plugin.__module__.split('.')[:-1])
        classes = plugin_info.load_plugin_classes(base_name, BotPlugin)
        _, new_class = classes[0]
        plugin.__class__ = new_class

        self.activate_plugin(name)

    def _install_potential_package_dependencies(self, path: Path,
                                                feedback: Dict[Path, str]):
        req_path = path / 'requirements.txt'
        if req_path.exists():
            log.info('Checking package dependencies from %s.', req_path)
            if self.autoinstall_deps:
                exc_info = install_packages(req_path)
                if exc_info is not None:
                    typ, value, trace = exc_info
                    feedback[path] = f'{typ}: {value}\n{"".join(traceback.format_tb(trace))}'
            else:
                msg, _ = check_dependencies(req_path)
                if msg and path not in feedback:  # favor the first error.
                    feedback[path] = msg

    def _load_plugins_generic(self,
                              path: Path,
                              extension: str,
                              base_module_name,
                              baseclass: Type,
                              dest_dict: Dict[str, Any],
                              dest_info_dict: Dict[str, Any],
                              feedback: Dict[Path, str]):
        self._install_potential_package_dependencies(path, feedback)
        plugfiles = path.glob('**/*.' + extension)
        for plugfile in plugfiles:
            try:
                plugin_info = PluginInfo.load(plugfile)
                name = plugin_info.name
                if name in dest_info_dict:
                    log.warning('Plugin %s already loaded.', name)
                    continue

                # save the plugin_info for ref.
                dest_info_dict[name] = plugin_info

                # Skip the core plugins not listed in CORE_PLUGINS if CORE_PLUGINS is defined.
                if self.core_plugins and plugin_info.core and (plugin_info.name not in self.core_plugins):
                    log.debug("%s plugin will not be loaded because it's not listed in CORE_PLUGINS", name)
                    continue

                plugin_classes = plugin_info.load_plugin_classes(base_module_name, baseclass)
                if not plugin_classes:
                    feedback[path] = f'Did not find any plugin in {path}.'
                    continue
                if len(plugin_classes) > 1:
                    # TODO: This is something we can support as "subplugins" or something similar.
                    feedback[path] = 'Contains more than one plugin, only one will be loaded.'

                # instantiate the plugin object.
                _, clazz = plugin_classes[0]
                dest_dict[name] = self._plugin_instance_callback(name, clazz)

            except Exception:
                feedback[path] = traceback.format_exc()

    def _load_plugins(self) -> Dict[Path, str]:
        feedback = {}
        for path in self.plugin_places:
            self._load_plugins_generic(path, 'plug', 'errbot.plugins', BotPlugin,
                                       self.plugins, self.plugin_infos, feedback)
            self._load_plugins_generic(path, 'flow', 'errbot.flows', BotFlow,
                                       self.flows, self.flow_infos, feedback)
        return feedback

    def update_plugin_places(self, path_list) -> Dict[Path, str]:
        """
        This updates where this manager is trying to find plugins and try to load newly found ones.
        :param path_list: the path list where to search for plugins.
        :return: the feedback for any specific path in case of error.
        """
        repo_roots = (CORE_PLUGINS, self._extra_plugin_dir, path_list)

        all_roots = collect_roots(repo_roots)

        log.debug('New entries added to sys.path:')
        for entry in all_roots:
            if entry not in sys.path:
                log.debug(entry)
                sys.path.append(entry)
        # so plugins can relatively import their repos
        _ensure_sys_path_contains(repo_roots)
        self.plugin_places = [Path(root) for root in all_roots]
        return self._load_plugins()

    def get_all_active_plugins(self) -> List[BotPlugin]:
        """This returns the list of plugins in the callback ordered defined from the config."""

        all_plugins = []
        for name in self.plugins_callback_order:
            # None is a placeholder for any plugin not having a defined order
            if name is None:
                all_plugins += [
                    plugin for name, plugin in self.plugins.items()
                    if name not in self.plugins_callback_order and plugin.is_activated
                ]
            else:
                plugin = self.plugins[name]
                if plugin.is_activated:
                    all_plugins.append(plugin)
        return all_plugins

    def get_all_active_plugin_names(self):
        return [name for name, plugin in self.plugins.items() if plugin.is_activated]

    def get_all_plugin_names(self):
        return self.plugins.keys()

    def get_plugin_by_path(self, path):
        for name, pi in self.plugin_infos.items():
            if str(pi.location.parent) == path:
                return self.plugins[name]

    def deactivate_all_plugins(self):
        for name in self.get_all_active_plugin_names():
            self.deactivate_plugin(name)

    # plugin blacklisting management
    def get_blacklisted_plugin(self):
        return self.get(BL_PLUGINS, [])

    def is_plugin_blacklisted(self, name):
        return name in self.get_blacklisted_plugin()

    def blacklist_plugin(self, name):
        if self.is_plugin_blacklisted(name):
            logging.warning('Plugin %s is already blacklisted.', name)
            return f'Plugin {name} is already blacklisted.'
        self[BL_PLUGINS] = self.get_blacklisted_plugin() + [name]
        log.info('Plugin %s is now blacklisted.', name)
        return f'Plugin {name} is now blacklisted.'

    def unblacklist_plugin(self, name):
        if not self.is_plugin_blacklisted(name):
            logging.warning('Plugin %s is not blacklisted.', name)
            return f'Plugin {name} is not blacklisted.'
        plugin = self.get_blacklisted_plugin()
        plugin.remove(name)
        self[BL_PLUGINS] = plugin
        log.info('Plugin %s removed from blacklist.', name)
        return f'Plugin {name} removed from blacklist.'

    # configurations management
    def get_plugin_configuration(self, name):
        configs = self[CONFIGS]
        if name not in configs:
            return None
        return configs[name]

    def set_plugin_configuration(self, name, obj):
        # TODO: port to with statement
        configs = self[CONFIGS]
        configs[name] = obj
        self[CONFIGS] = configs

    def activate_non_started_plugins(self):
        """
        Activates all plugins that are not activated, respecting its dependencies.

        :return: Empty string if no problem occured or a string explaining what went wrong.
        """
        log.info('Activate bot plugins...')
        errors = ''
        for name, plugin in self.plugins.items():
            try:
                if self.is_plugin_blacklisted(name):
                    errors += f'Notice: {plugin.name} is blacklisted, ' \
                              f'use {self.bot.prefix}plugin unblacklist {name} to unblacklist it.\n'
                    continue
                if not plugin.is_activated:
                    log.info('Activate plugin: %s.', name)
                    self.activate_plugin(name)
            except Exception as e:
                log.exception('Error loading %s.', name)
                errors += f'Error: {name} failed to activate: {e}.\n'

        log.debug('Activate flow plugins ...')
        for name, flow in self.flows.items():
            try:
                if not flow.is_activated:
                    log.info('Activate flow: %s', name)
                    self.activate_flow(name)
            except Exception as e:
                log.exception(f'Error loading flow {name}.')
                errors += f'Error: flow {name} failed to start: {e}.\n'
        return errors

    def _activate_plugin(self, plugin: BotPlugin, plugin_info: PluginInfo):
        """
        Activate a specific plugin with no check.
        """
        if plugin.is_activated:
            raise Exception('Internal Error, invalid activated state.')

        name = plugin.name
        try:
            config = self.get_plugin_configuration(name)
            if plugin.get_configuration_template() is not None and config is not None:
                log.debug('Checking configuration for %s...', name)
                plugin.check_configuration(config)
                log.debug('Configuration for %s checked OK.', name)
            plugin.configure(config)  # even if it is None we pass it on
        except Exception as ex:
            log.exception('Something is wrong with the configuration of the plugin %s', name)
            plugin.config = None
            raise PluginConfigurationException(str(ex))

        try:
            add_plugin_templates_path(plugin_info)
            populate_doc(plugin, plugin_info)
            plugin.activate()
            route(plugin)
            plugin.callback_connect()
        except Exception:
            log.error('Plugin %s failed at activation stage, deactivating it...', name)
            self.deactivate_plugin(name)
            raise

    def activate_flow(self, name: str):
        if name not in self.flows:
            raise PluginActivationException(f'Could not find the flow named {name}.')

        flow = self.flows[name]
        if flow.is_activated:
            raise PluginActivationException(f'Flow {name} is already active.')
        flow.activate()

    def deactivate_flow(self, name: str):
        flow = self.flows[name]
        if not flow.is_activated:
            raise PluginActivationException(f'Flow {name} is already inactive.')
        flow.deactivate()

    def activate_plugin(self, name: str):
        """
        Activate a plugin with its dependencies.
        """
        try:
            if name not in self.plugins:
                raise PluginActivationException(f'Could not find the plugin named {name}.')

            plugin = self.plugins[name]
            if plugin.is_activated:
                raise PluginActivationException(f'Plugin {name} already activate.')

            plugin_info = self.plugin_infos[name]

            if not check_python_plug_section(plugin_info):
                return None

            check_errbot_version(plugin_info)

            dep_track = set()
            depends_on = self._activate_plugin_dependencies(name, dep_track)
            plugin.dependencies = depends_on
            self._activate_plugin(plugin, plugin_info)

        except PluginActivationException:
            raise
        except Exception as e:
            log.exception(f'Error loading {name}.')
            raise PluginActivationException(f'{name} failed to start : {e}.')

    def _activate_plugin_dependencies(self, name: str, dep_track: Set[str]) -> List[str]:

        plugin_info = self.plugin_infos[name]
        dep_track.add(name)

        depends_on = plugin_info.dependencies
        for dep_name in depends_on:
            if dep_name in dep_track:
                raise PluginActivationException(f'Circular dependency in the set of plugins ({", ".join(dep_track)})')
            if dep_name not in self.plugins:
                raise PluginActivationException(f'Unknown plugin dependency {dep_name}.')
            dep_plugin = self.plugins[dep_name]
            dep_plugin_info = self.plugin_infos[dep_name]
            if not dep_plugin.is_activated:
                log.debug('%s depends on %s and %s is not activated. Activating it ...', name, dep_name, dep_name)
                self._activate_plugin_dependencies(dep_name, dep_track)
                self._activate_plugin(dep_plugin, dep_plugin_info)
        return depends_on

    def deactivate_plugin(self, name: str):
        plugin = self.plugins[name]
        if not plugin.is_activated:
            log.warning('Plugin already deactivated, ignore.')
            return
        plugin_info = self.plugin_infos[name]
        plugin.deactivate()
        remove_plugin_templates_path(plugin_info)

    def remove_plugin(self, plugin: BotPlugin):
        """
        Deactivate and remove a plugin completely.
        :param plugin: the plugin to remove
        :return:
        """
        # First deactivate it if it was activated
        if plugin.is_activated:
            self.deactivate_plugin(plugin.name)

        del(self.plugins[plugin.name])
        del(self.plugin_infos[plugin.name])

    def remove_plugins_from_path(self, root):
        """
        Remove all the plugins that are in the filetree pointed by root.
        """
        old_plugin_infos = deepcopy(self.plugin_infos)
        for name, pi in old_plugin_infos.items():
            if str(pi.location).startswith(root):
                self.remove_plugin(self.plugins[name])

    def shutdown(self):
        log.info('Shutdown.')
        self.close_storage()
        log.info('Bye.')

    def __hash__(self):
        # Ensures this class (and subclasses) are hashable.
        # Presumably the use of mixins causes __hash__ to be
        # None otherwise.
        return int(id(self))
