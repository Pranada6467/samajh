"""The client profile's total deadline, against a local server that drips its response."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator

import httpx
import pytest

from samajh.server.speech import DeadlineTransport


@pytest.fixture
def dripping_server() -> Iterator[str]:
    """Answers at once with headers, then sends one body byte every 0.1 s for 10 s."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(4)
    stop = threading.Event()

    def serve() -> None:
        while not stop.is_set():
            try:
                peer, _ = server.accept()
            except OSError:
                return
            with peer:
                try:
                    peer.recv(65536)
                    peer.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 100000\r\n\r\n")
                    until = time.monotonic() + 10
                    while time.monotonic() < until and not stop.is_set():
                        peer.sendall(b" ")
                        time.sleep(0.1)
                except OSError:
                    pass

    threading.Thread(target=serve, daemon=True).start()
    yield f"http://127.0.0.1:{server.getsockname()[1]}"
    stop.set()
    server.close()


def test_a_dripping_response_is_cut_at_the_deadline(dripping_server: str) -> None:
    # Each byte arrives well inside the 1 s per-read timeout, so httpx alone would wait 10 s.
    started = time.monotonic()
    with httpx.Client(transport=DeadlineTransport(0.5)) as http, pytest.raises(httpx.ReadTimeout):
        http.get(dripping_server, timeout=1.0)
    assert time.monotonic() - started < 2.0


def test_a_prompt_response_passes_through() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    with httpx.Client(transport=DeadlineTransport(5.0, httpx.MockTransport(handler))) as http:
        assert http.get("http://upstream.test/").json() == {"ok": True}
