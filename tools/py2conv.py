#!/usr/bin/env python
# Tool to convert err from python3 to python2

from glob import glob
import sys
import os
py_version = sys.version_info[:2]

lib3to2_input_sources = ["errbot", "scripts", "tests"]
# Avoid running config templates through lib3to2. For background info,
# see https://github.com/errbotio/errbot/issues/339
lib3to2_exclude = glob(os.path.join("errbot", "config-*.py"))
lib3to2_exclude += glob(os.path.join("errbot", "templates", "*"))
PY2 = py_version[0] == 2


def walk_lib3to2_input_sources():
    """
    Recursively walk through lib3to2 inputs, returning all the
    files detected while respecting the exclude list.
    """
    for source in lib3to2_input_sources:
        for root, directories, filenames in os.walk(source):
            for filename in filenames:
                path = os.path.join(root, filename)
                if path not in lib3to2_exclude and path.endswith('.py'):
                    # Yes, I'm aware this is a nesting monstrosity :)
                    yield path


def convert_to_python2():
    """
    Convert errbot source code (which is written for Python 3) to
    Python 2-compatible code (in-place) using lib3to2.
    """
    try:
        from lib3to2 import main as three2two
    except ImportError:
        print("Installing Err under Python 2, which requires 3to2 to be installed, but it was not found")
        print("I will now attempt to install it automatically, but this requires at least pip 1.4 to be installed")
        print("If you get the error 'no such option: --no-clean', please `pip install 3to2` manually and "
              "then `pip install err` again.")

        from pip import main as mainpip
        mainpip(['install', '3to2', '--no-clean'])
        from lib3to2 import main as three2two

    files_to_convert = list(walk_lib3to2_input_sources())
    three2two.main("lib3to2.fixes", ["-n", "--no-diffs", "-w"] + files_to_convert)


if __name__ == "__main__":
    if not PY2:
        raise Exception("This tool should only be used from a python2 environment")
    convert_to_python2()
