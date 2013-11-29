from six.moves import configparser
from itertools import chain
import logging
import sys
import os
from errbot import PY2
from errbot.botplugin import BotPlugin
from errbot.utils import version2array, PY3
from errbot.templating import remove_plugin_templates_path, add_plugin_templates_path
from errbot.version import VERSION
from yapsy.PluginManager import PluginManager

# hardcoded directory for the system plugins
from errbot import holder

BUILTIN = str(os.path.dirname(os.path.abspath(__file__))) + os.sep + 'builtins'
if PY2:  # keys needs to be byte strings en shelves under python 2
    BUILTIN = BUILTIN.encode()


class IncompatiblePluginException(Exception):
    pass


class PluginConfigurationException(Exception):
    pass


def get_builtins(extra):
    # adds the extra plugin dir from the setup for developers convenience
    if extra:
        if isinstance(extra, list):
            return [BUILTIN] + extra
        return [BUILTIN, extra]
    else:
        return [BUILTIN]


def init_plugin_manager():
    global simplePluginManager

    if not holder.plugin_manager:
        logging.info('init plugin manager')
        simplePluginManager = PluginManager(categories_filter={"bots": BotPlugin})
        simplePluginManager.setPluginInfoExtension('plug')
        holder.plugin_manager = simplePluginManager
    else:
        simplePluginManager = holder.plugin_manager


init_plugin_manager()


def get_plugin_obj_by_name(name):
    pta_item = simplePluginManager.getPluginByName(name, 'bots')
    if pta_item is None:
        return None
    return pta_item.plugin_object


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
        logging.warning('Plugin %s has no section [Python]. Assuming this plugin is runnning only under python 2.' % name)
        python_version = '2'

    if python_version not in ('2', '2+', '3'):
        logging.warning('Plugin %s has an invalid Version specified in section [Python]. The Version can only be 2, 2+ and 3' % name)
        return None

    if python_version == '2' and PY3:
        logging.error('\nPlugin %s is made for python 2 only and you are running err under python 3.\n\n'
                      'If the plugin can be run on python 2 and 3 please add this section to its .plug descriptor :\n[Python]\nVersion=2+\n\n'
                      'Or if the plugin is Python 3 only:\n[Python]\nVersion=3\n\n' % name)
        return None

    if python_version == '3' and PY2:
        logging.error('\nPlugin %s is made for python 3 and you are running err under python 2.')
        return None

    obj = pta_item.plugin_object
    min_version, max_version = obj.min_err_version, obj.max_err_version
    logging.info('Activating %s with min_err_version = %s and max_version = %s' % (name, min_version, max_version))
    current_version = version2array(VERSION)
    if min_version and version2array(min_version) > current_version:
        raise IncompatiblePluginException('The plugin %s asks for err with a minimal version of %s while err is version %s' % (name, min_version, VERSION))

    if max_version and version2array(max_version) < current_version:
        raise IncompatiblePluginException('The plugin %s asks for err with a maximal version of %s while err is version %s' % (name, max_version, VERSION))

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


def update_plugin_places(list):
    from config import BOT_EXTRA_PLUGIN_DIR
    builtins = get_builtins(BOT_EXTRA_PLUGIN_DIR)
    for entry in chain(builtins, list):
        if entry not in sys.path:
            sys.path.append(entry)  # so the plugins can relatively import their submodules

    errors = [check_dependencies(path) for path in list]
    errors = [error for error in errors if error is not None]
    simplePluginManager.setPluginPlaces(chain(builtins, list))
    all_candidates = []

    def add_candidate(candidate):
        all_candidates.append(candidate)

    simplePluginManager.locatePlugins()
    #noinspection PyBroadException
    try:
        simplePluginManager.loadPlugins(add_candidate)
    except Exception as _:
        logging.exception("Error while loading plugins")

    return all_candidates, errors


def get_all_plugins():
    logging.debug("All plugins: %s" % simplePluginManager.getAllPlugins())
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
    #noinspection PyBroadException
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
                #noinspection PyBroadException
                try:
                    get_distribution(stripped)
                except Exception as _:
                    missing_pkg.append(stripped)
        if missing_pkg:
            return ('You need those dependencies for %s: ' % path) + ','.join(missing_pkg)
        return None
    except Exception as _:
        return 'You need to have setuptools installed for the dependency check of the plugins'
