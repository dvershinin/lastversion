"""Test GitHub projects."""

import os
import re
from tempfile import TemporaryDirectory

from packaging import version

from lastversion.cli import main
from lastversion.lastversion import latest
from tests.helpers import captured_exit_code


def test_ndk():
    """Test a GitHub project."""
    repo = "https://github.com/lastversion-test-repos/ngx_devel_kit"

    output = latest(repo)

    assert output == version.parse("0.3.2")


def test_url_decoded():
    """
    Test a GitHub project with URL decoded characters.
    Tags contain '@' sign.
    """
    repo = "https://github.com/lastversion-test-repos/n8n"

    output = latest(repo)

    assert output == version.parse("0.225.1")


def test_high_micro_is_not_beta():
    """
    Test a GitHub project with a micro version number higher than 100,
    which is not a beta version because micro represents a date release
    """
    repo = "https://github.com/lastversion-test-repos/luajit2"

    output = latest(repo)

    assert output == version.parse("2.1")


def test_semver_preferred():
    """
    Test a GitHub project with a semver version number for releases and a
    high version number for pre-releases
    """
    repo = "https://github.com/lastversion-test-repos/kibana"

    output = latest(repo)

    assert output == version.parse("8.10.0")


def test_github_semver_shorthand_preferred():
    """Test a project with a shorthand semver version number for releases."""
    repo = "https://github.com/lastversion-test-repos/cgal"

    output = latest(repo)

    assert output == version.parse("5.6")


def test_github_extract_wordpress():
    """
    Test extracting a GitHub WordPress project into the current directory.
    Once extracted, `index.php` should be in the current directory
    """
    repo = "https://github.com/lastversion-test-repos/WordPress"
    with captured_exit_code():
        # switch to temporary directory
        with TemporaryDirectory() as tmp_dir:
            os.chdir(tmp_dir)
            main(["extract", repo])
            assert os.path.exists("index.php")
            assert os.path.exists("wp-config-sample.php")


def test_github_search_python():
    """Test searching a GitHub project."""
    repo = "python"
    output = latest(repo)
    assert output > version.parse("3.11")


def test_github_formal_filter():
    """Test filtering a GitHub project and only formal releases."""
    repo = "https://github.com/lastversion-test-repos/cadvisor"
    output = latest(repo, formal=True)
    assert output == version.parse("0.48.0")


def test_github_not_formal_filter():
    """Test filtering a GitHub project and only formal releases."""
    repo = "https://github.com/lastversion-test-repos/cadvisor"
    output = latest(repo, formal=False)
    assert output == version.parse("0.48.1")


def test_github_pre_in_front_is_not_stable():
    """Test a GitHub project with a pre-release version."""
    repo = "https://github.com/lastversion-test-repos/tailscale"
    output = latest(repo)
    assert output == version.parse("1.62.0")


def test_github_tag_name_prefixed():
    """Test a GitHub project with a tag name prefixed with repo name and digit."""
    repo = "https://github.com/lastversion-test-repos/hdf5"
    output = latest(repo)
    assert output == version.parse("1.14.4.3")


def test_github_nginx_source_url():
    """Test NGINX."""
    repo = "https://nginx.org/"

    result = latest(repo, "source", major="1.18.0")

    assert result == "https://nginx.org/download/nginx-1.18.0.tar.gz"


def test_github_temurin8_latest_tag():
    """Test Adoptium Temurin 8 latest tag."""
    repo = "https://github.com/adoptium/temurin8-binaries"
    output = latest(repo, output_format="tag")
    # Tag should follow update-style format like jdk8u472-b08 and move forward over time
    assert re.match(r"^jdk8u\d+-b\d+$", output)
    m = re.match(r"^jdk8u(\d+)-b(\d+)$", output)
    assert m is not None
    update_num = int(m.group(1))
    assert update_num >= 462
