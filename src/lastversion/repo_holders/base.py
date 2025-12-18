"""The base project holder class."""

import datetime
import json
import logging
import os
import platform
import re
import time

import feedparser
import requests
from cachecontrol import CacheControlAdapter
from cachecontrol.caches.file_cache import FileCache
from packaging.version import InvalidVersion

from lastversion.__about__ import __version__
from lastversion.config import get_config

# This class basically corresponds to something (often a website) which holds
# projects (usually a bunch). Often this is a github-like website, so we subclass session
# but this also maybe something special, which either way can be used as a source of version
# information for a project based on its URL or name (see LocalVersionSession)
# it is instantiated with a particular project in mind/set, but also has some methods for
# stuff like searching one
from lastversion.utils import asset_does_not_belong_to_machine, ensure_directory_exists
from lastversion.version import Version

log = logging.getLogger(__name__)


def _safe_open_write(filename, fmode):
    """Open a file for secure write, mirroring CacheControl's behavior without
    relying on its private API.
    """
    flags = os.O_WRONLY
    flags |= os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        os.remove(filename)
    except (IOError, OSError):
        pass
    fd = os.open(filename, flags, fmode)
    try:
        return os.fdopen(fd, "wb")
    except Exception:
        os.close(fd)
        raise


class LockAcquireTimeout(Exception):
    """Raised when an internal lock cannot be acquired within timeout."""


class InternalTimedDirLock:
    """Simple directory-based lock with timeout, no external dependencies.

    This lock attempts to `mkdir` a lock directory next to the target file path.
    Creation is atomic across processes. It retries until the timeout is reached.
    """

    def __init__(self, path, threaded=True, timeout=None):
        # `path` is the target data file path to be protected
        self.path = path
        self._lock_path = f"{path}.lock"
        self._timeout = 5 if timeout is None else timeout

    def __enter__(self):
        deadline = time.time() + self._timeout
        while True:
            try:
                os.mkdir(self._lock_path)
                break
            except FileExistsError:
                if time.time() >= deadline:
                    raise LockAcquireTimeout(f"Failed to acquire lock for {self.path}")
                time.sleep(0.1)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            os.rmdir(self._lock_path)
        except Exception:
            pass
        return False


class SafeFileCache(FileCache):
    """FileCache that avoids hanging on lock acquisition by timing out and
    skipping cache writes on lock errors.
    """

    def _write(self, path, data: bytes):
        # Ensure directory exists
        try:
            os.makedirs(os.path.dirname(path), self.dirmode)
        except (IOError, OSError):
            pass

        try:
            with self.lock_class(path) as lock:
                with _safe_open_write(lock.path, self.filemode) as fh:
                    fh.write(data)
        except LockAcquireTimeout as exc:
            # Do not fail requests on cache lock issues; just skip caching
            log.debug("Cache write skipped due to lock error: %s", exc)


def matches_filter(filter_s, positive, version_s):
    """Check if a version string matches a filter string.

    Args:
        filter_s (str): Filter string.
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
        filter_s = re.compile(rf"{filter_s.lstrip('~')}")
        return positive == bool(re.search(filter_s, version_s))
    return positive == bool(filter_s in version_s)


class BaseProjectHolder(requests.Session):
    """
    Generic project holder class abstracts a web-accessible project storage.
    E.g., project on GitHub, project on Gitlab, etc.
    A project may not have a name and be identified by a hostname only.
    In that case, the repo property is None.
    Either hostname and/or property have to be present
    """

    # List of odd repos where last char is part of version not beta level
    LAST_CHAR_FIX_REQUIRED_ON = []

    # web-accessible project holders may have a single well-known domain usable by everyone
    # in case of GitHub, that is GitHub.com, for Mercurial web gui - here isn't one, etc.
    DEFAULT_HOSTNAME = None
    SUBDOMAIN_INDICATOR = None
    # E.g., WordPress plugin directory is only one, but Gitea and GitHub can be hosted on arbitrary domains
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
    # If URI starts with project name, 0. Otherwise, skip through this many URI dirs

    REPO_URL_PROJECT_OFFSET = 0
    # When a project is identified by whichever URI there is (varying number of components)
    REPO_IS_URI = False
    RELEASE_URL_FORMAT = None
    SHORT_RELEASE_URL_FORMAT = None

    # Instance of project holder itself uniquely identifies a project (noname)
    REPO_IS_HOLDER = False
    DEFAULT_TIMEOUT = 30  # default timeout in seconds

    CACHE_DISABLED = False

    # Conventional changelog file candidates to try at a tag
    CHANGELOG_CANDIDATES = [
        "CHANGELOG.md",
        "CHANGELOG",
        "CHANGES.md",
        "CHANGES",
        "NEWS.md",
        "NEWS",
        "docs/CHANGELOG.md",
        "docs/CHANGES.md",
        "docs/NEWS.md",
    ]

    def repo_changelog(self, tag):
        """Default: no changelog retrieval; subclasses may override."""
        return None

    def repo_changelog_path(self, tag):
        """Default: no changelog path; subclasses may override to return (text, path)."""
        return None, None

    def collect_release_notes(self, tag, release):
        """Collect release notes text and provenance.

        Returns:
            (text, source): text string or None; source is 'release_body' or a filename path
        """
        try:
            text = release.get("body") or release.get("description")
            if text:
                return text, "release_body"
            text, path = self.repo_changelog_path(tag)
            if text:
                return text, path
        except Exception:
            return None, None
        return None, None

    @property
    def name(self):
        """Get project name, useful in URLs for assets, etc."""
        if self.repo:
            return self.repo.split("/")[-1]
        return None

    def __init__(self, name=None, hostname=None):
        super().__init__()
        self.mount("https://", requests.adapters.HTTPAdapter(max_retries=5))
        app_name = __name__.split(".", maxsplit=1)[0]

        # Load configuration
        config = get_config()

        self.cache_dir = None
        self.cache = None
        if not self.CACHE_DISABLED:
            # Use configured cache path or default
            self.cache_dir = config.file_cache_path
            log.info("Using cache directory: %s.", self.cache_dir)
            # Use a lock with a finite timeout to avoid rare hangs on cache writes
            lock_cls = InternalTimedDirLock
            self.cache = SafeFileCache(self.cache_dir, lock_class=lock_cls)
            cache_adapter = CacheControlAdapter(cache=self.cache)
            # noinspection HttpUrlsUsage
            self.mount("http://", cache_adapter)
            self.mount("https://", cache_adapter)
        else:
            log.info("Cache is disabled for this holder.")
            # Still need cache_dir for names_cache_filename even if HTTP cache is disabled
            self.cache_dir = config.file_cache_path

        self.names_cache_filename = f"{self.cache_dir}/repos.json"

        self.user_agent = f"{app_name}/{__version__}"
        self.headers.update({"User-Agent": self.user_agent})
        log.info("Created instance of %s", type(self).__name__)
        self.branches = None
        self.only = None
        self.exclude = None
        self.having_asset = None
        self.hostname = hostname
        if not self.hostname and self.DEFAULT_HOSTNAME:
            self.hostname = self.DEFAULT_HOSTNAME
        # identifies a project on a given hostname
        # normalize repo to number of meaningful parameters
        self.repo = self.get_base_repo_from_repo_arg(name)
        # in some case we do not specify repo, but feed is discovered; no repo is given then
        self.feed_url = None
        self.even = False
        self.formal = False

    def request(self, *args, **kwargs):
        """Set default timeout for requests."""
        kwargs.setdefault("timeout", self.DEFAULT_TIMEOUT)
        return super().request(*args, **kwargs)

    def get_name_cache(self):
        """Return name cache from file."""
        if self.CACHE_DISABLED or not os.path.exists(self.names_cache_filename):
            return {}
        try:
            with open(self.names_cache_filename, "r", encoding="utf-8") as reader:
                cache = json.load(reader)
            return cache
        except (IOError, ValueError) as e:
            log.warning("Error reading cache file: %s", e)
            return {}

    def update_name_cache(self, cache_data):
        """Update name cache file with new data."""
        if self.CACHE_DISABLED:
            return
        try:
            ensure_directory_exists(self.cache_dir)
            with open(self.names_cache_filename, "w", encoding="utf-8") as writer:
                json.dump(cache_data, writer)
        except (IOError, ValueError) as e:
            log.warning("Error writing to cache file: %s", e)

    @classmethod
    def clear_cache(cls, repo=None):
        """Clear the HTTP cache and release data cache.

        Args:
            repo: Optional repo identifier. If provided, clears cache only for
                  URLs containing this repo. If None, clears all cache.

        Returns:
            int: Number of cache entries cleared
        """
        from lastversion.cache import get_release_cache

        config = get_config()
        cache_dir = config.file_cache_path

        if not os.path.exists(cache_dir):
            log.info("Cache directory does not exist: %s", cache_dir)
            return 0

        cleared = 0

        # Clear release data cache
        release_cache = get_release_cache()
        if repo:
            # Clear release cache for specific repo
            release_cache.delete(repo)
        else:
            cleared += release_cache.clear()

        if repo:
            # Clear cache entries for specific repo
            # CacheControl uses URL-based filenames, so we need to find and remove
            # files that match the repo pattern
            from urllib.parse import quote

            # Common URL patterns for the repo
            repo_patterns = [
                f"/{repo}/",
                f"/{repo}.",
                f"/{quote(repo, safe='')}/",
            ]

            for root, dirs, files in os.walk(cache_dir):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    # Read the cached URL from the file or use filename heuristics
                    try:
                        # CacheControl stores URL hash as filename
                        # We can't easily reverse the hash, so we delete based on
                        # modification time (recent files for this repo)
                        # A more thorough approach: delete all and let it re-cache
                        if any(pattern in str(filepath) for pattern in repo_patterns):
                            os.remove(filepath)
                            cleared += 1
                    except (IOError, OSError):
                        pass

            # Also clear from names cache
            names_cache_file = os.path.join(cache_dir, "repos.json")
            if os.path.exists(names_cache_file):
                try:
                    with open(names_cache_file, "r", encoding="utf-8") as f:
                        names_cache = json.load(f)
                    # Remove entries matching the repo
                    repo_lower = repo.lower()
                    keys_to_remove = [
                        k
                        for k in names_cache
                        if repo_lower in k.lower() or (names_cache[k].get("repo", "").lower() == repo_lower)
                    ]
                    for key in keys_to_remove:
                        del names_cache[key]
                        cleared += 1
                    with open(names_cache_file, "w", encoding="utf-8") as f:
                        json.dump(names_cache, f)
                except (IOError, ValueError, json.JSONDecodeError):
                    pass

            log.info("Cleared %d cache entries for repo: %s", cleared, repo)
        else:
            # Clear all cache
            import shutil

            try:
                shutil.rmtree(cache_dir)
                log.info("Cleared all cache from: %s", cache_dir)
                cleared += 1  # Indicate success
            except (IOError, OSError) as e:
                log.warning("Error clearing cache: %s", e)

        return cleared

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
            repo = "/".join(url_parts[offset : offset + cls.REPO_URL_PROJECT_COMPONENTS])
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
                f"Repo arg {repo_arg} does not have enough URI components ({cls.REPO_URL_PROJECT_COMPONENTS}) for {cls.__name__}"
            )
        if cls.REPO_URL_PROJECT_COMPONENTS >= 1:
            repo_components = repo_arg.split("/")
            if repo_arg and len(repo_components) == cls.REPO_URL_PROJECT_COMPONENTS:
                return repo_arg
            # if a class has "find_repo_by_name_only" method, OK to have only one
            if len(repo_components) == 1 and hasattr(cls, "find_repo_by_name_only"):
                return repo_arg
            if len(repo_components) < cls.REPO_URL_PROJECT_COMPONENTS:
                raise ValueError(f"Repo arg {repo_arg} does not have enough components for {cls.__name__}")
            return "/".join(
                repo_components[
                    cls.REPO_URL_PROJECT_OFFSET : cls.REPO_URL_PROJECT_OFFSET + cls.REPO_URL_PROJECT_COMPONENTS
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
        """Check if given hostname matches to the project hosting's domains.

        Args:
            hostname: May include port (netloc format) for non-standard ports.
        """
        if not hostname:
            return None
        # Hosting does not have domains defined
        if not cls.DEFAULT_HOSTNAME and not cls.SUBDOMAIN_INDICATOR:
            return False
        # Extract hostname without port for comparison
        hostname_only = hostname.rsplit(":", 1)[0] if ":" in hostname else hostname
        if cls.DEFAULT_HOSTNAME == hostname_only:
            return True
        if cls.SUBDOMAIN_INDICATOR and hostname_only.startswith(cls.SUBDOMAIN_INDICATOR + "."):
            return True
        return False

    def matches_major_filter(self, version, major):
        """Check if version matches major filter."""
        if self.branches and major in self.branches and re.search(rf"{self.branches[major]}", str(version)):
            log.info("%s matches major %s", version, self.branches[major])
            return True
        if str(version).startswith(f"{major}."):
            log.info("%s is under the desired major %s", version, major)
            return True
        if str(version) == major:
            return True
        return False

    def remove_prefix(self, version_s):
        """Remove project name prefix from version string."""
        prefixes = (f"{self.name}-", f"{self.name}_")
        for prefix in prefixes:
            if version_s.startswith(prefix):
                version_s = version_s[len(prefix) :]
                log.info(
                    "Removed project name prefix '%s', working now on string '%s'",
                    prefix,
                    version_s,
                )
                break
        return version_s

    def sanitize_version(self, version_s, pre_ok=False, major=None):
        """
        Extract a version from tag name; that satisfies this holder's filters, etc.

        Returns:
            Version or None: The return value can be a Version object or None.
        """
        log.info("Sanitizing string %s as a satisfying version.", version_s)

        # for `libssh2-x.x.x` should remove project name prefix to prevent `2` going into the version
        version_s = self.remove_prefix(version_s)

        res = None

        if not matches_filter(self.only, True, version_s):
            log.info('"%s" does not match the "only" constraint "%s"', version_s, self.only)
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
            matches = re.findall(re.compile(r"(\d+([.][0-9x]+)+(rc\d?)?)"), version_s)
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
                    # Satisfy on the first matched version-like string, e.g., 5.2.6-3.12
                    break
            if not matches:
                log.info("Did not find anything that looks like a version in the tag")
                # As the last resort, let's try to convert underscores to dots, while stripping out
                # any "alphanumeric_". Many hg repos do this, e.g. PROJECT_1_2_3
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
                        log.info("Still not a valid version after applying underscores fix")
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
            if (shorter or "/" in release["tag_name"]) and self.SHORT_RELEASE_URL_FORMAT
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
        """Get assets for a given release."""
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
                if not assets_filter and asset_does_not_belong_to_machine(asset["name"]):
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

    def get_assets_with_digests(self, release, short_urls, assets_filter=None):
        """Get assets with digest information for a given release.

        Returns a list of dicts with url, name, size, and digest (if available).
        This provides more detailed asset info for JSON output.
        """
        result = []
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
                if not assets_filter and asset_does_not_belong_to_machine(asset["name"]):
                    log.info(
                        "Asset %s does not belong to this machine, skipping",
                        asset["name"],
                    )
                    continue
                asset_info = {
                    "url": asset.get("browser_download_url"),
                    "name": asset.get("name"),
                    "size": asset.get("size"),
                }
                # Include digest if available (GitHub provides this since June 2025)
                if asset.get("digest"):
                    asset_info["digest"] = asset["digest"]
                result.append(asset_info)
        else:
            download_url = self.release_download_url(release, short_urls)
            if not assets_filter or re.search(assets_filter, download_url):
                result.append({"url": download_url, "name": None, "size": None})
        return result

    def get_canonical_link(self):
        """Get the canonical link for a project."""
        if self.feed_url:
            return self.feed_url
        return f"https://{self.hostname}/{self.repo}"

    def get_feed_response(self, url):
        """
        Get feed response.
        Ensures that the same `Accept` header is used for all feed requests.
        Clears cookies after request to ensure cache-ability of further requests.
        """
        headers = {
            "Accept": "*/*",
            # private repos do not have releases.atom to begin with,
            # authorization header may cause a false positive 200 response with an empty feed!
            "Authorization": "",
        }
        response = self.get(url, headers=headers)
        # API requests are varied by cookie, we don't want serializer for cache fail because of that
        self.cookies.clear()
        return response

    def find_release_in_feed(self, url, pre_ok=False, major=None):
        """
        Find release in feed.
        To leverage cachecontrol, we fetch the feed using requests as usual,
        then supply its text to feedparser as a raw string
        """
        ret = {}
        log.debug("Requesting %s", url)
        r = self.get(url)
        feed = feedparser.parse(r.text)
        for tag in feed.entries:
            tag_name = tag["title"]
            version = self.sanitize_version(tag_name, pre_ok, major)
            if not version:
                continue
            if not ret or version > ret["version"]:
                ret = tag
                tag["tag_name"] = tag["title"]
                tag["version"] = version
                # converting from struct
                tag["tag_date"] = datetime.datetime(*tag["published_parsed"][:6])
        return ret or None
