#!/usr/bin/env python3
from jinja2 import Template
import requests
import time
import ast

template = Template(open('plugins.md').read())

blacklisted = [repo.strip() for repo in open('blacklisted.txt', 'r').readlines()]

with open('repos.json', 'r') as p:
    plugins = ast.literal_eval(p.read())

    # Removes the weird forks of errbot itself and
    # blacklisted repos
    for plugin, values in plugins.items():
        if values['path'].startswith('errbot') or \
           plugin in blacklisted:
            plugins.pop(plugin)

    sorted_plugins = sorted(plugins.items())

    with open('sorted-dedupped-plugins.txt', 'w') as out:
        for plugin in sorted_plugins:
            out.write(repr(plugin))
            out.write('\n')

    with open('Home.md', 'w') as out:
        out.write(template.render(plugins=sorted_plugins))
