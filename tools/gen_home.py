#!/usr/bin/env python3
from jinja2 import Template
import requests
import time

template = Template(open('plugins.md').read())

blacklisted = [repo.strip() for repo in open('blacklisted.txt', 'r').readlines()]

DEFAULT_AVATAR = 'https://upload.wikimedia.org/wikipedia/commons/5/5f/Err-logo.png'

with open('plugins.txt', 'r') as p:
    plugins = [eval(line) for line in p]
    # Removes the weird forks of errbot itself.
    plugins = [plugin for plugin in plugins if not plugin['path'].startswith('errbot')]

    # Be sure to remove the blacklisted ones.
    plugins = [plugin for plugin in plugins if plugin['repo'] not in blacklisted]

    # Removes dupes from the same repos.
    plugins = {(plugin['repo'], plugin['name']): plugin for plugin in plugins}.values()

    plugins = sorted(plugins, key=lambda plug: plug['name'])

    for plugin in plugins:
        if 'wikipedia' in plugin['avatar_url']:
            print("Query avatar for %s" % plugin['repo'])
            user = requests.get('https://api.github.com/users/' + plugin['repo'].split('/')[0]).json()
            time.sleep(12)  # github has a rate limiter.
            plugin['avatar_url'] = user['avatar_url'] if 'avatar_url' in user else DEFAULT_AVATAR
            print("Got %s" % plugin['avatar_url'])

    with open('Home.md', 'w') as out:
        out.write(template.render(plugins=plugins))
    with open('plugin-with-avatar.txt', 'w') as out:
        for plugin in plugins:
            out.write(repr(plugin))
            out.write('\n')
