#!/usr/bin/env python
"""
lastversion
==========
.. code:: shell
  $ lastversion wp-cli/wp-cli
  $ lastversion apache/incubator-pagespeed-ngx
"""

from setuptools import find_packages, setup
from io import open
import os
import re

_version_re = re.compile(r"__version__\s=\s'(.*)'")

# require at least requests==2.6.1 due to cachecontrol's bug:
# https://github.com/ionrock/cachecontrol/issues/137
# feedparser 6 dropped Python 2 support
install_requires = ['requests>=2.6.1', 'packaging', 'cachecontrol', 'lockfile', 'appdirs',
                    'feedparser <= 5.2.1; python_version < "3.0.0"',
                    'feedparser; python_version >= "3.0.0"',
                    'python-dateutil', 'PyYAML', 'tqdm',
                    'six', 'beautifulsoup4',
                    'distro']
tests_requires = [
    "pytest>=4.4.0",
    "flake8",
    # somehow getting this issue only in Travis, anyway this should fix:
    # https://github.com/pytest-dev/pytest/issues/6887#issuecomment-600979770
    "pytest-xdist==1.29.0"
]

docs_requires = [
    "mkdocs==1.2.1",
    "mkdocs-material",
    "mkdocstrings",
    "markdown-include"
]

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

base_dir = os.path.dirname(__file__)

with open(os.path.join(base_dir, "lastversion", "__about__.py"), 'r') as f:
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
    packages=find_packages(exclude=["tests", "docs"]),
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
        "Topic :: Utilities"
    ],
)
