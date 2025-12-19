"""CLI entry point."""

import argparse
import json
import logging
import os
import re
import sys

# try to use truststore if available
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

from lastversion import check_version, latest, utils
from lastversion.__about__ import __self__
from lastversion.argparse_version import VersionAction
from lastversion.exceptions import ApiCredentialsError, BadProjectError
from lastversion.holder_factory import HolderFactory
from lastversion.lastversion import (
    get_repo_data_from_spec,
    install_release,
    log,
    parse_version,
    update_spec,
    update_spec_commit,
)
from lastversion.repo_holders.base import BaseProjectHolder
from lastversion.repo_holders.github import TOKEN_PRO_TIP
from lastversion.utils import download_file, extract_file
from lastversion.version import Version


def handle_cache_action(args):
    """Handle cache management commands.

    Args:
        args: Parsed command line arguments

    Usage:
        lastversion cache clear          - Clear all cache
        lastversion cache clear <repo>   - Clear cache for specific repo
        lastversion cache info           - Show cache statistics
        lastversion cache cleanup        - Clean up expired cache entries

    Returns:
        Exit code
    """
    from lastversion.cache import get_release_cache
    from lastversion.config import get_config

    subcommand = args.repo.lower() if args.repo else "help"

    if subcommand == "clear":
        # Check if there's a repo argument (passed as part of the repo string after "clear")
        # For simplicity, clearing all cache when just "lastversion cache clear"
        cleared = BaseProjectHolder.clear_cache()
        if cleared:
            print("Cache cleared successfully")
        else:
            print("Cache was already empty or does not exist")
        return sys.exit(0)

    elif subcommand == "info":
        # Show cache statistics
        config = get_config()
        release_cache = get_release_cache()

        print("Cache Configuration:")
        print(f"  Config file: {config.config_path}")
        print(f"  Backend: {config.cache_backend}")
        print(f"  Release cache enabled: {config.release_cache_enabled}")
        print(f"  Release cache TTL: {config.release_cache_ttl}s")
        print(f"  File cache path: {config.file_cache_path}")
        print(f"  File cache max age: {config.file_cache_max_age}s")
        print()

        if release_cache.enabled or release_cache.backend:
            # Force create backend for stats even if not enabled
            if not release_cache.backend:
                from lastversion.cache import create_cache_backend

                try:
                    backend = create_cache_backend()
                    info = backend.info()
                except Exception as e:
                    print(f"Error getting cache info: {e}")
                    return sys.exit(1)
            else:
                info = release_cache.info()

            print("Release Data Cache Stats:")
            print(f"  Backend: {info.get('backend', 'N/A')}")
            print(f"  Entries: {info.get('entries', 0)}")
            if info.get("expired_entries"):
                print(f"  Expired entries: {info.get('expired_entries', 0)}")
            if info.get("size_human"):
                print(f"  Size: {info.get('size_human')}")
            elif info.get("size_bytes"):
                print(f"  Size: {info.get('size_bytes')} bytes")
            # Show last cleanup info
            last_cleanup = info.get("last_cleanup")
            if last_cleanup:
                from datetime import datetime

                cleanup_time = datetime.fromtimestamp(last_cleanup)
                print(f"  Last cleanup: {cleanup_time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print("  Last cleanup: never")
            print(f"  Auto-cleanup interval: {info.get('auto_cleanup_interval', 'N/A')}s")
        else:
            print("Release data cache is not enabled.")
            print(f"To enable, add to {config.config_path}:")
            print("  cache:")
            print("    release_cache:")
            print("      enabled: true")
            print("      ttl: 3600  # seconds")

        return sys.exit(0)

    elif subcommand == "cleanup":
        # Clean up expired cache entries
        release_cache = get_release_cache()
        if release_cache.backend:
            cleaned = release_cache.cleanup()
            print(f"Cleaned up {cleaned} expired cache entries")
        else:
            print("Release cache is not enabled, nothing to clean up")
        return sys.exit(0)

    elif subcommand == "help" or subcommand.startswith("-"):
        print("Usage:")
        print("  lastversion cache clear         - Clear all cache")
        print("  lastversion cache clear <repo>  - Clear cache for specific repo")
        print("  lastversion cache info          - Show cache configuration and stats")
        print("  lastversion cache cleanup       - Clean up expired cache entries")
        print("")
        print("To refresh cache for a repo, use --no-cache:")
        print("  lastversion --no-cache <repo>")
        return sys.exit(0)

    else:
        # Treat as repo name - clear cache for this repo and get fresh version
        cleared = BaseProjectHolder.clear_cache(repo=subcommand)
        print(f"Cleared {cleared} cache entries for {subcommand}")
        return sys.exit(0)


def handle_commit_based_spec(args, repo_data):
    """Handle update of commit-based spec files.

    Args:
        args: Parsed command line arguments
        repo_data: Dict with repo data from spec parsing

    Returns:
        Exit code
    """
    from lastversion.holder_factory import HolderFactory

    repo = repo_data.get("repo")
    if not repo:
        log.critical("Could not determine repository from spec file")
        return sys.exit(1)

    try:
        with HolderFactory.get_instance_for_repo(repo) as project:
            # Check if the holder supports getting latest commit
            if not hasattr(project, "get_latest_commit"):
                log.critical("Commit-based updates are only supported for GitHub repositories")
                return sys.exit(1)

            commit_info = project.get_latest_commit()
            if not commit_info:
                log.critical("Failed to get latest commit from %s", repo)
                return sys.exit(1)

            return update_spec_commit(args.repo, commit_info, repo_data)

    except (ApiCredentialsError, BadProjectError) as error:
        log.critical(str(error))
        return sys.exit(4)


def process_bulk_input(args):
    """Process multiple repositories from an input file.

    Args:
        args: Parsed command line arguments with input_file set

    Returns:
        Exit code (0 for success, 1 for any failures)
    """
    # Read repos from file or stdin
    if args.input_file == "-":
        repos = sys.stdin.read().strip().split("\n")
    else:
        try:
            with open(args.input_file, encoding="utf-8") as f:
                repos = f.read().strip().split("\n")
        except IOError as e:
            log.critical("Failed to read input file: %s", e)
            return sys.exit(1)

    # Filter out empty lines and comments
    repos = [r.strip() for r in repos if r.strip() and not r.strip().startswith("#")]

    if not repos:
        log.critical("No repositories found in input file")
        return sys.exit(1)

    results = []
    has_failures = False

    for repo in repos:
        try:
            result = latest(
                repo,
                output_format=args.format,
                pre_ok=args.pre,
                assets_filter=args.filter,
                short_urls=args.shorter_urls,
                major=args.major,
                formal=args.formal,
                at=args.at,
                having_asset=args.having_asset,
                only=args.only,
                even=args.even,
                cache_ttl=args.cache_ttl,
            )
            if result:
                if args.format == "json":
                    result["repo"] = repo
                    results.append(result)
                else:
                    print(f"{repo}: {result}")
            else:
                print(f"{repo}: not found", file=sys.stderr)
                has_failures = True
        except (BadProjectError, ApiCredentialsError) as e:
            print(f"{repo}: error - {e}", file=sys.stderr)
            has_failures = True

    # Output JSON results as array if json format
    if args.format == "json" and results:
        json.dump(results, sys.stdout)
        print()

    return sys.exit(1 if has_failures else 0)


def main(argv=None):
    """
    The entrypoint to CLI app.

    Args:
        argv: List of arguments, helps test CLI without resorting to subprocess module.
    """
    # ANSI escape code for starting bold text
    start_bold = "\033[1m"
    # ANSI escape code for ending the formatting (resets to normal text)
    end_bold = "\033[0m"

    epilog = "\n---\n"
    epilog += f"{start_bold}Sponsored Message: Check out the GetPageSpeed RPM "
    epilog += "repository at https://nginx-extras.getpagespeed.com/ for NGINX "
    epilog += "modules and performance tools. Enhance your server performance "
    epilog += f"today!{end_bold}"
    epilog += "\n---\n"

    if "GITHUB_API_TOKEN" not in os.environ and "GITHUB_TOKEN" not in os.environ:
        epilog += TOKEN_PRO_TIP
    parser = argparse.ArgumentParser(
        description="Find the latest software release.",
        epilog=epilog,
        prog="lastversion",
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="get",
        help="Action to run. Default: get",
        choices=[
            "get",
            "download",
            "extract",
            "unzip",
            "test",
            "format",
            "install",
            "update-spec",
            "cache",
        ],
    )
    parser.add_argument(
        "repo",
        metavar="<repo URL or string>",
        help="Repository in format owner/name or any URL that belongs to it, or a version string",
    )
    # affects what is considered last release
    parser.add_argument(
        "--pre",
        dest="pre",
        action="store_true",
        help="Include pre-releases in potential versions",
    )
    parser.add_argument(
        "--formal",
        dest="formal",
        action="store_true",
        help="Include only formally tagged versions",
    )
    parser.add_argument(
        "--sem",
        dest="sem",
        choices=["major", "minor", "patch", "any"],
        help="Semantic versioning level base to print or compare against. "
        "When used with -gt: 'minor' constrains to same major, 'patch' constrains "
        "to same major.minor. Exit code 4 if newer version exists outside constraint",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Will give you an idea of what is happening under the hood, " "-vv to increase verbosity level",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        dest="quiet",
        action="store_true",
        help="Suppress all non-error output, including progress bars",
    )
    parser.add_argument(
        "-i",
        "--input-file",
        dest="input_file",
        metavar="FILE",
        help="Read repository names/URLs from file (one per line). " "Use '-' to read from stdin",
    )
    # no --download = False, --download filename.tar, --download = None
    parser.add_argument(
        "-d",
        "-o",
        "--download",
        "--output",
        dest="download",
        nargs="?",
        default=False,
        const=None,
        metavar="FILENAME",
        help="Download with custom filename",
    )
    # how / which data of last release we want to present
    # assets will give download urls for assets if available and sources archive otherwise
    # sources will give download urls for sources always
    # json always includes "version", "tag_name" etc. + whichever json data was
    # used to satisfy lastversion
    parser.add_argument(
        "--format",
        choices=["version", "assets", "source", "json", "tag"],
        help="Output format",
    )
    parser.add_argument(
        "--assets",
        dest="assets",
        action="store_true",
        help="Returns assets download URLs for last release",
    )
    parser.add_argument(
        "--source",
        dest="source",
        action="store_true",
        help="Returns only source URL for last release",
    )
    parser.add_argument(
        "-gt",
        "--newer-than",
        type=check_version,
        metavar="VER",
        help="Output only if last version is newer than given version",
    )
    parser.add_argument(
        "-b",
        "--major",
        "--branch",
        metavar="MAJOR",
        help="Only consider releases of a specific major version, e.g. 2.1.x",
    )
    parser.add_argument(
        "--only",
        metavar="REGEX",
        help="Only consider releases containing this text. " "Useful for repos with multiple projects inside",
    )
    parser.add_argument(
        "--exclude",
        metavar="REGEX",
        help="Only consider releases NOT containing this text. " "Useful for repos with multiple projects inside",
    )
    parser.add_argument(
        "--filter",
        metavar="REGEX",
        help="Filters --assets result by a regular " "expression",
    )
    parser.add_argument(
        "--having-asset",
        metavar="ASSET",
        help="Only consider releases with this asset",
        nargs="?",
        const=True,
    )
    parser.add_argument(
        "-su",
        "--shorter-urls",
        dest="shorter_urls",
        action="store_true",
        help="A tiny bit shorter URLs produced",
    )
    parser.add_argument(
        "--even",
        dest="even",
        action="store_true",
        help="Only even versions like 1.[2].x, or 3.[6].x are considered as stable",
    )
    parser.add_argument(
        "--at",
        dest="at",
        help="If the repo argument is one word, specifies where to look up the "
        "project. The default is via internal lookup or GitHub Search",
        choices=HolderFactory.HOLDERS.keys(),
    )
    parser.add_argument(
        "-y",
        "--assumeyes",
        dest="assumeyes",
        action="store_true",
        help="Automatically answer yes for all questions",
    )
    parser.add_argument(
        "--no-cache",
        dest="no_cache",
        action="store_true",
        help="Do not use cache for HTTP requests",
    )
    parser.add_argument(
        "--cache-ttl",
        dest="cache_ttl",
        type=int,
        metavar="SECONDS",
        help="Override release cache TTL (requires release cache enabled in config)",
    )
    parser.add_argument(
        "--changelog",
        dest="changelog",
        action="store_true",
        help="Generate RPM %%changelog entry (1-7 concise bullets)",
    )
    parser.add_argument("--version", action=VersionAction)
    parser.set_defaults(
        validate=True,
        verbose=False,
        format="version",
        pre=False,
        formal=False,
        assets=False,
        newer_than=False,
        filter=False,
        shorter_urls=False,
        major=None,
        assumeyes=False,
        at=None,
        having_asset=None,
        even=False,
        changelog=False,
        quiet=False,
        cache_ttl=None,
    )
    args = parser.parse_args(argv)

    BaseProjectHolder.CACHE_DISABLED = args.no_cache

    # Handle quiet mode - suppress non-error output and progress bars
    if args.quiet:
        utils.QUIET_MODE = True
        # In quiet mode, only show errors
        logging.getLogger("lastversion").setLevel(logging.ERROR)

    if args.repo == "self":
        args.repo = __self__

    # "expand" repo:1.2 as repo --branch 1.2
    # noinspection HttpUrlsUsage
    if ":" in args.repo and not (args.repo.startswith(("https://", "http://")) and args.repo.count(":") == 1):
        # right split ':' once only to preserve it in protocol of URLs
        # https://github.com/repo/owner:2.1
        repo_args = args.repo.rsplit(":", 1)
        args.repo = repo_args[0]
        args.major = repo_args[1]

    # instead of using root logger, we use
    logger = logging.getLogger("lastversion")
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    # create formatter
    fmt = "%(name)s - %(levelname)s - %(message)s" if args.verbose else "%(levelname)s: %(message)s"
    formatter = logging.Formatter(fmt)
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)

    if args.verbose and not args.quiet:
        logger.setLevel(logging.DEBUG)
        log.info("Verbose %s level output.", args.verbose)
        if args.verbose >= 2:
            cachecontrol_logger = logging.getLogger("cachecontrol")
            cachecontrol_logger.removeHandler(logging.NullHandler())
            cachecontrol_logger.addHandler(ch)
            cachecontrol_logger.setLevel(logging.DEBUG)

    if args.assets:
        args.format = "assets"

    if args.source:
        args.format = "source"

    if args.filter:
        args.filter = re.compile(args.filter)

    # Handle bulk input from file
    if args.input_file:
        return process_bulk_input(args)

    # Handle cache management
    if args.action == "cache":
        return handle_cache_action(args)

    if args.action in ["test", "format"]:
        v = parse_version(args.repo)
        if not v:
            log.critical("Failed to parse as a valid version")
            sys.exit(1)
        else:
            # extract the desired print base
            v = v.sem_extract_base(args.sem)
            if args.action == "test":
                print(f"Parsed as: {v}")
                print(f"Stable: {not v.is_prerelease}")
            else:
                print(v)
            return sys.exit(0)

    if args.action == "install":
        # we can only install assets
        args.format = "json"
        if args.having_asset is None:
            args.having_asset = r"~\.(AppImage|rpm)$"
            try:
                import apt  # noqa: F401 - used for feature detection

                args.having_asset = r"~\.(AppImage|deb)$"
            except ImportError:
                pass

    if args.repo.endswith(".spec"):
        args.action = "update-spec"
        args.format = "dict"
        # Check if this is a commit-based spec file
        repo_data = get_repo_data_from_spec(args.repo)
        if repo_data.get("commit_based"):
            # Handle commit-based spec update
            return handle_commit_based_spec(args, repo_data)
        # Use semver constraint from spec file if not overridden by CLI
        if not args.sem and repo_data.get("sem"):
            args.sem = repo_data["sem"]

    if not args.sem:
        if args.action == "update-spec":
            args.sem = "minor"
        else:
            args.sem = "any"
    # imply source download, unless --assets specified
    # --download is legacy flag to specify download action or name of desired download file
    # --download == None indicates download intent where filename is based on upstream
    if args.action == "download" and args.download is False:
        args.download = None

    if args.download is not False:
        args.action = "download"
        if args.format != "assets":
            args.format = "source"

    if args.action in ["extract", "unzip"] and args.format != "assets":
        args.format = "source"

    if args.newer_than:
        base_compare = parse_version(args.repo)
        if base_compare:
            print(max([args.newer_than, base_compare]))
            return sys.exit(2 if base_compare <= args.newer_than else 0)

    # other action are either getting release or doing something with release (extend get action)
    try:
        res = latest(
            args.repo,
            args.format,
            args.pre,
            args.filter,
            args.shorter_urls,
            args.major,
            args.only,
            args.at,
            having_asset=args.having_asset,
            exclude=args.exclude,
            even=args.even,
            formal=args.formal,
            changelog=args.changelog,
            cache_ttl=args.cache_ttl,
        )
    except (ApiCredentialsError, BadProjectError) as error:
        log.critical(str(error))
        if (
            isinstance(error, ApiCredentialsError)
            and "GITHUB_API_TOKEN" not in os.environ
            and "GITHUB_TOKEN" not in os.environ
        ):
            log.critical(TOKEN_PRO_TIP)
        sys.exit(4)

    if res:
        # If user requested --changelog, prefer bullets from result dict
        if args.format in ["dict", "json"] and args.changelog and isinstance(res, dict):
            if not res.get("changelog"):
                # Ensure at least a minimal fallback is present
                res["changelog"] = [f"upstream release v{res.get('version')}"]
        if args.action == "update-spec":
            return update_spec(args.repo, res, sem=args.sem, changelog=args.changelog)
        if args.action == "download":
            # download command
            if args.format == "source":
                # there is only one source, but we need an array
                res = [res]
            download_name = None
            # save with custom filename if there's one file to download
            if len(res) == 1:
                download_name = args.download
            for url in res:
                log.info("Downloading %s ...", url)
                download_file(url, download_name)
            sys.exit(0)

        if args.action in ["unzip", "extract"]:
            # download command
            if args.format == "source":
                # there is only one source, but we need an array
                res = [res]
            for url in res:
                log.info("Extracting %s ...", url)
                extract_file(url)
            sys.exit(0)

        if args.action == "install":
            return install_release(res, args)

        # display version in various formats:
        if args.format == "assets":
            print("\n".join(res))
        elif args.format == "json":
            json.dump(res, sys.stdout)
        else:
            # result may be a tag str, not just Version
            if isinstance(res, Version):
                # Keep original version for semver constraint checking
                original_res = res
                res = res.sem_extract_base(args.sem)
            else:
                original_res = None
            print(res)
            # special exit code "2" is useful for scripting to detect if no newer release exists
            # exit code "4" is for when a newer version exists but outside semver constraint
            if args.newer_than:
                # Keep original newer_than for semver constraint checking
                original_newer_than = args.newer_than
                # set up same SEM base for display comparison
                args.newer_than = args.newer_than.sem_extract_base(args.sem)
                if res <= args.newer_than:
                    sys.exit(2)
                # Check semver constraints when --sem is specified with minor or patch
                # Exit code 4 means: newer version exists but outside semver constraint
                if original_res and args.sem in ("minor", "patch"):
                    if args.sem == "minor":
                        # For minor: latest must be within same major series
                        if original_res.major != original_newer_than.major:
                            log.info(
                                "Version %s is outside semver constraint (different major: %s vs %s)",
                                original_res,
                                original_res.major,
                                original_newer_than.major,
                            )
                            sys.exit(4)
                    elif args.sem == "patch":
                        # For patch: latest must be within same major.minor series
                        if (
                            original_res.major != original_newer_than.major
                            or original_res.minor != original_newer_than.minor
                        ):
                            log.info(
                                "Version %s is outside semver constraint (different major.minor: %s.%s vs %s.%s)",
                                original_res,
                                original_res.major,
                                original_res.minor,
                                original_newer_than.major,
                                original_newer_than.minor,
                            )
                            sys.exit(4)
    else:
        # empty list returned to --assets, emit 3
        if args.format == "assets" and res is not False:
            sys.exit(3)
        log.critical("No release was found")
        sys.exit(1)
