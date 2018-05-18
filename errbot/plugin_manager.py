""" Logic related to plugin loading and lifecycle """
import inspect

from importlib import machinery
import logging
import os
import subprocess
import sys
import traceback
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path

from typing import Tuple, Sequence, Dict, Union, Any, Type

from errbot.flow import BotFlow, Flow
from .botplugin import BotPlugin
from .plugin_info import PluginInfo
from .utils import version2tuple, collect_roots
from .templating import remove_plugin_templates_path, add_plugin_templates_path
from .version import VERSION
from .core_plugins.wsview import route
from .storage import StoreMixin

log = logging.getLogger(__name__)

CORE_PLUGINS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core_plugins')

try:
    from importlib import reload  # new in python 3.4
except ImportError:
    from imp import reload  # noqa


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
    log.info("Installing packages from '%s'." % req_path)
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
        else:
            # otherwise only install it as a user package
            subprocess.check_call(pip_cmdline + ['install', '--user', '--requirement', str(req_path)])
    except Exception:
        log.exception('Failed to execute pip install for %s.', req_path)
        return sys.exc_info()


def check_dependencies(req_path: Path) -> Tuple[Union[str, None], Sequence[str]]:
    """ This methods returns a pair of (message, packages missing).
    Or None, [] if everything is OK.
    """
    log.debug("check dependencies of %s" % req_path)
    # noinspection PyBroadException
    try:
        from pkg_resources import get_distribution
        missing_pkg = []

        if not os.path.isfile(req_path):
            log.debug('%s has no requirements.txt file' % req_path)
            return None, missing_pkg

        with open(req_path) as f:
            for line in f:
                stripped = line.strip()
                # skip empty lines.
                if not stripped:
                    continue

                # noinspection PyBroadException
                try:
                    get_distribution(stripped)
                except Exception:
                    missing_pkg.append(stripped)
        if missing_pkg:
            return (('You need these dependencies for %s: ' % req_path) + ','.join(missing_pkg),
                    missing_pkg)
        return None, missing_pkg
    except Exception:
        log.exception('Problem checking for dependencies.')
        return 'You need to have setuptools installed for the dependency check of the plugins', []


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
    log.info('Activating %s with min_err_version = %s and max_version = %s',
             name, min_version, max_version)
    current_version = version2tuple(VERSION)
    if min_version and min_version > current_version:
        raise IncompatiblePluginException(
            'The plugin %s asks for Errbot with a minimal version of %s while Errbot is version %s' % (
                name, min_version, VERSION)
        )

    if max_version and max_version < current_version:
        raise IncompatiblePluginException(
            'The plugin %s asks for Errbot with a maximum version of %s while Errbot is version %s' % (
                name, max_version, VERSION)
        )
    return True


# TODO: move this out, this has nothing to do with plugins
def global_restart():
    python = sys.executable
    os.execl(python, python, *sys.argv)


# Storage names
CONFIGS = 'configs'
BL_PLUGINS = 'bl_plugins'


class BotPluginManager(StoreMixin):

    def __init__(self, storage_plugin, repo_manager, extra, autoinstall_deps, core_plugins, plugins_callback_order):
        super().__init__()
        self.bot = None
        self.autoinstall_deps = autoinstall_deps
        self.extra = extra
        self.open_storage(storage_plugin, 'core')
        self.core_plugins = core_plugins
        self.plugins_callback_order = plugins_callback_order
        self.repo_manager = repo_manager

        # be sure we have a configs entry for the plugin configurations
        if CONFIGS not in self:
            self[CONFIGS] = {}

        self.plugin_infos = {}  # Name ->  PluginInfo
        self.plugins = {}  # Name ->  BotPlugin
        self.flows = {}  # Name ->  Flow
        self.plugin_places = []
        #locator = PluginFileLocator([PluginFileAnalyzerWithInfoFile("info_ext", 'plug'),
        #                            PluginFileAnalyzerWithInfoFile("info_ext", 'flow')])

    def attach_bot(self, bot):
        self.bot = bot

    def _activate_plugin(self, name: str):
        self.plugins[name].activate()
        plugin_info = self.plugin_infos[name]
        add_plugin_templates_path(plugin_info)

    def deactivate_plugin(self, name: str):
        obj = self.plugins[name]
        plugin_info = self.plugin_infos[name]
        remove_plugin_templates_path(plugin_info)
        try:
            return obj.deactivate()
        except Exception:
            add_plugin_templates_path(plugin_info)
            raise

    def check_enabled_core_plugin(self, plugin_info: PluginInfo) -> bool:
        """ Checks if the given plugin is core and if it is, if it is part of the enabled core_plugins_list.
        :param plugin_info: the info from the plugin
        :return: True if it is OK to load this plugin.
        """
        return plugin_info.core and plugin_info.name in self.core_plugins

    def get_plugin_obj_by_name(self, name: str) -> BotPlugin:
        return self.plugins.get(name, None)

    def activate_plugin_with_version_check(self, plugin: BotPlugin, dep_track=None):
        name = plugin.name
        plugin_info = self.plugin_infos[name]

        config = self.get_plugin_configuration(name)

        if not check_python_plug_section(plugin_info):
            return None

        if not check_errbot_version(plugin_info):
            return None

        depends_on = self._activate_plugin_dependencies(plugin_info, dep_track)

        plugin.dependencies = depends_on

        try:
            if plugin.get_configuration_template() is not None and config is not None:
                log.debug('Checking configuration for %s...', name)
                plugin.check_configuration(config)
                log.debug('Configuration for %s checked OK.', name)
            plugin.configure(config)  # even if it is None we pass it on
        except Exception as ex:
            log.exception('Something is wrong with the configuration of the plugin %s', name)
            plugin.config = None
            raise PluginConfigurationException(str(ex))
        add_plugin_templates_path(plugin_info)
        populate_doc(plugin, plugin_info)
        try:
            self._activate_plugin(name)
            route(plugin)
        except Exception:
            remove_plugin_templates_path(plugin_info)
            log.error('Plugin %s failed at activation stage, deactivating it...', name)
            self.deactivate_plugin(name)
            raise

    def _activate_plugin_dependencies(self, plugin_info: PluginInfo, dep_track):
        if dep_track is None:
            dep_track = set()

        name = plugin_info.name
        dep_track.add(name)

        depends_on = plugin_info.dependencies
        for dep_name in depends_on:
            if dep_name in dep_track:
                raise PluginActivationException('Circular dependency in the set of plugins (%s)' %
                                                ', '.join(dep_track))
            if dep_name not in self.get_all_active_plugin_names():
                log.debug('%s depends on %s and %s is not activated. Activating it ...', name, dep_name, dep_name)
                self._activate_plugin_dependencies(self.plugin_infos[dep_name], dep_track)
        return depends_on

    def reload_plugin_by_name(self, name):
        """
        Completely reload the given plugin, including reloading of the module's code
        :throws PluginActivationException: needs to be taken care of by the callers.
        """
        plugin = self.plugins[name]
        was_activated = plugin.is_activated

        if was_activated:
            self.deactivate_plugin(name)

        module_alias = plugin.__module__
        module_old = __import__(module_alias)
        f = module_old.__file__
        module_new = machinery.SourceFileLoader(module_alias, f).load_module(module_alias)
        class_name = type(plugin.plugin_object).__name__
        new_class = getattr(module_new, class_name)
        plugin.__class__ = new_class

        if was_activated:
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
                    feedback[path] = '%s: %s\n%s' % (typ, value, ''.join(traceback.format_tb(trace)))
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
                              feedback: Dict[Path, str]):
        self._install_potential_package_dependencies(path, feedback)
        plugfiles = path.glob('**/*.' + extension)
        for plugfile in plugfiles:
            try:
                plugin_info = PluginInfo.load(plugfile)
                name = plugin_info.name

                # save the plugin_info for ref.
                self.plugin_infos[name] = plugin_info

                # Skip the core plugins not listed in CORE_PLUGINS if CORE_PLUGINS is defined.
                if self.core_plugins and plugin_info.core and (plugin_info.name not in self.core_plugins):
                    log.debug("%s plugin will not be loaded because it's not listed in CORE_PLUGINS", name)
                    continue

                # load the module
                spec = spec_from_file_location(base_module_name, plugin_info.location / (plugin_info.module + '.py'))
                module = module_from_spec(spec)
                spec.loader.exec_module(module)
                sys.modules[base_module_name] = module


                # introspect the modules to find plugin classes
                def is_plugin(member):
                    return inspect.isclass(member) and issubclass(member, baseclass) and member != baseclass
                plugin_classes = inspect.getmembers(module, is_plugin)
                if not plugin_classes:
                    feedback[path] = 'Did not find any plugin in %s.' % path
                    continue
                if len(plugin_classes) > 1:
                    # TODO: This is something we can support as "subplugins" or something similar.
                    feedback[path] = 'Contains more than one plugin, only one will be loaded.'

                # instantiate the plugin object.
                _, clazz = plugin_classes[0]
                dest_dict[name] = clazz(self.bot, name)

            except Exception as e:
                feedback[path] = str(e)

    def load_plugins(self, feedback: Dict[Path, str]):
        for path in self.plugin_places:
            self._load_plugins_generic(path, 'plug', 'errbot.plugins', BotPlugin, self.plugins, feedback)
            self._load_plugins_generic(path, 'flow', 'errbot.flows', BotFlow, self.flows, feedback)

    def update_plugin_places(self, path_list, extra_plugin_dir):
        """ It returns a dictionary of path -> error strings."""
        repo_roots = (CORE_PLUGINS, extra_plugin_dir, path_list)

        all_roots = collect_roots(repo_roots)

        log.debug('New entries added to sys.path:')
        for entry in all_roots:
            if entry not in sys.path:
                log.debug(entry)
                sys.path.append(entry)
        # so plugins can relatively import their repos
        _ensure_sys_path_contains(repo_roots)
        self.plugin_places = [Path(root) for root in all_roots]
        errors = {}

        self.load_plugins(errors)
        return errors

    def get_all_active_plugin_objects_ordered(self):
        # Make sure there is a 'None' entry in the callback order, to include
        # any plugin not explicitly ordered.
        if None not in self.plugins_callback_order:
            self.plugins_callback_order = self.plugins_callback_order + (None,)

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

    def get_all_active_plugin_objects(self):
        return [plugin for plugin in self.plugins.values() if plugin.is_activated]

    def get_all_active_plugin_names(self):
        return [name for name, plugin in self.plugins.items() if plugin.is_activated]

    def get_all_plugin_names(self):
        return self.plugins.keys()

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
            logging.warning('Plugin %s is already blacklisted' % name)
            return 'Plugin %s is already blacklisted' % name
        self[BL_PLUGINS] = self.get_blacklisted_plugin() + [name]
        log.info('Plugin %s is now blacklisted' % name)
        return 'Plugin %s is now blacklisted' % name

    def unblacklist_plugin(self, name):
        if not self.is_plugin_blacklisted(name):
            logging.warning('Plugin %s is not blacklisted' % name)
            return 'Plugin %s is not blacklisted' % name
        plugin = self.get_blacklisted_plugin()
        plugin.remove(name)
        self[BL_PLUGINS] = plugin
        log.info('Plugin %s removed from blacklist' % name)
        return 'Plugin %s removed from blacklist' % name

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

    # this will load the plugins the admin has setup at runtime
    def update_dynamic_plugins(self):
        """ It returns a dictionary of path -> error strings."""
        return self.update_plugin_places(self.repo_manager.get_all_repos_paths(), self.extra)

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
                    errors += 'Notice: %s is blacklisted, use %splugin unblacklist %s to unblacklist it\n' % (
                        plugin.name, self.bot.prefix, name)
                    continue
                if not plugin.is_activated:
                    log.info('Activate plugin: %s', name)
                    self.activate_plugin_with_version_check(plugin)
            except Exception as e:
                log.exception('Error loading %s', name)
                errors += 'Error: %s failed to activate: %s\n' % (name, e)

        log.debug('Activate flow plugins ...')
        for flow in self.flows:
            try:
                if not flow.is_activated:
                    name = flow.name
                    log.info('Activate flow: %s' % name)
                    self.activate_plugin(name)
            except Exception as e:
                log.exception("Error loading flow %s" % name)
                errors += 'Error: flow %s failed to start: %s\n' % (name, e)
        return errors

    def activate_plugin(self, name, dep_track=None):
        """
        Internal recursive version of activate_plugin.
        """
        try:
            if name in self.get_all_active_plugin_names():
                raise PluginActivationException('Plugin already in active list')
            if name not in self.plugins:
                raise PluginActivationException('Could not find the plugin named %s.' % name)
            plugin = self.plugins[name]
            self.activate_plugin_with_version_check(plugin, dep_track)
            plugin.callback_connect()
        except PluginActivationException:
            raise
        except Exception as e:
            log.exception('Error loading %s.' % name)
            raise PluginActivationException('%s failed to start : %s.' % (name, e))

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
        for pi in self.plugin_infos:
            if str(pi.location).startswith(root):
                self.remove_plugin(self.plugins[pi.name])

    def shutdown(self):
        log.info('Shutdown.')
        self.close_storage()
        log.info('Bye.')

    def __hash__(self):
        # Ensures this class (and subclasses) are hashable.
        # Presumably the use of mixins causes __hash__ to be
        # None otherwise.
        return int(id(self))
