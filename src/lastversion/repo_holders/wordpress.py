"""Provides class to represent a WordPress plugin/core project holder."""

import logging

from lastversion.repo_holders.base import BaseProjectHolder
from lastversion.version import Version

log = logging.getLogger(__name__)


class WordPressPluginRepoSession(BaseProjectHolder):
    """A class to represent a WordPress plugin or core project holder."""

    DEFAULT_HOSTNAME = "wordpress.org"
    REPO_URL_PROJECT_COMPONENTS = 1
    # For project URLs, e.g., https://wordpress.org/plugins/opcache-reset/
    # a URI does not start with a repo name, skip '/plugins/'
    REPO_URL_PROJECT_OFFSET = 1

    KNOWN_REPOS_BY_NAME = {
        "wordpress": {"repo": "wordpress"},
    }

    def _get_core_project(self):
        """Fetch WordPress core version info from the version-check API.

        Returns:
            dict: Project dict with name, version, and download_link,
                or None if the API call fails.
        """
        url = "https://api.wordpress.org/core/version-check/1.7/"
        log.info("Requesting WordPress core version from %s", url)
        response = self.get(url)
        if response.status_code != 200:
            return None
        data = response.json()
        for offer in data.get("offers", []):
            if offer.get("response") == "upgrade":
                return {
                    "name": "WordPress",
                    "version": offer["version"],
                    "download_link": offer["download"],
                }
        return None

    def get_project(self):
        """Get project JSON data."""
        if self.is_core:
            return self._get_core_project()
        project = None
        url = f"https://api.{self.hostname}/plugins/info/1.0/{self.repo}.json"
        log.info("Requesting %s", url)
        response = self.get(url)
        if response.status_code == 200:
            project = response.json()
        return project

    def is_instance(self):
        return self.project

    def __init__(self, repo, hostname=None):
        super().__init__(repo, hostname)
        if hostname:
            self.hostname = hostname
        else:
            self.hostname = WordPressPluginRepoSession.DEFAULT_HOSTNAME
        self.is_core = repo and repo.lower() == "wordpress"
        self.project = self.get_project()

    def release_download_url(self, release, shorter=False):
        """Get release download URL."""
        if self.is_core:
            return self.project.get("download_link")
        return f'https://downloads.wordpress.org/plugin/{self.repo}.{release["version"]}.zip'

    def get_latest(self, pre_ok=False, major=None):
        """Get the latest release for this project."""
        ret = {}
        # we are in "enriching" project dict with desired version information
        # and return None if there's no matching version

        if self.is_core:
            latest_ver = self.project["version"]
            v = Version(latest_ver)
            if major and v.major != major:
                return None
            ret["version"] = v
            ret["tag_name"] = latest_ver
            self.project.update(ret)
            return self.project

        if not major:
            latest_ver = self.project["version"]
            v = Version(latest_ver)
            ret["version"] = v
            # there are no tags, we just put version string there
            ret["tag_name"] = latest_ver
        else:
            for release_ver in self.project["versions"]:
                version = self.sanitize_version(release_ver, pre_ok, major)
                if not version:
                    continue
                if "version" not in ret or version > ret["version"]:
                    ret["tag_name"] = release_ver
                    ret["version"] = version
                    log.info("Set current selection to %s", version)
                else:
                    log.info("Not set %s", version)
        if "tag_name" in ret:
            self.project.update(ret)
            return self.project
        return None

    @staticmethod
    def make_canonical_link(repo):
        """Make canonical link from repo."""
        return f"https://{WordPressPluginRepoSession.DEFAULT_HOSTNAME}/plugins/{repo}/"

    def get_canonical_link(self):
        """Get canonical link from repo."""
        if self.is_core:
            return f"https://{self.hostname}/"
        return f"https://{self.hostname}/plugins/{self.repo}/"
