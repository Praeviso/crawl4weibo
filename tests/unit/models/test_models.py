"""Tests for data models"""

import pytest

from crawl4weibo.models.comment import Comment
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

    def test_user_from_dict_alternative_keys(self):
        """Test User creation from alternative keys"""
        data = {
            "id": "123456",
            "screen_name": "AltUser",
            "follow_count": 12,
            "statuses_count": 34,
            "profile_image_url": "http://avatar.example",
            "cover_image_phone": "http://cover.example",
            "ip_location": "Shanghai",
            "birthday_text": "1995-02-03",
            "education_background": "Test University",
            "company_name": "Test Co",
            "register_time": "2020-01-01",
            "sunshine": "A",
        }
        user = User.from_dict(data)
        assert user.following_count == 12
        assert user.posts_count == 34
        assert user.avatar_url == "http://avatar.example"
        assert user.cover_image_url == "http://cover.example"
        assert user.location == "Shanghai"
        assert user.birthday == "1995-02-03"
        assert user.education == "Test University"
        assert user.company == "Test Co"
        assert user.registration_time == "2020-01-01"
        assert user.sunshine_credit == "A"

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

    def test_post_with_comments_serialization(self):
        """Test Post model with comments serialization"""
        comment = Comment(id="123", text="Test comment", user_screen_name="TestUser")

        post = Post(id="456", bid="ABC", user_id="789", comments=[comment])

        # Test to_dict includes comments
        post_dict = post.to_dict()
        assert "comments" in post_dict
        assert len(post_dict["comments"]) == 1
        assert post_dict["comments"][0]["text"] == "Test comment"

    def test_post_from_dict_with_comments(self):
        """Test Post from_dict preserves comments"""
        post_data = {
            "id": "456",
            "bid": "ABC",
            "user_id": "789",
            "comments": [
                {"id": "123", "text": "Test comment", "user_screen_name": "TestUser"}
            ],
        }
        new_post = Post.from_dict(post_data)
        assert len(new_post.comments) == 1
        assert new_post.comments[0].text == "Test comment"
        assert new_post.comments[0].user_screen_name == "TestUser"

    def test_post_empty_comments_default(self):
        """Test Post has empty comments list by default"""
        post = Post(id="123", bid="ABC", user_id="456")
        assert hasattr(post, "comments")
        assert isinstance(post.comments, list)
        assert len(post.comments) == 0

    def test_post_to_dict_omits_empty_comments(self):
        """Test Post to_dict omits comments field when empty"""
        post = Post(id="123", bid="ABC", user_id="456")
        post_dict = post.to_dict()
        # Empty comments should not be in to_dict output
        assert "comments" not in post_dict
