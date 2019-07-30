"""
lastversion
==========
License: BSD, see LICENSE for more details.
"""

import argparse
import json
import logging as log  # for verbose output
import os
import re
import sys

import requests
from appdirs import user_cache_dir
from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache
from packaging.version import Version, InvalidVersion

from .__about__ import __version__


def github_tag_download_url(repo, tag, version):
    """ The following format will benefit from:
    1) not using API, so is not subject to its rate limits
    2) likely has been accessed by someone in CDN and thus faster
    3) provides more or less unique filenames once the stuff is downloaded
    See https://fedoraproject.org/wiki/Packaging:SourceURL#Git_Tags
    We use variation of this: it does not need a parsed version (thus works for --pre better)
    and it is not broken on fancy release tags like v1.2.3-stable
    https://github.com/OWNER/PROJECT/archive/%{gittag}/%{gittag}-%{version}.tar.gz
    """
    if os.name != 'nt':
        return "https://github.com/{}/archive/{}/{}-{}.tar.gz".format(
            repo, tag, repo.split('/')[1], tag)
    else:
        return "https://github.com/{}/archive/{}/{}-{}.zip".format(
            repo, tag, repo.split('/')[1], tag)


windowsAssetMarkers = ('.exe', '-win32.exe', '-win64.exe', '-win64.zip')
posixAssetMarkers = ('.tar.gz', '-linux32', '-linux64')
darwingAssetMarkers = ('-osx-amd64')


def sanitize_version(version, preOk=False):
    """extract version from tag name"""
    log.info("Checking tag {} as version.".format(version))
    try:
        v = Version(version)
        if not v.is_prerelease or preOk:
            log.info("Parsed as Version OK")
            log.info("String representation of version is {}.".format(v))
            return v
        else:
            log.info("Parsed as unwated pre-release version: {}.".format(v))
            return False
    except InvalidVersion:
        log.info("Failed to parse tag as Version.")
        # attempt to remove extraneous chars and revalidate
        s = re.search(r'([0-9]+([.][0-9]+)+(rc[0-9]?)?)', version)
        if s:
            log.info("Sanitazied tag name value to {}.".format(s.group(1)))
            # we know regex is valid version format, so no need to try catch
            return Version(s.group(1))
        else:
            log.info("Did not find anything that looks like a version in the tag")
            return False


def latest(repo, format='version', pre=False, newer_than=False, filter=False):

    # data that we may collect further
    # the main thing, we're after - parsed version number, e.g. 1.2.3 (no extras chars)
    version = None
    # corresponding tag name, e.g. v1.2.3 or v1.2.3-stable (extra chars OK,
    # used for constructing non-API tar download URLs)
    tag = None
    description = None
    # set this when an API returns json
    data = None

    headers = {}
    cachedir = user_cache_dir("lastversion")
    log.info("Using cache directory: {}.".format(cachedir))
    # Some special non-Github cases for our repository are handled by checking URL

    # 1. nginx version is taken as version of stable (written by rpm check script)
    # to /usr/local/share/builder/nginx-stable.ver
    if repo.startswith('http://nginx.org/') or repo.startswith('https://nginx.org/'):
        with open('/usr/local/share/builder/nginx-stable.ver', 'r') as file:
            version = file.read().replace('\n', '')

    # 2. monit version can be obtained from Bitbucket downloads section of the project
    elif repo.startswith('https://mmonit.com/'):
        with CacheControl(requests.Session(),
                          cache=FileCache(cachedir)) as s:
            # Special case Monit repo
            response = s.get("https://api.bitbucket.org/2.0/repositories/{}/downloads".format(
                "tildeslash/monit"), headers=headers)
            data = response.json()
            version = sanitize_version(data['values'][0]['name'])
        s.close()

    # 3. Everything else is GitHub passed as owner/repo
    else:
        # But if full link specified, strip it to owner/repo
        if repo.startswith('https://github.com/'):
            repo = "/".join(repo.split('/')[3:5])

        api_token = os.getenv("GITHUB_API_TOKEN")
        if api_token:
            headers['Authorization'] = "token {}".format(api_token)

        with CacheControl(requests.Session(),
                          cache=FileCache(cachedir)) as s:

            s.headers.update(headers)

            # search it :)
            if '/' not in repo:
                r = s.get(
                    'https://api.github.com/search/repositories?q={}+in:name'.format(repo),
                    headers=headers)
                repo = r.json()['items'][0]['full_name']

            # releases/latest fetches only non-prerelease, non-draft, so it
            # should not be used for hunting down pre-releases assets
            if not pre:
                r = s.get(
                    'https://api.github.com/repos/{}/releases/latest'.format(repo),
                    headers=headers)
                if r.status_code == 200:
                    the_tag = r.json()['tag_name']
                    version = sanitize_version(the_tag, pre)
                    if version:
                        log.info("Set version as current selection: {}.".format(version))
                        tag = the_tag
                        data = r.json()
            else:
                r = s.get(
                    'https://api.github.com/repos/{}/releases'.format(repo),
                    headers=headers)
                if r.status_code == 200:
                    for release in r.json():
                        the_tag = release['tag_name']
                        the_version = sanitize_version(the_tag, pre)
                        if the_version and ((not version) or (the_version > version)):
                            version = the_version
                            log.info("Set version as current selection: {}.".format(version))
                            tag = the_tag
                            data = release

            # formal release may not exist at all, or be "late/old" in case
            # actual release is only a simple tag so let's try /tags

            r = s.get(
                'https://api.github.com/repos/{}/tags'.format(repo),
                headers=headers)
            if r.status_code == 200:
                for t in r.json():
                    the_tag = t['name']
                    the_version = sanitize_version(the_tag, pre)
                    if the_version and ((not version) or (the_version > version)):
                        version = the_version
                        log.info("Setting version as current selection: {}.".format(version))
                        tag = the_tag
                        data = t
            else:
                sys.stderr.write(r.text)
                return None

        s.close()

        # bail out, found nothing that looks like a release
        if not version:
            return False

        # special exit code "2" is useful for scripting to detect if no newer release exists
        if newer_than and not (version > newer_than):
            sys.exit(2)

        # return the release if we've reached far enough:
        if format == 'version':
            return str(version)
        elif format == 'json':
            if not data:
                data = {}
            if description:
                description = description.strip()
            data['version'] = str(version)
            data['description'] = description
            data['v_prefix'] = tag.startswith("v")
            data['spec_tag'] = tag.replace(str(version), "%{upstream_version}")
            return json.dumps(data)
        elif format == 'assets':
            urls = []
            if 'assets' in data and len(data['assets']) > 0:
                for asset in data['assets']:
                    if filter:
                        if not re.search(filter, asset['name']):
                            continue
                    else:
                        if os.name == 'nt' and asset['name'].endswith(posixAssetMarkers):
                            continue
                        # zips are OK for Linux, so we do some heuristics to weed out Windows stuff
                        if os.name == 'posix' and asset['name'].endswith(windowsAssetMarkers):
                            continue
                    urls.append(asset['browser_download_url'])
            else:
                download_url = github_tag_download_url(repo, tag, str(version))
                if not filter or re.search(filter, download_url):
                    urls.append(download_url)
            if not len(urls):
                sys.exit(3)
            else:
                return "\n".join(urls)
        elif format == 'source':
            return github_tag_download_url(repo, tag, str(version))


def check_version(value):
    try:
        value = Version(value)
    except InvalidVersion:
        raise argparse.ArgumentTypeError("%s is an invalid version value" % value)
    return value


def main():
    parser = argparse.ArgumentParser(description='Get latest release from GitHub.')
    parser.add_argument('repo', metavar='REPO',
                        help='GitHub repository in format owner/name')
    # affects what is considered last release
    parser.add_argument('--pre', dest='pre', action='store_true',
                        help='Include pre-releases in potential versions')
    parser.add_argument('--verbose', dest='verbose', action='store_true')
    # how / which data of last release we want to present
    # assets will give download urls for assets if available and sources archive otherwise
    # sources will give download urls for sources always
    # json always includes "version", "tag_name" etc + whichever json data was
    # used to satisfy lastversion
    parser.add_argument('--format',
                        choices=['version', 'assets', 'source', 'json'],
                        help='Output format')
    parser.add_argument('--assets', dest='assets', action='store_true',
                        help='Returns assets download URLs for last release')
    parser.add_argument('--source', dest='source', action='store_true',
                        help='Returns only source URL for last release')
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(version=__version__))
    parser.add_argument('-gt', '--newer-than', type=check_version, metavar='VER',
                        help="Output only if last version is newer than given version")
    parser.add_argument('--filter', metavar='REGEX', help="Filters --assets result by a regular "
                                                          "expression")

    parser.set_defaults(validate=True, verbose=False, format='version', pre=False, assets=False,
                        newer_than=False, filter=False)
    args = parser.parse_args()

    if args.repo == "self":
        args.repo = "dvershinin/lastversion"

    if args.verbose:
        log.basicConfig(format="%(levelname)s: %(message)s", level=log.DEBUG)
        log.info("Verbose output.")
    else:
        log.basicConfig(format="%(levelname)s: %(message)s")

    if args.assets:
        args.format = 'assets'

    if args.source:
        args.format = 'source'

    if args.filter:
        args.filter = re.compile(args.filter)

    version = latest(args.repo, args.format, args.pre, args.newer_than, args.filter)

    if version:
        print(version)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
