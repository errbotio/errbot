
#!/usr/bin/python
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

"""
Role
====

The ``PluginManager`` loads plugins that enforce the `Plugin
Description Policy`_, and offers the most simple methods to activate
and deactivate the plugins once they are loaded.

.. note:: It may also classify the plugins in various categories, but
          this behaviour is optional and if not specified elseway all
          plugins are stored in the same default category.

.. note:: It is often more useful to have the plugin manager behave
          like singleton, this functionality is provided by
          ``PluginManagerSingleton``


Plugin Description Policy
=========================

When creating a ``PluginManager`` instance, one should provide it with
a list of directories where plugins may be found. In each directory,
a plugin should contain the following elements:

For a  *Standard* plugin:

  ``myplugin.yapsy-plugin`` 
 
      A *plugin info file* identical to the one previously described.
 
  ``myplugin``
 
      A directory ontaining an actual Python plugin (ie with a
      ``__init__.py`` file that makes it importable). The upper
      namespace of the plugin should present a class inheriting the
      ``IPlugin`` interface (the same remarks apply here as in the
      previous case).


For a *Single file* plugin:

  ``myplugin.yapsy-plugin`` 
       
    A *plugin info file* which is identified thanks to its extension,
    see the `Plugin Info File Format`_ to see what should be in this
    file.
    
  
    The extension is customisable at the ``PluginManager``'s
    instanciation, since one may usually prefer the extension to bear
    the application name.
  
  ``myplugin.py``
  
     The source of the plugin. This file should at least define a class
     inheriting the ``IPlugin`` interface. This class will be
     instanciated at plugin loading and it will be notified the
     activation/deactivation events.


Plugin Info File Format
-----------------------

The plugin info file gathers, as its name suggests, some basic
information about the plugin.

- it gives crucial information needed to be able to load the plugin

- it provides some documentation like information like the plugin
  author's name and a short description fo the plugin functionality.

Here is an example of what such a file should contain::

	  [Core]
	  Name = My plugin Name
	  Module = the_name_of_the_pluginto_load_with_no_py_ending
         
	  [Documentation]
	  Description = What my plugin broadly does
	  Author = My very own name
	  Version = 0.1
	  Website = My very own website
	  Version = the_version_number_of_the_plugin
	  
	 
.. note:: From such plugin descriptions, the ``PluginManager`` will
          built its own representations of the plugins as instances of
          the :doc:`PluginInfo` class.


Extensibility
=============

Several mechanisms have been put up to help extending the basic
functionalities of the proivided classes.

A few *hints* to help you extend those classes:

If the new functionalities do not overlap the ones already
implemented, then they should be implemented as a Decorator class of the
base plugin. This should be done by inheriting the
``PluginManagerDecorator``.

If this previous way is not possible, then the functionalities should
be added as a subclass of ``PluginManager``.

.. note:: The first method is highly prefered since it makes it
          possible to have a more flexible design where one can pick
          several functionalities and litterally *add* them to get an
          object corresponding to one's precise needs.

API
===

"""

import sys
import os
import logging
import ConfigParser

from yapsy.IPlugin import IPlugin
from yapsy.PluginInfo import PluginInfo


PLUGIN_NAME_FORBIDEN_STRING=";;"
"""
.. warning:: This string (';;' by default) is forbidden in plugin
             names, and will be usable to describe lists of plugins
             for instance (see :doc:`ConfigurablePluginManager`)
"""


class PluginManager(object):
	"""
	Manage several plugins by ordering them in categories.
	
	The mechanism for searching and loading the plugins is already
	implemented in this class so that it can be used directly (hence
	it can be considered as a bit more than a mere interface)
	
	The file describing a plugin must be written in the syntax
	compatible with Python's ConfigParser module as in the
	`Plugin Info File Format`_  
	"""
	

	def __init__(self, 
				 categories_filter={"Default":IPlugin}, 
				 directories_list=None, 
				 plugin_info_ext="yapsy-plugin"):
		"""
		Initialize the mapping of the categories and set the list of
		directories where plugins may be. This can also be set by
		direct call the methods: 
		
		- ``setCategoriesFilter`` for ``categories_filter``
		- ``setPluginPlaces`` for ``directories_list``
		- ``setPluginInfoExtension`` for ``plugin_info_ext``

		You may look at these function's documentation for the meaning
		of each corresponding arguments.
		"""
		self.setPluginInfoClass(PluginInfo)
		self.setCategoriesFilter(categories_filter)		
		self.setPluginPlaces(directories_list)
		self.setPluginInfoExtension(plugin_info_ext)

	def setCategoriesFilter(self, categories_filter):
		"""
		Set the categories of plugins to be looked for as well as the
		way to recognise them.
		
		The ``categories_filter`` first defines the various categories
		in which the plugins will be stored via its keys and it also
		defines the interface tha has to be inherited by the actual
		plugin class belonging to each category.
		"""
		self.categories_interfaces = categories_filter.copy()
		# prepare the mapping from categories to plugin lists
		self.category_mapping = {}
		# also maps the plugin info files (useful to avoid loading
		# twice the same plugin...)
		self._category_file_mapping = {}
		for categ in categories_filter:
			self.category_mapping[categ] = []
			self._category_file_mapping[categ] = []
			

	def setPluginInfoClass(self,picls):
		"""
		Set the class that holds PluginInfo. The class should inherit
		from ``PluginInfo``.
		"""
		self._plugin_info_cls = picls

	def getPluginInfoClass(self):
		"""
		Get the class that holds PluginInfo. The class should inherit
		from ``PluginInfo``.
		"""
		return self._plugin_info_cls

	def setPluginPlaces(self, directories_list):
		"""
		Set the list of directories where to look for plugin places.
		"""
		if directories_list is None:
			directories_list = [os.path.dirname(__file__)]
		self.plugins_places = directories_list

	def setPluginInfoExtension(self,plugin_info_ext):
		"""
		Set the extension that identifies a plugin info file.

		The ``plugin_info_ext`` is the extension that will have the
		informative files describing the plugins and that are used to
		actually detect the presence of a plugin (see
		``collectPlugins``).
		"""
		self.plugin_info_ext = plugin_info_ext

	def getCategories(self):
		"""
		Return the list of all categories.
		"""
		return self.category_mapping.keys()
	
	def removePluginFromCategory(self,plugin,category_name):
		"""
		Remove a plugin from the category where it's assumed to belong.
		"""
		self.category_mapping[category_name].remove(plugin)
		
		
	def appendPluginToCategory(self,plugin,category_name):
		"""
		Append a new plugin to the given category.
		"""
		self.category_mapping[category_name].append(plugin)

	
	def getPluginsOfCategory(self,category_name):
		"""
		Return the list of all plugins belonging to a category.
		"""
		return self.category_mapping[category_name][:]
	
	def getAllPlugins(self):
		"""
		Return the list of all plugins (belonging to all categories).
		"""
		allPlugins = []
		for pluginsOfOneCategory in self.category_mapping.itervalues():
				allPlugins.extend(pluginsOfOneCategory)
		return allPlugins
	
	def _getPluginNameAndModuleFromStream(self, infoFileObject, candidate_infofile="<buffered info>"):
		"""
		Extract the name and module of a plugin from the
		content of the info file that describes it and which
		is stored in infoFileObject.

		.. note:: Prefer using ``_gatherCorePluginInfo``
		instead, whenever possible...
                
                .. warning:: ``infoFileObject`` must be a file-like
                object: either an opened file for instance or a string
                buffer wrapped in a StringIO instance as another
                example.

                .. note:: ``candidate_infofile`` must be provided
                whenever possible to get better error messages.
                
		Return a 3-uple with the name of the plugin, its
		module and the config_parser used to gather the core
		data *in a tuple*, if the required info could be
		localised, else return ``(None,None,None)``.
		
		.. note:: This is supposed to be used internally by subclasses
		    and decorators.
                """
		# parse the information buffer to get info about the plugin
		config_parser = ConfigParser.SafeConfigParser()
		try:
			config_parser.readfp(infoFileObject)
		except Exception,e:
			logging.debug("Could not parse the plugin file '%s' (exception raised was '%s')" % (candidate_infofile,e))
			return (None, None, None)
		# check if the basic info is available
		if not config_parser.has_section("Core"):
			logging.debug("Plugin info file has no 'Core' section (in '%s')" % candidate_infofile)					
			return (None, None, None)
		if not config_parser.has_option("Core","Name") or not config_parser.has_option("Core","Module"):
			logging.debug("Plugin info file has no 'Name' or 'Module' section (in '%s')" % candidate_infofile)
			return (None, None, None)
		# check that the given name is valid
		name = config_parser.get("Core", "Name")
		name = name.strip()
		if PLUGIN_NAME_FORBIDEN_STRING in name:
			logging.debug("Plugin name contains forbiden character: %s (in '%s')" % (PLUGIN_NAME_FORBIDEN_STRING,
																				   candidate_infofile))
			return (None, None, None)
		return (name,config_parser.get("Core", "Module"), config_parser)
        
	def _gatherCorePluginInfo(self, directory, filename):
		"""
		Gather the core information (name, and module to be loaded)
		about a plugin described by it's info file (found at
		'directory/filename').

		Return an instance of ``self.plugin_info_cls`` and the
		config_parser used to gather the core data *in a tuple*, if the
		required info could be localised, else return ``(None,None)``.
		
		.. note:: This is supposed to be used internally by subclasses
		    and decorators.
		
		"""
		# now we can consider the file as a serious candidate
		candidate_infofile = os.path.join(directory,filename)
		# parse the information file to get info about the plugin
		name,moduleName,config_parser = self._getPluginNameAndModuleFromStream(open(candidate_infofile),
                                                                                       candidate_infofile)
		if (name,moduleName,config_parser)==(None,None,None):
                        return (None,None)
		# start collecting essential info
		plugin_info = self._plugin_info_cls(name,os.path.join(directory,moduleName))
		return (plugin_info,config_parser)

	def gatherBasicPluginInfo(self, directory,filename):
		"""
		Gather some basic documentation about the plugin described by
		it's info file (found at 'directory/filename').

		Return an instance of ``self.plugin_info_cls`` gathering the
		required informations.

		See also:
		
		  ``self._gatherCorePluginInfo``
		"""
		plugin_info,config_parser = self._gatherCorePluginInfo(directory, filename)
		if plugin_info is None:
			return None
		# collect additional (but usually quite usefull) information
		if config_parser.has_section("Documentation"):
			if config_parser.has_option("Documentation","Author"):
				plugin_info.author	= config_parser.get("Documentation", "Author")
			if config_parser.has_option("Documentation","Version"):
				plugin_info.setVersion(config_parser.get("Documentation", "Version"))
			if config_parser.has_option("Documentation","Website"): 
				plugin_info.website	= config_parser.get("Documentation", "Website")
			if config_parser.has_option("Documentation","Copyright"):
				plugin_info.copyright	= config_parser.get("Documentation", "Copyright")
			if config_parser.has_option("Documentation","Description"):
				plugin_info.description = config_parser.get("Documentation", "Description")
		return plugin_info




	
	def getPluginCandidates(self):
		"""
		Return the list of possible plugins.

		Each possible plugin (ie a candidate) is described by a 3-uple:
		(info file path, python file path, plugin info instance)

		.. warning: locatePlugins must be called before !
		"""
		if not hasattr(self, '_candidates'):
			raise ValueError("locatePlugins must be called before getPluginCandidates")
		return self._candidates[:]

	def removePluginCandidate(self,candidateTuple):
		"""
		Remove a given candidate from the list of plugins that should be loaded.

		The candidate must be represented by the same tuple described
		in ``getPluginCandidates``.
		
		.. warning: locatePlugins must be called before !
		"""
		if not hasattr(self, '_candidates'):
			raise ValueError("locatePlugins must be called before removePluginCandidate")
		self._candidates.remove(candidateTuple)

	def appendPluginCandidate(self,candidateTuple):
		"""
		Append a new candidate to the list of plugins that should be loaded.
		
		The candidate must be represented by the same tuple described
		in ``getPluginCandidates``.
		
		.. warning: locatePlugins must be called before !
		"""
		if not hasattr(self, '_candidates'):
			raise ValueError("locatePlugins must be called before removePluginCandidate")
		self._candidates.append(candidateTuple)
		
		
	def locatePlugins(self):
		"""
		Walk through the plugins' places and look for plugins.

		Return the number of plugins found.
		"""
# 		print "%s.locatePlugins" % self.__class__
		self._candidates = []
		for directory in map(os.path.abspath,self.plugins_places):
			# first of all, is it a directory :)
			if not os.path.isdir(directory):
				logging.debug("%s skips %s (not a directory)" % (self.__class__.__name__,directory))
				continue
			# iteratively walks through the directory
			logging.debug("%s walks into directory: %s" % (self.__class__.__name__,directory))
			for item in os.walk(directory):
				dirpath = item[0]
				for filename in item[2]:
					# eliminate the obvious non plugin files
					if not filename.endswith(".%s" % self.plugin_info_ext):
						continue
					candidate_infofile = os.path.join(dirpath,filename)
					logging.debug("""%s found a candidate: 
	%s""" % (self.__class__.__name__, candidate_infofile))
#					print candidate_infofile
					plugin_info = self.gatherBasicPluginInfo(dirpath,filename)
					if plugin_info is None:
						logging.info("Plugin candidate rejected: '%s'" % candidate_infofile)
						continue
					# now determine the path of the file to execute,
					# depending on wether the path indicated is a
					# directory or a file
#					print plugin_info.path
					if os.path.isdir(plugin_info.path):
						candidate_filepath = os.path.join(plugin_info.path,"__init__")
					elif os.path.isfile(plugin_info.path+".py"):
						candidate_filepath = plugin_info.path
					else:
						logging.info("Plugin candidate rejected: '%s'" % candidate_infofile) 
						continue
#					print candidate_filepath
					self._candidates.append((candidate_infofile, candidate_filepath, plugin_info))
		return len(self._candidates)

	def loadPlugins(self, callback=None):
		"""
		Load the candidate plugins that have been identified through a
		previous call to locatePlugins.  For each plugin candidate
		look for its category, load it and store it in the appropriate
		slot of the ``category_mapping``.

		If a callback function is specified, call it before every load
		attempt.  The ``plugin_info`` instance is passed as an argument to
		the callback.
		"""
# 		print "%s.loadPlugins" % self.__class__		
		if not hasattr(self, '_candidates'):
			raise ValueError("locatePlugins must be called before loadPlugins")

		for candidate_infofile, candidate_filepath, plugin_info in self._candidates:
			# if a callback exists, call it before attempting to load
			# the plugin so that a message can be displayed to the
			# user
			if callback is not None:
				callback(plugin_info)
			# now execute the file and get its content into a
			# specific dictionnary
			candidate_globals = {"__file__":candidate_filepath+".py"}
			if "__init__" in  os.path.basename(candidate_filepath):
				sys.path.append(plugin_info.path)				
			try:
				candidateMainFile = open(candidate_filepath+".py","r")	
				exec(candidateMainFile,candidate_globals)
			except Exception,e:
				logging.debug("Unable to execute the code in plugin: %s" % candidate_filepath)
				logging.debug("\t The following problem occured: %s %s " % (os.linesep, e))
				if "__init__" in  os.path.basename(candidate_filepath):
					sys.path.remove(plugin_info.path)
				continue
			
			if "__init__" in  os.path.basename(candidate_filepath):
				sys.path.remove(plugin_info.path)
			# now try to find and initialise the first subclass of the correct plugin interface
			for element in candidate_globals.itervalues():
				current_category = None
				for category_name in self.categories_interfaces:
					try:
						is_correct_subclass = issubclass(element, self.categories_interfaces[category_name])
					except:
						continue
					if is_correct_subclass:
						if element is not self.categories_interfaces[category_name]:
							current_category = category_name
							break
				if current_category is not None:
					if not (candidate_infofile in self._category_file_mapping[current_category]): 
						# we found a new plugin: initialise it and search for the next one
						plugin_info.plugin_object = element()
						plugin_info.category = current_category
						self.category_mapping[current_category].append(plugin_info)
						self._category_file_mapping[current_category].append(candidate_infofile)
						current_category = None
					break

		# Remove candidates list since we don't need them any more and
		# don't need to take up the space
		delattr(self, '_candidates')

	def collectPlugins(self):
		"""
		Walk through the plugins' places and look for plugins.  Then
		for each plugin candidate look for its category, load it and
		stores it in the appropriate slot of the category_mapping.
		"""
# 		print "%s.collectPlugins" % self.__class__		
		self.locatePlugins()
		self.loadPlugins()


	def getPluginByName(self,name,category="Default"):
		"""
		Get the plugin correspoding to a given category and name
		"""
		if category in self.category_mapping:
			for item in self.category_mapping[category]:
				if item.name == name:
					return item
		return None

	def activatePluginByName(self,name,category="Default"):
		"""
		Activate a plugin corresponding to a given category + name.
		"""
		pta_item = self.getPluginByName(name,category)
		if pta_item is not None:
			plugin_to_activate = pta_item.plugin_object
			if plugin_to_activate is not None:
				logging.debug("Activating plugin: %s.%s"% (category,name))
				plugin_to_activate.activate()
				return plugin_to_activate			
		return None


	def deactivatePluginByName(self,name,category="Default"):
		"""
		Desactivate a plugin corresponding to a given category + name.
		"""
		if category in self.category_mapping:
			plugin_to_deactivate = None
			for item in self.category_mapping[category]:
				if item.name == name:
					plugin_to_deactivate = item.plugin_object
					break
			if plugin_to_deactivate is not None:
				logging.debug("Deactivating plugin: %s.%s"% (category,name))
				plugin_to_deactivate.deactivate()
				return plugin_to_deactivate			
		return None


class PluginManagerSingleton(object):
	"""
	Singleton version of the most basic plugin manager.

	Being a singleton, this class should not be initialised explicitly
	and the ``get`` classmethod must be called instead.

	To call one of this class's methods you have to use the ``get``
	method in the following way:
	``PluginManagerSingleton.get().themethodname(theargs)``

	To set up the various coonfigurables variables of the
	PluginManager's behaviour please call explicitly the following
	methods:

	  - ``setCategoriesFilter`` for ``categories_filter``
	  - ``setPluginPlaces`` for ``directories_list``
	  - ``setPluginInfoExtension`` for ``plugin_info_ext``
	"""
	
	__instance = None
	
	__decoration_chain = None

	def __init__(self):
		"""
		Initialisation: this class should not be initialised
		explicitly and the ``get`` classmethod must be called instead.

		To set up the various configurables variables of the
		PluginManager's behaviour please call explicitly the following
		methods:

		  - ``setCategoriesFilter`` for ``categories_filter``
		  - ``setPluginPlaces`` for ``directories_list``
		  - ``setPluginInfoExtension`` for ``plugin_info_ext``
		"""
		if self.__instance is not None:
			raise Exception("Singleton can't be created twice !")
				
	def setBehaviour(self,list_of_pmd):
		"""
		Set the functionalities handled by the plugin manager by
		giving a list of ``PluginManager`` decorators.
		
		This function shouldn't be called several time in a same
		process, but if it is only the first call will have an effect.

		It also has an effect only if called before the initialisation
		of the singleton.

		In cases where the function is indeed going to change anything
		the ``True`` value is return, in all other cases, the ``False``
		value is returned.
		"""
		if self.__decoration_chain is None and self.__instance is None:
			logging.debug("Setting up a specific behaviour for the PluginManagerSingleton")
			self.__decoration_chain = list_of_pmd
			return True
		else:
			logging.debug("Useless call to setBehaviour: the singleton is already instanciated of already has a behaviour.")
			return False
	setBehaviour = classmethod(setBehaviour)


	def get(self):
		"""
		Actually create an instance
		"""
		if self.__instance is None:
			if self.__decoration_chain is not None:
				# Get the object to be decorated
#				print self.__decoration_chain
				pm = self.__decoration_chain[0]()
				for cls_item in self.__decoration_chain[1:]:
#					print cls_item
					pm = cls_item(decorated_manager=pm)
				# Decorate the whole object
				self.__instance = pm
			else:
				# initialise the 'inner' PluginManagerDecorator
				self.__instance = PluginManager()			
			logging.debug("PluginManagerSingleton initialised")
		return self.__instance
	get = classmethod(get)


# For backward compatility import the most basic decorator (it changed
# place as of v1.8)
from yapsy.PluginManagerDecorator import PluginManagerDecorator

