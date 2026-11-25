"""Cover tar extraction into a caller-supplied destination."""

import io
import os
import tarfile

import pytest

from lastversion.exceptions import TarPathTraversalException
from lastversion.utils import check_if_tar_safe, extract_tar


def tar_buffer(entries):
    """Build an in-memory tar with the given (name, type, link target) entries.

    Args:
        entries (list): Member descriptions in extraction order.

    Returns:
        io.BytesIO: Archive positioned for reading.
    """
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, kind, target in entries:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.linkname = target
            if member.isfile():
                member.size = 2
                archive.addfile(member, io.BytesIO(b"ok"))
            else:
                archive.addfile(member)
    buffer.seek(0)
    return buffer


@pytest.mark.parametrize("kind", [tarfile.SYMTYPE, tarfile.LNKTYPE])
def test_tar_rejects_absolute_link(tmp_path, kind):
    """Reject an absolute target using only a single dangling link."""
    buffer = tar_buffer([("alias", kind, str(tmp_path / "unused"))])
    with tarfile.open(fileobj=buffer) as archive:
        assert not check_if_tar_safe(archive)
    buffer.seek(0)
    with pytest.raises(TarPathTraversalException):
        extract_tar(buffer, tmp_path / "output")
    assert not os.path.lexists(str(tmp_path / "output" / "alias"))


def test_tar_checks_links_after_stripping(tmp_path):
    """Check link targets against the directory structure users receive."""
    buffer = tar_buffer([("release", tarfile.DIRTYPE, ""), ("release/alias", tarfile.SYMTYPE, "../unused")])
    with pytest.raises(TarPathTraversalException):
        extract_tar(buffer, tmp_path / "output")


@pytest.mark.parametrize("wrapper", ["", "release", "Example.app"])
def test_tar_preserves_internal_links(tmp_path, wrapper):
    """Keep safe symbolic and hard links in each supported archive layout."""
    prefix = wrapper + "/" if wrapper else ""
    entries = [(wrapper, tarfile.DIRTYPE, "")] if wrapper else []
    entries.extend(
        [
            (prefix + "file", tarfile.REGTYPE, ""),
            (prefix + "bin/alias", tarfile.SYMTYPE, "../file"),
            (prefix + "hard", tarfile.LNKTYPE, prefix + "file"),
        ]
    )
    extract_tar(tar_buffer(entries), tmp_path)
    extract_tar(tar_buffer(entries), tmp_path)
    root = tmp_path / wrapper if wrapper.endswith(".app") else tmp_path
    assert (root / "file").read_bytes() == b"ok"
    assert (root / "bin" / "alias").is_symlink()
    assert (root / "bin" / "alias").read_bytes() == b"ok"
    assert (root / "hard").samefile(root / "file")


def test_tar_preflight_uses_output_directory(tmp_path):
    """Resolve existing links relative to the caller's output directory."""
    output = tmp_path / "output"
    output.mkdir()
    (output / "alias").symlink_to(tmp_path)
    buffer = tar_buffer([("alias/example", tarfile.REGTYPE, "")])
    with tarfile.open(fileobj=buffer) as archive:
        assert not check_if_tar_safe(archive, output)


def test_tar_ignores_working_directory_links(tmp_path, monkeypatch):
    """Strip the archive wrapper independently of names in the working directory."""
    working_dir = tmp_path / "cwd"
    working_dir.mkdir()
    (working_dir / "release").mkdir()
    (working_dir / "release" / "file").symlink_to(tmp_path / "unused")
    monkeypatch.chdir(working_dir)
    entries = [("release", tarfile.DIRTYPE, ""), ("release/file", tarfile.REGTYPE, "")]
    output = tmp_path / "output"
    extract_tar(tar_buffer(entries), output)
    assert (output / "file").read_bytes() == b"ok"
