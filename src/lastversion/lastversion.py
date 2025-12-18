# -*- coding: utf-8 -*-
# License: BSD, see LICENSE for more details.
"""
This is the main module of lastversion package.
To use it, import it and invoke any function documented here. For example:

```python
from lastversion import lastversion
lastversion.has_update(repo='mautic/mautic', current_version='1.2.3')
```
"""

import argparse
import logging
import os
import re
import shlex
import sys
from os.path import expanduser
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml
from packaging.version import InvalidVersion

from lastversion.ai import generate_changelog
from lastversion.cache import get_release_cache
from lastversion.exceptions import ApiCredentialsError
from lastversion.holder_factory import HolderFactory
from lastversion.repo_holders.test import TestProjectHolder
from lastversion.spdx_id_to_rpmspec import rpmspec_licenses
from lastversion.utils import download_file, extract_appimage_desktop_file, rpm_installed_version
from lastversion.version import Version

log = logging.getLogger(__name__)
FAILS_SEM_ERR_FMT = "Latest version %s fails semantic %s constraint against current version %s"


# noinspection GrazieInspection
def find_preferred_url(spec_urls):
    """
    Given a list of URLs of a project, return preferred one that might lead to version info.
    Basically returns the first URL that matches a handler by matching its primary domain.
    """
    # TODO: use rpmspec --parse if failed to get lastversion_repo inside spec (includes macro)
    for url in spec_urls:
        # parse URL and get domain
        parsed = urlparse(url)
        hostname = parsed.hostname
        # enumerate holders, and see if any of them can handle this domain
        for holder in HolderFactory.HOLDERS.values():
            if holder.DEFAULT_HOSTNAME and holder.DEFAULT_HOSTNAME == hostname:
                return url
    return spec_urls[0] if spec_urls else None


def get_repo_data_from_spec(rpmspec_filename):
    """
    Extracts repo data and CLI args from .spec file

    The project (repo) is specified inside the .spec file
    GitHub repo is resolved via %{upstream_github} + %{name}/%{upstream_name}
    No upstream_github global means that the spec was not prepared for lastversion
    Optional: use of spec_tag macros if the source is from GitHub. In edge cases we check
    new version via GitHub, but prepared sources are elsewhere

    Args:
        rpmspec_filename:

    Returns:

    """
    repo_data = {}
    with open(rpmspec_filename) as f:
        name = None
        upstream_github = None
        upstream_name = None
        current_version = None
        spec_repo = None
        spec_urls = []
        current_commit = None
        for line in f.readlines():
            if line.startswith("%global lastversion_repo"):
                spec_repo = shlex.split(line)[2].strip()
            elif line.startswith("%global upstream_github"):
                upstream_github = shlex.split(line)[2].strip()
            elif line.startswith("%global upstream_name"):
                upstream_name = shlex.split(line)[2].strip()
            elif line.startswith("%global commit "):
                # Commit-based release (snapshots)
                current_commit = shlex.split(line)[2].strip()
                repo_data["commit_based"] = True
            elif line.startswith("Name:"):
                name = line.split("Name:")[1].strip()
            elif line.startswith("URL:"):
                # append to spec_urls
                spec_urls.append(line.split("URL:")[1].strip())
            elif line.startswith("Source0:"):
                source0 = line.split("Source0:")[1].strip()
                # noinspection HttpUrlsUsage
                if source0.startswith("https://") or source0.startswith("http://"):
                    spec_urls.append(source0)
            elif line.startswith("%global upstream_version "):
                current_version = shlex.split(line)[2].strip()
                # influences %spec_tag to use %upstream_version instead of %version
                repo_data["module_of"] = True
            elif line.startswith("Version:") and not current_version:
                current_version = line.split("Version:")[1].strip()
            elif line.startswith("%global lastversion_only"):
                repo_data["only"] = shlex.split(line)[2].strip()
            elif line.startswith("%global lastversion_having_asset"):
                repo_data["having_asset"] = shlex.split(line)[2].strip()
            elif line.startswith("%global lastversion_major"):
                repo_data["major"] = shlex.split(line)[2].strip()
            elif line.startswith("%global lastversion_formal"):
                value = shlex.split(line)[2].strip()
                low = value.lower()
                if low in ["1", "true", "yes", "on"]:
                    repo_data["formal"] = True
                elif low in ["0", "false", "no", "off"]:
                    repo_data["formal"] = False
                else:
                    # Any non-empty string defaults to True for safety
                    repo_data["formal"] = bool(value)
            elif line.startswith("%global lastversion_sem"):
                # Semver constraint: major, minor, or patch
                value = shlex.split(line)[2].strip().lower()
                if value in ["major", "minor", "patch"]:
                    repo_data["sem"] = value

        # Store current commit for comparison
        if current_commit:
            repo_data["current_commit"] = current_commit

        if not current_version:
            log.critical("Did not find neither Version: nor %upstream_version in the spec file")
            sys.exit(1)
        try:
            if current_version != "x":
                repo_data["current_version"] = Version(current_version)
        except InvalidVersion:
            log.critical(
                "Failed to parse current version in %s. Tried %s",
                rpmspec_filename,
                current_version,
            )
            sys.exit(1)
        if upstream_name:
            repo_data["name"] = upstream_name
            repo_data["spec_name"] = "%{upstream_name}"
        else:
            repo_data["name"] = name
            repo_data["spec_name"] = "%{name}"

        if upstream_github:
            repo = f"{upstream_github}/{repo_data['name']}"
            log.info("Discovered GitHub repo %s from .spec file", repo)
        elif spec_repo:
            repo = spec_repo
            log.info("Discovered explicit repo %s from .spec file", repo)
        else:
            repo = find_preferred_url(spec_urls)

        if not repo:
            log.critical(
                "Failed to determine repo from %s. Please prepare your spec file using instructions: "
                "https://lastversion.getpagespeed.com/spec-preparing.html",
                rpmspec_filename,
            )
            sys.exit(1)

        repo_data["repo"] = repo
        return repo_data


def get_repo_data_from_yml(repo):
    """Get repo data from YAML file."""
    with open(repo) as fpi:
        repo_data = yaml.safe_load(fpi)
        if "repo" in repo_data:
            if "nginx-extras" in repo:
                repo_data["module_of"] = "nginx"
            name = os.path.splitext(os.path.basename(repo))[0]
            if "module_of" in repo_data:
                name = f'{repo_data["module_of"]}-module-{name}'
            repo_data["name"] = name
    return repo_data


def latest(
    repo,
    output_format="version",
    pre_ok=False,
    assets_filter=None,
    short_urls=False,
    major=None,
    only=None,
    at=None,
    having_asset=None,
    exclude=None,
    even=False,
    formal=False,
    changelog=False,
    cache_ttl=None,
):
    r"""Find the latest release version for a project.

    Args:
        major (str): Only consider versions which are "descendants" of this
          major version string
        short_urls (bool): Whether we should try to return shorter URLs for
          release data
        assets_filter (Union[str, Pattern]): Regular expression for filtering
          assets for the latest release
        only (str): Only consider tags with this text. Useful for repos with multiple projects.
                    The argument supports negation and regular expressions. To indicate a regex,
                    start it with tilde sign, to negate the expression, start it with exclamation
                    point. See `Examples`.
        repo (str): Repository specifier in any form.
        output_format (str): Affects the return format. Possible values `version`, `json`, `dict`,
                             `assets`, `source`, `tag`.
        pre_ok (bool): Specifies whether pre-releases can be accepted as a newer version.
        at (str): Specifies repo hosting more precisely, only useful if repo argument was
                  specified as one word.
        having_asset (Union[str, bool]): Only consider releases with the given asset.
                                         Pass `True` for any asset
        exclude (str): Only consider releases NOT containing this text/regular expression.
        even (bool): Consider as stable only releases with even minor component, e.g. 1.2.3
        formal (bool): Consider as stable only releases with formal tags set up in Web UI
        changelog (bool): Populate release["changelog"] using upstream notes (if True)
        cache_ttl (int): Optional TTL override for release data cache (seconds).
                         Only used when release cache is enabled in config.

    Examples:
        Find the latest version of Mautic, it is OK to consider betas.

        >>> latest("mautic/mautic", output_format='version', pre_ok=True)
        <Version('4.4.4')>

        Consider only tags without letters:

        >>> latest("openssl/openssl", output_format='version', only=r'!~\w')
        <Version('3.0.7')>

    Returns:
        Union[Version, dict]: Newer version object, if found and `output_format` is `version`.
    Returns:
        str: Single string containing tag, if found and `output_format` is `tag`

    """
    repo_data = {}

    # Check release data cache first (when enabled and using json/dict output)
    release_cache = get_release_cache()
    cache_key_params = {
        "pre_ok": pre_ok,
        "major": major,
        "only": only,
        "at": at,
        "having_asset": having_asset,
        "exclude": exclude,
        "even": even,
        "formal": formal,
    }

    def _return_from_cache(cached_data, fmt, is_stale=False):
        """Helper to return cached data in the appropriate format."""
        if cached_data is None:
            return None
        prefix = "stale " if is_stale else ""
        log.info("Using %scached release data for: %s", prefix, repo)
        if is_stale:
            log.warning("Network/API error occurred. Returning stale cached data for: %s", repo)
        if fmt == "version":
            try:
                return Version(cached_data.get("version", ""))
            except InvalidVersion:
                return None
        elif fmt == "tag":
            return cached_data.get("tag_name")
        elif fmt == "dict":
            # Convert version string back to Version object for dict output
            try:
                cached_data["version"] = Version(cached_data.get("version", ""))
            except InvalidVersion:
                pass
            return cached_data
        else:  # json
            return cached_data

    # Try to get from cache for formats that can use cached data
    if release_cache.enabled and output_format in ["json", "dict", "version", "tag"]:
        cached_release = release_cache.get(repo, **cache_key_params)
        if cached_release:
            result = _return_from_cache(cached_release, output_format, is_stale=False)
            if result is not None:
                return result
            # Fall through to fetch fresh data if cache parsing failed

    # noinspection HttpUrlsUsage
    if repo.endswith(".yml") and not repo.startswith(("http://", "https://")):
        repo_data = get_repo_data_from_yml(repo)

    # noinspection HttpUrlsUsage
    if repo.startswith(("http://", "https://")) and repo.endswith("Chart.yaml"):
        at = "helm_chart"

    if repo.endswith(".spec"):
        repo_data = get_repo_data_from_spec(rpmspec_filename=repo)

    # Define network error types that should trigger cache fallback
    network_errors = (
        requests.exceptions.RequestException,  # All requests errors (connection, timeout, etc.)
        ApiCredentialsError,  # Rate limits, auth failures
        ConnectionError,
        TimeoutError,
        OSError,  # Network unreachable, etc.
    )

    try:
        with HolderFactory.get_instance_for_repo(repo_data.get("repo", repo), at=at) as project:
            project.set_only(repo_data.get("only", only))
            project.set_exclude(exclude)
            project.set_having_asset(repo_data.get("having_asset", having_asset))
            project.set_even(even)
            project.set_formal(repo_data.get("formal", formal))
            release = project.get_latest(pre_ok=pre_ok, major=repo_data.get("major", major))

            # bail out, found nothing that looks like a release
            if not release:
                return None

            from_type = f"Located the latest release tag {release['tag_name']} at: {project.get_canonical_link()}"
            if "type" in release:
                from_type = f"{from_type} via {release['type']} mechanism"
            log.info(from_type)

            version = release["version"]
            tag = release["tag_name"]

            # return the release if we've reached far enough:
            if output_format == "version":
                return version

            if output_format in ["json", "dict"]:
                if output_format == "dict":
                    release["version"] = version
                else:
                    release["version"] = str(version)
                    if "tag_date" in release:
                        release["tag_date"] = str(release["tag_date"])
                release["v_prefix"] = tag.startswith("v")
                version_macro = "upstream_version" if "module_of" in repo_data else "version"
                version_macro = f"%{{{version_macro}}}"
                holder_i = {value: key for key, value in HolderFactory.HOLDERS.items()}
                release["source"] = holder_i[type(project)]
                release["spec_tag"] = tag.replace(str(version), version_macro)
                # spec_tag_no_prefix is the helpful macro that will allow us to know where tarball
                # extracts to (GitHub-specific)
                if release["spec_tag"].startswith(f"v{version_macro}") or re.match(r"^v\d", release["spec_tag"]):
                    release["spec_tag_no_prefix"] = release["spec_tag"].lstrip("v")
                else:
                    release["spec_tag_no_prefix"] = release["spec_tag"]
                release["tag_name"] = tag
                if hasattr(project, "repo_license"):
                    release["license"] = project.repo_license(tag)
                if hasattr(project, "repo_readme"):
                    release["readme"] = project.repo_readme(tag)
                if changelog:
                    text, source = project.collect_release_notes(tag, release)
                    if text:
                        context = {
                            "repo": project.get_canonical_link(),
                            "tag": tag,
                            "version": str(release["version"]),
                            "source": release.get("source"),
                        }
                        try:
                            bullets = generate_changelog(text, context)
                            if bullets:
                                release["changelog"] = bullets
                                release["changelog_source"] = source
                        except Exception:
                            pass
                release.update(repo_data)
                try:
                    # Get detailed asset info with digests BEFORE get_assets transforms them
                    release["assets_with_digests"] = project.get_assets_with_digests(release, short_urls, assets_filter)
                    # Get asset URLs (this transforms the assets list)
                    release["assets"] = project.get_assets(release, short_urls, assets_filter)
                except NotImplementedError:
                    pass
                release["from"] = project.get_canonical_link()

                if "license" in release and release["license"]:
                    spdx_id = release["license"].get("license", {}).get("spdx_id")
                    rpmspec_licence = rpmspec_licenses[spdx_id] if spdx_id in rpmspec_licenses else None
                    if rpmspec_licence:
                        release["rpmspec_license"] = rpmspec_licence

                release["source_url"] = project.release_download_url(release, short_urls)

                # Store in release cache if enabled
                if release_cache.enabled:
                    release_cache.set(repo, release, ttl=cache_ttl, **cache_key_params)

                return release

            if output_format == "assets":
                return project.get_assets(release, short_urls, assets_filter)

            if output_format == "source":
                return project.release_download_url(release, short_urls)

            if output_format == "tag":
                return tag

    except network_errors as e:
        # Network or API error - try to fall back to stale cached data
        log.warning("Network/API error while fetching release data: %s", e)

        # Try to get stale cache (bypass TTL check)
        if output_format in ["json", "dict", "version", "tag"]:
            # Get any cached data, even if expired (for fallback)
            stale_cache = release_cache.get(repo, ignore_expiry=True, **cache_key_params)
            if stale_cache:
                result = _return_from_cache(stale_cache, output_format, is_stale=True)
                if result is not None:
                    return result

        # No cached data available, re-raise the exception
        raise

    return None


def clear_cache(repo=None):
    """Clear the HTTP cache for lastversion.

    This function is useful for webhook handlers that need to invalidate
    cache when a new release is published.

    Args:
        repo (str): Optional repository identifier (e.g., "owner/repo").
                    If provided, attempts to clear cache for that repo only.
                    If None, clears the entire cache.

    Returns:
        int: Number of cache entries cleared (or 1 for full cache clear)

    Example:
        # In a webhook handler for GitHub release events:
        from lastversion import clear_cache, latest

        def handle_github_webhook(payload):
            repo = payload['repository']['full_name']
            clear_cache(repo)
            # Optionally fetch fresh version
            version = latest(repo, output_format='json')
            return version
    """
    from lastversion.repo_holders.base import BaseProjectHolder

    return BaseProjectHolder.clear_cache(repo)


def has_update(repo, current_version, pre_ok=False, at=None):
    """Given an existing version for a repo, checks if there is an update.

    Args:
        repo (str): Repository specifier in any form.
        current_version (str): A version you want to check update for.
        pre_ok (bool): Specifies whether pre-releases can be accepted as a newer version.
        at (str): Specifies repo hosting more precisely, only useful if repo argument was
                  specified as one word.

    Returns:
        Version: Newer version as an object, if found. Otherwise, False

    """
    latest_version = latest(repo, output_format="version", pre_ok=pre_ok, at=at)
    if latest_version and latest_version > Version(current_version):
        return latest_version
    return False


def check_version(value):
    """Given a version string, raises argparse.ArgumentTypeError if it does not contain any version.
    In lastversion CLI app, this is used as argument parser helper for --newer-than (-gt) option.

    Args:
        value (str): Free-format string which is meant to contain a user-supplied version

    Raises:
        argparse.ArgumentTypeError: Exception in a case version was not found in the input string

    Returns:
        Version: Parsed version object

    """
    value = parse_version(value)
    if not value:
        raise argparse.ArgumentTypeError("%s is an invalid version value" % value)
    return value


def parse_version(tag):
    """
    Parse version to a Version object.
    Argument may not be a version but a URL or a repo name, in which case return False
    E.g., used in lastversion repo-name -gt 1.2.3 (and repo-name is passed here as tag)
    """
    # If a URL is passed
    if tag.startswith(("http://", "https://")):
        return False
    # If a repo name is passed, e.g. "mautic/mautic"
    if "/" in tag and " " not in tag:
        return False
    h = TestProjectHolder()
    v = h.sanitize_version(tag, pre_ok=True)
    return v


def get_rpm_packager():
    """Get RPM packager name from ~/.rpmmacros"""
    try:
        rpmmacros = expanduser("~") + "/.rpmmacros"
        with open(rpmmacros) as f:
            for ln in f.readlines():
                if ln.startswith("%packager"):
                    return ln.split("%packager")[1].strip()
    except IOError:
        log.warning("~/.rpmmacros does not exist. Changelog will not be generated")
    return None


def build_changelog_bullets(res, repo_arg):
    """Build changelog bullets for a release dict using upstream notes and OpenAI.

    Returns:
        list[str] or None
    """
    try:
        raw_notes = res.get("body") or res.get("description")
    except AttributeError:
        raw_notes = None

    if not raw_notes:
        return None

    try:
        context = {
            "repo": res.get("from"),
            "tag": res.get("tag_name"),
            "version": str(res.get("version")),
            "source": res.get("source"),
        }
        return generate_changelog(raw_notes, context)
    except Exception:
        return None


def update_spec(repo, res, sem="minor", changelog: bool = False):
    print(res["version"])
    if "current_version" not in res or res["current_version"] < res["version"]:
        log.info("Updating spec %s with semantic %s", repo, sem)
        if "current_version" in res and len(res["version"].release) >= 3:
            current_major = res["current_version"].release[0]
            latest_major = res["version"].release[0]
            current_minor = res["current_version"].release[1]
            latest_minor = res["version"].release[1]
            if sem in ["minor", "patch"]:
                if latest_major != current_major:
                    log.warning(FAILS_SEM_ERR_FMT, res["version"], sem, res["current_version"])
                    sys.exit(4)
                if sem == "patch" and latest_minor != current_minor:
                    log.warning(FAILS_SEM_ERR_FMT, res["version"], sem, res["current_version"])
                    sys.exit(4)
    else:
        log.info("No newer version than already present in spec file")
        sys.exit(2)
    # update or add %lastversion_tag and %lastversion_dir, Version (?), Release
    # Flag to track if '%global lastversion_tag' is present
    lastversion_tag_present = False
    # Flag to track if '%global lastversion_dir' is present
    lastversion_dir_present = False
    out = []
    packager = get_rpm_packager()
    with open(repo) as f:
        for ln in f.readlines():
            if ln.startswith("%global lastversion_tag "):
                out.append(f'%global lastversion_tag {res["spec_tag"]}')
                lastversion_tag_present = True
            elif ln.startswith("%global lastversion_dir "):
                out.append(f"%global lastversion_dir " f'{res["spec_name"]}-{res["spec_tag_no_prefix"]}')
                lastversion_dir_present = True
            elif ln.startswith("%global upstream_version "):
                out.append(f'%global upstream_version {res["version"]}')
            elif ln.startswith("Version:") and ("module_of" not in res or not res["module_of"]):
                version_tag_regex = r"^Version:(\s+)(\S+)"
                m = re.match(version_tag_regex, ln)
                out.append("Version:" + m.group(1) + str(res["version"]))
            elif ln.startswith("%changelog") and packager:
                from datetime import datetime

                now = datetime.utcnow()
                today = now.strftime("%a %b %d %Y")
                out.append(ln.rstrip())
                # RPM guideline: include Version-Release in header (Release resets to 1 on bump)
                out.append(f"* {today} {packager} - {str(res['version'])}-1")
                bullets = None
                if isinstance(res, dict):
                    existing = res.get("changelog")
                    if isinstance(existing, list) and existing:
                        bullets = [str(b).strip() for b in existing if str(b).strip()]
                if changelog and not bullets:
                    bullets = build_changelog_bullets(res, repo)

                if bullets:
                    for b in bullets:
                        out.append(f"- {b}")
                else:
                    out.append(f"- upstream release v{res['version']}")
                out.append("\n")
            elif ln.startswith("Release:"):
                release_tag_regex = r"^Release:(\s+)(\S+)"
                m = re.match(release_tag_regex, ln)
                release = m.group(2)
                from string import digits

                release = release.lstrip(digits)
                out.append("Release:" + m.group(1) + "1" + release)
            elif ln.startswith("License:") and res.get("rpmspec_license"):
                # Update License: tag with the license from upstream
                license_tag_regex = r"^License:(\s+)(\S.*)"
                m = re.match(license_tag_regex, ln)
                if m:
                    out.append("License:" + m.group(1) + res["rpmspec_license"])
                else:
                    out.append(ln.rstrip())
            else:
                out.append(ln.rstrip())

    if not lastversion_tag_present:
        # Insert %lastversion_tag at the top of the spec file
        out.insert(0, f'%global lastversion_tag {res["spec_tag"]}')

    if not lastversion_dir_present:
        # Insert %lastversion_dir after %lastversion_tag
        lastversion_tag_index = out.index(f'%global lastversion_tag {res["spec_tag"]}')
        out.insert(
            lastversion_tag_index + 1,
            f"%global lastversion_dir {res['spec_name']}-{res['spec_tag_no_prefix']}",
        )

    with open(repo, "w") as f:
        f.write("\n".join(out))


def update_spec_commit(spec_file, commit_info, repo_data):
    """Update spec file for commit-based (snapshot) releases.

    Args:
        spec_file: Path to the spec file
        commit_info: Dict with 'sha', 'short_sha', 'date', 'message'
        repo_data: Dict with repo data from spec parsing

    Updates:
        - %global commit <sha>
        - %global commit_date <YYYYMMDD>
        - Release: 0.%{snapinfo}%{?dist} (if no releases) or 1.%{snapinfo}%{?dist}
    """
    current_commit = repo_data.get("current_commit")
    if current_commit == commit_info["sha"]:
        log.info("Commit %s is already current in spec file", commit_info["short_sha"])
        sys.exit(2)

    print(f"Updating to commit {commit_info['short_sha']}")

    # Format commit date as YYYYMMDD
    commit_date = commit_info["date"].strftime("%Y%m%d")

    out = []
    commit_present = False
    commit_date_present = False
    snapinfo_present = False

    with open(spec_file) as f:
        for ln in f.readlines():
            if ln.startswith("%global commit "):
                out.append(f'%global commit {commit_info["sha"]}')
                commit_present = True
            elif ln.startswith("%global commit_date "):
                out.append(f"%global commit_date {commit_date}")
                commit_date_present = True
            elif ln.startswith("%global snapinfo "):
                # Keep existing snapinfo definition
                out.append(ln.rstrip())
                snapinfo_present = True
            elif ln.startswith("Release:"):
                release_tag_regex = r"^Release:(\s+)(\S+)"
                m = re.match(release_tag_regex, ln)
                if m:
                    # Check if there's a formal release version
                    current_version = repo_data.get("current_version")
                    if current_version and str(current_version) != "0":
                        # Post-release snapshot: 1.snapinfo
                        out.append(f"Release:{m.group(1)}1.%{{snapinfo}}%{{?dist}}")
                    else:
                        # Pre-release snapshot: 0.snapinfo
                        out.append(f"Release:{m.group(1)}0.%{{snapinfo}}%{{?dist}}")
                else:
                    out.append(ln.rstrip())
            else:
                out.append(ln.rstrip())

    # Add missing globals at the top
    if not commit_present:
        out.insert(0, f'%global commit {commit_info["sha"]}')

    if not commit_date_present:
        # Insert after %global commit
        for i, line in enumerate(out):
            if line.startswith("%global commit "):
                out.insert(i + 1, f"%global commit_date {commit_date}")
                break

    if not snapinfo_present:
        # Add default snapinfo definition after commit_date
        for i, line in enumerate(out):
            if line.startswith("%global commit_date "):
                out.insert(i + 1, "%global snapinfo %{commit_date}git%{shortcommit}")
                break

    # Add shortcommit if not present
    has_shortcommit = any(line.startswith("%global shortcommit ") for line in out)
    if not has_shortcommit:
        for i, line in enumerate(out):
            if line.startswith("%global commit "):
                out.insert(i + 1, "%global shortcommit %(c=%{commit}; echo ${c:0:7})")
                break

    with open(spec_file, "w") as f:
        f.write("\n".join(out))

    log.info(
        "Updated %s to commit %s (%s)",
        spec_file,
        commit_info["short_sha"],
        commit_info["message"][:50],
    )


def install_app_image(url, install_name):
    """Install an AppImage from a URL to `~/Applications/<install_name>`

    Args:
        url (str): URL where AppImage file is hosted
        install_name (str): Short name that the AppImage will be renamed to
    """
    if not install_name.endswith(".AppImage"):
        install_name += ".AppImage"
    app_file_name = install_standalone_binary(url, install_name)
    extract_appimage_desktop_file(app_file_name)


def install_rpms(res, rpms, args):
    """Install RPMs using package manager"""
    # prevents downloading large packages if we already have newest installed
    # consult RPM database  for current version
    installed_version = rpm_installed_version(args.repo)
    if installed_version is False:
        log.warning(
            "Please install lastversion using YUM or DNF so it can check current "
            "program version. This is helpful to prevent unnecessary downloads"
        )
    if installed_version and Version(installed_version) >= Version(res["version"]):
        log.warning("Newest version %s is already installed", installed_version)
        sys.exit(0)
    # pass RPM URLs directly to package management program
    try:
        import subprocess

        params = ["yum", "install"]
        params.extend(rpms)
        if args.assumeyes:
            params.append("-y")
        subprocess.call(params)
    except OSError:
        log.critical("Failed to launch package manager. Only YUM/DNF is supported!")
        sys.exit(1)
    # if the system has yum, then lastversion has to be installed from yum and
    # has access to system packages like yum python or dnf python API
    # if install_with_dnf(rpms) is False or install_with_yum(rpms) is False:
    #     log.error('Failed talking to either DNF or YUM for package install')
    #     sys.exit(1)


def install_debs(_res, debs, args):
    """Install deb packages using apt.

    Args:
        _res: Release dict (unused, kept for API consistency with install_rpms)
        debs: List of deb package URLs
        args: CLI arguments
    """
    try:
        import subprocess

        # Download debs first, then install with apt
        local_debs = []
        for deb_url in debs:
            local_file = download_file(deb_url)
            local_debs.append(local_file)

        params = ["apt", "install"]
        params.extend(local_debs)
        if args.assumeyes:
            params.append("-y")
        subprocess.call(params)
    except OSError:
        log.critical("Failed to launch apt for package install!")
        sys.exit(1)


def install_standalone_binary(url, install_name):
    """Install a standalone binary from a URL to `~/Applications/<install_name>`

    Args:
        url (str): URL where the binary file is hosted
        install_name (str): Filename that the binary will be renamed to
    """
    home_dir = os.path.expanduser("~")
    apps_dir = os.path.join(home_dir, "Applications")
    app_file_name = os.path.join(apps_dir, install_name)

    Path(apps_dir).mkdir(exist_ok=True, parents=True)
    download_file(url, app_file_name)
    os.chmod(app_file_name, 0o755)  # skipcq: BAN-B103
    return app_file_name


def install_release(res, args):
    """Install latest release.

    Prefers native package formats (RPM/deb) over AppImages for better
    integration with package managers and architecture compatibility.
    """
    # Prefer RPMs on RPM-based distros
    rpms = [asset for asset in res["assets"] if asset.endswith(".rpm")]
    if rpms:
        return install_rpms(res, rpms, args)

    # Prefer debs on Debian-based distros
    debs = [asset for asset in res["assets"] if asset.endswith(".deb")]
    if debs:
        return install_debs(res, debs, args)

    # Fall back to AppImages (cross-distro)
    app_images = [asset for asset in res["assets"] if asset.endswith(".AppImage")]
    if app_images:
        return install_app_image(app_images[0], install_name=res.get("install_name", args.repo))

    # static files are those without an extension
    static_binaries = [asset for asset in res["assets"] if "." not in asset.rsplit("/", 1)[-1]]
    if static_binaries:
        return install_standalone_binary(static_binaries[0], install_name=res.get("install_name", args.repo))

    log.error("No installable assets found to install")
    sys.exit(1)
