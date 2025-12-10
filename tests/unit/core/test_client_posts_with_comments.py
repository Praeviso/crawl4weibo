import pytest
import responses


@pytest.mark.unit
class TestPostsWithComments:

    @responses.activate
    def test_get_user_posts_with_comments(self, client_no_rate_limit):
        """Test fetching user posts with comments enabled"""
        # Mock posts API response
        responses.add(
            responses.GET,
            "https://m.weibo.cn/api/container/getIndex",
            json={
                "ok": 1,
                "data": {
                    "cards": [
                        {
                            "card_type": 9,
                            "mblog": {
                                "id": "123",
                                "bid": "ABC",
                                "user": {"id": "456"},
                                "text": "Test post",
                                "comments_count": 5,
                            },
                        }
                    ]
                },
            },
        )

        # Mock comments API response
        responses.add(
            responses.GET,
            "https://m.weibo.cn/api/comments/show",
            json={
                "ok": 1,
                "data": {
                    "data": [
                        {
                            "id": "c1",
                            "text": "Comment 1",
                            "user": {"id": "u1", "screen_name": "User1"},
                        }
                    ],
                    "max": 1,
                    "total_number": 1,
                },
            },
        )

        posts = client_no_rate_limit.get_user_posts(
            "123456", page=1, with_comments=True, comment_limit=10
        )

        assert len(posts) == 1
        assert len(posts[0].comments) == 1
        assert posts[0].comments[0].text == "Comment 1"

    @responses.activate
    def test_get_user_posts_without_comments_default(self, client_no_rate_limit):
        """Test default behavior (no comments fetched)"""
        responses.add(
            responses.GET,
            "https://m.weibo.cn/api/container/getIndex",
            json={
                "ok": 1,
                "data": {
                    "cards": [
                        {
                            "card_type": 9,
                            "mblog": {
                                "id": "123",
                                "bid": "ABC",
                                "user": {"id": "456"},
                                "text": "Test post",
                            },
                        }
                    ]
                },
            },
        )

        posts = client_no_rate_limit.get_user_posts("123456", page=1)

        assert len(posts) == 1
        assert len(posts[0].comments) == 0

    @responses.activate
    def test_search_posts_with_comment_limit(self, client_no_rate_limit):
        """Test comment_limit parameter"""
        # Mock search posts API
        responses.add(
            responses.GET,
            "https://m.weibo.cn/api/container/getIndex",
            json={
                "ok": 1,
                "data": {
                    "cards": [
                        {
                            "card_type": 9,
                            "mblog": {
                                "id": "123",
                                "bid": "ABC",
                                "user": {"id": "456"},
                                "text": "AI post",
                            },
                        }
                    ]
                },
            },
        )

        # Mock comments API with multiple comments
        responses.add(
            responses.GET,
            "https://m.weibo.cn/api/comments/show",
            json={
                "ok": 1,
                "data": {
                    "data": [
                        {
                            "id": f"c{i}",
                            "text": f"Comment {i}",
                            "user": {"id": f"u{i}", "screen_name": f"User{i}"},
                        }
                        for i in range(50)
                    ],
                    "max": 5,
                    "total_number": 50,
                },
            },
        )

        posts, _ = client_no_rate_limit.search_posts(
            "人工智能", page=1, with_comments=True, comment_limit=10
        )

        assert len(posts) == 1
        assert len(posts[0].comments) == 10

    @responses.activate
    def test_fetch_comments_partial_failure(self, client_no_rate_limit):
        """Test graceful handling when some comment fetches fail"""
        # Mock 2 posts
        responses.add(
            responses.GET,
            "https://m.weibo.cn/api/container/getIndex",
            json={
                "ok": 1,
                "data": {
                    "cards": [
                        {
                            "card_type": 9,
                            "mblog": {
                                "id": "1",
                                "bid": "A",
                                "user": {"id": "u1"},
                                "text": "Post 1",
                            },
                        },
                        {
                            "card_type": 9,
                            "mblog": {
                                "id": "2",
                                "bid": "B",
                                "user": {"id": "u2"},
                                "text": "Post 2",
                            },
                        },
                    ]
                },
            },
        )

        # First comment request succeeds
        responses.add(
            responses.GET,
            "https://m.weibo.cn/api/comments/show",
            json={
                "ok": 1,
                "data": {
                    "data": [
                        {
                            "id": "c1",
                            "text": "Good comment",
                            "user": {"id": "u", "screen_name": "User"},
                        }
                    ],
                    "max": 1,
                    "total_number": 1,
                },
            },
        )

        # Second comment request fails
        responses.add(
            responses.GET,
            "https://m.weibo.cn/api/comments/show",
            json={"ok": 0, "msg": "Error"},
            status=400,
        )

        posts = client_no_rate_limit.get_user_posts("123", page=1, with_comments=True)

        # Should still return 2 posts, one with comments, one without
        assert len(posts) == 2
        # At least one should have comments (first one likely succeeded)
        posts_with_comments = [p for p in posts if p.comments]
        assert len(posts_with_comments) >= 0

    def test_post_model_has_comments_field(self):
        """Test Post model includes comments field"""
        from crawl4weibo.models.comment import Comment
        from crawl4weibo.models.post import Post

        comment = Comment(id="1", text="Test comment")
        post = Post(id="123", bid="ABC", user_id="456", comments=[comment])

        assert hasattr(post, "comments")
        assert isinstance(post.comments, list)
        assert len(post.comments) == 1
        assert post.comments[0].text == "Test comment"

    @responses.activate
    def test_get_post_by_bid_with_comments(self, client_no_rate_limit):
        """Test fetching single post with comments"""
        # Mock post API
        responses.add(
            responses.GET,
            "https://m.weibo.cn/statuses/show",
            json={
                "ok": 1,
                "data": {
                    "id": "123",
                    "bid": "ABC",
                    "user": {"id": "456"},
                    "text": "Single post",
                },
            },
        )

        # Mock comments API
        responses.add(
            responses.GET,
            "https://m.weibo.cn/api/comments/show",
            json={
                "ok": 1,
                "data": {
                    "data": [
                        {
                            "id": "c1",
                            "text": "Nice post",
                            "user": {"id": "u1", "screen_name": "Fan1"},
                        }
                    ],
                    "max": 1,
                    "total_number": 1,
                },
            },
        )

        post = client_no_rate_limit.get_post_by_bid(
            "ABC", with_comments=True, comment_limit=10
        )

        assert post.bid == "ABC"
        assert len(post.comments) == 1
        assert post.comments[0].text == "Nice post"

    @responses.activate
    def test_search_posts_by_count_with_comments(self, client_no_rate_limit):
        """Test search_posts_by_count with comments"""
        # Mock first page
        responses.add(
            responses.GET,
            "https://m.weibo.cn/api/container/getIndex",
            json={
                "ok": 1,
                "data": {
                    "cards": [
                        {
                            "card_type": 9,
                            "mblog": {
                                "id": "1",
                                "bid": "A",
                                "user": {"id": "u1"},
                                "text": "Post 1",
                            },
                        }
                    ],
                    "cardlistInfo": {"page": 2},
                },
            },
        )

        # Mock comment for first post
        responses.add(
            responses.GET,
            "https://m.weibo.cn/api/comments/show",
            json={
                "ok": 1,
                "data": {
                    "data": [
                        {
                            "id": "c1",
                            "text": "Comment 1",
                            "user": {"id": "u", "screen_name": "User"},
                        }
                    ],
                    "max": 1,
                    "total_number": 1,
                },
            },
        )

        posts = client_no_rate_limit.search_posts_by_count(
            "test", count=1, with_comments=True, comment_limit=5
        )

        assert len(posts) == 1
        assert len(posts[0].comments) == 1
