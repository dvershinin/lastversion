from packaging import version

from lastversion.lastversion import latest


def test_ndk():
    """Test a GitHub project."""
    repo = "https://github.com/lastversion-test-repos/ngx_devel_kit"

    output = latest(repo)

    assert output == version.parse("0.3.2")
