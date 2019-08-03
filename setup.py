# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

try:
    long_description = open("README.rst").read()
except IOError:
    long_description = ""

setup(
    name="douw",
    version="0.1.0",
    description="Drop-in website deployment",
    url='https://git.wukl.net/wukl/douw',
    license="MIT",
    author="Luc Everse",
    packages=find_packages(),
    install_requires=[],
    long_description=long_description,
    scripts=['bin/douw'],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: POSIX",
        "Topic :: Internet :: WWW/HTTP :: Site Management"
    ]
)
