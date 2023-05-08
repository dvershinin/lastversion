import io
import logging
import os
import platform
import re
import sys
import tarfile
import errno
import distro
import requests
import tqdm
from six.moves import urllib

log = logging.getLogger(__name__)


class ApiCredentialsError(Exception):
    """Raised when there's an API error related to credentials"""


class BadProjectError(Exception):
    """Raised when no such project exists"""


# matches os.name to known extensions that are meant *mostly* to run on it, and not other os.name-s
os_extensions = {
    'nt': ('.exe', '.msi', '.msi.asc', '.msi.sha256'),
    'posix': ('.tgz', '.tar.gz')
}

extension_distros = {
    'deb': ['ubuntu', 'debian'],
    'rpm': ['rhel', 'centos', 'fedora', 'amazon', 'cloudlinux'],
    'apk': ['alpine'],
    'dmg': ['darwin']
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
                     'mips64', 'ppc64', 'mips64le', 'ppc64le', 'aarch64', 'armhf', 'armv7hl']


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
    if sys.platform.startswith('linux'):
        # Weeding out non-matching Linux distros
        for ext, ext_distros in extension_distros.items():
            if asset.endswith("." + ext) and distro.id() not in ext_distros:
                return True
    # weed out non-64 bit stuff from x86_64 bit OS
    # caution: may be false positive with 32 bit Python on 64-bit OS
    if platform.machine() in ['x86_64', 'AMD64']:
        for non_amd64_word in non_amd64_markers:
            r = re.compile(r'\b{}\b'.format(non_amd64_word), flags=re.IGNORECASE)
            if r.search(asset):
                return True
            r = re.compile(r'\barm\d+\b', flags=re.IGNORECASE)
            if r.search(asset):
                return True
    return False


# monkey patching older requests library's response class, so it can use context manager
# https://github.com/psf/requests/issues/4136
def requests_response_patched_enter(self):
    return self


# noinspection PyUnusedLocal
def requests_response_patched_exit(self, *args):
    self.close()


if not hasattr(requests.Response, '__exit__'):
    requests.Response.__enter__ = requests_response_patched_enter
    requests.Response.__exit__ = requests_response_patched_exit


def extract_appimage_desktop_file(appimage_path):
    """Extracts the desktop file from an AppImage

    Args:
        appimage_path (str): Path to the AppImage

    Returns:
        str: Path to the extracted desktop file

    """
    import shutil
    import subprocess
    import tempfile

    temp_dir = tempfile.mkdtemp()

    # Extract the contents of the AppImage file to a temporary directory
    subprocess.call([appimage_path, "--appimage-extract"], cwd=temp_dir)

    # Search the temporary directory for the .desktop file
    desktop_file = None
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.endswith(".desktop"):
                desktop_file = os.path.join(root, file)
                break
        if desktop_file:
            break

    # Copy the .desktop file to the current directory
    if desktop_file:
        shutil.copy(desktop_file, ".")

    # Remove the temporary directory
    shutil.rmtree(temp_dir)


def get_content_disposition_filename(response):
    """Get the preferred filename from the `Content-Disposition` header.

    Examples:
        `attachment; filename="emulationstation-de-2.0.0-x64.deb"; filename*=UTF-8''emulationstation-de-2.0.0-x64.deb`

    """
    filename = None
    content_disp = response.headers.get('content-disposition')
    if not content_disp or not content_disp.startswith('attachment;'):
        return None
    for m in re.finditer(r"filename(?P<priority>\*)?=((?P<encoding>[\S-]+)'')?(?P<filename>[^;]*)", content_disp):
        filename = m.group('filename')
        encoding = m.group('encoding')
        if encoding:
            filename = urllib.parse.unquote(filename)
            filename = filename.encode(encoding).decode('utf-8')
        if m.group('priority'):
            break
    return filename


def download_file(url, local_filename=None):
    """Download a URL to the given filename.

    Args:
        url (str): URL to download from
        local_filename (:obj:`str`, optional): Destination filename
            Defaults to current directory plus base name of the URL.
    Returns:
        str: Destination filename, on success

    """
    if local_filename is None:
        local_filename = url.split('/')[-1]
    try:
        # NOTE the stream=True parameter below
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            if '.' not in local_filename and 'Content-Disposition' in r.headers:
                disp_filename = get_content_disposition_filename(r)
                if disp_filename:
                    local_filename = disp_filename
            # content-length may be empty, default to 0
            file_size = int(r.headers.get('Content-Length', 0))
            bar_size = 1024
            # fetch 8 KB at a time
            chunk_size = 8192
            # how many bars are there in a chunk?
            chunk_bar_size = chunk_size / bar_size
            # bars are by KB
            num_bars = int(file_size / bar_size)

            # noinspection PyTypeChecker
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
        pbar.close()
        os.remove(local_filename)
        log.warning('Cancelled')
        sys.exit(1)
    return local_filename


def is_within_directory(directory, target):
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)

    prefix = os.path.commonprefix([abs_directory, abs_target])

    return prefix == abs_directory


def safe_extract(tar, path=".", members=None):
    """Safe extract .tar.gz to workaround CVE-2007-4559. CVE-2007-4559

    Args:
        tar ():
        path ():
        members ():
    """
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not is_within_directory(path, member_path):
            raise Exception("Attempted Path Traversal in Tar File")

    tar.extractall(path, members)


def extract_file(url):
    """Extract an archive while stripping the top level dir."""
    smart_members = []
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            # Download the file in chunks and save it to a memory buffer
            # content-length may be empty, default to 0
            file_size = int(r.headers.get('Content-Length', 0))
            bar_size = 1024
            # fetch 8 KB at a time
            chunk_size = 8192
            # how many bars are there in a chunk?
            chunk_bar_size = chunk_size / bar_size
            # bars are by KB
            num_bars = int(file_size / bar_size)

            buffer = io.BytesIO()
            # noinspection PyTypeChecker
            with tqdm.tqdm(
                disable=None,  # disable on non-TTY
                total=num_bars,
                unit='KB',
                desc=url.split('/')[-1]
            ) as pbar:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        buffer.write(chunk)
                        pbar.update(chunk_bar_size)

            # Process the file in memory (e.g. extract its contents)
            buffer.seek(0)
            # Process the buffer (e.g. extract its contents)

            mode = 'r:gz'
            if url.endswith('.tar.xz'):
                mode = 'r:xz'

            with tarfile.open(fileobj=buffer, mode=mode) as tar_file:
                all_members = tar_file.getmembers()
                if not all_members:
                    log.critical('No or not an archive')
                root_dir = all_members[0].path
                root_dir_with_slash_len = len(root_dir) + 1
                for member in tar_file.getmembers():
                    if member.path.startswith(root_dir + "/"):
                        member.path = member.path[root_dir_with_slash_len:]
                        smart_members.append(member)
                safe_extract(tar_file, members=smart_members)
    except KeyboardInterrupt:
        pbar.close()
        log.warning('Cancelled')
        sys.exit(1)


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


def ensure_directory_exists(directory_path):
    """
    Ensure that the given directory exists.
    Workaround for `exist_ok=True` not being available in Python 2.7.

    Args:
        directory_path (str):

    Returns:

    """

    try:
        os.makedirs(directory_path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
