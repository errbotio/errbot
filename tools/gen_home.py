#!/usr/bin/env python3
from jinja2 import Template
import requests
import time
import ast
import json

template = Template(open('plugins.md').read())

blacklisted = [repo.strip() for repo in open('blacklisted.txt', 'r').readlines()]

PREFIX_LEN = len('https://github.com/')
with open('repos.json', 'r') as p:
    plugins = json.load(p)

    # Removes the weird forks of errbot itself and
    # blacklisted repos
    plugins = {
            plugin: values for plugin, values in plugins.items()
            if not values['path'].startswith('errbot') and
            values['repo'][PREFIX_LEN:] not in blacklisted}

    sorted_plugins = sorted(plugins.items())

    with open('sorted-dedupped-plugins.txt', 'w') as out:
        for plugin in sorted_plugins:
            out.write(repr(plugin))
            out.write('\n')

    with open('Home.md', 'w') as out:
        out.write(template.render(plugins=sorted_plugins))
