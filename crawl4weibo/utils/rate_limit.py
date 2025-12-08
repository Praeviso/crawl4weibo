#!/usr/bin/env python

"""
Rate limiting configuration and decorator for API methods
"""

import functools
import random
import time
from typing import Callable, Optional


class RateLimitConfig:
    """
    Request rate limiting configuration

    Automatically adjusts delays based on proxy pool size:
    - Larger pool → shorter delays (more IPs available)
    - Smaller pool → longer delays (avoid IP bans)
    - No pool → longest delays (use base_delay)
    """

    def __init__(
        self,
        base_delay: tuple[float, float] = (1.0, 3.0),
        min_delay: tuple[float, float] = (0.1, 0.3),
        pool_size_threshold: int = 20,
        method_multipliers: Optional[dict[str, float]] = None,
        disable_delay: bool = False,
    ):
        """
        Initialize rate limit configuration

        Args:
            base_delay: Base delay range when no proxies available (min, max)
                in seconds
            min_delay: Minimum delay range when proxy pool is large (min, max)
                in seconds
            pool_size_threshold: Pool size at which min_delay is reached
            method_multipliers: Per-method delay multipliers, e.g.
                {"search_posts": 0.5} means search_posts will have 50% of
                the calculated delay
            disable_delay: Set to True to disable all delays (for testing)

        Examples:
            ```python
            # Conservative: large delays for small pools
            RateLimitConfig(
                base_delay=(2.0, 4.0),
                min_delay=(0.5, 1.0),
                pool_size_threshold=10
            )

            # Aggressive: minimal delays with large pool
            RateLimitConfig(
                base_delay=(1.0, 2.0),
                min_delay=(0.05, 0.1),
                pool_size_threshold=50
            )

            # Method-specific tuning
            RateLimitConfig(
                method_multipliers={
                    "search_posts": 0.5,      # Fast pagination
                    "get_user_posts": 1.5,    # Slower user scraping
                }
            )
            ```
        """
        self.base_delay = base_delay
        self.min_delay = min_delay
        self.pool_size_threshold = pool_size_threshold
        self.method_multipliers = method_multipliers or {}
        self.disable_delay = disable_delay

    def get_delay(self, method_name: str, pool_size: int) -> float:
        """
        Calculate delay for a specific method based on current pool size

        Args:
            method_name: Name of the method being called
            pool_size: Current proxy pool size

        Returns:
            Delay in seconds (random value within calculated range)
        """
        if self.disable_delay:
            return 0.0

        if pool_size <= 0:
            delay_range = self.base_delay
        else:
            ratio = min(1.0, pool_size / self.pool_size_threshold)

            min_val = self.base_delay[0] * (1 - ratio) + self.min_delay[0] * ratio
            max_val = self.base_delay[1] * (1 - ratio) + self.min_delay[1] * ratio
            delay_range = (min_val, max_val)

        multiplier = self.method_multipliers.get(method_name, 1.0)
        adjusted_range = (delay_range[0] * multiplier, delay_range[1] * multiplier)

        return random.uniform(*adjusted_range)


def rate_limit(method_name: Optional[str] = None) -> Callable:
    """
    Decorator to add rate limiting to WeiboClient methods

    Automatically sleeps before executing the method based on:
    - Current proxy pool size
    - Global rate limit configuration
    - Method-specific multipliers

    Args:
        method_name: Optional method name for logging/multipliers.
            If not provided, uses function.__name__

    Usage:
        class WeiboClient:
            @rate_limit()
            def search_posts(self, query: str, page: int = 1):
                # No need for manual time.sleep() here
                ...

            @rate_limit("get_user_posts")
            def get_user_posts(self, uid: str, page: int = 1):
                ...
    """

    def decorator(func: Callable) -> Callable:
        actual_method_name = method_name or func.__name__

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            pool_size = self.get_proxy_pool_size()
            delay = self.rate_limit.get_delay(actual_method_name, pool_size)

            if delay > 0:
                self.logger.debug(
                    f"Rate limiting {actual_method_name}: "
                    f"sleeping {delay:.2f}s (pool_size={pool_size})"
                )
                time.sleep(delay)

            return func(self, *args, **kwargs)

        return wrapper

    return decorator
