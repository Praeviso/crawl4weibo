"""Tests for WeiboClient cookie initialization"""

import pytest
from unittest.mock import MagicMock, patch

from crawl4weibo import WeiboClient


@pytest.mark.unit
class TestClientCookieInitialization:
    """Test cookie initialization in WeiboClient"""

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_default_browser_mode(self, mock_fetcher_class):
        """Test that browser mode is enabled by default"""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_cookies.return_value = {"test": "cookie"}
        mock_fetcher_class.return_value = mock_fetcher

        WeiboClient()

        # Verify CookieFetcher was created with browser mode
        mock_fetcher_class.assert_called_once()
        call_kwargs = mock_fetcher_class.call_args.kwargs
        assert call_kwargs["use_browser"] is True

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_explicit_browser_mode_true(self, mock_fetcher_class):
        """Test explicit browser mode = True"""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_cookies.return_value = {"test": "cookie"}
        mock_fetcher_class.return_value = mock_fetcher

        WeiboClient(use_browser_cookies=True)

        call_kwargs = mock_fetcher_class.call_args.kwargs
        assert call_kwargs["use_browser"] is True

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_disable_browser_mode(self, mock_fetcher_class):
        """Test disabling browser mode"""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_cookies.return_value = {"test": "cookie"}
        mock_fetcher_class.return_value = mock_fetcher

        WeiboClient(use_browser_cookies=False)

        call_kwargs = mock_fetcher_class.call_args.kwargs
        assert call_kwargs["use_browser"] is False

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_provided_cookies_skip_fetch(self, mock_fetcher_class):
        """Test that providing cookies skips fetching"""
        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher

        cookies = {"provided": "cookie"}
        client = WeiboClient(cookies=cookies)

        # CookieFetcher should not be called
        mock_fetcher_class.assert_not_called()
        mock_fetcher.fetch_cookies.assert_not_called()

        # Verify cookies were set
        assert "provided" in client.session.cookies

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_auto_fetch_disabled(self, mock_fetcher_class):
        """Test disabling auto fetch"""
        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher

        WeiboClient(auto_fetch_cookies=False)

        # CookieFetcher should not be called
        mock_fetcher_class.assert_not_called()

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_cookies_successfully_fetched(self, mock_fetcher_class):
        """Test successful cookie fetching"""
        mock_fetcher = MagicMock()
        test_cookies = {"cookie1": "value1", "cookie2": "value2"}
        mock_fetcher.fetch_cookies.return_value = test_cookies
        mock_fetcher_class.return_value = mock_fetcher

        client = WeiboClient()

        # Verify cookies were added to session
        for name, value in test_cookies.items():
            assert client.session.cookies.get(name) == value

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_empty_cookies_handled(self, mock_fetcher_class):
        """Test empty cookies are handled gracefully"""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_cookies.return_value = {}
        mock_fetcher_class.return_value = mock_fetcher

        # Should not raise exception
        client = WeiboClient()
        assert client is not None

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_custom_user_agent_propagated(self, mock_fetcher_class):
        """Test custom user agent is propagated to CookieFetcher"""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_cookies.return_value = {}
        mock_fetcher_class.return_value = mock_fetcher

        custom_ua = "Custom User Agent"
        WeiboClient(user_agent=custom_ua)

        # Verify custom UA was passed to CookieFetcher
        call_kwargs = mock_fetcher_class.call_args.kwargs
        assert call_kwargs["user_agent"] == custom_ua

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_string_cookies_parsed(self, mock_fetcher_class):
        """Test string cookies are parsed correctly"""
        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher

        cookie_string = "name1=value1; name2=value2; name3=value3"
        client = WeiboClient(cookies=cookie_string)

        # Verify cookies were parsed
        assert client.session.cookies.get("name1") == "value1"
        assert client.session.cookies.get("name2") == "value2"
        assert client.session.cookies.get("name3") == "value3"


@pytest.mark.unit
class TestClientCookieErrorHandling:
    """Test error handling in cookie initialization"""

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_import_error_browser_mode(self, mock_fetcher_class):
        """Test ImportError when Playwright not installed (browser mode)"""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_cookies.side_effect = ImportError(
            "No module named 'playwright'"
        )
        mock_fetcher_class.return_value = mock_fetcher

        # Should raise ImportError with helpful message
        with pytest.raises(ImportError) as excinfo:
            WeiboClient(use_browser_cookies=True)

        # Note: The error should be re-raised for browser mode
        assert "playwright" in str(excinfo.value).lower()

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_import_error_simple_mode(self, mock_fetcher_class):
        """Test ImportError in simple mode (unexpected)"""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_cookies.side_effect = ImportError("Unexpected import error")
        mock_fetcher_class.return_value = mock_fetcher

        # Should raise for simple mode
        with pytest.raises(ImportError):
            WeiboClient(use_browser_cookies=False)

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_playwright_browser_not_installed(self, mock_fetcher_class):
        """Test error when Playwright installed but browser not installed"""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_cookies.side_effect = Exception(
            "Executable doesn't exist at ... chromium"
        )
        mock_fetcher_class.return_value = mock_fetcher

        # Should raise with helpful message
        with pytest.raises(Exception) as excinfo:
            WeiboClient(use_browser_cookies=True)

        assert "executable" in str(excinfo.value).lower()

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_general_exception_handled(self, mock_fetcher_class):
        """Test general exceptions are handled gracefully"""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_cookies.side_effect = Exception("Network timeout")
        mock_fetcher_class.return_value = mock_fetcher

        # Should not crash, just log warning
        client = WeiboClient(use_browser_cookies=False)
        assert client is not None


@pytest.mark.unit
class TestRefreshCookies:
    """Test refresh_cookies method"""

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_refresh_cookies_browser_mode(self, mock_fetcher_class):
        """Test refreshing cookies with browser mode"""
        # Initial setup
        mock_fetcher_init = MagicMock()
        mock_fetcher_init.fetch_cookies.return_value = {"initial": "cookie"}

        # Refresh setup
        mock_fetcher_refresh = MagicMock()
        mock_fetcher_refresh.fetch_cookies.return_value = {"refreshed": "cookie"}

        mock_fetcher_class.side_effect = [mock_fetcher_init, mock_fetcher_refresh]

        client = WeiboClient()

        # Refresh cookies
        client.refresh_cookies(use_browser=True)

        # Verify two CookieFetcher instances were created
        assert mock_fetcher_class.call_count == 2

        # Verify refresh used browser mode
        refresh_call = mock_fetcher_class.call_args_list[1]
        assert refresh_call.kwargs["use_browser"] is True

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_refresh_cookies_simple_mode(self, mock_fetcher_class):
        """Test refreshing cookies with simple mode"""
        mock_fetcher_init = MagicMock()
        mock_fetcher_init.fetch_cookies.return_value = {"initial": "cookie"}

        mock_fetcher_refresh = MagicMock()
        mock_fetcher_refresh.fetch_cookies.return_value = {"refreshed": "cookie"}

        mock_fetcher_class.side_effect = [mock_fetcher_init, mock_fetcher_refresh]

        client = WeiboClient()
        client.refresh_cookies(use_browser=False)

        # Verify refresh used simple mode
        refresh_call = mock_fetcher_class.call_args_list[1]
        assert refresh_call.kwargs["use_browser"] is False

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_refresh_cookies_updates_session(self, mock_fetcher_class):
        """Test that refresh_cookies updates session cookies"""
        mock_fetcher = MagicMock()
        new_cookies = {"new": "value", "test": "data"}
        mock_fetcher.fetch_cookies.return_value = new_cookies
        mock_fetcher_class.return_value = mock_fetcher

        client = WeiboClient()
        client.refresh_cookies(use_browser=True)

        # Verify new cookies are in session
        for name, value in new_cookies.items():
            assert client.session.cookies.get(name) == value


@pytest.mark.unit
class TestClientHeadersAndSession:
    """Test client headers and session setup"""

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_default_headers_set(self, mock_fetcher_class):
        """Test default headers are set correctly"""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_cookies.return_value = {}
        mock_fetcher_class.return_value = mock_fetcher

        client = WeiboClient()

        # Check required headers
        assert "User-Agent" in client.session.headers
        assert "Referer" in client.session.headers
        assert "Accept" in client.session.headers
        assert "X-Requested-With" in client.session.headers

        # Check specific values
        assert "Android" in client.session.headers["User-Agent"]
        assert client.session.headers["Referer"] == "https://m.weibo.cn/"
        assert client.session.headers["X-Requested-With"] == "XMLHttpRequest"

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_custom_user_agent_in_headers(self, mock_fetcher_class):
        """Test custom user agent is set in headers"""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_cookies.return_value = {}
        mock_fetcher_class.return_value = mock_fetcher

        custom_ua = "My Custom User Agent"
        client = WeiboClient(user_agent=custom_ua)

        assert client.session.headers["User-Agent"] == custom_ua


@pytest.mark.unit
class TestCookieInitializationFlow:
    """Test the complete cookie initialization flow"""

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_full_initialization_flow(self, mock_fetcher_class):
        """Test complete initialization flow with all components"""
        mock_fetcher = MagicMock()
        test_cookies = {"session": "abc123", "token": "xyz789"}
        mock_fetcher.fetch_cookies.return_value = test_cookies
        mock_fetcher_class.return_value = mock_fetcher

        # Initialize with various options
        client = WeiboClient(
            log_level="DEBUG",
            user_agent="Test UA",
            use_browser_cookies=True,
            auto_fetch_cookies=True,
        )

        # Verify all components initialized
        assert client.session is not None
        assert client.parser is not None
        assert client.proxy_pool is not None
        assert client.downloader is not None

        # Verify cookies were fetched and set
        mock_fetcher.fetch_cookies.assert_called_once()
        for name, value in test_cookies.items():
            assert client.session.cookies.get(name) == value

    @patch("crawl4weibo.core.client.CookieFetcher")
    def test_initialization_with_all_disabled(self, mock_fetcher_class):
        """Test initialization with auto_fetch disabled"""
        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher

        client = WeiboClient(
            cookies=None, auto_fetch_cookies=False, use_browser_cookies=False
        )

        # Cookie fetcher should not be called
        mock_fetcher_class.assert_not_called()

        # Client should still be functional
        assert client.session is not None
        assert client.parser is not None
