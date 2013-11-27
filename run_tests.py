#!/usr/bin/env python
import sys
import os
from glob import glob
from setup import PY3, py2_root

TRAVIS_INCOMPATIBLE = ('webhooks_tests.py',)

# Set nose verbosity level to verbose by default
os.environ['NOSE_VERBOSE'] = os.environ.get('NOSE_VERBOSE', "2")

try:
    import nose
except ImportError:
    sys.stderr.write("Tests require the 'nose' package which you are currently missing.\nYou can install nose with `pip install nose`.\n")
    sys.exit(1)

if not PY3:  # hack the path system to take the python 2 converted sources
    print('Changing root to ' + py2_root)
    print('Sys path ' + ', '.join(sys.path))

# Webhooks tests fail when run together with the other tests, but pass correctly
# when run in isolation. We work around this issue by running each set of tests
# separately. It's an ugly hack, but it works.
segments = ('tests', '*.py') if PY3 else (py2_root, 'tests', '*.py')
testsuites = glob(os.sep.join(segments))
testresults = []

for testsuite in testsuites:
    if os.environ.get("TRAVIS", "False") == "true" and os.path.basename(testsuite) in TRAVIS_INCOMPATIBLE:
        print("Incompatible test {} skipped".format(testsuite))
        continue
    print("\nRunning tests from {}\n".format(testsuite))
    testresults.append(nose.run(defaultTest=testsuite))

if False in testresults:
    print("\nSome tests failed to pass!")
    exit(-99)   # a test did not pass
else:
    print("\nAll tests have successfully passed")
    exit(0)  # no error
