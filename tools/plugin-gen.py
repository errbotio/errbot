#!/usr/bin/env python3
import configparser
import json
import logging
import os
import pathlib
import sys
import time
from datetime import datetime

import requests
from requests.auth import HTTPBasicAuth

logging.basicConfig()

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

DEFAULT_AVATAR = 'https://upload.wikimedia.org/wikipedia/commons/5/5f/Err-logo.png'

user_cache = {}

try:
    with open('user_cache', 'r') as f:
        user_cache = eval(f.read())
except FileNotFoundError:
    # File doesn't exist, so we continue on
    log.info("No user cache existing, will be generating it for the first time.")


def get_auth():
    """Get auth creds from Github Token

    token is generated from the personal tokens in github
    """
    token_file = pathlib.Path('token')
    token_env = os.getenv('ERRBOT_REPOS_TOKEN')

    if token_file.is_file():
        try:
            token_info = open('token', 'r').read()
        except ValueError:
            log.fatal("Token file cannot be properly read, should be of the form username:token")
            sys.exit(-1)
    elif token_env:
        token_info = token_env
    else:
        msg = "No 'token' file or environment variable 'ERROBOT_REPOS_TOKEN' found."
        log.fatal(msg)
        sys.exit(-1)

    try:
        user, token = token_info.strip().split(':')
    except ValueError:
        msg = "Token file cannot be properly read, should be of the form username:token"
        log.fatal(msg)
        sys.exit(-1)

    auth = HTTPBasicAuth(user, token)
    return auth


AUTH = get_auth()


def add_blacklisted(repo):
    with open('blacklisted.txt', 'a') as f:
        f.write(repo)
        f.write('\n')


plugins = {}


def save_plugins():
    with open('repos.json', 'w') as f:
        json.dump(plugins, f, indent=2, separators=(',', ': '))


BLACKLISTED = []
try:
    with open('blacklisted.txt', 'r') as f:
        BLACKLISTED = [line.strip() for line in f.readlines()]
except FileNotFoundError:
    log.info("No blacklisted.txt found, no plugins will be blacklisted.")


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
    if delay < 0:  # time drift
        delay = 2
    time.sleep(delay)


def parse_date(gh_date: str) -> datetime:
    return datetime.strptime(gh_date, "%Y-%m-%dT%H:%M:%SZ")


def check_repo(repo):
    repo_name = repo.get('full_name', None)
    if repo_name is None:
        log.error('No name in %s', repo)
    log.debug('Checking %s...', repo_name)
    code_resp = requests.get('https://api.github.com/search/code?q=extension:plug+repo:%s' % repo_name, auth=AUTH)
    if code_resp.status_code != 200:
        log.error('Error getting https://api.github.com/search/code?q=extension:plug+repo:%s', repo_name)
        log.error('code %d', code_resp.status_code)
        log.error('content %s', code_resp.text)

        return
    plug_items = code_resp.json()['items']
    if not plug_items:
        log.debug('No plugin found in %s, blacklisting it.', repo_name)
        add_blacklisted(repo_name)
        return
    owner = repo['owner']
    avatar_url = owner['avatar_url'] if 'avatar_url' in owner else DEFAULT_AVATAR

    days_old = (datetime.now() - parse_date(repo['updated_at'])).days
    score = repo['stargazers_count'] + repo['watchers_count'] * 2 + repo['forks_count'] - days_old / 25

    for plug in plug_items:
        plugfile_resp = requests.get('https://raw.githubusercontent.com/%s/master/%s' % (repo_name, plug['path']))
        log.debug('Found a plugin:')
        log.debug('Repo:  %s', repo_name)
        log.debug('File:  %s', plug['path'])
        parser = configparser.ConfigParser()
        try:
            parser.read_string(plugfile_resp.text)

            name = parser['Core']['Name']
            log.debug('Name: %s', name)

            if 'Documentation' in parser and 'Description' in parser['Documentation']:
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
                'repo': repo['html_url'],
                'documentation': doc,
                'name': name,
                'python': python,
                'avatar_url': avatar_url,
                'score': score,
            }

            repo_entry = plugins.get(repo_name, {})
            repo_entry[name] = plugin
            plugins[repo_name] = repo_entry
            log.debug('Catalog added plugin %s.', plugin['name'])
        except:
            log.error('Invalid syntax in %s, skipping... ' % plug['path'])
            continue

        rate_limit(plugfile_resp)

    save_plugins()
    rate_limit(code_resp)


def find_plugins(query):
    url = 'https://api.github.com/search/repositories?q=%s+in:name+language:python&sort=stars&order=desc' % query
    while True:
        repo_resp = requests.get(url, auth=AUTH)
        repo_json = repo_resp.json()
        if repo_json.get('message', None) == 'Bad credentials':
            log.error('Invalid credentials, check your token file, see README.')
            sys.exit(-1)
        log.debug("Repo reqs before ratelimit %s/%s" % (repo_resp.headers['X-RateLimit-Remaining'],
                                                        repo_resp.headers['X-RateLimit-Limit']))
        if 'message' in repo_json and repo_json['message'].startswith('API rate limit exceeded for'):
            log.error('API rate limit hit anyway ... wait for 30s')
            time.sleep(30)
            continue
        items = repo_json['items']

        for repo in items:
            if repo['full_name'] in BLACKLISTED:
                log.debug('Skipping %s.', repo)
                continue
            check_repo(repo)
        if 'next' not in repo_resp.links:
            break
        url = repo_resp.links['next']['url']
        log.debug('Next url: %s', url)
        rate_limit(repo_resp)


def main():
    find_plugins('err')
    # Those are found by global search only available on github UI:
    # https://github.com/search?l=&q=Documentation+extension%3Aplug&ref=advsearch&type=Code&utf8=%E2%9C%93
    url = 'https://api.github.com/repos/%s'
    with open('extras.txt', 'r') as extras:
        for repo_name in extras:
            repo_name = repo_name.strip()
            repo_resp = requests.get(url % repo_name, auth=AUTH)
            repo = repo_resp.json()
            if repo.get('message', None) == 'Bad credentials':
                log.error('Invalid credentials, check your token file, see README.')
                sys.exit(-1)
            if 'message' in repo and repo['message'].startswith('API rate limit exceeded for'):
                log.error('API rate limit hit anyway ... wait for 30s')
                time.sleep(30)
                continue
            if 'message' in repo and repo['message'].startswith('Not Found'):
                log.error('%s not found.', repo_name)
            else:
                check_repo(repo)
            rate_limit(repo_resp)


if __name__ == "__main__":
    main()
