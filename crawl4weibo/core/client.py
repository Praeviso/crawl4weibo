#!/usr/bin/env python

"""
Weibo Crawler Client - Based on successfully tested code
"""

import random
import time
from pathlib import Path
from typing import Any, Optional, Union

import requests

from ..exceptions.base import CrawlError, NetworkError, ParseError, UserNotFoundError
from ..models.comment import Comment
from ..models.post import Post
from ..models.user import User
from ..utils.cookie_fetcher import CookieFetcher
from ..utils.downloader import ImageDownloader
from ..utils.logger import setup_logger
from ..utils.parser import WeiboParser
from ..utils.proxy import ProxyPool, ProxyPoolConfig
from ..utils.rate_limit import RateLimitConfig, rate_limit


class WeiboClient:
    """Weibo Crawler Client"""

    def __init__(
        self,
        cookies: Optional[Union[str, dict[str, str]]] = None,
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        user_agent: Optional[str] = None,
        proxy_config: Optional[ProxyPoolConfig] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
        use_browser_cookies: bool = True,
        auto_fetch_cookies: bool = True,
    ):
        """
        Initialize Weibo client

        Args:
            cookies: Optional cookie string or dictionary. If provided,
                auto_fetch_cookies will be ignored.
            log_level: Logging level
            log_file: Log file path
            user_agent: Optional User-Agent string
            proxy_config: Proxy pool configuration object. If not provided,
                proxy will be disabled. Use ProxyPoolConfig to configure
                proxy settings like API URL, TTL, pool size, etc.
            rate_limit_config: Rate limiting configuration. If not provided,
                uses default configuration that automatically adjusts delays
                based on proxy pool size. Larger pools = shorter delays.
            use_browser_cookies: If True, uses Playwright to fetch cookies
                from a real browser. Requires playwright installation.
                If False, uses simple requests method (may not work if
                Weibo has strengthened anti-scraping). Default: True
            auto_fetch_cookies: If True and cookies parameter is not provided,
                automatically fetches cookies during initialization.
                Default: True
        """
        self.logger = setup_logger(
            level=getattr(__import__("logging"), log_level.upper()), log_file=log_file
        )

        self.session = requests.Session()

        default_user_agent = (
            "Mozilla/5.0 (Linux; Android 13; SM-G9980) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/112.0.5615.135 Mobile Safari/537.36"
        )
        self.user_agent = user_agent or default_user_agent
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Referer": "https://m.weibo.cn/",
                "Accept": "application/json, text/plain, */*",
                "X-Requested-With": "XMLHttpRequest",
            }
        )

        # Handle cookies
        if cookies:
            self._set_cookies(cookies)
            self.logger.info("Using provided cookies")
        elif auto_fetch_cookies:
            self._init_session(use_browser=use_browser_cookies)
        else:
            self.logger.info("Skipping cookie initialization")

        self.parser = WeiboParser()

        self.proxy_pool = ProxyPool(config=proxy_config)
        self.rate_limit = rate_limit_config or RateLimitConfig()
        self.downloader = ImageDownloader(
            session=self.session,
            download_dir="./weibo_images",
            proxy_pool=self.proxy_pool,
        )

        if proxy_config and proxy_config.proxy_api_url:
            proxy_mode = "one-time" if proxy_config.use_once_proxy else "pooling"
            self.logger.info(
                f"Proxy enabled in {proxy_mode} mode "
                f"(API: {proxy_config.proxy_api_url}"
                + (
                    ""
                    if proxy_config.use_once_proxy
                    else f", Capacity: {proxy_config.pool_size}, "
                    f"TTL: {proxy_config.dynamic_proxy_ttl}s, "
                    f"Strategy: {proxy_config.fetch_strategy}"
                )
                + ")"
            )

        self.logger.info("WeiboClient initialized successfully")

    def _set_cookies(self, cookies: Union[str, dict[str, str]]):
        if isinstance(cookies, str):
            cookie_dict = {}
            for pair in cookies.split(";"):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    cookie_dict[key.strip()] = value.strip()
            self.session.cookies.update(cookie_dict)
        elif isinstance(cookies, dict):
            self.session.cookies.update(cookies)

    def _init_session(self, use_browser: bool = False):
        """
        Initialize session and fetch cookies

        Args:
            use_browser: If True, uses Playwright browser automation.
                If False, uses simple requests method.
        """
        try:
            method = "browser" if use_browser else "requests"
            self.logger.debug(f"Initializing session with {method} method...")

            fetcher = CookieFetcher(user_agent=self.user_agent, use_browser=use_browser)
            cookies = fetcher.fetch_cookies()

            if cookies:
                self.session.cookies.update(cookies)
                self.logger.info(
                    f"Successfully fetched {len(cookies)} cookies using "
                    f"{'browser' if use_browser else 'requests'} method"
                )
            else:
                self.logger.warning("No cookies fetched during session initialization")

        except ImportError as e:
            if use_browser:
                # Browser mode is required, provide installation instructions
                self.logger.error(
                    "Playwright is required but not installed. "
                    "Please install it with the following commands:"
                )
                print("\n" + "=" * 70)
                print("ERROR: Playwright is not installed")
                print("=" * 70)
                print("\nWeibo's anti-scraping has been strengthened.")
                print("Browser automation is now required to fetch cookies.\n")
                print("Please run the following commands to install:\n")
                print("  uv add playwright")
                print("  uv run playwright install chromium\n")
                print("Or if you're using pip:\n")
                print("  pip install playwright")
                print("  playwright install chromium")
                print("=" * 70 + "\n")
                raise
            else:
                # Simple mode with ImportError is unexpected
                self.logger.error(f"Failed to initialize session: {e}")
                raise
        except Exception as e:
            # Catch Playwright browser not installed errors
            playwright_error = "playwright" in str(e).lower()
            executable_error = "executable" in str(e).lower()
            browser_error = "browser" in str(e).lower()

            if use_browser and (playwright_error or executable_error or browser_error):
                self.logger.error(
                    "Playwright browser is not installed. "
                    "Please install it with: playwright install chromium"
                )
                print("\n" + "=" * 70)
                print("ERROR: Playwright browser is not installed")
                print("=" * 70)
                print(
                    "\nPlaywright is installed, but the Chromium browser is missing.\n"
                )
                print("Please run the following command to install the browser:\n")
                print("  uv run playwright install chromium\n")
                print("Or if you're using pip:\n")
                print("  playwright install chromium")
                print("=" * 70 + "\n")
                raise
            else:
                self.logger.warning(f"Session initialization failed: {e}")

    def _request(
        self,
        url: str,
        params: dict[str, Any],
        max_retries: int = 3,
        use_proxy: bool = True,
    ) -> dict[str, Any]:
        """
        Send HTTP request

        Args:
            url: Request URL
            params: Request parameters
            max_retries: Maximum number of retries
            use_proxy: Whether to use proxy, default True. Set to False to
                disable proxy for a single request

        Returns:
            Response JSON data
        """
        is_once_proxy = (
            use_proxy
            and self.proxy_pool
            and self.proxy_pool.is_enabled()
            and self.proxy_pool.config.use_once_proxy
        )

        for attempt in range(1, max_retries + 1):
            proxies = None
            using_proxy = False
            proxy_url = None
            if use_proxy and self.proxy_pool and self.proxy_pool.is_enabled():
                proxies = self.proxy_pool.get_proxy()
                if proxies:
                    using_proxy = True
                    proxy_url = proxies.get("http")
                    self.logger.debug(f"Using proxy: {proxy_url}")
                else:
                    self.logger.warning(
                        "Proxy pool failed to get available proxy, "
                        "request will proceed without proxy"
                    )

            try:
                response = self.session.get(
                    url, params=params, proxies=proxies, timeout=5
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 432:
                    if using_proxy and proxy_url and not is_once_proxy:
                        if self.proxy_pool.remove_proxy(proxy_url):
                            self.logger.warning(
                                f"Proxy {proxy_url} returned 432, removed from pool"
                            )
                        else:
                            self.logger.debug(
                                f"Failed to remove proxy {proxy_url} from pool"
                            )

                    if attempt < max_retries:
                        if is_once_proxy:
                            self.logger.warning(
                                "Encountered 432 error with one-time proxy, "
                                "retrying immediately with fresh IP..."
                            )
                            continue
                        elif using_proxy:
                            sleep_time = random.uniform(0.5, 1.5)
                        else:
                            sleep_time = random.uniform(4, 7)
                        self.logger.warning(
                            f"Encountered 432 error, waiting {sleep_time:.1f} "
                            "seconds before retry..."
                        )
                        time.sleep(sleep_time)
                        continue
                    else:
                        raise NetworkError("Encountered 432 anti-crawler block")
                else:
                    response.raise_for_status()

            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    if is_once_proxy:
                        self.logger.warning(
                            f"Request failed with one-time proxy, "
                            f"retrying immediately with fresh IP: {e}"
                        )
                        continue
                    elif using_proxy:
                        sleep_time = random.uniform(0.5, 1.5)
                    else:
                        sleep_time = random.uniform(2, 5)
                    self.logger.warning(
                        f"Request failed, waiting {sleep_time:.1f} seconds "
                        f"before retry: {e}"
                    )
                    time.sleep(sleep_time)
                    continue
                else:
                    raise NetworkError(f"Request failed: {e}")

        raise CrawlError("Maximum retry attempts reached")

    def refresh_cookies(self, use_browser: bool = False):
        """
        Manually refresh cookies

        Args:
            use_browser: If True, uses Playwright browser automation.
                If False, uses simple requests method.

        Raises:
            ImportError: If use_browser=True but playwright is not installed
        """
        self._init_session(use_browser=use_browser)

    def add_proxy(self, proxy_url: str, ttl: Optional[int] = None):
        """
        Manually add static proxy to proxy pool

        Args:
            proxy_url: Proxy URL, format like 'http://1.2.3.4:8080' or 'http://user:pass@ip:port'
            ttl: Expiration time (seconds), None means never expires
        """
        self.proxy_pool.add_proxy(proxy_url, ttl)
        ttl_str = "never expires" if ttl is None else f"{ttl}s"
        self.logger.info(f"Added proxy to pool: {proxy_url}, TTL: {ttl_str}")

    def get_proxy_pool_size(self) -> int:
        """
        Get current proxy pool size

        Returns:
            Number of available proxies
        """
        return self.proxy_pool.get_pool_size()

    def clear_proxy_pool(self):
        """Clear proxy pool"""
        self.proxy_pool.clear_pool()
        self.logger.info("Proxy pool cleared")

    @rate_limit()
    def get_user_by_uid(self, uid: str, use_proxy: bool = True) -> User:
        """
        Get user information

        Args:
            uid: User ID
            use_proxy: Whether to use proxy, default True

        Returns:
            User object
        """
        url = "https://m.weibo.cn/api/container/getIndex"
        params = {"containerid": f"100505{uid}"}

        data = self._request(url, params, use_proxy=use_proxy)

        if not data.get("data") or not data["data"].get("userInfo"):
            raise UserNotFoundError(f"User {uid} not found")

        user_info = self.parser.parse_user_info(data)
        user = User.from_dict(user_info)

        self.logger.info(f"Fetched user: {user.screen_name}")
        return user

    @rate_limit()
    def get_user_posts(
        self,
        uid: str,
        page: int = 1,
        expand: bool = False,
        with_comments: bool = False,
        comment_limit: int = 10,
        use_proxy: bool = True,
    ) -> list[Post]:
        """
        Get user's posts list

        Args:
            uid: User ID
            page: Page number
            expand: Whether to expand long text posts
            with_comments: If True, fetch comments for each post
            comment_limit: Maximum comments per post (default: 10)
            use_proxy: Whether to use proxy, default True

        Returns:
            List of Post objects (with comments if with_comments=True)
        """
        url = "https://m.weibo.cn/api/container/getIndex"
        params = {"containerid": f"107603{uid}", "page": page}

        data = self._request(url, params, use_proxy=use_proxy)

        if not data.get("data"):
            return []

        posts_data, pagination = self.parser.parse_posts(data)
        posts = [Post.from_dict(post_data) for post_data in posts_data]
        for post in posts:
            if post.is_long_text and expand:
                try:
                    long_post = self.get_post_by_bid(post.bid)
                    post.text = long_post.text
                    post.pic_urls = long_post.pic_urls
                    post.video_url = long_post.video_url
                except Exception as e:
                    self.logger.warning(f"Failed to expand long post {post.bid}: {e}")

        # Fetch comments if requested
        if with_comments and posts:
            posts = self._fetch_comments_for_posts(
                posts, comment_limit=comment_limit, use_proxy=use_proxy
            )

        self.logger.info(f"Fetched {len(posts)} posts")
        return posts

    def get_post_by_bid(
        self,
        bid: str,
        with_comments: bool = False,
        comment_limit: int = 10,
        use_proxy: bool = True,
    ) -> Post:
        """
        Get post details by bid

        Args:
            bid: Post bid
            with_comments: If True, fetch comments for the post
            comment_limit: Maximum comments to fetch (default: 10)
            use_proxy: Whether to use proxy, default True

        Returns:
            Post object (with comments if with_comments=True)
        """
        url = "https://m.weibo.cn/statuses/show"
        params = {"id": bid}

        data = self._request(url, params, use_proxy=use_proxy)

        if not data.get("data"):
            raise ParseError(f"Post {bid} not found")

        post_data = self.parser._parse_single_post(data["data"])
        if not post_data:
            raise ParseError(f"Failed to parse post data {bid}")

        post = Post.from_dict(post_data)

        # Fetch comments if requested
        if with_comments:
            try:
                max_pages = max(1, (comment_limit + 9) // 10)
                comments = self.get_all_comments(
                    post.id, max_pages=max_pages, use_proxy=use_proxy
                )
                post.comments = comments[:comment_limit]
            except Exception as e:
                self.logger.warning(f"Failed to fetch comments: {e}")
                post.comments = []

        return post

    @rate_limit()
    def search_users(
        self, query: str, page: int = 1, count: int = 10, use_proxy: bool = True
    ) -> list[User]:
        """
        Search for users

        Args:
            query: Search keyword
            page: Page number
            count: Number of results per page
            use_proxy: Whether to use proxy, default True

        Returns:
            List of User objects
        """
        url = "https://m.weibo.cn/api/container/getIndex"
        params = {
            "containerid": f"100103type=3&q={query}",
            "page": page,
            "count": count,
        }

        data = self._request(url, params, use_proxy=use_proxy)
        users = []
        cards = data.get("data", {}).get("cards", [])

        for card in cards:
            if card.get("card_type") == 11:
                card_group = card.get("card_group", [])
                for group_card in card_group:
                    if group_card.get("card_type") == 10:
                        user_data = group_card.get("user", {})
                        if user_data:
                            users.append(User.from_dict(user_data))

        self.logger.info(f"Found {len(users)} users")
        return users

    @rate_limit()
    def search_posts(
        self,
        query: str,
        page: int = 1,
        with_comments: bool = False,
        comment_limit: int = 10,
        use_proxy: bool = True,
    ) -> tuple[list[Post], dict[str, Any]]:
        """
        Search for posts

        Args:
            query: Search keyword
            page: Page number
            with_comments: If True, fetch comments for each post
            comment_limit: Maximum comments per post (default: 10)
            use_proxy: Whether to use proxy, default True

        Returns:
            Tuple of (List of Post objects, pagination info dict)
            Pagination info contains:
            - page: next page number (None if last page)
            - has_more: whether there are more pages
        """
        url = "https://m.weibo.cn/api/container/getIndex"
        params = {"containerid": f"100103type=1&q={query}", "page": page}

        data = self._request(url, params, use_proxy=use_proxy)
        posts_data, pagination = self.parser.parse_posts(data)
        posts = [Post.from_dict(post_data) for post_data in posts_data]

        # Fetch comments if requested
        if with_comments and posts:
            posts = self._fetch_comments_for_posts(
                posts, comment_limit=comment_limit, use_proxy=use_proxy
            )

        self.logger.info(
            f"Found {len(posts)} posts (has_more: {pagination.get('has_more', False)})"
        )
        return posts, pagination

    def search_posts_by_count(
        self,
        query: str,
        count: int,
        max_pages: int = 50,
        with_comments: bool = False,
        comment_limit: int = 10,
        use_proxy: bool = True,
    ) -> list[Post]:
        """
        Search for posts by keyword with automatic pagination until
        reaching specified count

        Args:
            query: Search keyword
            count: Desired number of posts to retrieve
            max_pages: Maximum number of pages to fetch (safety limit),
                default 50
            with_comments: If True, fetch comments for each post
            comment_limit: Maximum comments per post (default: 10)
            use_proxy: Whether to use proxy, default True

        Returns:
            List of Post objects (may be fewer than count if no more
            results available)
        """
        all_posts = []
        page = 1

        self.logger.info(
            f"Starting search for '{query}', target count: {count}, "
            f"max pages: {max_pages}"
        )

        while len(all_posts) < count and page <= max_pages:
            try:
                posts, pagination = self.search_posts(
                    query,
                    page=page,
                    with_comments=with_comments,
                    comment_limit=comment_limit,
                    use_proxy=use_proxy,
                )

                if not posts:
                    self.logger.info(
                        f"No more posts found at page {page}, stopping pagination"
                    )
                    break

                all_posts.extend(posts)
                self.logger.info(
                    f"Page {page}: fetched {len(posts)} posts, "
                    f"total: {len(all_posts)}/{count}"
                )

                if len(all_posts) >= count:
                    break

                # Check if there are more pages using pagination info
                if not pagination.get("has_more", False):
                    self.logger.info(
                        "Reached last page (cardlistInfo.page is None), stopping"
                    )
                    break

                page += 1

            except Exception as e:
                self.logger.error(f"Error fetching page {page}: {e}")
                break

        result = all_posts[:count]
        self.logger.info(
            f"Search completed for '{query}': returned {len(result)} posts "
            f"(fetched {len(all_posts)} total from {page} pages)"
        )

        return result

    def search_all_posts(
        self,
        query: str,
        max_pages: Optional[int] = None,
        with_comments: bool = False,
        comment_limit: int = 10,
        use_proxy: bool = True,
    ) -> list[Post]:
        """
        Search for all posts by keyword with automatic pagination until
        reaching the last page (detected by cardlistInfo.page being None)

        Args:
            query: Search keyword
            max_pages: Maximum number of pages to fetch (safety limit),
                None for unlimited
            with_comments: If True, fetch comments for each post
            comment_limit: Maximum comments per post (default: 10)
            use_proxy: Whether to use proxy, default True

        Returns:
            List of all available Post objects
        """
        all_posts = []
        page = 1

        self.logger.info(
            f"Starting search for all posts matching '{query}'"
            + (f", max pages: {max_pages}" if max_pages else " (no limit)")
        )

        while True:
            if max_pages and page > max_pages:
                self.logger.info(f"Reached max pages limit ({max_pages}), stopping")
                break

            try:
                posts, pagination = self.search_posts(
                    query,
                    page=page,
                    with_comments=with_comments,
                    comment_limit=comment_limit,
                    use_proxy=use_proxy,
                )

                if not posts:
                    self.logger.info(
                        f"No more posts found at page {page}, stopping pagination"
                    )
                    break

                all_posts.extend(posts)
                self.logger.info(
                    f"Page {page}: fetched {len(posts)} posts, total: {len(all_posts)}"
                )

                # Check if there are more pages using pagination info
                if not pagination.get("has_more", False):
                    self.logger.info(
                        "Reached last page (cardlistInfo.page is None), stopping"
                    )
                    break

                page += 1

            except Exception as e:
                self.logger.error(f"Error fetching page {page}: {e}")
                break

        self.logger.info(
            f"Search completed for '{query}': fetched {len(all_posts)} posts "
            f"from {page} pages"
        )

        return all_posts

    def download_post_images(
        self,
        post: Post,
        download_dir: Optional[str] = None,
        subdir: Optional[str] = None,
    ) -> dict[str, Optional[str]]:
        """
        Download images from a single post

        Args:
            post: Post object containing image URLs
            download_dir: Custom download directory (optional)
            subdir: Subdirectory name for organizing downloads

        Returns:
            Dictionary mapping image URLs to downloaded file paths
        """
        if download_dir:
            self.downloader.download_dir = Path(download_dir)
            self.downloader.download_dir.mkdir(parents=True, exist_ok=True)

        if not post.pic_urls:
            self.logger.info(f"Post {post.id} has no images to download")
            return {}

        return self.downloader.download_post_images(post.pic_urls, post.id, subdir)

    def download_posts_images(
        self,
        posts: list[Post],
        download_dir: Optional[str] = None,
        subdir: Optional[str] = None,
    ) -> dict[str, dict[str, Optional[str]]]:
        """
        Download images from multiple posts

        Args:
            posts: List of Post objects
            download_dir: Custom download directory (optional)
            subdir: Subdirectory name for organizing downloads

        Returns:
            Dictionary mapping post IDs to their download results
        """
        if download_dir:
            self.downloader.download_dir = Path(download_dir)
            self.downloader.download_dir.mkdir(parents=True, exist_ok=True)

        posts_with_images = [post for post in posts if post.pic_urls]
        if not posts_with_images:
            self.logger.info("No posts with images found")
            return {}

        self.logger.info(
            f"Found {len(posts_with_images)} posts with images "
            f"out of {len(posts)} total posts"
        )
        return self.downloader.download_posts_images(posts_with_images, subdir)

    def download_user_posts_images(
        self,
        uid: str,
        pages: int = 1,
        download_dir: Optional[str] = None,
        expand_long_text: bool = False,
    ) -> dict[str, dict[str, Optional[str]]]:
        """
        Download images from user's posts

        Args:
            uid: User ID
            pages: Number of pages to fetch
            download_dir: Custom download directory (optional)
            expand_long_text: Whether to expand long text posts

        Returns:
            Dictionary mapping post IDs to their download results
        """
        all_posts = []

        for page in range(1, pages + 1):
            posts = self.get_user_posts(uid, page=page, expand=expand_long_text)
            if not posts:
                break
            all_posts.extend(posts)

        subdir = f"user_{uid}"

        return self.download_posts_images(all_posts, download_dir, subdir)

    @rate_limit()
    def get_comments(
        self,
        post_id: str,
        page: int = 1,
        use_proxy: bool = True,
    ) -> tuple[list[Comment], dict[str, int]]:
        """
        Get comments for a specific post

        Args:
            post_id: Post ID (numeric ID, not bid)
            page: Page number
            use_proxy: Whether to use proxy, default True

        Returns:
            Tuple of (List of Comment objects, pagination info dict with
            total_number and max fields)
        """
        url = "https://m.weibo.cn/api/comments/show"
        params = {"id": post_id, "page": page}

        data = self._request(url, params, use_proxy=use_proxy)

        if not data.get("data"):
            return [], {"total_number": 0, "max": 0}

        comments_data, pagination = self.parser.parse_comments(data)
        comments = [Comment.from_dict(comment_data) for comment_data in comments_data]

        self.logger.info(
            f"Fetched {len(comments)} comments for post {post_id} "
            f"(page {page}, total: {pagination.get('total_number', 0)})"
        )
        return comments, pagination

    def get_all_comments(
        self,
        post_id: str,
        max_pages: Optional[int] = None,
        use_proxy: bool = True,
    ) -> list[Comment]:
        """
        Get all comments for a specific post with automatic pagination

        Args:
            post_id: Post ID (numeric ID, not bid)
            max_pages: Maximum number of pages to fetch (None for all pages)
            use_proxy: Whether to use proxy, default True

        Returns:
            List of all Comment objects
        """
        all_comments = []
        page = 1
        pages_fetched = 0

        self.logger.info(
            f"Starting to fetch all comments for post {post_id}"
            + (f", max pages: {max_pages}" if max_pages else "")
        )

        while True:
            if max_pages and page > max_pages:
                self.logger.info(f"Reached max pages limit ({max_pages}), stopping")
                break

            try:
                comments, pagination = self.get_comments(
                    post_id, page=page, use_proxy=use_proxy
                )

                if not comments:
                    self.logger.info(f"No more comments at page {page}, stopping")
                    break

                all_comments.extend(comments)
                pages_fetched += 1

                max_page = pagination.get("max", 0)
                if max_page > 0 and page >= max_page:
                    self.logger.info(f"Reached last page ({max_page}), stopping")
                    break

                page += 1

            except Exception as e:
                self.logger.error(f"Error fetching page {page}: {e}")
                break

        self.logger.info(
            f"Fetched total {len(all_comments)} comments from {pages_fetched} pages"
        )
        return all_comments

    def _fetch_comments_for_posts(
        self,
        posts: list[Post],
        comment_limit: int = 10,
        use_proxy: bool = True,
    ) -> list[Post]:
        """
        Fetch comments for multiple posts sequentially

        Args:
            posts: List of Post objects to fetch comments for
            comment_limit: Maximum number of comments per post (default: 10)
            use_proxy: Whether to use proxy for requests

        Returns:
            Same list of Post objects with comments populated
        """
        if not posts:
            return posts

        # Calculate pages needed (10 comments per page)
        max_pages = max(1, (comment_limit + 9) // 10)

        self.logger.info(
            f"Fetching comments for {len(posts)} posts "
            f"(limit: {comment_limit} per post)"
        )

        successful_count = 0
        for i, post in enumerate(posts, 1):
            try:
                comments = self.get_all_comments(
                    post.id, max_pages=max_pages, use_proxy=use_proxy
                )
                post.comments = comments[:comment_limit]
                if post.comments:
                    successful_count += 1
                self.logger.debug(
                    f"[{i}/{len(posts)}] Fetched {len(post.comments)} comments "
                    f"for post {post.id}"
                )
            except Exception as e:
                self.logger.warning(
                    f"[{i}/{len(posts)}] Failed to fetch comments "
                    f"for post {post.id}: {e}"
                )
                post.comments = []

        self.logger.info(
            f"Comment fetching complete: {successful_count}/{len(posts)} "
            f"posts have comments"
        )

        return posts
