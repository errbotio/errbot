#!/usr/bin/python

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
from setuptools import setup, find_packages
from errbot.version import VERSION
def read(fname):
        return open(os.path.join(os.path.dirname(__file__), fname)).read()

changes = read('CHANGES.rst')

if changes.find(VERSION) == -1:
    raise Exception('You forgot to put a release note in CHANGES.rst ?!')

setup(
    name = "err",
    version = VERSION,
    packages = find_packages(),
    scripts = ['scripts/err.py'],

    install_requires = ['setuptools', 'xmpppy', 'dnspython', 'yapsy', 'python-daemon', 'jinja2'],

    package_data = {
        '': ['*.txt', '*.rst', '*.plug', '*.html'],
    },

    author = "Guillaume BINET",
    author_email = "gbin@gootz.net",
    description = "err is a plugin based XMPP chatbot designed to be easily deployable, extensible and maintainable.",
    long_description=''.join([read('README.rst'),'\n\n',changes]),
    license = "GPL",
    keywords = "xmpp jabber chatbot bot plugin",
    url = "http://gbin.github.com/err/",
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Topic :: Communications :: Chat",
        "Topic :: Communications :: Conferencing",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
    ],
    )
