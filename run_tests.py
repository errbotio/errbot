#!/usr/bin/env python

import os
import pytest
import subprocess
import sys
try:
    from shlex import quote
except ImportError:
    from pipes import quote

PY2 = sys.version_info < (3, 0, 0)

pep8_result = 0
pypi_linting = 0

if not PY2:
    # py.test has a pep8 plugin, however it has considerably fewer options
    # for configuration, hence the use of the stand-alone pep8 checker instead.
    pep8_result = subprocess.call(['pep8', '--statistics', '--show-source'])

    travis = os.environ.get("TRAVIS", "") == "true"
    if not travis or (travis and sys.version_info >= (3, 5, 0)):
        # RestructuredText linting fails on Python 3.3 and 3.4 on Travis for mysterious
        # reasons (it passes fine locally on Python 3.4)
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

pytest_result = pytest.main(" ".join([quote(arg) for arg in sys.argv[1:]]))

if pytest_result or pep8_result:
    sys.exit(1)
