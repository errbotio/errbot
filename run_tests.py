#!/usr/bin/env python

import pytest
import subprocess
import sys

PY3 = sys.version_info >= (3, 0, 0)

pep8_result = 0
pypi_linting = 0

if PY3:
    # py.test has a pep8 plugin, however it has considerably fewer options
    # for configuration, hence the use of the stand-alone pep8 checker instead.
    pep8_result = subprocess.call(['pep8', '--statistics', '--show-source'])
    pypi_linting = subprocess.call(['./setup.py',
                                    'check',
                                    '--restructuredtext',
                                    '--strict',
                                    '--metadata',
                                    ])
else:
    print("Skipping linting, these run only under python 3")

if pep8_result != 0:
    print("Pep8 failed.")
    sys.exit(-1)

if pypi_linting != 0:
    print("PyPI linting failed (check README.rst and CHANGES.rst).")
    sys.exit(-2)

pytest_result = pytest.main('-x')

if pytest_result or pep8_result:
    sys.exit(1)
