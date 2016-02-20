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
