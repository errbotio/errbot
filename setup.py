#!/usr/bin/env python

#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os
import sys
from glob import glob
from platform import system
from setuptools import setup, find_packages

py_version = sys.version_info[:2]
PY2 = py_version[0] == 2
PY3 = not PY2
ON_WINDOWS = system() == 'Windows'

if py_version < (2, 7):
    raise RuntimeError('Err requires Python 2.7 or later')

if PY3 and py_version < (3, 4):
    raise RuntimeError('On Python 3, Err requires Python 3.3 or later')

deps = ['webtest',
        'setuptools',
        'bottle',
        'requests',
        'jinja2',
        'pyOpenSSL',
        'colorlog',
        'yapsy>=1.11',  # new contract for plugin instantiation
        'markdown',  # rendering stuff
        'ansi',
        'Pygments>=2.0.2',
        'pygments-markdown-lexer>=0.1.0.dev39',  # sytax coloring to debug md
        ]

if PY2:
    deps += ['dnspython',  # dnspython is needed for SRV records
             'config',
             'backports.functools_lru_cache']
else:
    deps += ['dnspython3', ]  # dnspython3 for SRV records

# Extra dependencies for a development environment.
if 'develop' in sys.argv:
    deps += ['mock',
             'nose',
             'pep8',
             'pytest',
             'pytest-xdist',
             'PyOpenSSL']

if not ON_WINDOWS:
    deps += ['daemonize']

src_root = os.curdir
sys.path.insert(0, os.path.join(src_root, 'errbot'))  # hack to avoid loading err machinery from the errbot package


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


if __name__ == "__main__":
    from version import VERSION

    changes = read('CHANGES.rst')

    if changes.find(VERSION) == -1:
        raise Exception('You forgot to put a release note in CHANGES.rst ?!')

    if set(sys.argv) & {'bdist', 'bdist_dumb', 'bdist_rpm', 'bdist_wininst', 'bdist_msi'}:
        raise Exception("err doesn't support binary distributions")

    # under python2 if we want to make a source distribution,
    # don't pre-convert the sources, leave them as py3.
    if PY2 and ('install' in sys.argv or 'develop' in sys.argv):
        from py2conv import convert_to_python2
        convert_to_python2()

    setup(
        name="err",
        version=VERSION,
        packages=find_packages(src_root),
        scripts=['scripts/err.py'],

        install_requires=deps,
        tests_require=['nose', 'webtest', 'requests'],
        package_data={
            '': ['*.txt', '*.rst', '*.plug', '*.md', '*.js', '*.css'],
        },

        author="Guillaume BINET",
        author_email="gbin@gootz.net",
        description="err is a plugin based team chatbot designed to be easily deployable, extensible and maintainable.",
        long_description=''.join([read('README.rst'), '\n\n', changes]),
        license="GPL",
        keywords="xmpp jabber chatbot bot plugin",
        url="http://errbot.net/",
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Topic :: Communications :: Chat",
            "Topic :: Communications :: Chat :: Internet Relay Chat",
            "Topic :: Communications :: Conferencing",
            "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.3",
            "Programming Language :: Python :: 3.4",
        ],
        src_root=src_root,
        platforms='any',
    )

# restore the paths
sys.path.remove(os.path.join(src_root, 'errbot'))
