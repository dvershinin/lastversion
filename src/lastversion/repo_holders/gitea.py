"""Gitea repository session class."""

import json
import logging
import math
import os
import re
import time

from bs4 import BeautifulSoup
from dateutil import parser

from lastversion.exceptions import ApiCredentialsError, BadProjectError
from lastversion.repo_holders.base import BaseProjectHolder

log = logging.getLogger(__name__)

TOKEN_PRO_TIP = "ProTip: set GITHUB_API_TOKEN env var as per " "https://github.com/dvershinin/lastversion#tips"


def asset_matches(asset, search, regex_matching):
    """Check if the asset equals to string or satisfies a regular expression
    Args:
        asset (dict): asset dict as returned by the API
        search (str): string or regexp to match asset's name or label with
        regex_matching (bool): whether search argument is a regexp
    Returns:
        bool: Whether match is satisfied
    """
    if regex_matching:
        if asset["label"] and re.search(search, asset["label"]):
            return True
        if asset["name"] and re.search(search, asset["name"]):
            return True
    elif search in (asset["label"], asset["name"]):
        return True
    return False


class GiteaRepoSession(BaseProjectHolder):
    """A class to represent a Gitea-based project holder (Gitea, Codeberg, etc.)."""

    DEFAULT_HOSTNAME = "gitea.com"
    # Additional known Gitea-based forges
    KNOWN_HOSTNAMES = ["gitea.com", "codeberg.org"]
    CAN_BE_SELF_HOSTED = True
    """ The following format will benefit from:
    1) not using API, so is not subject to its rate limits
    2) likely has been accessed by someone in CDN and thus faster
    3) provides more or less unique filenames once the stuff is downloaded
    See https://fedoraproject.org/wiki/Packaging:SourceURL#Git_Tags
    We use variation of this: it does not need a parsed version (works for
    --pre better) and it is not broken on fancy release tags like v1.2.3-stable
    https://github.com/OWNER/PROJECT/archive/%{git_tag}/%{git_tag}-%{version}.tar.gz
    """
    RELEASE_URL_FORMAT = "https://{hostname}/{repo}/archive/{tag}.{ext}"
    SHORT_RELEASE_URL_FORMAT = RELEASE_URL_FORMAT

    def find_repo_by_name_only(self, repo):
        """Find repo by name only using Gitea API."""
        if self.is_link(repo):
            return None
        cache_repo_names_file = f"{self.cache_dir}/repos.json"
        try:
            with open(cache_repo_names_file, "r", encoding="utf-8") as reader:
                cache = json.load(reader)
        except (IOError, ValueError):
            cache = {}
        try:
            if repo in cache and time.time() - cache[repo]["updated_at"] < 3600 * 24 * 30:
                log.info("Found %s in repo short name cache", repo)
                if not cache[repo]["repo"]:
                    raise BadProjectError(f"No project found on GitHub for search query: {repo}")
        except TypeError:
            pass
        log.info("Making query against GitHub API to search repo %s", repo)
        r = self.get(f"{self.api_base}/search/repositories", params={"q": f"{repo} in:name"})
        if r.status_code == 404:
            # when not found, skip using this holder in the factory by not
            # setting self.repo
            return None
        if r.status_code != 200:
            raise BadProjectError(f"Error while identifying full repository on GitHub for " f"search query: {repo}")
        data = r.json()
        full_name = ""
        if data["items"]:
            full_name = data["items"][0]["full_name"]
        cache[repo] = {"repo": full_name, "updated_at": int(time.time())}
        try:
            with open(cache_repo_names_file, "w", encoding="utf-8") as writer:
                json.dump(cache, writer)
        except (IOError, ValueError):
            pass
        if not full_name:
            raise BadProjectError(f"No project found on GitHub for search query: {repo}")
        return full_name

    @classmethod
    def is_matching_hostname(cls, hostname):
        """Check if given hostname matches known Gitea-based forges."""
        if not hostname:
            return None
        # Extract hostname without port for comparison
        hostname_only = hostname.rsplit(":", 1)[0] if ":" in hostname else hostname
        # Check against known hostnames
        if hostname_only in cls.KNOWN_HOSTNAMES:
            return True
        return False

    def is_instance(self):
        """
        Check if this is a Gitea repo page.
        Navigate to the homepage of project by URL
        Gitea project page will have
        """
        project_page = f"https://{self.hostname}/{self.repo}"
        # log the URL we are about to check
        log.info("Checking as Gitea project at %s", project_page)
        response = self.get(project_page, timeout=10)
        if response.status_code == 200:
            # create beautiful soup :)
            soup = BeautifulSoup(response.text, "html.parser")
            # If there's <link rel="alternate" type="application/atom+xml" title="" href="/{repo}.atom">, it's a Gitea repo
            if soup.find("link", {"href": f"/{self.repo}.atom"}):
                return True
        return False

    def __init__(self, repo, hostname):
        super().__init__(repo, hostname)
        # dict holding repo/owner to feed contents of releases' atom
        self.feed_contents = {}
        self.rate_limited_count = 0
        self.api_token = os.getenv("GITEA_API_TOKEN")
        self.hostname = hostname
        if not self.hostname:
            self.hostname = self.DEFAULT_HOSTNAME
        # Explicitly specify the API version that we want:
        self.headers.update({"Accept": "application/vnd.github.v3+json"})
        if self.api_token:
            log.info("Using API token.")
            self.headers.update({"Authorization": f"token {self.api_token}"})
        if self.hostname != self.DEFAULT_HOSTNAME:
            self.api_base = f"https://{self.hostname}/api/v1"
        else:
            self.api_base = f"https://{self.DEFAULT_HOSTNAME}/api/v1"
        if "/" not in repo:
            official_repo = self.try_get_official(repo)
            if official_repo:
                repo = official_repo
                log.info("Using official repo %s", repo)
            else:
                repo = self.find_repo_by_name_only(repo)
                if repo:
                    log.info("Using repo %s obtained from search API", self.repo)
                else:
                    return

    @property
    def rate_limit_url(self):
        """Get the rate limit URL."""
        return f"{self.api_base}/rate_limit"

    def get(self, url, **kwargs):
        """Send GET request and account for GitHub rate limits and such."""
        r = super().get(url, **kwargs)
        log.info("Got HTTP status code %s from %s", r.status_code, url)
        if r.status_code == 401:
            if self.api_token:
                raise ApiCredentialsError("API request was denied despite using an API token. " "Missing scopes?")
            raise ApiCredentialsError(
                "Denied API access. Please set GITHUB_API_TOKEN env var as "
                "per https://github.com/dvershinin/lastversion#tips"
            )
        if r.status_code == 403 and "X-RateLimit-Reset" in r.headers and "X-RateLimit-Remaining" in r.headers:
            if self.rate_limited_count > 2:
                raise ApiCredentialsError(
                    f"API requests were denied after retrying " f"{self.rate_limited_count} times"
                )
            remaining = int(r.headers["X-RateLimit-Remaining"])
            # One sec to account for skewed clock between GitHub and client
            wait_for = float(r.headers["X-RateLimit-Reset"]) - time.time() + 1.0
            wait_for = math.ceil(wait_for)
            if not remaining:
                # got 403, likely due to used quota
                if wait_for < 300:
                    if wait_for < 0:
                        log.warning("Exceeded API quota. Repeating request because quota is about to " "be reinstated")
                    else:
                        w = f"Waiting {wait_for} seconds for API quota reinstatement."
                        if "GITHUB_API_TOKEN" not in os.environ and "GITHUB_TOKEN" not in os.environ:
                            w = f"{w} {TOKEN_PRO_TIP}"
                        log.warning(w)
                        time.sleep(wait_for)
                    self.rate_limited_count = self.rate_limited_count + 1
                    return self.get(url)
                raise ApiCredentialsError(f'Exceeded API rate limit after waiting: {r.json()["message"]}')
            return self.get(url)

        if r.status_code == 403 and url != self.rate_limit_url:
            self.rate_limited_count = 0
        return r

    def rate_limit(self):
        """Get rate limit info."""
        url = f"{self.api_base}/rate_limit"
        return self.get(url)

    def repo_query(self, uri):
        """Query the repo API."""
        url = f"{self.api_base}/repos/{self.repo}{uri}"
        return self.get(url)

    def repo_license(self, tag):
        """Get the license file for a tag."""
        r = self.repo_query(f"/license?ref={tag}")
        if r.status_code == 200:
            # unfortunately, unlike /readme, API always returns *latest* license, ignoring tag
            # we have to double-check whether the license file exists "at release tag"
            license_data = r.json()
            license_path = license_data["path"]
            license_r = self.repo_query(f"/contents/{license_path}?ref={tag}")
            if license_r.status_code == 200:
                return license_data
        return None

    def repo_readme(self, tag):
        """Get the readme file for a tag."""
        r = self.repo_query(f"/readme?ref={tag}")
        if r.status_code == 200:
            return r.json()
        return None

    def get_formal_release_for_tag(self, tag):
        """Get the formal release for a tag, if it exists."""
        r = self.repo_query(f"/releases/tags/{tag}")
        if r.status_code == 200:
            # noinspection SpellCheckingInspection
            return r.json()
        return None

    # finding in tags requires paging through ALL of them, because the API does not list them
    # in order of recency, thus this is very slow
    # in: current release to be returned, output: newer release to be returned
    def find_in_tags(self, pre_ok, major):
        """Find the latest release in tags."""
        ret = {}
        r = self.repo_query("/tags?per_page=100")
        if r.status_code != 200:
            return None
        tags = r.json()
        while "next" in r.links.keys():
            r = self.get(r.links["next"]["url"])
            tags.extend(r.json())

        for t in tags:
            tag_name = t["name"]
            version = self.sanitize_version(tag_name, pre_ok, major)
            if not version:
                continue
            d = parser.parse(t["commit"]["created"])

            if not ret or version > ret["version"] or d > ret["tag_date"]:
                # rare case: if upstream filed formal pre-release that passes as stable
                # version (tag is 1.2.3 instead of 1.2.3b) double check if pre-release
                # TODO handle API failure here as it may result in "false positive"?
                release_for_tag = self.get_formal_release_for_tag(tag_name)
                if release_for_tag:
                    ret = self.set_matching_formal_release(ret, release_for_tag, version, pre_ok)
                else:
                    ret = t
                    ret["tag_name"] = tag_name
                    ret["tag_date"] = d
                    ret["version"] = version
                    ret["type"] = "tag"
        return ret or None

    def get_latest(self, pre_ok=False, major=None):
        """
        Gets the latest release satisfying "pre-releases are OK" or major/branch constraints
        Strive to fetch formal API release if it exists, because it has useful information
        like assets.
        """
        if self.having_asset:
            # only formal releases which we enumerated above already, have assets,
            # so there is no point looking in the tags/graphql below
            # return whatever we got
            return None

        # formal release may not exist at all, or be "late/old" in case
        # actual release is only a simple tag, so let's try /tags
        ret = self.find_in_tags(pre_ok, major)

        return ret

    def set_matching_formal_release(self, ret, formal_release, version, pre_ok, data_type="release"):
        """Set the current release selection to this formal release if matching conditions."""
        if not pre_ok and formal_release["prerelease"]:
            log.info(
                "Found formal release for this tag which is unwanted " "pre-release: %s.",
                version,
            )
            return ret
        if self.having_asset:
            if "assets" not in formal_release or not formal_release["assets"]:
                log.info("Skipping this release due to no assets.")
                return ret
            if self.having_asset is not True:
                regex_matching = False
                search = self.having_asset
                if search.startswith("~"):
                    search = rf'{search.lstrip("~")}'
                    regex_matching = True
                found_asset = False
                for asset in formal_release["assets"]:
                    if asset_matches(asset, search, regex_matching=regex_matching):
                        found_asset = True
                        break
                if not found_asset:
                    log.info("Desired asset not found in the release.")
                    return ret
        formal_release["tag_date"] = parser.parse(formal_release["published_at"])
        formal_release["version"] = version
        formal_release["type"] = data_type
        log.info("Selected version as current selection: %s.", formal_release["version"])
        return formal_release

    def try_get_official(self, repo):
        """Check the existence of repo/repo

        Returns:
            str: updated repo
        """
        official_repo = f"{repo}/{repo}"
        log.info("Checking existence of %s", official_repo)
        r = self.get_feed_response(f"https://{self.hostname}/{official_repo}/releases.atom")
        # API requests are varied by cookie, we don't want serializer for
        # cache fail because of that
        self.cookies.clear()
        if r.status_code == 200:
            self.feed_contents[official_repo] = r.text
            return official_repo
        return None
