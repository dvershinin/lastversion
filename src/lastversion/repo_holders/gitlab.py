"""GitLab repo session."""

import logging
import os
import platform
import re
from datetime import timedelta

from dateutil import parser

from lastversion.exceptions import BadProjectError
from lastversion.repo_holders.base import BaseProjectHolder
from lastversion.utils import asset_does_not_belong_to_machine

log = logging.getLogger(__name__)


class GitLabRepoSession(BaseProjectHolder):
    """GitLab repo session."""

    DEFAULT_HOSTNAME = "gitlab.com"
    CAN_BE_SELF_HOSTED = True
    # Domains gitlab.example.com
    SUBDOMAIN_INDICATOR = "gitlab"

    # GitLab has unlimited nesting in subgroups
    REPO_URL_PROJECT_COMPONENTS = True

    def __init__(self, repo, hostname):
        super().__init__(repo, hostname)
        self.pa_token = os.getenv("GITLAB_PA_TOKEN")
        self.hostname = hostname
        if not self.hostname:
            self.hostname = self.DEFAULT_HOSTNAME
        if self.pa_token:
            log.info("Using Personal Access token.")
            self.headers.update({"Private-Token": self.pa_token})
        self.api_base = f"https://{self.hostname}/api/v4"
        self.repo = self.find_gitlab_project_path(repo)
        # lazy loaded dict cache of /releases response keyed by tag, only first page
        self.formal_releases_by_tag = None

    def repo_query(self, uri, params=None):
        """Query the repo API."""
        repo_enc = self.repo.replace("/", "%2F")
        url = f"{self.api_base}/projects/{repo_enc}{uri}"
        log.debug("Querying %s", url)
        return self.get(url, params=params)

    def ensure_formal_releases_fetched(self):
        """
        Prime cache for dict of recent formal releases
        this fetches /releases and allow quickly look up if a tag is marked as pre-release
        """
        if self.formal_releases_by_tag is None:
            self.formal_releases_by_tag = {}
            r = self.repo_query("/releases")
            if r.status_code == 200:
                for release in r.json():
                    self.formal_releases_by_tag[release["tag_name"]] = release

    def get_formal_release_for_tag(self, tag):
        """Get formal release for a given GitLab tag"""
        self.ensure_formal_releases_fetched()
        # no releases in /releases means no
        if self.formal_releases_by_tag and tag not in self.formal_releases_by_tag:
            r = self.repo_query(f"/releases/{tag}")
            if r.status_code == 200:
                self.formal_releases_by_tag[tag] = r.json()

        return self.formal_releases_by_tag.get(tag)

    def find_gitlab_project_path(self, uri):
        """
        Finds the GitLab project path from a given URL.

        Args:
            uri (str): The GitLab URI.

        Returns:
            str: The path of the project if found, otherwise None.
        """

        # /librewolf-community/browser/appimage/-/releases could be passed,
        # remove all starting /-/ as it is not part of the project path
        uri = uri.split("/-/")[0]

        url_parts = uri.split("/")

        for i in range(len(url_parts), 1, -1):
            potentional_repo = "/".join(url_parts[:i])
            potentional_repo_enc = potentional_repo.replace("/", "%2F")
            api_url = f"{self.api_base}/projects/{potentional_repo_enc}"

            log.debug("Checking if %s is repo", api_url)
            response = self.get(api_url)
            if response.status_code == 200:
                log.debug("Found repo %s", potentional_repo)
                return potentional_repo
        raise BadProjectError(
            f"Could not find GitLab project for {uri} on {self.hostname}. "
            "Check your GITLAB_PA_TOKEN and URL for correctness."
        )

    def get_latest(self, pre_ok=False, major=None):
        """Get the latest release."""
        ret = {}

        # gitlab returns tags by updated in desc order; this is just what we want :)
        r = self.repo_query("/repository/tags", params={"per_page": 100})
        if r.status_code == 200:
            for t in r.json():
                tag = t["name"]
                tag_date = parser.parse(t["commit"]["created_at"])
                version = self.sanitize_version(tag, pre_ok, major)
                if not version:
                    continue
                if ret and tag_date + timedelta(days=365) < ret["tag_date"]:
                    log.info("The version %s is newer, but is too old!", version)
                    break
                if not ret or ret and version > ret["version"]:
                    log.info("Setting version as current selection: %s.", version)
                    ret = t
                    ret["tag_name"] = tag
                    ret["tag_date"] = tag_date
                    ret["version"] = version
                    ret["type"] = "tag"
        if ret:
            formal_release = self.get_formal_release_for_tag(ret["tag_name"])
            if formal_release:
                ret.update(formal_release)
        return ret or None

    def _filter_assets(self, release, assets_filter):
        """Filter and return assets from release."""
        assets = release.get("assets", {}).get("links", [])
        arch_matched_assets = []
        if not assets_filter and platform.machine() in ["x86_64", "AMD64"]:
            for asset in assets:
                if "x86_64" in asset["name"]:
                    arch_matched_assets.append(asset)
            if arch_matched_assets:
                assets = arch_matched_assets
        return assets

    def get_assets(self, release, short_urls, assets_filter=None):
        """Get assets for a given release."""
        urls = []
        assets = self._filter_assets(release, assets_filter)

        for asset in assets:
            if assets_filter and not re.search(assets_filter, asset["name"]):
                continue
            if not assets_filter and asset_does_not_belong_to_machine(asset["name"]):
                log.info(
                    "Skipping asset %s as it does not belong to this machine.",
                    asset["name"],
                )
                continue
            urls.append(asset["url"])

        if not urls:
            download_url = self.release_download_url(release, short_urls)
            if not assets_filter or re.search(assets_filter, download_url):
                urls.append(download_url)
        return urls

    def get_assets_with_digests(self, release, short_urls, assets_filter=None):
        """Get assets with detailed information for GitLab releases.

        GitLab doesn't provide digests via API, but we include url, name, and size.
        """
        result = []
        assets = self._filter_assets(release, assets_filter)

        for asset in assets:
            if assets_filter and not re.search(assets_filter, asset["name"]):
                continue
            if not assets_filter and asset_does_not_belong_to_machine(asset["name"]):
                log.info(
                    "Skipping asset %s as it does not belong to this machine.",
                    asset["name"],
                )
                continue
            asset_info = {
                "url": asset.get("url") or asset.get("direct_asset_url"),
                "name": asset.get("name"),
                "size": None,  # GitLab API doesn't provide file size in release links
            }
            result.append(asset_info)

        if not result:
            download_url = self.release_download_url(release, short_urls)
            if not assets_filter or re.search(assets_filter, download_url):
                result.append({"url": download_url, "name": None, "size": None})
        return result

    def release_download_url(self, release, shorter=False):
        """Get release download URL."""
        if shorter:
            log.info("Shorter URLs are not supported for GitLab yet")
        # https://gitlab.com/onedr0p/sonarr-episode-prune/-/archive/v3.0.0/sonarr-episode-prune-v3.0.0.tar.gz
        ext = "zip" if os.name == "nt" else "tar.gz"
        tag = release["tag_name"]
        url_format = "https://{}/{}/-/archive/{}/{}-{}.{}"
        return url_format.format(self.hostname, self.repo, tag, self.repo.split("/")[1], tag, ext)

    def repo_license(self, tag):
        """Get repo license."""

        response = self.get(f"https://{self.hostname}/{self.repo}/-/raw/{tag}/LICENSE?ref_type=tags")
        if response.status_code == 200:
            return {"text": response.text}
        return None

    def repo_changelog(self, tag):
        """Try to fetch a conventional CHANGELOG/CHANGES/NEWS file at a tag."""
        for path in BaseProjectHolder.CHANGELOG_CANDIDATES:
            text = self.fetch_text_file_at_tag(tag, path)
            if text:
                return text
        return None

    def fetch_text_file_at_tag(self, tag: str, path: str) -> str:
        """Fetch text file via GitLab raw endpoint; set Accept for plain text."""
        response = self.get(
            f"https://{self.hostname}/{self.repo}/-/raw/{tag}/{path}?ref_type=tags",
            headers={"Accept": "text/plain, */*"},
        )
        if response.status_code == 200 and response.text and response.text.strip():
            return response.text
        return None

    def repo_changelog_path(self, tag):
        for path in BaseProjectHolder.CHANGELOG_CANDIDATES:
            text = self.fetch_text_file_at_tag(tag, path)
            if text:
                return text, path
        return None, None
