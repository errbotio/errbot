#!/usr/bin/env python

import pytest
import subprocess
import sys

PY3 = sys.version_info[0] == 3

pytest_result = pytest.main('-x')

# Skip pep8 checks on Python 2 because the code conversion done by
# 3to2 tends to mess things up
if PY3:
    # py.test has a pep8 plugin, however it has considerably fewer options
    # for configuration, hence the use of the stand-alone pep8 checker instead.
    pep8_result = subprocess.call(["pep8", "--statistics", "--show-source"])
else:
    print("Running under Python 2, skipping pep8 style checks")
    pep8_result = 0

if pytest_result or pep8_result:
    sys.exit(1)
