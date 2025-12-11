#!/usr/bin/env python

"""
Post model for crawl4weibo
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .comment import Comment


@dataclass
class Post:
    """Weibo post model"""

    id: str
    bid: str
    user_id: str
    text: str = ""
    created_at: Optional[datetime] = None
    source: str = ""
    reposts_count: int = 0
    comments_count: int = 0
    attitudes_count: int = 0
    pic_urls: list[str] = field(default_factory=list)
    video_url: str = ""
    is_original: bool = True
    retweeted_status: Optional["Post"] = None
    location: str = ""
    topic_ids: list[str] = field(default_factory=list)
    at_users: list[str] = field(default_factory=list)
    is_long_text: bool = False
    comments: list["Comment"] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Post":
        """
        Create Post instance from dictionary

        Returns:
            Post: Parsed post model
        """
        from .comment import Comment
        
        retweeted_status = None
        if data.get("retweeted_status"):
            retweeted_status = cls.from_dict(data["retweeted_status"])

        post_data = {
            "id": str(data.get("id", "")),
            "bid": data.get("bid", ""),
            "user_id": str(data.get("user_id", "")),
            "text": data.get("text", ""),
            "created_at": data.get("created_at"),
            "source": data.get("source", ""),
            "reposts_count": data.get("reposts_count", 0),
            "comments_count": data.get("comments_count", 0),
            "attitudes_count": data.get("attitudes_count", 0),
            "pic_urls": data.get("pic_urls", []),
            "video_url": data.get("video_url", ""),
            "is_original": data.get("is_original", True),
            "retweeted_status": retweeted_status,
            "location": data.get("location", ""),
            "topic_ids": data.get("topic_ids", []),
            "at_users": data.get("at_users", []),
            "is_long_text": data.get("is_long_text", False),
            "comments": [Comment.from_dict(c) for c in data.get("comments", [])],
            "raw_data": data,
        }
        return cls(**post_data)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert Post instance to dictionary

        Returns:
            dict[str, Any]: Serialized post data
        """
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "text": self.text,
            "created_at": self.created_at,
            "source": self.source,
            "reposts_count": self.reposts_count,
            "comments_count": self.comments_count,
            "attitudes_count": self.attitudes_count,
            "pic_urls": self.pic_urls,
            "video_url": self.video_url,
            "is_original": self.is_original,
            "location": self.location,
            "topic_ids": self.topic_ids,
            "at_users": self.at_users,
        }

        if self.retweeted_status:
            result["retweeted_status"] = self.retweeted_status.to_dict()

        if self.comments:
            result["comments"] = [comment.to_dict() for comment in self.comments]

        return result
