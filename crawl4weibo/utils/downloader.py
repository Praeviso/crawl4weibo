#!/usr/bin/env python

"""
Image downloader utilities for crawl4weibo
"""

import os
import random
import time
import urllib.parse
from pathlib import Path
from typing import Any

import requests

from ..exceptions.base import NetworkError
from .logger import get_logger
from .proxy import ProxyPool


class ImageDownloader:
    """Image downloader for Weibo posts"""

    def __init__(
        self,
        session: requests.Session | None = None,
        download_dir: str = "./images",
        max_retries: int = 3,
        delay_range: tuple[float, float] = (1.0, 3.0),
        proxy_pool: ProxyPool | None = None,
    ):
        """
        Initialize image downloader

        Args:
            session: Optional requests session to use
            download_dir: Directory to save downloaded images
            max_retries: Maximum number of retry attempts
            delay_range: Random delay range between downloads (min, max) in seconds
            proxy_pool: Optional proxy pool for downloading images
        """
        self.logger = get_logger()
        self.session = session or requests.Session()
        self.download_dir = Path(download_dir)
        self.max_retries = max_retries
        self.delay_range = delay_range
        self.proxy_pool = proxy_pool

        if (
            not hasattr(self.session, "headers")
            or "User-Agent" not in self.session.headers
        ):
            self.session.headers.update(
                {
                    "User-Agent": (
                        "Mozilla/5.0 (Linux; Android 13; SM-G9980) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/112.0.5615.135 Mobile Safari/537.36"
                    ),
                    "Referer": "https://m.weibo.cn/",
                }
            )

    def download_image(
        self,
        url: str,
        filename: str | None = None,
        subdir: str | None = None,
    ) -> str | None:
        """
        Download a single image

        Args:
            url: Image URL to download
            filename: Optional custom filename
            subdir: Optional subdirectory name

        Returns:
            Path to downloaded file if successful, None otherwise
        """
        if not url:
            return None

        try:
            self.download_dir.mkdir(parents=True, exist_ok=True)

            if subdir:
                save_dir = self.download_dir / subdir
                save_dir.mkdir(parents=True, exist_ok=True)
            else:
                save_dir = self.download_dir

            if not filename:
                filename = self._generate_filename(url)

            save_path = save_dir / filename

            if save_path.exists():
                self.logger.info(f"Image already exists: {save_path}")
                return str(save_path)

            for attempt in range(1, self.max_retries + 1):
                try:
                    # Get proxy if available
                    proxies = None
                    using_proxy = False
                    if self.proxy_pool and self.proxy_pool.is_enabled():
                        proxies = self.proxy_pool.get_proxy()
                        if proxies:
                            using_proxy = True
                            self.logger.debug(
                                f"Downloading with proxy: {proxies.get('http', 'N/A')}"
                            )

                    response = self.session.get(
                        url, timeout=30, stream=True, proxies=proxies
                    )
                    response.raise_for_status()

                    content_type = response.headers.get("content-type", "")
                    if not content_type.startswith("image/"):
                        self.logger.warning(f"URL does not return image content: {url}")
                        return None

                    with open(save_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    self.logger.info(f"Downloaded: {save_path}")
                    return str(save_path)

                except requests.exceptions.RequestException as e:
                    if attempt < self.max_retries:
                        # When using proxy, wait shorter time for faster retry on
                        # network instability
                        if using_proxy:
                            delay = random.uniform(0.5, 1.5)
                        else:
                            delay = random.uniform(2, 5)
                        self.logger.warning(
                            f"Download failed (attempt {attempt}), "
                            f"retrying in {delay:.1f}s: {e}"
                        )
                        time.sleep(delay)
                    else:
                        self.logger.error(
                            f"Failed to download {url} after "
                            f"{self.max_retries} attempts: {e}"
                        )
                        raise NetworkError(f"Failed to download image: {e}")

            return None

        except NetworkError:
            raise
        except Exception as e:
            self.logger.error(f"Error downloading image {url}: {e}")
            return None

    def download_post_images(
        self,
        pic_urls: list[str],
        post_id: str,
        subdir: str | None = None,
    ) -> dict[str, str | None]:
        """
        Download all images from a post

        Args:
            pic_urls: List of image URLs
            post_id: Post ID for organizing files
            subdir: Optional subdirectory name

        Returns:
            Dictionary mapping URLs to downloaded file paths
        """
        if not pic_urls:
            return {}

        results = {}
        post_subdir = f"{subdir}/{post_id}" if subdir else post_id

        self.logger.info(f"Downloading {len(pic_urls)} images for post {post_id}")

        for i, url in enumerate(pic_urls):
            if i > 0:
                delay = random.uniform(*self.delay_range)
                time.sleep(delay)

            filename = f"{post_id}_{i + 1:02d}_{self._generate_filename(url)}"
            try:
                downloaded_path = self.download_image(url, filename, post_subdir)
                results[url] = downloaded_path
            except NetworkError as e:
                self.logger.warning(f"Network error downloading {url}: {e}")
                results[url] = None

        successful_downloads = sum(1 for path in results.values() if path is not None)
        self.logger.info(
            f"Downloaded {successful_downloads}/{len(pic_urls)} "
            f"images for post {post_id}"
        )

        return results

    def download_posts_images(
        self,
        posts: list[Any],
        subdir: str | None = None,
    ) -> dict[str, dict[str, str | None]]:
        """
        Download images from multiple posts

        Args:
            posts: List of Post objects
            subdir: Optional subdirectory name

        Returns:
            Dictionary mapping post IDs to download results
        """
        if not posts:
            return {}

        results = {}
        total_images = sum(
            len(post.pic_urls) for post in posts if hasattr(post, "pic_urls")
        )

        self.logger.info(
            f"Starting batch download for {len(posts)} posts "
            f"({total_images} total images)"
        )

        for i, post in enumerate(posts):
            if not hasattr(post, "pic_urls") or not post.pic_urls:
                continue

            if i > 0:
                delay = random.uniform(*self.delay_range)
                time.sleep(delay)

            post_id = getattr(post, "id", f"post_{i}")
            results[post_id] = self.download_post_images(post.pic_urls, post_id, subdir)

        total_downloaded = sum(
            sum(1 for path in post_results.values() if path is not None)
            for post_results in results.values()
        )
        self.logger.info(
            f"Batch download completed: {total_downloaded}/{total_images} "
            f"images downloaded"
        )

        return results

    def _generate_filename(self, url: str) -> str:
        """Generate filename from URL"""
        parsed_url = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed_url.path)

        if not filename or "." not in filename:
            filename = f"image_{hash(url) % 1000000}.jpg"

        return filename

    def get_download_stats(self, download_results: dict[str, Any]) -> dict[str, int]:
        """
        Get statistics from download results

        Args:
            download_results: Results from download operations

        Returns:
            Dictionary with download statistics
        """
        stats = {
            "total_urls": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "already_existed": 0,
        }

        def count_results(results):
            if isinstance(results, dict):
                for value in results.values():
                    if isinstance(value, dict):
                        count_results(value)
                    elif isinstance(value, str):
                        stats["successful_downloads"] += 1
                        stats["total_urls"] += 1
                    elif value is None:
                        stats["failed_downloads"] += 1
                        stats["total_urls"] += 1

        count_results(download_results)
        return stats


class VideoDownloader:
    """Video downloader for Weibo posts"""

    VALID_CONTENT_TYPES = ("video/", "application/octet-stream")
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 13; SM-G9980) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/112.0.5615.135 Mobile Safari/537.36"
        ),
        "Referer": "https://m.weibo.cn/",
    }

    def __init__(
        self,
        session: requests.Session | None = None,
        download_dir: str = "./videos",
        max_retries: int = 3,
        delay_range: tuple[float, float] = (1.0, 3.0),
        proxy_pool: ProxyPool | None = None,
        chunk_size: int = 65536,
    ):
        """
        Initialize video downloader

        Args:
            session: Optional requests session to use
            download_dir: Directory to save downloaded videos
            max_retries: Maximum number of retry attempts
            delay_range: Random delay range between downloads (min, max) in seconds
            proxy_pool: Optional proxy pool for downloading videos
            chunk_size: Chunk size for streaming downloads in bytes
        """
        self.logger = get_logger()
        self.session = session or requests.Session()
        self.download_dir = Path(download_dir)
        self.max_retries = max_retries
        self.delay_range = delay_range
        self.proxy_pool = proxy_pool
        self.chunk_size = chunk_size

        if session is None:
            self.session.headers.update(self.DEFAULT_HEADERS)

    def download_video(
        self,
        url: str,
        filename: str | None = None,
        subdir: str | None = None,
    ) -> str | None:
        """
        Download a single video

        Args:
            url: Video URL to download
            filename: Optional custom filename
            subdir: Optional subdirectory name

        Returns:
            Path to downloaded file if successful, None otherwise
        """
        if not url:
            return None

        try:
            self.download_dir.mkdir(parents=True, exist_ok=True)

            if subdir:
                save_dir = self.download_dir / subdir
                save_dir.mkdir(parents=True, exist_ok=True)
            else:
                save_dir = self.download_dir

            if not filename:
                filename = self._generate_filename(url)

            save_path = save_dir / filename

            if save_path.exists():
                self.logger.info(f"Video already exists: {save_path}")
                return str(save_path)

            for attempt in range(1, self.max_retries + 1):
                try:
                    proxies = None
                    using_proxy = False
                    if self.proxy_pool and self.proxy_pool.is_enabled():
                        proxies = self.proxy_pool.get_proxy()
                        if proxies:
                            using_proxy = True
                            self.logger.debug(
                                f"Downloading with proxy: {proxies.get('http', 'N/A')}"
                            )

                    with self.session.get(
                        url, timeout=60, stream=True, proxies=proxies
                    ) as response:
                        response.raise_for_status()

                        content_type = response.headers.get("content-type", "")
                        if not any(
                            content_type.startswith(ct)
                            for ct in self.VALID_CONTENT_TYPES
                        ):
                            self.logger.warning(
                                f"URL does not return video content "
                                f"(got {content_type}): {url}"
                            )
                            return None

                        with open(save_path, "wb") as f:
                            for chunk in response.iter_content(
                                chunk_size=self.chunk_size
                            ):
                                if chunk:
                                    f.write(chunk)

                    self.logger.info(f"Downloaded video: {save_path}")
                    return str(save_path)

                except requests.exceptions.RequestException as e:
                    # Remove partial file to avoid false "already exists"
                    if save_path.exists():
                        try:
                            save_path.unlink()
                        except OSError as cleanup_err:
                            self.logger.warning(
                                f"Failed to remove incomplete file "
                                f"{save_path}: {cleanup_err}"
                            )

                    if attempt < self.max_retries:
                        if using_proxy:
                            delay = random.uniform(0.5, 1.5)
                        else:
                            delay = random.uniform(2, 5)
                        self.logger.warning(
                            f"Video download failed (attempt {attempt}), "
                            f"retrying in {delay:.1f}s: {e}"
                        )
                        time.sleep(delay)
                    else:
                        self.logger.error(
                            f"Failed to download video {url} after "
                            f"{self.max_retries} attempts: {e}"
                        )
                        raise NetworkError(f"Failed to download video: {e}")

            return None

        except NetworkError:
            raise
        except Exception as e:
            self.logger.error(f"Error downloading video {url}: {e}")
            return None

    def download_post_video(
        self,
        post: Any,
        subdir: str | None = None,
    ) -> str | None:
        """
        Download video from a single post

        Args:
            post: Post object with video_url attribute
            subdir: Optional subdirectory name

        Returns:
            Path to downloaded file if successful, None otherwise
        """
        video_url = getattr(post, "video_url", "")
        if not video_url:
            return None

        post_id = getattr(post, "id", "unknown")
        filename = f"{post_id}_{self._generate_filename(video_url)}"

        try:
            return self.download_video(video_url, filename, subdir)
        except NetworkError as e:
            self.logger.warning(
                f"Network error downloading video for post {post_id}: {e}"
            )
            return None

    def download_posts_videos(
        self,
        posts: list[Any],
        subdir: str | None = None,
    ) -> dict[str, str | None]:
        """
        Download videos from multiple posts

        Args:
            posts: List of Post objects
            subdir: Optional subdirectory name

        Returns:
            Dictionary mapping post IDs to downloaded file paths
        """
        if not posts:
            return {}

        results: dict[str, str | None] = {}
        video_posts = [p for p in posts if getattr(p, "video_url", "")]

        self.logger.info(
            f"Starting batch video download for {len(video_posts)} posts "
            f"with videos (out of {len(posts)} total)"
        )

        for i, post in enumerate(video_posts):
            if i > 0:
                delay = random.uniform(*self.delay_range)
                time.sleep(delay)

            post_id = getattr(post, "id", f"post_{i}")
            results[post_id] = self.download_post_video(post, subdir)

        successful = sum(1 for path in results.values() if path is not None)
        self.logger.info(
            f"Batch video download completed: {successful}/{len(video_posts)} "
            f"videos downloaded"
        )

        return results

    def _generate_filename(self, url: str) -> str:
        """Generate filename from URL"""
        parsed_url = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed_url.path)

        if not filename or "." not in filename:
            filename = f"video_{hash(url) % 1000000}.mp4"

        return filename

    def get_download_stats(
        self, download_results: dict[str, str | None]
    ) -> dict[str, int]:
        """
        Get statistics from download results

        Args:
            download_results: Results from download_posts_videos

        Returns:
            Dictionary with download statistics
        """
        stats = {
            "total": len(download_results),
            "successful": sum(1 for v in download_results.values() if v is not None),
            "failed": sum(1 for v in download_results.values() if v is None),
        }
        return stats
