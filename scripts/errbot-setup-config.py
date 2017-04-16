#!/usr/bin/env python

import errbot
import os
import shutil

shutil.copyfile(os.path.dirname(errbot.__file__) + os.path.sep + 'config-template.py', 'config.py')
