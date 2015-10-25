#!/usr/bin/env python3
from jinja2 import Template
template = Template(open('plugins.md').read())


with open('plugins.txt', 'r') as p:
    plugins = [eval(line) for line in p]

    with open('Home.md', 'w') as out:
        out.write(template.render(plugins=plugins))
