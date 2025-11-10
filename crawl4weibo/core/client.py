#!/usr/bin/env python

"""
Weibo Crawler Client - Based on successfully tested code
"""

import random
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import requests

from ..exceptions.base import CrawlError, NetworkError, ParseError, UserNotFoundError
from ..models.post import Post
from ..models.user import User
from ..utils.downloader import ImageDownloader
from ..utils.logger import setup_logger
from ..utils.parser import WeiboParser
from ..utils.proxy import ProxyPool, ProxyPoolConfig


class WeiboClient:
    """Weibo Crawler Client"""

    def __init__(
        self,
        cookies: Optional[Union[str, Dict[str, str]]] = None,
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        user_agent: Optional[str] = None,
        proxy_api_url: Optional[str] = None,
        proxy_api_parser: Optional[Callable[[dict], str]] = None,
        dynamic_proxy_ttl: int = 300,
        proxy_pool_size: int = 10,
        proxy_fetch_strategy: str = "random",
    ):
        """
        Initialize Weibo client

        Args:
            cookies: Optional cookie string or dictionary
            log_level: Logging level
            log_file: Log file path
            user_agent: Optional User-Agent string
            proxy_api_url: Dynamic proxy API URL, e.g.
                'http://api.proxy.com/get?format=json'
            proxy_api_parser: Custom proxy API response parser function,
                receives JSON response and returns proxy URL string
            dynamic_proxy_ttl: Dynamic proxy expiration time (seconds),
                default 300 seconds (5 minutes)
            proxy_pool_size: Proxy pool capacity, default 10
            proxy_fetch_strategy: Proxy fetch strategy, 'random' or
                'round_robin', default random
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
        self.session.headers.update(
            {
                "User-Agent": user_agent or default_user_agent,
                "Referer": "https://m.weibo.cn/",
                "Accept": "application/json, text/plain, */*",
                "X-Requested-With": "XMLHttpRequest",
            }
        )

        if cookies:
            self._set_cookies(cookies)

        self._init_session()

        self.parser = WeiboParser()

        # Initialize proxy pool configuration and proxy pool
        proxy_config = ProxyPoolConfig(
            proxy_api_url=proxy_api_url,
            proxy_api_parser=proxy_api_parser,
            dynamic_proxy_ttl=dynamic_proxy_ttl,
            pool_size=proxy_pool_size,
            fetch_strategy=proxy_fetch_strategy,
        )
        self.proxy_pool = ProxyPool(config=proxy_config)

        # Initialize image downloader with proxy pool support
        self.downloader = ImageDownloader(
            session=self.session,
            download_dir="./weibo_images",
            proxy_pool=self.proxy_pool,
        )

        if proxy_api_url:
            self.logger.info(
                f"Proxy pool enabled (API: {proxy_api_url}, "
                f"Capacity: {proxy_pool_size}, TTL: {dynamic_proxy_ttl}s, "
                f"Strategy: {proxy_fetch_strategy})"
            )

        self.logger.info("WeiboClient initialized successfully")

    def _set_cookies(self, cookies: Union[str, Dict[str, str]]):
        if isinstance(cookies, str):
            cookie_dict = {}
            for pair in cookies.split(";"):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    cookie_dict[key.strip()] = value.strip()
            self.session.cookies.update(cookie_dict)
        elif isinstance(cookies, dict):
            self.session.cookies.update(cookies)

    def _init_session(self):
        try:
            self.logger.debug("Initializing session...")
            self.session.get("https://m.weibo.cn/", timeout=5)
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            self.logger.warning(f"Session initialization failed: {e}")

    def _request(
        self,
        url: str,
        params: Dict[str, Any],
        max_retries: int = 3,
        use_proxy: bool = True,
    ) -> Dict[str, Any]:
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
        for attempt in range(1, max_retries + 1):
            proxies = None
            using_proxy = False
            if use_proxy and self.proxy_pool and self.proxy_pool.is_enabled():
                proxies = self.proxy_pool.get_proxy()
                if proxies:
                    using_proxy = True
                    self.logger.debug(f"Using proxy: {proxies.get('http', 'N/A')}")
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
                    if attempt < max_retries:
                        # When using proxy, wait shorter time as dynamic proxy
                        # rarely gets IP banned, usually just network instability
                        if using_proxy:
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
                    # When using proxy, wait shorter time for faster retry on
                    # network instability
                    if using_proxy:
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

    def get_user_posts(
        self, uid: str, page: int = 1, expand: bool = False, use_proxy: bool = True
    ) -> List[Post]:
        """
        Get user's posts list

        Args:
            uid: User ID
            page: Page number
            expand: Whether to expand long text posts
            use_proxy: Whether to use proxy, default True

        Returns:
            List of Post objects
        """
        time.sleep(random.uniform(1, 3))

        url = "https://m.weibo.cn/api/container/getIndex"
        params = {"containerid": f"107603{uid}", "page": page}

        data = self._request(url, params, use_proxy=use_proxy)

        if not data.get("data"):
            return []

        posts_data = self.parser.parse_posts(data)
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

        self.logger.info(f"Fetched {len(posts)} posts")
        return posts

    def get_post_by_bid(self, bid: str, use_proxy: bool = True) -> Post:
        """
        Get post details by bid

        Args:
            bid: Post bid
            use_proxy: Whether to use proxy, default True

        Returns:
            Post object
        """
        url = "https://m.weibo.cn/statuses/show"
        params = {"id": bid}

        data = self._request(url, params, use_proxy=use_proxy)

        if not data.get("data"):
            raise ParseError(f"Post {bid} not found")

        post_data = self.parser._parse_single_post(data["data"])
        if not post_data:
            raise ParseError(f"Failed to parse post data {bid}")

        return Post.from_dict(post_data)

    def search_users(
        self, query: str, page: int = 1, count: int = 10, use_proxy: bool = True
    ) -> List[User]:
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
        time.sleep(random.uniform(1, 3))

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

    def search_posts(
        self, query: str, page: int = 1, use_proxy: bool = True
    ) -> List[Post]:
        """
        Search for posts

        Args:
            query: Search keyword
            page: Page number
            use_proxy: Whether to use proxy, default True

        Returns:
            List of Post objects
        """
        time.sleep(random.uniform(1, 3))

        url = "https://m.weibo.cn/api/container/getIndex"
        params = {"containerid": f"100103type=1&q={query}", "page": page}

        data = self._request(url, params, use_proxy=use_proxy)
        posts_data = self.parser.parse_posts(data)
        posts = [Post.from_dict(post_data) for post_data in posts_data]

        self.logger.info(f"Found {len(posts)} posts")
        return posts

    def search_posts_by_count(
        self, query: str, count: int, max_pages: int = 50, use_proxy: bool = True
    ) -> List[Post]:
        """
        Search for posts by keyword with automatic pagination until
        reaching specified count

        Args:
            query: Search keyword
            count: Desired number of posts to retrieve
            max_pages: Maximum number of pages to fetch (safety limit),
                default 50
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
                posts = self.search_posts(query, page=page, use_proxy=use_proxy)

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

                page += 1

                if page <= max_pages:
                    time.sleep(random.uniform(2, 4))

            except Exception as e:
                self.logger.error(f"Error fetching page {page}: {e}")
                break

        result = all_posts[:count]
        self.logger.info(
            f"Search completed for '{query}': returned {len(result)} posts "
            f"(fetched {len(all_posts)} total from {page} pages)"
        )

        return result

    def download_post_images(
        self,
        post: Post,
        download_dir: Optional[str] = None,
        subdir: Optional[str] = None,
    ) -> Dict[str, Optional[str]]:
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
        posts: List[Post],
        download_dir: Optional[str] = None,
        subdir: Optional[str] = None,
    ) -> Dict[str, Dict[str, Optional[str]]]:
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
    ) -> Dict[str, Dict[str, Optional[str]]]:
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

            if page < pages:
                time.sleep(random.uniform(2, 4))

        subdir = f"user_{uid}"

        return self.download_posts_images(all_posts, download_dir, subdir)
