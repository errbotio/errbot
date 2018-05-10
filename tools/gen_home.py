#!/usr/bin/env python3
import json

from jinja2 import Template

template = Template(open("plugins.md").read())

blacklisted = [repo.strip() for repo in open("blacklisted.txt", "r").readlines()]

PREFIX_LEN = len("https://github.com/")

with open("repos.json", "r") as p:
    repos = json.load(p)

    # Removes the weird forks of errbot itself and
    # blacklisted repos
    filtered_plugins = []
    for repo, plugins in repos.items():
        for name, plugin in plugins.items():
            if plugin["path"].startswith("errbot/builtins"):
                continue
            if plugin["repo"][PREFIX_LEN:] in blacklisted:
                continue
            filtered_plugins.append(plugin)

    sorted_plugins = sorted(filtered_plugins, key=lambda plugin: -plugin["score"])

    with open("Home.md", "w") as out:
        out.write(template.render(plugins=sorted_plugins))
