#!/usr/bin/env python

"""
Unit tests for ProxyPool dynamic API fetching
Tests: API fetching, parsers, batch operations, error handling
"""

import pytest
import responses

from crawl4weibo.utils.proxy import ProxyPool, ProxyPoolConfig


@pytest.mark.unit
class TestProxyPoolDynamic:
    """Unit tests for dynamic proxy fetching from API"""

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


@pytest.mark.unit
class TestProxyPoolBatch:
    """Unit tests for batch proxy fetching"""

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
