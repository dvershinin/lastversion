#!/usr/bin/python

import requests, argparse, sys
from bs4 import BeautifulSoup
from packaging.version import Version, InvalidVersion

parser = argparse.ArgumentParser(description='Get latest release from GitHub.')
parser.add_argument('repo', metavar='R',
                    help='GitHub repository in format owner/name')
parser.add_argument('--nosniff', dest='sniff', action='store_false')
parser.add_argument('--novalidate', dest='validate', action='store_false')
parser.set_defaults(sniff=True, validate=True)
args = parser.parse_args()

repo = args.repo

version = None

if args.sniff:

  # Start by fetching HTML of releases page (screw you, Github!)
  response = requests.get("https://github.com/{}/releases".format(repo))
  html = response.text

  soup = BeautifulSoup(html, 'html.parser')

  # this tag is known to hold collection of releases not exposed through API
  taggedReleases = soup.find(class_='release-timeline-tags')
  if taggedReleases:
    latest = taggedReleases.find(class_='release-entry')
    version = latest.find("a").text.strip()

if not version:

  r = requests.get('https://api.github.com/repos/{}/releases/latest'.format(repo))
  if r.status_code == 200:
    version = r.json()['tag_name']
  else:
    sys.stderr.write(r.text)
    sys.exit(1)

# sanitize version tag:
version = version.lstrip("v").rstrip("-beta").rstrip("-stable");

if args.validate:
  try:
    v = Version(version)
  except InvalidVersion:
    print('Got invalid version: {}'.format(version))
    sys.exit(1)

# output the version if we've reached far enough:
print(version)