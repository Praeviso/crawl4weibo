#!/usr/bin/env python

"""
Comment model for crawl4weibo
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Comment:
    """Weibo comment model"""

    id: str
    text: str = ""
    created_at: str = ""
    source: str = ""
    user_id: str = ""
    user_screen_name: str = ""
    user_avatar_url: str = ""
    user_verified: bool = False
    user_verified_type: int = -1
    user_followers_count: str = ""
    like_counts: int = 0
    liked: bool = False
    reply_id: Optional[str] = None
    reply_text: Optional[str] = None
    pic_url: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Comment":
        """
        Create Comment instance from dictionary
        (expects flattened structure from parser)
        """
        comment_data = {
            "id": str(data.get("id", "")),
            "text": data.get("text", ""),
            "created_at": data.get("created_at", ""),
            "source": data.get("source", ""),
            "user_id": data.get("user_id", ""),
            "user_screen_name": data.get("user_screen_name", ""),
            "user_avatar_url": data.get("user_avatar_url", ""),
            "user_verified": data.get("user_verified", False),
            "user_verified_type": data.get("user_verified_type", -1),
            "user_followers_count": data.get("user_followers_count", ""),
            "like_counts": data.get("like_counts", 0),
            "liked": data.get("liked", False),
            "reply_id": data.get("reply_id"),
            "reply_text": data.get("reply_text"),
            "pic_url": data.get("pic_url", ""),
            "raw_data": data,
        }
        return cls(**comment_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert Comment instance to dictionary"""
        return {
            "id": self.id,
            "text": self.text,
            "created_at": self.created_at,
            "source": self.source,
            "user_id": self.user_id,
            "user_screen_name": self.user_screen_name,
            "user_avatar_url": self.user_avatar_url,
            "user_verified": self.user_verified,
            "user_verified_type": self.user_verified_type,
            "user_followers_count": self.user_followers_count,
            "like_counts": self.like_counts,
            "liked": self.liked,
            "reply_id": self.reply_id,
            "reply_text": self.reply_text,
            "pic_url": self.pic_url,
        }
