from urllib.request import urlopen
from urllib.error import HTTPError, URLError
import threading

from errbot import BotPlugin
from errbot.utils import version2array
from errbot.version import VERSION

HOME = 'http://version.errbot.io/'

installed_version = version2array(VERSION)


class VersionChecker(BotPlugin):

    connected = False
    activated = False

    def activate(self):
        if self.mode not in ('null', 'test', 'Dummy'):  # skip in all test confs.
            self.activated = True
            self.version_check()  # once at startup anyway
            self.start_poller(3600 * 24, self.version_check)  # once every 24H
            super().activate()
        else:
            self.log.info('Skip version checking under %s mode' % self.mode)

    def deactivate(self):
        self.activated = False
        super().deactivate()

    def _async_vcheck(self):
        # noinspection PyBroadException
        try:
            current_version_txt = urlopen(url=HOME + '?' + VERSION,
                                          timeout=10).read().decode("utf-8").strip()
            self.log.debug("Tested current Errbot version and it is " + current_version_txt)
            current_version = version2array(current_version_txt)
            if installed_version < current_version:
                self.log.debug('A new version %s has been found, notify the admins !' % current_version)
                self.warn_admins(
                    'Version {0} of err is available. http://pypi.python.org/pypi/errbot/{0}.'
                    ' You can disable this check '
                    'by doing {1}plugin blacklist VersionChecker'.format(current_version_txt, self._bot.prefix)
                )
        except (HTTPError, URLError):
            self.log.info('Could not establish connection to retrieve latest version.')

    def version_check(self):
        if not self.activated:
            self.log.debug('Version check disabled')
            return
        self.log.debug('Checking version in background.')
        threading.Thread(target=self._async_vcheck).start()

    def callback_connect(self):
        if not self.connected:
            self.connected = True
