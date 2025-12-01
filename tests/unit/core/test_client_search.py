"""Tests for WeiboClient search functionality"""

from unittest.mock import patch

import pytest
import responses

from crawl4weibo import Post, WeiboClient
from crawl4weibo.utils.proxy import ProxyPoolConfig
from crawl4weibo.utils.rate_limit import RateLimitConfig


@pytest.mark.unit
class TestSearchPosts:
    """Test search_posts method with pagination info"""

    @responses.activate
    def test_search_posts_returns_pagination_info(self):
        """Test that search_posts returns pagination info"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"

        mock_data = {
            "ok": 1,
            "data": {
                "cards": [
                    {
                        "card_type": 9,
                        "mblog": {
                            "id": "5000000001",
                            "bid": "MnHwC1",
                            "text": "Test post",
                            "created_at": "Tue Jan 01 12:00:00 +0800 2024",
                            "user": {"id": 123456},
                            "reposts_count": 10,
                            "comments_count": 5,
                            "attitudes_count": 20,
                        },
                    }
                ],
                "cardlistInfo": {"page": 2},
            },
        }

        responses.add(
            responses.GET,
            weibo_api_url,
            json=mock_data,
            status=200,
        )

        client = WeiboClient()
        posts, pagination = client.search_posts("Python", page=1)

        assert len(posts) == 1
        assert isinstance(posts[0], Post)
        assert pagination["page"] == 2
        assert pagination["has_more"] is True

    @responses.activate
    def test_search_posts_last_page_detection(self):
        """Test that last page is detected when cardlistInfo.page is None"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"

        mock_data = {
            "ok": 1,
            "data": {
                "cards": [
                    {
                        "card_type": 9,
                        "mblog": {
                            "id": "5000000001",
                            "bid": "MnHwC1",
                            "text": "Test post",
                            "created_at": "Tue Jan 01 12:00:00 +0800 2024",
                            "user": {"id": 123456},
                            "reposts_count": 10,
                            "comments_count": 5,
                            "attitudes_count": 20,
                        },
                    }
                ],
                "cardlistInfo": {"page": None},
            },
        }

        responses.add(
            responses.GET,
            weibo_api_url,
            json=mock_data,
            status=200,
        )

        client = WeiboClient()
        posts, pagination = client.search_posts("Python", page=1)

        assert len(posts) == 1
        assert pagination["page"] is None
        assert pagination["has_more"] is False


@pytest.mark.unit
class TestSearchPostsByCount:
    """Test search_posts_by_count method"""

    @responses.activate
    def test_search_posts_by_count_exact_count(self, client_no_rate_limit):
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
                ],
                "cardlistInfo": {"page": 2},
            },
        }

        responses.add(
            responses.GET,
            weibo_api_url,
            json=mock_post_data,
            status=200,
        )

        posts = client_no_rate_limit.search_posts_by_count("Python", count=25)

        # Should fetch 3 pages to get 25 posts (10+10+5)
        assert len(posts) == 25
        assert all(isinstance(post, Post) for post in posts)

    @responses.activate
    def test_search_posts_by_count_stops_at_last_page(self, client_no_rate_limit):
        """Test that search stops when cardlistInfo.page is None"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"

        # Mock first page
        mock_page1 = {
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
                ],
                "cardlistInfo": {"page": 2},
            },
        }

        # Mock second page (last page)
        mock_page2 = {
            "ok": 1,
            "data": {
                "cards": [
                    {
                        "card_type": 9,
                        "mblog": {
                            "id": f"500000001{i}",
                            "bid": f"MnHwD{i}",
                            "text": f"Test post page 2 {i}",
                            "created_at": "Tue Jan 01 12:00:00 +0800 2024",
                            "user": {"id": 123456},
                            "reposts_count": 10,
                            "comments_count": 5,
                            "attitudes_count": 20,
                        },
                    }
                    for i in range(5)
                ],
                "cardlistInfo": {"page": None},  # Last page
            },
        }

        responses.add(responses.GET, weibo_api_url, json=mock_page1, status=200)
        responses.add(responses.GET, weibo_api_url, json=mock_page2, status=200)

        client = WeiboClient()
        posts = client_no_rate_limit.search_posts_by_count("Python", count=100)

        # Should stop at page 2 (15 posts total)
        assert len(posts) == 15
        assert all(isinstance(post, Post) for post in posts)

    @responses.activate
    def test_search_posts_by_count_less_than_available(self, client_no_rate_limit):
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
                ],
                "cardlistInfo": {"page": 2},
            },
        }

        # Mock second page with no posts
        mock_post_data_page2 = {"ok": 1, "data": {"cards": [], "cardlistInfo": {}}}

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

        posts = client_no_rate_limit.search_posts_by_count("Python", count=20)

        # Should return only 5 posts (all available)
        assert len(posts) == 5
        assert all(isinstance(post, Post) for post in posts)

    @responses.activate
    def test_search_posts_by_count_respects_max_pages(self, client_no_rate_limit):
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
                ],
                "cardlistInfo": {"page": 2},
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

        posts = client_no_rate_limit.search_posts_by_count(
            "Python", count=100, max_pages=3
        )

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
                ],
                "cardlistInfo": {"page": None},
            },
        }

        responses.add(
            responses.GET,
            weibo_api_url,
            json=mock_post_data,
            status=200,
        )

        with patch("crawl4weibo.core.client.CookieFetcher"):
            proxy_config = ProxyPoolConfig(proxy_api_url=proxy_api_url)
            rate_config = RateLimitConfig(disable_delay=True)
            client = WeiboClient(
                proxy_config=proxy_config,
                rate_limit_config=rate_config,
                auto_fetch_cookies=False,
            )

            with patch.object(
                client.proxy_pool, "get_proxy", wraps=client.proxy_pool.get_proxy
            ) as mock_get_proxy:
                posts = client.search_posts_by_count("Python", count=1)
                mock_get_proxy.assert_called()

        assert len(posts) == 1


@pytest.mark.unit
class TestSearchAllPosts:
    """Test search_all_posts method"""

    @responses.activate
    def test_search_all_posts_fetches_until_last_page(self, client_no_rate_limit):
        """Test that search_all_posts fetches all posts until page is None"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"

        # Mock 3 pages of data
        for page_num in range(1, 4):
            is_last_page = page_num == 3
            mock_data = {
                "ok": 1,
                "data": {
                    "cards": [
                        {
                            "card_type": 9,
                            "mblog": {
                                "id": f"50000000{page_num}{i}",
                                "bid": f"MnHwC{page_num}{i}",
                                "text": f"Test post page {page_num} item {i}",
                                "created_at": "Tue Jan 01 12:00:00 +0800 2024",
                                "user": {"id": 123456},
                                "reposts_count": 10,
                                "comments_count": 5,
                                "attitudes_count": 20,
                            },
                        }
                        for i in range(10)
                    ],
                    "cardlistInfo": {"page": None if is_last_page else page_num + 1},
                },
            }
            responses.add(responses.GET, weibo_api_url, json=mock_data, status=200)

        client = WeiboClient()
        posts = client_no_rate_limit.search_all_posts("Python")

        # Should fetch all 30 posts from 3 pages
        assert len(posts) == 30
        assert all(isinstance(post, Post) for post in posts)

    @responses.activate
    def test_search_all_posts_respects_max_pages(self, client_no_rate_limit):
        """Test that search_all_posts respects max_pages limit"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"

        mock_data = {
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
                ],
                "cardlistInfo": {"page": 2},
            },
        }

        # Add more responses than max_pages
        for _ in range(10):
            responses.add(responses.GET, weibo_api_url, json=mock_data, status=200)

        client = WeiboClient()
        posts = client_no_rate_limit.search_all_posts("Python", max_pages=2)

        # Should fetch only 2 pages = 20 posts
        assert len(posts) == 20
        assert all(isinstance(post, Post) for post in posts)

    @responses.activate
    def test_search_all_posts_handles_empty_results(self, client_no_rate_limit):
        """Test that search_all_posts handles empty results gracefully"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"

        mock_data = {"ok": 1, "data": {"cards": [], "cardlistInfo": {}}}

        responses.add(responses.GET, weibo_api_url, json=mock_data, status=200)

        client = WeiboClient()
        posts = client_no_rate_limit.search_all_posts("NonExistentTopic")

        assert len(posts) == 0

