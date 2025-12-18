"""Test lastversion."""

import os
import subprocess

import pytest
from packaging import version

from lastversion.exceptions import BadProjectError
from lastversion.lastversion import latest
from lastversion.repo_holders.test import TestProjectHolder
from lastversion.version import Version

# change dir to tests directory to make relative paths possible
os.chdir(os.path.dirname(os.path.realpath(__file__)))


def test_tdesktop():
    """Test Telegram Desktop at GitHub."""
    repo = "https://github.com/telegramdesktop/tdesktop/releases"

    output = latest(repo, "version", False)

    assert output >= version.parse("1.8.1")


def test_mautic_pre():
    """Test Mautic."""
    repo = "https://github.com/lastversion-test-repos/mautic"

    output = latest(repo, "version", True)

    assert str(output) == "5.0.0a1"


def test_monit():
    """Test Monit."""
    repo = "https://mmonit.com/monit/dist/monit-5.26.0.tar.gz"

    output = latest(repo, "version")

    assert output > version.parse("5.25.0")


def test_gperftools():
    """Test gperftools."""
    repo = "https://github.com/gperftools/gperftools/releases"

    output = latest(repo)

    assert output >= version.parse("2.7")


def test_symfony():
    """Test Symfony."""
    repo = "https://github.com/symfony/symfony/releases"

    output = latest(repo)

    assert output >= version.parse("4.2.8")


def test_ngx_pagespeed():
    """Test ngx_pagespeed."""
    repo = "apache/incubator-pagespeed-ngx"

    output = latest(repo, output_format="version")

    assert output >= version.parse("1.13.35.2")


def test_wp_cli():
    """Test WP-CLI."""
    repo = "wp-cli/wp-cli"

    output = latest(repo)

    assert output >= version.parse("2.2.0")


def test_libvmod_xcounter():
    """Test GitHub libvmod-xcounter."""
    repo = "https://github.com/xcir/libvmod-xcounter"

    output = latest(repo)

    assert output >= version.parse("62.3")


def test_only_flag_quictls():
    """Test only filtering at GitHub."""
    repo = "https://github.com/lastversion-test-repos/openssl"

    # Example of a multiple project repo, look for Data Cluster Agent only
    output = latest(repo, only="quic1")

    assert output == version.parse("3.1.2")


def test_grafana():
    """Test Grafana at GitHub."""
    repo = "grafana/grafana"

    output = latest(repo, exclude="lib")

    assert output >= version.parse("6.2.2")


def test_roer():
    """Test a GitHub project."""
    repo = "spinnaker/roer"

    output = latest(repo)

    assert output >= version.parse("0.11.3")


def test_naxsi():
    """Test a GitHub project."""
    repo = "https://github.com/nbs-system/naxsi/releases"

    output = latest(repo)

    assert output >= version.parse("1.1")


def test_brotli():
    """Test ngx_brotli GitHub project."""
    repo = "https://github.com/eustas/ngx_brotli/releases"

    output = latest(repo)

    assert output == version.parse("0.1.2")


def test_changed_format():
    """
    Test a repo which changed the tag format from v20150121 to v2.0.1.
    Disregard "higher" number by checking that v20150121 release is too old.
    """
    repo = "https://github.com/lastversion-test-repos/nginx-http-shibboleth/releases"

    output = latest(repo)

    assert output == version.parse("2.0.2")


def test_major():
    """Test major selection."""
    repo = "https://github.com/SpiderLabs/ModSecurity"

    output = latest(repo, major="2.9")

    assert output >= version.parse("2.9.3")


def test_version_parse_with_dot_x():
    """Test version parsing to fail on wildcard type of version string."""
    v = "1.19.x"

    h = TestProjectHolder()

    assert h.sanitize_version(v) is None


def test_version_parse_dev():
    """Test version parsing to detect rc1 type suffix as a pre-release."""
    v = "1.19rc1"

    h = TestProjectHolder()

    v = h.sanitize_version(v, pre_ok=True)

    assert v.is_prerelease is True


def test_version_parse_dev2():
    """Test version parsing to detect -rc.2 type suffix as a pre-release."""
    v = "7.18.1-rc.2"

    h = TestProjectHolder()

    v = h.sanitize_version(v, pre_ok=True)

    assert v.is_prerelease is True


def test_version_parse_dev3():
    """Test parsing stable version leaves pre-release flag false."""
    v = "7.18.1"

    h = TestProjectHolder()

    v = h.sanitize_version(v, pre_ok=True)

    assert v.is_prerelease is False


def test_contain_rpm_related_data():
    """Test that json/dict output contains RPM-related keys."""
    repo = "dvershinin/lastversion"

    v = latest(repo, output_format="json")

    assert v["spec_tag"] == "v%{version}"
    assert v["v_prefix"] is True
    assert v["tag_name"].startswith("v")
    assert v["readme"]["path"] == "README.md"
    assert v["license"]["path"] == "LICENSE"


def test_yml_input():
    """Test passing a yml file as repo argument."""
    repo = os.path.dirname(os.path.abspath(__file__)) + "/geoip2.yml"

    v = latest(repo, output_format="json")

    # should be upstream_version because .yml has "module_of" set
    # rest is repo-specific
    assert v["spec_tag"] == "%{upstream_version}"
    assert v["v_prefix"] is False
    assert not v["tag_name"].startswith("v")
    assert v["readme"]["path"] == "README.md"
    assert v["license"]["path"] == "LICENSE"


def test_magento2_major():
    """Test major selection and returning version."""
    repo = "magento/magento2"

    v = latest(repo, major="2.3.4")

    assert v == version.parse("2.3.4.post2")


def test_magento2_major_tag():
    """Test major selection and returning tag."""
    repo = "magento/magento2"

    v = latest(repo, major="2.3.4", output_format="tag")

    assert v == "2.3.4-p2"


def test_squid_underscore_lover():
    """Test a repo with tags like SQUID_5_0_1."""
    repo = "https://github.com/squid-cache/squid/releases"

    v = latest(repo)

    assert v >= version.parse("5.0.1")


def test_patch_release_for_older_is_not_last():
    """
    Test a repo where a patch for older release is topmost.
    Aggregating versions should return newer release instead of patched release.
    """
    repo = "https://github.com/lastversion-test-repos/magento2/releases"

    v = latest(repo)

    assert v == version.parse("2.4.0")


def test_with_search():
    """Test using GitHub search API by specifying one word in repo."""
    repo = "telize"

    v = latest(repo)

    assert v >= version.parse("3.0.0")


def test_homepage_github_link_discovery():
    """Test with discovering GitHub repo from project own website."""
    repo = "https://transmissionbt.com/"

    v = latest(repo)

    assert v >= version.parse("3.0")


def test_homepage_feed_discovery():
    """Test with a project through website feed discovery."""
    repo = "https://filezilla-project.org/"

    v = latest(repo, only="FileZilla Client")

    assert v >= version.parse("3.50.0")


def test_main_url():
    """Test CLI with full URL at GitHub."""
    repo = "https://github.com/apache/incubator-pagespeed-ngx"

    with subprocess.Popen(["lastversion", repo], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        out, _ = process.communicate()

        assert version.parse(out.decode("utf-8").strip()) >= version.parse("1.13.35.2")


def test_cli_format_with_sem_base():
    """Test formatting arbitrary version string with semantic level extraction."""
    repo = "mysqld  Ver 5.6.51-91.0 for Linux on x86_64 (Percona Server (GPL), Release 91.0, Revision b59139e)"

    with subprocess.Popen(
        ["lastversion", "--sem", "major", "format", repo],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        out, _ = process.communicate()

        assert out.decode("utf-8").strip() == "5"


def test_cli_get_tag():
    """Test CLI with full URL at GitHub, get tag as a result."""
    repo = "https://github.com/lastversion-test-repos/Tasmota"

    with subprocess.Popen(
        ["lastversion", repo, "--format", "tag"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        out, _ = process.communicate()

        assert out.decode("utf-8").strip() == "v11.0.0"


def test_main_assets():
    """Test CLI with --format assets."""
    repo = "https://github.com/mautic/mautic"

    with subprocess.Popen(
        ["lastversion", repo, "--format", "assets", "--major", "4.4.11"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        out, _ = process.communicate()

        assert "4.4.11-update.zip" in str(out)


def test_tag_mess():
    """Test repository with tags like Rhino1_7_13_Release."""
    repo = "lastversion-test-repos/rhino"
    v = latest(repo)

    assert v == version.parse("1.7.13")


def test_dict_output():
    """Test dict output."""
    repo = "SiliconLabs/uC-OS2"
    v = latest(repo, output_format="dict")

    assert v["version"] >= version.parse("2.93.0")


def test_major_graphql():
    """Test deep major select using graphql."""
    repo = "php/php-src"
    v = latest(repo, major="5.6")

    assert v == version.parse("5.6.40")


def test_raises_bad_project_error_while_graphql():
    """
    Test getting BadProjectError while in graphql.
    When a bad project is passed as owner/name, we don't fail on 404 while getting `releases.atom`
    as we're still hoping to get something with graphql.
    So graphql response should be checked and BadProjectError raised so that we can communicate
    that the repo argument passed was invalid.
    """
    with pytest.raises(BadProjectError):
        repo = "SiliconLabs/uC-OS"
        latest(repo)


def test_rc_detection_anywhere():
    """Test rc indicator detected in middle too."""
    tag = "v5.12-rc1-dontuse"
    v = Version(tag)
    assert v == version.parse("5.12.rc1")


def test_patch_detection_anywhere():
    """Test patch/post detection in middle."""
    tag = "blah-2.3.4-p2-ok"
    v = Version(tag)
    assert v == version.parse("2.3.4.post2")


def test_last_b_is_beta():
    """Test trailing beta status detection."""
    tag = "1.1.1b"
    v = Version(tag)
    assert v == version.parse("1.1.1b")
    assert v.is_prerelease


def test_last_b_belongs_to_version():
    """
    Test no beta flag if desired by specific repos scheme.
    This fix is required for OpenSSL-like repos, are there any other? Probably not.
    """
    tag = "1.1.1b"
    v = Version(tag, char_fix_required=True)
    assert str(v) == "1.1.1b"
    assert not v.is_prerelease


def test_char_yml_direct():
    """Test URL with Chart.yaml."""
    repo = "https://github.com/bitnami/charts/blob/master/bitnami/aspnet-core/Chart.yaml"
    v = latest(repo)
    assert v >= version.parse("1.0.0")


def test_char_yml_indirect_hint():
    """Test URL with Chart.yaml"""
    repo = "https://github.com/bitnami/charts/blob/master/bitnami/aspnet-core"
    v = latest(repo, at="helm_chart")
    assert v >= version.parse("1.0.0")


def test_at_with_url_github():
    """Test direct URL spec with --at."""
    repo = "https://github.com/dvershinin/lastversion"
    v = latest(repo, at="github")
    assert v >= version.parse("1.3.4")


def test_having_specific_asset():
    """Test locating release with a given asset name."""
    repo = "https://github.com/lastversion-test-repos/portainer"
    v = latest(repo, having_asset="portainer-2.6.1-linux-amd64.tar.gz")
    assert v == version.parse("2.6.1")


def test_having_any_asset():
    """Test locating release with a given asset name."""
    repo = "https://github.com/lastversion-test-repos/portainer"
    v = latest(repo, having_asset=True)
    assert v == version.parse("2.6.3")


def test_tags_only_repo():
    """A repo may never publish a formal release which results
    in a completely empty releases atom without any formal and non-formal tags
    See #63"""
    repo = "https://github.com/lastversion-test-repos/cpython"
    v = latest(repo)
    assert v == version.parse("3.10.0")


def test_only_arg_again():
    """Test only arg with chart."""
    repo = "https://github.com/lastversion-test-repos/autoscaler/tags"
    v = latest(repo, only="chart")
    assert v == version.parse("9.16.0")


def test_only_arg_negated():
    """Test only arg with negation."""
    repo = "https://github.com/lastversion-test-repos/autoscaler/tags"
    v = latest(repo, only="!chart")
    assert v == version.parse("1.23.0")


def test_dict_no_license():
    """Test dict output without license."""
    repo = "https://github.com/lastversion-test-repos/nginx_ajp_module"
    release = latest(repo, output_format="dict")
    assert release["version"] == version.parse("0.3.2")
