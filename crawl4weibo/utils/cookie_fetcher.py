#!/usr/bin/env python

"""
Cookie fetcher module for Weibo
Supports both simple requests-based and browser-based cookie acquisition
"""

import asyncio
import contextlib
import os
import platform
import random
import time
from pathlib import Path
from typing import Optional, Union

import requests

LOGIN_URL = "https://passport.weibo.cn/signin/login?entry=mweibo"
MOBILE_URL = "https://m.weibo.cn/"
LOGIN_COOKIE_NAMES = {"SUB", "SUBP", "SSOLoginState"}


def _is_event_loop_running() -> bool:
    """Check if we're running inside an asyncio event loop"""
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


def _has_login_cookie(cookies: list[dict[str, str]]) -> bool:
    """Check if any cookie indicates an authenticated Weibo session"""
    return any(cookie.get("name") in LOGIN_COOKIE_NAMES for cookie in cookies)


def _discover_chrome_cdp_endpoint() -> Optional[str]:
    """读取 Chrome 的 DevToolsActivePort 文件，发现已运行的 Chrome 调试端点。
    支持 Chrome 146+ 的原生远程调试（approval mode）。"""
    home = Path.home()
    system = platform.system()

    if system == "Darwin":
        candidates = [
            home / "Library" / "Application Support" / "Google" / "Chrome",
            home / "Library" / "Application Support" / "Google" / "Chrome Canary",
        ]
    elif system == "Windows":
        local_app = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        candidates = [
            local_app / "Google" / "Chrome" / "User Data",
        ]
    else:
        candidates = [
            home / ".config" / "google-chrome",
            home / ".config" / "google-chrome-beta",
        ]

    for user_data_dir in candidates:
        port_file = user_data_dir / "DevToolsActivePort"
        if not port_file.exists():
            continue
        try:
            content = port_file.read_text().strip()
            lines = content.split("\n")
            port = int(lines[0].strip())
            if port > 0:
                return f"http://127.0.0.1:{port}"
        except (ValueError, IndexError, OSError):
            continue

    return None


class CookieFetcher:
    """Cookie fetcher for Weibo"""

    def __init__(
        self,
        user_agent: Optional[str] = None,
        use_browser: bool = False,
        require_login: bool = False,
        login_timeout: int = 120,
        headless: bool = True,
        storage_state_path: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize cookie fetcher

        Args:
            user_agent: User-Agent string
            use_browser: Whether to use browser automation (Playwright)
                If True, requires playwright to be installed
            require_login: If True, waits for logged-in cookies to appear
            login_timeout: Timeout for manual login in seconds
            headless: Whether to run the browser in headless mode
            storage_state_path: Optional path to persist Playwright storage state
        """
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Linux; Android 13; SM-G9980) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/112.0.5615.135 Mobile Safari/537.36"
        )
        self.use_browser = use_browser
        self.require_login = require_login
        self.login_timeout = login_timeout
        self.headless = headless
        self.storage_state_path = (
            Path(storage_state_path).expanduser()
            if storage_state_path is not None
            else None
        )

    def fetch_cookies(self, timeout: int = 30) -> dict[str, str]:
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
        if self.require_login and not self.use_browser:
            raise ValueError("require_login=True requires use_browser=True")
        if self.use_browser:
            return self._fetch_with_browser(timeout)
        else:
            return self._fetch_with_requests(timeout)

    def _fetch_with_requests(self, timeout: int = 5) -> dict[str, str]:
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
            response = session.get(MOBILE_URL, timeout=timeout)
            time.sleep(random.uniform(1, 2))

            if response.status_code == 200:
                return dict(session.cookies)
            else:
                return {}
        except Exception:
            return {}

    def _fetch_with_browser(self, timeout: int = 30) -> dict[str, str]:
        """
        Fetch cookies using Playwright browser automation

        Args:
            timeout: Timeout in seconds

        Returns:
            Dictionary of cookies

        Raises:
            ImportError: If playwright is not installed
        """
        # Check if we're in an event loop (e.g., Jupyter notebook)
        if _is_event_loop_running():
            # Use async API
            return self._fetch_with_browser_async_wrapper(timeout)
        else:
            # Use sync API
            return self._fetch_with_browser_sync(timeout)

    def _resolve_storage_state_path(self) -> Optional[str]:
        if not self.storage_state_path:
            return None
        if self.storage_state_path.exists():
            return str(self.storage_state_path)
        return None

    def _persist_storage_state_sync(self, context) -> None:
        if not self.storage_state_path:
            return
        self.storage_state_path.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(self.storage_state_path))
        self._secure_storage_state_file()

    async def _persist_storage_state_async(self, context) -> None:
        if not self.storage_state_path:
            return
        self.storage_state_path.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(self.storage_state_path))
        self._secure_storage_state_file()

    def _secure_storage_state_file(self) -> None:
        if not self.storage_state_path:
            return
        # Best-effort permission hardening; ignore if unsupported.
        with contextlib.suppress(OSError):
            self.storage_state_path.chmod(0o600)

    def _wait_for_login_sync(self, context, timeout: int) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            cookies = context.cookies()
            if _has_login_cookie(cookies):
                return
            time.sleep(1)
        raise TimeoutError(
            f"Login cookies not detected within {timeout} seconds. "
            "Please complete login in the browser window."
        )

    async def _wait_for_login_async(self, context, timeout: int) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            cookies = await context.cookies()
            if _has_login_cookie(cookies):
                return
            await asyncio.sleep(1)
        raise TimeoutError(
            f"Login cookies not detected within {timeout} seconds. "
            "Please complete login in the browser window."
        )

    def _ensure_login_sync(self, page, context, timeout: int) -> None:
        storage_state = self._resolve_storage_state_path()
        if storage_state:
            page.goto(
                MOBILE_URL,
                timeout=timeout * 1000,
                wait_until="domcontentloaded",
            )
            time.sleep(random.uniform(1, 2))
            if _has_login_cookie(context.cookies()):
                return

        page.goto(
            LOGIN_URL,
            timeout=timeout * 1000,
            wait_until="domcontentloaded",
        )
        self._wait_for_login_sync(context, self.login_timeout)
        page.goto(
            MOBILE_URL,
            timeout=timeout * 1000,
            wait_until="networkidle",
        )

    async def _ensure_login_async(self, page, context, timeout: int) -> None:
        storage_state = self._resolve_storage_state_path()
        if storage_state:
            await page.goto(
                MOBILE_URL,
                timeout=timeout * 1000,
                wait_until="domcontentloaded",
            )
            await asyncio.sleep(random.uniform(1, 2))
            if _has_login_cookie(await context.cookies()):
                return

        await page.goto(
            LOGIN_URL,
            timeout=timeout * 1000,
            wait_until="domcontentloaded",
        )
        await self._wait_for_login_async(context, self.login_timeout)
        await page.goto(
            MOBILE_URL,
            timeout=timeout * 1000,
            wait_until="networkidle",
        )

    def _fetch_with_browser_sync(self, timeout: int = 30) -> dict[str, str]:
        """
        Fetch cookies using synchronous Playwright API

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
            connected_via_cdp = False
            endpoint = _discover_chrome_cdp_endpoint()
            if endpoint:
                try:
                    browser = p.chromium.connect_over_cdp(endpoint)
                    connected_via_cdp = True
                except Exception:
                    pass

            if not connected_via_cdp:
                browser = p.chromium.launch(
                    headless=self.headless,
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
                storage_state=self._resolve_storage_state_path(),
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
                # Navigate to Weibo mobile homepage or login flow
                if self.require_login:
                    self._ensure_login_sync(page, context, timeout)
                else:
                    page.goto(
                        MOBILE_URL,
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

                if self.require_login and _has_login_cookie(cookies):
                    self._persist_storage_state_sync(context)
            finally:
                context.close()
                if not connected_via_cdp:
                    browser.close()

        return cookies_dict

    async def _fetch_with_browser_async(self, timeout: int = 30) -> dict[str, str]:
        """
        Fetch cookies using asynchronous Playwright API

        Args:
            timeout: Timeout in seconds

        Returns:
            Dictionary of cookies

        Raises:
            ImportError: If playwright is not installed
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required for browser-based cookie fetching. "
                "Install it with: uv add playwright && "
                "uv run playwright install chromium"
            )

        cookies_dict = {}

        async with async_playwright() as p:
            connected_via_cdp = False
            endpoint = _discover_chrome_cdp_endpoint()
            if endpoint:
                try:
                    browser = await p.chromium.connect_over_cdp(endpoint)
                    connected_via_cdp = True
                except Exception:
                    pass

            if not connected_via_cdp:
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                    ],
                )

            context = await browser.new_context(
                user_agent=self.user_agent,
                viewport={"width": 393, "height": 851},  # Android device size
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                device_scale_factor=2.75,
                is_mobile=True,
                has_touch=True,
                storage_state=self._resolve_storage_state_path(),
            )

            # Add extra headers
            await context.set_extra_http_headers(
                {
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept": (
                        "text/html,application/xhtml+xml,"
                        "application/xml;q=0.9,image/webp,*/*;q=0.8"
                    ),
                }
            )

            page = await context.new_page()

            try:
                # Navigate to Weibo mobile homepage or login flow
                if self.require_login:
                    await self._ensure_login_async(page, context, timeout)
                else:
                    await page.goto(
                        MOBILE_URL,
                        timeout=timeout * 1000,
                        wait_until="networkidle",
                    )

                # Wait a bit for JavaScript to execute and cookies to be set
                await asyncio.sleep(random.uniform(2, 4))

                # Optional: Simulate some human-like behavior
                # Scroll down a bit
                await page.evaluate("window.scrollBy(0, 300)")
                await asyncio.sleep(random.uniform(0.5, 1))

                # Get cookies
                cookies = await context.cookies()

                # Convert to dictionary format
                for cookie in cookies:
                    cookies_dict[cookie["name"]] = cookie["value"]

                if self.require_login and _has_login_cookie(cookies):
                    await self._persist_storage_state_async(context)
            finally:
                await context.close()
                if not connected_via_cdp:
                    await browser.close()

        return cookies_dict

    def _fetch_with_browser_async_wrapper(self, timeout: int = 30) -> dict[str, str]:
        """
        Wrapper to run async browser fetching in an existing event loop

        Args:
            timeout: Timeout in seconds

        Returns:
            Dictionary of cookies
        """
        # Run the coroutine in a new thread to avoid blocking the existing event loop
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run, self._fetch_with_browser_async(timeout)
            )
            return future.result()


def fetch_cookies_simple(user_agent: Optional[str] = None) -> dict[str, str]:
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
    user_agent: Optional[str] = None,
    timeout: int = 30,
    require_login: bool = False,
    login_timeout: int = 120,
    headless: bool = True,
    storage_state_path: Optional[Union[str, Path]] = None,
) -> dict[str, str]:
    """
    Convenience function to fetch cookies using browser automation

    Args:
        user_agent: Optional User-Agent string
        timeout: Timeout in seconds
        require_login: If True, waits for logged-in cookies to appear
        login_timeout: Timeout for manual login in seconds
        headless: Whether to run the browser in headless mode
        storage_state_path: Optional path to persist Playwright storage state

    Returns:
        Dictionary of cookies

    Raises:
        ImportError: If playwright is not installed
    """
    fetcher = CookieFetcher(
        user_agent=user_agent,
        use_browser=True,
        require_login=require_login,
        login_timeout=login_timeout,
        headless=headless,
        storage_state_path=storage_state_path,
    )
    return fetcher.fetch_cookies(timeout=timeout)
