import os
import unittest
from errbot.plugin_manager import check_dependencies


class TestPluginManagement(unittest.TestCase):
    def test_check_dependencies(self):
        response = check_dependencies(os.path.dirname(__file__) + os.path.sep + 'assets')
        try:
            self.assertIn('impossible_requirement', response)
        except AttributeError:
            # assertIn wasn't added until Python 3.1
            pass
