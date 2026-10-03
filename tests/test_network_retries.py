"""Regression tests for holder transport retry configuration."""

from cachecontrol import CacheControlAdapter

from lastversion.repo_holders.base import RETRY_METHODS, _make_retry
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


class _LegacyRetry:
    """Mimic urllib3 < 1.26 Retry, which only accepts ``method_whitelist``."""

    def __init__(
        self,
        total=None,
        connect=None,
        read=None,
        status=None,
        backoff_factor=0,
        status_forcelist=None,
        method_whitelist=None,
        respect_retry_after_header=True,
    ):
        self.total = total
        self.method_whitelist = method_whitelist
        self.status_forcelist = status_forcelist


def test_make_retry_falls_back_to_method_whitelist_on_old_urllib3():
    """EL7 ships urllib3 1.25, whose Retry rejects ``allowed_methods``."""
    retries = _make_retry(3, 0.1, retry_cls=_LegacyRetry)

    assert retries.total == 3
    assert retries.method_whitelist == RETRY_METHODS
    assert set(retries.status_forcelist) == {429, 500, 502, 503, 504}


def test_make_retry_limits_methods_on_installed_urllib3():
    """The installed urllib3 (>= 1.26 or the EL7 1.25 line) gets the method policy."""
    retries = _make_retry(3, 0.1)

    try:
        methods = retries.allowed_methods
    except AttributeError:
        methods = retries.method_whitelist
    assert methods == RETRY_METHODS
