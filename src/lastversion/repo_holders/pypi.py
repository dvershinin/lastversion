"""A module to represent a Pypi project holder."""

import logging

from dateutil import parser

from lastversion.repo_holders.base import BaseProjectHolder
from lastversion.version import Version

log = logging.getLogger(__name__)


class PypiRepoSession(BaseProjectHolder):
    """A class to represent a Pypi project holder."""

    DEFAULT_HOSTNAME = "pypi.org"
    REPO_URL_PROJECT_COMPONENTS = 1
    # For project URLs, e.g. https://pypi.org/project/lastversion/
    # a URI does not start with a repo name, skip '/project/'
    REPO_URL_PROJECT_OFFSET = 1
    CAN_BE_SELF_HOSTED = True

    def get_project(self):
        """Get project JSON data."""
        project = None
        url = f"https://{self.hostname}/pypi/{self.repo}/json"
        log.info("Requesting %s", url)
        r = self.get(url)
        if r.status_code == 200:
            project = r.json()
        return project

    def is_instance(self):
        return self.project

    def __init__(self, repo, hostname=None):
        super().__init__(repo, hostname)
        if hostname:
            self.hostname = hostname
        else:
            self.hostname = PypiRepoSession.DEFAULT_HOSTNAME
        self.project = self.get_project()

    def release_download_url(self, release, shorter=False):
        """Get release download URL."""
        for f in release["files"]:
            if f["packagetype"] == "sdist":
                return f["url"]
        return None

    def get_latest(self, pre_ok=False, major=None):
        """Get the latest project release."""
        ret = self.project
        # we are in "enriching" project dict with desired version information
        # and return None if there's no matching version

        if self.project is None:
            print("Project is not listed on PyPI")
            return None
        if not major:
            latest_ver = self.project["info"]["version"]
            v = Version(latest_ver)
            ret["version"] = v
            # there are no tags, we just put version string there
            ret["tag_name"] = latest_ver
        else:
            for release_ver in self.project["releases"]:
                version = self.sanitize_version(release_ver, pre_ok, major)
                if not version:
                    continue
                if "version" not in ret or version > ret["version"]:
                    ret["tag_name"] = release_ver
                    ret["version"] = version
        if "tag_name" in ret:
            # consider tag_date as upload time of the selected release first file
            ret["files"] = self.project["releases"][ret["tag_name"]]
            ret["tag_date"] = parser.parse(ret["files"][0]["upload_time"])
            return ret
        return None

    @staticmethod
    def make_canonical_link(repo):
        """Make canonical link for a repo."""
        return f"https://{PypiRepoSession.DEFAULT_HOSTNAME}/project/{repo}/"

    def get_canonical_link(self):
        """Get the canonical link for a repo."""
        return f"https://{self.hostname}/project/{self.repo}/"
