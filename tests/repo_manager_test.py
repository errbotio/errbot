import tempfile
import shutil
import os

import pytest

from errbot import repo_manager
from errbot.storage.memory import MemoryStoragePlugin

assets = os.path.join(os.path.dirname(__file__), 'assets')


@pytest.fixture
def plugdir_and_storage(request):
    plugins_dir = tempfile.mkdtemp()
    storage_plugin = MemoryStoragePlugin('repomgr')

    def on_finish():
        shutil.rmtree(plugins_dir)
    request.addfinalizer(on_finish)
    return plugins_dir, storage_plugin


def test_index_population(plugdir_and_storage):
    plugdir, storage = plugdir_and_storage
    manager = repo_manager.BotRepoManager(storage,
                                          plugdir,
                                          (os.path.join(assets, 'repos', 'simple.json'),))
    manager.index_update()

    index_entry = manager[repo_manager.REPO_INDEX]

    assert repo_manager.LAST_UPDATE in index_entry
    assert 'pluginname1' in index_entry['name1/err-reponame1']
    assert 'pluginname2' in index_entry['name2/err-reponame2']


def test_index_merge(plugdir_and_storage):
    plugdir, storage = plugdir_and_storage
    manager = repo_manager.BotRepoManager(storage,
                                          plugdir,
                                          (os.path.join(assets, 'repos', 'b.json'),
                                           os.path.join(assets, 'repos', 'a.json'),))
    manager.index_update()

    index_entry = manager[repo_manager.REPO_INDEX]

    # First they should be all here
    assert 'pluginname1' in index_entry['name1/err-reponame1']
    assert 'pluginname2' in index_entry['name2/err-reponame2']
    assert 'pluginname3' in index_entry['name3/err-reponame3']

    # then it must be the correct one of the overriden one

    assert index_entry['name2/err-reponame2']['pluginname2']['name'] == 'NewPluginName2'


def test_reverse_merge(plugdir_and_storage):
    plugdir, storage = plugdir_and_storage
    manager = repo_manager.BotRepoManager(storage,
                                          plugdir,
                                          (os.path.join(assets, 'repos', 'a.json'),
                                           os.path.join(assets, 'repos', 'b.json'),))
    manager.index_update()

    index_entry = manager[repo_manager.REPO_INDEX]
    assert not index_entry['name2/err-reponame2']['pluginname2']['name'] == 'NewPluginName2'


def test_no_update_if_one_fails(plugdir_and_storage):
    plugdir, storage = plugdir_and_storage
    manager = repo_manager.BotRepoManager(storage,
                                          plugdir,
                                          (os.path.join(assets, 'repos', 'a.json'),
                                           os.path.join(assets, 'repos', 'doh.json'),))
    manager.index_update()
    assert repo_manager.REPO_INDEX not in manager


def test_tokenization():
    e = {
        "python": "2+",
        "repo": "https://github.com/name/err-reponame1",
        "path": "/plugin1.plug",
        "avatar_url": "https://avatars.githubusercontent.com/u/588833?v=3",
        "name": "PluginName1",
        "documentation": "docs1"
    }
    words = {
        'https',
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
    assert repo_manager.tokenizeJsonEntry(e) == words


def test_search(plugdir_and_storage):
    plugdir, storage = plugdir_and_storage
    manager = repo_manager.BotRepoManager(storage,
                                          plugdir,
                                          (os.path.join(assets, 'repos', 'simple.json'),))

    a = [p for p in manager.search_repos('docs2')]
    assert len(a) == 1
    assert a[0].name == 'pluginname2'

    a = [p for p in manager.search_repos('zorg')]
    assert len(a) == 0

    a = [p for p in manager.search_repos('plug')]
    assert len(a) == 2


def test_git_url_name_guessing():
    assert repo_manager.human_name_for_git_url('https://github.com/errbotio/err-imagebot.git') \
        == 'errbotio/err-imagebot'
