import os

from packaging import version

from lastversion.lastversion import latest

# change dir to tests directory to make relative paths possible
os.chdir(os.path.dirname(os.path.realpath(__file__)))


def test_gitlab_1():
    """Test specifying a deep-level link at GitLab."""
    repo = "https://gitlab.com/ddcci-driver-linux/ddcci-driver-linux/-/tree/master"

    v = latest(repo)

    assert v >= version.parse("0.4.1")


def test_gitlab_format_json():
    """Test specifying a deep-level link at GitLab."""
    repo = "https://gitlab.com/ddcci-driver-linux/ddcci-driver-linux/-/tree/master"

    v = latest(repo, output_format="dict")

    assert "tag_date" in v and v["tag_date"].day == 20


def test_gitlab_at():
    """Test specifying GitLab repo with an --at parameter."""
    repo = "ddcci-driver-linux/ddcci-driver-linux"

    v = latest(repo, at="gitlab")

    assert v >= version.parse("0.4.1")
