#!/usr/bin/env python

"""
Crawl4Weibo Simple Usage Example
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crawl4weibo import WeiboClient


def main():
    print("Crawl4Weibo - Weibo Crawler")
    print("=" * 30)

    client = WeiboClient()

    test_uid = "2656274875"

    try:
        print("\nFetching user information...")
        user = client.get_user_by_uid(test_uid)
        print(f"Username: {user.screen_name}")
        print(f"Followers: {user.followers_count}")
        print(f"Posts: {user.posts_count}")

        print("\nFetching posts...")
        posts_page1 = client.get_user_posts(test_uid, page=1, expand=True)
        posts_page2 = client.get_user_posts(test_uid, page=2, expand=True)
        posts = (posts_page1 or []) + (posts_page2 or [])
        print(f"Retrieved {len(posts)} posts")

        for i, post in enumerate(posts[:3], 1):
            print(f"  {i}. {post.text[:50]}...")
            print(f"     Likes: {post.attitudes_count} | Comments: {post.comments_count}")

        if posts:
            print("\nFetching single post by ID...")
            first_post_bid = posts[0].bid
            print(f"Fetching post ID: {first_post_bid}")
            single_post = client.get_post_by_bid(first_post_bid)
            print(f"Content: {single_post.text[:50]}...")

        print("\nSearching users...")
        users = client.search_users("新浪")
        for user in users:
            print(f"  - {user.screen_name} (Followers: {user.followers_count})")

        print("\nSearching posts...")
        posts = client.search_posts_by_count("人工智能", count=40)
        for post in posts:
            print(f"  - {post.text[:50]}...")

        print("\nTest completed successfully!")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
