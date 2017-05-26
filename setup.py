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
PY35_OR_GREATER = py_version >= (3, 5)

ON_WINDOWS = system() == 'Windows'

if py_version < (3, 3):
    raise RuntimeError('Errbot requires Python 3.3 or later')

VERSION_FILE = os.path.join('errbot', 'version.py')

deps = ['webtest',
        'setuptools',
        'bottle',
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
        'dnspython3',
        ]

if not PY35_OR_GREATER:
    deps += ['typing', ]  # backward compatibility for 3.3 and 3.4


if not ON_WINDOWS:
    deps += ['daemonize']

src_root = os.curdir


def read_version():
    """
    Read directly the errbot/version.py and gives the version without loading Errbot.
    :return: errbot.version.VERSION
    """

    variables = {}
    with open(VERSION_FILE) as f:
        exec(compile(f.read(), 'version.py', 'exec'), variables)
    return variables['VERSION']


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


if __name__ == "__main__":

    VERSION = read_version()

    args = set(sys.argv)

    open('CHANGES.rst', 'r', encoding='utf-8') as changes_file:
        changes = changes_file.read()
    changes_file.close()

    if changes.find(VERSION) == -1:
        raise Exception('You forgot to put a release note in CHANGES.rst ?!')

    if args & {'bdist', 'bdist_dumb', 'bdist_rpm', 'bdist_wininst', 'bdist_msi'}:
        raise Exception("err doesn't support binary distributions")

    packages = find_packages(src_root, include=['errbot', 'errbot.*'])

    setup(
        name="errbot",
        version=VERSION,
        packages=packages,
        entry_points={
            'console_scripts': [
                'errbot = errbot.cli:main',
            ]
        },

        install_requires=deps,
        tests_require=['nose', 'webtest', 'requests'],
        package_data={
            'errbot': ['backends/*.plug',
                       'backends/*.html',
                       'backends/styles/*.css',
                       'backends/images/*.svg',
                       'core_plugins/*.plug',
                       'core_plugins/*.md',                       
                       'core_plugins/templates/*.md',
                       'storage/*.plug',
                       'templates/initdir/example.py',
                       'templates/initdir/example.plug',
                       'templates/initdir/config.py.tmpl',
                       'templates/*.md',
                       'templates/new_plugin.py.tmpl',
                       ],
        },
        extras_require={
            'graphic':  ['PySide', ],
            'hipchat': ['hypchat', 'sleekxmpp', 'pyasn1', 'pyasn1-modules'],
            'IRC': ['irc', ],
            'slack': ['slackclient>=1.0.5', ],
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
            "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.3",
            "Programming Language :: Python :: 3.4",
            "Programming Language :: Python :: 3.5",
        ],
        src_root=src_root,
        platforms='any',
    )
