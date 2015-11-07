from urllib.request import urlopen
from urllib.error import HTTPError, URLError

from errbot import BotPlugin
from errbot.version import VERSION
from errbot.utils import version2array

HOME = 'http://gbin.github.io/err/version'

installed_version = version2array(VERSION)


class VersionChecker(BotPlugin):
    min_err_version = VERSION  # don't copy paste that for your plugin, it is just because it is a bundled plugin !
    max_err_version = VERSION

    connected = False
    actived = False

    def activate(self):
        self.actived = True
        self.version_check()  # once at startup anyway
        self.start_poller(3600 * 24, self.version_check)  # once every 24H
        super(VersionChecker, self).activate()

    def deactivate(self):
        self.actived = False
        super(VersionChecker, self).deactivate()

    def version_check(self):
        if not self.actived:
            self.log.debug('Version check disabled')
            return
        self.log.debug('Checking version')
        # noinspection PyBroadException
        try:
            current_version_txt = urlopen(url=HOME, timeout=10).read().decode("utf-8").strip()
            current_version = version2array(current_version_txt)
            if installed_version < current_version:
                self.log.debug('A new version %s has been found, notify the admins !' % current_version)
                self.warn_admins(
                    'Version {0} of err is available. http://pypi.python.org/pypi/err/{0}. You can disable this check '
                    'by doing !plugin blacklist VersionChecker'.format(current_version_txt)
                )
        except (HTTPError, URLError):
            self.log.info('Could not establish connection to retrieve latest version.')

    def callback_connect(self):
        if not self.connected:
            self.connected = True
