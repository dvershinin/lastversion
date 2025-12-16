"""Test Alpine Linux package repository."""

import os

from lastversion.lastversion import latest

# change dir to tests directory to make relative paths possible
os.chdir(os.path.dirname(os.path.realpath(__file__)))


def test_alpine_nginx_at_alpine():
    """Test querying nginx package with --at alpine (main repo)."""
    repo = "nginx"
    v = latest(repo, at="alpine")

    # nginx should return a version like 1.26.3
    assert v is not None
    assert v.major >= 1


def test_alpine_redis_at_alpine():
    """Test querying redis package with --at alpine (community repo)."""
    repo = "redis"
    v = latest(repo, at="alpine")

    # redis should return a version like 7.2.x
    assert v is not None
    assert v.major >= 7


def test_alpine_with_major_version():
    """Test querying package with specific Alpine branch via --major."""
    repo = "nginx"
    # Use a specific Alpine version branch
    v = latest(repo, at="alpine", major="3.21")

    assert v is not None
    assert v.major >= 1


def test_alpine_url_detection():
    """Test URL-based auto-detection for Alpine packages."""
    # Full URL format for pkgs.alpinelinux.org
    url = "https://pkgs.alpinelinux.org/package/v3.21/main/x86_64/nginx"
    v = latest(url)

    assert v is not None
    assert v.major >= 1


def test_alpine_nonexistent_package():
    """Test that non-existent package returns None."""
    repo = "this-package-definitely-does-not-exist-12345"
    v = latest(repo, at="alpine")

    assert v is None
