import os

from packaging import version

from lastversion.lastversion import latest

# change dir to tests directory to make relative paths possible
os.chdir(os.path.dirname(os.path.realpath(__file__)))


def test_sf_keepass():
    """Test a SourceForge project."""
    repo = "https://sourceforge.net/projects/keepass"

    v = latest(repo)

    assert v >= version.parse("2.45")
