#!/usr/bin/env python

"""
Unit tests for ProxyPoolConfig
"""

import pytest

from crawl4weibo.utils.proxy import ProxyPoolConfig


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
