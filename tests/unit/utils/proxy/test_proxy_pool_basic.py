#!/usr/bin/env python

"""
Unit tests for basic ProxyPool operations
Tests: add, get, clear, rotation, expiration, capacity
"""

import time

import pytest

from crawl4weibo.utils.proxy import ProxyPool, ProxyPoolConfig


@pytest.mark.unit
class TestProxyPoolBasic:
    """Unit tests for basic ProxyPool operations"""

    def test_add_static_proxy_without_ttl(self):
        """Test adding static proxy without expiration"""
        pool = ProxyPool()
        pool.add_proxy("http://1.2.3.4:8080")

        assert pool.get_pool_size() == 1
        proxy = pool.get_proxy()
        assert proxy["http"] == "http://1.2.3.4:8080"

    def test_add_static_proxy_with_ttl(self):
        """Test adding static proxy with expiration"""
        pool = ProxyPool()
        pool.add_proxy("http://1.2.3.4:8080", ttl=1)

        assert pool.get_pool_size() == 1
        time.sleep(1.5)
        assert pool.get_pool_size() == 0

    def test_add_multiple_static_proxies(self):
        """Test adding multiple static proxies"""
        pool = ProxyPool()
        pool.add_proxy("http://1.2.3.4:8080")
        pool.add_proxy("http://5.6.7.8:8080")
        pool.add_proxy("http://9.10.11.12:8080")

        assert pool.get_pool_size() == 3

    def test_proxy_round_robin_rotation(self):
        """Test proxy round-robin rotation from pool"""
        config = ProxyPoolConfig(fetch_strategy="round_robin")
        pool = ProxyPool(config=config)
        pool.add_proxy("http://1.2.3.4:8080")
        pool.add_proxy("http://5.6.7.8:8080")

        proxy1 = pool.get_proxy()
        proxy2 = pool.get_proxy()
        proxy3 = pool.get_proxy()

        assert proxy1["http"] == "http://1.2.3.4:8080"
        assert proxy2["http"] == "http://5.6.7.8:8080"
        assert proxy3["http"] == "http://1.2.3.4:8080"

    def test_proxy_random_selection(self):
        """Test proxy random selection from pool"""
        config = ProxyPoolConfig(fetch_strategy="random")
        pool = ProxyPool(config=config)
        pool.add_proxy("http://1.2.3.4:8080")
        pool.add_proxy("http://5.6.7.8:8080")

        # Test that we can get proxies (random selection)
        proxy = pool.get_proxy()
        assert proxy is not None
        assert proxy["http"] in ["http://1.2.3.4:8080", "http://5.6.7.8:8080"]

    def test_clean_expired_proxies(self):
        """Test expired proxies are cleaned"""
        pool = ProxyPool()
        pool.add_proxy("http://1.2.3.4:8080", ttl=1)
        pool.add_proxy("http://5.6.7.8:8080")

        assert pool.get_pool_size() == 2
        time.sleep(1.5)
        assert pool.get_pool_size() == 1

    def test_clear_pool(self):
        """Test clearing proxy pool"""
        pool = ProxyPool()
        pool.add_proxy("http://1.2.3.4:8080")
        pool.add_proxy("http://5.6.7.8:8080")

        assert pool.get_pool_size() == 2
        pool.clear_pool()
        assert pool.get_pool_size() == 0

    def test_pool_capacity(self):
        """Test IP pool capacity management"""
        config = ProxyPoolConfig(pool_size=3)
        pool = ProxyPool(config=config)

        assert pool.get_pool_capacity() == 3

    def test_is_enabled_with_api(self):
        """Test proxy pool enabled with API"""
        config = ProxyPoolConfig(proxy_api_url="http://api.proxy.com/get")
        pool = ProxyPool(config=config)
        assert pool.is_enabled() is True

    def test_is_enabled_with_static_proxy(self):
        """Test proxy pool enabled with static proxies"""
        pool = ProxyPool()
        assert pool.is_enabled() is False

        pool.add_proxy("http://1.2.3.4:8080")
        assert pool.is_enabled() is True
