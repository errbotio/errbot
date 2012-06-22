from itertools import chain
import logging
import sys, os
from errbot.botplugin import BotPlugin
from errbot.version import VERSION
from config import BOT_EXTRA_PLUGIN_DIR

__author__ = 'gbin'
from yapsy.PluginManager import PluginManager

# hardcoded directory for the system plugins
BUILTINS = [os.path.dirname(os.path.abspath(__file__)) + os.sep + 'builtins', ]

class IncompatiblePluginException(Exception):
    pass

# adds the extra plugin dir from the setup for developpers convenience
if BOT_EXTRA_PLUGIN_DIR:
    BUILTINS.append(BOT_EXTRA_PLUGIN_DIR)

def init_plugin_manager():
    global simplePluginManager
    simplePluginManager = PluginManager(categories_filter={"bots": BotPlugin})
    simplePluginManager.setPluginInfoExtension('plug')

init_plugin_manager()

def version2array(version):
    response = [int(el) for el in version.split('.')]
    if len(response) != 3:
        raise Exception('version %s in not in format "x.y.z" for example "1.2.2"' % version)
    return response


def activate_plugin_with_version_check(name):
    pta_item = simplePluginManager.getPluginByName(name, 'bots')
    if pta_item is None:
        logging.warning('Could not active %s')
        return None

    obj = pta_item.plugin_object
    min_version, max_version = obj.min_err_version, obj.max_err_version
    logging.info('Activating %s with min_err_version = %s and max_version = %s' % (name, min_version, max_version))
    current_version = version2array(VERSION)
    if min_version and version2array(min_version) > current_version:
        raise IncompatiblePluginException('The plugin %s asks for err with a minimal version of %s and err is %s' % (name, min_version, VERSION))

    if max_version and version2array(max_version) < current_version:
        raise IncompatiblePluginException('The plugin %s asks for err with a maximal version of %s and err is %s' % (name, min_version, VERSION))
    return simplePluginManager.activatePluginByName(name, "bots")


def update_plugin_places(list):
    for entry in chain(BUILTINS, list):
        if entry not in sys.path:
            sys.path.append(entry) # so the plugins can relatively import their submodules

    simplePluginManager.setPluginPlaces(chain(BUILTINS, list))
    simplePluginManager.collectPlugins()


def activate_all_plugins():
    for pluginInfo in simplePluginManager.getAllPlugins():
        try:
            if hasattr(pluginInfo, 'is_activated') and not pluginInfo.is_activated:
                logging.info('Activate plugin %s' % pluginInfo.name)
                activate_plugin_with_version_check(pluginInfo.name)
        except Exception, e:
            logging.exception("Error loading %s" % pluginInfo.name)


def get_all_plugins():
    return simplePluginManager.getAllPlugins()


def get_all_active_plugin_objects():
    return [plug.plugin_object for plug in simplePluginManager.getAllPlugins() if hasattr(plug, 'is_activated') and plug.is_activated]


def get_all_active_plugin_names():
    return map(lambda p: p.name, filter(lambda p: hasattr(p, 'is_activated') and p.is_activated, simplePluginManager.getAllPlugins()))


def get_all_plugin_names():
    return map(lambda p: p.name, simplePluginManager.getAllPlugins())


def deactivate_plugin(name):
    if name not in get_all_active_plugin_names():
        return "Plugin %s not in active list" % name
    simplePluginManager.deactivatePluginByName(name, "bots")
    return "Plugin %s deactivated" % name


def activate_plugin(name):
    if name in get_all_active_plugin_names():
        return "Plugin already in active list"
    if name not in get_all_plugin_names():
        return "I don't know this %s plugin" % name
    activate_plugin_with_version_check(name)
    return "Plugin %s activated" % name


def deactivate_all_plugins():
    for name in get_all_active_plugin_names():
        simplePluginManager.deactivatePluginByName(name, "bots")


def global_restart():
    python = sys.executable
    os.execl(python, python, *sys.argv)
