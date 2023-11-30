import os

from packaging import version

from lastversion.lastversion import latest

# change dir to tests directory to make relative paths possible
os.chdir(os.path.dirname(os.path.realpath(__file__)))


def test_pypi_full_url():
    """Test with full PyPi URL."""
    repo = "https://pypi.org/project/pylockfile/"
    v = latest(repo)

    assert v == version.parse("0.0.3.3")


def test_project_at_pypi():
    """Test project at Pypi with short name."""
    repo = "pylockfile"
    v = latest(repo, at="pip")

    assert v == version.parse("0.0.3.3")
