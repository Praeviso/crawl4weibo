"""Exercise requests/urllib3 streaming against a bounded, loopback-only server.

Unlike the live Weibo integration tests, these need no credentials, proxy, browser,
or external network. Run with:
    pytest tests/integration/test_downloader_http.py
"""

import contextlib
import gzip
import threading
import zlib
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import requests

from crawl4weibo.exceptions.base import NetworkError
from crawl4weibo.utils.downloader import ImageDownloader, VideoDownloader

PAYLOAD = bytes(range(256)) * 129 + b"media trailer\x00\xff"


@dataclass(frozen=True)
class _Response:
    body: bytes
    content_type: str
    content_encoding: str | None = None
    truncated: bool = False


@dataclass
class _Server:
    url: str = ""
    responses: list[_Response] = field(default_factory=list)
    requests: list[str] = field(default_factory=list)


@pytest.fixture
def local_http_server():
    state = _Server()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        timeout = 2

        def log_message(self, *args):
            pass

        def do_GET(self):
            # A client can close early as soon as the invalid gzip is detected.
            with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                self._send_chunked_response()

        def _send_chunked_response(self):
            attempt = len(state.requests)
            state.requests.append(self.path)
            if not state.responses:
                self.send_error(500, "No response configured")
                return

            response = state.responses[min(attempt, len(state.responses) - 1)]
            self.send_response(200)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Connection", "close")
            if response.content_encoding:
                self.send_header("Content-Encoding", response.content_encoding)
            self.end_headers()
            self.close_connection = True

            # Split compressed headers and bodies across wire chunks independently
            # of the downloader's iter_content chunk size.
            offset = 0
            for size in (1, 2, 7, 31, 257, len(response.body)):
                chunk = response.body[offset : offset + size]
                if chunk:
                    self.wfile.write(f"{len(chunk):x}\r\n".encode("ascii"))
                    self.wfile.write(chunk + b"\r\n")
                offset += len(chunk)

            if response.truncated:
                # Advertise another chunk, but close before its body is complete.
                self.wfile.write(b"20\r\nshort")
            else:
                self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        state.url = f"http://127.0.0.1:{server.server_port}/media"
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": 0.01},
            daemon=True,
        )
        thread.start()
        try:
            yield state
        finally:
            server.shutdown()
            thread.join(timeout=2)
            assert not thread.is_alive(), "Loopback HTTP server did not stop"


@pytest.fixture
def local_session(local_http_server, monkeypatch):
    with requests.Session() as session:
        # Ignore ambient proxies and .netrc credentials even in developer shells.
        session.trust_env = False
        session.headers["Accept-Encoding"] = "gzip, deflate"
        request = session.request

        def bounded_request(method, url, **kwargs):
            if url != local_http_server.url:
                pytest.fail(f"Unexpected non-fixture request: {url}")
            kwargs["timeout"] = (2, 2)
            kwargs["allow_redirects"] = False
            return request(method, url, **kwargs)

        monkeypatch.setattr(session, "request", bounded_request)
        yield session


@pytest.fixture
def download(kind, tmp_path, local_session):
    downloader_type, method, extension, content_type = {
        "image": (ImageDownloader, "download_image", "jpg", "image/jpeg"),
        "video": (VideoDownloader, "download_video", "mp4", "video/mp4"),
    }[kind]
    downloader = downloader_type(
        session=local_session, download_dir=str(tmp_path), max_retries=1
    )
    target = tmp_path / f"download.{extension}"
    return downloader, getattr(downloader, method), target, content_type


@pytest.mark.integration
@pytest.mark.parametrize("kind", ["image", "video"])
class TestDownloaderLocalHTTP:
    @pytest.mark.parametrize("encoding", [None, "gzip", "deflate"])
    def test_chunked_download_preserves_decoded_bytes(
        self, encoding, local_http_server, download
    ):
        _, download_file, target, content_type = download
        body = PAYLOAD
        if encoding == "gzip":
            body = gzip.compress(body, mtime=0)
        elif encoding == "deflate":
            body = zlib.compress(body)
        local_http_server.responses.append(_Response(body, content_type, encoding))

        result = download_file(local_http_server.url, target.name)

        assert result == str(target)
        assert Path(result).read_bytes() == PAYLOAD
        assert local_http_server.requests == ["/media"]

    @pytest.mark.parametrize("failure", ["truncated_chunk", "invalid_gzip"])
    def test_stream_failure_raises_network_error(
        self, kind, failure, local_http_server, download
    ):
        _, download_file, target, content_type = download
        if failure == "truncated_chunk":
            response = _Response(PAYLOAD, content_type, truncated=True)
        else:
            response = _Response(b"not a gzip stream", content_type, "gzip")
        local_http_server.responses.append(response)

        with pytest.raises(NetworkError, match="Failed to download"):
            download_file(local_http_server.url, target.name)

        assert local_http_server.requests == ["/media"]
        if kind == "video":
            assert not target.exists(), "Incomplete video must not remain on disk"

    def test_retry_replaces_partial_bytes_with_complete_download(
        self, local_http_server, download, monkeypatch
    ):
        downloader, download_file, target, content_type = download
        downloader.max_retries = 2
        monkeypatch.setattr("crawl4weibo.utils.downloader.time.sleep", lambda _: None)
        local_http_server.responses.extend(
            [
                _Response(
                    b"discarded partial data" * 2048, content_type, truncated=True
                ),
                _Response(gzip.compress(PAYLOAD, mtime=0), content_type, "gzip"),
            ]
        )

        result = download_file(local_http_server.url, target.name)

        assert result == str(target)
        assert Path(result).read_bytes() == PAYLOAD
        assert local_http_server.requests == ["/media", "/media"]
