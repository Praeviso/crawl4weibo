#!/usr/bin/env python

"""
crawl4weibo - A professional Weibo crawler library
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core.client import WeiboClient
from .exceptions.base import (
    AuthenticationError,
    CrawlError,
    NetworkError,
    ParseError,
    RateLimitError,
    UserNotFoundError,
)
from .models.comment import Comment
from .models.post import Post
from .models.user import User
from .utils.downloader import ImageDownloader
from .utils.proxy import ProxyPoolConfig
from .utils.rate_limit import RateLimitConfig

__all__ = [
    "WeiboClient",
    "User",
    "Post",
    "Comment",
    "ImageDownloader",
    "ProxyPoolConfig",
    "RateLimitConfig",
    "CrawlError",
    "AuthenticationError",
    "RateLimitError",
    "UserNotFoundError",
    "NetworkError",
    "ParseError",
]
