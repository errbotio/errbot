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
        self.assertIn('pluginname1', index_entry['name1/err-reponame1'])
        self.assertIn('pluginname2', index_entry['name2/err-reponame2'])

    def test_index_merge(self):
        manager = repo_manager.BotRepoManager(self.storage_plugin,
                                              self.plugins_dir,
                                              (os.path.join(self.assets, 'repos', 'b.json'),
                                               os.path.join(self.assets, 'repos', 'a.json'),))
        manager.index_update()

        index_entry = manager[repo_manager.REPO_INDEX]

        # First they should be all here
        self.assertIn('pluginname1', index_entry['name1/err-reponame1'])
        self.assertIn('pluginname2', index_entry['name2/err-reponame2'])
        self.assertIn('pluginname3', index_entry['name3/err-reponame3'])

        # then it must be the correct one of the overriden one

        self.assertEqual(index_entry['name2/err-reponame2']['pluginname2']['name'], 'NewPluginName2')

    def test_reverse_merge(self):
        manager = repo_manager.BotRepoManager(self.storage_plugin,
                                              self.plugins_dir,
                                              (os.path.join(self.assets, 'repos', 'a.json'),
                                               os.path.join(self.assets, 'repos', 'b.json'),))
        manager.index_update()

        index_entry = manager[repo_manager.REPO_INDEX]
        self.assertFalse(index_entry['name2/err-reponame2']['pluginname2']['name'] == 'NewPluginName2')

    def test_no_update_if_one_fails(self):
        manager = repo_manager.BotRepoManager(self.storage_plugin,
                                              self.plugins_dir,
                                              (os.path.join(self.assets, 'repos', 'a.json'),
                                               os.path.join(self.assets, 'repos', 'doh.json'),))
        manager.index_update()
        self.assertNotIn(repo_manager.REPO_INDEX, manager)

    def test_tokenization(self):
        e = {
                "python": "2+",
                "repo": "https://github.com/name/err-reponame1",
                "path": "/plugin1.plug",
                "avatar_url": "https://avatars.githubusercontent.com/u/588833?v=3",
                "name": "PluginName1",
                "documentation": "docs1"
            }
        words = {'https',
                 'com',
                 'name',
                 'err',
                 'docs1',
                 'reponame1',
                 'plug',
                 '2',
                 'plugin1',
                 'avatars',
                 'github',
                 'githubusercontent',
                 'u',
                 'v',
                 '3',
                 '588833',
                 'pluginname1'
                 }

        self.assertEquals(repo_manager.tokenizeJsonEntry(e), words)

    def test_search(self):
        manager = repo_manager.BotRepoManager(self.storage_plugin,
                                              self.plugins_dir,
                                              (os.path.join(self.assets, 'repos', 'simple.json'),))

        a = [p for p in manager.search_repos('docs2')]
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0].name, 'pluginname2')

        a = [p for p in manager.search_repos('zorg')]
        self.assertEqual(len(a), 0)

        a = [p for p in manager.search_repos('plug')]
        self.assertEqual(len(a), 2)

    def test_git_url_name_guessing(self):
        self.assertEqual(repo_manager.human_name_for_git_url('https://github.com/errbotio/err-imagebot.git'),
                         'errbotio/err-imagebot')
