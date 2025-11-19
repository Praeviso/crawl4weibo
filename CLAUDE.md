# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Crawl4Weibo is a production-ready Python library for scraping Weibo (微博) mobile web data. It handles anti-scraping mechanisms (including "432 protection"), manages proxy pools, and returns structured data models. The library supports both simple cookie fetching and browser-based cookie acquisition using Playwright for enhanced anti-scraping bypass.

## Development Commands

### Setup and Installation
```bash
uv sync --dev                # Install all dependencies including dev tools

# For browser-based cookie fetching (optional but recommended):
uv add playwright            # Install Playwright
uv run playwright install chromium  # Install Chromium browser
```

### Testing
```bash
uv run pytest                                    # Run all tests
uv run pytest -m "unit and not slow"            # Fast tests only (pre-PR gate)
uv run pytest tests/test_proxy.py -v            # Specific test file
uv run pytest tests/test_proxy.py::TestProxyPool::test_batch_proxy_fetch_multiple_proxies  # Single test
```

Test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`

### Code Quality
```bash
uv run ruff check crawl4weibo --fix            # Lint and auto-fix
uv run ruff format crawl4weibo                 # Format code
```

### Running Examples
```bash
uv run python examples/simple_example.py              # Basic usage demo
uv run python examples/download_images_example.py     # Image download demo
```

## Architecture

### Module Organization

```
crawl4weibo/
├── core/          # Request orchestration and retry logic
│   └── client.py  # WeiboClient - main entry point
├── models/        # Typed data models
│   ├── user.py    # User dataclass
│   └── post.py    # Post dataclass with recursive repost support
├── utils/         # Shared utilities
│   ├── parser.py  # WeiboParser - JSON response to model conversion
│   ├── proxy.py   # ProxyPool - unified dynamic/static proxy management
│   ├── proxy_parsers.py  # Modular proxy API response parsers
│   ├── cookie_fetcher.py  # CookieFetcher - browser/requests-based cookie acquisition
│   ├── downloader.py  # ImageDownloader - batch image fetching
│   └── logger.py  # Logging setup
└── exceptions/    # Business-level exceptions
    └── base.py    # CrawlError, NetworkError, RateLimitError, etc.
```

### Core Request Flow

1. **WeiboClient** (core/client.py) - Main entry point
   - Initializes session with mobile User-Agent (Android Chrome)
   - Calls `_init_session()` to fetch initial cookies
     - **Browser mode** (default): Uses Playwright to simulate real browser and fetch cookies (more reliable)
     - **Simple mode**: Uses requests to fetch cookies (may fail with strengthened anti-scraping)
   - Uses `_request()` with exponential backoff retry (handles 432 protection)
   - Supports per-request proxy control via `use_proxy` parameter
   - Supports manual cookie refresh via `refresh_cookies()` method

2. **CookieFetcher** (utils/cookie_fetcher.py) - Cookie acquisition
   - Two fetching strategies:
     - **Requests-based**: Fast, simple, but may fail with enhanced anti-scraping
     - **Browser-based** (Playwright): Slower but more reliable, simulates real mobile browser
   - Browser mode uses stealth settings to avoid detection
   - Simulates mobile device (Android) with proper viewport and touch support

3. **WeiboParser** (utils/parser.py) - Response transformation
   - Converts raw JSON API responses to typed User/Post models
   - Handles nested repost chains recursively
   - Extracts pagination info and metadata

4. **ProxyPool** (utils/proxy.py) - Proxy management
   - Supports two modes: **pooling** (default) and **one-time**
   - **Pooling mode**: Caches proxies with TTL, reuses them across requests
     - Supports dynamic proxy APIs (fetches multiple proxies per call)
     - Supports static proxies with optional TTL
     - Two fetch strategies: `random` or `round_robin`
     - Automatically cleans expired proxies
   - **One-time mode** (`use_once_proxy=True`): Fetches fresh proxy for each request
     - Ideal for single-use IP providers
     - Uses internal buffer to efficiently consume batch API responses
     - No pooling or caching beyond current batch
     - Immediate retry on failure (no wait needed)
     - Cost-efficient: uses all proxies from batch before fetching new batch
   - Parser architecture: `proxy_parsers.py` contains modular format-specific parsers

5. **Exception Hierarchy** (exceptions/base.py)
   - `CrawlError` - Base exception with `message` and `code`
   - `NetworkError` - HTTP failures, timeouts
   - `RateLimitError` - 432 protection triggered (includes `retry_after`)
   - `AuthenticationError` - Cookie/auth failures
   - `ParseError` - JSON parsing failures
   - `UserNotFoundError` - User ID not found

### Key Design Patterns

**Proxy Pool Architecture**
- Supports two operational modes via `use_once_proxy` parameter:
  - **Pooling mode** (default, `use_once_proxy=False`):
    - Caches proxies in memory with TTL management
    - Reuses proxies across multiple requests
    - Batch-fetches proxies when pool not full
    - Custom parsers must return `List[str]` (not single string)
    - Respects `pool_size` limit when adding proxies
  - **One-time mode** (`use_once_proxy=True`):
    - Fetches fresh proxies from API as needed
    - Uses internal buffer (FIFO queue) to store batch responses
    - Consumes all proxies from buffer before making new API call
    - Ideal for providers that charge per IP count
    - Example: API returns 10 IPs → uses all 10 before next API call
    - No pooling beyond current batch
- Default parsers in `proxy_parsers.py` support:
  - Plain text: single/multiple lines, with/without auth
  - JSON: various nested formats (see test cases for examples)

**Retry Strategy**
- Exponential backoff in `WeiboClient._request()`
- Max retries configurable (default 3)
- Special handling for 432 status codes (anti-scraping)
- Retry wait times vary by proxy mode:
  - **One-time proxy mode**: No wait (immediate retry with fresh IP)
  - **Pooled proxy mode**: 0.5-1.5s wait
  - **No proxy mode**: 2-7s wait

**Model Design**
- Dataclasses in `models/` are lightweight
- IO-heavy operations stay in `core/` and `utils/`
- Post model supports recursive `retweeted_status` for repost chains

## Testing Guidelines

- Place tests in `tests/` mirroring module structure
- Use `@responses.activate` for mocking HTTP calls
- Mark network-consuming tests with `@pytest.mark.integration`
- When testing proxy parsers:
  - Test both single and batch proxy responses
  - Verify pool size limits are respected
  - Test custom parser returns `List[str]`
  - Test both pooling and one-time proxy modes

## Common Tasks

### Adding a New Proxy Parser Format

1. Add parser function to `crawl4weibo/utils/proxy_parsers.py`
2. Update `default_proxy_parser()` to detect new format if needed
3. Add test cases to `tests/test_proxy_parsers.py`
4. Ensure parser returns `List[str]`, not `str`

### Adding a New API Endpoint

1. Add method to `WeiboClient` in `core/client.py`
2. Use `self._request()` for HTTP calls (includes retry logic)
3. Pass response to `WeiboParser` for data extraction
4. Add corresponding model if new data structure needed
5. Add unit tests with mocked responses

### Modifying Retry Behavior

The retry logic is in `WeiboClient._request()`:
- Handles network errors and rate limits
- Uses exponential backoff with jitter
- Special case: 432 status triggers longer delays
- Three wait strategies based on proxy mode:
  1. One-time proxy: immediate retry (fresh IP each time)
  2. Pooled proxy: short wait (0.5-1.5s)
  3. No proxy: longer wait (2-7s)

### Browser-Based Cookie Fetching

**Important**: Due to Weibo's strengthened anti-scraping, browser automation (Playwright) is now **required** and enabled by default.

**Prerequisites** (users must install before using the library):
```bash
uv add playwright
uv run playwright install chromium
```

If not installed, the client will display a friendly error message with installation instructions.

**Usage** (transparent to users):
```python
from crawl4weibo.core.client import WeiboClient

# Browser mode is used by default
client = WeiboClient()
```

**Advanced options** (rarely needed):
- Disable browser mode: `WeiboClient(use_browser_cookies=False)` (not recommended)
- Manual refresh: `client.refresh_cookies(use_browser=True)`

## Code Style

- PEP 8 with 88-character lines (enforced by ruff)
- Double-quoted strings
- Type hints on all public APIs
- snake_case for functions/variables
- Keep upstream JSON keys unchanged in raw parsing

## Commit Guidelines

Use Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
- Subject line imperative mood, under 72 characters
- Include test evidence in PR descriptions
- Flag API/behavior changes explicitly
