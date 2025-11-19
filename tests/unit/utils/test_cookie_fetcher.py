#!/usr/bin/env python

"""
Unit tests for cookie_fetcher module
"""

import asyncio
from unittest.mock import Mock, patch

import pytest
import responses

from crawl4weibo.utils.cookie_fetcher import (
    CookieFetcher,
    _is_event_loop_running,
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


class TestEventLoopDetection:
    """Test event loop detection functionality"""

    def test_is_event_loop_running_no_loop(self):
        """Test event loop detection when no loop is running"""
        assert _is_event_loop_running() is False

    @pytest.mark.asyncio
    async def test_is_event_loop_running_with_loop(self):
        """Test event loop detection when loop is running"""
        assert _is_event_loop_running() is True


class TestAsyncBrowserSupport:
    """Test async browser cookie fetching"""

    def test_browser_mode_routes_to_sync_by_default(self):
        """Test browser mode uses sync API when not in event loop"""
        fetcher = CookieFetcher(use_browser=True)

        with patch.object(
            fetcher, "_fetch_with_browser_sync", return_value={"test": "cookie"}
        ) as mock_sync, patch.object(
            fetcher, "_fetch_with_browser_async_wrapper"
        ) as mock_async:
            cookies = fetcher._fetch_with_browser()

            # Should call sync version
            mock_sync.assert_called_once()
            mock_async.assert_not_called()
            assert cookies == {"test": "cookie"}

    @pytest.mark.asyncio
    async def test_browser_mode_routes_to_async_in_event_loop(self):
        """Test browser mode uses async API when in event loop"""
        fetcher = CookieFetcher(use_browser=True)

        with patch.object(
            fetcher, "_fetch_with_browser_sync"
        ) as mock_sync, patch.object(
            fetcher,
            "_fetch_with_browser_async_wrapper",
            return_value={"test": "cookie"},
        ) as mock_async:
            cookies = fetcher._fetch_with_browser()

            # Should call async wrapper version
            mock_async.assert_called_once()
            mock_sync.assert_not_called()
            assert cookies == {"test": "cookie"}

    def test_async_wrapper_executes_in_thread(self):
        """Test async wrapper properly executes async code in thread"""
        fetcher = CookieFetcher(use_browser=True)

        # Mock the async method
        async def mock_async_fetch(timeout):
            await asyncio.sleep(0.01)
            return {"async": "cookie"}

        with patch.object(
            fetcher, "_fetch_with_browser_async", side_effect=mock_async_fetch
        ):
            # This should work even though we're not in an async context
            cookies = fetcher._fetch_with_browser_async_wrapper(timeout=30)
            assert cookies == {"async": "cookie"}

    @pytest.mark.asyncio
    async def test_fetch_with_browser_async_full_flow(self):
        """Test the full async browser flow with mocked Playwright"""
        fetcher = CookieFetcher(use_browser=True)

        # Create comprehensive mocks for async Playwright
        mock_cookie_list = [
            {"name": "async_cookie1", "value": "async_value1"},
            {"name": "async_cookie2", "value": "async_value2"},
        ]

        # Create async mock functions
        async def mock_goto(*args, **kwargs):
            pass

        async def mock_evaluate(*args, **kwargs):
            pass

        async def mock_cookies():
            return mock_cookie_list

        async def mock_new_page():
            return mock_page

        async def mock_set_headers(*args, **kwargs):
            pass

        async def mock_close():
            pass

        async def mock_new_context(*args, **kwargs):
            return mock_context

        async def mock_launch(*args, **kwargs):
            return mock_browser

        # Mock async context manager and page operations
        mock_page = Mock()
        mock_page.goto = Mock(side_effect=mock_goto)
        mock_page.evaluate = Mock(side_effect=mock_evaluate)

        mock_context = Mock()
        mock_context.cookies = Mock(side_effect=mock_cookies)
        mock_context.new_page = Mock(side_effect=mock_new_page)
        mock_context.set_extra_http_headers = Mock(side_effect=mock_set_headers)
        mock_context.close = Mock(side_effect=mock_close)

        mock_browser = Mock()
        mock_browser.new_context = Mock(side_effect=mock_new_context)
        mock_browser.close = Mock(side_effect=mock_close)

        mock_chromium = Mock()
        mock_chromium.launch = Mock(side_effect=mock_launch)

        mock_playwright_instance = Mock()
        mock_playwright_instance.chromium = mock_chromium

        # Mock the async_playwright context manager
        class MockAsyncPlaywright:
            async def __aenter__(self):
                return mock_playwright_instance

            async def __aexit__(self, *args):
                pass

        # Patch the import and execute
        with patch("builtins.__import__") as mock_import:

            def custom_import(name, *args, **kwargs):
                if name == "playwright.async_api":
                    module = Mock()
                    module.async_playwright = lambda: MockAsyncPlaywright()
                    return module
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = custom_import

            # Execute the async method
            cookies = await fetcher._fetch_with_browser_async(timeout=30)

            # Verify results
            assert isinstance(cookies, dict)
            assert len(cookies) == 2
            assert cookies["async_cookie1"] == "async_value1"
            assert cookies["async_cookie2"] == "async_value2"

            # Verify the flow was called correctly
            mock_chromium.launch.assert_called_once()
            mock_browser.new_context.assert_called_once()
            mock_context.set_extra_http_headers.assert_called_once()
            mock_context.new_page.assert_called_once()
            mock_page.goto.assert_called_once()
            mock_context.cookies.assert_called_once()
            assert mock_context.close.call_count == 1
            assert mock_browser.close.call_count == 1

    def test_fetch_with_browser_async_import_error(self):
        """Test async browser raises ImportError when playwright not installed"""
        fetcher = CookieFetcher(use_browser=True)

        # Mock the import to raise ImportError
        with patch("builtins.__import__") as mock_import:

            def custom_import(name, *args, **kwargs):
                if name == "playwright.async_api":
                    raise ImportError("No module named 'playwright'")
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = custom_import

            # Should raise ImportError with helpful message
            with pytest.raises(ImportError) as exc_info:
                asyncio.run(fetcher._fetch_with_browser_async(timeout=30))

            assert "Playwright is required" in str(exc_info.value)
            assert "uv add playwright" in str(exc_info.value)
