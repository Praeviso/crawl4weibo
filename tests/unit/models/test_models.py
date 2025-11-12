"""Tests for data models"""

import pytest

from crawl4weibo.models.post import Post
from crawl4weibo.models.user import User


@pytest.mark.unit
class TestUser:
    def test_user_creation(self):
        """Test User creation"""
        user = User(
            id="123456", screen_name="TestUser", followers_count=1000, posts_count=500
        )
        assert user.id == "123456"
        assert user.screen_name == "TestUser"
        assert user.followers_count == 1000
        assert user.posts_count == 500

    def test_user_from_dict(self):
        """Test User creation from dictionary"""
        data = {
            "id": "123456",
            "screen_name": "TestUser",
            "followers_count": 1000,
            "posts_count": 500,
        }
        user = User.from_dict(data)
        assert user.id == "123456"
        assert user.screen_name == "TestUser"
        assert user.followers_count == 1000
        assert user.posts_count == 500

    def test_user_to_dict(self):
        """Test User to dictionary conversion"""
        user = User(
            id="123456", screen_name="TestUser", followers_count=1000, posts_count=500
        )
        user_dict = user.to_dict()
        assert user_dict["id"] == "123456"
        assert user_dict["screen_name"] == "TestUser"
        assert user_dict["followers_count"] == 1000
        assert user_dict["posts_count"] == 500


@pytest.mark.unit
class TestPost:
    def test_post_creation(self):
        """Test Post creation"""
        post = Post(
            id="123",
            bid="ABC123",
            user_id="456",
            text="Test post content",
            attitudes_count=10,
            comments_count=5,
            reposts_count=2,
        )
        assert post.id == "123"
        assert post.bid == "ABC123"
        assert post.user_id == "456"
        assert post.text == "Test post content"
        assert post.attitudes_count == 10
        assert post.comments_count == 5
        assert post.reposts_count == 2

    def test_post_from_dict(self):
        """Test Post creation from dictionary"""
        data = {
            "id": "123",
            "bid": "ABC123",
            "user_id": "456",
            "text": "Test post content",
            "attitudes_count": 10,
            "comments_count": 5,
            "reposts_count": 2,
        }
        post = Post.from_dict(data)
        assert post.id == "123"
        assert post.bid == "ABC123"
        assert post.text == "Test post content"
        assert post.attitudes_count == 10

    def test_post_to_dict(self):
        """Test Post to dictionary conversion"""
        post = Post(
            id="123",
            bid="ABC123",
            user_id="456",
            text="Test post content",
            attitudes_count=10,
            comments_count=5,
            reposts_count=2,
        )
        post_dict = post.to_dict()
        assert post_dict["id"] == "123"
        assert post_dict["text"] == "Test post content"
        assert post_dict["attitudes_count"] == 10
