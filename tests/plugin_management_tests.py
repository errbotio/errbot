import os
import unittest
from errbot.plugin_manager import check_dependencies, get_builtins, BUILTIN


class TestPluginManagement(unittest.TestCase):
    def test_check_dependencies(self):
        response = check_dependencies(str(os.path.dirname(__file__)) + os.path.sep + 'assets')
        self.assertIn('impossible_requirement', response)

    def test_builtin(self):
        self.assertEquals(get_builtins(None), [BUILTIN])
        self.assertEquals(get_builtins('toto'), [BUILTIN, 'toto'])
        self.assertEquals(get_builtins(['titi', 'tutu']), [BUILTIN, 'titi', 'tutu'])
