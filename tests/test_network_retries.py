"""Regression tests for holder transport retry configuration."""

from cachecontrol import CacheControlAdapter

from lastversion.repo_holders.test import TestProjectHolder as ProjectHolder


def test_cache_adapter_retries_transient_connection_and_server_failures():
    """Keep retry policy attached after CacheControl replaces the adapter."""
    holder = ProjectHolder("example")

    adapter = holder.get_adapter("https://example.com/releases")
    retries = adapter.max_retries

    assert isinstance(adapter, CacheControlAdapter)
    assert retries.total == holder.NETWORK_RETRIES
    assert retries.connect == holder.NETWORK_RETRIES
    assert retries.read == holder.NETWORK_RETRIES
    assert retries.status == holder.NETWORK_RETRIES
    assert retries.backoff_factor == holder.NETWORK_BACKOFF_FACTOR
    assert set(retries.status_forcelist) == {429, 500, 502, 503, 504}
    assert retries.respect_retry_after_header is True
