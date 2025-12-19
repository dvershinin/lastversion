"""Configuration management for lastversion.

Loads configuration from platform-appropriate location and provides access to
settings throughout the application.

Config file locations:
- Linux: ~/.config/lastversion/lastversion.yml
- macOS: ~/Library/Application Support/lastversion/lastversion.yml
- Windows: C:\\Users\\<user>\\AppData\\Local\\lastversion\\lastversion.yml
"""

import copy
import logging
import os
from typing import Any, Dict, Optional

import yaml
from appdirs import user_cache_dir, user_config_dir

log = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG: Dict[str, Any] = {
    "cache": {
        # Release data cache (stores parsed JSON release data)
        "release_cache": {
            "enabled": False,  # Off by default
            "ttl": 3600,  # 1 hour in seconds when enabled
        },
        # Cache backend: "file" (default) or "redis"
        "backend": "file",
        # File backend settings
        "file": {
            "path": None,  # None = use default appdirs location
            "max_age": 86400,  # Auto-cleanup: delete files older than 24 hours
            "max_size": 104857600,  # 100MB max cache size
        },
        # Redis backend settings (requires lastversion[redis])
        "redis": {
            "url": None,  # e.g., "redis://localhost:6379/0"
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "password": None,
            "key_prefix": "lastversion:",
        },
    }
}

# Singleton instance
_config_instance: Optional["Config"] = None


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence.

    Args:
        base: Base dictionary with default values.
        override: Dictionary with values to override.

    Returns:
        Merged dictionary.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class Config:
    """Configuration manager for lastversion.

    Loads configuration from platform-appropriate location and provides
    access to settings. Uses singleton pattern for global access.
    """

    APP_NAME = "lastversion"
    CONFIG_FILENAME = "lastversion.yml"

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.

        Args:
            config_path: Optional path to config file. If None, uses default location.
        """
        self._config: Dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self._config_path = config_path or self._get_default_config_path()
        self._loaded = False

    def _get_default_config_path(self) -> str:
        """Get the default configuration file path.

        Returns:
            Path to the default config file.
        """
        config_dir = user_config_dir(self.APP_NAME)
        return os.path.join(config_dir, self.CONFIG_FILENAME)

    def load(self) -> "Config":
        """Load configuration from file.

        Returns:
            Self for chaining.
        """
        if self._loaded:
            return self

        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    user_config = yaml.safe_load(f) or {}
                self._config = deep_merge(DEFAULT_CONFIG, user_config)
                log.info("Loaded configuration from %s", self._config_path)
            except (IOError, yaml.YAMLError) as e:
                log.warning("Error loading config file %s: %s", self._config_path, e)
                self._config = copy.deepcopy(DEFAULT_CONFIG)
        else:
            log.debug("No config file found at %s, using defaults", self._config_path)

        self._loaded = True
        return self

    @property
    def config_path(self) -> str:
        """Get the path to the configuration file."""
        return self._config_path

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot-separated key.

        Args:
            key: Dot-separated key path (e.g., "cache.backend").
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        self.load()
        parts = key.split(".")
        value = self._config
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value by dot-separated key.

        This only affects the runtime configuration, not the file.

        Args:
            key: Dot-separated key path (e.g., "cache.backend").
            value: Value to set.
        """
        self.load()
        parts = key.split(".")
        config = self._config
        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]
        config[parts[-1]] = value

    @property
    def cache_backend(self) -> str:
        """Get the configured cache backend."""
        return self.get("cache.backend", "file")

    @property
    def release_cache_enabled(self) -> bool:
        """Check if release data cache is enabled."""
        return self.get("cache.release_cache.enabled", False)

    @property
    def release_cache_ttl(self) -> int:
        """Get the release cache TTL in seconds."""
        return self.get("cache.release_cache.ttl", 3600)

    @property
    def file_cache_path(self) -> str:
        """Get the file cache path."""
        path = self.get("cache.file.path")
        if path:
            return path
        return user_cache_dir(self.APP_NAME)

    @property
    def file_cache_max_age(self) -> int:
        """Get the max age for file cache entries in seconds."""
        return self.get("cache.file.max_age", 86400)

    @property
    def file_cache_max_size(self) -> int:
        """Get the max size for file cache in bytes."""
        return self.get("cache.file.max_size", 104857600)

    @property
    def redis_url(self) -> Optional[str]:
        """Get the Redis URL if configured."""
        return self.get("cache.redis.url")

    @property
    def redis_host(self) -> str:
        """Get the Redis host."""
        return self.get("cache.redis.host", "localhost")

    @property
    def redis_port(self) -> int:
        """Get the Redis port."""
        return self.get("cache.redis.port", 6379)

    @property
    def redis_db(self) -> int:
        """Get the Redis database number."""
        return self.get("cache.redis.db", 0)

    @property
    def redis_password(self) -> Optional[str]:
        """Get the Redis password."""
        return self.get("cache.redis.password")

    @property
    def redis_key_prefix(self) -> str:
        """Get the Redis key prefix."""
        return self.get("cache.redis.key_prefix", "lastversion:")

    def to_dict(self) -> Dict[str, Any]:
        """Return the full configuration as a dictionary."""
        self.load()
        return self._config.copy()


def get_config(config_path: Optional[str] = None) -> Config:
    """Get the global configuration instance.

    Args:
        config_path: Optional path to config file. Only used on first call.

    Returns:
        The global Config instance.
    """
    global _config_instance  # pylint: disable=global-statement
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance


def reset_config() -> None:
    """Reset the global configuration instance.

    Useful for testing.
    """
    global _config_instance  # pylint: disable=global-statement
    _config_instance = None
