#!/usr/bin/env python

"""
Unit tests for cookie_fetcher module
"""

import pytest
import responses
from unittest.mock import patch, Mock

from crawl4weibo.utils.cookie_fetcher import (
    CookieFetcher,
    fetch_cookies_simple,
)


class TestCookieFetcher:
    """Test CookieFetcher class"""

    def test_init_default_user_agent(self):
        """Test initialization with default user agent"""
        fetcher = CookieFetcher()
        assert fetcher.use_browser is False
        assert "Android" in fetcher.user_agent
        assert "Chrome" in fetcher.user_agent

    def test_init_custom_user_agent(self):
        """Test initialization with custom user agent"""
        custom_ua = "Custom User Agent"
        fetcher = CookieFetcher(user_agent=custom_ua)
        assert fetcher.user_agent == custom_ua

    def test_init_browser_mode(self):
        """Test initialization with browser mode enabled"""
        fetcher = CookieFetcher(use_browser=True)
        assert fetcher.use_browser is True

    @responses.activate
    def test_fetch_with_requests_success(self):
        """Test successful cookie fetching with requests"""
        # Mock the response
        responses.add(
            responses.GET,
            "https://m.weibo.cn/",
            status=200,
            headers={"Set-Cookie": "test_cookie=test_value; Path=/"},
        )

        fetcher = CookieFetcher(use_browser=False)
        cookies = fetcher.fetch_cookies()

        assert isinstance(cookies, dict)
        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == "https://m.weibo.cn/"

    @responses.activate
    def test_fetch_with_requests_empty_cookies(self):
        """Test cookie fetching returns empty dict when no cookies"""
        responses.add(responses.GET, "https://m.weibo.cn/", status=200)

        fetcher = CookieFetcher(use_browser=False)
        cookies = fetcher.fetch_cookies()

        assert isinstance(cookies, dict)
        assert len(cookies) == 0

    @responses.activate
    def test_fetch_with_requests_failure(self):
        """Test cookie fetching handles request failure"""
        responses.add(
            responses.GET,
            "https://m.weibo.cn/",
            status=500,
        )

        fetcher = CookieFetcher(use_browser=False)
        cookies = fetcher.fetch_cookies()

        # Should return empty dict on failure
        assert isinstance(cookies, dict)
        assert len(cookies) == 0

    @responses.activate
    def test_fetch_with_requests_timeout(self):
        """Test cookie fetching handles timeout"""
        responses.add(
            responses.GET,
            "https://m.weibo.cn/",
            body=Exception("Timeout"),
        )

        fetcher = CookieFetcher(use_browser=False)
        cookies = fetcher.fetch_cookies()

        # Should return empty dict on timeout
        assert isinstance(cookies, dict)
        assert len(cookies) == 0

    def test_fetch_with_browser_success(self):
        """Test successful cookie fetching with browser (mocked)"""
        fetcher = CookieFetcher(use_browser=True)

        # Create mock playwright objects
        mock_page = Mock()
        mock_context = Mock()
        mock_browser = Mock()
        mock_playwright = Mock()

        mock_context.cookies.return_value = [
            {"name": "cookie1", "value": "value1"},
            {"name": "cookie2", "value": "value2"},
        ]
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_playwright.chromium.launch.return_value = mock_browser

        # Mock the context manager
        with patch("builtins.__import__") as mock_import:

            def custom_import(name, *args, **kwargs):
                if name == "playwright.sync_api":
                    module = Mock()
                    module.sync_playwright = Mock(
                        return_value=Mock(
                            __enter__=Mock(return_value=mock_playwright),
                            __exit__=Mock(return_value=None),
                        )
                    )
                    return module
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = custom_import

            cookies = fetcher.fetch_cookies()

            # Verify results
            assert isinstance(cookies, dict)
            assert len(cookies) == 2
            assert cookies["cookie1"] == "value1"
            assert cookies["cookie2"] == "value2"


class TestConvenienceFunctions:
    """Test convenience functions"""

    @responses.activate
    def test_fetch_cookies_simple(self):
        """Test fetch_cookies_simple function"""
        responses.add(
            responses.GET,
            "https://m.weibo.cn/",
            status=200,
            headers={"Set-Cookie": "test=value"},
        )

        cookies = fetch_cookies_simple()
        assert isinstance(cookies, dict)

    @responses.activate
    def test_fetch_cookies_simple_with_custom_ua(self):
        """Test fetch_cookies_simple with custom user agent"""
        custom_ua = "Custom UA"
        responses.add(responses.GET, "https://m.weibo.cn/", status=200)

        cookies = fetch_cookies_simple(user_agent=custom_ua)
        assert isinstance(cookies, dict)

        # Verify custom UA was used
        assert responses.calls[0].request.headers["User-Agent"] == custom_ua


class TestErrorHandling:
    """Test error handling scenarios"""

    @responses.activate
    def test_requests_mode_with_various_status_codes(self):
        """Test requests mode handles various HTTP status codes"""
        status_codes = [200, 301, 302, 400, 403, 404, 500, 502, 503]

        for status_code in status_codes:
            responses.reset()
            responses.add(responses.GET, "https://m.weibo.cn/", status=status_code)

            fetcher = CookieFetcher(use_browser=False)
            cookies = fetcher.fetch_cookies()

            # All should return dict (empty or with cookies)
            assert isinstance(cookies, dict)


@pytest.mark.unit
class TestCookieFetcherIntegration:
    """Integration-style tests for CookieFetcher"""

    @responses.activate
    def test_fetch_cookies_routes_to_correct_method(self):
        """Test fetch_cookies routes to correct internal method"""
        responses.add(responses.GET, "https://m.weibo.cn/", status=200)

        # Test requests mode
        fetcher_requests = CookieFetcher(use_browser=False)
        cookies = fetcher_requests.fetch_cookies()
        assert isinstance(cookies, dict)

    @responses.activate
    def test_user_agent_propagation(self):
        """Test user agent is properly propagated through the system"""
        custom_ua = "Test User Agent v1.0"
        responses.add(responses.GET, "https://m.weibo.cn/", status=200)

        fetcher = CookieFetcher(user_agent=custom_ua, use_browser=False)
        fetcher.fetch_cookies()

        # Verify the request was made with custom UA
        assert len(responses.calls) == 1
        assert responses.calls[0].request.headers["User-Agent"] == custom_ua
