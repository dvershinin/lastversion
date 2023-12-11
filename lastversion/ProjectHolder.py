# -*- coding: utf-8 -*-
import json
import logging
import os
import platform
import re

import requests
from appdirs import user_cache_dir
from cachecontrol import CacheControlAdapter
from cachecontrol.caches.file_cache import FileCache
from packaging.version import InvalidVersion

from .Version import Version
from .__about__ import __version__

# this class basically corresponds to something (often a website) which holds
# projects (usually a bunch). often this is a github-like website, so we subclass session
# but this also maybe something special, which either way can be used as a source of version
# information for a project based on its URL or name (see LocalVersionSession)
# it is instantiated with a particular project in mind/set, but also has some methods for
# stuff like searching one
from .utils import asset_does_not_belong_to_machine, ensure_directory_exists

log = logging.getLogger(__name__)


def matches_filter(filter_s, positive, version_s):
    """Check if version string matches a filter string.

    Args:
        filter_s (str):  Filter string.
        positive (bool): Whether filter is positive or negative.
        version_s (str): Version string, often a tag name.

    Returns:
        bool: True if version matches filter, False otherwise.
    """
    if not filter_s:
        return True

    if filter_s.startswith("!"):
        positive = not positive
        filter_s = filter_s[1:]
    if filter_s.startswith("~"):
        filter_s = re.compile(r"{}".format(filter_s.lstrip("~")))
        return positive == bool(re.search(filter_s, version_s))
    return positive == bool(filter_s in version_s)


class ProjectHolder(requests.Session):
    """
    Generic project holder class abstracts a web-accessible project storage.
    E.g. project on GitHub, project on Gitlab, etc.
    A project may not have a name and be identified by a hostname only.
    In that case the repo property is None.
    Either hostname and/or property have to be present
    """

    # List of odd repos where last char is part of version not beta level
    LAST_CHAR_FIX_REQUIRED_ON = []

    # web accessible project holders may have single well-known domain usable by everyone
    # in case of GitHub, that is GitHub.com, for Mercurial web gui - here isn't one, etc.
    DEFAULT_HOSTNAME = None
    SUBDOMAIN_INDICATOR = None
    # E.g. WordPress plugin directory is only one, but Gitea and GitHub can be hosted on arbitrary domains
    CAN_BE_SELF_HOSTED = False
    KNOWN_REPO_URLS = {}
    KNOWN_REPOS_BY_NAME = {}
    # e.g. owner/project, but mercurial just /project together with hostname
    # adapter array should list how many elements make up "repo", e.g. for hg.nginx.com/repo it
    # is only one instead of 2
    # or a "format" specifier for matching
    # 0 means no project name in URI (identified by hostname), 1 means project name is first component, etc.
    # True means as many as given in URI
    REPO_URL_PROJECT_COMPONENTS = 2
    # if URI starts with project name, 0. Otherwise, skip through this many URI dirs

    REPO_URL_PROJECT_OFFSET = 0
    # When project is identified by whichever URI there is (varying number of components)
    REPO_IS_URI = False
    RELEASE_URL_FORMAT = None
    SHORT_RELEASE_URL_FORMAT = None

    # Instance of project holder itself uniquely identifies a project (noname)
    REPO_IS_HOLDER = False

    @property
    def name(self):
        """Get project name, useful in URLs for assets, etc."""
        if self.repo:
            return self.repo.split("/")[-1]
        return None

    def __init__(self, name=None, hostname=None):
        super(ProjectHolder, self).__init__()

        app_name = __name__.split(".")[0]

        self.cache_dir = user_cache_dir(app_name)
        log.info("Using cache directory: %s.", self.cache_dir)
        self.cache = FileCache(self.cache_dir)
        cache_adapter = CacheControlAdapter(cache=self.cache)
        # noinspection HttpUrlsUsage
        self.mount("http://", cache_adapter)
        self.mount("https://", cache_adapter)

        self.names_cache_filename = "{}/repos.json".format(self.cache_dir)

        self.headers.update({"User-Agent": f"{app_name}/{__version__}"})
        log.info("Created instance of %s", type(self).__name__)
        self.branches = None
        self.only = None
        self.exclude = None
        self.having_asset = None
        self.hostname = hostname
        if not self.hostname and self.DEFAULT_HOSTNAME:
            self.hostname = self.DEFAULT_HOSTNAME
        # identifies project on a given hostname
        # normalize repo to number of meaningful parameters
        self.repo = self.get_base_repo_from_repo_arg(name)
        # in some case we do not specify repo, but feed is discovered, no repo is given then
        self.feed_url = None
        self.even = False
        self.formal = False

    def get_name_cache(self):
        """Return name cache from file."""
        if not os.path.exists(self.names_cache_filename):
            return {}
        try:
            with open(self.names_cache_filename, "r") as reader:
                cache = json.load(reader)
            return cache
        except (IOError, ValueError) as e:
            log.warning("Error reading cache file: %s", e)
            return {}

    def update_name_cache(self, cache_data):
        """Update name cache file with new data."""
        try:
            ensure_directory_exists(self.cache_dir)
            with open(self.names_cache_filename, "w") as writer:
                json.dump(cache_data, writer)
        except (IOError, ValueError) as e:
            log.warning("Error writing to cache file: %s", e)

    def is_instance(self):
        """Check if project holder is valid instance."""
        return False

    def set_branches(self, branches):
        """Sets project holder's branches."""
        self.branches = branches

    def set_only(self, only):
        """Sets "only" tag selector for this holder."""
        self.only = only
        if only:
            log.info('Only considering tags with "%s"', only)
        return self

    def set_exclude(self, exclude):
        """Sets "exclude" tag selector for this holder."""
        self.exclude = exclude
        if exclude:
            log.info('Only considering tags without "%s"', exclude)
        return self

    def set_even(self, even):
        """Set to return only releases with even numbering like 1.2.3."""
        self.even = even
        if even:
            log.info("Only considering releases with even numbering")
        return self

    def set_formal(self, formal):
        """Set to return only formally tagged releases."""
        self.formal = formal
        if formal:
            log.info("Only considering formally tagged releases")
        return self

    def set_having_asset(self, having_asset):
        """Sets "having_asset" selector for this holder."""
        self.having_asset = having_asset
        if having_asset:
            log.info('Only considering releases with asset "%s"', having_asset)
        return self

    @staticmethod
    def is_link(repo):
        """Check if repo is a link."""
        # noinspection HttpUrlsUsage
        return repo.startswith(("https://", "http://"))

    @classmethod
    def get_host_repo_for_link(cls, repo):
        """Return hostname and repo from a link."""
        hostname = None
        # return repo modified to result of extraction
        if cls.is_link(repo):
            # parse hostname for passing to whatever holder selected
            url_parts = repo.split("/")
            hostname = url_parts[2]
            offset = 3 + cls.REPO_URL_PROJECT_OFFSET
            repo = "/".join(
                url_parts[offset : offset + cls.REPO_URL_PROJECT_COMPONENTS]
            )
        return hostname, repo

    @classmethod
    def get_base_repo_from_repo_arg(cls, repo_arg):
        """Return meaningful URI components from a repo."""
        if cls.REPO_IS_HOLDER:
            return None
        # repo has to have enough meaningful components provided in URI
        # REPO_URL_PROJECT_COMPONENTS = 2
        # if URI starts with project name, 0. Otherwise, skip through this many URI dirs
        # REPO_URL_PROJECT_OFFSET = 0
        # if is an empty string but we want some, raise value error
        # holder defined arbitrary number of URI components, zero or unlimited
        if cls.REPO_IS_URI:
            return repo_arg
        if not repo_arg and cls.REPO_URL_PROJECT_COMPONENTS > 0:
            raise ValueError(
                f"Repo arg {repo_arg} does not have enouh URI components ({cls.REPO_URL_PROJECT_COMPONENTS}) for {cls.__name__}"
            )
        if cls.REPO_URL_PROJECT_COMPONENTS >= 1:
            repo_components = repo_arg.split("/")
            if repo_arg and len(repo_components) == cls.REPO_URL_PROJECT_COMPONENTS:
                return repo_arg
            # if class has "find_repo_by_name_only" method, OK to have only one
            if len(repo_components) == 1 and hasattr(cls, "find_repo_by_name_only"):
                return repo_arg
            if len(repo_components) < cls.REPO_URL_PROJECT_COMPONENTS:
                raise ValueError(
                    f"Repo arg {repo_arg} does not have enough components for {cls.__name__}"
                )
            return "/".join(
                repo_components[
                    cls.REPO_URL_PROJECT_OFFSET : cls.REPO_URL_PROJECT_OFFSET
                    + cls.REPO_URL_PROJECT_COMPONENTS
                ]
            )
        return None

    @classmethod
    def is_official_for_repo(cls, repo, hostname):
        """Check if repo is a known repo for this type of project holder."""
        if hostname and hostname in cls.KNOWN_REPO_URLS:
            log.info("Selecting known repo %s", hostname)
            return cls.KNOWN_REPO_URLS[hostname]
        if repo and repo.lower() in cls.KNOWN_REPOS_BY_NAME:
            log.info("Selecting known repo %s", repo)
            return cls.KNOWN_REPOS_BY_NAME[repo.lower()]
        return False

    @classmethod
    def is_matching_hostname(cls, hostname):
        """Check if given hostname matches to the project hosting's domains."""
        if not hostname:
            return None
        # Hosting does not have domains defined
        if not cls.DEFAULT_HOSTNAME and not cls.SUBDOMAIN_INDICATOR:
            return False
        if cls.DEFAULT_HOSTNAME == hostname:
            return True
        if cls.SUBDOMAIN_INDICATOR and hostname.startswith(
            cls.SUBDOMAIN_INDICATOR + "."
        ):
            return True
        return False

    def matches_major_filter(self, version, major):
        if (
            self.branches
            and major in self.branches
            and re.search(rf"{self.branches[major]}", str(version))
        ):
            log.info("%s matches major %s", version, self.branches[major])
            return True
        if str(version).startswith(f"{major}."):
            log.info("%s is under the desired major %s", version, major)
            return True
        if str(version) == major:
            return True
        return False

    def sanitize_version(self, version_s, pre_ok=False, major=None):
        """
        Extract a version from tag name; that satisfies this holder's filters, etc.

        Returns:
            Version or None: The return value can be a Version object or None.
        """
        log.info("Sanitizing string %s as a satisfying version.", version_s)

        # for libssh2-x.x.x should remove project name prefix to prevent `2` going into the version
        prefix = "{}-".format(self.name)
        if version_s.startswith(prefix):
            version_s = version_s[len(prefix) :]
            log.info(
                "Removed project name prefix, working now on string '%s'", version_s
            )

        res = None

        if not matches_filter(self.only, True, version_s):
            log.info(
                '"%s" does not match the "only" constraint "%s"', version_s, self.only
            )
            return None

        if not matches_filter(self.exclude, False, version_s):
            log.info(
                '"%s" does not match the "exclude" constraint "%s"',
                version_s,
                self.exclude,
            )
            return None

        try:
            char_fix_required = self.repo in self.LAST_CHAR_FIX_REQUIRED_ON
            v = Version(version_s, char_fix_required=char_fix_required)
            if not v.is_prerelease or pre_ok:
                log.info("Parsed as Version OK. String representation: %s.", v)
                res = v
            else:
                log.info("Parsed as unwanted pre-release version: %s.", v)
        except InvalidVersion:
            log.info("Failed to parse %s as Version.", version_s)
            # attempt to remove extraneous chars and revalidate
            # we use findall for cases where "tag" may be 'foo/2.x/2.45'
            matches = re.findall(r"([0-9]+([.][0-9x]+)+(rc[0-9]?)?)", version_s)
            for s in matches:
                version_s = s[0]
                log.info("Sanitized tag name value to %s.", version_s)
                # now we may have gotten a non-version like 2.x, so let's try to parse it
                try:
                    res = Version(version_s)
                except InvalidVersion:
                    log.info("Failed to parse %s as Version.", version_s)
                    continue
                if res:
                    # Satisfy on the first matched version-like string, e.g. 5.2.6-3.12
                    break
            if not matches:
                log.info("Did not find anything that looks like a version in the tag")
                # As the last resort, let's try to convert underscores to dots, while stripping out
                # any "alphanumeric_". many hg repos do this, e.g. PROJECT_1_2_3
                parts = version_s.split("_")
                if len(parts) >= 2 and parts[0].isalpha():
                    # gets list except first item, joins by dot
                    version_s = ".".join(parts[1:])
                    try:
                        v = Version(version_s)
                        if not v.is_prerelease or pre_ok:
                            log.info("Parsed as Version OK")
                            log.info("String representation of version is %s.", v)
                            res = v
                        else:
                            log.info("Parsed as unwanted pre-release version: %s.", v)
                    except InvalidVersion:
                        log.info(
                            "Still not a valid version after applying underscores fix"
                        )
        # apply --major filter
        if res and major and not self.matches_major_filter(res, major):
            log.info("%s is not under the desired major %s", version_s, major)
            return None

        if res and self.even and not res.even:
            return None

        return res

    def _type(self):
        """Get project holder's class name."""
        return self.__class__.__name__

    def release_download_url(self, release, shorter=False):
        """Get release download URL."""
        if not self.RELEASE_URL_FORMAT:
            log.warning("Getting release URL for %s is not implemented", self._type())
            return None
        ext = "zip" if os.name == "nt" else "tar.gz"

        fmt = (
            self.SHORT_RELEASE_URL_FORMAT
            if shorter and self.SHORT_RELEASE_URL_FORMAT
            else self.RELEASE_URL_FORMAT
        )

        return fmt.format(
            hostname=self.hostname,
            repo=self.repo,
            name=self.name,
            tag=release["tag_name"],
            ext=ext,
            version=release["version"],
        )

    def get_assets(self, release, short_urls, assets_filter=None):
        urls = []
        assets = release.get("assets", [])
        arch_matched_assets = []
        if not assets_filter and platform.machine() in ["x86_64", "AMD64"]:
            for asset in assets:
                if "x86_64" in asset["name"]:
                    arch_matched_assets.append(asset)
            if arch_matched_assets:
                assets = arch_matched_assets

        if assets:
            for asset in assets:
                if assets_filter and not re.search(assets_filter, asset["name"]):
                    continue
                if not assets_filter and asset_does_not_belong_to_machine(
                    asset["name"]
                ):
                    log.info(
                        "Asset %s does not belong to this machine, skipping",
                        asset["name"],
                    )
                    continue
                urls.append(asset["browser_download_url"])
        else:
            download_url = self.release_download_url(release, short_urls)
            if not assets_filter or re.search(assets_filter, download_url):
                urls.append(download_url)
        return urls

    def get_canonical_link(self):
        if self.feed_url:
            return self.feed_url
        return f"https://{self.hostname}/{self.repo}"
