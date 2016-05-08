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

from platform import system
from setuptools import setup, find_packages

py_version = sys.version_info[:2]
PY2 = py_version[0] == 2
PY3 = not PY2
PY35_OR_GREATER = py_version[:2] >= (3, 5)

ON_WINDOWS = system() == 'Windows'

if py_version < (2, 7):
    raise RuntimeError('Errbot requires Python 2.7 or later')

if PY3 and py_version < (3, 3):
    raise RuntimeError('On Python 3, Errbot requires Python 3.3 or later')

deps = ['webtest',
        'setuptools',
        'bottle',
        'threadpool',
        'rocket-errbot',
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
             'backports.functools_lru_cache',
             'configparser>=3.5.0b2', ]  # This is a backport from Python 3
else:
    deps += ['dnspython3', ]  # dnspython3 for SRV records

if not PY35_OR_GREATER:
    deps += ['typing', ]  # backward compatibility for 3.3 and 3.4


# Extra dependencies for a development environment.
# if 'develop' in sys.argv: <- we cannot do that as pip is doing that in 2 steps.
# TODO(gbin): find another way to filter those out if we don't need them.

deps += ['mock',
         'pep8',
         'flaky',
         # Order matters here, pytest must come last. See also:
         #   https://github.com/errbotio/errbot/pull/496
         #   https://bitbucket.org/pypa/setuptools/issues/196/tests_require-pytest-pytest-cov-breaks
         'pytest-xdist',
         'pytest',
         'PyOpenSSL',
         'docutils',  # for rst linting for pypi.
         ]

if not ON_WINDOWS:
    deps += ['daemonize']

src_root = os.curdir
sys.path.insert(0, os.path.join(src_root, 'errbot'))  # hack to avoid loading err machinery from the errbot package


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


if __name__ == "__main__":
    from version import VERSION

    args = set(sys.argv)

    changes = read('CHANGES.rst')

    if changes.find(VERSION) == -1:
        raise Exception('You forgot to put a release note in CHANGES.rst ?!')

    if args & {'bdist', 'bdist_dumb', 'bdist_rpm', 'bdist_wininst', 'bdist_msi'}:
        raise Exception("err doesn't support binary distributions")

    # under python2 if we want to make a source distribution,
    # don't pre-convert the sources, leave them as py3.
    if PY2 and args & {'install', 'develop', 'bdist_wheel'}:
        from py2conv import convert_to_python2
        convert_to_python2()

    setup(
        name="errbot",
        version=VERSION,
        packages=find_packages(src_root, exclude=['tests', 'tests.*', 'tools']),
        entry_points={
            'console_scripts': [
                'errbot = errbot.err:main',
                'err.py = errbot.err:main'
            ]
        },

        install_requires=deps,
        tests_require=['nose', 'webtest', 'requests'],
        package_data={
            '': ['*.txt', '*.rst', '*.plug', '*.md'],
        },
        extras_require={
            'graphic':  ['PySide', ],
            'hipchat': ['hypchat', 'sleekxmpp', 'pyasn1', 'pyasn1-modules'],
            'IRC': ['irc', ],
            'slack': ['slackclient>=1.0.0', ],
            'telegram': ['python-telegram-bot', ],
            'XMPP': ['sleekxmpp', 'pyasn1', 'pyasn1-modules'],
        },

        author="errbot.io",
        author_email="info@errbot.io",
        description="Errbot is a chatbot designed to be simple to extend with plugins written in Python.",
        long_description=''.join([read('README.rst'), '\n\n', changes]),
        license="GPL",
        keywords="xmpp irc slack hipchat gitter tox chatbot bot plugin chatops",
        url="http://errbot.io/",
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
            "Programming Language :: Python :: 3.5",
        ],
        src_root=src_root,
        platforms='any',
    )

# restore the paths
sys.path.remove(os.path.join(src_root, 'errbot'))
