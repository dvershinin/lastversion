"""
lastversion
==========
License: BSD, see LICENSE for more details.
"""

import requests
import argparse
import sys
import os
import re
import json
from bs4 import BeautifulSoup
from packaging.version import Version, InvalidVersion
import logging as log  # for verbose output
from __about__ import __version__


def sanitize_version(version):
    """extract what appears to be the version information"""
    s = re.search(r'([0-9]+([.][0-9]+)+)', version)
    if s:
        return s.group(1)
    else:
        return version.strip()


def latest(repo, sniff=True, validate=True, format='version', pre=False):

    # data that we may collect further
    version = None
    description = None
    # set this when an API returns json
    data = None

    # Some special non-Github cases for our repository are handled by checking URL

    # 1. nginx version is taken as version of stable (written by rpm check script)
    # to /usr/local/share/builder/nginx-stable.ver
    if repo.startswith('http://nginx.org/') or repo.startswith('https://nginx.org/'):
        with open('/usr/local/share/builder/nginx-stable.ver', 'r') as file:
            version = file.read().replace('\n', '')

    # 2. monit version can be obtained from Bitbucket downloads section of the project
    elif repo.startswith('https://mmonit.com/'):
        # Special case Monit repo
        response = requests.get(
            "https://api.bitbucket.org/2.0/repositories/{}/downloads".format("tildeslash/monit"),
            headers={'Connection': 'close'})
        data = response.json()
        version = sanitize_version(data['values'][0]['name'])

    # 3. Everything else is GitHub passed as owner/repo
    else:
        # But if full link specified, strip it to owner/repo
        if repo.startswith('https://github.com/'):
            repo = "/".join(repo.split('/')[3:5])

        if sniff:
            # Start by fetching HTML of releases page (screw you, Github!)
            response = requests.get(
                "https://github.com/{}/releases".format(repo),
                headers={'Connection': 'close'})
            html = response.text

            log.info("Parsing HTML of releases page...")
            soup = BeautifulSoup(html, 'lxml')

            r = soup.find(class_='release-entry')
            while r:
                # this tag is known to hold collection of releases not exposed through API
                if 'release-timeline-tags' in r['class']:
                    for release in r.find_all(class_='release-entry', recursive=False):
                        # dotted (collapsed) section of release entries has nothing to look at:
                        release_a = release.find("a")
                        if not release_a:
                            continue
                        the_version = release_a.text
                        the_version = sanitize_version(the_version)
                        # check if version is ok and not a prerelease; move on to next tag otherwise
                        if validate:
                            try:
                                v = Version(the_version)
                                if not v.is_prerelease or pre:
                                    version = the_version
                                    break
                            except InvalidVersion:
                                # move on to next thing to parse it
                                continue
                        else:
                            version = the_version
                            break
                else:
                    # formal release
                    if pre:
                        label_latest = r.find(class_='label-prerelease', recursive=False)
                    else:
                        label_latest = r.find(class_='label-latest', recursive=False)
                    if label_latest:
                        the_version = r.find(class_='css-truncate-target').text
                        if not pre:
                            the_version = sanitize_version(the_version)
                        # trust this to be the release and validate below
                        version = the_version
                        if format == 'json':
                            description = r.find(class_='markdown-body')
                            if not description:
                                description = r.find(class_='commit-desc')
                            if description:
                                description = description.text
                        break
                r = r.find_next_sibling(class_='release-entry', recursive=False)

        if not version:
            headers = {'Connection': 'close'}
            api_token = os.getenv("GITHUB_API_TOKEN")
            if api_token:
                headers['Authorization'] = "token {}".format(api_token)

            r = requests.get(
                'https://api.github.com/repos/{}/releases/latest'.format(repo),
                headers=headers)
            if r.status_code == 200:
                version = r.json()['tag_name']
                version = sanitize_version(version)
            else:
                sys.stderr.write(r.text)
                return None

    if validate:
        try:
            Version(version)
        except InvalidVersion:
            sys.stderr.write('Got invalid version: {}'.format(version))
            return None

    # return the release if we've reached far enough:
    if format == 'version':
        return version
    elif format == 'json':
        if not data:
            data = {}
        if description:
            description = description.strip()
        data['version'] = version
        data['description'] = description
        return json.dumps(data)


def main():
    parser = argparse.ArgumentParser(description='Get latest release from GitHub.')
    parser.add_argument('repo', metavar='REPO',
                        help='GitHub repository in format owner/name')
    parser.add_argument('--nosniff', dest='sniff', action='store_false',
                        help='Only use GitHub API, no HTML parsing (worse)')
    parser.add_argument('--novalidate', dest='validate', action='store_false')
    parser.add_argument('--pre', dest='pre', action='store_true',
                        help='Include pre-releases in potential versions')
    parser.add_argument('--verbose', dest='verbose', action='store_true')
    parser.add_argument('--format',
                        choices=['json', 'version'],
                        help='Output format')
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(version=__version__))
    parser.set_defaults(sniff=True, validate=True, verbose=False, format='version', pre=False)
    args = parser.parse_args()

    if args.verbose:
        log.basicConfig(format="%(levelname)s: %(message)s", level=log.DEBUG)
        log.info("Verbose output.")
    else:
        log.basicConfig(format="%(levelname)s: %(message)s")

    version = latest(args.repo, args.sniff, args.validate, args.format, args.pre)

    if version:
        print(version)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
