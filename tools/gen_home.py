#!/usr/bin/env python3
import json

from jinja2 import Template

template = Template(open("plugins.md").read())

blocklist = [repo.strip() for repo in open("blocklist.txt", "r").readlines()]

PREFIX_LEN = len("https://github.com/")

with open("repos.json", "r") as p:
    repos = json.load(p)

    # Removes the weird forks of errbot itself and
    # blocklist repos
    filtered_plugins = []
    for repo, plugins in repos.items():
        for name, plugin in plugins.items():
            if plugin["path"].startswith("errbot/builtins"):
                continue
            if plugin["repo"][PREFIX_LEN:] in blocklist:
                continue
            filtered_plugins.append(plugin)

    sorted_plugins = sorted(filtered_plugins, key=lambda plugin: -plugin["score"])

    with open("Home.md", "w") as out:
        out.write(template.render(plugins=sorted_plugins))
