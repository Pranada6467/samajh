"""StreamSession against a fake websocket: no network."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from samajh.clients._runtime import Ledger
from samajh.clients.errors import CapExceeded
from samajh.clients.gnani import (
    GnaniClient,
    PrismaStream,
    StreamBudgetExceeded,
    StreamError,
    StreamTimeout,
    stream_language,
    stream_session,
)

KEY = "gk_test_key_0123456789abcdef"


class FakeSocket:
    """Replies to `commit` with the scripted transcripts; can emit an error on the Nth frame."""

    def __init__(
        self, finals=("नमस्ते",), *, error_after: int | None = None, error_text: str = "", silent=False
    ):
        self.sent: list[bytes | str] = []
        self.finals, self.error_after, self.error_text, self.silent = finals, error_after, error_text, silent
        self.inbox: asyncio.Queue[str] = asyncio.Queue()
        self.inbox.put_nowait(json.dumps({"type": "connected"}))
        self.closed = False
        self.headers: dict[str, str] = {}

    async def send(self, message):
        self.sent.append(message)
        frames = sum(isinstance(m, bytes) for m in self.sent)
        if isinstance(message, bytes) and self.error_after is not None and frames == self.error_after:
            await self.inbox.put(json.dumps({"type": "error", "message": self.error_text}))
        if isinstance(message, str) and json.loads(message)["type"] == "commit" and not self.silent:
            for text in self.finals:
                await self.inbox.put(json.dumps({"type": "transcript", "text": text}))

    async def recv(self):
        return await self.inbox.get()

    async def close(self):
        self.closed = True


def make(tmp_path: Path, sock: FakeSocket, *, cap: float = 100.0, **kw):
    client = GnaniClient(
        api_key=KEY, credit_cap=cap, state=tmp_path, stt_credits_per_second=0.01, tts_credits_per_char=0.002
    )

    async def connect(url, headers):
        sock.headers, sock.url = headers, url
        return sock

    return client, stream_session(client, PrismaStream(), connect=connect, **kw)


def stream_rows(tmp_path: Path):
    return [e for e in Ledger(tmp_path / "ledger.jsonl").entries() if e.kind == "stt.stream"]


def test_reframes_any_chunks_to_1024_byte_frames_and_pads_the_tail(tmp_path):
    sock = FakeSocket()
    _, s = make(tmp_path, sock)
    with s:
        for size in (100, 3000, 7, 1500):
            s.send(bytes(size))
        s.commit(2)
    frames = [m for m in sock.sent if isinstance(m, bytes)]
    assert {len(f) for f in frames} == {1024}
    assert len(frames) == -(-4607 // 1024)
    assert json.loads(sock.sent[-1]) == {"type": "commit"}  # after every frame


def test_split_when_two_segments_arrive_before_commit_returns(tmp_path):
    sock = FakeSocket(finals=())
    _, s = make(tmp_path, sock)
    with s:
        s.send(bytes(2048))
        sock.inbox.put_nowait(json.dumps({"type": "transcript", "text": "एक"}))
        sock.finals = ("दो",)
        r = s.commit(2)
    assert r.segments == ("एक", "दो") and r.split and r.text == "एक दो"


def test_server_error_raises_with_the_key_redacted(tmp_path):
    sock = FakeSocket(error_after=1, error_text=f"bad key {KEY}")
    _, s = make(tmp_path, sock)
    with pytest.raises(StreamError) as info, s:
        s.send(bytes(1024))
        s.commit(2)
    assert KEY not in str(info.value) and "<key>" in str(info.value)
    assert KEY not in (tmp_path / "ledger.jsonl").read_text()


def test_commit_without_a_final_times_out(tmp_path):
    _, s = make(tmp_path, FakeSocket(silent=True))
    with pytest.raises(StreamTimeout), s:
        s.send(bytes(1024))
        s.commit(0.2)
    [row] = stream_rows(tmp_path)
    assert row.error_code == "commit_timeout"


def test_one_ledger_row_per_session_with_seconds_sent(tmp_path):
    sock = FakeSocket()
    _, s = make(tmp_path, sock)
    with s:
        s.send(bytes(16000))
        s.commit(2)
        s.abort()
    [row] = stream_rows(tmp_path)
    sent = sum(len(m) for m in sock.sent if isinstance(m, bytes))
    assert row.audio_seconds == pytest.approx(sent / 2 / 8000, abs=1e-3)
    assert row.est_credits == pytest.approx(row.audio_seconds * 0.01)
    assert row.cache_hit is False and row.status == 101 and sock.closed


def test_cap_refuses_before_connecting(tmp_path):
    sock = FakeSocket()
    _, s = make(tmp_path, sock, cap=0.1)  # 30 s at 0.01/s = 0.3 > 0.1
    with pytest.raises(CapExceeded):
        s.open()
    assert sock.headers == {} and stream_rows(tmp_path) == []


def test_stream_budget_refuses_once_reached(tmp_path):
    _, s = make(tmp_path, FakeSocket(), max_stream_seconds=0.5)
    with s:
        s.send(bytes(16000))  # 1 s
        s.commit(2)
    sock = FakeSocket()
    _, s2 = make(tmp_path, sock, max_stream_seconds=0.5)
    with pytest.raises(StreamBudgetExceeded):
        s2.open()
    assert sock.headers == {}


def test_takes_no_gnani_lock_and_sends_settings_as_headers(tmp_path):
    sock = FakeSocket()
    _, s = make(tmp_path, sock)
    with s:
        s.send(bytes(1024))
        s.commit(2)
    assert not (tmp_path / "gnani.lock").exists()
    assert sock.url == "wss://api.vachana.ai/stt/v3/stream"
    assert sock.headers["x-api-key-id"] == KEY
    assert sock.headers["language_code"] == "hi-IN" and sock.headers["x-min-silence-ms"] == "2000"
    assert sock.headers["x-sample-rate"] == "8000"


def test_hinglish_streams_as_one_hindi_locale():
    assert stream_language("hi-en").headers(KEY)["language_code"] == "hi-IN"
    assert "," not in stream_language("hi-en").headers(KEY)["language_code"]


def test_commit_without_close_returns_the_final_first_and_close_bills_once(tmp_path):
    sock = FakeSocket()
    _, s = make(tmp_path, sock)
    s.open()
    s.send(bytes(3000))
    result = s.commit(2, close=False)
    assert result.text == "नमस्ते" and result.flush_ms is not None
    assert result.commit_to_final_ms >= result.flush_ms
    assert not sock.closed and stream_rows(tmp_path) == []
    s.close()
    s.abort()  # a no-op after close
    rows = stream_rows(tmp_path)
    assert sock.closed and len(rows) == 1 and rows[0].error_code is None


class SlowCloseSocket(FakeSocket):
    async def close(self):
        await asyncio.sleep(1.5)  # under the client's 2 s close bound, so it completes
        self.closed = True


def test_send_after_an_upstream_error_returns_at_once_and_closes_in_the_background(tmp_path):
    import time

    sock = SlowCloseSocket(error_after=1, error_text="boom")
    _, s = make(tmp_path, sock)
    s.open()
    s.send(bytes(1024))
    deadline = time.monotonic() + 2
    while s._state.error is None and time.monotonic() < deadline:  # the reader sees the error
        time.sleep(0.01)
    started = time.perf_counter()
    with pytest.raises(StreamError):
        s.send(bytes(1024))
    assert time.perf_counter() - started < 0.05
    deadline = time.monotonic() + 5
    while not stream_rows(tmp_path) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert sock.closed and len(stream_rows(tmp_path)) == 1  # closed and billed exactly once
    s.abort()
    assert len(stream_rows(tmp_path)) == 1
