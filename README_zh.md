# Crawl4Weibo

**中文** | **[English](README.md)**

---

Crawl4Weibo 是一个开箱即用的微博爬虫 Python 库，模拟移动端请求、处理常见反爬策略，并返回结构化数据模型，适合数据采集、分析与监控场景。

## ✨ 特性
- **无需 Cookie 即可运行**：自动初始化 session 和移动端 UA
- **内置 432 防护处理**：指数退避重试，减少请求失败
- **支持动态和静态IP代理池统一管理**：可配置过期时间，支持轮询和自动清理
- **标准化的数据模型**：`User` 与 `Post` 数据模型，可递归访问转发内容
- **支持微博长文展开**：关键词搜索、用户列表抓取与批量分页
- **提供图像下载工具**：支持单条、批量和整页下载，并带重复文件检查
- **统一日志与错误类型**：便于快速定位网络、解析或鉴权问题

## 安装
```bash
pip install crawl4weibo
```
或使用更快的 `uv`：
```bash
uv pip install crawl4weibo
```

## 快速开始
```python
from crawl4weibo import WeiboClient

client = WeiboClient()
uid = "2656274875"

# 获取用户信息
user = client.get_user_by_uid(uid)
print(f"{user.screen_name} - 粉丝: {user.followers_count}")

# 获取用户微博（支持展开长文）
posts = client.get_user_posts(uid, page=1, expand=True)
for post in posts[:3]:
    print(f"{post.text[:50]}... - 点赞: {post.attitudes_count}")

# 搜索用户
users = client.search_users("新浪")
for user in users[:3]:
    print(f"{user.screen_name} - 粉丝: {user.followers_count}")

# 搜索微博
results = client.search_posts("人工智能", page=1)
print(f"找到 {len(results)} 条搜索结果")
```
更多示例请参考 [`examples/simple_example.py`](examples/simple_example.py)。

**运行示例：**
```bash
# 克隆仓库后运行
python examples/simple_example.py

# 或使用 uv
uv run python examples/simple_example.py
```

## 图片下载示例
```python
from crawl4weibo import WeiboClient

client = WeiboClient()

# 方式1: 下载单个帖子的图片
post = client.get_post_by_bid("Q6FyDtbQc")
if post.pic_urls:
    results = client.download_post_images(
        post,
        download_dir="./downloads",
        subdir="single_post"
    )
    print(f"成功下载 {sum(1 for p in results.values() if p)} 张图片")

# 方式2: 批量下载用户帖子的图片
posts = client.get_user_posts("2656274875", page=1)
results = client.download_posts_images(
    posts[:3],  # 下载前3个帖子的图片
    download_dir="./downloads"
)

# 方式3: 下载用户多页帖子的图片
results = client.download_user_posts_images(
    uid="2656274875",
    pages=2,  # 下载前2页
    download_dir="./downloads"
)
```
更多用法请参考 [`examples/download_images_example.py`](examples/download_images_example.py)。

**运行示例：**
```bash
python examples/download_images_example.py
```

## 代理池配置示例
```python
from crawl4weibo import WeiboClient, ProxyPoolConfig

# 方式1: 使用动态代理API（池化模式 - 默认）
proxy_config = ProxyPoolConfig(
    proxy_api_url="http://api.proxy.com/get?format=json",
    dynamic_proxy_ttl=300,      # 动态代理过期时间（秒）
    pool_size=10,               # IP池容量
    fetch_strategy="random"     # random(随机) 或 round_robin(轮询)
)
client = WeiboClient(proxy_config=proxy_config)

# 方式2: 一次性代理模式（适用于单次使用的IP提供商）
proxy_config = ProxyPoolConfig(
    proxy_api_url="http://api.proxy.com/get",
    use_once_proxy=True,
)
client = WeiboClient(proxy_config=proxy_config)
# 高效：如果API返回多个IP，会全部用完再获取新批次

# 方式3: 手动添加静态代理
client = WeiboClient()
client.add_proxy("http://1.2.3.4:8080", ttl=600)  # 指定过期时间
client.add_proxy("http://5.6.7.8:8080")  # 永不过期

# 方式4: 混合使用动态和静态代理
proxy_config = ProxyPoolConfig(
    proxy_api_url="http://api.proxy.com/get",
    pool_size=20
)
client = WeiboClient(proxy_config=proxy_config)
client.add_proxy("http://1.2.3.4:8080", ttl=None)

# 方式5: 自定义解析器（适配不同代理服务商）
def custom_parser(data):
    return [f"http://{data['result']['ip']}:{data['result']['port']}"]

proxy_config = ProxyPoolConfig(
    proxy_api_url="http://custom-api.com/proxy",
    proxy_api_parser=custom_parser
)
client = WeiboClient(proxy_config=proxy_config)

# 灵活控制单次请求是否使用代理
user = client.get_user_by_uid("2656274875", use_proxy=False)
posts = client.get_user_posts("2656274875", page=1)  # 使用代理
```

## API 能力速览
- `get_user_by_uid(uid)`：获取用户画像与计数
- `get_user_posts(uid, page=1, expand=False)`：抓取用户首页微博，支持展开长文
- `get_post_by_bid(bid)`：获取单条微博的完整正文与多媒体信息
- `search_users(query, page=1, count=10)` / `search_posts(query, page=1)`：关键词搜索
- `download_post_images(post, ...)`、`download_user_posts_images(uid, pages=2, ...)`：下载图像素材
- **统一异常**：`NetworkError`、`RateLimitError`、`UserNotFoundError` 等，便于业务兜底

## 开发与测试
```bash
uv sync --dev                # 安装开发依赖
uv run pytest                # 运行全部测试 (内置 unit/integration/slow 标记)
uv run ruff check crawl4weibo --fix
uv run ruff format crawl4weibo
uv run python examples/simple_example.py
```
项目结构、贡献指南与更多流程请参见 `docs/DEVELOPMENT.md` 与 `AGENTS.md`。

## 许可证
MIT License
