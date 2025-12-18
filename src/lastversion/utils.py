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
import zipfile
from pathlib import Path
from urllib.parse import unquote

import distro
import requests
import tqdm

from lastversion.exceptions import TarPathTraversalException

# Global quiet mode flag - when True, suppresses progress bars and non-error output
QUIET_MODE = False

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

DOWNLOAD_TIMEOUT = 30

log = logging.getLogger(__name__)
content_disposition_regex = re.compile(r"filename(?P<priority>\*)?=((?P<encoding>\S+)'')?(?P<filename>[^;]*)")

# matches os.name to known extensions that are meant *mostly* to run on it,
# and not other os.name-s
os_extensions = {
    "nt": (".exe", ".msi", ".msi.asc", ".msi.sha256"),
    "posix": (".tgz", ".tar.gz"),
}

# Extensions exclusive to specific distros as per `distro.id()`
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

# Markers indicating x86_64/amd64 architecture
x86_64_markers = [
    "x86_64",
    "x86-64",
    "amd64",
    "x64",
]


def is_file_ext_not_compatible_with_os(file_ext):
    """
    Check if the file extension is not compatible with the OS
    Returns:

    """
    return any(os.name != os_name and file_ext == ext for os_name, ext in os_extensions.items())


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
    The function supports only Linux and OSX distros.
    """
    # Weeding out non-matching Linux distros
    if asset_ext != "AppImage":
        for ext, ext_distros in extension_distros.items():
            if asset_ext == ext and distro.id() not in ext_distros:
                return True

    return False


def is_not_compatible_bitness(asset_name):
    """Check if an asset has words that show it's not meant for this machine's arch.

    On x86_64/AMD64: filters out arm/aarch64/32-bit assets
    On aarch64/arm64: filters out x86_64/amd64 assets
    """
    machine = platform.machine()

    # On x86_64, filter out non-x86_64 assets
    if machine in ["x86_64", "AMD64"]:
        for non_amd64_word in non_amd64_markers:
            regex = re.compile(rf"\b{non_amd64_word}\b", flags=re.IGNORECASE)
            if regex.search(asset_name):
                return True
            # Also check for armNN patterns
            regex = re.compile(r"\barm\d+\b", flags=re.IGNORECASE)
            if regex.search(asset_name):
                return True

    # On aarch64/arm64, filter out x86_64 assets
    elif machine in ["aarch64", "arm64"]:
        for x86_word in x86_64_markers:
            regex = re.compile(rf"\b{x86_word}\b", flags=re.IGNORECASE)
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
            log.warning("xdg-desktop-menu is not available, can't install the .desktop file")

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
        with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as response:
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
                disable=QUIET_MODE or None,  # disable on non-TTY or in quiet mode
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


def check_if_tar_safe(tar_file: tarfile.TarFile) -> bool:
    """CVE-2007-4559"""
    all_members = tar_file.getnames()
    root_dir = Path(all_members[0]).parent.resolve()
    for member in all_members:
        member_path = Path(member).resolve()
        # Check if the member path resolves within the root directory
        if os.path.commonpath([member_path, root_dir]) != str(root_dir):
            return False
    return True


def extract_tar(buffer: io.BytesIO, to_dir):
    """Extract a tar/zip archive to dir.
    If the archive has only one top dir, it will be stripped.
    """

    archive_file: tarfile.TarFile
    with tarfile.open(fileobj=buffer, mode="r") as archive_file:
        if not check_if_tar_safe(archive_file):
            raise TarPathTraversalException("Attempted Path Traversal in Tar File")

        contents = archive_file.getmembers()
        assert contents, "Empty TAR archive"
        top_dir = Path(contents[0].name).resolve()
        only_one_top_dir = True
        # If the directory is .app, it's a macOS app bundle, don't strip it
        if not contents[0].isdir() or top_dir.name.endswith(".app"):
            only_one_top_dir = False
        if only_one_top_dir:
            for item in contents[1:]:
                item_path = Path(item.name).resolve()
                # Check if the item path resolves within the top directory
                if os.path.commonpath([item_path, top_dir]) != str(top_dir):
                    only_one_top_dir = False
                    break

        log.info("only one top dir: %s", only_one_top_dir)
        if only_one_top_dir:
            for item in contents[1:]:
                item.path = str(Path(item.name).resolve().relative_to(top_dir))
                archive_file.extract(item, to_dir)
        else:
            archive_file.extractall(path=to_dir)  # nosec B202 - trusted sources


def extract_zip(buffer: io.BytesIO, to_dir):
    """
    Extract a tar/zip archive to dir.
    If the archive has only one top dir, it will be stripped.
    """
    archive_file: zipfile.ZipFile
    with zipfile.ZipFile(buffer, "r") as archive_file:
        contents = archive_file.infolist()
        assert contents, "Empty archive"
        top_dir = Path(contents[0].filename).resolve()
        only_one_top_dir = True
        # If the directory is .app, it's a macOS app bundle, don't strip it
        if not contents[0].is_dir() or top_dir.name.endswith(".app"):
            only_one_top_dir = False
        if only_one_top_dir:
            for item in contents[1:]:
                item_path = Path(item.filename).resolve()
                # Check if the item path resolves within the top directory
                if os.path.commonpath([item_path, top_dir]) != str(top_dir):
                    only_one_top_dir = False
                    break
        log.info("only one top dir: %s", only_one_top_dir)
        if only_one_top_dir:
            for item in contents[1:]:
                new_path = str(Path(item.filename).resolve().relative_to(top_dir))
                if item.is_dir():
                    new_path += "/"
                item.filename = new_path
                archive_file.extract(item, to_dir)
        else:
            archive_file.extractall(path=to_dir)  # nosec B202 - trusted sources


def detect_archive_type(buffer: io.BytesIO, url: str) -> str:
    """Detect archive type by magic bytes or file extension.

    Args:
        buffer: File buffer to read magic bytes from.
        url: URL to fall back on extension detection.

    Returns:
        Archive type: '7z', 'zip', or 'tar' (for any tar variant).
    """
    # Read magic bytes
    magic = buffer.read(8)
    buffer.seek(0)

    # 7z magic: 37 7A BC AF 27 1C
    if magic[:6] == b"7z\xbc\xaf'\x1c":
        return "7z"
    # ZIP magic: 50 4B (PK)
    if magic[:2] == b"PK":
        return "zip"

    # Fall back to URL extension
    url_lower = url.lower()
    if url_lower.endswith(".7z"):
        return "7z"
    if url_lower.endswith(".zip"):
        return "zip"

    # Default to tar (handles .tar, .tar.gz, .tgz, .tar.bz2, .tar.xz, etc.)
    return "tar"


def extract_7z(buffer: io.BytesIO, to_dir):
    """
    Extract a 7z archive to dir.
    py7zr maybe hard to strip the top level dir.
    """
    if not PY7ZR_AVAILABLE:
        log.critical("pip install py7zr to support .7z archives")
        return
    with py7zr.SevenZipFile(buffer) as file:
        file.extractall(path=to_dir)  # nosec B202 - trusted sources


def extract_file(url: str, to_dir="."):
    """Extract an archive from url to dir, stripping the top level dir by default."""
    if url.endswith(".7z") and not PY7ZR_AVAILABLE:
        log.critical("pip install py7zr to support .7z archives")
        return
    try:
        with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as response:
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
                disable=QUIET_MODE or None,  # disable on non-TTY or in quiet mode
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
            # Detect archive type by magic bytes or extension
            archive_type = detect_archive_type(buffer, url)
            buffer.seek(0)

            if archive_type == "7z":
                extract_7z(buffer, to_dir=to_dir)
            elif archive_type == "zip":
                extract_zip(buffer, to_dir=to_dir)
            else:
                extract_tar(buffer, to_dir=to_dir)
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
