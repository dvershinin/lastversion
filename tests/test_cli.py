"""Test CLI functions."""

import os
import subprocess
import sys
import tempfile

from packaging import version

from lastversion.cli import main

from .helpers import captured_exit_code


def test_cli_help_contains_changelog_flag():
    with subprocess.Popen(["lastversion", "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        out, _ = process.communicate()
        help_text = out.decode("utf-8", errors="ignore")
        assert "--changelog" in help_text


def test_cli_format_devel():
    """
    Test that the CLI formatting returns the correct version for a devel
      version.

    Examples:
      * `lastversion test 'blah-1.2.3-devel' # > 1.2.3.dev0`
    """
    with subprocess.Popen(
        ["lastversion", "format", "blah-1.2.3-devel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        out, _ = process.communicate()

        assert version.parse(out.decode("utf-8").strip()) == version.parse("1.2.3.dev0")


def test_cli_format_no_clear():
    """
    Test that the CLI formatting returns error for a version that is not clear.

    Examples:
        * `lastversion test '1.2.x' # > False (no clear version)`
    """
    with subprocess.Popen(
        ["lastversion", "format", "1.2.x"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        process.communicate()

        # exit code should be 1
        assert process.returncode == 1


def test_cli_format_rc1():
    """
    Test that the CLI formatting returns the correct version for a rc version.

    Examples:
        * `lastversion test '1.2.3-rc1' # > 1.2.3rc1`
    """
    with subprocess.Popen(
        ["lastversion", "format", "1.2.3-rc1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        out, _ = process.communicate()

        assert version.parse(out.decode("utf-8").strip()) == version.parse("1.2.3-rc1")


def test_cli_format_rc_with_garbage(capsys):
    """Test that the CLI returns the correct version for a rc version."""
    with captured_exit_code() as get_exit_code:
        main(["format", "v5.12-rc1-do-not-use"])
    exit_code = get_exit_code()

    captured = capsys.readouterr()
    assert "5.12rc1" == captured.out.rstrip()
    assert not exit_code  # Check the exit code is correct


def test_cli_format_rc_with_post(capsys):
    """Test that the CLI returns the correct version for a rc version."""
    with captured_exit_code() as get_exit_code:
        main(["format", "v2.41.0-rc2.windows.1"])
    exit_code = get_exit_code()

    captured = capsys.readouterr()
    assert "2.41.0rc2.post1" == captured.out.rstrip()
    assert not exit_code  # Check the exit code is correct


def test_cli_gt_stable_vs_rc(capsys):
    """Test that the CLI comparison is positive when comparing stable to RC."""
    with captured_exit_code() as get_exit_code:
        main(["v2.41.0.windows.1", "-gt", "v2.41.0-rc2.windows.1"])
    exit_code = get_exit_code()

    captured = capsys.readouterr()
    assert "2.41.0" == captured.out.rstrip()
    assert not exit_code  # Check the exit code is correct


def test_cli_gt_first_arg_is_repo(capsys):
    """First repo is arg having a number."""
    with captured_exit_code() as get_exit_code:
        main(["https://github.com/Pisex/cs2-bans", "-gt", "2.5.2"])
    exit_code = get_exit_code()

    captured = capsys.readouterr()
    assert version.parse(captured.out.rstrip()) >= version.parse("2.5.3")
    assert not exit_code  # Check the exit code is correct


def test_unzip_osx_bundle_strip(capsys):  # pylint: disable=unused-argument
    """Test that ZIP files with single top level directory are stripped."""
    with captured_exit_code() as get_exit_code:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            # Set the temp directory as the current working directory
            os.chdir(tmp_dir_name)
            main(["--assets", "unzip", "lastversion-test-repos/MinimalMIDIPlayer-strip"])
            # Assert that MinimalMIDIPlayer.app exists and is a directory
            assert os.path.isdir("Contents")
            # Assert file MinimalMIDIPlayer.app/Contents/Info.plist exists
            assert os.path.isfile("Contents/Info.plist")
    exit_code = get_exit_code()

    assert not exit_code  # Check the exit code is correct


def test_unzip_osx_bundle(capsys):  # pylint: disable=unused-argument
    """Test that OSX bundles are unzipped and .app is not stripped."""
    with captured_exit_code() as get_exit_code:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            # Set the temp directory as the current working directory
            os.chdir(tmp_dir_name)
            main(["--assets", "unzip", "lastversion-test-repos/MinimalMIDIPlayer"])
            # Assert that MinimalMIDIPlayer.app exists and is a directory
            assert os.path.isdir("MinimalMIDIPlayer.app")
            # Assert file MinimalMIDIPlayer.app/Contents/Info.plist exists
            assert os.path.isfile("MinimalMIDIPlayer.app/Contents/Info.plist")
    exit_code = get_exit_code()

    assert not exit_code  # Check the exit code is correct


def test_cli_get_assets(capsys):
    """Test that the CLI --assets return AppImage on Linux."""
    if sys.platform == "linux":
        with captured_exit_code() as get_exit_code:
            main(["--assets", "https://github.com/lastversion-test-repos/OneDriveGUI"])
        exit_code = get_exit_code()
        assert not exit_code  # Check the exit code is correct

        captured = capsys.readouterr()
        assert ".AppImage" in captured.out
