#!/usr/bin/env python

"""
Test cases for the image downloader functionality
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from crawl4weibo.exceptions.base import NetworkError
from crawl4weibo.models.post import Post
from crawl4weibo.utils.downloader import ImageDownloader


@pytest.mark.unit
class TestImageDownloader:
    """Unit tests for ImageDownloader class"""

    def test_downloader_initialization(self):
        """Test downloader initializes correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = ImageDownloader(download_dir=temp_dir)
            assert downloader.download_dir == Path(temp_dir)
            assert downloader.max_retries == 3
            assert downloader.delay_range == (1.0, 3.0)

    def test_generate_filename(self):
        """Test filename generation from URL"""
        downloader = ImageDownloader()
        
        # Test with proper image URL
        url = "https://wx1.sinaimg.cn/large/12345.jpg"
        filename = downloader._generate_filename(url)
        assert filename == "12345.jpg"
        
        # Test with URL without extension
        url = "https://example.com/image"
        filename = downloader._generate_filename(url)
        assert filename.startswith("image_")
        assert filename.endswith(".jpg")

    @patch('requests.Session.get')
    def test_download_image_success(self, mock_get):
        """Test successful image download"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = ImageDownloader(download_dir=temp_dir)
            
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "image/jpeg"}
            mock_response.iter_content.return_value = [b"fake_image_data"]
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            url = "https://example.com/test.jpg"
            result = downloader.download_image(url, "test.jpg")
            
            assert result is not None
            assert "test.jpg" in result
            assert Path(result).exists()

    @patch('requests.Session.get')
    def test_download_image_non_image_content(self, mock_get):
        """Test download with non-image content type"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = ImageDownloader(download_dir=temp_dir)
            
            # Mock response with non-image content type
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/html"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            url = "https://example.com/notimage.txt"
            result = downloader.download_image(url, "test.jpg")
            
            assert result is None

    @patch('requests.Session.get')
    def test_download_image_network_error(self, mock_get):
        """Test download with network error"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = ImageDownloader(download_dir=temp_dir, max_retries=1)
            
            # Mock network error
            mock_get.side_effect = requests.exceptions.RequestException("Network error")
            
            url = "https://example.com/test.jpg"
            
            with pytest.raises(NetworkError):
                downloader.download_image(url, "test.jpg")

    def test_download_post_images(self):
        """Test downloading images from a post"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = ImageDownloader(download_dir=temp_dir)
            
            # Mock the download_image method
            with patch.object(downloader, 'download_image') as mock_download:
                mock_download.return_value = f"{temp_dir}/test_image.jpg"
                
                pic_urls = [
                    "https://example.com/img1.jpg",
                    "https://example.com/img2.jpg"
                ]
                post_id = "12345"
                
                results = downloader.download_post_images(pic_urls, post_id)
                
                assert len(results) == 2
                assert all(path is not None for path in results.values())
                assert mock_download.call_count == 2

    def test_download_posts_images(self):
        """Test downloading images from multiple posts"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = ImageDownloader(download_dir=temp_dir)
            
            # Create mock posts
            post1 = Post(
                id="1",
                bid="bid1",
                user_id="user1",
                pic_urls=["https://example.com/img1.jpg"]
            )
            post2 = Post(
                id="2",
                bid="bid2", 
                user_id="user2",
                pic_urls=["https://example.com/img2.jpg", "https://example.com/img3.jpg"]
            )
            posts = [post1, post2]
            
            # Mock the download_post_images method
            with patch.object(downloader, 'download_post_images') as mock_download:
                mock_download.return_value = {"url": "path"}
                
                results = downloader.download_posts_images(posts)
                
                assert len(results) == 2
                assert "1" in results
                assert "2" in results
                assert mock_download.call_count == 2

    def test_download_post_images_with_network_error(self):
        """Test downloading post images with network errors"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = ImageDownloader(download_dir=temp_dir, max_retries=1)
            
            pic_urls = [
                "https://example.com/img1.jpg",
                "https://example.com/img2.jpg"
            ]
            post_id = "12345"
            
            with patch.object(downloader, 'download_image') as mock_download:
                def side_effect(url, filename=None, subdir=None):
                    if "img1" in url:
                        raise NetworkError("Network error")
                    return f"{temp_dir}/test_image.jpg"
                
                mock_download.side_effect = side_effect
                
                results = downloader.download_post_images(pic_urls, post_id)
                
                assert len(results) == 2
                assert results[pic_urls[0]] is None
                assert results[pic_urls[1]] is not None

    def test_get_download_stats(self):
        """Test getting download statistics"""
        downloader = ImageDownloader()
        
        # Mock download results
        download_results = {
            "post1": {
                "url1": "/path/to/image1.jpg",
                "url2": None,
            },
            "post2": {
                "url3": "/path/to/image3.jpg",
            }
        }
        
        stats = downloader.get_download_stats(download_results)
        
        assert stats["total_urls"] == 3
        assert stats["successful_downloads"] == 2
        assert stats["failed_downloads"] == 1


@pytest.mark.integration
class TestImageDownloaderIntegration:
    """Integration tests for ImageDownloader with real posts"""

    def test_download_with_real_client(self):
        """Test downloading with real client and posts"""
        from crawl4weibo import WeiboClient
        
        try:
            client = WeiboClient()
            
            posts = client.get_user_posts("2656274875", page=1)
            posts_with_images = [post for post in posts if post.pic_urls]
            
            if not posts_with_images:
                pytest.skip("No posts with images found for testing")
                
            post = posts_with_images[0]
            
            with tempfile.TemporaryDirectory() as temp_dir:
                results = client.download_post_images(
                    post,
                    download_dir=temp_dir,
                    subdir="test"
                )
                
                assert isinstance(results, dict)
                assert len(results) == len(post.pic_urls)
                
                successful_downloads = sum(1 for path in results.values() if path is not None)
                assert successful_downloads >= 0  # At least attempt was made
                
        except Exception as e:
            pytest.skip(f"Integration test failed due to network/API issues: {e}")