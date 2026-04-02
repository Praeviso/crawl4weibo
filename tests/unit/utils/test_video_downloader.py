#!/usr/bin/env python

"""
Test cases for the video downloader functionality
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from crawl4weibo.exceptions.base import NetworkError
from crawl4weibo.models.post import Post
from crawl4weibo.utils.downloader import VideoDownloader
from crawl4weibo.utils.parser import WeiboParser


@pytest.mark.unit
class TestVideoDownloader:
    """Unit tests for VideoDownloader class"""

    def test_downloader_initialization(self):
        """Test downloader initializes correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(download_dir=temp_dir)
            assert downloader.download_dir == Path(temp_dir)
            assert downloader.max_retries == 3
            assert downloader.delay_range == (1.0, 3.0)
            assert downloader.chunk_size == 65536

    def test_generate_filename(self):
        """Test filename generation from URL"""
        downloader = VideoDownloader()

        url = "https://f.video.weibocdn.com/abc123.mp4?label=mp4_720p"
        filename = downloader._generate_filename(url)
        assert filename == "abc123.mp4"

        # URL without extension
        url = "https://example.com/video"
        filename = downloader._generate_filename(url)
        assert filename.startswith("video_")
        assert filename.endswith(".mp4")

    def test_default_session_uses_browser_headers(self):
        """Test standalone downloader sets browser headers on its own session."""
        downloader = VideoDownloader()

        assert downloader.session.headers["User-Agent"].startswith("Mozilla/5.0")
        assert downloader.session.headers["Referer"] == "https://m.weibo.cn/"

    @patch("requests.Session.get")
    def test_download_video_success(self, mock_get):
        """Test successful video download"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(download_dir=temp_dir)

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "video/mp4"}
            mock_response.iter_content.return_value = [b"fake_video_data"]
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            url = "https://example.com/test.mp4"
            result = downloader.download_video(url, "test.mp4")

            assert result is not None
            assert "test.mp4" in result
            assert Path(result).exists()

    @patch("requests.Session.get")
    def test_download_video_octet_stream_content(self, mock_get):
        """Test download with application/octet-stream content type"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(download_dir=temp_dir)

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/octet-stream"}
            mock_response.iter_content.return_value = [b"fake_video_data"]
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            url = "https://example.com/test.mp4"
            result = downloader.download_video(url, "test.mp4")

            assert result is not None

    @patch("requests.Session.get")
    def test_download_video_non_video_content(self, mock_get):
        """Test download with non-video content type"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(download_dir=temp_dir)

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/html"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            url = "https://example.com/notvideo.txt"
            result = downloader.download_video(url, "test.mp4")

            assert result is None

    @patch("requests.Session.get")
    def test_download_video_network_error(self, mock_get):
        """Test download with network error"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(download_dir=temp_dir, max_retries=1)

            mock_get.side_effect = requests.exceptions.RequestException("Network error")

            url = "https://example.com/test.mp4"

            with pytest.raises(NetworkError):
                downloader.download_video(url, "test.mp4")

    def test_download_video_empty_url(self):
        """Test download with empty URL"""
        downloader = VideoDownloader()
        result = downloader.download_video("")
        assert result is None

    def test_download_post_video(self):
        """Test downloading video from a post"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(download_dir=temp_dir)

            post = Post(
                id="12345",
                bid="bid1",
                user_id="user1",
                video_url="https://example.com/video.mp4",
            )

            with patch.object(downloader, "download_video") as mock_download:
                mock_download.return_value = f"{temp_dir}/12345_video.mp4"

                result = downloader.download_post_video(post)

                assert result is not None
                mock_download.assert_called_once()

    def test_download_post_video_no_video(self):
        """Test downloading video from post without video"""
        downloader = VideoDownloader()

        post = Post(id="12345", bid="bid1", user_id="user1", video_url="")

        result = downloader.download_post_video(post)
        assert result is None

    def test_download_posts_videos(self):
        """Test downloading videos from multiple posts"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(download_dir=temp_dir)

            post1 = Post(
                id="1",
                bid="bid1",
                user_id="user1",
                video_url="https://example.com/video1.mp4",
            )
            post2 = Post(
                id="2",
                bid="bid2",
                user_id="user2",
                video_url="https://example.com/video2.mp4",
            )
            post3 = Post(
                id="3",
                bid="bid3",
                user_id="user3",
                video_url="",  # no video
            )
            posts = [post1, post2, post3]

            with patch.object(downloader, "download_post_video") as mock_download:
                mock_download.return_value = f"{temp_dir}/video.mp4"

                results = downloader.download_posts_videos(posts)

                # Only post1 and post2 have videos
                assert len(results) == 2
                assert "1" in results
                assert "2" in results
                assert mock_download.call_count == 2

    def test_download_posts_videos_empty(self):
        """Test downloading videos from empty list"""
        downloader = VideoDownloader()
        results = downloader.download_posts_videos([])
        assert results == {}

    def test_get_download_stats(self):
        """Test getting download statistics"""
        downloader = VideoDownloader()

        results = {
            "post1": "/path/to/video1.mp4",
            "post2": None,
            "post3": "/path/to/video3.mp4",
        }

        stats = downloader.get_download_stats(results)

        assert stats["total"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1


@pytest.mark.unit
class TestVideoUrlExtraction:
    """Unit tests for video URL extraction in parser"""

    def test_extract_video_url_best_quality(self):
        """Test that _extract_video_url returns best quality URL"""
        parser = WeiboParser()

        mblog = {
            "page_info": {
                "type": "video",
                "media_info": {
                    "stream_url": "https://example.com/stream.mp4",
                    "stream_url_hd": "https://example.com/stream_hd.mp4",
                    "mp4_sd_url": "https://example.com/sd.mp4",
                    "mp4_720p_mp4": "https://example.com/720p.mp4",
                },
            }
        }

        result = parser._extract_video_url(mblog)
        assert result == "https://example.com/720p.mp4"

    def test_extract_video_url_fallback(self):
        """Test fallback when higher quality is not available"""
        parser = WeiboParser()

        mblog = {
            "page_info": {
                "type": "video",
                "media_info": {
                    "stream_url": "https://example.com/stream.mp4",
                },
            }
        }

        result = parser._extract_video_url(mblog)
        assert result == "https://example.com/stream.mp4"

    def test_extract_video_url_prefers_hd_stream_over_sd(self):
        """Test HD stream is preferred over SD when 720p is unavailable."""
        parser = WeiboParser()

        mblog = {
            "page_info": {
                "type": "video",
                "media_info": {
                    "stream_url_hd": "https://example.com/stream_hd.mp4",
                    "mp4_sd_url": "https://example.com/sd.mp4",
                    "stream_url": "https://example.com/stream.mp4",
                },
            }
        }

        result = parser._extract_video_url(mblog)
        assert result == "https://example.com/stream_hd.mp4"

    def test_extract_video_url_no_video(self):
        """Test extraction when post has no video"""
        parser = WeiboParser()

        mblog = {"page_info": {"type": "webpage"}}
        assert parser._extract_video_url(mblog) == ""

        mblog_no_page = {"text": "hello"}
        assert parser._extract_video_url(mblog_no_page) == ""

    def test_extract_video_urls_all_qualities(self):
        """Test extracting all quality URLs"""
        parser = WeiboParser()

        mblog = {
            "page_info": {
                "type": "video",
                "media_info": {
                    "stream_url": "https://example.com/stream.mp4",
                    "stream_url_hd": "https://example.com/stream_hd.mp4",
                    "mp4_sd_url": "https://example.com/sd.mp4",
                    "mp4_720p_mp4": "https://example.com/720p.mp4",
                },
            }
        }

        result = parser._extract_video_urls(mblog)
        assert result == {
            "720p": "https://example.com/720p.mp4",
            "sd": "https://example.com/sd.mp4",
            "stream_hd": "https://example.com/stream_hd.mp4",
            "stream": "https://example.com/stream.mp4",
        }

    def test_extract_video_urls_partial(self):
        """Test extracting URLs when only some qualities are available"""
        parser = WeiboParser()

        mblog = {
            "page_info": {
                "type": "video",
                "media_info": {
                    "stream_url": "https://example.com/stream.mp4",
                    "mp4_sd_url": "https://example.com/sd.mp4",
                },
            }
        }

        result = parser._extract_video_urls(mblog)
        assert len(result) == 2
        assert "sd" in result
        assert "stream" in result
        assert "720p" not in result

    def test_extract_video_urls_no_video(self):
        """Test extraction returns empty dict when no video"""
        parser = WeiboParser()

        assert parser._extract_video_urls({"text": "hello"}) == {}
        assert parser._extract_video_urls({"page_info": {"type": "webpage"}}) == {}
