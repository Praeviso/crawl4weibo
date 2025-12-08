#!/usr/bin/env python

"""
Proxy pool manager
"""

import random
import time
from dataclasses import dataclass
from typing import Callable, Optional

import requests

from .proxy_parsers import default_proxy_parser


@dataclass
class ProxyPoolConfig:
    """Proxy pool configuration class"""

    proxy_api_url: Optional[str] = None
    """Dynamic proxy API URL"""

    proxy_api_parser: Optional[Callable[[dict], list[str]]] = None
    """Custom proxy API response parser function, should return list of proxy URLs"""

    dynamic_proxy_ttl: int = 300
    """Dynamic proxy expiration time (seconds), default 300 seconds (5 minutes)"""

    pool_size: int = 10
    """Proxy pool capacity, default 10"""

    fetch_strategy: str = "random"
    """Proxy fetch strategy: 'random' or 'round_robin', default random"""

    use_once_proxy: bool = False
    """Use one-time proxy mode: fetch fresh proxy for each request, no pooling.
    When enabled, proxies are used once and discarded, ideal for providers
    that give single-use IPs"""


class ProxyPool:
    """Proxy pool manager, supports unified management of dynamic and static proxies"""

    def __init__(self, config: Optional[ProxyPoolConfig] = None):
        """
        Initialize proxy pool

        Args:
            config: Proxy pool configuration object, if None will use
                default configuration
        """
        self.config = config or ProxyPoolConfig()
        self._proxy_pool: list[tuple[str, float]] = []
        self._current_index = 0
        self._once_mode_buffer: list[str] = []

    def add_proxy(self, proxy_url: str, ttl: Optional[int] = None):
        """
        Manually add static proxy to proxy pool

        Args:
            proxy_url: Proxy URL, format like 'http://1.2.3.4:8080' or 'http://user:pass@ip:port'
            ttl: Expiration time (seconds), None means never expires
        """
        expire_time = time.time() + ttl if ttl is not None else float("inf")
        self._proxy_pool.append((proxy_url, expire_time))

    def _fetch_proxies_from_api(self) -> list[str]:
        """
        Fetch proxy URLs from proxy API

        Returns:
            List of proxy URLs, empty list if fetch failed
        """
        if not self.config.proxy_api_url:
            return []

        try:
            response = requests.get(self.config.proxy_api_url, timeout=5)
            response.raise_for_status()

            try:
                proxy_data = response.json()
            except ValueError:
                proxy_data = response.text

            parser = self.config.proxy_api_parser or default_proxy_parser
            return parser(proxy_data)
        except Exception:
            return []

    def _clean_expired_proxies(self):
        """Clean up expired proxies"""
        current_time = time.time()
        self._proxy_pool = [
            (proxy_url, expire_time)
            for proxy_url, expire_time in self._proxy_pool
            if expire_time > current_time
        ]

    def _is_pool_full(self) -> bool:
        """
        Check if the proxy pool has reached its maximum configured size.
        """
        return len(self._proxy_pool) >= self.config.pool_size

    def get_proxy(self) -> Optional[dict[str, str]]:
        """
        Get an available proxy

        Strategy (one-time mode):
        - Uses a buffer to store batch-fetched proxies
        - Returns proxies from buffer one by one (FIFO)
        - Fetches new batch from API when buffer is empty

        Strategy (pooling mode):
        1. Clean up expired proxies
        2. If proxy pool is not full, try to fetch new proxies from dynamic
           API and add to pool (may add multiple proxies at once)
        3. If proxy pool is full, select proxy from pool based on strategy
           (random/round-robin)
        4. If pool is empty and cannot fetch new proxy, return None

        Returns:
            Proxy dictionary, format: {'http': 'http://...', 'https': 'http://...'}
            Returns None if no proxy is available
        """
        if self.config.use_once_proxy:
            if not self._once_mode_buffer:
                proxy_urls = self._fetch_proxies_from_api()
                if proxy_urls:
                    self._once_mode_buffer.extend(proxy_urls)

            if self._once_mode_buffer:
                proxy_url = self._once_mode_buffer.pop(0)
                return {"http": proxy_url, "https": proxy_url}
            return None

        self._clean_expired_proxies()

        if not self._is_pool_full():
            proxy_urls = self._fetch_proxies_from_api()
            if proxy_urls:
                remaining_slots = self.config.pool_size - len(self._proxy_pool)
                for proxy_url in proxy_urls[:remaining_slots]:
                    self.add_proxy(proxy_url, ttl=self.config.dynamic_proxy_ttl)

        if self._proxy_pool:
            if self.config.fetch_strategy == "random":
                proxy_url, _ = random.choice(self._proxy_pool)
            else:
                proxy_url, _ = self._proxy_pool[self._current_index]
                self._current_index = (self._current_index + 1) % len(self._proxy_pool)
            return {"http": proxy_url, "https": proxy_url}

        return None

    def get_pool_size(self) -> int:
        """
        Get current proxy pool size (excluding expired proxies)

        Returns:
            Number of available proxies
        """
        self._clean_expired_proxies()
        return len(self._proxy_pool)

    def clear_pool(self):
        """
        Clear all proxies from the pool and reset internal buffers.

        This method removes all proxies from the proxy pool, resets the current index,
        and empties the once mode buffer. After calling this method, the proxy pool
        will be empty and ready for new proxies to be added.
        """
        self._proxy_pool = []
        self._current_index = 0
        self._once_mode_buffer = []

    def is_enabled(self) -> bool:
        """
        Check if proxy pool is enabled

        Returns:
            True if dynamic API is configured or there are proxies in the pool
        """
        if self.config.use_once_proxy:
            return bool(self.config.proxy_api_url)

        self._clean_expired_proxies()
        return bool(self.config.proxy_api_url or self._proxy_pool)

    def get_pool_capacity(self) -> int:
        """
        Get proxy pool capacity (maximum number of proxies allowed in the pool)

        Returns:
            Maximum proxy pool capacity
        """
        return self.config.pool_size

    def get_once_buffer_size(self) -> int:
        """
        Get current once mode buffer size (only relevant in once mode)

        Returns:
            Number of proxies remaining in once mode buffer
        """
        return len(self._once_mode_buffer)

    def remove_proxy(self, proxy_url: str) -> bool:
        """
        Remove a specific proxy from the pool (pooling mode only)

        This is used when a proxy fails (e.g., returns 432 error) and should
        be immediately removed from the pool. Only works in pooling mode;
        in once mode, proxies are already single-use and discarded after use.

        Args:
            proxy_url: The proxy URL to remove (e.g., 'http://1.2.3.4:8080')

        Returns:
            True if proxy was found and removed, False otherwise
        """
        if self.config.use_once_proxy:
            return False

        initial_pool_size = len(self._proxy_pool)
        self._proxy_pool = [
            (url, expire_time)
            for url, expire_time in self._proxy_pool
            if url != proxy_url
        ]

        removed = len(self._proxy_pool) < initial_pool_size
        if (
            removed
            and self._current_index >= len(self._proxy_pool)
            and self._proxy_pool
        ):
            self._current_index = 0

        return removed
