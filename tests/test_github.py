from packaging import version

from lastversion.lastversion import latest


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
