import os
import platform
import re
import sys

import requests
import tqdm


class ApiCredentialsError(Exception):
    """raised when there's an API error related to credentials"""


class BadProjectError(Exception):
    """raised when no such project exists"""


# matches os.name to known extensions that are meant *mostly* to run on it, and not other os.name-s
osExtensions = {
    'nt': ('.exe', '.msi', '.msi.asc', '.msi.sha256'),
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


# monkey patching older requests library's response class so it can use context manager
# https://github.com/psf/requests/issues/4136
def requests_response_patched_enter(self):
    return self


def requests_response_patched_exit(self, *args):
    self.close()


if not hasattr(requests.Response, '__exit__'):
    requests.Response.__enter__ = requests_response_patched_enter
    requests.Response.__exit__ = requests_response_patched_exit


def download_file(url, local_filename=None):
    if local_filename is None:
        local_filename = url.split('/')[-1]
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        # content-length may be empty, default to 0
        file_size = int(r.headers.get('Content-Length', 0))
        bar_size = 1024
        # fetch 8 KB at a time
        chunk_size = 8192
        # how many bars are there in a chunk?
        chunk_bar_size = chunk_size / bar_size
        # bars are by KB
        num_bars = int(file_size / bar_size)

        pbar = tqdm.tqdm(
            disable=None,  # disable on non-TTY
            total=num_bars,
            unit='KB',
            desc='Downloading {}'.format(local_filename),
            leave=True  # progressbar stays
        )
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    # we fetch 8 KB, so we update progress by +8x
                    pbar.update(chunk_bar_size)
        pbar.set_description('Downloaded {}'.format(local_filename))
        pbar.close()

    return local_filename


def rpm_installed_version(name):
    try:
        import rpm
    except ImportError:
        return False
    ts = rpm.TransactionSet()
    mi = ts.dbMatch('name', name)
    if mi:
        for h in mi:
            return h['version']
    return None
