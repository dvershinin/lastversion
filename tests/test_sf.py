import os

from packaging import version

from lastversion.lastversion import latest
from lastversion.repo_holders.sourceforge import SourceForgeRepoSession

# change dir to tests directory to make relative paths possible
os.chdir(os.path.dirname(os.path.realpath(__file__)))


def test_sf_default_hostname_with_short_name():
    """Regression for #243: `--at sf <name>` must default hostname, not None."""
    holder = SourceForgeRepoSession("sevenzip", None)
    assert holder.hostname == "sourceforge.net"
    # URL used by get_latest() must not contain 'None'
    assert holder.repo == "sevenzip"


def test_sf_keepass():
    """Test a SourceForge project."""
    repo = "https://sourceforge.net/projects/keepass"

    v = latest(repo)

    assert v >= version.parse("2.45")
