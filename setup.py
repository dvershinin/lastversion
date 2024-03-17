#!/usr/bin/env python
"""
lastversion
==========
.. code:: shell
  $ lastversion wp-cli/wp-cli
  $ lastversion apache/incubator-pagespeed-ngx
"""

import io
import os
import re
from setuptools import find_packages, setup


_version_re = re.compile(r"__version__\s=\s\"(.*)\"")


install_requires = [
    # require at least requests==2.6.1 due to cachecontrol's bug:
    # https://github.com/ionrock/cachecontrol/issues/137
    "requests>=2.6.1",
    "packaging",
    # Cachecontrol 0.12.12 uses filelock instead of lockfile, and reverts to lockfile in 0.12.14.
    # Newer versions use filelock, but most distros package cachecontrol 0.12.11.
    # Ideally we can specify 0.12.14, but pip doesn't allow this, so just pin to what we can
    "cachecontrol<=0.12.11",
    "lockfile",
    "appdirs",
    "feedparser",
    "python-dateutil",
    "PyYAML",
    "tqdm",
    "beautifulsoup4",
    "distro",
    # pin due to https://github.com/ionrock/cachecontrol/issues/292
    "urllib3 < 2",
]
tests_requires = [
    "pytest>=4.4.0",
    "flake8",
    "flake8-bugbear",
    "pytest-xdist",
    "pytest-cov",
]

docs_requires = [
    "mkdocs==1.5.3",
    "mkdocs-material==9.5.3",
    "mkdocstrings[python]",
    "markdown-include"
]

with io.open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

base_dir = os.path.join(os.path.dirname(__file__), "src")

with open(os.path.join(base_dir, "lastversion", "__about__.py"), "r", encoding="utf-8") as f:
    version = _version_re.search(f.read()).group(1)

setup(
    name="lastversion",
    version=version,
    author="Danila Vershinin",
    author_email="info@getpagespeed.com",
    url="https://github.com/dvershinin/lastversion",
    description="A CLI tool to find the latest stable version of an arbitrary project",
    long_description=long_description,
    long_description_content_type="text/markdown",
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    zip_safe=False,
    license="BSD",
    install_requires=install_requires,
    extras_require={
        "tests": install_requires + tests_requires,
        "docs": docs_requires,
        "build": install_requires + tests_requires + docs_requires,
    },
    tests_require=tests_requires,
    include_package_data=True,
    entry_points={"console_scripts": ["lastversion = lastversion:main"]},
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Operating System :: OS Independent",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Version Control",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
        "Environment :: Console",
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires='>=3.6',
    keywords="version, release, latest, stable, pypi, github, gitlab, bitbucket, mercurial, hg, wordpress"
)
