#!/usr/bin/env python

import configparser
import os
import re
import requests
import sys

from errbot import PY2

if PY2:
    input = raw_input


def new_plugin_wizard(directory=None):
    """
    Start the wizard to create a new plugin in the current working directory.
    """
    if directory is None:
        print("This wizard will create a new plugin for you in the current directory.")
        directory = os.getcwd()
    else:
        print("This wizard will create a new plugin for you in '%s'." % directory)

    if not os.path.isdir(directory):
        print("Error: The path '%s' does not exist or is not a directory." % directory)
        sys.exit(1)

    try:
        plugin_code = download_plugin_skeleton()
    except requests.HTTPError as e:
        print(
            "Error: I couldn't download the plugin skeleton from GitHub "
            "which is needed to write out a new plugin file for you."
        )
        print("Details: {!s}".format(e))
        sys.exit(1)

    name = ask(
        "What should the name of your new plugin be?",
        validation_regex=r'^[a-zA-Z][a-zA-Z0-9 _-]*$'
    ).strip()
    module_name = name.lower().replace(' ', '_')
    class_name = "".join([s.capitalize() for s in name.lower().split(' ')])

    description = ask(
        "What may I use as a short (one-line) description of your plugin?"
    )
    python_version = ask(
        "Which python version will your plugin work with? 2, 2+ or 3?",
        valid_responses=['2', '2+', '3']
    )
    errbot_min_version = ask(
        "Which minimum version of errbot will your plugin work with? Leave blank to support any version"
    ).strip()
    errbot_max_version = ask(
        "Which maximum version of errbot will your plugin work with? Leave blank to support any version"
    ).strip()

    plug = configparser.ConfigParser()
    plug["Core"] = {
        "Name": name,
        "Module": module_name,
    }
    plug["Documentation"] = {
        "Description": description,
    }
    plug["Python"] = {
        "Version": python_version,
    }
    plug["Errbot"] = {}
    if errbot_min_version != "":
        plug["Errbot"]["Min"] = errbot_min_version
    if errbot_max_version != "":
        plug["Errbot"]["Max"] = errbot_max_version

    plug_path = os.path.join(directory, module_name+".plug")
    py_path = os.path.join(directory, module_name+".py")
    if os.path.exists(plug_path) or os.path.exists(py_path):
        print(
            "Warning: A plugin with this name was already found at {path}\n"
            "If you continue, these will be overwritten.".format(
                path=os.path.join(directory, module_name+".{py,plug}")
            )
        )
        ask(
            "Press Ctrl+C to abort now or type in 'overwrite' to confirm overwriting of these files.",
            valid_responses=["overwrite"],
        )

    with open(plug_path, 'w') as f:
        plug.write(f)

    plugin_code = plugin_code.replace("class Skeleton(", "class %s(" % class_name)
    plugin_code = plugin_code.replace("Fill in your plugin description here.", description)

    with open(py_path, 'w') as f:
        f.write(plugin_code)

    print("Success! You'll find your new plugin at '%s'" % py_path)


def ask(question, valid_responses=None, validation_regex=None):
    """
    Ask the user for some input. If valid_responses is supplied, the user
    must respond with something present in this list.
    """
    response = None
    print(question)
    while True:
        response = input("> ")
        if valid_responses is not None:
            assert isinstance(valid_responses, list)
            if response in valid_responses:
                break
            else:
                print("Bad input: Please answer one of: %s" % ", ".join(valid_responses))
        elif validation_regex is not None:
            m = re.search(validation_regex, response)
            if m is None:
                print("Bad input: Please respond with something matching this regex: %s" % validation_regex)
            else:
                break
        else:
            break
    return response


def download_plugin_skeleton():
    """
    Download the plugin skeleton from https://github.com/errbotio/plugin-skeleton.

    Returns the contents of skeleton.py from the one on GitHub.
    """
    response = requests.get("https://github.com/errbotio/plugin-skeleton/raw/master/skeleton.py")
    response.raise_for_status()
    return response.text


if __name__ == "__main__":
    try:
        new_plugin_wizard()
    except KeyboardInterrupt:
        sys.exit(1)
