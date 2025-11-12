#!/usr/bin/env python

"""
Unit tests for proxy removal/elimination from pool
"""

import pytest

from crawl4weibo.utils.proxy import ProxyPool, ProxyPoolConfig


@pytest.mark.unit
class TestProxyRemoval:
    """Unit tests for proxy removal/elimination mechanism"""

    def test_remove_proxy_from_pool(self):
        """Test removing a specific proxy from pool"""
        config = ProxyPoolConfig(fetch_strategy="round_robin")
        pool = ProxyPool(config=config)
        pool.add_proxy("http://1.2.3.4:8080")
        pool.add_proxy("http://5.6.7.8:9090")
        pool.add_proxy("http://10.11.12.13:3128")

        assert pool.get_pool_size() == 3

        removed = pool.remove_proxy("http://5.6.7.8:9090")
        assert removed is True
        assert pool.get_pool_size() == 2

        proxies_in_pool = [pool.get_proxy()["http"] for _ in range(2)]
        assert "http://5.6.7.8:9090" not in proxies_in_pool
        assert "http://1.2.3.4:8080" in proxies_in_pool
        assert "http://10.11.12.13:3128" in proxies_in_pool

    def test_remove_nonexistent_proxy(self):
        """Test removing a proxy that doesn't exist"""
        pool = ProxyPool()
        pool.add_proxy("http://1.2.3.4:8080")

        removed = pool.remove_proxy("http://9.9.9.9:9999")
        assert removed is False
        assert pool.get_pool_size() == 1

    def test_remove_proxy_adjusts_round_robin_index(self):
        """Test that removing proxy adjusts round-robin index correctly"""
        config = ProxyPoolConfig(fetch_strategy="round_robin")
        pool = ProxyPool(config=config)
        pool.add_proxy("http://1.2.3.4:8080")
        pool.add_proxy("http://5.6.7.8:9090")
        pool.add_proxy("http://10.11.12.13:3128")

        proxy1 = pool.get_proxy()
        proxy2 = pool.get_proxy()
        assert proxy1["http"] == "http://1.2.3.4:8080"
        assert proxy2["http"] == "http://5.6.7.8:9090"

        pool.remove_proxy("http://1.2.3.4:8080")
        pool.remove_proxy("http://5.6.7.8:9090")

        assert pool.get_pool_size() == 1
        proxy3 = pool.get_proxy()
        assert proxy3["http"] == "http://10.11.12.13:3128"

    def test_remove_proxy_in_once_mode_does_nothing(self):
        """Test that remove_proxy does nothing in once mode"""
        config = ProxyPoolConfig(use_once_proxy=True)
        pool = ProxyPool(config=config)

        pool.add_proxy("http://1.2.3.4:8080")
        assert pool.get_pool_size() == 1

        removed = pool.remove_proxy("http://1.2.3.4:8080")
        assert removed is False
        assert pool.get_pool_size() == 1

    def test_remove_all_proxies_from_pool(self):
        """Test removing all proxies leaves pool empty"""
        pool = ProxyPool()
        pool.add_proxy("http://1.2.3.4:8080")
        pool.add_proxy("http://5.6.7.8:9090")

        pool.remove_proxy("http://1.2.3.4:8080")
        pool.remove_proxy("http://5.6.7.8:9090")

        assert pool.get_pool_size() == 0
        assert pool.get_proxy() is None

    def test_remove_proxy_with_auth(self):
        """Test removing proxy with authentication credentials"""
        pool = ProxyPool()
        pool.add_proxy("http://user:pass@1.2.3.4:8080")
        pool.add_proxy("http://5.6.7.8:9090")

        assert pool.get_pool_size() == 2

        removed = pool.remove_proxy("http://user:pass@1.2.3.4:8080")
        assert removed is True
        assert pool.get_pool_size() == 1

        proxy = pool.get_proxy()
        assert proxy["http"] == "http://5.6.7.8:9090"
