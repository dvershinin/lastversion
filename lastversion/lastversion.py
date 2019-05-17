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
from bs4 import BeautifulSoup
from packaging.version import Version, InvalidVersion


def sanitize_version(version):
    """extract what appears to be the version information"""
    s = re.search(r'([0-9]+([.][0-9]+)+)', version)
    if s:
        return s.group(1)
    else:
        return version.strip()


def latest(repo, sniff=True, validate=True):

    version = None

    if repo.startswith('https://github.com/'):
        repo = "/".join(repo.split('/')[3:5])

    if sniff:

        # Start by fetching HTML of releases page (screw you, Github!)
        response = requests.get(
            "https://github.com/{}/releases".format(repo),
            headers={'Connection': 'close'})
        html = response.text

        soup = BeautifulSoup(html, 'lxml')

        r = soup.find(class_='release-entry')
        while r:
            # this tag is known to hold collection of releases not exposed through API
            if 'release-timeline-tags' in r['class']:
                for release in r.find_all(class_='release-entry', recursive=False):
                    the_version = release.find("a").text
                    the_version = sanitize_version(the_version)
                    # check if version is ok and not a prerelease; move on to next tag otherwise
                    if validate:
                        try:
                            v = Version(the_version)
                            if not v.is_prerelease:
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
                label_latest = r.find(class_='label-latest', recursive=False)
                if label_latest:
                    the_version = r.find(class_='css-truncate-target').text
                    the_version = sanitize_version(the_version)
                    # trust this to be the release and validate below
                    version = the_version
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

    # return the version if we've reached far enough:
    return version


def main():

    parser = argparse.ArgumentParser(description='Get latest release from GitHub.')
    parser.add_argument('repo', metavar='R',
                        help='GitHub repository in format owner/name')
    parser.add_argument('--nosniff', dest='sniff', action='store_false')
    parser.add_argument('--novalidate', dest='validate', action='store_false')
    parser.set_defaults(sniff=True, validate=True)
    args = parser.parse_args()

    version = latest(args.repo, args.sniff, args.validate)

    if version:
        print(version)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
