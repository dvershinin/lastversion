import os

from lastversion import lastversion
from packaging import version

# change dir to tests directory to make relative paths possible
os.chdir(os.path.dirname(os.path.realpath(__file__)))


def test_symfony():
    repo = "https://github.com/symfony/symfony/releases"

    output = lastversion.latest(repo)

    assert version.parse(output) >= version.parse("4.2.8")


def test_ngx_pagespeed():
    repo = "apache/incubator-pagespeed-ngx"

    output = lastversion.latest(repo)

    assert version.parse(output) >= version.parse("1.13.35.2")


def test_wp_cli():
    repo = "wp-cli/wp-cli"

    output = lastversion.latest(repo)

    assert version.parse(output) >= version.parse("2.2.0")


def test_libvmod_xcounter():
    repo = "https://github.com/xcir/libvmod-xcounter"

    output = lastversion.latest(repo)

    assert version.parse(output) >= version.parse("62.3")
