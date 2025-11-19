#!/usr/bin/env python

"""
Cookie fetcher module for Weibo
Supports both simple requests-based and browser-based cookie acquisition
"""

import random
import time
from typing import Dict, Optional

import requests


class CookieFetcher:
    """Cookie fetcher for Weibo"""

    def __init__(self, user_agent: Optional[str] = None, use_browser: bool = False):
        """
        Initialize cookie fetcher

        Args:
            user_agent: User-Agent string
            use_browser: Whether to use browser automation (Playwright)
                If True, requires playwright to be installed
        """
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Linux; Android 13; SM-G9980) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/112.0.5615.135 Mobile Safari/537.36"
        )
        self.use_browser = use_browser

    def fetch_cookies(self, timeout: int = 30) -> Dict[str, str]:
        """
        Fetch cookies from Weibo

        Args:
            timeout: Timeout in seconds

        Returns:
            Dictionary of cookies

        Raises:
            ImportError: If use_browser=True but playwright is not installed
            Exception: If cookie fetching fails
        """
        if self.use_browser:
            return self._fetch_with_browser(timeout)
        else:
            return self._fetch_with_requests(timeout)

    def _fetch_with_requests(self, timeout: int = 5) -> Dict[str, str]:
        """
        Fetch cookies using simple requests (legacy method)

        Args:
            timeout: Timeout in seconds

        Returns:
            Dictionary of cookies
        """
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )

        try:
            response = session.get("https://m.weibo.cn/", timeout=timeout)
            time.sleep(random.uniform(1, 2))

            if response.status_code == 200:
                return dict(session.cookies)
            else:
                return {}
        except Exception:
            return {}

    def _fetch_with_browser(self, timeout: int = 30) -> Dict[str, str]:
        """
        Fetch cookies using Playwright browser automation

        Args:
            timeout: Timeout in seconds

        Returns:
            Dictionary of cookies

        Raises:
            ImportError: If playwright is not installed
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required for browser-based cookie fetching. "
                "Install it with: uv add playwright && "
                "uv run playwright install chromium"
            )

        cookies_dict = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
            )

            context = browser.new_context(
                user_agent=self.user_agent,
                viewport={"width": 393, "height": 851},  # Android device size
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                device_scale_factor=2.75,
                is_mobile=True,
                has_touch=True,
            )

            # Add extra headers
            context.set_extra_http_headers(
                {
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept": (
                        "text/html,application/xhtml+xml,"
                        "application/xml;q=0.9,image/webp,*/*;q=0.8"
                    ),
                }
            )

            page = context.new_page()

            try:
                # Navigate to Weibo mobile homepage
                page.goto(
                    "https://m.weibo.cn/",
                    timeout=timeout * 1000,
                    wait_until="networkidle",
                )

                # Wait a bit for JavaScript to execute and cookies to be set
                time.sleep(random.uniform(2, 4))

                # Optional: Simulate some human-like behavior
                # Scroll down a bit
                page.evaluate("window.scrollBy(0, 300)")
                time.sleep(random.uniform(0.5, 1))

                # Get cookies
                cookies = context.cookies()

                # Convert to dictionary format
                for cookie in cookies:
                    cookies_dict[cookie["name"]] = cookie["value"]

            finally:
                context.close()
                browser.close()

        return cookies_dict


def fetch_cookies_simple(user_agent: Optional[str] = None) -> Dict[str, str]:
    """
    Convenience function to fetch cookies using simple requests method

    Args:
        user_agent: Optional User-Agent string

    Returns:
        Dictionary of cookies
    """
    fetcher = CookieFetcher(user_agent=user_agent, use_browser=False)
    return fetcher.fetch_cookies()


def fetch_cookies_browser(
    user_agent: Optional[str] = None, timeout: int = 30
) -> Dict[str, str]:
    """
    Convenience function to fetch cookies using browser automation

    Args:
        user_agent: Optional User-Agent string
        timeout: Timeout in seconds

    Returns:
        Dictionary of cookies

    Raises:
        ImportError: If playwright is not installed
    """
    fetcher = CookieFetcher(user_agent=user_agent, use_browser=True)
    return fetcher.fetch_cookies(timeout=timeout)
