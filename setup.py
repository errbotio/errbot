#!/usr/bin/env python2

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
import sys

py_version = sys.version_info[:2]
PY3 = py_version[0] == 3

if PY3:
    deps = ['setuptools', 'sleekxmpp', 'yapsy', 'bottle', 'jinja2']
    if py_version < (3, 2):
        raise RuntimeError(
            'On Python 3, Err requires Python 3.2 or later')
else:
    deps = ['configparser', 'setuptools', 'sleekxmpp', 'dnspython', 'yapsy', 'python-daemon', 'config', 'bottle', 'jinja2']
    if py_version < (2, 7):
        raise RuntimeError(
            'On Python 2, Err requires Python 2.7 or later')

py2_root = os.path.abspath(os.path.join("build", "py2_src"))
src_dirs = ("errbot", "scripts", "tests")

def all_files_in_rep(rootfolder, extension=".py"):
    return (os.path.join(dirname, filename)
            for dirname, dirnames, filenames in os.walk(rootfolder)
            for filename in filenames
            if filename.endswith(extension))


def newest_file_in_tree(rootfolder, extension=".py"):
    return max(all_files_in_rep(rootfolder, extension),
               key=lambda fn: os.stat(fn).st_mtime)


def oldest_file_in_tree(rootfolder, extension=".py"):
    return min(all_files_in_rep(rootfolder, extension),
               key=lambda fn: os.stat(fn).st_mtime)


def need_to_regenerate():
    for d in src_dirs:
        oldest_file = oldest_file_in_tree(os.path.join(py2_root, d))
        newest_file = newest_file_in_tree(d)
        oldest = os.stat(oldest_file).st_mtime
        newest = os.stat(newest_file).st_mtime
        print('dir ' + d)
        print('oldest ' + oldest_file + ': ' + str(oldest))
        print('newest ' + newest_file + ': ' + str(newest))
        if newest > oldest:
            return True
    return False

def setup_python2():
    from pip import main as mainpip
    mainpip(['install', '3to2'])
    from lib3to2 import main as three2two
    import shutil
    import shlex

    try:
        regenerate = need_to_regenerate()
    except Exception as _:
        regenerate = True  # we need to do it if the dir doesn't exist

    if regenerate:
        for d in src_dirs:
            tmp_src = os.path.join(py2_root, d)
            try:
                shutil.rmtree(tmp_src)
            except OSError:
                pass  # ignore if the directory doesn't exist.

            shutil.copytree(d, tmp_src)
            for fname in all_files_in_rep(tmp_src):
                os.utime(fname, None)

        three2two.main("lib3to2.fixes", shlex.split("-w {0}".format(py2_root)))
    else:
        print('Sources already uptodate for python 2')

    return py2_root


if PY3:
    src_root = os.curdir
else:
    src_root = setup_python2()
    sys.path.insert(0, src_root)

sys.path.insert(0, src_root + os.path.sep + 'errbot')  # hack to avoid loading err machinery from the errbot package


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


if __name__ == "__main__":
    from version import VERSION

    changes = read('CHANGES.rst')

    if changes.find(VERSION) == -1:
        raise Exception('You forgot to put a release note in CHANGES.rst ?!')

    setup(
        name="err",
        version=VERSION,
        packages=find_packages(src_root),
        scripts=['scripts/err.py'],

        install_requires=deps,

        package_data={
            '': ['*.txt', '*.rst', '*.plug', '*.html', '*.js', '*.css'],
        },

        author="Guillaume BINET",
        author_email="gbin@gootz.net",
        description="err is a plugin based team chatbot designed to be easily deployable, extensible and maintainable.",
        long_description=''.join([read('README.rst'), '\n\n', changes]),
        license="GPL",
        keywords="xmpp jabber chatbot bot plugin",
        url="http://gbin.github.com/err/",
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Topic :: Communications :: Chat",
            "Topic :: Communications :: Conferencing",
            "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.2",
        ],
        src_root=src_root,
    )

# restore the paths
sys.path.remove(src_root + os.path.sep + 'errbot')
