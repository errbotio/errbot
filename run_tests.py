#!/usr/bin/env python
import sys
from setup import PY3, py2_root

try:
    import nose
except ImportError:
    sys.stderr.write("Tests require the 'nose' package which you are currently missing.\nYou can install nose with `pip install nose`.\n")
    sys.exit(1)

try:
    import webtest
except ImportError:
    sys.stderr.write("Tests require the 'webtest' package which you are currently missing.\nYou can install webtest with `pip install webtest`.\n")
    sys.exit(1)

if not PY3:  # hack the path system to take the python 2 converted sources
    print('Changing root to ' + py2_root)
    print('Sys path ' + ', '.join(sys.path))
    if nose.run('tests', argv=['-v', '-w', py2_root]):
        exit(0)  # no error
else:
    if nose.run('tests'):
        exit(0)  # no error
exit(-99)  # a test did not pass
