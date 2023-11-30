"""WikiPedia Repo Session."""

import logging

from bs4 import BeautifulSoup
from dateutil import parser

from .ProjectHolder import ProjectHolder

log = logging.getLogger(__name__)


def remove_words(title):
    """Remove words from a title that are not part of the version."""
    parts = title.split(" ")
    parts_n = []
    for part in parts:
        if not part.isalpha() or ".post" in part:
            parts_n.append(part)
    return " ".join(parts_n)


class WikipediaRepoSession(ProjectHolder):
    """Wikipedia repo session."""

    KNOWN_REPOS_BY_NAME = {
        "alpine": {
            "repo": "Alpine_Linux",
        },
        "rocky": {
            "repo": "Rocky_Linux",
        },
        "rockylinux": {
            "repo": "Rocky_Linux",
        },
        "fedora": {"repo": "Fedora_(operating_system)"},
        "rhel": {"repo": "Red_Hat_Enterprise_Linux"},
        "redhat": {"repo": "Red_Hat_Enterprise_Linux"},
        "almalinux": {"repo": "AlmaLinux"},
        "ios": {"repo": "IOS"},
        "ubuntu": {"repo": "Ubuntu"},
        "debian": {"repo": "Debian"},
        "android": {"repo": "Android_(operating_system)"},
        "windows": {"repo": "Microsoft_Windows"},
        "osx": {"repo": "MacOS"},
        "sles": {"repo": "SUSE_Linux_Enterprise"},
        "opensuse": {"repo": "OpenSUSE"},
    }

    REPO_URL_PROJECT_COMPONENTS = 1
    DEFAULT_HOSTNAME = "en.wikipedia.org"
    # For project URLs, e.g. https://en.wikipedia.org/wiki/Rocky_Linux
    # a URI does not start with a repo name, skip '/wiki/'
    REPO_URL_PROJECT_OFFSET = 1

    def __init__(self, repo, hostname):
        super(WikipediaRepoSession, self).__init__(repo, hostname)
        self.hostname = hostname
        if not self.hostname:
            self.hostname = self.DEFAULT_HOSTNAME

    def get_latest(self, pre_ok=False, major=None):
        """Get the latest release."""
        tag_name = None
        tag = {}
        r = self.get(f"https://{self.hostname}/wiki/{self.repo}")
        soup = BeautifulSoup(r.text, "html.parser")
        # we only need the first one
        infobox = soup.select_one(".infobox")
        links = infobox.select("a")
        for link in links:
            if link.text.lower() in ["latest release", "stable release"]:
                release_data = link.parent.parent.select_one(".infobox-data")
                # get published before it's removed:
                published_span = release_data.select_one("span.published")
                if published_span:
                    tag["tag_date"] = parser.parse(published_span.text)
                for t in release_data.select("sup, span"):
                    t.decompose()
                tag_name = release_data.text
                tag_name = tag_name.replace(" Service Pack ", ".post")
                # remove alphas from beginning
                tag_name = remove_words(tag_name).split("/", maxsplit=1)[0]
                # Remove unicode stuff (for Python 2)
                tag["title"] = release_data.text.encode("ascii", "ignore").decode()
                log.info("Pre-parsed title: %s", tag["title"])
                break
        if not tag_name:
            return None
        # Remove unicode stuff (for Python 2)
        tag_name = tag_name.encode("ascii", "ignore").decode()
        version = self.sanitize_version(tag_name, pre_ok, major)
        if version:
            tag["tag_name"] = tag_name
            tag["version"] = version
            return tag
        return None
