"""Offline protocol smoke coverage for the real optional MCP dependency.

Run with ``uv run --extra mcp pytest tests/integration/test_mcp_stdio.py``.
The server uses no cookies, browser, accounts, or external network access.
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import threading
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from queue import Empty, Queue
from typing import Any

import pytest

# Block network access in the child as well as disabling cookie acquisition.
# This preserves the real CLI, WeiboClient, FastMCP and AnyIO runtime.
_SERVER_BOOTSTRAP = """
import runpy
import sys


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.gethostbyname"}:
        raise RuntimeError("Network access is forbidden in the MCP stdio smoke test")


sys.addaudithook(deny_network)
sys.argv = ["crawl4weibo.mcp.server", "--disable-browser-cookies"]
runpy.run_module("crawl4weibo.mcp.server", run_name="__main__")
"""


@pytest.mark.integration
def test_real_mcp_stdio_initialize_tools_and_health(tmp_path: Path) -> None:
    """Exercise registration, JSON-RPC transport and clean shutdown, offline."""
    try:
        version("mcp")
    except PackageNotFoundError:
        pytest.skip("Install crawl4weibo[mcp] to run the real MCP stdio smoke test")

    # Use the current interpreter without uv syncing away the optional dependency.
    # Do not pass through proxy settings, credentials or the user's home directory.
    env = {
        key: os.environ[key]
        for key in ("PATH", "SYSTEMROOT", "WINDIR")
        if key in os.environ
    }
    env.update(
        HOME=str(tmp_path),
        USERPROFILE=str(tmp_path),
        TMPDIR=str(tmp_path),
        TEMP=str(tmp_path),
        TMP=str(tmp_path),
        PYTHONPATH=str(Path(__file__).resolve().parents[2]),
        PYTHONIOENCODING="utf-8",
        PYTHONUNBUFFERED="1",
    )
    lines: Queue[str | None] = Queue()
    stderr_path = tmp_path / "mcp-stderr.log"
    # A single deadline bounds the whole exchange, including unexpected messages.
    deadline = time.monotonic() + 30

    with stderr_path.open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(
            [sys.executable, "-u", "-c", _SERVER_BOOTSTRAP],
            cwd=tmp_path,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
            text=True,
            encoding="utf-8",
        )
        assert process.stdin is not None
        assert process.stdout is not None

        def read_stdout() -> None:
            try:
                for line in process.stdout:
                    lines.put(line)
            finally:
                lines.put(None)

        reader = threading.Thread(target=read_stdout, daemon=True)
        reader.start()

        def send(message: dict[str, Any]) -> None:
            process.stdin.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
            process.stdin.flush()

        def request(request_id: int, method: str, params: dict[str, Any]) -> Any:
            send({"id": request_id, "method": method, "params": params})
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    pytest.fail(f"MCP timeout waiting for {method}")
                try:
                    line = lines.get(timeout=remaining)
                except Empty:
                    pytest.fail(
                        f"MCP timeout waiting for {method}:\n"
                        f"{stderr_path.read_text(encoding='utf-8')}"
                    )
                if line is None:
                    pytest.fail(
                        f"MCP exited before replying to {method}:\n"
                        f"{stderr_path.read_text(encoding='utf-8')}"
                    )
                message = json.loads(line)
                assert message["jsonrpc"] == "2.0"
                if "id" not in message:
                    continue  # Protocol notifications may precede a response.
                assert message["id"] == request_id, message
                assert "error" not in message, message
                return message["result"]

        exited_cleanly = False
        try:
            initialized = request(
                1,
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "crawl4weibo-smoke", "version": "1.0"},
                },
            )
            assert initialized["protocolVersion"] == "2024-11-05"
            assert initialized["serverInfo"]["name"] == "crawl4weibo"
            assert "tools" in initialized["capabilities"]
            assert "resources" in initialized["capabilities"]
            send({"method": "notifications/initialized"})

            tools = request(2, "tools/list", {})["tools"]
            by_name = {tool["name"]: tool for tool in tools}
            assert set(by_name) == {
                "get_user_by_uid",
                "get_user_posts",
                "get_post_by_bid",
                "search_users",
                "search_posts",
                "get_comments",
                "get_all_comments",
            }
            assert all(tool["inputSchema"]["type"] == "object" for tool in tools)
            user_schema = by_name["get_user_by_uid"]["inputSchema"]
            assert "uid" in user_schema["required"]
            assert user_schema["properties"]["uid"]["type"] == "string"

            health = request(3, "resources/read", {"uri": "weibo://health"})
            assert len(health["contents"]) == 1
            content = health["contents"][0]
            assert content["uri"].rstrip("/") == "weibo://health"
            assert json.loads(content["text"]) == {
                "status": "ok",
                "service": "crawl4weibo-mcp",
            }
        finally:
            # EOF must stop the real AnyIO transport. A deadlocked server is
            # killed and reaped, rather than hanging the rest of the test suite.
            with contextlib.suppress(BrokenPipeError):
                process.stdin.close()
            try:
                process.wait(timeout=5)
                exited_cleanly = True
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            finally:
                reader.join(timeout=5)
                process.stdout.close()

        assert exited_cleanly, "MCP server did not shut down within 5 seconds of EOF"
        assert process.returncode == 0, stderr_path.read_text(encoding="utf-8")
        assert not reader.is_alive(), "MCP stdout reader did not stop after shutdown"
