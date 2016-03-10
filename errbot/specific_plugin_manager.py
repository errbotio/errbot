import logging
import sys

import traceback
from yapsy.PluginManager import PluginManager
from yapsy.PluginFileLocator import PluginFileLocator, PluginFileAnalyzerWithInfoFile

from .utils import collect_roots

log = logging.getLogger(__name__)


class SpecificPluginLocator(PluginFileAnalyzerWithInfoFile):
    """
    This is a plugin locator (kind of filter in yapsy jargon) to match a backend.
    We have to go through hoops because yapsy is really aggressive at instanciating plugin.
    (this would instanciate several bots, we don't want to do that).
    """
    def __init__(self, name_to_find):
        super().__init__('SpecificBackendLocator', 'plug')
        self._name_to_find = name_to_find

    def getInfosDictFromPlugin(self, dirpath, filename):
        plugin_info_dict, config_parser = super().getInfosDictFromPlugin(dirpath, filename)
        if plugin_info_dict['name'] != self._name_to_find:
            # reject
            return None, config_parser
        return plugin_info_dict, config_parser


class SpecificPluginManager(PluginManager):
    """ SpecificPluginManager is a customized plugin manager to enumerate plugins
        and load only a specific one.
    """
    def __init__(self, bot_config, category, base_class, base_search_dir, extra_search_dirs=()):
        self._config = bot_config
        # set a locator that gets every possible backends as a first discovery pass.
        self._locator = PluginFileLocator(analyzers=[PluginFileAnalyzerWithInfoFile('SpecificLocator', 'plug')])
        self._locator.disableRecursiveScan()  # This is done below correctly with find_roots_with_extra
        super().__init__(plugin_locator=self._locator)
        self.setCategoriesFilter({category: base_class})

        all_plugins_paths = collect_roots((base_search_dir, extra_search_dirs))
        log.info('%s search paths %s', category, all_plugins_paths)
        self.setPluginPlaces(all_plugins_paths)
        for entry in all_plugins_paths:
            if entry not in sys.path:
                sys.path.append(entry)  # so backends can relatively import their submodules
        self.locatePlugins()
        log.info('Found those plugings available:')
        for (_, _, plug) in self.getPluginCandidates():
            log.info('\t%10s  (%s)' % (plug.name, plug.path + '.py'))

    def instanciateElement(self, element):
        """ Override the loading method to inject config
        :param element: plugin class to load.
        """
        log.debug("Class to load %s" % element.__name__)
        return element(self._config)

    def get_candidate(self, name):
        """ Find the plugin by name.

        :param name: The name of the plugin you are looking for.
        :return: :raise Exception:
        """
        for (_, _, plug) in self.getPluginCandidates():
            if plug.name == name:
                return plug
        raise Exception("Plugin '%s' not found." % name)

    def get_plugin_by_name(self, name):
        # set a locator to narrow it to only one.
        self._locator.setAnalyzers([SpecificPluginLocator(name)])
        log.debug("Refilter the plugins...")
        self.locatePlugins()
        log.debug("Load the one remaining...")
        plugins = self.loadPlugins()
        if len(plugins) == 0:
            raise Exception("Could not find the plugin '%s'." % name)
        if len(plugins) != 1:
            raise Exception("There are 2 plugins with the name '%s'." % name)
        if plugins[0].error is not None:
            reason = plugins[0].error
            formatted_error = "%s:\n%s" % (reason[0], ''.join(traceback.format_tb(plugins[0].error[2])))
            raise Exception('Error loading plugin %s:\nError:\n%s\n' % (name, formatted_error))

        return plugins[0].plugin_object
