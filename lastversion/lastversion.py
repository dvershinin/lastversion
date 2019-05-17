"""
lastversion
==========
License: BSD, see LICENSE for more details.
"""

import requests
import argparse
import sys
from bs4 import BeautifulSoup
from packaging.version import Version, InvalidVersion


def sanitize_version(version):
    """strip some common prefixes and suffixes of non-beta packages to get clean version"""
    return version.strip().lstrip("v").replace("RELEASE.", "").replace("-stable", "")


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

        # this tag is known to hold collection of releases not exposed through API
        taggedReleases = soup.find(class_='release-timeline-tags')
        if taggedReleases:
            for release in taggedReleases.find_all(class_='release-entry'):
                the_version = release.find("a").text
                the_version = sanitize_version(the_version)
                # check if version is parseable non prerelease, and move on to next tag otherwise
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

    if not version:

        r = requests.get(
            'https://api.github.com/repos/{}/releases/latest'.format(repo),
            headers={'Connection': 'close'})
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
