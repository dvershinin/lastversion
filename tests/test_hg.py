"""Test Mercurial repositories."""

import os

from packaging import version

from lastversion.lastversion import latest

# change dir to tests directory to make relative paths possible
os.chdir(os.path.dirname(os.path.realpath(__file__)))


def test_hg_nginx():
    """Test NGINX."""
    repo = "https://nginx.org/"

    output = latest(repo, "version")

    assert output >= version.parse("1.18.0")
