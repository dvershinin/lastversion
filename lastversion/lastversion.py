"""
lastversion
==========
License: BSD, see LICENSE for more details.
"""

import argparse
import json
import logging
import os
import re
import sys
import yaml
from appdirs import user_cache_dir
from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache
# from cachecontrol.heuristics import ExpiresAfter
from packaging.version import Version, InvalidVersion

from .ProjectHolder import ProjectHolder
from .HolderFactory import HolderFactory
from .__about__ import __version__
from .utils import download_file, ApiCredentialsError, BadProjectError, rpm_installed_version

log = logging.getLogger(__name__)


def latest(repo, output_format='version', pre_ok=False, assets_filter=False,
           short_urls=False, major=None, only=None):
    cache_dir = user_cache_dir("lastversion")
    log.info("Using cache directory: {}.".format(cache_dir))
    repo_data = {}
    if repo.endswith('.yml'):
        with open(repo) as fpi:
            repo_data = yaml.safe_load(fpi)
            if 'repo' in repo_data:
                if 'nginx-extras' in repo:
                    repo_data['module_of'] = 'nginx'
                name = os.path.splitext(os.path.basename(repo))[0]
                if 'module_of' in repo_data:
                    name = '{}-module-{}'.format(repo_data['module_of'], name)
                repo = repo_data['repo']
                repo_data['name'] = name

    # find the right hosting for this repo
    project_holder = HolderFactory.get_instance_for_repo(repo, only=only)

    # we are completely "offline" for 1 hour, not even making conditional requests
    # heuristic=ExpiresAfter(hours=1)   <- make configurable
    with CacheControl(project_holder, cache=FileCache(cache_dir)) as s:
        release = s.get_latest(pre_ok=pre_ok, major=major)
    s.close()

    # bail out, found nothing that looks like a release
    if not release:
        return None

    version = release['version']
    tag = release['tag_name']

    # return the release if we've reached far enough:
    if output_format == 'version':
        return version

    if output_format == 'json':
        release['version'] = str(version)
        release['tag_date'] = str(release['tag_date'])
        release['v_prefix'] = tag.startswith("v")
        version_macro = 'upstream_version' if 'module_of' in repo_data else 'version'
        version_macro = '%{{{}}}'.format(version_macro)
        release['spec_tag'] = tag.replace(
            str(version),
            version_macro
        )
        # spec_tag_no_prefix is the helpful macro which will allow us to know where tarball
        # extracts to (GitHub-specific)
        if release['spec_tag'].startswith('v{}'.format(version_macro)) or \
                re.match(r'^v\d', release['spec_tag']):
            release['spec_tag_no_prefix'] = release['spec_tag'].lstrip('v')
        else:
            release['spec_tag_no_prefix'] = release['spec_tag']
        release['tag_name'] = tag
        if hasattr(s, 'repo_license'):
            release['license'] = s.repo_license(tag)
        if hasattr(s, 'repo_readme'):
            release['readme'] = s.repo_readme(tag)
        release.update(repo_data)
        release['assets'] = s.get_assets(release, short_urls, assets_filter)
        return release

    if output_format == 'assets':
        return s.get_assets(release, short_urls, assets_filter)

    if output_format == 'source':
        return s.release_download_url(release, short_urls)

    if output_format == 'tag':
        return tag

    return None


def has_update(repo, current_version, pre_ok=False):
    latest_version = latest(repo, output_format='version', pre_ok=pre_ok)
    if latest_version and latest_version > Version(current_version):
        return latest_version
    return False


def check_version(value):
    """
    Argument parser helper for --newer-than (-gt) option
    :param value:
    :type value:
    :return:
    :rtype:
    """
    try:
        # TODO use sanitize_version so that we can just pass tags as values
        # help devel releases to be correctly identified
        # https://www.python.org/dev/peps/pep-0440/#developmental-releases
        value = re.sub('-devel$', '.dev0', value, 1)
        # help post (patch) releases to be correctly identified (e.g. Magento 2.3.4-p2)
        value = re.sub('-p(\\d+)$', '.post\\1', value, 1)
        value = Version(value)
    except InvalidVersion:
        raise argparse.ArgumentTypeError("%s is an invalid version value" % value)
    return value


def parse_version(tag):
    h = ProjectHolder()
    return h.sanitize_version(tag, pre_ok=True)


def main():
    epilog = None
    if "GITHUB_API_TOKEN" not in os.environ:
        epilog = 'ProTip: set GITHUB_API_TOKEN env var as per ' \
                 'https://github.com/dvershinin/lastversion#tips'
    parser = argparse.ArgumentParser(description='Find the latest release from '
                                                 'GitHub/GitLab/BitBucket.',
                                     epilog=epilog,
                                     prog='lastversion')
    parser.add_argument('action', nargs='?', default='get', help='Special action to run, '
                                                                 'e.g. download, install, test')
    parser.add_argument('repo', metavar='<repo or URL>',
                        help='GitHub/GitLab/BitBucket repository in format owner/name or any URL '
                             'that belongs to it')
    # affects what is considered last release
    parser.add_argument('--pre', dest='pre', action='store_true',
                        help='Include pre-releases in potential versions')
    parser.add_argument('--verbose', dest='verbose', action='store_true',
                        help='Will give you idea of what is happening under the hood')
    # no --download = False, --download filename.tar, --download = None
    parser.add_argument('-d', '--download', dest='download', nargs='?', default=False, const=None,
                        metavar='FILENAME', help='Download with custom filename')
    # how / which data of last release we want to present
    # assets will give download urls for assets if available and sources archive otherwise
    # sources will give download urls for sources always
    # json always includes "version", "tag_name" etc + whichever json data was
    # used to satisfy lastversion
    parser.add_argument('--format',
                        choices=['version', 'assets', 'source', 'json', 'tag'],
                        help='Output format')
    parser.add_argument('--assets', dest='assets', action='store_true',
                        help='Returns assets download URLs for last release')
    parser.add_argument('--source', dest='source', action='store_true',
                        help='Returns only source URL for last release')
    parser.add_argument('-gt', '--newer-than', type=check_version, metavar='VER',
                        help="Output only if last version is newer than given version")
    parser.add_argument('-b', '--major', '--branch', metavar='MAJOR',
                        help="Only consider releases of a specific major "
                             "version, e.g. 2.1.x")
    parser.add_argument('--only', metavar='ONLY', help="Only consider releases containing this "
                                                       "text. Useful for repos with multiple "
                                                       "projects inside")
    parser.add_argument('--filter', metavar='REGEX', help="Filters --assets result by a regular "
                                                          "expression")
    parser.add_argument('-su', '--shorter-urls', dest='shorter_urls', action='store_true',
                        help='A tiny bit shorter URLs produced')
    parser.add_argument('-y', '--assumeyes', dest='assumeyes', action='store_true',
                        help='Automatically answer yes for all questions')
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(version=__version__))
    parser.set_defaults(validate=True, verbose=False, format='version',
                        pre=False, assets=False, newer_than=False, filter=False,
                        shorter_urls=False, major=None, ssumeyes=False)
    args = parser.parse_args()

    if args.repo == "self":
        args.repo = "dvershinin/lastversion"

    # instead of using root logger, we use
    logger = logging.getLogger('lastversion')
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    # create formatter
    fmt = '%(name)s - %(levelname)s - %(message)s' if args.verbose else '%(levelname)s: %(message)s'
    formatter = logging.Formatter(fmt)
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        log.info("Verbose output.")

    if args.assets:
        args.format = 'assets'

    if args.source:
        args.format = 'source'

    if args.filter:
        args.filter = re.compile(args.filter)

    if args.action == 'test':
        print(parse_version(args.repo))
        # TODO dynamic exit status
        sys.exit(0)

    if args.action == 'install':
        # we can only install assets
        args.format = 'json'

    # imply source download, unless --assets specified
    # --download is legacy flag to specify download action or name of desired download file
    # --download == None indicates download intent where filename is based on upstream
    if args.action == 'download':
        if args.download is False:
            args.download = None

    if args.download is not False:
        args.action = 'download'
        if args.format != 'assets':
            args.format = 'source'

    # other action are either getting release or doing something with release (extend get action)
    try:
        res = latest(args.repo, args.format, args.pre, args.filter,
                     args.shorter_urls, args.major, args.only)
    except (ApiCredentialsError, BadProjectError) as error:
        sys.stderr.write(str(error) + os.linesep)
        sys.exit(4)

    if res:
        # download command
        if args.action == 'download':
            if args.format == 'source':
                # there is only one source, but we need an array
                res = [res]
            for url in res:
                log.info("Downloading {} ...".format(url))
                # there can be many assets, so we do not "rename" them
                # there can be only one source, so we allow passing custom filename for it
                download_file(url, args.download if args.format == 'source' else None)
            sys.exit(0)

        if args.action == 'install':
            rpms = [asset for asset in res['assets'] if asset.endswith('.rpm')]
            if not rpms:
                log.error('No assets found to install')
                sys.exit(1)
            # prevents downloading large packages if we already have newest installed
            # consult RPM database  for current version
            installed_version = rpm_installed_version(args.repo)
            if installed_version is False:
                log.warning('Please install lastversion using YUM or DNF so it can check current '
                            'program version. This is helpful to prevent unnecessary downloads')
            if installed_version and Version(installed_version) >= Version(res['version']):
                log.warning('Newest version {} is already installed'.format(installed_version))
                sys.exit(0)
            # pass RPM URLs directly to package management program
            try:
                import subprocess
                params = ['yum', 'install']
                params.extend(rpms)
                if args.assumeyes:
                    params.append('-y')
                subprocess.call(params)
            except OSError:
                log.critical('Failed to launch package manager. Only YUM/DNF is supported!')
                sys.exit(1)
            # if the system has yum, then lastversion has to be installed from yum and
            # has access to system packages like yum python or dnf python API
            # if install_with_dnf(rpms) is False or install_with_yum(rpms) is False:
            #     log.error('Failed talking to either DNF or YUM for package install')
            #     sys.exit(1)
            sys.exit(0)

        # display version in various formats:
        if args.format == 'assets':
            print("\n".join(res))
        elif args.format == 'json':
            json.dump(res, sys.stdout)
        else:
            print(res)
            # special exit code "2" is useful for scripting to detect if no newer release exists
            if args.newer_than:
                if res <= args.newer_than:
                    sys.exit(2)
    else:
        # empty list returned to --assets, emit 3
        if args.format == 'assets' and res is not False:
            sys.exit(3)
        sys.stderr.write("No release was found" + os.linesep)
        sys.exit(1)


if __name__ == "__main__":
    main()
