#!/usr/bin/env python

"""
Video Download Example - Demonstrates how to use crawl4weibo to download Weibo videos
"""

from crawl4weibo import WeiboClient


def main():
    """Demonstrates video download functionality"""

    client = WeiboClient()
    test_uid = "2656274875"

    print("=== Weibo Video Download Functionality Demo ===\n")

    # Example 1: Download video from a single post
    print("1. Download video from a single post")
    try:
        posts = client.get_user_posts(test_uid, page=1)
        video_post = next((p for p in posts if p.video_url), None)

        if video_post:
            print(f"Found video post: {video_post.id}")
            print(f"  Video URL: {video_post.video_url}")
            if video_post.video_urls:
                print(f"  Available qualities: {list(video_post.video_urls.keys())}")

            result = client.download_post_video(
                video_post,
                download_dir="./example_downloads",
                subdir="single_video",
            )

            if result:
                print(f"  Downloaded to: {result}")
            else:
                print("  Download failed")
        else:
            print("No video posts found on page 1")
    except Exception as e:
        print(f"Failed: {e}")

    print("\n" + "=" * 50 + "\n")

    # Example 2: Download videos from user's recent posts
    print("2. Batch download videos from user's posts")
    try:
        results = client.download_user_posts_videos(
            uid=test_uid,
            pages=2,
            download_dir="./example_downloads",
        )

        stats = client.video_downloader.get_download_stats(results)
        print("Download statistics:")
        print(f"  Total videos: {stats['total']}")
        print(f"  Successfully downloaded: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")
    except Exception as e:
        print(f"Failed: {e}")

    print("\n=== Demo completed ===")
    print("Downloaded videos are saved in the ./example_downloads/ directory")


if __name__ == "__main__":
    main()
