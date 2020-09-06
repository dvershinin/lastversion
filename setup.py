#!/usr/bin/env python
"""
lastversion
==========
.. code:: shell
  $ lastversion wp-cli/wp-cli
  $ lastversion apache/incubator-pagespeed-ngx
"""

from setuptools import find_packages, setup
import os
import re

_version_re = re.compile(r"__version__\s=\s'(.*)'")

# require at least requests==2.6.1 due to cachecontrol's bug:
# https://github.com/ionrock/cachecontrol/issues/137
install_requires = ['requests>=2.6.1', 'packaging', 'cachecontrol', 'lockfile', 'appdirs',
                    'python-dateutil', 'feedparser', 'PyYAML', 'tqdm',
                    'six', 'beautifulsoup4']
tests_requires = ["pytest>=4.4.0", "flake8", "pytest-xdist"]

with open("README.md", "r") as fh:
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
    description="A CLI tool to fetch last GitHub release version",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests"]),
    zip_safe=False,
    license="BSD",
    install_requires=install_requires,
    extras_require={
        "tests": install_requires + tests_requires,
    },
    tests_require=tests_requires,
    include_package_data=True,
    entry_points={"console_scripts": ["lastversion = lastversion:main"]},
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Operating System :: OS Independent",
        "Topic :: Software Development",
    ],
)
