"""
lastversion
==========
License: BSD, see LICENSE for more details.
"""

import requests, argparse, sys
from bs4 import BeautifulSoup
from packaging.version import Version, InvalidVersion

def latest(repo, sniff = True, validate = True):

    version = None

    if sniff:

        # Start by fetching HTML of releases page (screw you, Github!)
        response = requests.get("https://github.com/{}/releases".format(repo), headers={'Connection': 'close'})
        html = response.text

        soup = BeautifulSoup(html, 'html.parser')

        # this tag is known to hold collection of releases not exposed through API
        taggedReleases = soup.find(class_='release-timeline-tags')
        if taggedReleases:
            latest = taggedReleases.find(class_='release-entry')
            version = latest.find("a").text.strip()

    if not version:

        r = requests.get('https://api.github.com/repos/{}/releases/latest'.format(repo), headers={'Connection': 'close'})
        if r.status_code == 200:
            version = r.json()['tag_name']
        else:
            sys.stderr.write(r.text)
            return None;

    # sanitize version tag:
    version = version.lstrip("v").rstrip("-beta").rstrip("-stable");

    if validate:
        try:
            v = Version(version)
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