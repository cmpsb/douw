# -*- coding: utf-8 -*-
import os
from setuptools import setup, find_packages

ver_globals = {}
with open(os.path.join('douw', 'version.py'), 'rt') as version_file:
    exec(version_file.read(), ver_globals)

try:
    long_description = open("README.rst.rst").read()
except IOError:
    long_description = ""

setup(
    name="douw",
    version=ver_globals['__version__'],
    description="Drop-in website deployment",
    url='https://git.wukl.net/wukl/douw',
    license="MIT",
    author="Luc Everse",
    author_email='luc@wukl.net',
    packages=find_packages(),
    install_requires=[],
    tests_require=[
        'pytest',
        'pycodestyle'
    ],
    python_requires='>=3.8',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    scripts=['bin/douw'],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: POSIX",
        "Topic :: Internet :: WWW/HTTP :: Site Management"
    ]
)
