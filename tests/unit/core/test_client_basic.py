"""Tests for WeiboClient basic functionality"""

from unittest.mock import patch

import pytest
import responses

from crawl4weibo import Post, User, WeiboClient


@pytest.mark.unit
class TestWeiboClient:
    def test_client_initialization(self):
        """Test client initialization"""
        client = WeiboClient()
        assert client is not None
        assert hasattr(client, "get_user_by_uid")
        assert hasattr(client, "get_user_posts")
        assert hasattr(client, "get_post_by_bid")
        assert hasattr(client, "search_users")
        assert hasattr(client, "search_posts")

    def test_client_methods_exist(self):
        """Test that all expected methods exist"""
        client = WeiboClient()
        methods = [
            "get_user_by_uid",
            "get_user_posts",
            "get_post_by_bid",
            "search_users",
            "search_posts",
            "search_posts_by_count",
        ]

        for method in methods:
            assert hasattr(client, method), f"Method {method} should exist"
            assert callable(getattr(client, method)), (
                f"Method {method} should be callable"
            )

    def test_imports_work(self):
        """Test that imports work correctly"""
        assert WeiboClient is not None
        assert User is not None
        assert Post is not None

    def test_client_with_proxy_initialization(self):
        """Test client initialization with proxy"""
        proxy_api_url = "http://api.proxy.com/get"
        client = WeiboClient(proxy_api_url=proxy_api_url)

        assert client is not None
        assert client.proxy_pool is not None
        assert client.proxy_pool.config.proxy_api_url == proxy_api_url

    def test_client_without_proxy(self):
        """Test client initialization without proxy"""
        client = WeiboClient()
        assert client.proxy_pool is not None
        assert client.proxy_pool.get_pool_size() == 0

    def test_add_proxy_to_client(self):
        """Test adding static proxy to client"""
        client = WeiboClient()
        client.add_proxy("http://1.2.3.4:8080", ttl=60)

        assert client.get_proxy_pool_size() == 1

    def test_clear_proxy_pool(self):
        """Test clearing proxy pool"""
        client = WeiboClient()
        client.add_proxy("http://1.2.3.4:8080")
        client.add_proxy("http://5.6.7.8:8080")

        assert client.get_proxy_pool_size() == 2
        client.clear_proxy_pool()
        assert client.get_proxy_pool_size() == 0

    @responses.activate
    def test_request_uses_proxy_when_enabled(self):
        """Test requests use proxy when enabled"""
        proxy_api_url = "http://api.proxy.com/get"
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"

        responses.add(
            responses.GET,
            proxy_api_url,
            json={"ip": "1.2.3.4", "port": "8080"},
            status=200,
        )

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

        client = WeiboClient(proxy_api_url=proxy_api_url)

        with patch.object(
            client.proxy_pool, "get_proxy", wraps=client.proxy_pool.get_proxy
        ) as mock_get_proxy:
            user = client.get_user_by_uid("2656274875")
            mock_get_proxy.assert_called()

        assert user is not None
        assert user.screen_name == "TestUser"

    @responses.activate
    def test_request_without_proxy_when_disabled(self):
        """Test requests skip proxy when use_proxy=False"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"
        proxy_api_url = "http://api.proxy.com/get"

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

        client = WeiboClient(proxy_api_url=proxy_api_url)

        with patch.object(client.proxy_pool, "get_proxy") as mock_get_proxy:
            user = client.get_user_by_uid("2656274875", use_proxy=False)
            mock_get_proxy.assert_not_called()

        assert user is not None
        assert user.screen_name == "TestUser"
