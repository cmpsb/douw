# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

try:
    long_description = open("README.rst.rst").read()
except IOError:
    long_description = ""

setup(
    name="douw",
    version="0.3.0",
    description="Drop-in website deployment",
    url='https://git.wukl.net/wukl/douw',
    license="MIT",
    author="Luc Everse",
    author_email='luc@wukl.net',
    packages=find_packages(),
    install_requires=[],
    tests_require=[
        'pytest',
        'pytest-pep8'
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
