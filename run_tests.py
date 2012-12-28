#!/usr/bin/env python
import os
import sys
from setup import PY3, py2_root

import nose

if not PY3:  # hack the path system to take the python 2 converted sources
    sys.path.insert(0, py2_root)
    print('Changing root to ' + py2_root)
    print('Sys path ' + ', '.join(sys.path))
    nose.run('tests', argv = ['-v', '-w', py2_root])
else:
    nose.run('tests')