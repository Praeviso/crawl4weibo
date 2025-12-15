"""Live availability smoke test for scheduled GitHub Actions runs.

This test is intentionally strict (does not `skip`) so the workflow status
reflects real-world availability.
"""

from __future__ import annotations

import os
import time

import pytest

from crawl4weibo import WeiboClient
from crawl4weibo.utils.proxy import ProxyPoolConfig
from crawl4weibo.utils.rate_limit import RateLimitConfig


@pytest.mark.availability
@pytest.mark.slow
def test_weibo_api_availability_smoke() -> None:
    if os.getenv("RUN_WEIBO_AVAILABILITY") != "1":
        pytest.skip("Only run in scheduled availability workflow")

    uid = os.getenv("WEIBO_HEALTHCHECK_UID", "2656274875")

    start = time.monotonic()
    proxy_api_url = os.getenv("WEIBO_PROXY_API_URL")
    use_once_proxy = os.getenv("WEIBO_USE_ONCE_PROXY", "").lower() in {"1", "true", "yes"}
    proxy_config = (
        ProxyPoolConfig(proxy_api_url=proxy_api_url, use_once_proxy=use_once_proxy)
        if proxy_api_url
        else None
    )

    client = WeiboClient(
        rate_limit_config=RateLimitConfig(disable_delay=True),
        proxy_config=proxy_config,
    )

    user = client.get_user_by_uid(uid)
    posts = client.get_user_posts(uid, page=1, expand=False)

    elapsed_s = time.monotonic() - start
    print(f"Healthcheck OK in {elapsed_s:.2f}s (uid={uid})")

    assert user is not None
    assert getattr(user, "id", None) == uid
    assert len(getattr(user, "screen_name", "")) > 0

    assert isinstance(posts, list)
    assert posts, "Expected at least one post from a high-activity test account"
    assert getattr(posts[0], "user_id", None) == uid
