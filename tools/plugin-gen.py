#!/usr/bin/env python3

import requests
import sys
from requests.auth import HTTPBasicAuth
import logging
import time
import configparser
import json
logging.basicConfig()

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

DEFAULT_AVATAR = 'https://upload.wikimedia.org/wikipedia/commons/5/5f/Err-logo.png'

# token is generated from the personal tokens in github.
AUTH = HTTPBasicAuth('gbin', open('token', 'r').read().strip())

# for authenticated requests the limit is 5000 req/hours
PAUSE = 3600.0 / 5000.0

# for searchs it is 50 request per minute
SEARCH_PAUSE = 60.0 / 50.0

user_cache = {}

with open('user_cache', 'r') as f:
    user_cache = eval(f.read())


def add_blacklisted(repo):
    with open('blacklisted.txt', 'a') as f:
        f.write(repo)
        f.write('\n')

plugins = {}


def save_plugins():
    with open('repos.json', 'w') as f:
        f.write(json.dumps(plugins))

with open('blacklisted.txt', 'r') as f:
    BLACKLISTED = [line.strip() for line in f.readlines()]


def get_avatar_url(repo):
    username = repo.split('/')[0]
    if username in user_cache:
        user = user_cache[username]
    else:
        time.sleep(PAUSE)
        user_res = requests.get('https://api.github.com/users/' + username, auth=AUTH)
        log.debug("User reqs before ratelimit %s/%s" % (
            user_res.headers['X-RateLimit-Remaining'],
            user_res.headers['X-RateLimit-Limit']))
        user = user_res.json()
        if 'avatar_url' in user:  # don't pollute the presistent cache
            user_cache[username] = user
            with open('user_cache', 'w') as f:
                f.write(repr(user_cache))
    return user['avatar_url'] if 'avatar_url' in user else DEFAULT_AVATAR


def check_repo(repo):
    log.debug('Checking %s...', repo)
    time.sleep(SEARCH_PAUSE)
    code_resp = requests.get('https://api.github.com/search/code?q=extension:plug+repo:%s' % repo, auth=AUTH)
    log.debug("Search before ratelimit %s/%s" % (
        code_resp.headers['X-RateLimit-Remaining'],
        code_resp.headers['X-RateLimit-Limit']))
    plug_items = code_resp.json()['items']
    if not plug_items:
        log.debug('No plugin found in %s, blacklisting it.', repo)
        add_blacklisted(repo)
        return
    avatar_url = get_avatar_url(repo)

    for plug in plug_items:
        time.sleep(PAUSE)
        f = requests.get('https://raw.githubusercontent.com/%s/master/%s' % (repo, plug["path"]))
        log.debug('Found a plugin:')
        log.debug('Repo:  %s', repo)
        log.debug('File:  %s', plug['path'])
        parser = configparser.ConfigParser()
        parser.read_string(f.text)
        name = parser['Core']['Name']
        log.debug('Name: %s' % name)

        if 'Documentation' in parser:
            doc = parser['Documentation']['Description']
            log.debug('Documentation: %s' % doc)
        else:
            doc = ''

        if 'Python' in parser:
            python = parser['Python']['Version']
            log.debug('Python Version: %s' % python)
        else:
            python = '2'

        plugin = {
            'path': plug['path'],
            'repo': 'https://github.com/{0}'.format(repo),
            'documentation': doc,
            'name': name,
            'python': python,
            'avatar_url': avatar_url,
        }

        plugins[repo+'~'+name] = plugin
        log.debug('Catalog added plugin %s.', plugin['name'])

    save_plugins()


def find_plugins():
    url = 'https://api.github.com/search/repositories?q=err+in:name+language:python&sort=stars&order=desc'
    while True:
        time.sleep(PAUSE)
        repo_req = requests.get(url, auth=AUTH)
        repo_resp = repo_req.json()
        if repo_resp.get('message', None) == 'Bad credentials':
            log.error('Invalid credentials, check your token file, see README.')
            sys.exit(-1)
        log.debug("Repo reqs before ratelimit %s/%s" % (
            repo_req.headers['X-RateLimit-Remaining'],
            repo_req.headers['X-RateLimit-Limit']))
        items = repo_resp['items']

        for i, item in enumerate(items):
            repo = item['full_name']
            if repo in BLACKLISTED:
                log.debug('Skipping %s.', repo)
                continue
            check_repo(repo)
        if 'next' not in repo_req.links:
            break
        url = repo_req.links['next']['url']
        log.debug('Next url: %s', url)


def main():
    find_plugins()
    # Those are found by global search only available on github UI:
    # https://github.com/search?l=&q=Documentation+extension%3Aplug&ref=advsearch&type=Code&utf8=%E2%9C%93
    with open('extras.txt', 'r') as extras:
        for repo in extras:
            check_repo(repo.strip())

if __name__ == "__main__":
    main()
