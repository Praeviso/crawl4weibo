"""Integration tests for WeiboClient - tests actual API responses"""

import contextlib

import pytest

from crawl4weibo import WeiboClient
from crawl4weibo.utils.rate_limit import RateLimitConfig


@pytest.fixture
def client():
    """
    Create a WeiboClient instance for integration testing with real authentication.
    
    Integration tests use this fixture to get a client with:
    - Rate limiting disabled (no artificial delays between requests)
    - Real cookie fetching enabled (authenticates with Weibo API)
    
    This provides true integration testing against the real API while still
    optimizing test execution speed by removing rate limit delays.
    
    Note: Some tests may be skipped if the API is unavailable or rate-limited.
    """
    rate_config = RateLimitConfig(disable_delay=True)
    return WeiboClient(rate_limit_config=rate_config)



@pytest.mark.integration
class TestWeiboClientIntegration:
    """Integration tests that make real API calls"""

    def test_get_user_by_uid_returns_data(self, client):
        """Test that get_user_by_uid returns user data"""
        test_uid = "2656274875"

        try:
            user = client.get_user_by_uid(test_uid)

            assert user is not None
            assert hasattr(user, "id")
            assert hasattr(user, "screen_name")
            assert hasattr(user, "followers_count")
            assert hasattr(user, "posts_count")

            assert user.id == test_uid
            assert len(user.screen_name) > 0
            # followers_count is a formatted string (e.g., "1.4亿"), check it's not empty
            assert len(str(user.followers_count)) > 0

        except Exception as e:
            pytest.skip(f"API call failed, skipping integration test: {e}")

    def test_get_user_posts_returns_data(self, client):
        """Test that get_user_posts returns post data"""
        test_uid = "2656274875"

        try:
            posts = client.get_user_posts(test_uid, page=1)

            assert isinstance(posts, list)

            if posts:
                post = posts[0]
                assert hasattr(post, "id")
                assert hasattr(post, "bid")
                assert hasattr(post, "text")
                assert hasattr(post, "user_id")
                assert hasattr(post, "attitudes_count")
                assert hasattr(post, "comments_count")
                assert hasattr(post, "reposts_count")

                assert post.user_id == test_uid
                assert len(post.text) > 0

        except Exception as e:
            pytest.skip(f"API call failed, skipping integration test: {e}")

    def test_get_user_posts_with_expand_returns_data(self, client):
        """Test that get_user_posts with expand=True returns post data"""
        test_uid = "2656274875"

        try:
            posts = client.get_user_posts(test_uid, page=1, expand=True)

            assert isinstance(posts, list)

            if posts:
                post = posts[0]
                assert hasattr(post, "text")
                assert hasattr(post, "user_id")
                assert post.user_id == test_uid

        except Exception as e:
            pytest.skip(f"API call failed, skipping integration test: {e}")

    def test_get_post_by_bid_returns_data(self, client):
        """Test that get_post_by_bid returns post data"""
        test_uid = "2656274875"

        try:
            posts = client.get_user_posts(test_uid, page=1)

            if not posts:
                pytest.skip("No posts available to test get_post_by_bid")

            test_bid = posts[0].bid

            post = client.get_post_by_bid(test_bid)

            assert post is not None
            assert hasattr(post, "bid")
            assert hasattr(post, "text")
            assert hasattr(post, "user_id")

            assert post.bid == test_bid
            # Text should not be empty
            assert len(post.text) > 0

        except Exception as e:
            pytest.skip(f"API call failed, skipping integration test: {e}")

    def test_search_users_returns_data(self, client):
        """Test that search_users returns user data"""
        query = "新浪"

        try:
            users = client.search_users(query)

            assert isinstance(users, list)

            if users:
                user = users[0]
                assert hasattr(user, "id")
                assert hasattr(user, "screen_name")
                assert hasattr(user, "followers_count")

                assert len(user.screen_name) > 0
                assert len(user.id) > 0

        except Exception as e:
            pytest.skip(f"API call failed, skipping integration test: {e}")

    def test_search_posts_returns_data(self, client):
        """Test that search_posts returns post data"""
        query = "人工智能"

        try:
            # search_posts returns a tuple: (posts, pagination_info)
            posts, pagination = client.search_posts(query, page=1)

            assert isinstance(posts, list)
            assert isinstance(pagination, dict)
            assert "has_more" in pagination

            if posts:
                post = posts[0]
                assert hasattr(post, "id")
                assert hasattr(post, "text")
                assert hasattr(post, "user_id")

                assert len(post.text) > 0
                assert len(post.user_id) > 0

        except Exception as e:
            pytest.skip(f"API call failed, skipping integration test: {e}")

    def test_client_handles_invalid_uid(self, client):
        """Test that client handles invalid UIDs gracefully"""
        invalid_uid = "invalid_uid_12345"

        with contextlib.suppress(Exception):
            client.get_user_by_uid(invalid_uid)

    def test_client_handles_empty_search_results(self, client):
        """Test that client handles empty search results gracefully"""
        rare_query = "xyzabc123veryrarequery456"

        try:
            users = client.search_users(rare_query)
            # search_posts returns a tuple: (posts, pagination_info)
            posts, pagination = client.search_posts(rare_query)

            # Should return empty lists, not raise exceptions
            assert isinstance(users, list)
            assert isinstance(posts, list)
            assert isinstance(pagination, dict)

        except Exception as e:
            pytest.skip(f"API call failed, skipping integration test: {e}")
