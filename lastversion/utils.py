import logging
import os
import platform
import re
import sys

import requests
import tqdm

log = logging.getLogger(__name__)


class ApiCredentialsError(Exception):
    """raised when there's an API error related to credentials"""


class BadProjectError(Exception):
    """raised when no such project exists"""


# matches os.name to known extensions that are meant *mostly* to run on it, and not other os.name-s
os_extensions = {
    'nt': ('.exe', '.msi', '.msi.asc', '.msi.sha256'),
    'posix': ('.tgz', '.tar.gz')
}

extension_distros = {
    'deb': ['ubuntu', 'debian'],
    'rpm': ['rhel', 'centos', 'fedora', 'amazon', 'cloudlinux'],
    'apk': ['alpine'],
    'darwin': ['dmg']
}

# matches *start* of sys.platform value to words in asset name
platform_markers = {
    'win': ['windows', 'win'],
    'linux': ['linux'],
    'darwin': ['osx', 'darwin'],
    'freebsd': ['freebsd', 'netbsd', 'openbsd']
}

# this is all too simple for now
non_amd64_markers = ['i386', 'i686', 'arm', 'arm64', '386', 'ppc64', 'armv7', 'armv7l',
                     'mips64', 'ppc64', 'mips64le', 'ppc64le', 'aarch64']


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
    for os_name, ext in os_extensions.items():
        if os.name != os_name and asset.endswith(ext):
            return True
    for pf, pf_words in platform_markers.items():
        if not sys.platform.startswith(pf):
            for pfWord in pf_words:
                r = re.compile(r'\b{}(\d+)?\b'.format(pfWord), flags=re.IGNORECASE)
                matches = r.search(asset)
                if matches:
                    return True
    if sys.platform == 'linux':
        import distro
        # Weeding out non-matching Linux distros
        for ext, ext_distros in extension_distros.items():
            if asset.endswith("." + ext) and distro.id() not in ext_distros:
                return True
    # weed out non-64 bit stuff from x86_64 bit OS
    # caution: may be false positive with 32 bit Python on 64 bit OS
    if platform.machine() in ['x86_64', 'AMD64']:
        for non_amd64_word in non_amd64_markers:
            r = re.compile(r'\b{}\b'.format(non_amd64_word), flags=re.IGNORECASE)
            matches = r.search(asset)
            if matches:
                return True
            r = re.compile(r'\barm\d+\b', flags=re.IGNORECASE)
            matches = r.search(asset)
            if matches:
                return True
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
    """Download a URL to the given filename.

    Args:
        url (str): URL to download from
        local_filename (str): Destination filename

    Returns:
        str: Destination filename, on success

    """
    if local_filename is None:
        local_filename = url.split('/')[-1]
    try:
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
    except KeyboardInterrupt:
        os.remove(local_filename)
        log.warning('Cancelled')
        os._exit(1)
    return local_filename


def rpm_installed_version(name):
    """Get the installed version of a package with the given name.

    Args:
        name (str): Package name

    Returns:
        string: Version of the installed packaged, or None
    """
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
