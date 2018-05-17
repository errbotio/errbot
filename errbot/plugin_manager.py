""" Logic related to plugin loading and lifecycle """
from configparser import ConfigParser

from importlib import machinery, import_module
import logging
import os
import subprocess
import sys
import traceback

from typing import Tuple, Sequence

from errbot.flow import BotFlow
from .botplugin import BotPlugin
from .plugin_info import PluginInfo
from .utils import version2tuple, collect_roots
from .templating import remove_plugin_templates_path, add_plugin_templates_path
from .version import VERSION
from .core_plugins.wsview import route
from .storage import StoreMixin

log = logging.getLogger(__name__)

CORE_PLUGINS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'core_plugins')

BOTPLUGIN_TAG = 'botplugin'
BOTFLOW_TAG = 'botflow'

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
       :param base_paths:
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


def install_packages(req_path):
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
    try:
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and (sys.base_prefix != sys.prefix)):
            # this is a virtualenv, so we can use it directly
            subprocess.check_call(pip_cmdline + ['install', '--requirement', req_path])
        else:
            # otherwise only install it as a user package
            subprocess.check_call(pip_cmdline + ['install', '--user', '--requirement', req_path])
    except Exception:
        log.exception('Failed to execute pip install for %s.', req_path)
        return sys.exc_info()


def check_dependencies(req_path: str) -> Tuple[str, Sequence[str]]:
    """ This methods returns a pair of (message, packages missing).
    Or None, [] if everything is OK.In order to let us help you better, please fill out the following fields as best you can:
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


def check_enabled_core_plugin(plugin_info: PluginInfo, core_plugin_list) -> bool:
    """ Checks if the given plugin is core and if it is, if it is part of the enabled core_plugins_list.
    :param plugin_info: the info from the plugin
    :param core_plugin_list: the list from CORE_PLUGINS in the config.
    :return: True if it is OK to load this plugin.
    """
    return plugin_info.core and plugin_info.name in core_plugin_list


def check_python_plug_section(plugin_info: PluginInfo) -> bool:
    """ Checks if we have the correct version to run this plugin.
    Returns true if the plugin is loadable """
    version = plugin_info.python_version
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
    name, min_version, max_version = plugin_info.name, plugin_info.min_version, plugin_info.max_version
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



# TODO: move this out, this has nothing to do with plugins
def global_restart():
    python = sys.executable
    os.execl(python, python, *sys.argv)


class BotPluginManager(StoreMixin):
    # Storage names
    CONFIGS = 'configs'
    BL_PLUGINS = 'bl_plugins'

    def __init__(self, storage_plugin, repo_manager, extra, autoinstall_deps, core_plugins, plugins_callback_order):
        self.bot = None
        self.autoinstall_deps = autoinstall_deps
        self.extra = extra
        self.open_storage(storage_plugin, 'core')
        self.core_plugins = core_plugins
        self.plugins_callback_order = plugins_callback_order
        self.repo_manager = repo_manager

        # be sure we have a configs entry for the plugin configurations
        if self.CONFIGS not in self:
            self[self.CONFIGS] = {}

        self.plug_infos = {}  # Name ->  PluginInfo
        self.plugins = {}  # Name ->  BotPlugin
        self.flows = {}  # Name ->  Flow
        #locator = PluginFileLocator([PluginFileAnalyzerWithInfoFile("info_ext", 'plug'),
        #                            PluginFileAnalyzerWithInfoFile("info_ext", 'flow')])

    def attach_bot(self, bot):
        self.bot = bot

    #def instanciateElement(self, element) -> BotPlugin:
    #    """Overrides the instanciation of plugins to inject the bot reference."""
    #    return element(self.bot, name=self._current_pluginfo.name)

    def activate_plugin(self, name: str):
        obj = self.get_plugin_obj_by_name(name)
        obj.activate()

    def deactivate_plugin(self, name: str):
        obj, path = self.plugins[name]
        # TODO handle the "un"routing.

        remove_plugin_templates_path(path)
        try:
            return obj.deactivate()
        except Exception:
            add_plugin_templates_path(path)
            raise

    def get_plugin_obj_by_name(self, name: str) -> BotPlugin:
        obj, _ = self.plugins.get(name, (None, None))
        return obj

    def activate_plugin_with_version_check(self, plugin_object: BotPlugin, plugin_info: PluginInfo, dep_track=None) -> BotPlugin:
        name = plugin_info.name

        config = self.get_plugin_configuration(name)

        if not check_python_plug_section(plugin_info):
            return None

        if not check_errbot_version(plugin_info):
            return None

        depends_on = self._activate_plugin_dependencies(name, plug, dep_track)

        obj = plugin_object

        obj.dependencies = depends_on

        try:
            if obj.get_configuration_template() is not None and config is not None:
                log.debug('Checking configuration for %s...', name)
                obj.check_configuration(config)
                log.debug('Configuration for %s checked OK.', name)
            obj.configure(config)  # even if it is None we pass it on
        except Exception as ex:
            log.exception('Something is wrong with the configuration of the plugin %s', name)
            obj.config = None
            raise PluginConfigurationException(str(ex))
        plugin_path = os.path.dirname(sys.modules[plugin_object.__class__.__module__].__file__)
        add_plugin_templates_path(plugin_path)
        populate_doc(obj, plug)
        try:
            self.activate_plugin(name)
            route(obj)
            return obj
        except Exception:
            remove_plugin_templates_path(plugin_path)
            log.error("Plugin %s failed at activation stage, deactivating it...", name)
            self.deactivate_plugin(name)
            raise

    def _activate_plugin_dependencies(self, name: str, plug: ConfigParser, dep_track):
        try:
            if dep_track is None:
                dep_track = set()

            dep_track.add(name)

            depends_on = [dep_name.strip() for dep_name in plug.get("Core", "DependsOn").split(',')]
            for dep_name in depends_on:
                if dep_name in dep_track:
                    raise PluginActivationException("Circular dependency in the set of plugins (%s)" %
                                                    ', '.join(dep_track))
                if dep_name not in self.get_all_active_plugin_names():
                    log.debug('%s depends on %s and %s is not activated. Activating it ...', name, dep_name,
                              dep_name)
                    self._activate_plugin(dep_name, dep_track)
            return depends_on
        except NoOptionError:
            return []

    def reload_plugin_by_name(self, name):
        """
        Completely reload the given plugin, including reloading of the module's code
        :throws PluginActivationException: needs to be taken care of by the callers.
        """
        was_activated = name in self.get_all_active_plugin_names()

        if was_activated:
            self.deactivate_plugin_by_name(name)

        plugin = self.get_plugin_by_name(name)

        module_alias = plugin.plugin_object.__module__
        module_old = __import__(module_alias)
        f = module_old.__file__
        module_new = machinery.SourceFileLoader(module_alias, f).load_module(module_alias)
        class_name = type(plugin.plugin_object).__name__
        new_class = getattr(module_new, class_name)
        plugin.plugin_object.__class__ = new_class

        if was_activated:
            self.activate_plugin(name)

    def _plugin_info_currently_loading(self, pluginfo):
        # Keeps track of what is the current plugin we are attempting to load.
        self._current_pluginfo = pluginfo

    def update_plugin_places(self, path_list, extra_plugin_dir, autoinstall_deps=True):
        """ It returns a dictionary of path -> error strings."""
        repo_roots = (CORE_PLUGINS, extra_plugin_dir, path_list)

        all_roots = collect_roots(repo_roots)

        log.debug("All plugin roots:")
        for entry in all_roots:
            log.debug("-> %s", entry)
            if entry not in sys.path:
                log.debug("Add %s to sys.path", entry)
                sys.path.append(entry)
        # so plugins can relatively import their repos
        _ensure_sys_path_contains(repo_roots)

        errors = {}
        if autoinstall_deps:
            for path in all_roots:
                req_path = os.path.join(path, 'requirements.txt')
                if not os.path.isfile(req_path):
                    log.debug('%s has no requirements.txt file' % path)
                    continue
                exc_info = install_packages(req_path)
                if exc_info is not None:
                    typ, value, trace = exc_info
                    errors[path] = '%s: %s\n%s' % (typ, value, ''.join(traceback.format_tb(trace)))
        else:
            dependencies_result = {path: check_dependencies(path)[0] for path in all_roots}
            errors.update({path: dep_error for path, dep_error in dependencies_result.items() if dep_error is not None})
        self.setPluginPlaces(all_roots)
        try:
            self.locatePlugins()
        except ValueError:
            # See https://github.com/errbotio/errbot/issues/769.
            # Unfortunately we cannot obtain information on which file specifically caused the issue,
            # but we can point users in the right direction at least.
            log.error(
                "ValueError was raised while scanning directories for plugins. "
                "This typically happens when your bot and/or plugin directories contain "
                "badly formatted .plug files. To help troubleshoot, we suggest temporarily "
                "removing all data and plugins from your bot and then trying again."
            )
            raise

        # Checks if CORE_PLUGINS is defined in config. If so, iterate through plugin candidates and remove any
        # that are not defined in the config before loading them.
        if self.core_plugins is not None:
            candidates = self.getPluginCandidates()
            for candidate in candidates:
                if not check_enabled_core_plugin(candidate[2].name, candidate[2].details, self.core_plugins):
                    self.removePluginCandidate(candidate)
                    log.debug("%s plugin will not be loaded because it's not listed in CORE_PLUGINS", candidate[2].name)

        self.all_candidates = [candidate[2] for candidate in self.getPluginCandidates()]

        loaded_plugins = self.loadPlugins(self._plugin_info_currently_loading)

        errors.update({pluginfo.path: ''.join(traceback.format_tb(pluginfo.error[2]))
                       for pluginfo in loaded_plugins if pluginfo.error is not None})
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
                    p.plugin_object for p in self.getPluginsOfCategory(BOTPLUGIN_TAG)
                    if p.name not in self.plugins_callback_order and hasattr(p, 'is_activated') and p.is_activated
                ]
            else:
                p = self.get_plugin_by_name(name)
                if p is not None and hasattr(p, 'is_activated') and p.is_activated:
                    all_plugins.append(p.plugin_object)
        return all_plugins

    def get_all_active_plugin_objects(self):
        return [plug.plugin_object
                for plug in self.getPluginsOfCategory(BOTPLUGIN_TAG)
                if hasattr(plug, 'is_activated') and plug.is_activated]

    def get_all_active_plugin_names(self):
        return [p.name for p in self.getAllPlugins() if hasattr(p, 'is_activated') and p.is_activated]

    def get_all_plugin_names(self):
        return [p.name for p in self.getPluginsOfCategory(BOTPLUGIN_TAG)]

    def deactivate_all_plugins(self):
        for name in self.get_all_active_plugin_names():
            self.deactivatePluginByName(name, BOTPLUGIN_TAG)

    # plugin blacklisting management
    def get_blacklisted_plugin(self):
        return self.get(self.BL_PLUGINS, [])

    def is_plugin_blacklisted(self, name):
        return name in self.get_blacklisted_plugin()

    def blacklist_plugin(self, name):
        if self.is_plugin_blacklisted(name):
            logging.warning('Plugin %s is already blacklisted' % name)
            return 'Plugin %s is already blacklisted' % name
        self[self.BL_PLUGINS] = self.get_blacklisted_plugin() + [name]
        log.info('Plugin %s is now blacklisted' % name)
        return 'Plugin %s is now blacklisted' % name

    def unblacklist_plugin(self, name):
        if not self.is_plugin_blacklisted(name):
            logging.warning('Plugin %s is not blacklisted' % name)
            return 'Plugin %s is not blacklisted' % name
        plugin = self.get_blacklisted_plugin()
        plugin.remove(name)
        self[self.BL_PLUGINS] = plugin
        log.info('Plugin %s removed from blacklist' % name)
        return 'Plugin %s removed from blacklist' % name

    # configurations management
    def get_plugin_configuration(self, name):
        configs = self[self.CONFIGS]
        if name not in configs:
            return None
        return configs[name]

    def set_plugin_configuration(self, name, obj):
        configs = self[self.CONFIGS]
        configs[name] = obj
        self[self.CONFIGS] = configs

    # this will load the plugins the admin has setup at runtime
    def update_dynamic_plugins(self):
        """ It returns a dictionary of path -> error strings."""
        return self.update_plugin_places(self.repo_manager.get_all_repos_paths(), self.extra, self.autoinstall_deps)

    def activate_non_started_plugins(self):
        """
        Activates all plugins that are not activated, respecting its dependencies.

        :return: Empty string if no problem occured or a string explaining what went wrong.
        """
        log.info('Activate bot plugins...')
        errors = ''
        for pluginInfo in self.getPluginsOfCategory(BOTPLUGIN_TAG):
            try:
                if self.is_plugin_blacklisted(pluginInfo.name):
                    errors += 'Notice: %s is blacklisted, use %splugin unblacklist %s to unblacklist it\n' % (
                        pluginInfo.name, self.bot.prefix, pluginInfo.name)
                    continue
                if hasattr(pluginInfo, 'is_activated') and not pluginInfo.is_activated:
                    log.info('Activate plugin: %s' % pluginInfo.name)
                    self.activate_plugin_with_version_check(pluginInfo)
            except Exception as e:
                log.exception("Error loading %s" % pluginInfo.name)
                errors += 'Error: %s failed to start: %s\n' % (pluginInfo.name, e)

        log.debug('Activate flow plugins ...')
        for pluginInfo in self.getPluginsOfCategory(BOTFLOW_TAG):
            try:
                if hasattr(pluginInfo, 'is_activated') and not pluginInfo.is_activated:
                    name = pluginInfo.name

                    log.info('Activate flow: %s' % name)

                    pta_item = self.getPluginByName(name, BOTFLOW_TAG)
                    if pta_item is None:
                        log.warning('Could not activate %s', name)
                        continue
                    try:
                        self.activatePluginByName(name, BOTFLOW_TAG)
                    except Exception as e:
                        pta_item.activated = False  # Yapsy doesn't revert this in case of error
                        log.error("Plugin %s failed at activation stage with e, deactivating it...", e, name)
                        self.deactivatePluginByName(name, BOTFLOW_TAG)
            except Exception as e:
                log.exception("Error loading flow %s" % pluginInfo.name)
                errors += 'Error: flow %s failed to start: %s\n' % (pluginInfo.name, e)
        return errors

    def activate_plugin(self, name):
        """
        Activate the given plugin.

        :param name: the name of the plugin you want to activate.
        :throws PluginActivationException: if an error occured while activating the plugin.
        """
        self._activate_plugin(name)

    def _activate_plugin(self, name, dep_track=None):
        """
        Internal recursive version of activate_plugin.
        """
        try:
            if name in self.get_all_active_plugin_names():
                raise PluginActivationException("Plugin already in active list")
            if name not in self.get_all_plugin_names():
                raise PluginActivationException("I don't know this %s plugin" % name)
            plugin_info = self.get_plugin_by_name(name)
            if plugin_info is None:
                raise PluginActivationException("get_plugin_by_name did not find %s (should not happen)." % name)
            self.activate_plugin_with_version_check(plugin_info, dep_track)
            plugin_info.plugin_object.callback_connect()
        except PluginActivationException:
            raise
        except Exception as e:
            log.exception("Error loading %s" % name)
            raise PluginActivationException('%s failed to start : %s\n' % (name, e))

    def deactivate_plugin(self, name):
        self.deactivate_plugin_by_name(name)

    def remove_plugin(self, plugin):
        """
        Deactivate and remove a plugin completely.
        :param plugin: the plugin to remove
        :return:
        """
        # First deactivate it if it was activated
        if hasattr(plugin, 'is_activated') and plugin.is_activated:
            self.deactivate_plugin(plugin.name)

        # Remove it from the candidate list (so it doesn't appear as a failed plugin)
        self.all_candidates.remove(plugin)

        # Remove it from yapsy itself
        for category, plugins in self.category_mapping.items():
            if plugin in plugins:
                log.debug('plugin found and removed from category %s', category)
                plugins.remove(plugin)

    def remove_plugins_from_path(self, root):
        """
        Remove all the plugins that are in the filetree pointed by root.
        """
        for plugin in self.getAllPlugins():
            if plugin.path.startswith(root):
                self.remove_plugin(plugin)

    def shutdown(self):
        log.info('Shutdown.')
        self.close_storage()
        log.info('Bye.')

    def __hash__(self):
        # Ensures this class (and subclasses) are hashable.
        # Presumably the use of mixins causes __hash__ to be
        # None otherwise.
        return int(id(self))
