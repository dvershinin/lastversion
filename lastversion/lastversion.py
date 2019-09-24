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

import dateutil.parser
import requests
from appdirs import user_cache_dir
from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache
from packaging.version import Version, InvalidVersion

from .__about__ import __version__

windowsAssetMarkers = ('.exe', '-win32.exe', '-win64.exe', '-win64.zip')
posixAssetMarkers = ('.tar.gz', '-linux32', '-linux64')
darwinAssetMarkers = ('-osx-amd64', '-darwin-amd64.tar')


def github_tag_download_url(hostname, repo, tag, shorter=False):
    """ The following format will benefit from:
    1) not using API, so is not subject to its rate limits
    2) likely has been accessed by someone in CDN and thus faster
    3) provides more or less unique filenames once the stuff is downloaded
    See https://fedoraproject.org/wiki/Packaging:SourceURL#Git_Tags
    We use variation of this: it does not need a parsed version (thus works for --pre better)
    and it is not broken on fancy release tags like v1.2.3-stable
    https://github.com/OWNER/PROJECT/archive/%{gittag}/%{gittag}-%{version}.tar.gz
    """
    ext = 'tar.gz' if "https://{}/{}/archive/{}/{}-{}.tar.gz" else 'zip'
    format = 'https://{}/{}/archive/{}/{}-{}.{}'
    if shorter:
        format = 'https://{}/{}/archive/{}.{}'
        return format.format(hostname, repo, tag, ext)
    else:
        return format.format(hostname, repo, tag, repo.split('/')[1], tag, ext)


def sanitize_version(version, pre_ok=False):
    """extract version from tag name"""
    log.info("Checking tag {} as version.".format(version))
    try:
        v = Version(version)
        if not v.is_prerelease or pre_ok:
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


def latest(repo, output_format='version', pre=False, newer_than=False, assets_filter=False,
           shortUrls=False):

    # data that we may collect further
    # the main thing, we're after - parsed version number, e.g. 1.2.3 (no extras chars)
    version = None
    # corresponding tag name, e.g. v1.2.3 or v1.2.3-stable (extra chars OK,
    # used for constructing non-API tar download URLs)
    tag = None
    description = None
    # set this when an API returns json
    data = None
    license = None
    # date of selected release, used in checks
    # github API returns tags NOT in chronological order
    # so if author switched from v20150121 (old) to v2.0.1 format, the old value is "higher"
    # so we have to check if a tag is actually newer, this is very slow but we have to accept :)
    tagDate = None

    headers = {}
    cache_dir = user_cache_dir("lastversion")
    log.info("Using cache directory: {}.".format(cache_dir))
    # Some special non-Github cases for our repository are handled by checking URL

    # 1. nginx version is taken as version of stable (written by rpm check script)
    # to /usr/local/share/builder/nginx-stable.ver
    if repo.startswith(('http://nginx.org/', 'https://nginx.org/')):
        with open('/usr/local/share/builder/nginx-stable.ver', 'r') as file:
            return file.read().replace('\n', '')

    # 2. monit version can be obtained from Bitbucket downloads section of the project
    elif repo.startswith('https://mmonit.com/'):
        with CacheControl(requests.Session(),
                          cache=FileCache(cache_dir)) as s:
            # Special case Monit repo
            response = s.get("https://api.bitbucket.org/2.0/repositories/{}/downloads".format(
                "tildeslash/monit"), headers=headers)
            data = response.json()
            s.close()
            return sanitize_version(data['values'][0]['name'])

    # 3. Everything else is GitHub passed as owner/repo
    else:
        # But if full link specified, strip it to owner/repo
        apiBase = 'https://api.github.com'
        githubHostname = 'github.com'
        if repo.startswith(('https://', 'http://')):
            urlParts = repo.split('/')
            githubHostname = urlParts[2]
            repo = urlParts[3] + "/" + urlParts[4]
            if 'github.com' != githubHostname:
                apiBase = "https://{}/api/v3".format(githubHostname)

        # Explicitly specify API version we want:
        # headers['Accept'] = "application/vnd.github.v3+json"

        api_token = os.getenv("GITHUB_API_TOKEN")
        if api_token:
            headers['Authorization'] = "token {}".format(api_token)

        with CacheControl(requests.Session(),
                          cache=FileCache(cache_dir)) as s:

            s.headers.update(headers)

            # search it :)
            if '/' not in repo:
                r = s.get(
                    '{}/search/repositories?q={}+in:name'.format(apiBase, repo),
                    headers=headers)
                repo = r.json()['items'][0]['full_name']

            # releases/latest fetches only non-prerelease, non-draft, so it
            # should not be used for hunting down pre-releases assets
            if not pre:
                # https://stackoverflow.com/questions/28060116/which-is-more-reliable-for-github-api-conditional-requests-etag-or-last-modifie/57309763?noredirect=1#comment101114702_57309763
                # ideally we disable ETag validation for this endpoint completely
                r = s.get(
                    '{}/repos/{}/releases/latest'.format(apiBase, repo),
                    headers=headers)
                if r.status_code == 200:
                    the_tag = r.json()['tag_name']
                    version = sanitize_version(the_tag, pre)
                    if version:
                        log.info("Set version as current selection: {}.".format(version))
                        tag = the_tag
                        data = r.json()
                        tagDate = dateutil.parser.parse(r.json()['published_at'])
            else:
                r = s.get(
                    '{}/repos/{}/releases'.format(apiBase, repo),
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
                            tagDate = dateutil.parser.parse(data['published_at'])

            # formal release may not exist at all, or be "late/old" in case
            # actual release is only a simple tag so let's try /tags

            r = s.get(
                '{}/repos/{}/tags'.format(apiBase, repo),
                headers=headers)
            if r.status_code == 200:
                for t in r.json():
                    the_tag = t['name']
                    the_version = sanitize_version(the_tag, pre)

                    r_commit = s.get(
                        '{}/repos/{}/git/commits/{}'.format(
                            apiBase, repo, t['commit']['sha']), headers=headers)
                    the_date = r_commit.json()['committer']['date']
                    the_date = dateutil.parser.parse(the_date)

                    if (the_version and ((not version) or (the_version > version))) \
                            or (not tagDate or the_date > tagDate):
                        # rare case: if upstream filed formal pre-release that passes as stable
                        # version (tag is 1.2.3 instead of 1.2.3b) double check if pre-release
                        # TODO handle API failure here as it may result in "false positive"?
                        if not pre:
                            r = s.get('{}/repos/{}/releases/tags/{}'.
                                      format(apiBase, repo, the_tag), headers=headers)
                            if r.status_code == 200:
                                if r.json()['prerelease']:
                                    log.info(
                                        "Found formal release for this tag which is unwanted "
                                        "pre-release: {}.".format(version))
                                    continue
                        version = the_version
                        log.info("Setting version as current selection: {}.".format(version))
                        tag = the_tag
                        tagDate = the_date
                        data = t
            else:
                sys.stderr.write(r.text)
                return None

            if output_format == 'json':
                r = s.get(
                    '{}/repos/{}/license'.format(apiBase, repo),
                    headers=headers)
                if r.status_code == 200:
                    license = r.json()
        s.close()

        # bail out, found nothing that looks like a release
        if not version:
            return False

        # special exit code "2" is useful for scripting to detect if no newer release exists
        if newer_than and not (version > newer_than):
            sys.exit(2)

        # return the release if we've reached far enough:
        if output_format == 'version':
            return str(version)
        elif output_format == 'json':
            if not data:
                data = {}
            if description:
                description = description.strip()
            data['version'] = str(version)
            data['description'] = description
            data['v_prefix'] = tag.startswith("v")
            data['spec_tag'] = tag.replace(str(version), "%{upstream_version}")
            data['tag_name'] = tag
            data['license'] = license
            return json.dumps(data)
        elif output_format == 'assets':
            urls = []
            if 'assets' in data and len(data['assets']) > 0:
                for asset in data['assets']:
                    if assets_filter:
                        if not re.search(assets_filter, asset['name']):
                            continue
                    else:
                        if os.name == 'nt' and asset['name'].endswith(
                                posixAssetMarkers + darwinAssetMarkers):
                            continue
                        # zips are OK for Linux, so we do some heuristics to weed out Windows stuff
                        if os.name == 'posix' and asset['name'].endswith(
                                darwinAssetMarkers + windowsAssetMarkers):
                            continue
                    urls.append(asset['browser_download_url'])
            else:
                download_url = github_tag_download_url(githubHostname, repo, tag, shortUrls)
                if not assets_filter or re.search(assets_filter, download_url):
                    urls.append(download_url)
            if not len(urls):
                sys.exit(3)
            else:
                return "\n".join(urls)
        elif output_format == 'source':
            return github_tag_download_url(githubHostname, repo, tag, shortUrls)


def check_version(value):
    try:
        value = Version(value)
    except InvalidVersion:
        raise argparse.ArgumentTypeError("%s is an invalid version value" % value)
    return value


def download_file(url, local_filename=None):
    if local_filename is None:
        local_filename = url.split('/')[-1]
    print("Downloading {}".format(local_filename))
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    # f.flush()
    return local_filename


def main():
    parser = argparse.ArgumentParser(description='Get latest release from GitHub.',
                                     prog='lastversion')
    parser.add_argument('repo', metavar='REPO',
                        help='GitHub repository in format owner/name')
    # affects what is considered last release
    parser.add_argument('--pre', dest='pre', action='store_true',
                        help='Include pre-releases in potential versions')
    parser.add_argument('--verbose', dest='verbose', action='store_true')
    # no --download = False, --download filename.tar, --download = None
    parser.add_argument('-d', '--download', dest='download', nargs='?', default=False, const=None)
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
    parser.add_argument('-su', '--shorter-urls', dest='shorter_urls', action='store_true',
                        help='A tiny bit shorter URLs produced')

    parser.set_defaults(validate=True, verbose=False, format='version', pre=False, assets=False,
                        newer_than=False, filter=False, shorter_urls=False)
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

    # imply source download, unless --assets specified
    if args.download is not False and args.format != 'assets':
        args.format = 'source'

    version = latest(args.repo, args.format, args.pre, args.newer_than, args.filter,
                     args.shorter_urls)

    if version:
        if args.download is not False:
            for url in version.splitlines():
                log.info("Downloading {} ...".format(url))
                # there can be many assets, so we do not "rename" them
                # there can be only one source, so we allow passing custom filename for it
                download_file(version, args.download if args.format == 'source' else None)
        else:
            print(version)
    else:
        sys.stderr.write("No release was found" + os.linesep)
        sys.exit(1)


if __name__ == "__main__":
    main()
