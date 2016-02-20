import os
import urllib.request
import ast
from tarfile import TarFile

import subprocess

from errbot.storage import StoreMixin
from .utils import PY2, which, human_name_for_git_url


def get_known_repos():
    """
    Get known repos from registry

    An example entry of the json file is the following
    'errbotio/err-pypi': {
        'avatar_url': None,
        'documentation': 'some commands to query pypi',
        'path': 'https://github.com/errbotio/err-pypi.git',
        'python': None
    }, ...
    """
    registry_url = 'http://bit.ly/1kjdlRX'
    registry = urllib.request.urlopen(registry_url).read()
    return ast.literal_eval(registry.decode('utf-8'))

KNOWN_PUBLIC_REPOS = get_known_repos()

REPOS = b'repos' if PY2 else 'repos'


class BotRepoManager(StoreMixin):
    """
    Manages the repo list, git clones/updates or the repos.
    """
    def __init__(self, storage_plugin, plugin_dir):
        self.storage_plugin = storage_plugin
        self.plugin_dir = plugin_dir
        self.open_storage(storage_plugin, 'repomgr')

    def get_installed_plugin_repos(self):

        repos = self.get(REPOS, {})

        if not repos:
            return repos

        # Fix to migrate exiting plugins into new format
        for url in self.get(REPOS, repos).values():
            if type(url) == dict:
                continue
            t_name = '/'.join(url.split('/')[-2:])
            name = t_name.replace('.git', '')

            t_repo = {name: {
                'path': url,
                'documentation': 'Unavilable',
                'python': None,
                'avatar_url': None,
                }
            }
            repos.update(t_repo)
        return repos

    def add_plugin_repo(self, name, url):
        if PY2:
            name = name.encode('utf-8')
            url = url.encode('utf-8')
        repos = self.get_installed_plugin_repos()

        t_installed = {name: {
            'path': url,
            'documentation': 'Unavailable',
            'python': None,
            'avatar_url': None,
            }
        }

        repos.update(t_installed)
        self[REPOS] = repos

    def set_plugin_repos(self, repos):
        """ Used externally.
        """
        self[REPOS] = repos

    def get_all_repos_paths(self):
        return [self.plugin_dir + os.sep + d for d in self.get(REPOS, {}).keys()]

    def install_repo(self, repo):
        if repo in KNOWN_PUBLIC_REPOS:
            repo = KNOWN_PUBLIC_REPOS[repo]['path']  # replace it by the url
        git_path = which('git')

        if not git_path:
            return ('git command not found: You need to have git installed on '
                    'your system to be able to install git based plugins.', )

        # TODO: Update download path of plugin.
        if repo.endswith('tar.gz'):
            tar = TarFile(fileobj=urllib.urlopen(repo))
            tar.extractall(path=self.plugin_dir)
            s = repo.split(':')[-1].split('/')[-2:]
            human_name = '/'.join(s).rstrip('.tar.gz')
        else:
            human_name = human_name_for_git_url(repo)
            p = subprocess.Popen([git_path, 'clone', repo, human_name], cwd=self.plugin_dir, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            feedback = p.stdout.read().decode('utf-8')
            error_feedback = p.stderr.read().decode('utf-8')
            if p.wait():
                return "Could not load this plugin: \n\n%s\n\n---\n\n%s" % (feedback, error_feedback),

        self.add_plugin_repo(human_name, repo)
