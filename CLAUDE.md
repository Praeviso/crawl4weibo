# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Crawl4Weibo is a production-ready Python library for scraping Weibo (微博) mobile web data. It handles anti-scraping mechanisms (including "432 protection"), manages proxy pools, and returns structured data models. The library is designed to work without cookies by simulating mobile requests with appropriate headers.

## Development Commands

### Setup and Installation
```bash
uv sync --dev                # Install all dependencies including dev tools
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
uv run python examples/simple_example.py       # Basic usage demo
uv run python examples/download_images_example.py  # Image download demo
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
│   ├── downloader.py  # ImageDownloader - batch image fetching
│   └── logger.py  # Logging setup
└── exceptions/    # Business-level exceptions
    └── base.py    # CrawlError, NetworkError, RateLimitError, etc.
```

### Core Request Flow

1. **WeiboClient** (core/client.py) - Main entry point
   - Initializes session with mobile User-Agent (Android Chrome)
   - Calls `_init_session()` to fetch initial cookies from m.weibo.cn
   - Uses `_request()` with exponential backoff retry (handles 432 protection)
   - Supports per-request proxy control via `use_proxy` parameter

2. **WeiboParser** (utils/parser.py) - Response transformation
   - Converts raw JSON API responses to typed User/Post models
   - Handles nested repost chains recursively
   - Extracts pagination info and metadata

3. **ProxyPool** (utils/proxy.py) - Proxy management
   - Supports dynamic proxy APIs (fetches multiple proxies per call)
   - Supports static proxies with optional TTL
   - Two fetch strategies: `random` or `round_robin`
   - Automatically cleans expired proxies
   - Parser architecture: `proxy_parsers.py` contains modular format-specific parsers

4. **Exception Hierarchy** (exceptions/base.py)
   - `CrawlError` - Base exception with `message` and `code`
   - `NetworkError` - HTTP failures, timeouts
   - `RateLimitError` - 432 protection triggered (includes `retry_after`)
   - `AuthenticationError` - Cookie/auth failures
   - `ParseError` - JSON parsing failures
   - `UserNotFoundError` - User ID not found

### Key Design Patterns

**Proxy Pool Architecture**
- Custom parsers must return `List[str]` (not single string)
- Default parsers in `proxy_parsers.py` support:
  - Plain text: single/multiple lines, with/without auth
  - JSON: various nested formats (see test cases for examples)
- Pool automatically batch-fetches proxies when not full
- Respects `pool_size` limit when adding proxies

**Retry Strategy**
- Exponential backoff in `WeiboClient._request()`
- Max retries configurable (default 3)
- Special handling for 432 status codes (anti-scraping)

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
