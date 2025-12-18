"""BitBucket repository session."""

import logging

from dateutil import parser

from lastversion.exceptions import BadProjectError
from lastversion.repo_holders.base import BaseProjectHolder

log = logging.getLogger(__name__)


class BitBucketRepoSession(BaseProjectHolder):
    """BitBucket repository session."""

    DEFAULT_HOSTNAME = "bitbucket.org"
    CAN_BE_SELF_HOSTED = True
    KNOWN_REPO_URLS = {
        "mmonit.com": {
            "repo": "tildeslash/monit",
            # get URL from the official website because it is a "prepared"
            # source that has the `./configure` script available
            "release_url_format": "https://mmonit.com/{name}/dist/{name}-" "{version}.tar.gz",
        }
    }

    KNOWN_REPOS_BY_NAME = {"monit": KNOWN_REPO_URLS["mmonit.com"]}

    def __init__(self, repo, hostname):
        super().__init__(repo, hostname)
        self.hostname = hostname
        if not self.hostname:
            self.hostname = self.DEFAULT_HOSTNAME

    def get_latest(self, pre_ok=False, major=None):
        """Get the latest release."""
        # Try to get releases from downloads first (for paid plans)
        try:
            response = self.get(f"https://api.bitbucket.org/2.0/repositories/{self.repo}/downloads")
            response.raise_for_status()

            # Check if response is valid JSON
            try:
                data = response.json()
            except ValueError:
                # If downloads API returns HTML error (free plan), fall back to tags
                log.info("Downloads API not available, falling back to tags API")
                return self._get_latest_from_tags(pre_ok, major)

            if data.get("values"):
                release = data["values"][0]
                version = self.sanitize_version(release["name"], pre_ok, major)
                release["version"] = version
                release["tag_name"] = release["name"]
                release["tag_date"] = parser.parse(release["created_on"])
                return release
        except Exception as e:
            log.info("Downloads API failed: %s, falling back to tags API", e)

        # Fall back to tags API
        return self._get_latest_from_tags(pre_ok, major)

    def _get_latest_from_tags(self, pre_ok=False, major=None):
        """Get the latest release from tags API."""
        # Get all tags with pagination
        all_tags = []
        next_url = f"https://api.bitbucket.org/2.0/repositories/{self.repo}/refs/tags?pagelen=100"

        while next_url:
            response = self.get(next_url)
            response.raise_for_status()

            try:
                data = response.json()
            except ValueError as e:
                raise BadProjectError(f"Invalid JSON response from BitBucket API: {e}")

            if not data.get("values"):
                break

            all_tags.extend(data["values"])

            # Check if there are more pages
            next_url = data.get("next")

        if not all_tags:
            raise BadProjectError(f"No tags found for repository {self.repo}")

        # Find the latest valid version from all tags
        latest_release = None
        latest_version = None

        for tag in all_tags:
            tag_name = tag["name"]
            version = self.sanitize_version(tag_name, pre_ok, major)

            if not version:
                continue

            if latest_version is None or version > latest_version:
                latest_version = version
                latest_release = {
                    "name": tag_name,
                    "version": version,
                    "tag_name": tag_name,
                    "tag_date": parser.parse(tag["target"]["date"]),
                    "created_on": tag["target"]["date"],
                }

        if not latest_release:
            raise BadProjectError(f"No valid versions found for repository {self.repo}")

        return latest_release
