"""
Cache provider for agent descriptor resolution.

This module provides a simple wrapper around requests-cache
to enable caching of agent descriptors with support for
HTTP caching mechanisms.
"""

import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# Try importing requests_cache, provide fallback if not available
try:
    import requests_cache

    REQUESTS_CACHE_AVAILABLE = True
except ImportError:
    REQUESTS_CACHE_AVAILABLE = False
    logger.warning("requests_cache not found. Install with: pip install requests-cache")

    # Create a mock CachedSession for compatibility
    import requests

    class MockCachedSession(requests.Session):
        """Mock implementation when requests_cache isn't available."""

        def __init__(self, *args, **kwargs):
            super().__init__()
            self.cache = None
            logger.warning("Using uncached session - caching disabled")

    # Create mock module
    class MockRequestsCache:
        def __init__(self):
            self.CachedSession = MockCachedSession

        def is_installed(self):
            return False

    requests_cache = MockRequestsCache()  # type: ignore


class CacheProvider:
    """
    Simple cache provider using requests-cache for HTTP caching.

    This class wraps requests-cache to provide HTTP caching with
    support for standard caching headers (ETag, Last-Modified, Cache-Control).
    """

    def __init__(
        self,
        cache_name: str = "agent_resolver_cache",
        backend: str = "memory",
        expire_after: int = 3600,
        **kwargs,
    ):
        """
        Initialize a cache provider.

        Args:
            cache_name: Name for the cache
            backend: Backend to use ('memory', 'sqlite', etc.)
            expire_after: Default cache expiration in seconds
            **kwargs: Additional arguments passed to requests_cache.install_cache
        """
        self.cache_name = cache_name
        self.backend = backend
        self.expire_after = expire_after
        self.kwargs = kwargs
        self.session = self._create_cached_session()

    def _create_cached_session(self) -> requests_cache.CachedSession:
        """Create and return a cached session."""
        return requests_cache.CachedSession(
            cache_name=self.cache_name,
            backend=self.backend,
            expire_after=timedelta(seconds=self.expire_after),
            allowable_methods=("GET", "HEAD"),
            **self.kwargs,
        )

    def clear(self) -> None:
        """Clear all cache entries."""
        self.session.cache.clear()
        logger.debug("Cache cleared")

    def get_session(self) -> requests_cache.CachedSession:
        """Get the cached session for making requests."""
        return self.session

    @property
    def is_installed(self) -> bool:
        """Check if requests-cache is properly installed."""
        return requests_cache.is_installed()


# Default in-memory cache singleton
default_cache = CacheProvider()
