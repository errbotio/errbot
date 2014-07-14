#!/usr/bin/env python

import pytest
import subprocess
import sys

pytest_result = pytest.main()
# py.test has a pep8 plugin, however it has considerably fewer options
# for configuration, hence the use of the stand-alone pep8 checker instead.
pep8_result = subprocess.call(["pep8", "--statistics", "--show-source"])

if pytest_result or pep8_result:
    sys.exit(1)
