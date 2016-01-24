import logging
import os

from errbot.backends.test import FullStackTest


class TestCorePlugins(FullStackTest):
    """
    Tests the CORE_PLUGINS filter fromt the config file.
    It only allows Help and Backup, this checks if the state is consistent with that.
    """

    def setUp(self, extra_plugin_dir=None, extra_test_file=None, loglevel=logging.DEBUG, extra_config=None):
        super().setUp(extra_plugin_dir=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'room_tests'),
                      extra_test_file=extra_test_file,
                      extra_config={'CORE_PLUGINS': ('Help', 'Utils')})
        # we NEED utils otherwise the test locks at startup

    def test_help_is_still_here(self):
        self.assertCommand('!help', 'All commands')

    def test_backup_help_not_here(self):
        self.assertCommand('!help backup', 'That command is not defined.')

    def test_backup_should_not_be_there(self):
        self.assertCommand('!backup', 'Command "backup" not found.')

    def test_echo_still_here(self):
        self.assertCommand('!echo toto', 'toto')
