"""A module to represent an Alpine Linux package repository holder."""

import io
import logging
import re
import tarfile

from lastversion.repo_holders.base import BaseProjectHolder
from lastversion.version import Version

log = logging.getLogger(__name__)


class AlpineRepoSession(BaseProjectHolder):
    """A class to represent an Alpine Linux package repository holder."""

    DEFAULT_HOSTNAME = "pkgs.alpinelinux.org"
    CDN_HOSTNAME = "dl-cdn.alpinelinux.org"
    REPO_URL_PROJECT_COMPONENTS = 1
    # URL format: /package/v3.21/main/x86_64/nginx
    REPO_URL_PROJECT_OFFSET = 4

    DEFAULT_BRANCH = "edge"
    DEFAULT_ARCH = "x86_64"
    REPOS = ["main", "community"]

    def __init__(self, repo, hostname=None):
        super().__init__(repo, hostname)
        self.hostname = hostname or self.DEFAULT_HOSTNAME
        self.branch = self.DEFAULT_BRANCH
        self.arch = self.DEFAULT_ARCH
        self.apk_repo = None  # Will be set when package is found
        self.project = None

        # Try to find the package in Alpine repositories
        # This runs both for URL-based (hostname=DEFAULT_HOSTNAME) and
        # explicit --at alpine (hostname=None -> set to DEFAULT_HOSTNAME)
        if self.repo:
            self._try_find_package()

    def _try_find_package(self):
        """Try to find the package in Alpine repositories."""
        if not self.repo:
            return
        for apk_repo in self.REPOS:
            pkg_info = self._fetch_package_from_index(self.branch, apk_repo, self.arch)
            if pkg_info:
                self.project = pkg_info
                self.apk_repo = apk_repo
                log.info("Found package %s in %s/%s", self.repo, self.branch, apk_repo)
                break

    def _get_apkindex_url(self, branch, apk_repo, arch):
        """Construct URL for APKINDEX.tar.gz."""
        # Branches in URLs use 'v' prefix for versioned branches
        branch_path = branch if branch == "edge" else f"v{branch}"
        return f"https://{self.CDN_HOSTNAME}/alpine/{branch_path}/{apk_repo}/{arch}/APKINDEX.tar.gz"

    def _parse_apkindex(self, content):
        """Parse APKINDEX content and return dict of packages.

        APKINDEX format:
        P:package_name
        V:version
        A:arch
        ...
        (blank line separates entries)
        """
        packages = {}
        current_pkg = {}

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                # End of package entry
                if "P" in current_pkg and "V" in current_pkg:
                    packages[current_pkg["P"]] = current_pkg
                current_pkg = {}
                continue

            if ":" in line:
                key, value = line.split(":", 1)
                current_pkg[key] = value

        # Handle last entry if no trailing newline
        if "P" in current_pkg and "V" in current_pkg:
            packages[current_pkg["P"]] = current_pkg

        return packages

    def _fetch_package_from_index(self, branch, apk_repo, arch):
        """Fetch and parse APKINDEX to find package info."""
        url = self._get_apkindex_url(branch, apk_repo, arch)
        log.info("Fetching APKINDEX from %s", url)

        try:
            response = self.get(url)
            if response.status_code != 200:
                log.debug("Failed to fetch APKINDEX from %s: %s", url, response.status_code)
                return None

            # APKINDEX is a tar.gz containing an APKINDEX file
            tar_bytes = io.BytesIO(response.content)
            with tarfile.open(fileobj=tar_bytes, mode="r:gz") as tar:
                for member in tar.getmembers():
                    if member.name == "APKINDEX":
                        file_obj = tar.extractfile(member)
                        if file_obj:
                            content = file_obj.read().decode("utf-8")
                            packages = self._parse_apkindex(content)
                            if self.repo in packages:
                                return packages[self.repo]
        except (OSError, tarfile.TarError, UnicodeDecodeError) as e:
            log.debug("Error fetching/parsing APKINDEX: %s", e)
            return None

        return None

    def is_instance(self):
        """Check if this holder has a valid project."""
        return self.project is not None

    def get_latest(self, pre_ok=False, major=None):  # noqa: ARG002  # pylint: disable=unused-argument
        """Get the latest release for this package.

        Args:
            pre_ok: Whether pre-releases are acceptable (not used for Alpine).
            major: Alpine branch version (e.g., "3.21"). Defaults to "edge".
        """
        # If major is specified, use it as the branch
        if major:
            self.branch = str(major)
            # Re-fetch with the specified branch
            self.project = None
            self.apk_repo = None
            for apk_repo in self.REPOS:
                pkg_info = self._fetch_package_from_index(self.branch, apk_repo, self.arch)
                if pkg_info:
                    self.project = pkg_info
                    self.apk_repo = apk_repo
                    break

        if not self.project:
            log.warning("Package %s not found in Alpine repositories", self.repo)
            return None

        # Alpine version format: 1.26.3-r0
        version_str = self.project.get("V", "")
        if not version_str:
            return None

        # Parse version - Alpine uses format like "1.26.3-r0"
        # We need to handle the -rN suffix specially
        try:
            v = Version(version_str)
        except (ValueError, TypeError):
            # Try to extract just the version part before -r
            match = re.match(r"^([\d.]+)", version_str)
            if match:
                v = Version(match.group(1))
            else:
                log.warning("Could not parse version: %s", version_str)
                return None

        ret = {
            "version": v,
            "tag_name": version_str,
            "description": self.project.get("T", ""),
            "url": self.project.get("U", ""),
            "license": self.project.get("L", ""),
            "maintainer": self.project.get("m", ""),
            "arch": self.project.get("A", self.arch),
            "alpine_branch": self.branch,
            "alpine_repo": self.apk_repo,
        }

        return ret

    def release_download_url(self, release, shorter=False):  # noqa: ARG002  # pylint: disable=unused-argument
        """Get release download URL for the package.

        Alpine packages are downloaded as .apk files from the CDN.
        """
        if not self.project:
            return None

        version = release.get("tag_name", "")
        arch = release.get("arch", self.arch)
        branch_path = self.branch if self.branch == "edge" else f"v{self.branch}"

        return f"https://{self.CDN_HOSTNAME}/alpine/{branch_path}/{self.apk_repo}/{arch}/{self.repo}-{version}.apk"

    @staticmethod
    def make_canonical_link(repo):
        """Make canonical link for a package."""
        return f"https://{AlpineRepoSession.DEFAULT_HOSTNAME}/packages?name={repo}&branch=edge"

    def get_canonical_link(self):
        """Get the canonical link for this package."""
        branch_path = self.branch if self.branch == "edge" else f"v{self.branch}"
        apk_repo = self.apk_repo or "main"
        return f"https://{self.DEFAULT_HOSTNAME}/package/{branch_path}/{apk_repo}/{self.arch}/{self.repo}"
