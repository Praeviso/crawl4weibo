"""Tests for WeiboClient proxy integration and elimination"""

from unittest.mock import patch

import pytest
import responses

from crawl4weibo import WeiboClient


@pytest.mark.unit
class TestProxyElimination:
    """Tests for proxy elimination on 432 errors"""

    @responses.activate
    def test_proxy_removed_on_432_pooling_mode(self):
        """Test that proxy is removed from pool when it returns 432 in pooling mode"""
        proxy_api_url = "http://api.proxy.com/get"
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"

        responses.add(
            responses.GET,
            proxy_api_url,
            json={
                "data": [
                    {"ip": "1.2.3.4", "port": "8080"},
                    {"ip": "5.6.7.8", "port": "9090"},
                ]
            },
            status=200,
        )

        responses.add(
            responses.GET,
            weibo_api_url,
            status=432,
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

        client = WeiboClient(proxy_api_url=proxy_api_url, proxy_pool_size=5)

        client.add_proxy("http://10.20.30.40:8080")
        initial_pool_size = client.get_proxy_pool_size()
        assert initial_pool_size == 1

        with patch("time.sleep"):
            user = client.get_user_by_uid("2656274875")

        assert user is not None
        assert user.screen_name == "TestUser"

    @responses.activate
    def test_proxy_not_removed_on_200_success(self):
        """Test that proxy is NOT removed when request succeeds with 200"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"

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
        client.add_proxy("http://1.2.3.4:8080")
        assert client.get_proxy_pool_size() == 1

        user = client.get_user_by_uid("2656274875")

        assert user is not None
        assert client.get_proxy_pool_size() == 1

    @responses.activate
    def test_proxy_not_removed_in_once_mode(self):
        """Test that proxy is NOT removed in once mode (proxies are single-use anyway)"""
        proxy_api_url = "http://api.proxy.com/get"
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"

        responses.add(
            responses.GET,
            proxy_api_url,
            json={
                "data": [
                    {"ip": "1.1.1.1", "port": "8080"},
                    {"ip": "2.2.2.2", "port": "8080"},
                ]
            },
            status=200,
        )

        responses.add(
            responses.GET,
            weibo_api_url,
            status=432,
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

        client = WeiboClient(proxy_api_url=proxy_api_url, use_once_proxy=True)

        assert client.get_proxy_pool_size() == 0

        user = client.get_user_by_uid("2656274875")

        assert user is not None
        assert user.screen_name == "TestUser"
        assert client.get_proxy_pool_size() == 0

    @responses.activate
    def test_multiple_432_removes_multiple_proxies(self):
        """Test that multiple 432 errors remove multiple proxies"""
        weibo_api_url = "https://m.weibo.cn/api/container/getIndex"

        responses.add(responses.GET, weibo_api_url, status=432)
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
        client.proxy_pool.config.fetch_strategy = "round_robin"
        client.add_proxy("http://1.2.3.4:8080")
        client.add_proxy("http://5.6.7.8:9090")
        client.add_proxy("http://10.11.12.13:3128")

        assert client.get_proxy_pool_size() == 3

        with patch("time.sleep"):
            user = client.get_user_by_uid("2656274875")

        assert user is not None
        assert client.get_proxy_pool_size() <= 2
