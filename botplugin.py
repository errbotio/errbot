import logging
import os
import shelve
from config import BOT_DATA_DIR
from utils import PLUGINS_SUBDIR

# this class handle the basic needs of bot plugins like loading, unloading and creating a storage
class BotPlugin(object):

    def __init__(self):
        self.is_activated = False

    def activate(self):
        classname = self.__class__.__name__
        logging.debug('Init shelf for %s' % classname)
        filename = BOT_DATA_DIR + os.sep + PLUGINS_SUBDIR + os.sep + classname + '.db'
        logging.debug('Loading %s' % filename)
        if hasattr(self.__class__, '_shelf'):
	    self.__class__._shelf.close()

	self.__class__._shelf = shelve.DbfilenameShelf(filename)
        BotPlugin.botbase_class.__bases__ += ( self.__class__,) # I use a class parameter to avoid a circular dependency to errBot
        self.is_activated = True


    def deactivate(self):
        BotPlugin.botbase_class.__bases__ = filter(lambda e: e != self.__class__, BotPlugin.botbase_class.__bases__)
        logging.debug('Closing shelf %s' % self.shelf)
        self.shelf.close()
        self.is_activated = False

    @property
    def shelf(self):
        return self.__class__._shelf

