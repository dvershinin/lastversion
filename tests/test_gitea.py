import os

from packaging import version

from lastversion.lastversion import latest

# change dir to tests directory to make relative paths possible
os.chdir(os.path.dirname(os.path.realpath(__file__)))


def test_gitea_tags():
    """Simple Gitea test"""
    repo = "https://gitea.com/lastversion-test-repos/tea/tags"
    v = latest(repo)
    assert v == version.parse("0.8.0")


def test_codeberg_repo():
    """Test Codeberg support (Codeberg is a Gitea instance)"""
    repo = "https://codeberg.org/forgejo/forgejo"
    v = latest(repo)
    # Forgejo should have versions, just check it's valid
    assert v is not None
    assert isinstance(v, version.Version)
