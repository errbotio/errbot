#!/usr/bin/env python

import pytest
import subprocess
import sys

PY35 = sys.version_info >= (3, 5, 0)

pep8_result = 0
pypi_linting = 0

if PY35:
    # only need to test it once under the latest version (for travis.ci).
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
    print("Skipping linting, those run only under python 3.5+")

if pep8_result != 0:
    print("Pep8 failed.")
    sys.exit(-1)

if pypi_linting != 0:
    print("Pypi linting failed (check README.rst and CHANGES.rst).")
    sys.exit(-2)

pytest_result = pytest.main('-x')

if pytest_result or pep8_result:
    sys.exit(1)
