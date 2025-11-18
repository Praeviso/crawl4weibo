"""Tests for WeiboClient comment scraping functionality"""

import pytest
import responses

from crawl4weibo import WeiboClient
from crawl4weibo.models.comment import Comment


@pytest.mark.unit
class TestWeiboClientComments:
    def test_client_has_comment_methods(self):
        """Test that comment methods exist"""
        client = WeiboClient()
        assert hasattr(client, "get_comments")
        assert hasattr(client, "get_all_comments")
        assert callable(getattr(client, "get_comments"))
        assert callable(getattr(client, "get_all_comments"))

    @responses.activate
    def test_get_comments_single_page(self):
        """Test getting comments for a single page"""
        weibo_api_url = "https://m.weibo.cn/api/comments/show"

        # Mock API response with sample comment data
        responses.add(
            responses.GET,
            weibo_api_url,
            json={
                "ok": 1,
                "msg": "数据获取成功",
                "data": {
                    "data": [
                        {
                            "id": 5180492392696133,
                            "created_at": "06-23",
                            "source": "来自上海",
                            "user": {
                                "id": 1843842531,
                                "screen_name": "童童-__-",
                                "profile_image_url": "https://example.com/avatar.jpg",
                                "followers_count": "637",
                                "followers_count_str": "637",
                                "verified": False,
                                "verified_type": -1,
                            },
                            "text": "回复@妖怪档案馆:在哪里买呀 没看到链接",
                            "reply_id": 4897275770308603,
                            "reply_text": "回复@潘帕斯的非典型射手:哇！！！！开心！",
                            "like_counts": 0,
                            "liked": False,
                        },
                        {
                            "id": 5178102621670790,
                            "created_at": "06-16",
                            "source": "来自广东",
                            "user": {
                                "id": 7550644732,
                                "screen_name": "佳娴骐仕",
                                "profile_image_url": "https://example.com/avatar2.jpg",
                                "followers_count": "1",
                                "followers_count_str": "1",
                                "verified": False,
                                "verified_type": -1,
                            },
                            "text": "宝藏博主啊[太开心]想看各诸神仙的，有没集合呀",
                            "like_counts": 0,
                            "liked": False,
                        },
                    ],
                    "total_number": 235,
                    "max": 24,
                },
            },
            status=200,
        )

        client = WeiboClient()
        comments, pagination = client.get_comments("4876256422135140", page=1)

        assert len(comments) == 2
        assert pagination["total_number"] == 235
        assert pagination["max"] == 24

        # Check first comment
        assert isinstance(comments[0], Comment)
        assert comments[0].id == "5180492392696133"
        assert comments[0].user_screen_name == "童童-__-"
        assert "在哪里买呀" in comments[0].text
        assert comments[0].reply_id == "4897275770308603"
        assert comments[0].like_counts == 0

        # Check second comment
        assert comments[1].id == "5178102621670790"
        assert comments[1].user_screen_name == "佳娴骐仕"
        assert "宝藏博主" in comments[1].text

    @responses.activate
    def test_get_comments_with_image(self):
        """Test getting comment with image attachment"""
        weibo_api_url = "https://m.weibo.cn/api/comments/show"

        responses.add(
            responses.GET,
            weibo_api_url,
            json={
                "ok": 1,
                "data": {
                    "data": [
                        {
                            "id": 5074131670537286,
                            "created_at": "2024-09-02",
                            "source": "来自湖北",
                            "user": {
                                "id": 5643908670,
                                "screen_name": "妖怪档案馆",
                                "profile_image_url": "https://example.com/avatar.jpg",
                                "followers_count_str": "32.6万",
                                "verified": True,
                                "verified_type": 0,
                            },
                            "text": "回复@刘冬子:是这一篇？",
                            "pic": {
                                "pid": "0069Xgt0gy1ht99333vm0j30cn7psqkk",
                                "url": "https://example.com/pic.jpg",
                            },
                            "like_counts": 0,
                            "liked": False,
                        }
                    ],
                    "total_number": 1,
                    "max": 1,
                },
            },
            status=200,
        )

        client = WeiboClient()
        comments, pagination = client.get_comments("123456")

        assert len(comments) == 1
        assert comments[0].pic_url == "https://example.com/pic.jpg"
        assert comments[0].user_verified is True

    @responses.activate
    def test_get_comments_empty_response(self):
        """Test getting comments when no comments exist"""
        weibo_api_url = "https://m.weibo.cn/api/comments/show"

        responses.add(
            responses.GET,
            weibo_api_url,
            json={"ok": 1, "data": {"data": [], "total_number": 0, "max": 0}},
            status=200,
        )

        client = WeiboClient()
        comments, pagination = client.get_comments("123456")

        assert len(comments) == 0
        assert pagination["total_number"] == 0
        assert pagination["max"] == 0

    @responses.activate
    def test_get_all_comments_multiple_pages(self):
        """Test getting all comments with pagination"""
        weibo_api_url = "https://m.weibo.cn/api/comments/show"

        # Mock page 1
        responses.add(
            responses.GET,
            weibo_api_url,
            json={
                "ok": 1,
                "data": {
                    "data": [
                        {
                            "id": 1,
                            "text": "Comment 1",
                            "created_at": "2024-01-01",
                            "source": "iPhone",
                            "user": {
                                "id": 123,
                                "screen_name": "User1",
                                "profile_image_url": "avatar1.jpg",
                                "followers_count_str": "100",
                                "verified": False,
                                "verified_type": -1,
                            },
                            "like_counts": 0,
                            "liked": False,
                        }
                    ],
                    "total_number": 2,
                    "max": 2,
                },
            },
            status=200,
        )

        # Mock page 2
        responses.add(
            responses.GET,
            weibo_api_url,
            json={
                "ok": 1,
                "data": {
                    "data": [
                        {
                            "id": 2,
                            "text": "Comment 2",
                            "created_at": "2024-01-02",
                            "source": "Android",
                            "user": {
                                "id": 456,
                                "screen_name": "User2",
                                "profile_image_url": "avatar2.jpg",
                                "followers_count_str": "200",
                                "verified": False,
                                "verified_type": -1,
                            },
                            "like_counts": 5,
                            "liked": True,
                        }
                    ],
                    "total_number": 2,
                    "max": 2,
                },
            },
            status=200,
        )

        client = WeiboClient()
        all_comments = client.get_all_comments("123456")

        assert len(all_comments) == 2
        assert all_comments[0].text == "Comment 1"
        assert all_comments[1].text == "Comment 2"
        assert all_comments[1].like_counts == 5
        assert all_comments[1].liked is True

    @responses.activate
    def test_get_all_comments_with_max_pages(self):
        """Test getting comments with max_pages limit"""
        weibo_api_url = "https://m.weibo.cn/api/comments/show"

        # Mock session initialization
        responses.add(
            responses.GET, "https://m.weibo.cn/", body="", status=200
        )

        # Mock page 1
        responses.add(
            responses.GET,
            weibo_api_url,
            json={
                "ok": 1,
                "data": {
                    "data": [
                        {
                            "id": 1,
                            "text": "Comment 1",
                            "created_at": "2024-01-01",
                            "source": "iPhone",
                            "user": {
                                "id": 123,
                                "screen_name": "User1",
                                "profile_image_url": "avatar1.jpg",
                                "followers_count_str": "100",
                                "verified": False,
                                "verified_type": -1,
                            },
                            "like_counts": 0,
                            "liked": False,
                        }
                    ],
                    "total_number": 100,
                    "max": 10,
                },
            },
            status=200,
        )

        client = WeiboClient()
        all_comments = client.get_all_comments("123456", max_pages=1)

        # Should only fetch 1 page even though max=10
        assert len(all_comments) == 1
        # Should have 2 API calls: 1 for session init, 1 for comments
        assert len([c for c in responses.calls if "comments" in c.request.url]) == 1

    @responses.activate
    def test_comment_model_to_dict(self):
        """Test Comment model to_dict method"""
        weibo_api_url = "https://m.weibo.cn/api/comments/show"

        responses.add(
            responses.GET,
            weibo_api_url,
            json={
                "ok": 1,
                "data": {
                    "data": [
                        {
                            "id": 123456,
                            "text": "Test comment",
                            "created_at": "2024-01-01",
                            "source": "iPhone",
                            "user": {
                                "id": 789,
                                "screen_name": "TestUser",
                                "profile_image_url": "avatar.jpg",
                                "followers_count_str": "500",
                                "verified": True,
                                "verified_type": 0,
                            },
                            "like_counts": 10,
                            "liked": True,
                            "reply_id": 999,
                            "reply_text": "Original comment",
                        }
                    ],
                    "total_number": 1,
                    "max": 1,
                },
            },
            status=200,
        )

        client = WeiboClient()
        comments, _ = client.get_comments("123456")

        comment_dict = comments[0].to_dict()
        assert comment_dict["id"] == "123456"
        assert comment_dict["text"] == "Test comment"
        assert comment_dict["user_id"] == "789"
        assert comment_dict["user_screen_name"] == "TestUser"
        assert comment_dict["like_counts"] == 10
        assert comment_dict["liked"] is True
        assert comment_dict["reply_id"] == "999"
        assert comment_dict["reply_text"] == "Original comment"
