import logging
from errbot import BotPlugin
from errbot.version import VERSION
import urllib2
from errbot.utils import version2array

HOME = 'http://www.gootz.net/err/version'

installed_version = version2array(VERSION)

class VersionChecker(BotPlugin):
    min_err_version = VERSION # don't copy paste that for your plugin, it is just because it is a bundled plugin !
    max_err_version = VERSION

    connected = False
    actived = False

    def activate(self):
        self.actived=True
        self.version_check() # once at startup anyway
        self.start_poller(3600 * 24 , self.version_check) # once every 24H
        super(VersionChecker, self).activate()

    def deactivate(self):
        self.actived=False
        super(VersionChecker, self).deactivate()

    def version_check(self):
        if not self.actived:
            logging.debug('Version check disabled')
            return
        logging.debug('Checking version')
        try:
            current_version_txt = urllib2.urlopen(HOME).read().strip()
            current_version = version2array(current_version_txt)
            if installed_version < current_version:
                logging.debug('A new version %s has been found, notify the admins !' % current_version)
                self.warn_admins('Version %s of err is available. http://pypi.python.org/pypi/err/%s. You can disable this check by doing !unload VersionChecker' % (current_version_txt, current_version_txt))
        except Exception as e:
            logging.exception('Could not version check')

    def callback_connect(self):
        if not self.connected:
            self.connected = True
