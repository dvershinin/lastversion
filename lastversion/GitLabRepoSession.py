import logging
import os
import platform
import re
from datetime import timedelta

from dateutil import parser

from .ProjectHolder import ProjectHolder
from .utils import asset_does_not_belong_to_machine

log = logging.getLogger(__name__)


class GitLabRepoSession(ProjectHolder):
    DEFAULT_HOSTNAME = "gitlab.com"
    CAN_BE_SELF_HOSTED = True
    # Domains gitlab.example.com
    SUBDOMAIN_INDICATOR = "gitlab"

    def __init__(self, repo, hostname):
        super(GitLabRepoSession, self).__init__(repo, hostname)
        self.pa_token = os.getenv("GITLAB_PA_TOKEN")
        self.hostname = hostname
        if not self.hostname:
            self.hostname = self.DEFAULT_HOSTNAME
        if self.pa_token:
            log.info("Using Personal Access token.")
            self.headers.update({"Private-Token": self.pa_token})
        self.api_base = f"https://{self.hostname}/api/v4"
        self.repo_id = self.repo.replace("/", "%2F")
        # lazy loaded dict cache of /releases response keyed by tag, only first page
        self.formal_releases_by_tag = None

    def repo_query(self, uri):
        url = f"{self.api_base}/projects/{self.repo_id}{uri}"
        return self.get(url)

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

    def get_latest(self, pre_ok=False, major=None):
        """Get the latest release."""
        ret = None

        # gitlab returns tags by updated in desc order; this is just what we want :)
        r = self.repo_query("/repository/tags")
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
        return ret

    def get_assets(self, release, short_urls, assets_filter=None):
        urls = []
        assets = release.get("assets", {}).get("links", [])
        arch_matched_assets = []
        if not assets_filter and platform.machine() in ["x86_64", "AMD64"]:
            for asset in assets:
                if "x86_64" in asset["name"]:
                    arch_matched_assets.append(asset)
            if arch_matched_assets:
                assets = arch_matched_assets

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

    def release_download_url(self, release, shorter=False):
        """Get release download URL."""
        if shorter:
            log.info("Shorter URLs are not supported for GitLab yet")
        # https://gitlab.com/onedr0p/sonarr-episode-prune/-/archive/v3.0.0/sonarr-episode-prune-v3.0.0.tar.gz
        ext = "zip" if os.name == "nt" else "tar.gz"
        tag = release["tag_name"]
        url_format = "https://{}/{}/-/archive/{}/{}-{}.{}"
        return url_format.format(
            self.hostname, self.repo, tag, self.repo.split("/")[1], tag, ext
        )

    def repo_license(self, tag):
        # TODO implement
        pass
