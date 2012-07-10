#!/usr/bin/python

"""
Role
====

Defines a basic interface for plugin managers which filter the
available list of plugins before loading.

One use fo this would be to prevent untrusted plugins from entering the system

API
===
"""
 

from yapsy.IPlugin import IPlugin
from yapsy.PluginManagerDecorator import  PluginManagerDecorator


class FilteredPluginManager(PluginManagerDecorator):
	"""
	Base class for decorators which filter the plugins list
	before they are loaded.
	"""

	def __init__(self, 
				 decorated_manager=None,
				 categories_filter={"Default":IPlugin}, 
				 directories_list=None, 
				 plugin_info_ext="yapsy-plugin"):
		"""
		"""
		# Create the base decorator class
		PluginManagerDecorator.__init__(self,decorated_manager,
										categories_filter,
										directories_list,
										plugin_info_ext)
		# prepare the mapping of the latest version of each plugin
		self.rejectedPlugins =  [ ] 



	def filterPlugins(self):
		"""
		This method goes through the currently available candidates, and
		and either leaves them, or moves them into the list of rejected Plugins.
		
		This method can be overridden if the isPluginOk() sentinel is not
		powerful enough.
		"""
		self.rejectedPlugins        = [ ]
		for candidate_infofile, candidate_filepath, plugin_info in self._component.getPluginCandidates():
			if not self.isPluginOk( plugin_info):
				self.rejectPluginCandidate((candidate_infofile, candidate_filepath, plugin_info) )

	def rejectPluginCandidate(self,pluginTuple):
		"""
		This is method can be called to mark move a plugin from Candidates list
		to the rejected List.
		"""
		if pluginTuple in self.getPluginCandidates():
			self._component.removePluginCandidate(pluginTuple)
		if not pluginTuple in self.rejectedPlugins:
			self.rejectedPlugins.append(pluginTuple)

	def unrejectPluginCandidate(self,pluginTuple):
		"""
		This is method can be called to mark move a plugin from the rejected list
		to into the Candidates List.
		"""
		if not pluginTuple in self.getPluginCandidates():
			self._component.appendPluginCandidate(pluginTuple)
		if pluginTuple in self.rejectedPlugins:
			self.rejectedPlugins.remove(pluginTuple)

	def removePluginCandidate(self,pluginTuple):
		if pluginTuple in self.getPluginCandidates():
			self._component.removePluginCandidate(pluginTuple)
		if  pluginTuple in self.rejectedPlugins:
			self.rejectedPlugins.remove(pluginTuple)


	def appendPluginCandidate(self,pluginTuple):
		if self.isPluginOk(pluginTuple[2]):
			if pluginTuple not in self.getPluginCandidates():
				self._component.appendPluginCandidate(pluginTuple)
		else:
			if not pluginTuple in self.rejectedPlugins:
				self.rejectedPlugins.append(pluginTuple)

	def isPluginOk(self,info):
		"""
		Sentinel function to detect if a plugin should be filtered.

		Subclasses should override this function and return false for
		any plugin which they do not want to be loadable.
		"""
		return True

	def locatePlugins(self):
		"""
		locate and filter plugins.
		"""
		#Reset Catalogue
		self.setCategoriesFilter(self._component.categories_interfaces)
		#Reread and filter.
		self._component.locatePlugins()
		self.filterPlugins()
		return len(self._component.getPluginCandidates()) 

	def getRejectedPlugins(self):
		return self.rejectedPlugins[:]
