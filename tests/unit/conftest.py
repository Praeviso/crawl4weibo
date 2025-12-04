"""
Pytest fixtures for unit tests

This module provides common fixtures for unit testing, including
a WeiboClient instance with rate limiting disabled for faster test execution.
"""

from unittest.mock import MagicMock, patch

import pytest

from crawl4weibo import WeiboClient
from crawl4weibo.utils.proxy import ProxyPoolConfig
from crawl4weibo.utils.rate_limit import RateLimitConfig


@pytest.fixture
def client_no_rate_limit():
    """
    Provides a WeiboClient instance with rate limiting disabled.

    Unit tests should use this fixture instead of creating their own
    WeiboClient instances to avoid unnecessary delays. Rate limiting
    is disabled because unit tests mock all external requests and
    don't need throttling.

    Usage:
        def test_something(client_no_rate_limit):
            user = client_no_rate_limit.get_user_by_uid("123")
            assert user is not None

    For tests that explicitly test rate limiting behavior, create
    a custom client with the desired RateLimitConfig instead of
    using this fixture.
    """
    with patch("crawl4weibo.core.client.CookieFetcher"):
        rate_config = RateLimitConfig(disable_delay=True)
        client = WeiboClient(rate_limit_config=rate_config, auto_fetch_cookies=False)
        yield client


@pytest.fixture
def client_no_rate_limit_with_proxy():
    """
    Provides a WeiboClient instance with rate limiting disabled and
    proxy configuration enabled.

    This is useful for testing proxy-related functionality without
    the overhead of rate limiting delays.

    Usage:
        def test_proxy_feature(client_no_rate_limit_with_proxy):
            # Test will use the pre-configured proxy setup
            client = client_no_rate_limit_with_proxy
            # ...
    """
    with patch("crawl4weibo.core.client.CookieFetcher"):
        rate_config = RateLimitConfig(disable_delay=True)
        proxy_config = ProxyPoolConfig(proxy_api_url="http://api.proxy.com/get")
        client = WeiboClient(
            rate_limit_config=rate_config,
            proxy_config=proxy_config,
            auto_fetch_cookies=False,
        )
        yield client


@pytest.fixture
def mock_cookie_fetcher():
    """
    Provides a mocked CookieFetcher that returns dummy cookies.

    This is useful for tests that need to verify cookie handling
    without actually fetching cookies from the network.
    """
    with patch("crawl4weibo.core.client.CookieFetcher") as mock:
        mock_instance = MagicMock()
        mock_instance.fetch_cookies.return_value = {
            "SUB": "_test_sub_cookie",
            "SUBP": "_test_subp_cookie",
        }
        mock.return_value = mock_instance
        yield mock_instance
