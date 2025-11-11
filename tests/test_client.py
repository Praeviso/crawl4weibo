"""Tests for WeiboClient"""

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


@pytest.mark.unit
class TestSearchPostsByCount:
    """Test search_posts_by_count method"""

    @responses.activate
    def test_search_posts_by_count_exact_count(self):
        """Test fetching exact count of posts"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"

        # Mock response with 10 posts per page
        mock_post_data = {
            "ok": 1,
            "data": {
                "cards": [
                    {
                        "card_type": 9,
                        "mblog": {
                            "id": f"500000000{i}",
                            "bid": f"MnHwC{i}",
                            "text": f"Test post {i}",
                            "created_at": "Tue Jan 01 12:00:00 +0800 2024",
                            "user": {"id": 123456},
                            "reposts_count": 10,
                            "comments_count": 5,
                            "attitudes_count": 20,
                        },
                    }
                    for i in range(10)
                ]
            },
        }

        responses.add(
            responses.GET,
            weibo_api_url,
            json=mock_post_data,
            status=200,
        )

        client = WeiboClient()
        posts = client.search_posts_by_count("Python", count=25)

        # Should fetch 3 pages to get 25 posts (10+10+5)
        assert len(posts) == 25
        assert all(isinstance(post, Post) for post in posts)

    @responses.activate
    def test_search_posts_by_count_less_than_available(self):
        """Test when fewer posts are available than requested"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"

        # Mock first page with posts
        mock_post_data_page1 = {
            "ok": 1,
            "data": {
                "cards": [
                    {
                        "card_type": 9,
                        "mblog": {
                            "id": f"500000000{i}",
                            "bid": f"MnHwC{i}",
                            "text": f"Test post {i}",
                            "created_at": "Tue Jan 01 12:00:00 +0800 2024",
                            "user": {"id": 123456},
                            "reposts_count": 10,
                            "comments_count": 5,
                            "attitudes_count": 20,
                        },
                    }
                    for i in range(5)
                ]
            },
        }

        # Mock second page with no posts
        mock_post_data_page2 = {"ok": 1, "data": {"cards": []}}

        responses.add(
            responses.GET,
            weibo_api_url,
            json=mock_post_data_page1,
            status=200,
        )

        responses.add(
            responses.GET,
            weibo_api_url,
            json=mock_post_data_page2,
            status=200,
        )

        client = WeiboClient()
        posts = client.search_posts_by_count("Python", count=20)

        # Should return only 5 posts (all available)
        assert len(posts) == 5
        assert all(isinstance(post, Post) for post in posts)

    @responses.activate
    def test_search_posts_by_count_respects_max_pages(self):
        """Test that max_pages limit is respected"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"

        mock_post_data = {
            "ok": 1,
            "data": {
                "cards": [
                    {
                        "card_type": 9,
                        "mblog": {
                            "id": f"500000000{i}",
                            "bid": f"MnHwC{i}",
                            "text": f"Test post {i}",
                            "created_at": "Tue Jan 01 12:00:00 +0800 2024",
                            "user": {"id": 123456},
                            "reposts_count": 10,
                            "comments_count": 5,
                            "attitudes_count": 20,
                        },
                    }
                    for i in range(10)
                ]
            },
        }

        # Add enough responses for more than max_pages
        for _ in range(10):
            responses.add(
                responses.GET,
                weibo_api_url,
                json=mock_post_data,
                status=200,
            )

        client = WeiboClient()
        posts = client.search_posts_by_count("Python", count=100, max_pages=3)

        # Should fetch only 3 pages = 30 posts
        assert len(posts) == 30
        assert all(isinstance(post, Post) for post in posts)

    @responses.activate
    def test_search_posts_by_count_with_proxy(self):
        """Test search_posts_by_count uses proxy when enabled"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"
        proxy_api_url = "http://api.proxy.com/get"

        responses.add(
            responses.GET,
            proxy_api_url,
            json={"ip": "1.2.3.4", "port": "8080"},
            status=200,
        )

        mock_post_data = {
            "ok": 1,
            "data": {
                "cards": [
                    {
                        "card_type": 9,
                        "mblog": {
                            "id": "5000000001",
                            "bid": "MnHwC1",
                            "text": "Test post 1",
                            "created_at": "Tue Jan 01 12:00:00 +0800 2024",
                            "user": {"id": 123456},
                            "reposts_count": 10,
                            "comments_count": 5,
                            "attitudes_count": 20,
                        },
                    }
                ]
            },
        }

        responses.add(
            responses.GET,
            weibo_api_url,
            json=mock_post_data,
            status=200,
        )

        client = WeiboClient(proxy_api_url=proxy_api_url)

        with patch.object(
            client.proxy_pool, "get_proxy", wraps=client.proxy_pool.get_proxy
        ) as mock_get_proxy:
            posts = client.search_posts_by_count("Python", count=1)
            mock_get_proxy.assert_called()

        assert len(posts) == 1


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

        client = WeiboClient(proxy_api_url=proxy_api_url, use_once_proxy=True)

        import time

        start_time = time.time()
        user = client.get_user_by_uid("2656274875")
        elapsed_time = time.time() - start_time

        assert user is not None
        assert user.screen_name == "TestUser"
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

        client = WeiboClient(proxy_api_url=proxy_api_url, use_once_proxy=True)

        import time

        start_time = time.time()
        user = client.get_user_by_uid("2656274875")
        elapsed_time = time.time() - start_time

        assert user is not None
        assert user.screen_name == "TestUser"
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

        client = WeiboClient(proxy_api_url=proxy_api_url, use_once_proxy=False)

        import time

        start_time = time.time()
        user = client.get_user_by_uid("2656274875")
        elapsed_time = time.time() - start_time

        assert user is not None
        assert user.screen_name == "TestUser"
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

        client = WeiboClient()

        import time

        start_time = time.time()
        user = client.get_user_by_uid("2656274875")
        elapsed_time = time.time() - start_time

        assert user is not None
        assert user.screen_name == "TestUser"
        assert elapsed_time >= 4.0


