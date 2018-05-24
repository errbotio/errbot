#!/usr/bin/env python

import errno
import jinja2
import os
import re
import sys
from configparser import ConfigParser

from errbot.version import VERSION


def new_plugin_wizard(directory=None):
    """
    Start the wizard to create a new plugin in the current working directory.
    """
    if directory is None:
        print('This wizard will create a new plugin for you in the current directory.')
        directory = os.getcwd()
    else:
        print(f'This wizard will create a new plugin for you in "{directory}".')

    if os.path.exists(directory) and not os.path.isdir(directory):
        print(f'Error: The path "{directory}" exists but it isn\'t a directory')
        sys.exit(1)

    name = ask("What should the name of your new plugin be?", validation_regex=r'^[a-zA-Z][a-zA-Z0-9 _-]*$').strip()
    module_name = name.lower().replace(' ', '_')
    directory_name = name.lower().replace(' ', '-')
    class_name = ''.join([s.capitalize() for s in name.lower().split(' ')])

    description = ask('What may I use as a short (one-line) description of your plugin?')
    python_version = '3'
    errbot_min_version = ask(f'Which minimum version of errbot will your plugin work with? '
                             f'Leave blank to support any version or input CURRENT to select '
                             f'the current version {VERSION}.').strip()
    if errbot_min_version.upper() == 'CURRENT':
        errbot_min_version = VERSION
    errbot_max_version = ask(f'Which maximum version of errbot will your plugin work with? '
                             f'Leave blank to support any version or input CURRENT to select '
                             f'the current version {VERSION}.').strip()
    if errbot_max_version.upper() == "CURRENT":
        errbot_max_version = VERSION

    plug = ConfigParser()
    plug['Core'] = {'Name': name,
                    'Module': module_name,
                    }
    plug['Documentation'] = {
        'Description': description,
    }
    plug['Python'] = {
        'Version': python_version,
    }

    if errbot_max_version != '' or errbot_min_version != '':
        plug['Errbot'] = {}
        if errbot_min_version != '':
            plug['Errbot']['Min'] = errbot_min_version
        if errbot_max_version != '':
            plug['Errbot']['Max'] = errbot_max_version

    plugin_path = directory
    plugfile_path = os.path.join(plugin_path, module_name + '.plug')
    pyfile_path = os.path.join(plugin_path, module_name + '.py')

    try:
        os.makedirs(plugin_path, mode=0o700)
    except IOError as e:
        if e.errno != errno.EEXIST:
            raise

    if os.path.exists(plugfile_path) or os.path.exists(pyfile_path):
        path = os.path.join(directory, f'{module_name}.{{py,plug}}')
        ask(f'Warning: A plugin with this name was already found at {path}\n'
            f'If you continue, these will be overwritten.\n'
            f'Press Ctrl+C to abort now or type in "overwrite" to confirm overwriting of these files.',
            valid_responses=['overwrite'],
            )

    with open(plugfile_path, 'w') as f:
        plug.write(f)

    with open(pyfile_path, 'w') as f:
        f.write(render_plugin(locals()))

    print(f'Success! You\'ll find your new plugin at \'{plugfile_path}\'')
    print('(Don\'t forget to include a LICENSE file if you are going to publish your plugin).')


def ask(question, valid_responses=None, validation_regex=None):
    """
    Ask the user for some input. If valid_responses is supplied, the user
    must respond with something present in this list.
    """
    response = None
    print(question)
    while True:
        response = input('> ')
        if valid_responses is not None:
            assert isinstance(valid_responses, list)
            if response in valid_responses:
                break
            else:
                print(f'Bad input: Please answer one of: {", ".join(valid_responses)}')
        elif validation_regex is not None:
            m = re.search(validation_regex, response)
            if m is None:
                print(f'Bad input: Please respond with something matching this regex: {validation_regex}')
            else:
                break
        else:
            break
    return response


def render_plugin(values):
    """
    Render the Jinja template for the plugin with the given values.
    """
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
        auto_reload=False,
        keep_trailing_newline=True,
        autoescape=True
    )
    template = env.get_template('new_plugin.py.tmpl')
    return template.render(**values)


if __name__ == '__main__':
    try:
        new_plugin_wizard()
    except KeyboardInterrupt:
        sys.exit(1)
