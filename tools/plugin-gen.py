#!/usr/bin/env python3
from datetime import datetime

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
        user_res = requests.get('https://api.github.com/users/' + username, auth=AUTH)
        user = user_res.json()
        if 'avatar_url' in user:  # don't pollute the presistent cache
            user_cache[username] = user
            with open('user_cache', 'w') as f:
                f.write(repr(user_cache))
        rate_limit(user_res)
    return user['avatar_url'] if 'avatar_url' in user else DEFAULT_AVATAR


def rate_limit(resp):
    """
    Wait enough to be in the budget for this request.
    :param resp: the http response from github
    :return:
    """
    if 'X-RateLimit-Remaining' not in resp.headers:
        log.info("No rate limit detected. Hum along...")
        return
    remain = int(resp.headers['X-RateLimit-Remaining'])
    limit = int(resp.headers['X-RateLimit-Limit'])
    log.info('Rate limiter: %s allowed out of %d', remain, limit)
    if remain > 1:  # margin by one request
        return
    reset = int(resp.headers['X-RateLimit-Reset'])
    ts = datetime.fromtimestamp(reset)
    delay = (ts - datetime.now()).total_seconds()
    log.info("Hit rate limit. Have to wait for %d seconds", delay)
    time.sleep(delay)


def check_repo(repo):
    log.debug('Checking %s...', repo)
    code_resp = requests.get('https://api.github.com/search/code?q=extension:plug+repo:%s' % repo, auth=AUTH)
    if code_resp.status_code != 200:
        log.error('Error getting https://api.github.com/search/code?q=extension:plug+repo:%s', repo)
        log.error('code %d', code_resp.status_code)
        log.error('content %s', code_resp.text)

        return
    plug_items = code_resp.json()['items']
    if not plug_items:
        log.debug('No plugin found in %s, blacklisting it.', repo)
        add_blacklisted(repo)
        return
    avatar_url = get_avatar_url(repo)

    for plug in plug_items:
        plugfile_resp = requests.get('https://raw.githubusercontent.com/%s/master/%s' % (repo, plug["path"]))
        log.debug('Found a plugin:')
        log.debug('Repo:  %s', repo)
        log.debug('File:  %s', plug['path'])
        parser = configparser.ConfigParser()
        parser.read_string(plugfile_resp.text)
        name = parser['Core']['Name']
        log.debug('Name: %s', name)

        if 'Documentation' in parser:
            doc = parser['Documentation']['Description']
            log.debug('Documentation: %s', doc)
        else:
            doc = ''

        if 'Python' in parser:
            python = parser['Python']['Version']
            log.debug('Python Version: %s', python)
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
        rate_limit(plugfile_resp)

    save_plugins()
    rate_limit(code_resp)


def find_plugins():
    url = 'https://api.github.com/search/repositories?q=err+in:name+language:python&sort=stars&order=desc'
    while True:
        repo_resp = requests.get(url, auth=AUTH)
        repo_json = repo_resp.json()
        if repo_json.get('message', None) == 'Bad credentials':
            log.error('Invalid credentials, check your token file, see README.')
            sys.exit(-1)
        log.debug("Repo reqs before ratelimit %s/%s" % (
            repo_resp.headers['X-RateLimit-Remaining'],
            repo_resp.headers['X-RateLimit-Limit']))
        items = repo_json['items']

        for i, item in enumerate(items):
            repo = item['full_name']
            if repo in BLACKLISTED:
                log.debug('Skipping %s.', repo)
                continue
            check_repo(repo)
        if 'next' not in repo_resp.links:
            break
        url = repo_resp.links['next']['url']
        log.debug('Next url: %s', url)
        rate_limit(repo_resp)


def main():
    find_plugins()
    # Those are found by global search only available on github UI:
    # https://github.com/search?l=&q=Documentation+extension%3Aplug&ref=advsearch&type=Code&utf8=%E2%9C%93
    with open('extras.txt', 'r') as extras:
        for repo in extras:
            check_repo(repo.strip())

if __name__ == "__main__":
    main()
