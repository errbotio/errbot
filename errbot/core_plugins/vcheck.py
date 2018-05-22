from urllib.error import HTTPError, URLError
import threading
import sys

import requests

from errbot import BotPlugin
from errbot.utils import version2tuple
from errbot.version import VERSION

HOME = 'http://version.errbot.io/'

installed_version = version2tuple(VERSION)

PY_VERSION = '.'.join(str(e) for e in sys.version_info[:3])


class VersionChecker(BotPlugin):

    connected = False
    activated = False

    def activate(self):
        if self.mode not in ('null', 'test', 'Dummy', 'text'):  # skip in all test confs.
            self.activated = True
            self.version_check()  # once at startup anyway
            self.start_poller(3600 * 24, self.version_check)  # once every 24H
            super().activate()
        else:
            self.log.info('Skip version checking under %s mode.', self.mode)

    def deactivate(self):
        self.activated = False
        super().deactivate()

    def _async_vcheck(self):
        # noinspection PyBroadException
        try:
            current_version_txt = requests.get(HOME, params={'errbot': VERSION, 'python': PY_VERSION}).text.strip()
            self.log.debug("Tested current Errbot version and it is " + current_version_txt)
            current_version = version2tuple(current_version_txt)
            if installed_version < current_version:
                self.log.debug('A new version %s has been found, notify the admins!', current_version)
                self.warn_admins(f'Version {current_version_txt} of Errbot is available. '
                                 f'http://pypi.python.org/pypi/errbot/{current_version_txt}. '
                                 f'To disable this check do: {self._bot.prefix}plugin blacklist VersionChecker')
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
