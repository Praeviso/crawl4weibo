"""Tests for retry behavior with different proxy modes"""

import time
from unittest.mock import patch

import pytest
import responses

from crawl4weibo import WeiboClient
from crawl4weibo.utils.proxy import ProxyPoolConfig
from crawl4weibo.utils.rate_limit import RateLimitConfig


@pytest.mark.unit
@pytest.mark.slow
class TestOnceProxyRetry:
    """Test retry behavior with one-time proxy mode"""

    @responses.activate
    def test_once_proxy_432_retry_no_wait(self):
        """Test 432 error retry with one-time proxy has no wait time"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"
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

        responses.add(responses.GET, weibo_api_url, status=432)
        responses.add(
            responses.GET,
            weibo_api_url,
            json={
                "ok": 1,
                "data": {
                    "userInfo": {
                        "id": 2656274875,
                        "screen_name": "TestUser",
                        "followers_count": 1000,
                    }
                },
            },
            status=200,
        )

        with patch("crawl4weibo.core.client.CookieFetcher"):
            proxy_config = ProxyPoolConfig(
                proxy_api_url=proxy_api_url, use_once_proxy=True
            )
            rate_config = RateLimitConfig(disable_delay=True)
            client = WeiboClient(
                proxy_config=proxy_config,
                rate_limit_config=rate_config,
                auto_fetch_cookies=False,
            )

            start_time = time.time()
            user = client.get_user_by_uid("2656274875")
            elapsed_time = time.time() - start_time

        assert user is not None
        assert user.screen_name == "TestUser"
        # With mocked cookie fetcher and disabled rate limiting, should complete quickly
        assert elapsed_time < 1.0

    @responses.activate
    def test_once_proxy_network_error_retry_no_wait(self):
        """Test network error retry with one-time proxy has no wait time"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"
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

        responses.add(responses.GET, weibo_api_url, status=500)
        responses.add(
            responses.GET,
            weibo_api_url,
            json={
                "ok": 1,
                "data": {
                    "userInfo": {
                        "id": 2656274875,
                        "screen_name": "TestUser",
                        "followers_count": 1000,
                    }
                },
            },
            status=200,
        )

        with patch("crawl4weibo.core.client.CookieFetcher"):
            proxy_config = ProxyPoolConfig(
                proxy_api_url=proxy_api_url, use_once_proxy=True
            )
            rate_config = RateLimitConfig(disable_delay=True)
            client = WeiboClient(
                proxy_config=proxy_config,
                rate_limit_config=rate_config,
                auto_fetch_cookies=False,
            )

            start_time = time.time()
            user = client.get_user_by_uid("2656274875")
            elapsed_time = time.time() - start_time

        assert user is not None
        assert user.screen_name == "TestUser"
        # With mocked cookie fetcher and disabled rate limiting, should complete quickly
        assert elapsed_time < 1.0

    @responses.activate
    def test_pooled_proxy_432_retry_has_wait(self):
        """Test 432 error retry with pooled proxy has wait time"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"
        proxy_api_url = "http://api.proxy.com/get"

        responses.add(
            responses.GET,
            proxy_api_url,
            json={"data": [{"ip": "1.1.1.1", "port": "8080"}]},
            status=200,
        )

        responses.add(responses.GET, weibo_api_url, status=432)
        responses.add(
            responses.GET,
            weibo_api_url,
            json={
                "ok": 1,
                "data": {
                    "userInfo": {
                        "id": 2656274875,
                        "screen_name": "TestUser",
                        "followers_count": 1000,
                    }
                },
            },
            status=200,
        )

        with patch("crawl4weibo.core.client.CookieFetcher"):
            proxy_config = ProxyPoolConfig(
                proxy_api_url=proxy_api_url, use_once_proxy=False
            )
            rate_config = RateLimitConfig(disable_delay=True)
            client = WeiboClient(
                proxy_config=proxy_config,
                rate_limit_config=rate_config,
                auto_fetch_cookies=False,
            )

            start_time = time.time()
            user = client.get_user_by_uid("2656274875")
            elapsed_time = time.time() - start_time

        assert user is not None
        assert user.screen_name == "TestUser"
        # Test verifies 432 retry has wait time in pooled proxy mode (0.5-1.5s)
        # With disabled rate limiting, this wait is from retry logic
        assert elapsed_time >= 0.5

    @responses.activate
    def test_no_proxy_432_retry_has_longer_wait(self):
        """Test 432 error retry without proxy has longer wait time"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"

        responses.add(responses.GET, weibo_api_url, status=432)
        responses.add(
            responses.GET,
            weibo_api_url,
            json={
                "ok": 1,
                "data": {
                    "userInfo": {
                        "id": 2656274875,
                        "screen_name": "TestUser",
                        "followers_count": 1000,
                    }
                },
            },
            status=200,
        )

        with patch("crawl4weibo.core.client.CookieFetcher"):
            rate_config = RateLimitConfig(disable_delay=True)
            client = WeiboClient(
                rate_limit_config=rate_config, auto_fetch_cookies=False
            )

            start_time = time.time()
            user = client.get_user_by_uid("2656274875")
            elapsed_time = time.time() - start_time

        assert user is not None
        assert user.screen_name == "TestUser"
        # Test verifies 432 retry without proxy has longer wait (4-7s)
        # With disabled rate limiting, this wait is from retry logic
        assert elapsed_time >= 4.0
