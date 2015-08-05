import os
import unittest
import tempfile
from errbot.plugin_manager import check_dependencies, CORE_PLUGINS
from errbot.utils import find_roots, find_roots_with_extra


def touch(name):
    with open(name, 'a'):
        os.utime(name, None)


class TestPluginManagement(unittest.TestCase):
    def test_check_dependencies(self):
        response, deps = check_dependencies(str(os.path.dirname(__file__)) + os.path.sep + 'assets')
        self.assertIn('impossible_requirement', response)
        self.assertEqual(['impossible_requirement'], deps)

    def test_find_plugin_roots(self):
        root = tempfile.mkdtemp()
        a = os.path.join(root, 'a')
        b = os.path.join(a, 'b')
        c = os.path.join(root, 'c')
        os.mkdir(a)
        os.mkdir(b)
        os.mkdir(c)
        touch(os.path.join(a, 'toto.plug'))
        touch(os.path.join(b, 'titi.plug'))
        touch(os.path.join(root, 'tutu.plug'))
        roots = find_roots(root)
        self.assertIn(root, roots)
        self.assertIn(a, roots)
        self.assertIn(b, roots)
        self.assertNotIn(c, roots)

    def test_builtin(self):
        toto = tempfile.mkdtemp()
        touch(os.path.join(toto, 'toto.plug'))
        touch(os.path.join(toto, 'titi.plug'))
        titi = tempfile.mkdtemp()
        touch(os.path.join(titi, 'tata.plug'))
        self.assertEquals(find_roots_with_extra(CORE_PLUGINS, None), [CORE_PLUGINS])
        self.assertEquals(find_roots_with_extra(CORE_PLUGINS, toto), [CORE_PLUGINS, toto])
        self.assertEquals(find_roots_with_extra(CORE_PLUGINS, [toto, titi]), [CORE_PLUGINS, toto, titi])
        self.assertEquals(find_roots_with_extra(CORE_PLUGINS, [toto, titi, 'nothing']), [CORE_PLUGINS, toto, titi])

    def test_ignore_dotted_directories(self):
        root = tempfile.mkdtemp()
        a = os.path.join(root, '.invisible')
        os.mkdir(a)
        touch(os.path.join(a, 'toto.plug'))
        self.assertEquals(find_roots_with_extra(CORE_PLUGINS, root), [CORE_PLUGINS])
