import os
import platform
import re
import sys

import requests


class ApiCredentialsError(Exception):
    """raise this when there's a lookup error for my app"""


# matches os.name to known extensions that are meant *mostly* to run on it, and not other os.name-s
osExtensions = {
    'nt': '.exe',
    'posix': ('.tgz', '.tar.gz')
}

# matches *start* of sys.platform value to words in asset name
pfMarkers = {
    'win': ['windows', 'win'],
    'linux': ['linux'],
    'darwin': ['osx', 'darwin'],
    'freebsd': ['freebsd', 'netbsd', 'openbsd']
}

# matches platform.dist() ('redhat', '8.0', 'Ootpa') to words in asset name
# TODO use https://pypi.org/project/distro/
distroMarkers = {
    'centos': ['centos'],
    'redhat': ['centos', 'redhat']
}

# this is all too simple for now
nonAmd64Markers = ['i386', 'i686', 'arm', 'arm64', '386', 'ppc64', 'armv7',
                   'mips64', 'ppc64', 'mips64le', 'ppc64le']


def asset_does_not_belong_to_machine(asset):
    """
    Checks whether a given asset name is likely unusable on this machine
    An asset belongs to machine as long as this returns False
    :param asset:
    :type asset: str
    :return:
    :rtype:
    """
    # replace underscore with dash so that our shiny word boundary regexes won't break
    asset = asset.replace('_', '-')
    # bail if asset's extension "belongs" to other OS-es (simple)
    for osName, osExts in osExtensions.items():
        if os.name != osName and asset.endswith(osExts):
            return True
    # bail if asset's platform words belong to other platforms
    for pf, pfWords in pfMarkers.items():
        if not sys.platform.startswith(pf):
            for pfWord in pfWords:
                r = re.compile(r'\b{}(\d+)?\b'.format(pfWord), flags=re.IGNORECASE)
                matches = r.search(asset)
                if matches:
                    return True
    # weed out non-64 bit stuff from x86_64 bit OS
    # caution: may be false positive with 32 bit Python on 64 bit OS
    if platform.machine() in ['x86_64', 'AMD64']:
        for nonAmd64Word in nonAmd64Markers:
            r = re.compile(r'\b{}\b'.format(nonAmd64Word), flags=re.IGNORECASE)
            matches = r.search(asset)
            if matches:
                return True
            r = re.compile(r'\barm\d+\b', flags=re.IGNORECASE)
            matches = r.search(asset)
            if matches:
                return True
    # TODO weed out non-matching distros
    return False


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
