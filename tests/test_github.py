"""Test GitHub projects."""
import os
from tempfile import TemporaryDirectory

from packaging import version

from lastversion import main
from lastversion.lastversion import latest
from .helpers import captured_exit_code


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

    assert output == version.parse("2.1.20230410")


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
