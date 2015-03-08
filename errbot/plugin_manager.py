from configparser import NoSectionError
from itertools import chain
import importlib
import fnmatch
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

# hardcoded directory for the system plugins
from . import holder

BUILTIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'builtins')

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
    plugin_roots = []
    for root, dirnames, filenames in os.walk(path):
        for filename in fnmatch.filter(filenames, '*.plug'):
            plugin_roots.append(os.path.dirname(os.path.join(root, filename)))
    return plugin_roots

def get_preloaded_plugins(extra):
    # adds the extra plugin dir from the setup for developers convenience
    all_builtins_and_extra = [BUILTIN]
    if extra:
        if isinstance(extra, list):
            for path in extra:
                all_builtins_and_extra.extend(find_plugin_roots(path))
        else:
            all_builtins_and_extra.extend(find_plugin_roots(extra))
    return all_builtins_and_extra


def init_plugin_manager():
    global simplePluginManager

    if not holder.plugin_manager:
        logging.debug('init plugin manager')
        simplePluginManager = PluginManager(categories_filter={"bots": BotPlugin})
        simplePluginManager.setPluginInfoExtension('plug')
        holder.plugin_manager = simplePluginManager
    else:
        simplePluginManager = holder.plugin_manager


init_plugin_manager()


def get_plugin_by_name(name):
    pta_item = simplePluginManager.getPluginByName(name, 'bots')
    if pta_item is None:
        return None
    return pta_item


def get_plugin_obj_by_name(name):
    plugin = get_plugin_by_name(name)
    return None if plugin is None else plugin.plugin_object


def populate_doc(plugin):
    plugin_type = type(plugin.plugin_object)
    plugin_type.__errdoc__ = plugin_type.__doc__ if plugin_type.__doc__ else plugin.description


def activate_plugin_with_version_check(name, config):
    pta_item = simplePluginManager.getPluginByName(name, 'bots')
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
        logging.error(
            '\nPlugin %s is made for python 2 only and you are running '
            'err under python 3.\n\n'
            'If the plugin can be run on python 2 and 3 please add this '
            'section to its .plug descriptor :\n[Python]\nVersion=2+\n\n'
            'Or if the plugin is Python 3 only:\n[Python]\nVersion=3\n\n' % name
        )
        return None

    if python_version == '3' and PY2:
        logging.error('\nPlugin %s is made for python 3 and you are running err under python 2.')
        return None

    obj = pta_item.plugin_object
    min_version, max_version = obj.min_err_version, obj.max_err_version
    logging.info('Activating %s with min_err_version = %s and max_version = %s' % (name, min_version, max_version))
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
            logging.debug('Checking configuration for %s...' % name)
            obj.check_configuration(config)
            logging.debug('Configuration for %s checked OK.' % name)
        obj.configure(config)  # even if it is None we pass it on
    except Exception as e:
        logging.exception('Something is wrong with the configuration of the plugin %s' % name)
        obj.config = None
        raise PluginConfigurationException(str(e))
    add_plugin_templates_path(pta_item.path)
    populate_doc(pta_item)
    try:
        return simplePluginManager.activatePluginByName(name, "bots")
    except Exception as _:
        pta_item.activated = False  # Yapsy doesn't revert this in case of error
        remove_plugin_templates_path(pta_item.path)
        logging.error("Plugin %s failed at activation stage, deactivating it..." % name)
        simplePluginManager.deactivatePluginByName(name, "bots")
        raise


def deactivate_plugin_by_name(name):
    pta_item = simplePluginManager.getPluginByName(name, 'bots')
    remove_plugin_templates_path(pta_item.path)
    try:
        return simplePluginManager.deactivatePluginByName(name, "bots")
    except Exception as _:
        add_plugin_templates_path(pta_item.path)
        raise


def reload_plugin_by_name(name):
    """
    Completely reload the given plugin, including reloading of the module's code
    """
    if name in get_all_active_plugin_names():
        deactivate_plugin_by_name(name)

    plugin = get_plugin_by_name(name)
    logging.critical(dir(plugin))
    module = __import__(plugin.path.split(os.sep)[-1])
    reload(module)

    class_name = type(plugin.plugin_object).__name__
    new_class = getattr(module, class_name)
    plugin.plugin_object.__class__ = new_class

def install_package(package):
    if hasattr(sys, 'real_prefix'):
        # this is a virtualenv, so we can use it directly
        pip.main(['install', package])
    else:
        # otherwise only install it as a user package
        pip.main(['install', '--user', package])
    globals()[package] = importlib.import_module(package)

def update_plugin_places(path_list, extra_plugin_dir, autoinstall_deps=True):
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
                logging.info("Trying to install an unmet dependency: %s" % dep)
                install_package(dep)
        errors =[]
    else:
        errors = [dependencies_result[0] for result in dependencies_result]
    errors = [error for error in errors if error is not None]
    simplePluginManager.setPluginPlaces(chain(builtins, path_list))
    all_candidates = []

    def add_candidate(candidate):
        all_candidates.append(candidate)

    simplePluginManager.locatePlugins()
    # noinspection PyBroadException
    try:
        simplePluginManager.loadPlugins(add_candidate)
    except Exception as _:
        logging.exception("Error while loading plugins")

    return all_candidates, errors


def get_all_plugins():
    logging.debug("All plugins: %s" % ', '.join([plug.name for plug in simplePluginManager.getAllPlugins()]))
    return simplePluginManager.getAllPlugins()


def get_all_active_plugin_objects():
    return [plug.plugin_object for plug in get_all_plugins() if hasattr(plug, 'is_activated') and plug.is_activated]


def get_all_active_plugin_names():
    return [p.name for p in get_all_plugins() if hasattr(p, 'is_activated') and p.is_activated]


def get_all_plugin_names():
    return [p.name for p in get_all_plugins()]


def deactivate_all_plugins():
    for name in get_all_active_plugin_names():
        simplePluginManager.deactivatePluginByName(name, "bots")


def global_restart():
    python = sys.executable
    os.execl(python, python, *sys.argv)


def check_dependencies(path):
    """ This methods returns a pair of (message, packages missing).
    Or None if everything is OK.
    """
    logging.debug("check dependencies of %s" % path)
    # noinspection PyBroadException
    try:
        from pkg_resources import get_distribution

        req_path = path + os.sep + 'requirements.txt'
        if not os.path.isfile(req_path):
            logging.debug('%s has no requirements.txt file' % path)
            return None
        missing_pkg = []
        with open(req_path) as f:
            for line in f:
                stripped = line.strip()
                # noinspection PyBroadException
                try:
                    get_distribution(stripped)
                except Exception as _:
                    missing_pkg.append(stripped)
        if missing_pkg:
            return (('You need those dependencies for %s: ' % path) + ','.join(missing_pkg),
                    missing_pkg)
        return None
    except Exception as _:
        return ('You need to have setuptools installed for the dependency check of the plugins', [])
