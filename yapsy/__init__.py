"""

Overview
========

Yapsy's main purpose is to offer a way to easily design a plugin
system in Python, and motivated by the fact that many other Python
plugin system are either too complicated for a basic use or depend on
a lot of libraries. Yapsy only depends on Python's standard library.

|yapsy| basically defines two core classes:

- a fully functional though very simple ``PluginManager`` class

- an interface ``IPlugin`` which defines the interface of plugin
  instances handled by the ``PluginManager``


Getting started
===============

The basic classes defined by |yapsy| should work "as is" and enable
you to load and activate your plugins. So that the following code
should get you a fully working plugin management system::

   from yapsy.PluginManager import PluginManager
   
   # Build the manager
   simplePluginManager = PluginManager()
   # Tell it the default place(s) where to find plugins
   simplePluginManager.setPluginPlaces(["path/to/myplugins"])
   # Load all plugins
   simplePluginManager.collectPlugins()

   # Activate all loaded plugins
   for pluginInfo in simplePluginManager.getAllPlugins():
      simplePluginManager.activatePluginByName(pluginInfo.name)


.. note:: The ``plugin_info`` object (typically an instance of
          ``IPlugin``) plays as *the entry point of each
          plugin*. That's also where |yapsy| ceases to guide you: it's
          up to you to define what your plugins can do and how you
          want to talk to them ! Talking to your plugin will then look
          very much like the following::

             # Trigger 'some action' from the loaded plugins
             for pluginInfo in simplePluginManager.getAllPlugins():
                pluginInfo.plugin_object.doSomething(...)



.. _extend:

Extensibility
=============

For applications that require the plugins and their managers to be
more sophisticated, several techniques make such enhancement easy. The
following sections detail the three most frequent needs for extensions
and what you can do about it.


More sophisticated plugin classes
---------------------------------

You can define a plugin class with a richer interface that
``IPlugin``, so long as it inherits from IPlugin, it should work the
same. The only thing you need to know is that the plugin instance is
accessible via the ``PluginInfo`` instance from its
``PluginInfo.plugin_object``.


It is also possible to define a wider variety of plugins, by defining
as much subclasses of IPlugin. But in such a case you have to inform
the manager about that before collecting plugins::

   # Build the manager
   simplePluginManager = PluginManager()
   # Tell it the default place(s) where to find plugins
   simplePluginManager.setPluginPlaces(["path/to/myplugins"])
   # Define the various categories corresponding to the different
   # kinds of plugins you have defined
   simplePluginManager.setCategoriesFilter({
      "Playback" : IPlaybackPlugin,
      "SongInfo" : ISongInfoPlugin,
      "Visualization" : IVisualisation,
      })


.. note:: Communicating with the plugins belonging to a given category
          might then be achieved with some code looking like the
          following::

             # Trigger 'some action' from the "Visualization" plugins 
             for pluginInfo in simplePluginManager.getPluginsOfCategory("Visualization"):
                pluginInfo.plugin_object.doSomething(...)

      
Enhance the manager's interface
-------------------------------

To make the plugin manager more helpful to the other components of an
application, you should consider decorating it.

Actually a "template" for such decoration is provided as
:doc:`PluginManagerDecorator`, which must be inherited in order to
implement the right decorator for your application.

Such decorators can be chained, so that you can take advantage of the ready-made decorators such as:

:doc:`ConfigurablePluginManager`

  Implements a ``PluginManager`` that uses a configuration file to
  save the plugins to be activated by default and also grants access
  to this file to the plugins.


:doc:`AutoInstallPluginManager`

  Automatically copy the plugin files to the right plugin directory. 


Modify the way plugins are loaded
---------------------------------


To tweak the plugin loading phase it is highly advised to re-implement
your own manager class.

The nice thing is, if your new manager  inherits ``PluginManager``, then it will naturally fit as the start point of any decoration chain. You just have to provide an instance of this new manager to the first decorators, like in the following::

   # build and configure a specific manager
   baseManager = MyNewManager()
   # start decorating this manager to add some more responsibilities
   myFirstDecorator = AFirstPluginManagerDecorator(baseManager)
   # add even more stuff
   mySecondDecorator = ASecondPluginManagerDecorator(myFirstDecorator)

.. note:: Some decorators have been implemented that modify the way
          plugins are loaded, this is however not the easiest way to
          do it and it makes it harder to build a chain of decoration
          that would include these decorators.  Among those are
          :doc:`VersionedPluginManager` and
          :doc:`FilteredPluginManager`

"""

# tell epydoc that the documentation is in the reStructuredText format
__docformat__ = "restructuredtext en"

