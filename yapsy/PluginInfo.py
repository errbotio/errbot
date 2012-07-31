#!/usr/bin/python
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

"""
Role
====

Encapsulate a plugin instance as well as some metadata.

API
===
"""

class PluginInfo(object):
	"""
	Representation of the most basic set of information related to a
	given plugin such as its name, author, description...
	"""
	
	def __init__(self, plugin_name, plugin_path):
		"""
		Set the name and path of the plugin as well as the default
		values for other usefull variables.
		
		.. warning:: The ``path`` attribute is the full path to the
		    plugin if it is organised as a directory or the full path
		    to a file without the ``.py`` extension if the plugin is
		    defined by a simple file. In the later case, the actual
		    plugin is reached via ``plugin_info.path+'.py'``.
			
		"""
		self.name = plugin_name
		self.path = plugin_path
		self.author		= "Unknown"
		self.version	= "?.?"
		self.website	= "None"
		self.copyright	= "Unknown"
		self.description = ""
		self.plugin_object = None
		self.category     = None

	def _getIsActivated(self):
		"""
		Return the activated state of the plugin object.
		Makes it possible to define a property.
		"""
		return self.plugin_object.is_activated
	
	is_activated = property(fget=_getIsActivated)

	def setVersion(self, vstring):
		"""
		Set the version of the plugin.

		Used by subclasses to provide different handling of the
		version number.
		"""
		self.version = vstring

