import ast
import logging
import os
import shutil
import subprocess
import urllib.request
from collections import namedtuple
from datetime import timedelta, datetime
from os import path
from tarfile import TarFile
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import json

import re

from errbot.plugin_manager import check_dependencies
from errbot.storage import StoreMixin
from errbot.version import VERSION
from .utils import PY2, which, human_name_for_git_url

log = logging.getLogger(__name__)


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

INSTALLED_REPOS = b'installed_repos' if PY2 else 'installed_repos'

REPO_INDEXES_CHECK_INTERVAL = timedelta(hours=1)

REPO_INDEX = b'repo_index' if PY2 else 'repo_index'
LAST_UPDATE = 'last_update'

RepoEntry = namedtuple('RepoEntry', 'entry_name, name, python, repo, path, avatar_url, documentation')
find_words = re.compile(r"(\w[\w']*\w|\w)")


def makeEntry(json_key, json_value):
    return RepoEntry(entry_name=json_key.split('~')[0],
                     name=json_value['name'],
                     python=json_value['python'],
                     repo=json_value['repo'],
                     path=json_value['path'],
                     avatar_url=json_value['avatar_url'],
                     documentation=json_value['documentation'])


def tokenizeJsonEntry(json_dict):
    """
    Returns all the words in a repo entry.
    """
    return set(find_words.findall(' '.join((word.lower() for word in json_dict.values()))))


class BotRepoManager(StoreMixin):
    """
    Manages the repo list, git clones/updates or the repos.
    """
    def __init__(self, storage_plugin, plugin_dir, plugin_indexes):
        """
        Make a repo manager.
        :param storage_plugin: where the manager store its state.
        :param plugin_dir: where on disk it will git clone the repos.
        :param plugin_indexes: a list of URL / path to get the json repo index.
        """
        super()
        self.plugin_indexes = plugin_indexes
        self.storage_plugin = storage_plugin
        self.plugin_dir = plugin_dir
        self.open_storage(storage_plugin, 'repomgr')

    def check_for_index_update(self):
        if REPO_INDEX not in self:
            log.info('No repo index, creating it.')
            self[REPO_INDEX] = {LAST_UPDATE: 0}

        if datetime.fromtimestamp(self[REPO_INDEX][LAST_UPDATE]) < datetime.now() - REPO_INDEXES_CHECK_INTERVAL:
            log.debug('Index is too old, update it.')
            self.index_update()

    def index_update(self):
        index = {LAST_UPDATE: datetime.now().timestamp()}
        for source in reversed(self.plugin_indexes):
            src_file = None
            try:
                if source.startswith('http'):
                    log.debug('Update from remote source %s...', source)
                    src_file = urlopen(url=source, timeout=10)
                else:
                    log.debug('Update from local source %s...', source)
                    src_file = open(source, 'r')

                index.update(json.loads(src_file.read()))
            except (HTTPError, URLError, IOError):
                log.exception('Could not update from source %s, keep the index as it is.', source)
                break
            finally:
                if src_file:
                    src_file.close()
        else:
            # nothing failed so ok, we can store the index.
            self[REPO_INDEX] = index
            log.debug('Stored %d repo entries.', len(index) - 1)

    def search_repos(self, query):
        """
        A simple search feature, keywords are AND and case insensitive on all the fields.

        :param query: a string query
        :return: an iterator of RepoEntry
        """
        # first see if we are up to date.
        self.check_for_index_update()
        if REPO_INDEX not in self:
            log.error('No index.')
            return
        query_work_set = set(find_words.findall(query.lower()))
        for key, entry in self[REPO_INDEX].items():
            if key == LAST_UPDATE:
                continue
            if query_work_set.intersection(tokenizeJsonEntry(entry)):
                yield makeEntry(key, entry)

    def get_installed_plugin_repos(self):

        repos = self.get(INSTALLED_REPOS, {})

        if not repos:
            return repos

        # Fix to migrate exiting plugins into new format
        for url in self.get(INSTALLED_REPOS, repos).values():
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
        self[INSTALLED_REPOS] = repos

    def set_plugin_repos(self, repos):
        """ Used externally.
        """
        self[INSTALLED_REPOS] = repos

    def get_all_repos_paths(self):
        return [self.plugin_dir + os.sep + d for d in self.get(INSTALLED_REPOS, {}).keys()]

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

    def update_repos(self, repos):
        """
        This git pulls the specified repos on disk.
        Yields tuples like (name, success, reason)
        """
        git_path = which('git')
        if not git_path:
            yield ('everything', False, 'git command not found: You need to have git installed on '
                                        'your system to be able to install git based plugins.')

        # protects for update outside of what we know is installed
        names = set(self.get_installed_plugin_repos().keys()).intersection(set(repos))

        for d in (path.join(self.plugin_dir, name) for name in names):
            p = subprocess.Popen([git_path, 'pull'], cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            feedback = p.stdout.read().decode('utf-8') + '\n' + '-' * 50 + '\n'
            err = p.stderr.read().strip().decode('utf-8')
            if err:
                feedback += err + '\n' + '-' * 50 + '\n'
            dep_err = check_dependencies(d)
            if dep_err:
                feedback += dep_err + '\n'
            yield d, not p.wait(), feedback

    def update_all_repos(self):
        return self.update_repos(self.get_installed_plugin_repos().keys())

    def uninstall_repo(self, name):
        repo_path = path.join(self.plugin_dir, name)
        shutil.rmtree(repo_path)
        repos = self.get_installed_plugin_repos().pop(name)
        self.set_plugin_repos(repos)
