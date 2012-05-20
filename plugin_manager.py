from itertools import chain
import logging
from botplugin import BotPlugin

__author__ = 'gbin'
from yapsy.PluginManager import PluginManager

# hardcoded directory for the system plugins
BUILTINS = ["builtins", ]

def init_plugin_manager():
    global simplePluginManager
    simplePluginManager = PluginManager(categories_filter={"bots": BotPlugin})
    simplePluginManager.setPluginInfoExtension('plug')

init_plugin_manager()

def update_plugin_places(list):
    simplePluginManager.setPluginPlaces(chain(BUILTINS,list))
    simplePluginManager.collectPlugins()

def activate_all_plugins():
    for pluginInfo in simplePluginManager.getAllPlugins():
        try:
            logging.info('Activate plugin %s' % pluginInfo.name)
            simplePluginManager.activatePluginByName(pluginInfo.name, "bots")
        except:
            logging.exception("Error loading %s" % pluginInfo.name)


def get_all_plugins():
    return simplePluginManager.getAllPlugins()


def get_all_active_plugin_names():
    return map(lambda p:p.name, filter(lambda p:p.is_activated, simplePluginManager.getAllPlugins()))


def get_active_plugin_names():
    return map(lambda p:p.name, simplePluginManager.getAllPlugins())


def deactivate_plugin(name):
    if name not in get_all_active_plugin_names():
        return "Plugin %s not in active list" % name
    simplePluginManager.deactivatePluginByName(name, "bots")
    return "Plugin %s deactivated" % name


def activate_plugin(name):
    if name in get_all_active_plugin_names():
        return "Plugin already in active list"
    if name not in get_active_plugin_names():
        return "I don't know this %s plugin" % name
    simplePluginManager.activatePluginByName(name, "bots")
    return "Plugin %s activated" % name

def deactivate_all_plugins():
    for name in get_all_active_plugin_names():
        simplePluginManager.deactivatePluginByName(name, "bots")

