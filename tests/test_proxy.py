#!/usr/bin/env python

"""
Test cases for proxy pool functionality
"""

import time

import pytest
import responses

from crawl4weibo.utils.proxy import ProxyPool, ProxyPoolConfig


@pytest.mark.unit
class TestProxyPoolConfig:
    """Unit tests for ProxyPoolConfig class"""

    def test_default_config(self):
        """Test default configuration"""
        config = ProxyPoolConfig()
        assert config.proxy_api_url is None
        assert config.dynamic_proxy_ttl == 300
        assert config.pool_size == 10
        assert config.fetch_strategy == "random"

    def test_custom_config(self):
        """Test custom configuration"""
        config = ProxyPoolConfig(
            proxy_api_url="http://api.proxy.com/get",
            dynamic_proxy_ttl=600,
            pool_size=20,
            fetch_strategy="round_robin",
        )
        assert config.proxy_api_url == "http://api.proxy.com/get"
        assert config.dynamic_proxy_ttl == 600
        assert config.pool_size == 20
        assert config.fetch_strategy == "round_robin"


@pytest.mark.unit
class TestProxyPool:
    """Unit tests for ProxyPool class"""

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

    @responses.activate
    def test_pool_auto_fetch_when_not_full(self):
        """Test pool automatically fetches proxy when not full"""
        proxy_api_url = "http://api.proxy.com/get"
        config = ProxyPoolConfig(proxy_api_url=proxy_api_url, pool_size=2)
        pool = ProxyPool(config=config)

        # Mock API to return different proxies
        responses.add(
            responses.GET,
            proxy_api_url,
            json={"ip": "1.2.3.4", "port": "8080"},
            status=200,
        )

        # First get_proxy should fetch from API
        proxy1 = pool.get_proxy()
        assert proxy1 is not None
        assert pool.get_pool_size() == 1

        # Add another response
        responses.add(
            responses.GET,
            proxy_api_url,
            json={"ip": "5.6.7.8", "port": "8080"},
            status=200,
        )

        # Second get_proxy should fetch another one
        proxy2 = pool.get_proxy()
        assert proxy2 is not None
        assert pool.get_pool_size() == 2

    @responses.activate
    def test_pool_no_fetch_when_full(self):
        """Test pool doesn't fetch when already full"""
        proxy_api_url = "http://api.proxy.com/get"
        config = ProxyPoolConfig(proxy_api_url=proxy_api_url, pool_size=2)
        pool = ProxyPool(config=config)

        # Add 2 static proxies to fill the pool
        pool.add_proxy("http://1.2.3.4:8080")
        pool.add_proxy("http://5.6.7.8:8080")

        assert pool.get_pool_size() == 2

        # get_proxy should not trigger API call when pool is full
        proxy = pool.get_proxy()
        assert proxy is not None
        assert pool.get_pool_size() == 2  # Still 2

    @responses.activate
    def test_get_proxy_with_default_parser(self):
        """Test getting proxy with default parser"""
        proxy_api_url = "http://api.proxy.com/get"
        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        responses.add(
            responses.GET,
            proxy_api_url,
            json={"ip": "1.2.3.4", "port": "8080"},
            status=200,
        )

        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is not None
        assert proxy["http"] == "http://1.2.3.4:8080"
        assert proxy["https"] == "http://1.2.3.4:8080"

    @responses.activate
    def test_get_proxy_with_auth(self):
        """Test getting proxy with authentication"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            json={
                "ip": "1.2.3.4",
                "port": "8080",
                "username": "user",
                "password": "pass",
            },
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is not None
        assert proxy["http"] == "http://user:pass@1.2.3.4:8080"
        assert proxy["https"] == "http://user:pass@1.2.3.4:8080"

    @responses.activate
    def test_get_proxy_with_proxy_field(self):
        """Test parsing response with proxy field"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            json={"proxy": "http://5.6.7.8:9090"},
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is not None
        assert proxy["http"] == "http://5.6.7.8:9090"
        assert proxy["https"] == "http://5.6.7.8:9090"

    @responses.activate
    def test_get_proxy_with_nested_data(self):
        """Test parsing nested response data"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            json={"data": {"ip": "10.20.30.40", "port": 7777}},
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is not None
        assert proxy["http"] == "http://10.20.30.40:7777"
        assert proxy["https"] == "http://10.20.30.40:7777"

    @responses.activate
    def test_get_proxy_with_custom_parser(self):
        """Test using custom parser"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            json={"result": {"host": "1.1.1.1", "port": "3128"}},
            status=200,
        )

        def custom_parser(data):
            host = data["result"]["host"]
            port = data["result"]["port"]
            return [f"http://{host}:{port}"]

        config = ProxyPoolConfig(
            proxy_api_url=proxy_api_url, proxy_api_parser=custom_parser
        )
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is not None
        assert proxy["http"] == "http://1.1.1.1:3128"
        assert proxy["https"] == "http://1.1.1.1:3128"

    @responses.activate
    def test_get_proxy_api_failure(self):
        """Test proxy API failure returns None"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(responses.GET, proxy_api_url, status=500)

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is None

    @responses.activate
    def test_get_proxy_invalid_json(self):
        """Test invalid JSON response returns None"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(responses.GET, proxy_api_url, body="invalid json", status=200)

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is None

    @responses.activate
    def test_get_proxy_parser_error(self):
        """Test parser exception returns None"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            json={"unexpected": "format"},
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is None

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

    @responses.activate
    def test_dynamic_proxy_added_to_pool(self):
        """Test dynamic proxy is added to pool with TTL"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            json={"ip": "1.2.3.4", "port": "8080"},
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url, dynamic_proxy_ttl=60)
        pool = ProxyPool(config=config)
        assert pool.get_pool_size() == 0

        proxy = pool.get_proxy()
        assert proxy is not None
        assert pool.get_pool_size() == 1

    @responses.activate
    def test_fallback_to_dynamic_when_pool_empty(self):
        """Test fallback to dynamic API when pool is empty"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            json={"ip": "1.2.3.4", "port": "8080"},
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is not None
        assert proxy["http"] == "http://1.2.3.4:8080"

    @responses.activate
    def test_get_proxy_plain_text_format(self):
        """Test parsing plain text proxy format (ip:port)"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            body="218.95.37.11:25152\n219.150.218.21:25089\n218.95.37.161:25015",
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is not None
        # All 3 proxies should be in pool
        assert pool.get_pool_size() == 3
        # Proxy should be one of the three
        assert proxy["http"] in [
            "http://218.95.37.11:25152",
            "http://219.150.218.21:25089",
            "http://218.95.37.161:25015",
        ]

    @responses.activate
    def test_get_proxy_plain_text_single_line(self):
        """Test parsing single line plain text proxy"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET, proxy_api_url, body="10.20.30.40:8080", status=200
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is not None
        assert proxy["http"] == "http://10.20.30.40:8080"
        assert proxy["https"] == "http://10.20.30.40:8080"

    @responses.activate
    def test_get_proxy_plain_text_with_auth(self):
        """Test parsing plain text proxy with authentication (ip:port:user:pass)"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            body="218.95.37.11:25152:myuser:mypass",
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is not None
        assert proxy["http"] == "http://myuser:mypass@218.95.37.11:25152"
        assert proxy["https"] == "http://myuser:mypass@218.95.37.11:25152"

    @responses.activate
    def test_get_proxy_plain_text_multiline_with_auth(self):
        """Test parsing multiple lines with auth"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            body="218.95.37.11:25152:user1:pass1\n219.150.218.21:25089:user2:pass2",
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is not None
        # Both proxies should be in pool
        assert pool.get_pool_size() == 2
        # Proxy should be one of the two
        assert proxy["http"] in [
            "http://user1:pass1@218.95.37.11:25152",
            "http://user2:pass2@219.150.218.21:25089",
        ]

    @responses.activate
    def test_get_proxy_json_array_with_colon_format(self):
        """Test parsing JSON array with colon-separated proxy strings"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            json={
                "data": [
                    "218.95.37.11:25152:username:password",
                    "219.150.218.21:25089:username:password",
                    "218.95.37.161:25015:username:password",
                ]
            },
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is not None
        # All 3 proxies should be in pool
        assert pool.get_pool_size() == 3
        # Proxy should be one of the three
        assert proxy["http"] in [
            "http://username:password@218.95.37.11:25152",
            "http://username:password@219.150.218.21:25089",
            "http://username:password@218.95.37.161:25015",
        ]

    @responses.activate
    def test_get_proxy_json_array_with_colon_format_no_auth(self):
        """Test parsing JSON array with colon-separated proxy strings without auth"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            json={"data": ["10.20.30.40:8080", "50.60.70.80:9090"]},
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is not None
        # Both proxies should be in pool
        assert pool.get_pool_size() == 2
        # Proxy should be one of the two
        assert proxy["http"] in ["http://10.20.30.40:8080", "http://50.60.70.80:9090"]

    @responses.activate
    def test_get_proxy_with_special_chars_in_credentials(self):
        """Test URL encoding of special characters in username/password"""
        proxy_api_url = "http://api.proxy.com/get"
        # Test with special characters: @, :, /
        responses.add(
            responses.GET,
            proxy_api_url,
            json={
                "ip": "1.2.3.4",
                "port": "8080",
                "username": "user@domain",
                "password": "pass:word/123",
            },
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is not None
        # Special characters should be URL encoded
        assert proxy["http"] == "http://user%40domain:pass%3Aword%2F123@1.2.3.4:8080"
        assert proxy["https"] == "http://user%40domain:pass%3Aword%2F123@1.2.3.4:8080"

    @responses.activate
    def test_get_proxy_plain_text_with_special_chars_in_credentials(self):
        """Test URL encoding for plain text format with special chars (excluding colon)"""
        proxy_api_url = "http://api.proxy.com/get"
        # Note: colon (:) cannot be used in plain text format as it's the delimiter
        # Test with @, /, and other special chars
        responses.add(
            responses.GET,
            proxy_api_url,
            body="10.20.30.40:9090:user@test:p@ss/w0rd",
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is not None
        assert proxy["http"] == "http://user%40test:p%40ss%2Fw0rd@10.20.30.40:9090"
        assert proxy["https"] == "http://user%40test:p%40ss%2Fw0rd@10.20.30.40:9090"

    @responses.activate
    def test_batch_proxy_fetch_multiple_proxies(self):
        """Test fetching multiple proxies from API in one call"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            json={
                "data": [
                    {"ip": "1.2.3.4", "port": "8080"},
                    {"ip": "5.6.7.8", "port": "9090"},
                    {"ip": "10.11.12.13", "port": "3128"},
                ]
            },
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url, pool_size=5)
        pool = ProxyPool(config=config)

        # First call should fetch all 3 proxies
        proxy = pool.get_proxy()
        assert proxy is not None
        assert pool.get_pool_size() == 3

    @responses.activate
    def test_batch_proxy_respects_pool_size(self):
        """Test batch fetch respects pool size limit"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            json={
                "data": [
                    {"ip": "1.2.3.4", "port": "8080"},
                    {"ip": "5.6.7.8", "port": "9090"},
                    {"ip": "10.11.12.13", "port": "3128"},
                    {"ip": "20.21.22.23", "port": "8888"},
                    {"ip": "30.31.32.33", "port": "7777"},
                ]
            },
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url, pool_size=3)
        pool = ProxyPool(config=config)

        # Should only add first 3 proxies due to pool size limit
        proxy = pool.get_proxy()
        assert proxy is not None
        assert pool.get_pool_size() == 3

    @responses.activate
    def test_batch_proxy_partial_fill(self):
        """Test batch fetch partially fills pool when already has proxies"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            json={
                "data": [
                    {"ip": "10.11.12.13", "port": "3128"},
                    {"ip": "20.21.22.23", "port": "8888"},
                    {"ip": "30.31.32.33", "port": "7777"},
                ]
            },
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url, pool_size=4)
        pool = ProxyPool(config=config)

        # Add 2 static proxies
        pool.add_proxy("http://1.2.3.4:8080")
        pool.add_proxy("http://5.6.7.8:9090")
        assert pool.get_pool_size() == 2

        # Should only add 2 more to reach pool size of 4
        proxy = pool.get_proxy()
        assert proxy is not None
        assert pool.get_pool_size() == 4

    @responses.activate
    def test_batch_proxy_plain_text_multiple_lines(self):
        """Test batch parsing of multiple plain text proxies"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            body="1.2.3.4:8080\n5.6.7.8:9090\n10.11.12.13:3128",
            status=200,
        )

        config = ProxyPoolConfig(proxy_api_url=proxy_api_url, pool_size=5)
        pool = ProxyPool(config=config)

        proxy = pool.get_proxy()
        assert proxy is not None
        # Should have all 3 proxies in pool
        assert pool.get_pool_size() == 3

    @responses.activate
    def test_custom_parser_returns_multiple_proxies(self):
        """Test custom parser can return multiple proxies"""
        proxy_api_url = "http://api.proxy.com/get"
        responses.add(
            responses.GET,
            proxy_api_url,
            json={
                "proxies": [
                    {"host": "1.1.1.1", "port": "3128"},
                    {"host": "2.2.2.2", "port": "8080"},
                ]
            },
            status=200,
        )

        def custom_parser(data):
            proxies = data["proxies"]
            return [f"http://{p['host']}:{p['port']}" for p in proxies]

        config = ProxyPoolConfig(
            proxy_api_url=proxy_api_url,
            proxy_api_parser=custom_parser,
            pool_size=5,
        )
        pool = ProxyPool(config=config)
        proxy = pool.get_proxy()

        assert proxy is not None
        assert pool.get_pool_size() == 2


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


