import os

from packaging import version

from lastversion.lastversion import latest

# change dir to tests directory to make relative paths possible
os.chdir(os.path.dirname(os.path.realpath(__file__)))


def test_wiki_known_ios():
    """Test iOS version."""
    repo = "ios"
    v = latest(repo)
    assert v >= version.parse("14.6")


def test_wiki_direct_url_meego():
    """Test Meego version."""
    repo = "https://en.wikipedia.org/wiki/MeeGo"
    v = latest(repo)
    assert v == version.parse("1.2.0.10")
