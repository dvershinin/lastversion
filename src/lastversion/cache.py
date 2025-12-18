"""Cache backends for lastversion.

Provides file-based and Redis cache backends for storing release data
with configurable TTL and auto-cleanup.
"""

import hashlib
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from lastversion.config import get_config

log = logging.getLogger(__name__)


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    def get(self, key: str, ignore_expiry: bool = False) -> Optional[Dict[str, Any]]:
        """Get a value from the cache.

        Args:
            key: Cache key.
            ignore_expiry: If True, return data even if expired (for fallback).

        Returns:
            Cached value or None if not found/expired.
        """

    @abstractmethod
    def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key.
            value: Value to cache (must be JSON-serializable).
            ttl: Time-to-live in seconds. None uses default.
        """

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a value from the cache.

        Args:
            key: Cache key.

        Returns:
            True if deleted, False if not found.
        """

    @abstractmethod
    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries cleared.
        """

    @abstractmethod
    def cleanup(self) -> int:
        """Clean up expired entries.

        Returns:
            Number of entries cleaned up.
        """

    @abstractmethod
    def info(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache info (size, entries, etc.).
        """


class FileCacheBackend(CacheBackend):
    """File-based cache backend with TTL and auto-cleanup support."""

    CACHE_SUBDIR = "release_cache"
    CLEANUP_MARKER_FILE = ".last_cleanup"

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        default_ttl: int = 3600,
        max_age: int = 86400,
        max_size: int = 104857600,
        auto_cleanup: bool = True,
    ):
        """Initialize file cache backend.

        Args:
            cache_dir: Base cache directory. None uses default.
            default_ttl: Default TTL in seconds.
            max_age: Max age for cleanup in seconds. Also used as auto-cleanup interval.
            max_size: Max total cache size in bytes.
            auto_cleanup: Whether to run cleanup automatically when overdue.
        """
        config = get_config()
        self.cache_dir = cache_dir or config.file_cache_path
        self.release_cache_dir = os.path.join(self.cache_dir, self.CACHE_SUBDIR)
        self.default_ttl = default_ttl
        self.max_age = max_age
        self.max_size = max_size
        self.auto_cleanup = auto_cleanup
        self._ensure_cache_dir()

        # Check if automatic cleanup is needed
        if self.auto_cleanup:
            self._maybe_cleanup()

    def _ensure_cache_dir(self) -> None:
        """Ensure the cache directory exists."""
        try:
            os.makedirs(self.release_cache_dir, exist_ok=True)
        except OSError as e:
            log.warning("Failed to create cache directory %s: %s", self.release_cache_dir, e)

    def _get_cleanup_marker_path(self) -> str:
        """Get path to the cleanup marker file."""
        return os.path.join(self.release_cache_dir, self.CLEANUP_MARKER_FILE)

    def _maybe_cleanup(self) -> None:
        """Run cleanup if it's been too long since the last one.

        This provides automatic cleanup without requiring explicit cron jobs.
        Cleanup is triggered if more than max_age seconds have passed since
        the last cleanup.
        """
        marker_path = self._get_cleanup_marker_path()

        try:
            if os.path.exists(marker_path):
                marker_mtime = os.path.getmtime(marker_path)
                time_since_cleanup = time.time() - marker_mtime
                if time_since_cleanup < self.max_age:
                    # Cleanup was done recently, skip
                    return
                log.debug("Auto-cleanup triggered: %d seconds since last cleanup", int(time_since_cleanup))
            else:
                log.debug("Auto-cleanup triggered: no previous cleanup marker found")

            # Run cleanup
            cleaned = self.cleanup()
            if cleaned > 0:
                log.info("Auto-cleanup removed %d expired cache entries", cleaned)

        except OSError as e:
            log.debug("Error checking cleanup marker: %s", e)

    def _touch_cleanup_marker(self) -> None:
        """Update the cleanup marker file timestamp."""
        marker_path = self._get_cleanup_marker_path()
        try:
            # Create or update the marker file
            with open(marker_path, "w", encoding="utf-8") as f:
                f.write(str(time.time()))
        except OSError as e:
            log.debug("Error updating cleanup marker: %s", e)

    def _get_cache_path(self, key: str) -> str:
        """Get the file path for a cache key.

        Args:
            key: Cache key.

        Returns:
            Full file path for the cache entry.
        """
        # Hash the key to create a safe filename
        key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return os.path.join(self.release_cache_dir, f"{key_hash}.json")

    def get(self, key: str, ignore_expiry: bool = False) -> Optional[Dict[str, Any]]:
        """Get a value from the file cache.

        Args:
            key: Cache key.
            ignore_expiry: If True, return data even if expired (for fallback).

        Returns:
            Cached value or None if not found.
        """
        cache_path = self._get_cache_path(key)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check if expired (unless ignoring expiry for fallback)
            # Note: We don't delete expired entries here - that's done by cleanup()
            # This allows stale cache to be used for fallback on network errors
            if not ignore_expiry:
                expires_at = data.get("_expires_at", 0)
                if expires_at and time.time() > expires_at:
                    log.debug("Cache entry expired for key: %s", key)
                    return None

            return data.get("value")
        except (IOError, json.JSONDecodeError, KeyError) as e:
            log.debug("Error reading cache for key %s: %s", key, e)
            return None

    def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Set a value in the file cache."""
        self._ensure_cache_dir()
        cache_path = self._get_cache_path(key)

        if ttl is None:
            ttl = self.default_ttl

        expires_at = time.time() + ttl if ttl > 0 else 0

        data = {
            "key": key,
            "value": value,
            "_expires_at": expires_at,
            "_created_at": time.time(),
        }

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            log.debug("Cached value for key: %s (TTL: %d)", key, ttl)
        except (IOError, TypeError) as e:
            log.warning("Error writing cache for key %s: %s", key, e)

    def delete(self, key: str) -> bool:
        """Delete a value from the file cache."""
        cache_path = self._get_cache_path(key)

        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                return True
            except OSError as e:
                log.warning("Error deleting cache entry %s: %s", cache_path, e)
        return False

    def clear(self) -> int:
        """Clear all cache entries."""
        cleared = 0
        if not os.path.exists(self.release_cache_dir):
            return 0

        for filename in os.listdir(self.release_cache_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.release_cache_dir, filename)
                try:
                    os.remove(filepath)
                    cleared += 1
                except OSError:
                    pass

        log.info("Cleared %d cache entries", cleared)
        return cleared

    def cleanup(self) -> int:
        """Clean up expired and old entries."""
        cleaned = 0
        now = time.time()
        total_size = 0
        entries = []

        if not os.path.exists(self.release_cache_dir):
            return 0

        # Collect all entries with their metadata
        for filename in os.listdir(self.release_cache_dir):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(self.release_cache_dir, filename)
            try:
                stat = os.stat(filepath)
                mtime = stat.st_mtime
                size = stat.st_size
                entries.append((filepath, mtime, size))
                total_size += size
            except OSError:
                continue

        # Remove expired entries (based on TTL in file)
        for filepath, mtime, size in entries:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                expires_at = data.get("_expires_at", 0)
                if expires_at and now > expires_at:
                    os.remove(filepath)
                    cleaned += 1
                    total_size -= size
                    continue
            except (IOError, json.JSONDecodeError):
                pass

            # Also remove entries older than max_age
            if now - mtime > self.max_age:
                try:
                    os.remove(filepath)
                    cleaned += 1
                    total_size -= size
                except OSError:
                    pass

        # If still over max_size, remove oldest entries
        if total_size > self.max_size:
            # Re-collect remaining entries
            remaining = []
            for filename in os.listdir(self.release_cache_dir):
                if not filename.endswith(".json"):
                    continue
                filepath = os.path.join(self.release_cache_dir, filename)
                try:
                    stat = os.stat(filepath)
                    remaining.append((filepath, stat.st_mtime, stat.st_size))
                except OSError:
                    continue

            # Sort by mtime (oldest first) and remove until under limit
            remaining.sort(key=lambda x: x[1])
            current_size = sum(e[2] for e in remaining)

            for filepath, _, size in remaining:
                if current_size <= self.max_size:
                    break
                try:
                    os.remove(filepath)
                    cleaned += 1
                    current_size -= size
                except OSError:
                    pass

        if cleaned > 0:
            log.info("Cleaned up %d cache entries", cleaned)

        # Update the cleanup marker
        self._touch_cleanup_marker()

        return cleaned

    def info(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_size = 0
        entry_count = 0
        expired_count = 0
        now = time.time()

        if os.path.exists(self.release_cache_dir):
            for filename in os.listdir(self.release_cache_dir):
                if not filename.endswith(".json"):
                    continue

                filepath = os.path.join(self.release_cache_dir, filename)
                try:
                    stat = os.stat(filepath)
                    total_size += stat.st_size
                    entry_count += 1

                    # Check if expired
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    expires_at = data.get("_expires_at", 0)
                    if expires_at and now > expires_at:
                        expired_count += 1
                except (OSError, json.JSONDecodeError):
                    pass

        # Get last cleanup time
        last_cleanup = None
        marker_path = self._get_cleanup_marker_path()
        if os.path.exists(marker_path):
            try:
                last_cleanup = os.path.getmtime(marker_path)
            except OSError:
                pass

        return {
            "backend": "file",
            "path": self.release_cache_dir,
            "entries": entry_count,
            "expired_entries": expired_count,
            "size_bytes": total_size,
            "size_human": self._format_size(total_size),
            "max_size_bytes": self.max_size,
            "max_age_seconds": self.max_age,
            "default_ttl_seconds": self.default_ttl,
            "last_cleanup": last_cleanup,
            "auto_cleanup_interval": self.max_age,  # Uses max_age for cleanup interval
        }

    @staticmethod
    def _format_size(size: int) -> str:
        """Format bytes as human-readable string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class RedisCacheBackend(CacheBackend):
    """Redis-based cache backend with TTL support."""

    def __init__(
        self,
        url: Optional[str] = None,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        key_prefix: str = "lastversion:",
        default_ttl: int = 3600,
    ):
        """Initialize Redis cache backend.

        Args:
            url: Redis URL (takes precedence over host/port/db).
            host: Redis host.
            port: Redis port.
            db: Redis database number.
            password: Redis password.
            key_prefix: Prefix for all cache keys.
            default_ttl: Default TTL in seconds.
        """
        try:
            import redis  # pylint: disable=import-outside-toplevel
        except ImportError as e:
            raise ImportError(
                "Redis support requires the 'redis' package. " "Install it with: pip install lastversion[redis]"
            ) from e

        self.key_prefix = key_prefix
        self.default_ttl = default_ttl

        if url:
            self._client = redis.from_url(url)
        else:
            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
            )

        # Test connection
        try:
            self._client.ping()
            log.info("Connected to Redis at %s", url or f"{host}:{port}/{db}")
        except redis.ConnectionError as e:
            log.error("Failed to connect to Redis: %s", e)
            raise

    def _make_key(self, key: str) -> str:
        """Create a prefixed Redis key."""
        return f"{self.key_prefix}{key}"

    def get(self, key: str, ignore_expiry: bool = False) -> Optional[Dict[str, Any]]:
        """Get a value from Redis cache.

        Args:
            key: Cache key.
            ignore_expiry: Ignored for Redis (TTL is handled automatically).

        Returns:
            Cached value or None if not found.
        """
        # Note: ignore_expiry is not applicable for Redis since
        # expired keys are automatically deleted by Redis
        _ = ignore_expiry  # Acknowledge parameter
        redis_key = self._make_key(key)
        try:
            data = self._client.get(redis_key)
            if data:
                return json.loads(data)
        except (json.JSONDecodeError, Exception) as e:  # pylint: disable=broad-except
            log.debug("Error reading Redis cache for key %s: %s", key, e)
        return None

    def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Set a value in Redis cache."""
        redis_key = self._make_key(key)
        if ttl is None:
            ttl = self.default_ttl

        try:
            data = json.dumps(value)
            if ttl > 0:
                self._client.setex(redis_key, ttl, data)
            else:
                self._client.set(redis_key, data)
            log.debug("Cached value in Redis for key: %s (TTL: %d)", key, ttl)
        except Exception as e:  # pylint: disable=broad-except
            log.warning("Error writing to Redis for key %s: %s", key, e)

    def delete(self, key: str) -> bool:
        """Delete a value from Redis cache."""
        redis_key = self._make_key(key)
        try:
            return self._client.delete(redis_key) > 0
        except Exception as e:  # pylint: disable=broad-except
            log.warning("Error deleting Redis key %s: %s", key, e)
            return False

    def clear(self) -> int:
        """Clear all cache entries with our prefix."""
        pattern = f"{self.key_prefix}*"
        cleared = 0
        try:
            cursor = 0
            while True:
                cursor, keys = self._client.scan(cursor, match=pattern, count=100)
                if keys:
                    cleared += self._client.delete(*keys)
                if cursor == 0:
                    break
            log.info("Cleared %d Redis cache entries", cleared)
        except Exception as e:  # pylint: disable=broad-except
            log.warning("Error clearing Redis cache: %s", e)
        return cleared

    def cleanup(self) -> int:
        """Redis handles TTL automatically, so this is a no-op."""
        return 0

    def info(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        pattern = f"{self.key_prefix}*"
        entry_count = 0
        total_size = 0

        try:
            cursor = 0
            while True:
                cursor, keys = self._client.scan(cursor, match=pattern, count=100)
                entry_count += len(keys)
                for key in keys:
                    try:
                        size = self._client.memory_usage(key) or 0
                        total_size += size
                    except Exception:  # pylint: disable=broad-except
                        pass
                if cursor == 0:
                    break

            info = self._client.info("memory")
            used_memory = info.get("used_memory", 0)
        except Exception as e:  # pylint: disable=broad-except
            log.warning("Error getting Redis info: %s", e)
            return {
                "backend": "redis",
                "error": str(e),
            }

        return {
            "backend": "redis",
            "entries": entry_count,
            "size_bytes": total_size,
            "redis_used_memory": used_memory,
            "default_ttl_seconds": self.default_ttl,
        }


class ReleaseDataCache:
    """High-level cache for release data.

    This cache stores parsed release JSON data with TTL, completely
    bypassing HTTP requests when a valid cache entry exists.
    """

    def __init__(
        self,
        backend: Optional[CacheBackend] = None,
        enabled: bool = False,
        ttl: int = 3600,
    ):
        """Initialize release data cache.

        Args:
            backend: Cache backend to use. None creates one from config.
            enabled: Whether caching is enabled.
            ttl: Default TTL in seconds.
        """
        self.enabled = enabled
        self.ttl = ttl
        self._backend = backend

    @property
    def backend(self) -> Optional[CacheBackend]:
        """Get or create the cache backend."""
        if self._backend is None and self.enabled:
            self._backend = create_cache_backend()
        return self._backend

    def make_cache_key(self, repo: str, **kwargs) -> str:
        """Create a cache key for a repo query.

        Args:
            repo: Repository identifier.
            **kwargs: Additional parameters that affect the query.

        Returns:
            Cache key string.
        """
        # Include relevant parameters in the key
        key_parts = [repo]
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}={v}")
        return ":".join(key_parts)

    def get(self, repo: str, ignore_expiry: bool = False, **kwargs) -> Optional[Dict[str, Any]]:
        """Get cached release data for a repo.

        Args:
            repo: Repository identifier.
            ignore_expiry: If True, return data even if expired (for fallback).
            **kwargs: Additional parameters that affect the query.

        Returns:
            Cached release data or None.
        """
        if not self.enabled or self.backend is None:
            return None

        key = self.make_cache_key(repo, **kwargs)
        data = self.backend.get(key, ignore_expiry=ignore_expiry)
        if data:
            log.info("Release cache hit for: %s", repo)
        return data

    def set(self, repo: str, data: Dict[str, Any], ttl: Optional[int] = None, **kwargs) -> None:
        """Cache release data for a repo.

        Args:
            repo: Repository identifier.
            data: Release data to cache.
            ttl: Optional TTL override.
            **kwargs: Additional parameters that affect the query.
        """
        if not self.enabled or self.backend is None:
            return

        key = self.make_cache_key(repo, **kwargs)
        self.backend.set(key, data, ttl or self.ttl)

    def delete(self, repo: str, **kwargs) -> bool:
        """Delete cached release data for a repo.

        Args:
            repo: Repository identifier.
            **kwargs: Additional parameters that affect the query.

        Returns:
            True if deleted.
        """
        if self.backend is None:
            return False

        key = self.make_cache_key(repo, **kwargs)
        return self.backend.delete(key)

    def clear(self) -> int:
        """Clear all cached release data."""
        if self.backend is None:
            return 0
        return self.backend.clear()

    def cleanup(self) -> int:
        """Clean up expired entries."""
        if self.backend is None:
            return 0
        return self.backend.cleanup()

    def info(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self.backend is None:
            return {"enabled": self.enabled, "backend": None}
        info = self.backend.info()
        info["enabled"] = self.enabled
        info["ttl"] = self.ttl
        return info


def create_cache_backend(backend_type: Optional[str] = None) -> CacheBackend:
    """Create a cache backend based on configuration.

    Args:
        backend_type: Optional backend type override ("file" or "redis").

    Returns:
        Configured cache backend.

    Raises:
        ValueError: If backend type is unknown.
        ImportError: If redis backend requested but redis not installed.
    """
    config = get_config()

    if backend_type is None:
        backend_type = config.cache_backend

    if backend_type == "file":
        return FileCacheBackend(
            cache_dir=config.file_cache_path,
            default_ttl=config.release_cache_ttl,
            max_age=config.file_cache_max_age,
            max_size=config.file_cache_max_size,
        )
    if backend_type == "redis":
        return RedisCacheBackend(
            url=config.redis_url,
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=config.redis_password,
            key_prefix=config.redis_key_prefix,
            default_ttl=config.release_cache_ttl,
        )
    raise ValueError(f"Unknown cache backend: {backend_type}")


# Global release cache instance
_release_cache: Optional[ReleaseDataCache] = None


def get_release_cache() -> ReleaseDataCache:
    """Get the global release data cache instance.

    Returns:
        The global ReleaseDataCache instance.
    """
    global _release_cache  # pylint: disable=global-statement
    if _release_cache is None:
        config = get_config()
        _release_cache = ReleaseDataCache(
            enabled=config.release_cache_enabled,
            ttl=config.release_cache_ttl,
        )
    return _release_cache


def reset_release_cache() -> None:
    """Reset the global release cache instance.

    Useful for testing.
    """
    global _release_cache  # pylint: disable=global-statement
    _release_cache = None
