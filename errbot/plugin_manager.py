from itertools import chain
import logging
import sys, os
from errbot.botplugin import BotPlugin
from errbot.utils import version2array
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
    BUILTINS.append(BOT_EXTRA_PLUGIN_DIR)

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

def activate_plugin_with_version_check(name, config):
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

    try:
        obj.configure(config) # even if it is None we pass it on
    except Exception, e:
        logging.exception('Something is wrong with the configuration of the plugin %s' % name)
        obj.config = None
        raise PluginConfigurationException(str(e))

    return simplePluginManager.activatePluginByName(name, "bots")


def update_plugin_places(list):
    for entry in chain(BUILTINS, list):
        if entry not in sys.path:
            sys.path.append(entry) # so the plugins can relatively import their submodules

    errors = [check_dependencies(path) for path in list]
    errors = [error for error in errors if error is not None]
    simplePluginManager.setPluginPlaces(chain(BUILTINS, list))
    simplePluginManager.collectPlugins()
    return errors


def activate_all_plugins(configs):
    errors = ''
    for pluginInfo in simplePluginManager.getAllPlugins():
        try:
            if hasattr(pluginInfo, 'is_activated') and not pluginInfo.is_activated:
                logging.info('Activate plugin %s' % pluginInfo.name)
                activate_plugin_with_version_check(pluginInfo.name, configs.get(pluginInfo.name, None))
        except Exception, e:
            logging.exception("Error loading %s" % pluginInfo.name)
            errors += '%s failed to start : %s\n' % (pluginInfo.name ,e)
    return errors

def get_all_plugins():
    return simplePluginManager.getAllPlugins()


def get_all_active_plugin_objects():
    return [plug.plugin_object for plug in simplePluginManager.getAllPlugins() if hasattr(plug, 'is_activated') and plug.is_activated]


def get_all_active_plugin_names():
    return map(lambda p: p.name, filter(lambda p: hasattr(p, 'is_activated') and p.is_activated, simplePluginManager.getAllPlugins()))


def get_all_plugin_names():
    return map(lambda p: p.name, simplePluginManager.getAllPlugins())

def deactivatePluginByName(name):
    return simplePluginManager.deactivatePluginByName(name, "bots")


def deactivate_all_plugins():
    for name in get_all_active_plugin_names():
        simplePluginManager.deactivatePluginByName(name, "bots")


def global_restart():
    python = sys.executable
    os.execl(python, python, *sys.argv)

def check_dependencies(path):
    try:
        from pkg_resources import get_distribution
        req_path = path + os.sep + 'requirements.txt'
        if not os.path.isfile(req_path):
            logging.debug('%s has no requirements.txt file' % path)
            return None
        missing_pkg = []
        with open(req_path) as f:
            for line in f:
                stripped= line.strip()
                try:
                    get_distribution(stripped)
                except Exception as e:
                    missing_pkg.append(stripped)
        if missing_pkg:
            return ('You need those dependencies for %s: ' % path) + ','.join(missing_pkg)
        return None
    except Exception as e:
        return 'You need to have setuptools installed for the dependency check of the plugins'
