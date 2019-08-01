import os

from lastversion import lastversion
from packaging import version

# change dir to tests directory to make relative paths possible
os.chdir(os.path.dirname(os.path.realpath(__file__)))


def test_tdesktop():
    repo = "https://github.com/telegramdesktop/tdesktop/releases"

    output = lastversion.latest(repo, 'version', False)

    assert version.parse(output) == version.parse("1.7.14")


def test_mautic_pre():
    repo = "mautic/mautic"

    output = lastversion.latest(repo, 'version', True)

    assert version.parse(output) == version.parse("2.15.2")


def test_monit():
    repo = "https://mmonit.com/"

    output = lastversion.latest(repo, 'version')

    assert output > version.parse("5.25.0")


def test_gperftools():
    repo = "https://github.com/gperftools/gperftools/releases"

    output = lastversion.latest(repo)

    assert version.parse(output) >= version.parse("2.7")


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


def test_datadog_agent():
    repo = "DataDog/datadog-agent"

    output = lastversion.latest(repo)

    assert version.parse(output) >= version.parse("6.11.3")


def test_grafana():
    repo = "grafana/grafana"

    output = lastversion.latest(repo)

    assert version.parse(output) >= version.parse("6.2.2")


def test_roer():
    repo = "spinnaker/roer"

    output = lastversion.latest(repo)

    assert version.parse(output) >= version.parse("0.11.3")


def test_ndk():
    repo = "https://github.com/simplresty/ngx_devel_kit"

    output = lastversion.latest(repo)

    assert version.parse(output) <= version.parse("0.3.0")


def test_naxsi():
    repo = "https://github.com/nbs-system/naxsi/releases"

    output = lastversion.latest(repo)

    assert version.parse(output) <= version.parse("0.56")


def test_brotli():
    repo = "https://github.com/eustas/ngx_brotli/releases"

    output = lastversion.latest(repo)

    assert version.parse(output) == version.parse("0.1.2")
