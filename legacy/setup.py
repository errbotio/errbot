#!/usr/bin/env python
from setuptools import setup

setup(
    name="err",
    version='3.2.0',
    install_requires=['errbot'],
    author="errbot.io",
    author_email="info@errbot.io",
    description="Errbot is a chatbot designed to be simple to extend with plugins written in Python.",
    long_description='LEGACY: please install the package called "errbot" instead.',
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
    platforms='any',
)
