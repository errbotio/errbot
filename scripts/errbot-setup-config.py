#!/usr/bin/env python

from __future__ import absolute_import
import errbot
import os
import shutil

shutil.copyfile(os.path.dirname(errbot.__file__) + os.path.sep + u'config-template.py', u'config.py')
