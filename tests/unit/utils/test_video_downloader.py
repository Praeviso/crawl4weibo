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
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
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
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
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
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
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
            "stream_hd": "https://example.com/stream_hd.mp4",
            "sd": "https://example.com/sd.mp4",
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


@pytest.mark.unit
class TestVideoDownloaderEdgeCases:
    """Tests for edge cases and uncovered paths in VideoDownloader"""

    @patch("requests.Session.get")
    def test_download_video_with_subdir(self, mock_get):
        """Test download creates subdirectory correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(download_dir=temp_dir)

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "video/mp4"}
            mock_response.iter_content.return_value = [b"fake_video_data"]
            mock_response.raise_for_status.return_value = None
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_get.return_value = mock_response

            result = downloader.download_video(
                "https://example.com/test.mp4", "test.mp4", subdir="my_sub"
            )

            assert result is not None
            assert "my_sub" in result
            assert Path(result).exists()

    def test_download_video_already_exists(self):
        """Test download skips when file already exists"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(download_dir=temp_dir)

            # Create a file that "already exists"
            existing = Path(temp_dir) / "existing.mp4"
            existing.write_bytes(b"existing content")

            result = downloader.download_video(
                "https://example.com/existing.mp4", "existing.mp4"
            )

            assert result == str(existing)

    def test_download_video_auto_generate_filename(self):
        """Test download auto-generates filename from URL"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(download_dir=temp_dir)

            with patch.object(downloader, "session") as mock_session:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.headers = {"content-type": "video/mp4"}
                mock_response.iter_content.return_value = [b"data"]
                mock_response.raise_for_status.return_value = None
                mock_response.__enter__ = Mock(return_value=mock_response)
                mock_response.__exit__ = Mock(return_value=False)
                mock_session.get.return_value = mock_response

                result = downloader.download_video("https://example.com/clip.mp4")

                assert result is not None
                assert "clip.mp4" in result

    @patch("requests.Session.get")
    def test_download_video_with_proxy(self, mock_get):
        """Test download uses proxy when available"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_pool = Mock()
            mock_pool.is_enabled.return_value = True
            mock_pool.get_proxy.return_value = {
                "http": "http://proxy:8080",
                "https": "http://proxy:8080",
            }

            downloader = VideoDownloader(
                download_dir=temp_dir, proxy_pool=mock_pool
            )

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "video/mp4"}
            mock_response.iter_content.return_value = [b"data"]
            mock_response.raise_for_status.return_value = None
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_get.return_value = mock_response

            result = downloader.download_video(
                "https://example.com/test.mp4", "test.mp4"
            )

            assert result is not None
            call_kwargs = mock_get.call_args
            assert call_kwargs.kwargs.get("proxies") is not None

    @patch("requests.Session.get")
    def test_download_video_retry_cleans_partial_file(self, mock_get):
        """Test that partial files are cleaned up on failure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(
                download_dir=temp_dir, max_retries=2
            )

            call_count = 0

            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call: write partial file then fail
                    partial = Path(temp_dir) / "test.mp4"
                    partial.write_bytes(b"partial")
                    raise requests.exceptions.ConnectionError("broken")
                # Second call: succeed
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_resp.headers = {"content-type": "video/mp4"}
                mock_resp.iter_content.return_value = [b"complete_data"]
                mock_resp.raise_for_status.return_value = None
                mock_resp.__enter__ = Mock(return_value=mock_resp)
                mock_resp.__exit__ = Mock(return_value=False)
                return mock_resp

            mock_get.side_effect = side_effect

            result = downloader.download_video(
                "https://example.com/test.mp4", "test.mp4"
            )

            assert result is not None
            assert Path(result).read_bytes() == b"complete_data"

    @patch("requests.Session.get")
    def test_download_video_retry_with_proxy_uses_short_delay(self, mock_get):
        """Test retry delay is shorter when using proxy"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_pool = Mock()
            mock_pool.is_enabled.return_value = True
            mock_pool.get_proxy.return_value = {"http": "http://p:8080"}

            downloader = VideoDownloader(
                download_dir=temp_dir, max_retries=2, proxy_pool=mock_pool
            )

            mock_get.side_effect = [
                requests.exceptions.ConnectionError("fail1"),
                # Second call succeeds
                Mock(
                    status_code=200,
                    headers={"content-type": "video/mp4"},
                    iter_content=Mock(return_value=[b"data"]),
                    raise_for_status=Mock(return_value=None),
                    __enter__=Mock(
                        return_value=Mock(
                            status_code=200,
                            headers={"content-type": "video/mp4"},
                            iter_content=Mock(return_value=[b"data"]),
                            raise_for_status=Mock(return_value=None),
                        )
                    ),
                    __exit__=Mock(return_value=False),
                ),
            ]

            with patch("crawl4weibo.utils.downloader.time.sleep") as mock_sleep:
                result = downloader.download_video(
                    "https://example.com/test.mp4", "test.mp4"
                )

                # Should use proxy delay range (0.5-1.5)
                if mock_sleep.called:
                    delay = mock_sleep.call_args[0][0]
                    assert 0.5 <= delay <= 1.5

    def test_download_post_video_network_error_handled(self):
        """Test download_post_video catches NetworkError gracefully"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(download_dir=temp_dir)

            post = Post(
                id="999",
                bid="bid999",
                user_id="u1",
                video_url="https://example.com/video.mp4",
            )

            with patch.object(
                downloader, "download_video", side_effect=NetworkError("fail")
            ):
                result = downloader.download_post_video(post)
                assert result is None


@pytest.mark.unit
class TestWeiboClientVideoDownload:
    """Tests for WeiboClient video download methods"""

    def test_download_post_video_with_video(self, client_no_rate_limit):
        """Test client download_post_video delegates to video_downloader"""
        post = Post(
            id="100",
            bid="bid100",
            user_id="u1",
            video_url="https://example.com/v.mp4",
        )

        with patch.object(
            client_no_rate_limit.video_downloader,
            "download_post_video",
            return_value="/tmp/100_v.mp4",
        ) as mock_dl:
            result = client_no_rate_limit.download_post_video(post)
            assert result == "/tmp/100_v.mp4"
            mock_dl.assert_called_once_with(post, None)

    def test_download_post_video_no_video(self, client_no_rate_limit):
        """Test client download_post_video returns None when no video"""
        post = Post(id="101", bid="bid101", user_id="u1", video_url="")

        result = client_no_rate_limit.download_post_video(post)
        assert result is None

    def test_download_post_video_custom_dir(self, client_no_rate_limit):
        """Test client download_post_video with custom download_dir"""
        post = Post(
            id="102",
            bid="bid102",
            user_id="u1",
            video_url="https://example.com/v.mp4",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(
                client_no_rate_limit.video_downloader,
                "download_post_video",
                return_value=f"{temp_dir}/v.mp4",
            ):
                result = client_no_rate_limit.download_post_video(
                    post, download_dir=temp_dir
                )
                assert result is not None
                assert client_no_rate_limit.video_downloader.download_dir == Path(
                    temp_dir
                )

    def test_download_posts_videos(self, client_no_rate_limit):
        """Test client download_posts_videos filters and delegates"""
        posts = [
            Post(
                id="1", bid="b1", user_id="u1",
                video_url="https://example.com/v1.mp4",
            ),
            Post(id="2", bid="b2", user_id="u2", video_url=""),
            Post(
                id="3", bid="b3", user_id="u3",
                video_url="https://example.com/v3.mp4",
            ),
        ]

        with patch.object(
            client_no_rate_limit.video_downloader,
            "download_posts_videos",
            return_value={"1": "/tmp/v1.mp4", "3": "/tmp/v3.mp4"},
        ) as mock_dl:
            result = client_no_rate_limit.download_posts_videos(posts)
            assert len(result) == 2
            # Should only pass posts with video_url
            called_posts = mock_dl.call_args[0][0]
            assert len(called_posts) == 2

    def test_download_posts_videos_none_with_video(self, client_no_rate_limit):
        """Test client download_posts_videos with no video posts"""
        posts = [
            Post(id="1", bid="b1", user_id="u1", video_url=""),
            Post(id="2", bid="b2", user_id="u2", video_url=""),
        ]

        result = client_no_rate_limit.download_posts_videos(posts)
        assert result == {}

    def test_download_posts_videos_custom_dir(self, client_no_rate_limit):
        """Test client download_posts_videos with custom download_dir"""
        posts = [
            Post(
                id="1", bid="b1", user_id="u1",
                video_url="https://example.com/v.mp4",
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(
                client_no_rate_limit.video_downloader,
                "download_posts_videos",
                return_value={"1": f"{temp_dir}/v.mp4"},
            ):
                client_no_rate_limit.download_posts_videos(
                    posts, download_dir=temp_dir
                )
                assert client_no_rate_limit.video_downloader.download_dir == Path(
                    temp_dir
                )

    def test_download_user_posts_videos(self, client_no_rate_limit):
        """Test client download_user_posts_videos fetches and delegates"""
        posts = [
            Post(
                id="1", bid="b1", user_id="u1",
                video_url="https://example.com/v.mp4",
            ),
        ]

        with patch.object(
            client_no_rate_limit, "get_user_posts", return_value=posts
        ) as mock_get:
            with patch.object(
                client_no_rate_limit,
                "download_posts_videos",
                return_value={"1": "/tmp/v.mp4"},
            ) as mock_dl:
                result = client_no_rate_limit.download_user_posts_videos(
                    "12345", pages=1
                )

                assert result == {"1": "/tmp/v.mp4"}
                mock_get.assert_called_once_with(
                    "12345", page=1, expand=False
                )
                mock_dl.assert_called_once()
                # Check subdir is user_{uid}
                call_args = mock_dl.call_args
                assert call_args[0][1] is None  # download_dir
                assert call_args[0][2] == "user_12345"  # subdir

    def test_download_user_posts_videos_multi_page(self, client_no_rate_limit):
        """Test client download_user_posts_videos with multiple pages"""
        page1 = [
            Post(
                id="1", bid="b1", user_id="u1",
                video_url="https://example.com/v1.mp4",
            ),
        ]
        page2 = [
            Post(
                id="2", bid="b2", user_id="u1",
                video_url="https://example.com/v2.mp4",
            ),
        ]

        with patch.object(
            client_no_rate_limit,
            "get_user_posts",
            side_effect=[page1, page2],
        ):
            with patch.object(
                client_no_rate_limit,
                "download_posts_videos",
                return_value={"1": "/v1.mp4", "2": "/v2.mp4"},
            ) as mock_dl:
                result = client_no_rate_limit.download_user_posts_videos(
                    "12345", pages=2
                )

                assert len(result) == 2
                # Should have collected posts from both pages
                called_posts = mock_dl.call_args[0][0]
                assert len(called_posts) == 2

    def test_download_user_posts_videos_empty_page_stops(
        self, client_no_rate_limit
    ):
        """Test pagination stops when an empty page is returned"""
        page1 = [
            Post(
                id="1", bid="b1", user_id="u1",
                video_url="https://example.com/v.mp4",
            ),
        ]

        with patch.object(
            client_no_rate_limit,
            "get_user_posts",
            side_effect=[page1, []],
        ) as mock_get:
            with patch.object(
                client_no_rate_limit,
                "download_posts_videos",
                return_value={"1": "/v.mp4"},
            ):
                client_no_rate_limit.download_user_posts_videos(
                    "12345", pages=3
                )

                # Should stop after page 2 returns empty
                assert mock_get.call_count == 2
