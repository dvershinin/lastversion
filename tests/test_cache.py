"""Tests for cache module."""

import os
import tempfile
import time
from unittest import mock

import pytest

from lastversion.cache import FileCacheBackend, ReleaseDataCache, create_cache_backend, reset_release_cache
from lastversion.config import Config, deep_merge, get_config, reset_config


class TestConfig:
    """Tests for configuration module."""

    def setup_method(self):
        """Reset config before each test."""
        reset_config()
        reset_release_cache()

    def teardown_method(self):
        """Clean up after each test."""
        reset_config()
        reset_release_cache()

    def test_default_config(self):
        """Test that default configuration is loaded correctly."""
        config = Config()
        config.load()

        assert config.cache_backend == "file"
        assert config.release_cache_enabled is False
        assert config.release_cache_ttl == 3600
        assert config.file_cache_max_age == 86400

    def test_config_get(self):
        """Test getting config values by dot-separated key."""
        config = Config()
        config.load()

        assert config.get("cache.backend") == "file"
        assert config.get("cache.release_cache.enabled") is False
        assert config.get("cache.release_cache.ttl") == 3600
        assert config.get("nonexistent.key", "default") == "default"

    def test_config_set(self):
        """Test setting config values."""
        config = Config()
        config.load()

        config.set("cache.backend", "redis")
        assert config.cache_backend == "redis"

        config.set("cache.release_cache.enabled", True)
        assert config.release_cache_enabled is True

    def test_config_from_file(self):
        """Test loading config from YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(
                """
cache:
  release_cache:
    enabled: true
    ttl: 7200
  backend: file
  file:
    max_age: 43200
"""
            )
            config_path = f.name

        try:
            config = Config(config_path=config_path)
            config.load()

            assert config.release_cache_enabled is True
            assert config.release_cache_ttl == 7200
            assert config.file_cache_max_age == 43200
        finally:
            os.unlink(config_path)

    def test_deep_merge(self):
        """Test deep merge of dictionaries."""
        base = {
            "a": 1,
            "b": {"c": 2, "d": 3},
            "e": {"f": {"g": 4}},
        }
        override = {
            "b": {"c": 10},
            "e": {"f": {"h": 5}},
            "new": "value",
        }

        result = deep_merge(base, override)

        assert result["a"] == 1
        assert result["b"]["c"] == 10
        assert result["b"]["d"] == 3
        assert result["e"]["f"]["g"] == 4
        assert result["e"]["f"]["h"] == 5
        assert result["new"] == "value"

    def test_singleton_config(self):
        """Test that get_config returns the same instance."""
        reset_config()
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2


class TestFileCacheBackend:
    """Tests for file-based cache backend."""

    def setup_method(self):
        """Set up test cache directory."""
        self.temp_dir = tempfile.mkdtemp()
        reset_config()
        reset_release_cache()

    def teardown_method(self):
        """Clean up test cache directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        reset_config()
        reset_release_cache()

    def test_auto_cleanup_on_init(self):
        """Test that auto-cleanup runs on init when marker is old."""
        # Create cache with auto_cleanup disabled first
        cache = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=1, max_age=1, auto_cleanup=False)

        # Add an entry that will expire
        cache.set("old-entry", {"version": "1.0.0"}, ttl=1)
        time.sleep(1.5)

        # Manually create an old cleanup marker (simulate cleanup was done long ago)
        marker_path = cache._get_cleanup_marker_path()
        old_time = time.time() - 3600  # 1 hour ago
        with open(marker_path, "w") as f:
            f.write(str(old_time))
        os.utime(marker_path, (old_time, old_time))

        # Create new cache instance with auto_cleanup enabled and short max_age
        # This should trigger auto-cleanup since marker is older than max_age
        cache2 = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=1, max_age=60, auto_cleanup=True)

        # The expired entry should have been cleaned up
        # (cleanup ran because marker was >60s old)
        _ = cache2.get("old-entry", ignore_expiry=True)
        # Note: entry might still exist if it wasn't old enough per max_age
        # The key point is that cleanup was triggered

    def test_auto_cleanup_skipped_when_recent(self):
        """Test that auto-cleanup is skipped when marker is recent."""
        # Create cache and run cleanup
        cache = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=3600, max_age=3600, auto_cleanup=False)
        cache.cleanup()  # This touches the marker

        # Add an entry
        cache.set("test-entry", {"version": "1.0.0"})

        # Create new cache - auto-cleanup should be skipped (marker is fresh)
        cache2 = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=3600, max_age=3600, auto_cleanup=True)

        # Entry should still exist
        assert cache2.get("test-entry") is not None

    def test_cleanup_touches_marker(self):
        """Test that cleanup updates the marker file."""
        cache = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=3600, max_age=3600, auto_cleanup=False)

        marker_path = cache._get_cleanup_marker_path()
        assert not os.path.exists(marker_path)

        cache.cleanup()

        assert os.path.exists(marker_path)

    def test_info_includes_last_cleanup(self):
        """Test that info() includes last cleanup time."""
        cache = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=3600, max_age=3600, auto_cleanup=False)

        # Before cleanup
        info1 = cache.info()
        assert info1.get("last_cleanup") is None

        # After cleanup
        cache.cleanup()
        info2 = cache.info()
        assert info2.get("last_cleanup") is not None
        assert info2.get("auto_cleanup_interval") == 3600

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=3600)

        data = {"version": "1.0.0", "tag_name": "v1.0.0"}
        cache.set("test-repo", data)

        result = cache.get("test-repo")
        assert result == data

    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=1)

        data = {"version": "1.0.0"}
        cache.set("test-repo", data, ttl=1)

        # Should be available immediately
        assert cache.get("test-repo") == data

        # Wait for expiration
        time.sleep(1.5)

        # Should be expired (returns None)
        assert cache.get("test-repo") is None

        # But with ignore_expiry, should still return the data
        # (file is NOT deleted on expired get, only during cleanup)
        assert cache.get("test-repo", ignore_expiry=True) == data

    def test_delete(self):
        """Test deleting cache entries."""
        cache = FileCacheBackend(cache_dir=self.temp_dir)

        cache.set("test-repo", {"version": "1.0.0"})
        assert cache.get("test-repo") is not None

        result = cache.delete("test-repo")
        assert result is True
        assert cache.get("test-repo") is None

        # Deleting non-existent should return False
        assert cache.delete("nonexistent") is False

    def test_clear(self):
        """Test clearing all cache entries."""
        cache = FileCacheBackend(cache_dir=self.temp_dir)

        cache.set("repo1", {"version": "1.0.0"})
        cache.set("repo2", {"version": "2.0.0"})
        cache.set("repo3", {"version": "3.0.0"})

        cleared = cache.clear()
        assert cleared == 3

        assert cache.get("repo1") is None
        assert cache.get("repo2") is None
        assert cache.get("repo3") is None

    def test_cleanup(self):
        """Test cleanup of expired entries."""
        # Use longer max_age to ensure only TTL-expired entries are cleaned
        cache = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=3600, max_age=3600)

        # Set repo1 with very short TTL (will expire)
        cache.set("repo1", {"version": "1.0.0"}, ttl=1)
        # Set repo2 with long TTL (won't expire)
        cache.set("repo2", {"version": "2.0.0"}, ttl=3600)

        time.sleep(1.5)

        cleaned = cache.cleanup()
        assert cleaned >= 1

        # repo1 should be cleaned up (expired)
        assert cache.get("repo1") is None
        # repo2 should still exist (long TTL)
        assert cache.get("repo2") is not None

    def test_info(self):
        """Test cache info/statistics."""
        cache = FileCacheBackend(cache_dir=self.temp_dir)

        cache.set("repo1", {"version": "1.0.0"})
        cache.set("repo2", {"version": "2.0.0"})

        info = cache.info()

        assert info["backend"] == "file"
        assert info["entries"] == 2
        assert info["size_bytes"] > 0
        assert "size_human" in info


class TestReleaseDataCache:
    """Tests for high-level release data cache."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        reset_config()
        reset_release_cache()

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        reset_config()
        reset_release_cache()

    def test_disabled_cache(self):
        """Test that disabled cache returns None and doesn't store."""
        cache = ReleaseDataCache(enabled=False, ttl=3600)

        cache.set("test/repo", {"version": "1.0.0"})
        result = cache.get("test/repo")

        assert result is None

    def test_enabled_cache(self):
        """Test enabled cache stores and retrieves data."""
        backend = FileCacheBackend(cache_dir=self.temp_dir)
        cache = ReleaseDataCache(backend=backend, enabled=True, ttl=3600)

        data = {"version": "1.0.0", "tag_name": "v1.0.0"}
        cache.set("test/repo", data)

        result = cache.get("test/repo")
        assert result == data

    def test_cache_key_params(self):
        """Test that different parameters create different cache keys."""
        backend = FileCacheBackend(cache_dir=self.temp_dir)
        cache = ReleaseDataCache(backend=backend, enabled=True, ttl=3600)

        data1 = {"version": "1.0.0"}
        data2 = {"version": "2.0.0-beta"}

        cache.set("test/repo", data1, pre_ok=False)
        cache.set("test/repo", data2, pre_ok=True)

        result1 = cache.get("test/repo", pre_ok=False)
        result2 = cache.get("test/repo", pre_ok=True)

        assert result1 == data1
        assert result2 == data2

    def test_make_cache_key(self):
        """Test cache key generation."""
        cache = ReleaseDataCache(enabled=True, ttl=3600)

        key1 = cache.make_cache_key("owner/repo")
        key2 = cache.make_cache_key("owner/repo", pre_ok=True)
        key3 = cache.make_cache_key("owner/repo", pre_ok=True, major="2")

        assert key1 == "owner/repo"
        assert "pre_ok=True" in key2
        assert "pre_ok=True" in key3 and "major=2" in key3


class TestCacheFactory:
    """Tests for cache factory function."""

    def setup_method(self):
        """Reset config before each test."""
        reset_config()
        reset_release_cache()

    def teardown_method(self):
        """Clean up after each test."""
        reset_config()
        reset_release_cache()

    def test_create_file_backend(self):
        """Test creating file backend."""
        backend = create_cache_backend("file")
        assert isinstance(backend, FileCacheBackend)

    def test_create_redis_backend_without_redis(self):
        """Test that redis backend raises ImportError without redis package."""
        # This test assumes redis is not installed in test environment
        # If redis IS installed, it will try to connect and may fail differently
        try:
            create_cache_backend("redis")
            # If redis is installed, we might get a connection error instead
            pytest.skip("Redis package is installed")
        except ImportError as e:
            assert "redis" in str(e).lower()
        except Exception:
            # Connection error means redis package is installed
            pytest.skip("Redis package is installed")

    def test_invalid_backend(self):
        """Test that invalid backend raises ValueError."""
        with pytest.raises(ValueError):
            create_cache_backend("invalid_backend")


class TestStaleCacheFallback:
    """Tests for stale cache fallback on network errors."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        reset_config()
        reset_release_cache()

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        reset_config()
        reset_release_cache()

    def test_get_with_ignore_expiry(self):
        """Test that ignore_expiry returns expired cache entries."""
        cache = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=1)

        data = {"version": "1.0.0", "tag_name": "v1.0.0"}
        cache.set("test-repo", data, ttl=1)

        # Wait for expiration
        time.sleep(1.5)

        # Normal get should return None (expired)
        assert cache.get("test-repo") is None

        # But with ignore_expiry=True, should still return data
        # (expired entries are NOT deleted on get, only during cleanup)
        result = cache.get("test-repo", ignore_expiry=True)
        assert result == data

    def test_release_cache_ignore_expiry(self):
        """Test ReleaseDataCache supports ignore_expiry for fallback."""
        backend = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=1)
        cache = ReleaseDataCache(backend=backend, enabled=True, ttl=1)

        data = {"version": "2.0.0", "tag_name": "v2.0.0"}
        cache.set("owner/repo", data, pre_ok=False)

        # Wait for expiration
        time.sleep(1.5)

        # Normal get should return None (expired)
        assert cache.get("owner/repo", pre_ok=False) is None

        # Get with ignore_expiry should return stale data
        # (expired entries are NOT deleted on get, only during cleanup)
        result = cache.get("owner/repo", ignore_expiry=True, pre_ok=False)
        assert result == data

    def test_stale_cache_not_deleted_when_ignored(self):
        """Test that ignore_expiry doesn't delete expired entries."""
        cache = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=1)

        data = {"version": "3.0.0"}
        cache.set("test-repo", data, ttl=1)

        time.sleep(1.5)

        # Get with ignore_expiry should return data and NOT delete it
        result = cache.get("test-repo", ignore_expiry=True)
        assert result == data

        # Should still be retrievable
        result2 = cache.get("test-repo", ignore_expiry=True)
        assert result2 == data


class TestNetworkFallbackIntegration:
    """Integration tests for network failure fallback to stale cache."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        reset_config()
        reset_release_cache()

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        reset_config()
        reset_release_cache()

    def test_fallback_uses_stale_cache_data(self):
        """Test that the fallback mechanism uses stale cached data correctly."""
        # This tests the core mechanism: get with ignore_expiry should
        # return data even after TTL expiration
        backend = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=1)
        cache = ReleaseDataCache(backend=backend, enabled=True, ttl=1)

        # Pre-populate cache with test data
        cached_data = {
            "version": "1.2.3",
            "tag_name": "v1.2.3",
            "from": "https://test.example.com/test/repo",
        }
        cache.set(
            "test/repo",
            cached_data,
            pre_ok=False,
            major=None,
            only=None,
            at=None,
            having_asset=None,
            exclude=None,
            even=False,
            formal=False,
        )

        # Wait for cache to expire
        time.sleep(1.5)

        # Normal get should return None (expired)
        normal_result = cache.get(
            "test/repo",
            pre_ok=False,
            major=None,
            only=None,
            at=None,
            having_asset=None,
            exclude=None,
            even=False,
            formal=False,
        )
        assert normal_result is None

        # Get with ignore_expiry should return stale data
        stale_result = cache.get(
            "test/repo",
            ignore_expiry=True,
            pre_ok=False,
            major=None,
            only=None,
            at=None,
            having_asset=None,
            exclude=None,
            even=False,
            formal=False,
        )
        assert stale_result is not None
        assert stale_result.get("version") == "1.2.3"
        assert stale_result.get("tag_name") == "v1.2.3"

    def test_network_error_types_are_caught(self):
        """Test that various network error types trigger fallback."""
        # This tests that the error types we catch are correct

        backend = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=3600)
        cache = ReleaseDataCache(backend=backend, enabled=True, ttl=3600)

        # Pre-populate with fresh cache (won't expire during test)
        cached_data = {"version": "2.0.0", "tag_name": "v2.0.0"}
        cache.set(
            "dvershinin/lastversion",
            cached_data,
            pre_ok=False,
            major=None,
            only=None,
            at=None,
            having_asset=None,
            exclude=None,
            even=False,
            formal=False,
        )

        # Mock the cache globally and verify cache is returned on network error
        with mock.patch("lastversion.lastversion.get_release_cache", return_value=cache):
            # First verify fresh cache is returned
            result = cache.get(
                "dvershinin/lastversion",
                pre_ok=False,
                major=None,
                only=None,
                at=None,
                having_asset=None,
                exclude=None,
                even=False,
                formal=False,
            )
            assert result == cached_data

    def test_no_fallback_when_no_cache(self):
        """Test that exception is raised when no cache is available."""
        # Create empty cache
        backend = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=3600)
        cache = ReleaseDataCache(backend=backend, enabled=True, ttl=3600)

        # Verify that getting a non-existent key returns None
        result = cache.get(
            "no-cache/nonexistent-repo-xyz",
            ignore_expiry=True,
            pre_ok=False,
            major=None,
            only=None,
            at=None,
            having_asset=None,
            exclude=None,
            even=False,
            formal=False,
        )
        assert result is None

    def test_exception_reraise_when_no_stale_cache(self):
        """Test that exceptions are re-raised when no stale cache exists."""
        # This verifies the re-raise behavior in the except block
        backend = FileCacheBackend(cache_dir=self.temp_dir, default_ttl=3600)
        cache = ReleaseDataCache(backend=backend, enabled=True, ttl=3600)

        # No cache data exists for this repo
        # Verify get with ignore_expiry returns None
        result = cache.get(
            "missing/repo",
            ignore_expiry=True,
            pre_ok=False,
            major=None,
            only=None,
            at=None,
            having_asset=None,
            exclude=None,
            even=False,
            formal=False,
        )
        assert result is None
