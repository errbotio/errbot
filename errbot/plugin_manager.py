from configparser import NoSectionError
from itertools import chain
import importlib
import fnmatch
import inspect
import logging
import sys
import os
import pip
from . import PY2
from .botplugin import BotPlugin
from .utils import version2array, PY3
from .templating import remove_plugin_templates_path, add_plugin_templates_path
from .version import VERSION
from yapsy.PluginManager import PluginManager
from .core_plugins.wsview import route

log = logging.getLogger(__name__)

CORE_PLUGINS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'core_plugins')

try:
    from importlib import reload  # new in python 3.4
except ImportError:
    from imp import reload


class IncompatiblePluginException(Exception):
    pass


class PluginConfigurationException(Exception):
    pass


def find_plugin_roots(path):
    """ Recursively find the plugins from the given path.
    It is usefull so you can give a root directory of checked out plugins and
    it will discover them automatically.
    """
    plugin_roots = set()  # you can have several .plug per directory.
    for root, dirnames, filenames in os.walk(path):
        for filename in fnmatch.filter(filenames, '*.plug'):
            plugin_roots.add(os.path.dirname(os.path.join(root, filename)))
    return plugin_roots


def get_preloaded_plugins(extra):
    # adds the extra plugin dir from the setup for developers convenience
    all_builtins_and_extra = [CORE_PLUGINS]
    if extra:
        if isinstance(extra, list):
            for path in extra:
                all_builtins_and_extra.extend(find_plugin_roots(path))
        else:
            all_builtins_and_extra.extend(find_plugin_roots(extra))
    return all_builtins_and_extra


def populate_doc(plugin):
    plugin_type = type(plugin.plugin_object)
    plugin_type.__errdoc__ = plugin_type.__doc__ if plugin_type.__doc__ else plugin.description


def install_package(package):
    if hasattr(sys, 'real_prefix'):
        # this is a virtualenv, so we can use it directly
        pip.main(['install', package])
    else:
        # otherwise only install it as a user package
        pip.main(['install', '--user', package])
    globals()[package] = importlib.import_module(package)


def check_dependencies(path):
    """ This methods returns a pair of (message, packages missing).
    Or None if everything is OK.
    """
    log.debug("check dependencies of %s" % path)
    # noinspection PyBroadException
    try:
        from pkg_resources import get_distribution

        req_path = path + os.sep + 'requirements.txt'
        if not os.path.isfile(req_path):
            log.debug('%s has no requirements.txt file' % path)
            return None
        missing_pkg = []
        with open(req_path) as f:
            for line in f:
                stripped = line.strip()
                # noinspection PyBroadException
                try:
                    get_distribution(stripped)
                except Exception:
                    missing_pkg.append(stripped)
        if missing_pkg:
            return (('You need those dependencies for %s: ' % path) + ','.join(missing_pkg),
                    missing_pkg)
        return None
    except Exception:
        return ('You need to have setuptools installed for the dependency check of the plugins', [])


def global_restart():
    python = sys.executable
    os.execl(python, python, *sys.argv)


class BotPluginManager(PluginManager):
    """Customized yapsy PluginManager for ErrBot."""
    def _init_plugin_manager(self):
        self.setCategoriesFilter({"bots": BotPlugin})
        plugin_locator = self._locatorDecide('plug', None)
        self.setPluginLocator(plugin_locator, None)

    def instanciateElement(self, element):
        """ Override the loading method to inject bot """
        # check if we have a plugin not overridding __init__ incorrectly
        args, argslist, kwargs, _ = inspect.getargspec(element.__init__)

        log.debug('plugin __init__(args=%s, argslist=%s, kwargs=%s)' % (args, argslist, kwargs))
        if len(args) == 1 and argslist is None and kwargs is None:
            log.warn(('Warning: %s needs to implement __init__(self, *args, **kwargs) '
                      'and forward them to super().__init__') % element.__name__)
            obj = element()
            obj._load_bot(self)  # sideload the bot
            return obj

        return element(self)

    def get_plugin_by_name(self, name):
        plugin = self.getPluginByName(name, 'bots')
        if plugin is None:
            return None
        return plugin

    def get_plugin_obj_by_name(self, name):
        plugin = self.get_plugin_by_name(name)
        return None if plugin is None else plugin.plugin_object

    def activate_plugin_with_version_check(self, name, config):
        pta_item = self.getPluginByName(name, 'bots')
        if pta_item is None:
            logging.warning('Could not activate %s' % name)
            return None

        try:
            python_version = pta_item.details.get("Python", "Version")
        except NoSectionError:
            logging.warning(
                'Plugin %s has no section [Python]. Assuming this '
                'plugin is runnning only under python 2.' % name
            )
            python_version = '2'

        if python_version not in ('2', '2+', '3'):
            logging.warning(
                'Plugin %s has an invalid Version specified in section [Python]. '
                'The Version can only be 2, 2+ and 3' % name
            )
            return None

        if python_version == '2' and PY3:
            log.error(
                '\nPlugin %s is made for python 2 only and you are running '
                'err under python 3.\n\n'
                'If the plugin can be run on python 2 and 3 please add this '
                'section to its .plug descriptor :\n[Python]\nVersion=2+\n\n'
                'Or if the plugin is Python 3 only:\n[Python]\nVersion=3\n\n' % name
            )
            return None

        if python_version == '3' and PY2:
            log.error('\nPlugin %s is made for python 3 and you are running err under python 2.')
            return None

        obj = pta_item.plugin_object
        min_version, max_version = obj.min_err_version, obj.max_err_version
        log.info('Activating %s with min_err_version = %s and max_version = %s' % (name, min_version, max_version))
        current_version = version2array(VERSION)
        if min_version and version2array(min_version) > current_version:
            raise IncompatiblePluginException(
                'The plugin %s asks for err with a minimal version of %s while err is version %s' % (
                    name, min_version, VERSION)
            )

        if max_version and version2array(max_version) < current_version:
            raise IncompatiblePluginException(
                'The plugin %s asks for err with a maximal version of %s while err is version %s' % (
                    name, max_version, VERSION)
            )

        try:
            if obj.get_configuration_template() is not None and config is not None:
                log.debug('Checking configuration for %s...' % name)
                obj.check_configuration(config)
                log.debug('Configuration for %s checked OK.' % name)
            obj.configure(config)  # even if it is None we pass it on
        except Exception as e:
            log.exception('Something is wrong with the configuration of the plugin %s' % name)
            obj.config = None
            raise PluginConfigurationException(str(e))
        add_plugin_templates_path(pta_item.path)
        populate_doc(pta_item)
        try:
            obj = self.activatePluginByName(name, "bots")
            route(obj)
            return obj
        except Exception:
            pta_item.activated = False  # Yapsy doesn't revert this in case of error
            remove_plugin_templates_path(pta_item.path)
            log.error("Plugin %s failed at activation stage, deactivating it..." % name)
            self.deactivatePluginByName(name, "bots")
            raise

    def deactivate_plugin_by_name(self, name):
        # TODO handle the "un"routing.

        pta_item = self.getPluginByName(name, 'bots')
        remove_plugin_templates_path(pta_item.path)
        try:
            return self.deactivatePluginByName(name, "bots")
        except Exception:
            add_plugin_templates_path(pta_item.path)
            raise

    def reload_plugin_by_name(self, name):
        """
        Completely reload the given plugin, including reloading of the module's code
        """
        if name in self.get_all_active_plugin_names():
            self.deactivate_plugin_by_name(name)

        plugin = self.get_plugin_by_name(name)
        logging.critical(dir(plugin))
        module = __import__(plugin.path.split(os.sep)[-1])
        reload(module)

        class_name = type(plugin.plugin_object).__name__
        new_class = getattr(module, class_name)
        plugin.plugin_object.__class__ = new_class

    def update_plugin_places(self, path_list, extra_plugin_dir, autoinstall_deps=True):
        builtins = get_preloaded_plugins(extra_plugin_dir)
        paths = builtins + path_list
        for entry in paths:
            if entry not in sys.path:
                sys.path.append(entry)  # so plugins can relatively import their submodules
        dependencies_result = [check_dependencies(path) for path in paths]
        deps_to_install = set()
        if autoinstall_deps:
            for result in dependencies_result:
                if result:
                    deps_to_install.update(result[1])
            if deps_to_install:
                for dep in deps_to_install:
                    log.info("Trying to install an unmet dependency: %s" % dep)
                    install_package(dep)
            errors = []
        else:
            errors = [result[0] for result in dependencies_result if result is not None]
        self.setPluginPlaces(chain(builtins, path_list))
        all_candidates = []

        def add_candidate(candidate):
            all_candidates.append(candidate)

        self.locatePlugins()
        # noinspection PyBroadException
        try:
            self.loadPlugins(add_candidate)
        except Exception:
            log.exception("Error while loading plugins")

        return all_candidates, errors

    def get_all_active_plugin_objects(self):
        return [plug.plugin_object
                for plug in self.getAllPlugins()
                if hasattr(plug, 'is_activated') and plug.is_activated]

    def get_all_active_plugin_names(self):
        return [p.name for p in self.getAllPlugins() if hasattr(p, 'is_activated') and p.is_activated]

    def get_all_plugin_names(self):
        return [p.name for p in self.getAllPlugins()]

    def deactivate_all_plugins(self):
        for name in self.get_all_active_plugin_names():
            self.deactivatePluginByName(name, "bots")
