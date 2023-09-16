import subprocess
import sys

from packaging import version
from contextlib import contextmanager
from lastversion import main


@contextmanager
def captured_exit_code():
    """Capture the exit code of a function."""
    exit_code = None

    def mock_exit(code=0):
        """Mock the exit function."""
        nonlocal exit_code
        exit_code = code

    original_exit = sys.exit
    sys.exit = mock_exit
    try:
        yield lambda: exit_code
    finally:
        sys.exit = original_exit


def test_cli_format_devel():
    """
    Test that the CLI formatting returns the correct version for a devel version.
    `lastversion test 'blah-1.2.3-devel' # > 1.2.3.dev0`
    """
    process = subprocess.Popen(
        ['lastversion', 'format', 'blah-1.2.3-devel'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    out, err = process.communicate()

    assert version.parse(out.decode('utf-8').strip()) == version.parse("1.2.3.dev0")


def test_cli_format_no_clear():
    """
    Test that the CLI formatting returns error for a version that is not clear.
    `lastversion test '1.2.x' # > False (no clear version)`
    """
    process = subprocess.Popen(
        ['lastversion', 'format', '1.2.x'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    out, err = process.communicate()

    # exit code should be 1
    assert process.returncode == 1


def test_cli_format_rc1():
    """
    Test that the CLI formatting returns the correct version for a rc version.
    `lastversion test '1.2.3-rc1' # > 1.2.3rc1`
    """
    process = subprocess.Popen(
        ['lastversion', 'format', '1.2.3-rc1'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    out, err = process.communicate()

    assert version.parse(out.decode('utf-8').strip()) == version.parse("1.2.3-rc1")


def test_cli_format_rc_with_garbage(capsys):
    """Test that the CLI formatting returns the correct version for a rc version."""
    with captured_exit_code() as get_exit_code:
        main(['format', 'v5.12-rc1-dontuse'])
    exit_code = get_exit_code()

    captured = capsys.readouterr()
    assert "5.12rc1" == captured.out.rstrip()
    assert not exit_code  # Check the exit code is correct


def test_cli_format_rc_with_post(capsys):
    """Test that the CLI formatting returns the correct version for a rc version."""
    with captured_exit_code() as get_exit_code:
        main(['format', 'v2.41.0-rc2.windows.1'])
    exit_code = get_exit_code()

    captured = capsys.readouterr()
    assert "2.41.0rc2.post1" == captured.out.rstrip()
    assert not exit_code  # Check the exit code is correct


def test_cli_gt_stable_vs_rc(capsys):
    """Test that the CLI comparison is positive when comparing stable to RC."""
    with captured_exit_code() as get_exit_code:
        main(['v2.41.0.windows.1', '-gt', 'v2.41.0-rc2.windows.1'])
    exit_code = get_exit_code()

    captured = capsys.readouterr()
    assert "2.41.0" == captured.out.rstrip()
    assert not exit_code  # Check the exit code is correct
