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

from lastversion.__about__ import __self__
from lastversion import check_version, latest
from lastversion.argparse_version import VersionAction
from lastversion.exceptions import ApiCredentialsError, BadProjectError
from lastversion.holder_factory import HolderFactory
from lastversion.lastversion import log, parse_version, update_spec, install_release
from lastversion.repo_holders.base import BaseProjectHolder
from lastversion.repo_holders.github import TOKEN_PRO_TIP
from lastversion.utils import download_file, extract_file
from lastversion.version import Version


def main_with_bulk_support(argv=None):
    """
    Wrapper that handles bulk input via -i/--input option.

    Args:
        argv: List of arguments
    """
    # Check if -i/--input is in the arguments
    if argv is None:
        import sys as _sys

        argv = _sys.argv[1:]

    # Check for --help to add our custom option
    if "--help" in argv or "-h" in argv:
        # Let main handle help but we'll add a note about -i
        try:
            main(argv)
        except SystemExit:
            # Print additional help for -i option
            print("\nBulk processing option:")
            print("  -i FILE, --input FILE")
            print(
                "                        Read repository list from file, one repository per line"
            )
            print(
                "                        Lines starting with '#' are treated as comments"
            )
            raise

    input_file = None
    input_file_idx = None

    # Find -i or --input in argv
    for i, arg in enumerate(argv):
        if arg == "-i" or arg == "--input":
            if i + 1 < len(argv):
                input_file = argv[i + 1]
                input_file_idx = i
                break
        elif arg.startswith("--input="):
            input_file = arg.split("=", 1)[1]
            input_file_idx = i
            break

    if input_file:
        # Bulk mode: read repos from file and process each
        repos = []
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                repos = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]
        except FileNotFoundError:
            log.critical(f"Input file not found: {input_file}")
            sys.exit(1)
            return  # In case sys.exit is mocked
        except IOError as e:
            log.critical(f"Error reading input file: {e}")
            sys.exit(1)
            return  # In case sys.exit is mocked

        if not repos:
            log.critical("No repositories found in input file")
            sys.exit(1)
            return  # In case sys.exit is mocked

        # Remove -i/--input and its value from argv
        new_argv = list(argv)
        if argv[input_file_idx].startswith("--input="):
            del new_argv[input_file_idx]
        else:
            del new_argv[input_file_idx : input_file_idx + 2]

        # Process each repo
        exit_code = 0
        for repo in repos:
            # Create argv for this repo
            repo_argv = new_argv + [repo]
            try:
                main(repo_argv)
            except SystemExit as e:
                if e.code and e.code != 0:
                    exit_code = e.code

        sys.exit(exit_code)
    else:
        # Normal mode: just call main
        return main(argv)


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
        help="Semantic versioning level base to print or compare against",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Will give you an idea of what is happening under the hood, "
        "-vv to increase verbosity level",
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
        help="Only consider releases containing this text. "
        "Useful for repos with multiple projects inside",
    )
    parser.add_argument(
        "--exclude",
        metavar="REGEX",
        help="Only consider releases NOT containing this text. "
        "Useful for repos with multiple projects inside",
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
    )
    args = parser.parse_args(argv)

    BaseProjectHolder.CACHE_DISABLED = args.no_cache

    if args.repo == "self":
        args.repo = __self__

    # "expand" repo:1.2 as repo --branch 1.2
    # noinspection HttpUrlsUsage
    if ":" in args.repo and not (
        args.repo.startswith(("https://", "http://")) and args.repo.count(":") == 1
    ):
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
    fmt = (
        "%(name)s - %(levelname)s - %(message)s"
        if args.verbose
        else "%(levelname)s: %(message)s"
    )
    formatter = logging.Formatter(fmt)
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)

    if args.verbose:
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
                import apt

                args.having_asset = r"~\.(AppImage|deb)$"
            except ImportError:
                pass

    if args.repo.endswith(".spec"):
        args.action = "update-spec"
        args.format = "dict"

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
        if args.action == "update-spec":
            return update_spec(args.repo, res, sem=args.sem)
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
                res = res.sem_extract_base(args.sem)
            print(res)
            # special exit code "2" is useful for scripting to detect if no newer release exists
            if args.newer_than:
                # set up same SEM base
                args.newer_than = args.newer_than.sem_extract_base(args.sem)
                if res <= args.newer_than:
                    sys.exit(2)
    else:
        # empty list returned to --assets, emit 3
        if args.format == "assets" and res is not False:
            sys.exit(3)
        log.critical("No release was found")
        sys.exit(1)
