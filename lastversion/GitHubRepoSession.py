import logging
from urllib.parse import unquote

import math
import os
import re
import time
from datetime import datetime
from datetime import timedelta

import feedparser
from dateutil import parser

from .ProjectHolder import ProjectHolder
from .exceptions import ApiCredentialsError, BadProjectError

log = logging.getLogger(__name__)

TOKEN_PRO_TIP = (
    "ProTip: set GITHUB_API_TOKEN env var as per "
    "https://github.com/dvershinin/lastversion#tips"
)


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


class GitHubRepoSession(ProjectHolder):
    """A class to represent a GitHub project holder."""

    DEFAULT_HOSTNAME = "github.com"
    CAN_BE_SELF_HOSTED = True
    TOKEN_ENV_VARS = [
        "LASTVERSION_GITHUB_API_TOKEN",
        "GITHUB_API_TOKEN",
        "GITHUB_TOKEN",
    ]

    # one-word aliases or simply known popular repos to skip using search API
    KNOWN_REPOS_BY_NAME = {
        "php": {
            "repo": "php/php-src",
            # get URL from the official website because it is a "prepared" source
            "release_url_format": "https://www.php.net/distributions/php-{version}.tar.gz",
        },
        "linux": {"repo": "torvalds/linux"},
        "kernel": {"repo": "torvalds/linux"},
        "openssl": {"repo": "openssl/openssl"},
        "python": {"repo": "python/cpython"},
        "cmake": {"repo": "kitware/cmake"},
        "kodi": {"repo": "xbmc/xbmc"},
        "quictls": {"repo": "quictls/openssl"},
    }

    """
    The last alphanumeric after digits is part of version scheme, not beta level.
    E.g. 1.1.1b is not beta. Hard-coding such odd repos is required.
    """
    LAST_CHAR_FIX_REQUIRED_ON = ["openssl/openssl", "quictls/openssl"]

    """ The following format will benefit from:
    1) not using API, so is not subject to its rate limits
    2) likely has been accessed by someone in CDN and thus faster
    3) provides more or less unique filenames once the stuff is downloaded
    See https://fedoraproject.org/wiki/Packaging:SourceURL#Git_Tags
    We use variation of this: it does not need a parsed version (thus works for --pre better)
    and it is not broken on fancy release tags like v1.2.3-stable
    https://github.com/OWNER/PROJECT/archive/%{gittag}/%{gittag}-%{version}.tar.gz
    """
    RELEASE_URL_FORMAT = "https://{hostname}/{repo}/archive/{tag}/{name}-{tag}.{ext}"
    SHORT_RELEASE_URL_FORMAT = "https://{hostname}/{repo}/archive/{tag}.{ext}"

    def api_search_repo(self, name):
        """API search for a repository

        Returns:
            str: Complete repo qualitfier, e.g. "OWNER/PROJECT"
        """
        log.info("Making query against GitHub API to search repo %s", name)
        r = self.get(
            f"{self.api_base}/search/repositories",
            params={"q": f"{name} in:name", "sort": "stars", "per_page": 1},
        )

        if r.status_code == 200:
            data = r.json()
            if data["items"]:
                return data["items"][0]["full_name"]

        return None

    def find_repo_by_name_only(self, repo):
        """Find a repo by name only, without owner."""

        cache = self.get_name_cache()

        try:
            if (
                repo in cache
                and time.time() - cache[repo]["updated_at"] < 3600 * 24 * 30
            ):
                log.info("Found %s in repo short name cache", repo)
                if not cache[repo]["repo"]:
                    raise BadProjectError(
                        f"No project found on GitHub for search query: {repo}"
                    )
                return cache[repo]["repo"]
        except TypeError:
            pass

        full_name = self.try_get_official(repo)
        if full_name:
            log.info("Using official repo %s", repo)
        else:
            full_name = self.api_search_repo(repo)

        cache[repo] = {"repo": full_name, "updated_at": int(time.time())}

        self.update_name_cache(cache)

        if not full_name:
            raise BadProjectError(
                f"No project found on GitHub for search query: {repo}"
            )
        return full_name

    def __init__(self, repo, hostname=DEFAULT_HOSTNAME):
        super(GitHubRepoSession, self).__init__(repo, hostname)
        # dict holding repo/owner to feed contents of releases' atom
        self.feed_contents = {}
        # lazy loaded dict cache of /releases response keyed by tag, only first page
        self.formal_releases_by_tag = None
        self.rate_limited_count = 0
        self.api_token = None
        for var_name in self.TOKEN_ENV_VARS:
            token = os.getenv(var_name)
            if token:
                self.api_token = token
                log.info("Using API token %s.", var_name)
                self.headers.update({"Authorization": f"token {self.api_token}"})
                break
        if not self.api_token:
            log.info(
                "No API token found in environment variables %s.", self.TOKEN_ENV_VARS
            )

        # Explicitly specify the API version that we want:
        self.headers.update({"Accept": "application/vnd.github+json"})

        if self.hostname != self.DEFAULT_HOSTNAME:
            self.api_base = f"https://{self.hostname}/api/v3"
        else:
            self.api_base = f"https://api.{self.DEFAULT_HOSTNAME}"

        if "/" not in repo:
            self.repo = self.find_repo_by_name_only(repo)

    def get_rate_limit_url(self):
        return f"{self.api_base}/rate_limit"

    def get(self, url, **kwargs):
        """Send GET request and account for GitHub rate limits and such."""
        r = super(GitHubRepoSession, self).get(url, **kwargs)
        log.info("Got HTTP status code %s from %s", r.status_code, url)
        if r.status_code == 401:
            if self.api_token:
                raise ApiCredentialsError(
                    "API request was denied despite using an API token. "
                    "Missing scopes?"
                )
            raise ApiCredentialsError(
                "Denied API access. Please set GITHUB_API_TOKEN env var "
                "as per https://github.com/dvershinin/lastversion#tips"
            )
        if (
            r.status_code == 403
            and "X-RateLimit-Reset" in r.headers
            and "X-RateLimit-Remaining" in r.headers
        ):
            if self.rate_limited_count > 2:
                raise ApiCredentialsError(
                    f"API requests were denied after retrying {self.rate_limited_count} times"
                )
            remaining = int(r.headers["X-RateLimit-Remaining"])
            # One sec to account for skewed clock between GitHub and client
            wait_for = float(r.headers["X-RateLimit-Reset"]) - time.time() + 1.0
            wait_for = math.ceil(wait_for)
            if not remaining:
                # got 403, likely due to used quota
                if wait_for < 300:
                    if wait_for < 0:
                        log.warning(
                            "Exceeded API quota. Repeating request because "
                            "quota is about to be reinstated"
                        )
                    else:
                        w = (
                            f"Waiting {wait_for} seconds for API quota "
                            f"reinstatement."
                        )
                        if not self.api_token:
                            w = f"{w} {TOKEN_PRO_TIP}"
                        log.warning(w)
                        time.sleep(wait_for)
                    self.rate_limited_count = self.rate_limited_count + 1
                    return self.get(url)
                raise ApiCredentialsError(
                    f"Exceeded GitHub API rate limits. Giving up due to high "
                    f"expected wait {wait_for}s. API says: "
                    f'{r.json()["message"]}'
                )
            return self.get(url)

        if r.status_code == 403 and url != self.get_rate_limit_url():
            self.rate_limited_count = 0
        return r

    def rate_limit(self):
        """Get rate limit info."""
        url = f"{self.api_base}/rate_limit"
        return self.get(url)

    def repo_query(self, uri):
        """API query for a repository"""
        url = f"{self.api_base}/repos/{self.repo}{uri}"
        return self.get(url)

    def repo_license(self, tag):
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
        """API query for a repository's README"""
        r = self.repo_query(f"/readme?ref={tag}")
        if r.status_code == 200:
            return r.json()
        return None

    def find_in_tags_via_graphql(self, ret, pre_ok, major):
        """GraphQL allows for faster search across many tags.
        We aggregate the highest semantic version among batches of 100 records.
        In this way --major filtering results in much fewer requests compared to traditional API
        use.

        Args:
            ret (dict): currently selected release object
            pre_ok (bool): whether betas are acceptable
            major (str): the major filter

        Returns: currently selected release object

        """
        query_fmt = """
        {
          rateLimit {
            cost
            remaining
          }
          repository(owner: "%s", name: "%s") {
            tags: refs(refPrefix: "refs/tags/", first: 100, after: "%s",
              orderBy: {field: TAG_COMMIT_DATE, direction: DESC}) {
              edges {
                cursor,
                node {
                  ...refInfo
                }
              }
            }
          }
        }

        fragment refInfo on Ref {
          name
          target {
            sha: oid
            commitResourcePath
            __typename
            ... on Tag {
              target {
                ... on Commit {
                  ...commitInfo
                }
              }
              tagger {
                name
                email
                date
              }
            }
            ... on Commit {
              ...commitInfo
            }
          }
        }

        fragment commitInfo on Commit {
          zipballUrl
          tarballUrl
          author {
            name
            email
            date
          }
        }

        """
        cursor = ""
        log.info("Using graphql queries...")
        while True:
            # testing on php/php-src
            owner, name = self.repo.split("/")
            query = query_fmt % (owner, name, cursor)
            log.info("Running query %s", query)
            r = self.post(f"{self.api_base}/graphql", json={"query": query})
            log.info('Requested graphql with cursor "%s"', cursor)
            if r.status_code != 200:
                log.info("query returned non 200 response code %s", r.status_code)
                return ret
            j = r.json()
            if "errors" in j and j["errors"][0]["type"] == "NOT_FOUND":
                raise BadProjectError(f"No such project found on GitHub: {self.repo}")
            if not j["data"]["repository"]["tags"]["edges"]:
                log.info("No tags in GraphQL response: %s", r.text)
                break
            for edge in j["data"]["repository"]["tags"]["edges"]:
                node = edge["node"]
                cursor = edge["cursor"]
                tag_name = node["name"]
                version = self.sanitize_version(tag_name, pre_ok, major)
                if not version:
                    continue
                if "tagger" in node["target"]:
                    # use date of annotated tag as it better corresponds to
                    # "release date"
                    log.info("Using annotated tag date")
                    d = node["target"]["tagger"]["date"]
                else:
                    # using commit date because the tag is not annotated
                    log.info("Using commit date")
                    d = node["target"]["author"]["date"]
                tag_date = parser.parse(d)
                if ret and tag_date + timedelta(days=365) < ret["tag_date"]:
                    log.info("The version %s is newer, but is too old!", version)
                    break
                if not ret or version > ret["version"] or tag_date > ret["tag_date"]:
                    # we always want to return formal release if it exists,
                    # because it has useful data grab formal release via APi
                    # to check for pre-release mark
                    formal_release = self.get_formal_release_for_tag(tag_name)
                    if formal_release:
                        ret = self.set_matching_formal_release(
                            ret, formal_release, version, pre_ok
                        )
                    else:
                        if not self.having_asset:
                            ret = {
                                "tag_name": tag_name,
                                "tag_date": tag_date,
                                "version": version,
                                "type": "graphql",
                            }
            if ret:
                break
        return ret

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
        """Get formal release for a given tag, using cache from /releases"""
        self.ensure_formal_releases_fetched()
        # no releases in /releases means no
        if self.formal_releases_by_tag and tag not in self.formal_releases_by_tag:
            r = self.repo_query(f"/releases/tags/{tag}")
            if r.status_code == 200:
                self.formal_releases_by_tag[tag] = r.json()

        return self.formal_releases_by_tag.get(tag)

    def find_in_tags(self, ret, pre_ok, major):
        """
        Find a more recent release in the /tags API endpoint.
        Finding in `/tags` requires paging through ALL of them because the API
         does not list them in order of recency, thus this is very slow.
        We need to check all tags commit dates because of the most recent wins.
        We don't check tags which are:
          * marked pre-release in releases endpoints
          * has a beta-like, non-version tag name

        # in: current release to be returned, output: newer release to be returned
        """
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
            c = self.repo_query(f'/git/commits/{t["commit"]["sha"]}')
            d = c.json()["committer"]["date"]
            d = parser.parse(d)

            if not ret or version > ret["version"] or d > ret["tag_date"]:
                # rare case: if upstream filed formal pre-release that passes as stable
                # version (tag is 1.2.3 instead of 1.2.3b) double check if pre-release
                # TODO handle API failure here as it may result in "false positive"?
                release_for_tag = self.get_formal_release_for_tag(tag_name)
                if release_for_tag:
                    ret = self.set_matching_formal_release(
                        ret, release_for_tag, version, pre_ok
                    )
                else:
                    ret = t
                    ret["tag_name"] = tag_name
                    ret["tag_date"] = d
                    ret["version"] = version
                    ret["type"] = "tag"
        return ret

    def get_releases_feed_contents(self, rename_checked=False):
        """
        Fetch contents of repository's `releases.atom` feed.

        The `releases.atom` and `tags.atom` don't differ much except releases having more data.

        The `releases.atom` feed includes non-formal releases which are just tags, so we are good.
        Based on testing, edited old releases don't jump forward in the list and stay behind (good).
        The only downside is they don't bear pre-release mark (unlike API), and have limited data.
        We work around these by checking the pre-release flag and get full release data via API.
        """
        if self.repo in self.feed_contents:
            return self.feed_contents[self.repo]
        headers = {
            "Accept": "*/*",
            # private repos do not have releases.atom to begin with,
            # authorization header may cause a false positive 200 response with an empty feed!
            "Authorization": "",
        }
        r = self.get(
            f"https://{self.hostname}/{self.repo}/releases.atom", headers=headers
        )
        # API requests are varied by cookie, we don't want serializer for cache fail because of that
        self.cookies.clear()
        if r.status_code == 404 and not rename_checked:
            # #44: in some network locations, GitHub returns 404 (as opposed to a 301 redirect) for the renamed
            # repositories /releases.atom. When we get a 404, we lazily load repo info via API, and hopefully
            # get redirect there as well as the new repo full name
            r = self.repo_query("")
            if r.status_code == 200:
                repo_data = r.json()
                if self.repo != repo_data["full_name"]:
                    log.info(
                        "Detected name change from %s to %s",
                        self.repo,
                        repo_data["full_name"],
                    )
                    self.repo = repo_data["full_name"]
                    # request the feed from the new location
                    return self.get_releases_feed_contents(rename_checked=False)
        if r.status_code == 200:
            self.feed_contents[self.repo] = r.text
            return r.text
        return None

    def get_releases_feed_entries(self):
        """Get an array of `releases.atom` feed entries."""
        feed_contents = self.get_releases_feed_contents()
        if not feed_contents:
            log.info("The releases.atom feed failed to be fetched!")
            return None
        feed = feedparser.parse(feed_contents)
        if "bozo" in feed and feed["bozo"] == 1 and "bozo_exception" in feed:
            exc = feed.bozo_exception
            log.info("Failed to parse feed: %s", exc.getMessage())
            return None
        if not feed.entries:
            log.info("Feed has no elements. Means no tags and no releases")
            return []
        return feed.entries

    def enrich_release_info(self, release):
        """Enrich release info with data from repo."""
        if release:
            release["install_name"] = self.name
        return release

    def get_release_from_feed(self, pre_ok, major):
        """Get the latest release from the `releases.atom` feed."""
        ret = None
        seen_semver = False

        feed_entries = self.get_releases_feed_entries()
        if feed_entries:
            for tag in feed_entries:
                # https://github.com/apache/incubator-pagespeed-ngx/releases/tag/v1.13.35.2-stable
                tag_name = tag["link"].split("/")[-1]
                tag_name = unquote(tag_name)
                log.info("Checking tag %s", tag_name)
                version = self.sanitize_version(tag_name, pre_ok, major)
                if not version:
                    log.info("We did not find a valid version in %s tag", tag_name)
                    continue
                if version.is_semver():
                    seen_semver = True
                comparable = ret and ret["version"].is_semver() == version.is_semver()
                if not comparable:
                    log.info("Tag %s is not comparable to current selection", tag_name)
                # current tag and chosen tag are only comparable if they are both same semver or not
                if comparable and ret["version"] > version:
                    log.info(
                        "Tag %s does not contain newer version than we already found",
                        tag_name,
                    )
                    continue
                # if we have seen a semver tag, then any non-semver can be discarded
                if seen_semver and not version.is_semver():
                    log.info(
                        "Tag %s is not a semver and we already found a semver", tag_name
                    )
                    continue
                tag_date = parser.parse(tag["updated"])
                if ret and ret["version"] == version and ret["tag_date"] >= tag_date:
                    log.info(
                        "Tag %s matches already selected version and is not newer",
                        tag_name,
                    )
                    continue
                if ret and tag_date + timedelta(days=365) < ret["tag_date"]:
                    log.info("The version %s is newer, but is too old!", version)
                    break
                # we always want to return formal release if it exists, because it has useful data
                # grab formal release via APi to check for pre-release mark
                formal_release = self.get_formal_release_for_tag(tag_name)
                if formal_release:
                    # use the full release info
                    ret = self.set_matching_formal_release(
                        ret, formal_release, version, pre_ok
                    )
                else:
                    if self.having_asset:
                        continue
                    log.info("No formal release for tag %s", tag_name)
                    tag["tag_name"] = tag_name
                    tag["tag_date"] = tag_date
                    tag["version"] = version
                    tag["type"] = "feed"
                    # remove keys which are non-jsonable
                    # TODO use those (pop returns them)
                    tag.pop("updated_parsed", None)
                    tag.pop("published_parsed", None)
                    ret = tag
                    log.info("Selected version as current selection: %s.", version)
        return ret

    def get_latest(self, pre_ok=False, major=None):
        """
        Get the latest release satisfying "pre-releases are OK" or major/branch constraints
        Strive to fetch formal API release if it exists, because it has useful information
        like assets.
        """
        # data of selected tag, always contains ['version', 'tag_name', 'tag_date', 'type'] will
        # be returned
        ret = None

        # then always get *all* tags through pagination

        # if pre not ok, filter out tags to check

        # if major, filter out tags to check for major

        if not self.formal:
            ret = self.get_release_from_feed(pre_ok, major)

            # we are good with release from feeds only without looking at the API
            # simply because feeds list stuff in order of recency,
            # however, still use /tags unless releases.atom has data within a year
            if ret and ret["tag_date"].replace(tzinfo=None) > (
                datetime.utcnow() - timedelta(days=365)
            ):
                return self.enrich_release_info(ret)

            log.info(
                "Feed contained none or only tags older than 1 year. Switching to API"
            )

        # only if we did not find desired stuff through feeds, we switch to using API :)
        # this may be required in cases
        # releases.atom has limited/no tags (#63), and all those are beta / invalid / non-versions
        # likewise, we want an older branch (major), which is not there in releases.atom
        # due to the limited nature of data inside it

        self.ensure_formal_releases_fetched()
        for tag_name in self.formal_releases_by_tag:
            release = self.formal_releases_by_tag[tag_name]
            version = self.sanitize_version(tag_name, pre_ok, major)
            if not version:
                continue
            if not ret or version > ret["version"]:
                ret = self.set_matching_formal_release(ret, release, version, pre_ok)

        if self.having_asset or self.formal:
            # only formal releases which we enumerated above already, have assets,
            # so there is no point looking in the tags/graphql below
            # return whatever we got
            return self.enrich_release_info(ret)

        # formal release may not exist at all, or be "late/old" in case
        # actual release is only a simple tag, so let's try /tags
        if self.api_token:
            # GraphQL requires auth
            ret = self.find_in_tags_via_graphql(ret, pre_ok, major)
        else:
            ret = self.find_in_tags(ret, pre_ok, major)

        return self.enrich_release_info(ret)

    def set_matching_formal_release(
        self, ret, formal_release, version, pre_ok, data_type="release"
    ):
        """Set the current release selection to this formal release if matching conditions."""
        if not pre_ok and formal_release["prerelease"]:
            log.info(
                "Found formal release for this tag which is unwanted "
                "pre-release: %s.",
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
        log.info(
            "Selected version as current selection: %s.", formal_release["version"]
        )
        return formal_release

    def try_get_official(self, repo):
        """Check the existence of repo/repo

        Returns:
            str: updated repo
        """
        official_repo = f"{repo}/{repo}"
        log.info("Checking existence of %s", official_repo)
        r = self.get(f"https://{self.hostname}/{official_repo}/releases.atom")
        # API requests are varied by cookie, we don't want serializer for cache fail because of that
        self.cookies.clear()
        if r.status_code == 200:
            self.feed_contents[official_repo] = r.text
            return official_repo
        return None
