"""Tests for WeiboClient search functionality"""

from unittest.mock import patch

import pytest
import responses

from crawl4weibo import Post, WeiboClient


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
