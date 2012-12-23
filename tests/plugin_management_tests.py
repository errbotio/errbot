import os
import unittest
from errbot.plugin_manager import check_dependencies


class TestPluginManagement(unittest.TestCase):
    def test_check_dependencies(self):
        response = check_dependencies(os.path.dirname(__file__) + os.path.sep + 'assets')
        self.assertEquals('You need those dependencies for /home/gbin/projects/err/tests/assets: impossible_requirement', response)

