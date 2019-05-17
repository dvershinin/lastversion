import os

from lastversion import lastversion
from packaging import version

# change dir to tests directory to make relative paths possible
os.chdir(os.path.dirname(os.path.realpath(__file__)))


def test_ngx_pagespeed():
    repo = "apache/incubator-pagespeed-ngx"

    output = lastversion.latest(repo)

    assert version.parse(output) >= version.parse("1.13.35.2")
