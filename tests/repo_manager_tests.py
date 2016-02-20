import tempfile
import unittest
import shutil
import os

from errbot import repo_manager
from errbot.storage.memory import MemoryStoragePlugin


class TestRepoManagement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.assets = os.path.join(os.path.dirname(__file__), 'assets')

    def setUp(self):
        self.plugins_dir = tempfile.mkdtemp()
        self.storage_plugin = MemoryStoragePlugin('repomgr')

    def tearDown(self):
        shutil.rmtree(self.plugins_dir)

    def test_index_population(self):
        manager = repo_manager.BotRepoManager(self.storage_plugin,
                                              self.plugins_dir,
                                              (os.path.join(self.assets, 'repos', 'simple.json'),))
        manager.index_update()

        index_entry = manager[repo_manager.REPO_INDEX]

        self.assertIn(repo_manager.LAST_UPDATE, index_entry)
        self.assertIn('name1/err-reponame1~pluginname1', index_entry)
        self.assertIn('name2/err-reponame2~pluginname2', index_entry)

    def test_index_merge(self):
        manager = repo_manager.BotRepoManager(self.storage_plugin,
                                              self.plugins_dir,
                                              (os.path.join(self.assets, 'repos', 'b.json'),
                                               os.path.join(self.assets, 'repos', 'a.json'),))
        manager.index_update()

        index_entry = manager[repo_manager.REPO_INDEX]

        # First they should be all here
        self.assertIn('name1/err-reponame1~pluginname1', index_entry)
        self.assertIn('name2/err-reponame2~pluginname2', index_entry)
        self.assertIn('name3/err-reponame3~pluginname3', index_entry)

        # then it must be the correct one of the overriden one

        self.assertEqual(index_entry['name2/err-reponame2~pluginname2']['name'], 'NewPluginName2')

    def test_reverse_merge(self):
        manager = repo_manager.BotRepoManager(self.storage_plugin,
                                              self.plugins_dir,
                                              (os.path.join(self.assets, 'repos', 'a.json'),
                                               os.path.join(self.assets, 'repos', 'b.json'),))
        manager.index_update()

        index_entry = manager[repo_manager.REPO_INDEX]
        self.assertFalse(index_entry['name2/err-reponame2~pluginname2']['name'] == 'NewPluginName2')

    def test_no_update_if_one_fails(self):
        manager = repo_manager.BotRepoManager(self.storage_plugin,
                                              self.plugins_dir,
                                              (os.path.join(self.assets, 'repos', 'a.json'),
                                               os.path.join(self.assets, 'repos', 'doh.json'),))
        manager.index_update()
        self.assertNotIn(repo_manager.REPO_INDEX, manager)




