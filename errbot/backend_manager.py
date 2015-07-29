import os
import logging
import sys

from yapsy.PluginManager import PluginManager
from yapsy.PluginFileLocator import PluginFileLocator, PluginFileAnalyzerWithInfoFile

from errbot.errBot import ErrBot
from .utils import find_roots_with_extra

CORE_BACKENDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backends')
log = logging.getLogger(__name__)


class SpecificBackendLocator(PluginFileAnalyzerWithInfoFile):
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


class BackendManager(PluginManager):
    """ BackendManager is a customized plugin manager to enumerate backends
        and load only one.
    """
    def __init__(self, config):
        self._config = config
        # set a locator that gets every possible backends as a first discovery pass.
        self._locator = PluginFileLocator(analyzers=[PluginFileAnalyzerWithInfoFile('AllBackendLocator', 'plug')])
        super().__init__(plugin_locator=self._locator)
        self.setCategoriesFilter({'backend': ErrBot})
        if hasattr(config, 'BOT_EXTRA_BACKEND_DIR'):
            extra = config.BOT_EXTRA_BACKEND_DIR
        else:
            extra = []
        all_backends_paths = find_roots_with_extra(CORE_BACKENDS, extra)
        log.info('Backends search paths %s', all_backends_paths)
        self.setPluginPlaces(all_backends_paths)
        for entry in all_backends_paths:
            if entry not in sys.path:
                sys.path.append(entry)  # so backends can relatively import their submodules
        self.locatePlugins()
        log.info('Found those backends available:')
        for (_, _, plug) in self.getPluginCandidates():
            log.info('\t%10s  (%s)' % (plug.name, plug.path + '.py'))

    def instanciateElement(self, element):
        """ Override the loading method to inject config """
        log.debug("Class to load %s" % element.__name__)
        return element(self._config)

    def get_candidate(self, name):
        """ Find the backend plugin by name.

        :param name: The name of the plugin you are looking for.
        :return: :raise Exception:
        """
        for (_, _, plug) in self.getPluginCandidates():
            if plug.name == name:
                return plug
        raise Exception("Backend '%s' not found." % name)

    def get_backend_by_name(self, name):
        # set a locator to narrow it to only one.
        self._locator.setAnalyzers([SpecificBackendLocator(name)])
        log.debug("Refilter the backend plugins...")
        self.locatePlugins()
        log.debug("Load the one remaining...")
        self.loadPlugins()
        log.debug("Find it back...")
        plugins = self.getAllPlugins()
        if len(plugins) == 0:
            raise Exception("Could not find the backend '%s'." % name)
        if len(plugins) != 1:
            raise Exception("There are 2 backends with the name '%s'." % name)
        return plugins[0].plugin_object
