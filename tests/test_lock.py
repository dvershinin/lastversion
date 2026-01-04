"""Tests for the PID-based file locking mechanism."""

import os
import subprocess
import sys
import tempfile

import pytest

from lastversion.repo_holders.base import InternalTimedDirLock, LockAcquireTimeout, _is_process_alive


class TestIsProcessAlive:
    """Tests for the _is_process_alive helper function."""

    def test_current_process_is_alive(self):
        """Current process should be detected as alive."""
        assert _is_process_alive(os.getpid()) is True

    def test_invalid_pid_not_alive(self):
        """Invalid PIDs should not be detected as alive."""
        assert _is_process_alive(0) is False
        assert _is_process_alive(-1) is False
        assert _is_process_alive(-999) is False

    def test_nonexistent_pid_not_alive(self):
        """Non-existent PID (very high number) should not be alive."""
        # Use a very high PID that's unlikely to exist
        assert _is_process_alive(999999999) is False


class TestInternalTimedDirLock:
    """Tests for the InternalTimedDirLock class."""

    def test_basic_lock_acquire_release(self):
        """Lock should be acquirable and releasable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_target = os.path.join(tmpdir, "test_file")
            lock_path = f"{lock_target}.lock"

            with InternalTimedDirLock(lock_target):
                # Lock directory should exist while held
                assert os.path.isdir(lock_path)
                # PID file should exist
                pid_file = os.path.join(lock_path, "pid")
                assert os.path.isfile(pid_file)
                # PID should be our process
                with open(pid_file, "r") as f:
                    assert int(f.read().strip()) == os.getpid()

            # Lock should be released
            assert not os.path.exists(lock_path)

    def test_lock_timeout_on_held_lock(self):
        """Lock acquisition should timeout if another process holds it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_target = os.path.join(tmpdir, "test_file")
            lock_path = f"{lock_target}.lock"

            # Create lock directory and PID file with our PID (simulating held lock)
            os.mkdir(lock_path)
            with open(os.path.join(lock_path, "pid"), "w") as f:
                f.write(str(os.getpid()))

            # Trying to acquire should timeout since process (us) is alive
            with pytest.raises(LockAcquireTimeout):
                with InternalTimedDirLock(lock_target, timeout=0.3):
                    pass

            # Cleanup
            os.remove(os.path.join(lock_path, "pid"))
            os.rmdir(lock_path)

    def test_stale_lock_cleanup_dead_process(self):
        """Stale lock from dead process should be automatically cleaned up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_target = os.path.join(tmpdir, "test_file")
            lock_path = f"{lock_target}.lock"

            # Create a stale lock with a non-existent PID
            os.mkdir(lock_path)
            with open(os.path.join(lock_path, "pid"), "w") as f:
                f.write("999999999")  # Very high PID, unlikely to exist

            # Lock should be acquired after cleaning stale lock
            with InternalTimedDirLock(lock_target) as lock:
                assert lock is not None
                # Verify we now hold the lock
                with open(os.path.join(lock_path, "pid"), "r") as f:
                    assert int(f.read().strip()) == os.getpid()

            # Lock should be released
            assert not os.path.exists(lock_path)

    def test_stale_lock_without_pid_file(self):
        """Lock directory without PID file should be cleaned up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_target = os.path.join(tmpdir, "test_file")
            lock_path = f"{lock_target}.lock"

            # Create an empty lock directory (no PID file)
            os.mkdir(lock_path)

            # Lock should be acquired after cleaning up empty lock dir
            with InternalTimedDirLock(lock_target) as lock:
                assert lock is not None

            assert not os.path.exists(lock_path)

    def test_stale_lock_invalid_pid_content(self):
        """Lock with invalid PID file content should be cleaned up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_target = os.path.join(tmpdir, "test_file")
            lock_path = f"{lock_target}.lock"

            # Create lock with invalid PID content
            os.mkdir(lock_path)
            with open(os.path.join(lock_path, "pid"), "w") as f:
                f.write("not_a_number")

            # Lock should be acquired after cleaning up invalid lock
            with InternalTimedDirLock(lock_target) as lock:
                assert lock is not None

            assert not os.path.exists(lock_path)

    def test_crashed_subprocess_lock_cleanup(self):
        """Lock from crashed subprocess should be detected and cleaned up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_target = os.path.join(tmpdir, "test_file")
            lock_path = f"{lock_target}.lock"

            # Use a subprocess to create a lock and exit without cleanup
            # This simulates a crash scenario
            script = f"""
import os
lock_path = {repr(lock_path)}
os.mkdir(lock_path)
with open(os.path.join(lock_path, "pid"), "w") as f:
    f.write(str(os.getpid()))
# Exit without cleanup (simulating crash)
"""
            # Use stdout/stderr=PIPE for Python 3.6 compatibility
            # (capture_output was added in Python 3.7)
            proc = subprocess.run(
                [sys.executable, "-c", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
            )
            assert proc.returncode == 0

            # Lock directory should exist but process should be dead
            assert os.path.isdir(lock_path)
            with open(os.path.join(lock_path, "pid"), "r") as f:
                dead_pid = int(f.read().strip())
            assert not _is_process_alive(dead_pid)

            # We should be able to acquire lock (stale lock cleaned up)
            with InternalTimedDirLock(lock_target, timeout=1) as lock:
                assert lock is not None
                # Verify we now hold the lock
                with open(os.path.join(lock_path, "pid"), "r") as f:
                    assert int(f.read().strip()) == os.getpid()

            assert not os.path.exists(lock_path)

    def test_old_style_lock_with_extra_files(self):
        """Old lock directory with extra files should be cleaned up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_target = os.path.join(tmpdir, "test_file")
            lock_path = f"{lock_target}.lock"

            # Simulate old-style lock (pre-v3.6.5) with no pid file
            # but with some leftover files from a crash
            os.mkdir(lock_path)
            # Create some extra files that might be left from crashes
            with open(os.path.join(lock_path, "some_leftover_file"), "w") as f:
                f.write("leftover data")
            os.mkdir(os.path.join(lock_path, "nested_dir"))
            with open(os.path.join(lock_path, "nested_dir", "another_file"), "w") as f:
                f.write("more leftover data")

            # Lock should be acquired after cleaning up the messy old lock
            with InternalTimedDirLock(lock_target) as lock:
                assert lock is not None
                # Verify we now hold the lock with new PID file
                pid_file = os.path.join(lock_path, "pid")
                assert os.path.isfile(pid_file)
                with open(pid_file, "r") as f:
                    assert int(f.read().strip()) == os.getpid()

            assert not os.path.exists(lock_path)
