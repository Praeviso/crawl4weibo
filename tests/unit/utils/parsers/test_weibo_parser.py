"""Tests for WeiboParser comment parsing with exception handling"""

import pytest

from crawl4weibo.exceptions.base import ParseError
from crawl4weibo.utils.parser import WeiboParser


@pytest.mark.unit
class TestWeiboParserComments:
    """Test suite for parse_comments and _parse_single_comment methods"""

    def setup_method(self):
        """Initialize parser before each test"""
        self.parser = WeiboParser()

    # ========== parse_comments Tests ==========

    def test_parse_comments_success(self):
        """Test successful parsing of comments"""
        response_data = {
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
                            "followers_count_str": "100",
                            "verified": False,
                            "verified_type": -1,
                        },
                        "like_counts": 5,
                        "liked": False,
                    }
                ],
                "total_number": 1,
                "max": 1,
            }
        }

        comments, pagination = self.parser.parse_comments(response_data)

        assert len(comments) == 1
        assert comments[0]["id"] == "123456"
        assert comments[0]["text"] == "Test comment"
        assert pagination["total_number"] == 1
        assert pagination["max"] == 1

    def test_parse_comments_missing_data_key(self):
        """Test parsing when 'data' key is missing - should return empty list"""
        response_data = {"ok": 1, "msg": "success"}

        comments, pagination = self.parser.parse_comments(response_data)

        assert comments == []
        assert pagination == {}

    def test_parse_comments_empty_data(self):
        """Test parsing when data object exists but is empty"""
        response_data = {"data": {}}

        comments, pagination = self.parser.parse_comments(response_data)

        assert comments == []
        assert pagination["total_number"] == 0
        assert pagination["max"] == 0

    def test_parse_comments_empty_comment_list(self):
        """Test parsing when comment list is empty"""
        response_data = {"data": {"data": [], "total_number": 0, "max": 0}}

        comments, pagination = self.parser.parse_comments(response_data)

        assert len(comments) == 0
        assert pagination["total_number"] == 0
        assert pagination["max"] == 0

    def test_parse_comments_data_not_list(self):
        """Test parsing when 'data.data' is not a list - gracefully handles by skipping invalid items"""
        response_data = {"data": {"data": "not_a_list", "total_number": 0, "max": 0}}

        # Should not raise, but will log errors and return empty list
        # (each character in string gets passed to _parse_single_comment and fails gracefully)
        comments, pagination = self.parser.parse_comments(response_data)

        # All comments fail to parse, so we get empty list
        assert comments == []
        assert pagination["total_number"] == 0

    def test_parse_comments_malformed_pagination(self):
        """Test parsing with malformed pagination data"""
        response_data = {
            "data": {
                "data": [
                    {
                        "id": 123,
                        "text": "Test",
                        "created_at": "2024-01-01",
                        "source": "",
                        "user": {
                            "id": 1,
                            "screen_name": "User",
                            "profile_image_url": "",
                            "followers_count_str": "0",
                            "verified": False,
                            "verified_type": -1,
                        },
                        "like_counts": 0,
                        "liked": False,
                    }
                ],
                "total_number": "invalid",  # Invalid type
                "max": None,  # Invalid type
            }
        }

        comments, pagination = self.parser.parse_comments(response_data)

        # Should handle gracefully with defaults
        assert len(comments) == 1
        assert pagination["total_number"] == "invalid"  # Returns as-is
        assert pagination["max"] is None  # Returns as-is

    def test_parse_comments_mixed_valid_invalid_comments(self):
        """Test parsing when some comments are valid and some fail"""
        response_data = {
            "data": {
                "data": [
                    {
                        "id": 123,
                        "text": "Valid comment",
                        "created_at": "2024-01-01",
                        "source": "iPhone",
                        "user": {
                            "id": 1,
                            "screen_name": "User1",
                            "profile_image_url": "avatar.jpg",
                            "followers_count_str": "100",
                            "verified": False,
                            "verified_type": -1,
                        },
                        "like_counts": 0,
                        "liked": False,
                    },
                    None,  # Invalid comment
                    {
                        "id": 456,
                        "text": "Another valid comment",
                        "created_at": "2024-01-02",
                        "source": "Android",
                        "user": {
                            "id": 2,
                            "screen_name": "User2",
                            "profile_image_url": "avatar2.jpg",
                            "followers_count_str": "200",
                            "verified": True,
                            "verified_type": 0,
                        },
                        "like_counts": 5,
                        "liked": True,
                    },
                ],
                "total_number": 3,
                "max": 3,
            }
        }

        comments, pagination = self.parser.parse_comments(response_data)

        # Should skip None comment and return only valid ones
        assert len(comments) == 2
        assert comments[0]["id"] == "123"
        assert comments[1]["id"] == "456"
        assert pagination["total_number"] == 3

    def test_parse_comments_exception_in_iteration(self):
        """Test when exception occurs during comment list iteration"""
        # Create a mock object that raises exception when iterated
        class FailingIterable:
            def __iter__(self):
                raise ValueError("Simulated iteration error")

        response_data = {
            "data": {
                "data": FailingIterable(),
                "total_number": 0,
                "max": 0,
            }
        }

        with pytest.raises(ParseError) as exc_info:
            self.parser.parse_comments(response_data)

        assert "Failed to parse comments" in str(exc_info.value)
        assert "Simulated iteration error" in str(exc_info.value)

    def test_parse_comments_none_input(self):
        """Test parsing with None as input"""
        with pytest.raises(ParseError) as exc_info:
            self.parser.parse_comments(None)

        assert "Failed to parse comments" in str(exc_info.value)

    def test_parse_comments_missing_nested_data_key(self):
        """Test when 'data.data' key is missing"""
        response_data = {"data": {"total_number": 10, "max": 1}}

        comments, pagination = self.parser.parse_comments(response_data)

        # Should return empty list when comment data is missing
        assert comments == []
        assert pagination["total_number"] == 10
        assert pagination["max"] == 1

    # ========== _parse_single_comment Tests ==========

    def test_parse_single_comment_success(self):
        """Test successful parsing of a single comment"""
        comment_data = {
            "id": 123456789,
            "text": "Test comment text",
            "created_at": "2024-01-01",
            "source": "iPhone 13",
            "user": {
                "id": 987654321,
                "screen_name": "TestUser",
                "profile_image_url": "https://example.com/avatar.jpg",
                "verified": True,
                "verified_type": 0,
                "followers_count_str": "10万",
            },
            "like_counts": 100,
            "liked": True,
            "reply_id": 555555,
            "reply_text": "Original comment",
            "pic": {"pid": "abc123", "url": "https://example.com/pic.jpg"},
        }

        result = self.parser._parse_single_comment(comment_data)

        assert result is not None
        assert result["id"] == "123456789"
        assert result["text"] == "Test comment text"
        assert result["user_id"] == "987654321"
        assert result["user_screen_name"] == "TestUser"
        assert result["user_verified"] is True
        assert result["like_counts"] == 100
        assert result["liked"] is True
        assert result["reply_id"] == "555555"
        assert result["reply_text"] == "Original comment"
        assert result["pic_url"] == "https://example.com/pic.jpg"

    def test_parse_single_comment_minimal_data(self):
        """Test parsing comment with minimal required data"""
        comment_data = {}

        result = self.parser._parse_single_comment(comment_data)

        # Should still return a comment with default values
        assert result is not None
        assert result["id"] == ""
        assert result["text"] == ""
        assert result["user_id"] == ""
        assert result["user_screen_name"] == ""
        assert result["user_verified"] is False
        assert result["like_counts"] == 0
        assert result["liked"] is False
        assert result["reply_id"] is None
        assert result["reply_text"] is None
        assert result["pic_url"] == ""

    def test_parse_single_comment_missing_user(self):
        """Test parsing comment with missing user data"""
        comment_data = {
            "id": 123,
            "text": "Comment without user",
            "created_at": "2024-01-01",
            "source": "Web",
            "like_counts": 0,
            "liked": False,
        }

        result = self.parser._parse_single_comment(comment_data)

        assert result is not None
        assert result["id"] == "123"
        assert result["user_id"] == ""
        assert result["user_screen_name"] == ""
        assert result["user_verified"] is False

    def test_parse_single_comment_missing_pic(self):
        """Test parsing comment with missing pic data"""
        comment_data = {
            "id": 123,
            "text": "Comment without pic",
            "created_at": "2024-01-01",
            "source": "iPhone",
            "user": {"id": 1, "screen_name": "User"},
            "like_counts": 0,
            "liked": False,
        }

        result = self.parser._parse_single_comment(comment_data)

        assert result is not None
        assert result["pic_url"] == ""

    def test_parse_single_comment_empty_pic_object(self):
        """Test parsing comment with empty pic object"""
        comment_data = {
            "id": 123,
            "text": "Comment with empty pic",
            "created_at": "2024-01-01",
            "source": "iPhone",
            "user": {"id": 1, "screen_name": "User"},
            "pic": {},
            "like_counts": 0,
            "liked": False,
        }

        result = self.parser._parse_single_comment(comment_data)

        assert result is not None
        assert result["pic_url"] == ""

    def test_parse_single_comment_none_pic(self):
        """Test parsing comment with None pic"""
        comment_data = {
            "id": 123,
            "text": "Comment with None pic",
            "created_at": "2024-01-01",
            "source": "iPhone",
            "user": {"id": 1, "screen_name": "User"},
            "pic": None,
            "like_counts": 0,
            "liked": False,
        }

        result = self.parser._parse_single_comment(comment_data)

        assert result is not None
        assert result["pic_url"] == ""

    def test_parse_single_comment_none_reply_id(self):
        """Test parsing comment with None or 0 reply_id"""
        # Test with None
        comment_data = {
            "id": 123,
            "text": "No reply",
            "created_at": "2024-01-01",
            "source": "iPhone",
            "user": {"id": 1, "screen_name": "User"},
            "reply_id": None,
            "like_counts": 0,
            "liked": False,
        }

        result = self.parser._parse_single_comment(comment_data)
        assert result["reply_id"] is None

        # Test with 0
        comment_data["reply_id"] = 0
        result = self.parser._parse_single_comment(comment_data)
        assert result["reply_id"] is None

        # Test with valid reply_id
        comment_data["reply_id"] = 999
        result = self.parser._parse_single_comment(comment_data)
        assert result["reply_id"] == "999"

    def test_parse_single_comment_html_in_text(self):
        """Test parsing comment with HTML tags in text"""
        comment_data = {
            "id": 123,
            "text": "<a href='#'>Test</a> with <b>HTML</b> tags",
            "created_at": "2024-01-01",
            "source": "iPhone",
            "user": {"id": 1, "screen_name": "User"},
            "like_counts": 0,
            "liked": False,
        }

        result = self.parser._parse_single_comment(comment_data)

        # Text should be cleaned (HTML tags removed)
        assert result is not None
        assert "<a" not in result["text"]
        assert "<b>" not in result["text"]
        assert "Test with HTML tags" == result["text"]

    def test_parse_single_comment_whitespace_in_text(self):
        """Test parsing comment with excessive whitespace"""
        comment_data = {
            "id": 123,
            "text": "Comment   with    multiple   spaces\n\nand\n\nnewlines",
            "created_at": "2024-01-01",
            "source": "iPhone",
            "user": {"id": 1, "screen_name": "User"},
            "like_counts": 0,
            "liked": False,
        }

        result = self.parser._parse_single_comment(comment_data)

        # Whitespace should be normalized
        assert result is not None
        assert result["text"] == "Comment with multiple spaces and newlines"

    def test_parse_single_comment_wrong_type_id(self):
        """Test parsing comment with non-standard ID types"""
        comment_data = {
            "id": "string_id_123",  # String instead of int
            "text": "Test",
            "created_at": "2024-01-01",
            "source": "iPhone",
            "user": {"id": "user_456", "screen_name": "User"},
            "like_counts": 0,
            "liked": False,
        }

        result = self.parser._parse_single_comment(comment_data)

        # Should handle string IDs
        assert result is not None
        assert result["id"] == "string_id_123"
        assert result["user_id"] == "user_456"

    def test_parse_single_comment_missing_optional_fields(self):
        """Test parsing comment with missing optional fields"""
        comment_data = {
            "id": 123,
            "text": "Minimal comment",
            "user": {"id": 1},
        }

        result = self.parser._parse_single_comment(comment_data)

        # Should use defaults for missing fields
        assert result is not None
        assert result["created_at"] == ""
        assert result["source"] == ""
        assert result["user_screen_name"] == ""
        assert result["user_avatar_url"] == ""
        assert result["user_followers_count"] == ""
        assert result["like_counts"] == 0
        assert result["liked"] is False

    def test_parse_single_comment_none_input(self):
        """Test parsing None comment data"""
        result = self.parser._parse_single_comment(None)

        # Should return None for invalid input
        assert result is None

    def test_parse_single_comment_exception_during_parsing(self):
        """Test handling of unexpected exceptions during parsing"""

        # Create a dict that raises exception on access
        class FailingDict(dict):
            def get(self, key, default=None):
                if key == "text":
                    raise RuntimeError("Simulated error")
                return super().get(key, default)

        comment_data = FailingDict(
            {"id": 123, "text": "This will fail", "user": {"id": 1}}
        )

        result = self.parser._parse_single_comment(comment_data)

        # Should return None when parsing fails
        assert result is None

    def test_parse_single_comment_unicode_text(self):
        """Test parsing comment with unicode characters"""
        comment_data = {
            "id": 123,
            "text": "测试中文评论 🎉🎊 emoji test",
            "created_at": "2024-01-01",
            "source": "iPhone",
            "user": {"id": 1, "screen_name": "用户名"},
            "like_counts": 0,
            "liked": False,
        }

        result = self.parser._parse_single_comment(comment_data)

        assert result is not None
        assert "测试中文评论" in result["text"]
        assert "🎉🎊" in result["text"]
        assert result["user_screen_name"] == "用户名"

    def test_parse_single_comment_nested_user_missing_fields(self):
        """Test parsing when user object has missing nested fields"""
        comment_data = {
            "id": 123,
            "text": "Test",
            "created_at": "2024-01-01",
            "source": "iPhone",
            "user": {
                "id": 1
                # Missing: screen_name, profile_image_url, verified, etc.
            },
            "like_counts": 0,
            "liked": False,
        }

        result = self.parser._parse_single_comment(comment_data)

        assert result is not None
        assert result["user_id"] == "1"
        assert result["user_screen_name"] == ""
        assert result["user_avatar_url"] == ""
        assert result["user_verified"] is False
        assert result["user_verified_type"] == -1

    def test_parse_single_comment_verified_types(self):
        """Test parsing different verified types"""
        # Blue V (individual verification)
        comment_data = {
            "id": 123,
            "text": "Test",
            "created_at": "2024-01-01",
            "source": "iPhone",
            "user": {
                "id": 1,
                "screen_name": "User",
                "verified": True,
                "verified_type": 0,
            },
            "like_counts": 0,
            "liked": False,
        }

        result = self.parser._parse_single_comment(comment_data)
        assert result["user_verified"] is True
        assert result["user_verified_type"] == 0

        # Yellow V (organization verification)
        comment_data["user"]["verified_type"] = 1
        result = self.parser._parse_single_comment(comment_data)
        assert result["user_verified_type"] == 1

        # Not verified
        comment_data["user"]["verified"] = False
        comment_data["user"]["verified_type"] = -1
        result = self.parser._parse_single_comment(comment_data)
        assert result["user_verified"] is False
        assert result["user_verified_type"] == -1
