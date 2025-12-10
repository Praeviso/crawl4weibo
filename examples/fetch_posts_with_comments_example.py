#!/usr/bin/env python

"""
Example: Fetch posts with comments

Demonstrates the with_comments feature that allows fetching
posts and their comments in one operation.
"""

from crawl4weibo import WeiboClient


def main():
    # Initialize client with browser-based cookie fetching
    client = WeiboClient()

    print("Example 1: Get user posts with comments")
    print("=" * 60)

    # Fetch user posts with top 10 comments per post
    posts = client.get_user_posts(
        "2656274875", page=1, with_comments=True, comment_limit=10
    )

    print(f"Fetched {len(posts)} posts\n")

    for i, post in enumerate(posts[:3], 1):
        print(f"{i}. Post: {post.text[:50]}...")
        print(f"   Likes: {post.attitudes_count} | Comments: {post.comments_count}")
        print(f"   Fetched {len(post.comments)} comments:")

        for j, comment in enumerate(post.comments[:3], 1):
            print(f"     {j}. {comment.user_screen_name}: {comment.text[:40]}...")

        if len(post.comments) > 3:
            print(f"     ... and {len(post.comments) - 3} more comments")
        print()

    print("\nExample 2: Search posts with comments")
    print("=" * 60)

    # Search posts and get top 20 comments per post
    posts, pagination = client.search_posts(
        "人工智能", page=1, with_comments=True, comment_limit=20
    )

    print(f"Found {len(posts)} posts matching '人工智能'\n")

    posts_with_comments = [p for p in posts if p.comments]
    print(f"{len(posts_with_comments)} posts have comments")

    if posts_with_comments:
        post = posts_with_comments[0]
        print(f"\nTop post: {post.text[:60]}...")
        print(f"Comments ({len(post.comments)}):")
        for comment in post.comments[:5]:
            print(f"  - {comment.user_screen_name}: {comment.text[:50]}...")

    print("\nExample 3: Get single post with all its comments")
    print("=" * 60)

    if posts:
        # Get full details of first post with up to 50 comments
        detailed_post = client.get_post_by_bid(
            posts[0].bid, with_comments=True, comment_limit=50
        )

        print(f"Post: {detailed_post.text[:60]}...")
        print(f"Total comments on Weibo: {detailed_post.comments_count}")
        print(f"Fetched comments: {len(detailed_post.comments)}")


if __name__ == "__main__":
    main()
