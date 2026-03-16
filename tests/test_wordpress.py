"""Tests for WordPress adapter (core and plugins)."""

import os

from packaging import version

from lastversion.lastversion import latest

# change dir to tests directory to make relative paths possible
os.chdir(os.path.dirname(os.path.realpath(__file__)))


def test_wordpress_core_latest():
    """Test that 'wordpress' returns the actual latest core version."""
    v = latest("wordpress")
    assert v >= version.parse("6.9.4")


def test_wordpress_plugin():
    """Test that plugin lookup still works."""
    v = latest("https://wordpress.org/plugins/akismet/")
    assert v >= version.parse("5.0")
