#!/usr/bin/env python

"""
Unit tests for ProxyPool once mode (use_once_proxy=True)
Tests single-use proxy functionality with buffering
"""

import pytest
import responses

from crawl4weibo.utils.proxy import ProxyPool, ProxyPoolConfig


@pytest.mark.unit
class TestOnceProxy:
    """Unit tests for one-time proxy mode"""

    @responses.activate
    def test_once_proxy_fetch_fresh_each_time(self):
        """Test one-time mode fetches fresh proxy each time"""
        proxy_api_url = "http://api.proxy.com/get"

        responses.add(
            responses.GET,
            proxy_api_url,
            json={"data": [{"ip": "1.1.1.1", "port": "8080"}]},
            status=200,
        )
        responses.add(
            responses.GET,
            proxy_api_url,
            json={"data": [{"ip": "2.2.2.2", "port": "8080"}]},
            status=200,
        )
        responses.add(
            responses.GET,
            proxy_api_url,
            json={"data": [{"ip": "3.3.3.3", "port": "8080"}]},
            status=200,
        )

        config = ProxyPoolConfig(
            proxy_api_url=proxy_api_url,
            use_once_proxy=True,
        )
        pool = ProxyPool(config=config)

        proxy1 = pool.get_proxy()
        proxy2 = pool.get_proxy()
        proxy3 = pool.get_proxy()

        assert proxy1 == {"http": "http://1.1.1.1:8080", "https": "http://1.1.1.1:8080"}
        assert proxy2 == {"http": "http://2.2.2.2:8080", "https": "http://2.2.2.2:8080"}
        assert proxy3 == {"http": "http://3.3.3.3:8080", "https": "http://3.3.3.3:8080"}
        assert pool.get_pool_size() == 0
        assert pool.get_once_buffer_size() == 0

    @responses.activate
    def test_once_proxy_no_pooling(self):
        """Test one-time mode does not use pooling"""
        proxy_api_url = "http://api.proxy.com/get"

        responses.add(
            responses.GET,
            proxy_api_url,
            json={"data": [{"ip": "1.1.1.1", "port": "8080"}]},
            status=200,
        )

        config = ProxyPoolConfig(
            proxy_api_url=proxy_api_url,
            use_once_proxy=True,
            pool_size=10,
        )
        pool = ProxyPool(config=config)

        pool.add_proxy("http://9.9.9.9:8080")
        assert pool.get_pool_size() == 1

        proxy = pool.get_proxy()
        assert proxy == {"http": "http://1.1.1.1:8080", "https": "http://1.1.1.1:8080"}

    @responses.activate
    def test_once_proxy_api_failure(self):
        """Test one-time mode handles API failure gracefully"""
        proxy_api_url = "http://api.proxy.com/get"

        responses.add(
            responses.GET,
            proxy_api_url,
            status=500,
        )

        config = ProxyPoolConfig(
            proxy_api_url=proxy_api_url,
            use_once_proxy=True,
        )
        pool = ProxyPool(config=config)

        proxy = pool.get_proxy()
        assert proxy is None

    @responses.activate
    def test_once_proxy_is_enabled(self):
        """Test is_enabled works correctly in once mode"""
        proxy_api_url = "http://api.proxy.com/get"

        config = ProxyPoolConfig(
            proxy_api_url=proxy_api_url,
            use_once_proxy=True,
        )
        pool = ProxyPool(config=config)

        assert pool.is_enabled() is True

        pool.add_proxy("http://1.2.3.4:8080")
        assert pool.is_enabled() is True

        config_no_api = ProxyPoolConfig(use_once_proxy=True)
        pool_no_api = ProxyPool(config=config_no_api)
        assert pool_no_api.is_enabled() is False

    @responses.activate
    def test_once_proxy_multiple_proxies_from_api(self):
        """Test one-time mode uses all proxies from batch API response"""
        proxy_api_url = "http://api.proxy.com/get"

        responses.add(
            responses.GET,
            proxy_api_url,
            json={
                "data": [
                    {"ip": "1.1.1.1", "port": "8080"},
                    {"ip": "2.2.2.2", "port": "9090"},
                    {"ip": "3.3.3.3", "port": "3128"},
                ]
            },
            status=200,
        )
        responses.add(
            responses.GET,
            proxy_api_url,
            json={
                "data": [
                    {"ip": "4.4.4.4", "port": "8080"},
                    {"ip": "5.5.5.5", "port": "9090"},
                ]
            },
            status=200,
        )

        config = ProxyPoolConfig(
            proxy_api_url=proxy_api_url,
            use_once_proxy=True,
        )
        pool = ProxyPool(config=config)

        proxy1 = pool.get_proxy()
        assert proxy1 == {"http": "http://1.1.1.1:8080", "https": "http://1.1.1.1:8080"}
        assert pool.get_once_buffer_size() == 2

        proxy2 = pool.get_proxy()
        assert proxy2 == {"http": "http://2.2.2.2:9090", "https": "http://2.2.2.2:9090"}
        assert pool.get_once_buffer_size() == 1

        proxy3 = pool.get_proxy()
        assert proxy3 == {"http": "http://3.3.3.3:3128", "https": "http://3.3.3.3:3128"}
        assert pool.get_once_buffer_size() == 0

        proxy4 = pool.get_proxy()
        assert proxy4 == {"http": "http://4.4.4.4:8080", "https": "http://4.4.4.4:8080"}
        assert pool.get_once_buffer_size() == 1

        proxy5 = pool.get_proxy()
        assert proxy5 == {"http": "http://5.5.5.5:9090", "https": "http://5.5.5.5:9090"}
        assert pool.get_once_buffer_size() == 0

        assert pool.get_pool_size() == 0

    def test_once_proxy_config_defaults(self):
        """Test use_once_proxy defaults to False"""
        config = ProxyPoolConfig()
        assert config.use_once_proxy is False

    @responses.activate
    def test_once_proxy_clear_buffer(self):
        """Test clear_pool also clears once mode buffer"""
        proxy_api_url = "http://api.proxy.com/get"

        responses.add(
            responses.GET,
            proxy_api_url,
            json={
                "data": [
                    {"ip": "1.1.1.1", "port": "8080"},
                    {"ip": "2.2.2.2", "port": "9090"},
                    {"ip": "3.3.3.3", "port": "3128"},
                ]
            },
            status=200,
        )

        config = ProxyPoolConfig(
            proxy_api_url=proxy_api_url,
            use_once_proxy=True,
        )
        pool = ProxyPool(config=config)

        proxy1 = pool.get_proxy()
        assert proxy1 is not None
        assert pool.get_once_buffer_size() == 2

        pool.clear_pool()
        assert pool.get_once_buffer_size() == 0
        assert pool.get_pool_size() == 0

    @responses.activate
    def test_once_proxy_buffer_efficiency(self):
        """Test that buffer reduces API calls for batch responses"""
        proxy_api_url = "http://api.proxy.com/get"

        responses.add(
            responses.GET,
            proxy_api_url,
            json={
                "data": [
                    {"ip": "1.1.1.1", "port": "8080"},
                    {"ip": "2.2.2.2", "port": "8080"},
                    {"ip": "3.3.3.3", "port": "8080"},
                    {"ip": "4.4.4.4", "port": "8080"},
                    {"ip": "5.5.5.5", "port": "8080"},
                ]
            },
            status=200,
        )

        config = ProxyPoolConfig(
            proxy_api_url=proxy_api_url,
            use_once_proxy=True,
        )
        pool = ProxyPool(config=config)

        proxies = [pool.get_proxy() for _ in range(5)]

        assert len(set(p["http"] for p in proxies)) == 5
        assert len(responses.calls) == 1
        assert pool.get_once_buffer_size() == 0
