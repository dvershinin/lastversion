"""Helper functions for tests."""
import sys
from contextlib import contextmanager


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
