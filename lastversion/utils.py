"""Utility functions for lastversion."""
import errno
import io
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.parse import unquote

import distro
import requests
import tqdm

from .exceptions import TarPathTraversalException

PY7ZR_AVAILABLE = False
try:
    # noinspection PyUnresolvedReferences
    import py7zr

    PY7ZR_AVAILABLE = True
except ImportError:
    pass

RPM_AVAILABLE = False
try:
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    import rpm

    RPM_AVAILABLE = True
except ImportError:
    pass

log = logging.getLogger(__name__)
content_disposition_regex = re.compile(
    r"filename(?P<priority>\*)?=((?P<encoding>[\S-]+)'')?(?P<filename>[^;]*)"
)

# matches os.name to known extensions that are meant *mostly* to run on it,
# and not other os.name-s
os_extensions = {
    "nt": (".exe", ".msi", ".msi.asc", ".msi.sha256"),
    "posix": (".tgz", ".tar.gz"),
}

extension_distros = {
    "deb": ["ubuntu", "debian"],
    "rpm": ["rhel", "centos", "fedora", "amazon", "cloudlinux"],
    "apk": ["alpine"],
    "dmg": ["darwin"],
}

# matches *start* of sys.platform value to words in asset name
platform_markers = {
    "win": ["windows", "win"],
    "linux": ["linux"],
    "darwin": ["osx", "darwin"],
    "freebsd": ["freebsd", "netbsd", "openbsd"],
}

# this is all too simple for now
# noinspection SpellCheckingInspection
non_amd64_markers = [
    "i386",
    "i686",
    "arm",
    "arm64",
    "386",
    "ppc64",
    "armv7",
    "armv7l",
    "mips64",
    "ppc64",
    "mips64le",
    "ppc64le",
    "aarch64",
    "armhf",
    "armv7hl",
]


def is_file_ext_not_compatible_with_os(file_ext):
    """
    Check if the file extension is not compatible with the OS
    Returns:

    """
    return any(
        os.name != os_name and file_ext == ext for os_name, ext in os_extensions.items()
    )


def is_asset_name_compatible_with_platform(asset_name):
    """Check if an asset has words that indicate it's not for this platform."""
    for platform_name, pf_words in platform_markers.items():
        if not sys.platform.startswith(platform_name):
            for pf_word in pf_words:
                regex = re.compile(rf"\b{pf_word}(\d+)?\b", flags=re.IGNORECASE)
                matches = regex.search(asset_name)
                if matches:
                    return True
    return False


def is_not_compatible_to_distro(asset_ext):
    """
    Check if the file extension is not compatible with the current distro.
    The function supports only Linux distros.
    """
    if not sys.platform.startswith("linux"):
        return False
    # Weeding out non-matching Linux distros
    if asset_ext != "AppImage":
        for ext, ext_distros in extension_distros.items():
            if asset_ext == ext and distro.id() not in ext_distros:
                return True

    return False


def is_not_compatible_bitness(asset_name):
    """Check if an asset has words that show it's not meant for 64-bit OS"""
    if platform.machine() not in ["x86_64", "AMD64"]:
        return False
    for non_amd64_word in non_amd64_markers:
        regex = re.compile(rf"\b{non_amd64_word}\b", flags=re.IGNORECASE)
        if regex.search(asset_name):
            return True
        regex = re.compile(r"\barm\d+\b", flags=re.IGNORECASE)
        if regex.search(asset_name):
            return True
    return False


def asset_does_not_belong_to_machine(asset_name):
    """
    Check if an asset's name contains words that indicate it's not meant for
    this machine

    Args:
        asset_name (str): Base name of asset, e.g. `example.zip`

    Returns:

    """
    # replace underscore with dash so that our shiny word boundary regexes
    # won't break
    asset_name = asset_name.replace("_", "-")
    asset_ext = os.path.splitext(asset_name)[1].lstrip(".")

    if not asset_ext:
        # We don't know. Maybe compatible, maybe not. Let's not filter it out.
        return False

    # Bail if asset's extension "belongs" to other OS (simple)
    if is_file_ext_not_compatible_with_os(asset_ext):
        return True

    if is_asset_name_compatible_with_platform(asset_name):
        return True

    # Bail if asset's extension "belongs" to other linux distros (complex)
    if is_not_compatible_to_distro(asset_ext):
        return True

    # weed out non-64 bit stuff from x86_64 bit OS
    # caution: may be false positive with 32-bit Python on 64-bit OS
    if is_not_compatible_bitness(asset_name):
        return True

    return False


def requests_response_patched_enter(self):
    """
    Monkey patching older requests library's response class, so it can use
    context manager.
    See https://github.com/psf/requests/issues/4136
    Args:
        self:

    Returns:

    """
    return self


# noinspection PyUnusedLocal
# pylint: disable=unused-argument
def requests_response_patched_exit(self, *args):
    """Patched exit method for requests.Response"""
    self.close()


if not hasattr(requests.Response, "__exit__"):
    requests.Response.__enter__ = requests_response_patched_enter
    requests.Response.__exit__ = requests_response_patched_exit


def extract_appimage_desktop_file(appimage_path):
    """Extracts the desktop file from an AppImage

    Args:
        appimage_path (str): Path to the AppImage

    Returns:
        str: Path to the extracted desktop file

    """
    temp_dir = tempfile.mkdtemp()

    # Extract the contents of the AppImage file to a temporary directory
    subprocess.call([appimage_path, "--appimage-extract"], cwd=temp_dir)

    # Search the temporary directory for the .desktop file
    desktop_file = None
    for root, _, files in os.walk(temp_dir):
        for file in files:
            if file.endswith(".desktop"):
                desktop_file = os.path.join(root, file)
                break
        if desktop_file:
            break

    # Install the .desktop file
    if desktop_file:
        # if xdg-desktop-menu is not available, we can't install the
        # .desktop file
        xdg_desktop_menu_path = shutil.which("xdg-desktop-menu")
        if xdg_desktop_menu_path:
            subprocess.call([xdg_desktop_menu_path, "install", desktop_file])
        else:
            log.warning(
                "xdg-desktop-menu is not available, can't install the " ".desktop file"
            )

    # Remove the temporary directory
    shutil.rmtree(temp_dir)


def get_content_disposition_filename(response):
    """Get the preferred filename from the `Content-Disposition` header.

    Examples:
        `attachment; filename="emulation-station-de-2.0.0-x64.deb";
        filename*=UTF-8''emulation-station-de-2.0.0-x64.deb`

    """
    filename = None
    content_disp = response.headers.get("content-disposition")
    if not content_disp or not content_disp.startswith("attachment;"):
        return None
    for match in re.finditer(content_disposition_regex, content_disp):
        filename = match.group("filename")
        encoding = match.group("encoding")
        if encoding:
            filename = unquote(filename)
            filename = filename.encode(encoding).decode("utf-8")
        if match.group("priority"):
            break
    return filename


def download_file(url, local_filename=None):
    """Download a URL to the given filename.

    Args:
        url (str): URL to download from
        local_filename (str, optional): Destination filename
            Defaults to current directory plus base name of the URL.
    Returns:
        str: Destination filename, on success

    """
    if local_filename is None:
        local_filename = url.split("/")[-1]
    try:
        # Note that the stream=True parameter below
        with requests.get(url, stream=True, timeout=5) as response:
            response.raise_for_status()
            if "." not in local_filename and "Content-Disposition" in response.headers:
                disp_filename = get_content_disposition_filename(response)
                if disp_filename:
                    local_filename = disp_filename
            # content-length may be empty, default to 0
            file_size = int(response.headers.get("Content-Length", 0))
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
                unit="KB",
                desc=f"Downloading {local_filename}",
                leave=True,  # progressbar stays
            )
            with open(local_filename, "wb") as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # filter out keep-alive new chunks
                        file.write(chunk)
                        # we fetch 8 KB, so we update progress by +8x
                        pbar.update(chunk_bar_size)
            pbar.set_description(f"Downloaded {local_filename}")
            pbar.close()
    except KeyboardInterrupt:
        pbar.close()
        os.remove(local_filename)
        log.warning("Cancelled")
        sys.exit(1)
    return local_filename


def is_within_directory(directory, target):
    """Check if the target path is within the directory path."""
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
            raise TarPathTraversalException("Attempted Path Traversal in Tar File")

    tar.extractall(path, members)


def extract_tar(buffer, mode):
    """Extract a tar archive while stripping the top level dir.

    Args:
        buffer ():
        mode ():
    """
    smart_members = []
    with tarfile.open(fileobj=buffer, mode=mode) as tar_file:
        all_members = tar_file.getmembers()
        if not all_members:
            log.critical("No or not an archive")
        root_dir = all_members[0].path
        root_dir_with_slash_len = len(root_dir) + 1
        for member in tar_file.getmembers():
            if member.path.startswith(root_dir + "/"):
                member.path = member.path[root_dir_with_slash_len:]
                smart_members.append(member)
        safe_extract(tar_file, members=smart_members)


def extract_file(url):
    """Extract an archive while stripping the top level dir."""
    if url.endswith(".7z") and not PY7ZR_AVAILABLE:
        log.critical("pip install py7zr to support .7z archives")
        return
    try:
        with requests.get(url, stream=True, timeout=5) as response:
            response.raise_for_status()
            # Download the file in chunks and save it to a memory buffer
            # content-length may be empty, default to 0
            file_size = int(response.headers.get("Content-Length", 0))
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
                unit="KB",
                desc=url.split("/")[-1],
            ) as pbar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        buffer.write(chunk)
                        pbar.update(chunk_bar_size)

            # Process the file in memory (e.g., extract its contents)
            buffer.seek(0)
            # Process the buffer (e.g., extract its contents)

            mode = "r:gz"
            if url.endswith(".tar.xz"):
                mode = "r:xz"
            elif url.endswith(".7z"):
                if PY7ZR_AVAILABLE:
                    with py7zr.SevenZipFile(buffer) as archive:
                        archive.extractall()
                return  # Exit the function after extracting
            extract_tar(buffer, mode)
    except KeyboardInterrupt:
        pbar.close()
        log.warning("Cancelled")
        sys.exit(1)


def rpm_installed_version(name):
    """Get the installed version of a package with the given name.

    Args:
        name (str): Package name

    Returns:
        string: Version of the installed packaged, or None
    """
    if not RPM_AVAILABLE:
        return False
    transaction_set = rpm.TransactionSet()
    match_iterator = transaction_set.dbMatch("name", name)
    if match_iterator:
        for header in match_iterator:
            return header["version"]
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
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
