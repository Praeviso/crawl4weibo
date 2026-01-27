#!/usr/bin/env python

"""
User model for crawl4weibo
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class User:
    """Weibo user model"""

    id: str
    screen_name: str = ""
    gender: str = ""
    location: str = ""
    description: str = ""
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    verified: bool = False
    verified_reason: str = ""
    avatar_url: str = ""
    cover_image_url: str = ""
    birthday: Optional[str] = None
    education: str = ""
    company: str = ""
    registration_time: Optional[datetime] = None
    sunshine_credit: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "User":
        """
        Create User instance from dictionary

        Returns:
            User: Parsed user model
        """

        def _coalesce_str(*values: Any) -> str:
            for value in values:
                if isinstance(value, str) and value.strip():
                    return value
            return ""

        following_count = data.get("following_count")
        if following_count in (None, ""):
            following_count = data.get("follow_count", data.get("friends_count", 0))

        posts_count = data.get("posts_count")
        if posts_count in (None, ""):
            posts_count = data.get("statuses_count", 0)

        registration_time = data.get("registration_time")
        registration_value = (
            registration_time
            if isinstance(registration_time, datetime)
            else _coalesce_str(data.get("registration_time"), data.get("register_time"))
        )

        user_data = {
            "id": str(data.get("id", "")),
            "screen_name": data.get("screen_name", ""),
            "gender": data.get("gender", ""),
            "location": _coalesce_str(
                data.get("location"),
                data.get("ip_location"),
                data.get("region_name"),
            ),
            "description": data.get("description", ""),
            "followers_count": data.get("followers_count", 0),
            "following_count": following_count,
            "posts_count": posts_count,
            "verified": data.get("verified", False),
            "verified_reason": data.get("verified_reason", ""),
            "avatar_url": _coalesce_str(
                data.get("avatar_url"), data.get("profile_image_url")
            ),
            "cover_image_url": _coalesce_str(
                data.get("cover_image_url"), data.get("cover_image_phone")
            ),
            "birthday": _coalesce_str(data.get("birthday"), data.get("birthday_text")),
            "education": _coalesce_str(
                data.get("education"), data.get("education_background")
            ),
            "company": _coalesce_str(data.get("company"), data.get("company_name")),
            "registration_time": registration_value,
            "sunshine_credit": _coalesce_str(
                data.get("sunshine_credit"), data.get("sunshine")
            ),
            "raw_data": data,
        }
        return cls(**user_data)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert User instance to dictionary

        Returns:
            dict[str, Any]: Serialized user data
        """
        return {
            "id": self.id,
            "screen_name": self.screen_name,
            "gender": self.gender,
            "location": self.location,
            "description": self.description,
            "followers_count": self.followers_count,
            "following_count": self.following_count,
            "posts_count": self.posts_count,
            "verified": self.verified,
            "verified_reason": self.verified_reason,
            "avatar_url": self.avatar_url,
            "cover_image_url": self.cover_image_url,
            "birthday": self.birthday,
            "education": self.education,
            "company": self.company,
            "registration_time": self.registration_time,
            "sunshine_credit": self.sunshine_credit,
        }
