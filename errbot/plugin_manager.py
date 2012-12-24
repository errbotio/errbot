from itertools import chain
import logging
import sys
import os
from errbot.botplugin import BotPlugin
from errbot.utils import version2array
from errbot.templating import remove_plugin_templates_path, add_plugin_templates_path
from errbot.version import VERSION
from config import BOT_EXTRA_PLUGIN_DIR

from yapsy.PluginManager import PluginManager

# hardcoded directory for the system plugins
BUILTINS = [os.path.dirname(os.path.abspath(__file__)) + os.sep + 'builtins', ]


class IncompatiblePluginException(Exception):
    pass


class PluginConfigurationException(Exception):
    pass

# adds the extra plugin dir from the setup for developpers convenience
if BOT_EXTRA_PLUGIN_DIR:
    if isinstance(BOT_EXTRA_PLUGIN_DIR, basestring):
        #noinspection PyTypeChecker
        BUILTINS.append(BOT_EXTRA_PLUGIN_DIR)
    else:
        BUILTINS.extend(BOT_EXTRA_PLUGIN_DIR)


def init_plugin_manager():
    global simplePluginManager
    simplePluginManager = PluginManager(categories_filter={"bots": BotPlugin})
    simplePluginManager.setPluginInfoExtension('plug')


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
        logging.warning('Could not activate %s')
        return None

    obj = pta_item.plugin_object
    min_version, max_version = obj.min_err_version, obj.max_err_version
    logging.info('Activating %s with min_err_version = %s and max_version = %s' % (name, min_version, max_version))
    current_version = version2array(VERSION)
    if min_version and version2array(min_version) > current_version:
        raise IncompatiblePluginException('The plugin %s asks for err with a minimal version of %s and err is %s' % (name, min_version, VERSION))

    if max_version and version2array(max_version) < current_version:
        raise IncompatiblePluginException('The plugin %s asks for err with a maximal version of %s and err is %s' % (name, max_version, VERSION))

    try:
        if obj.get_configuration_template() is not None and config is not None:
            logging.debug('Checking configuration for %s...' % name)
            obj.check_configuration(config)
            logging.debug('Configuration for %s checked OK.' % name)
        obj.configure(config)  # even if it is None we pass it on
    except Exception, e:
        logging.exception('Something is wrong with the configuration of the plugin %s' % name)
        obj.config = None
        raise PluginConfigurationException(str(e))
    add_plugin_templates_path(pta_item.path)
    populate_doc(pta_item)
    try:
        return simplePluginManager.activatePluginByName(name, "bots")
    except Exception as _:
        remove_plugin_templates_path(pta_item.path)
        raise


def deactivatePluginByName(name):
    pta_item = simplePluginManager.getPluginByName(name, 'bots')
    remove_plugin_templates_path(pta_item.path)
    try:
        return simplePluginManager.deactivatePluginByName(name, "bots")
    except Exception as _:
        add_plugin_templates_path(pta_item.path)
        raise


def update_plugin_places(list):
    for entry in chain(BUILTINS, list):
        if entry not in sys.path:
            sys.path.append(entry)  # so the plugins can relatively import their submodules

    errors = [check_dependencies(path) for path in list]
    errors = [error for error in errors if error is not None]
    simplePluginManager.setPluginPlaces(chain(BUILTINS, list))
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
    return simplePluginManager.getAllPlugins()


def get_all_active_plugin_objects():
    return [plug.plugin_object for plug in simplePluginManager.getAllPlugins() if hasattr(plug, 'is_activated') and plug.is_activated]


def get_all_active_plugin_names():
    return map(lambda p: p.name, filter(lambda p: hasattr(p, 'is_activated') and p.is_activated, simplePluginManager.getAllPlugins()))


def get_all_plugin_names():
    return map(lambda p: p.name, simplePluginManager.getAllPlugins())


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
