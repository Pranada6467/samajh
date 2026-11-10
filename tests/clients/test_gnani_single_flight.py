"""Cross-process single flight through `GnaniClient`, against a local server that counts overlap."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from samajh.clients.gnani import BatchOptions, GnaniClient, Timbre

REPO = Path(__file__).resolve().parents[2]
HEADER = b"RIFF\xff\xff\xff\xffWAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00"
TIMBRE_WAV = HEADER + b"data\xff\xff\xff\xff" + b"\x01\x00" * 800
PCM_WAV = HEADER + b"data\x80\x3e\x00\x00" + b"\x01\x00" * 8000  # 1 s

CALLER = """
import sys
from pathlib import Path
from samajh.clients.gnani import GnaniClient, Timbre
client = GnaniClient(api_key="test-key-not-real", credit_cap=10.0, state=Path(sys.argv[2]), base_url=sys.argv[1])
speech = client.tts("नमस्ते " + sys.argv[3], Timbre(model="timbre-v3.0", voice="Shivani", language="hi-IN"))
assert not speech.call.cache_hit and speech.call.attempts == 1 and speech.audio_seconds == 0.1
"""


class Overlap:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.now = self.peak = self.total = 0


@pytest.fixture
def server() -> Iterator[tuple[str, Overlap]]:
    seen = Overlap()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["content-length"]))
            with seen.lock:
                seen.now += 1
                seen.total += 1
                seen.peak = max(seen.peak, seen.now)
            time.sleep(0.5)
            with seen.lock:
                seen.now -= 1
            self.send_response(200)
            self.send_header("content-type", "audio/wav")
            self.send_header("content-length", str(len(TIMBRE_WAV)))
            self.end_headers()
            self.wfile.write(TIMBRE_WAV)

        def log_message(self, *args: object) -> None:
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}", seen
    finally:
        httpd.shutdown()
        httpd.server_close()


def run_three(base_url: str, states: list[Path]) -> None:
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", CALLER, base_url, str(state), str(i)],
            cwd=REPO,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for i, state in enumerate(states)
    ]
    for p in procs:
        _, err = p.communicate(timeout=60)
        assert p.returncode == 0, err


def test_three_processes_sharing_a_state_dir_never_overlap(
    server: tuple[str, Overlap], tmp_path: Path
) -> None:
    base_url, seen = server
    run_three(base_url, [tmp_path] * 3)
    assert (seen.total, seen.peak) == (3, 1)
    assert len((tmp_path / "ledger.jsonl").read_text().splitlines()) == 3


def test_control_separate_locks_do_overlap(server: tuple[str, Overlap], tmp_path: Path) -> None:
    """Without the shared lock the same three calls collide, so the test above is not vacuous."""
    base_url, seen = server
    run_three(base_url, [tmp_path / str(i) for i in range(3)])
    assert seen.total == 3 and seen.peak >= 2


# ---------------------------------------------------------------- batch requests and the cache re-check


@pytest.fixture
def api_server() -> Iterator[tuple[str, Overlap]]:
    """TTS and the batch routes on one host. Every request but the transcript download is counted."""
    seen = Overlap()
    transcript = {
        "file_id": "file-1",
        "job_id": "job-1",
        "model": "prisma-v3.0",
        "duration_seconds": 1.0,
        "segments": [],
        "full_transcript": "ok",
    }

    class Handler(BaseHTTPRequestHandler):
        def answer(self) -> None:
            self.rfile.read(int(self.headers.get("content-length", 0)))
            if self.path.startswith("/storage/"):
                return self.reply(200, "application/json", json.dumps(transcript).encode())
            with seen.lock:
                seen.now += 1
                seen.total += 1
                seen.peak = max(seen.peak, seen.now)
            time.sleep(0.2)
            with seen.lock:
                seen.now -= 1
            if self.path == "/api/v1/tts/inference":
                return self.reply(200, "audio/wav", TIMBRE_WAV)
            base = f"http://127.0.0.1:{self.server.server_address[1]}"
            body: dict[str, object] = {"job_id": "job-1", "status": "COMPLETED"}
            if self.path.endswith("/files"):
                body = {
                    "data": [
                        {"file_id": "file-1", "status": "COMPLETED", "transcript_url": f"{base}/storage/t.json"}
                    ]
                }
            self.reply(200, "application/json", json.dumps(body).encode())

        do_GET = do_POST = answer

        def reply(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("content-type", content_type)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}", seen
    finally:
        httpd.shutdown()
        httpd.server_close()


def run_batch_beside_tts(base_url: str, states: list[Path]) -> None:
    """One batch job (4 API requests) while two other threads make 3 TTS calls each."""

    def client(state: Path) -> GnaniClient:
        return GnaniClient(
            api_key="test-key-not-real", credit_cap=10.0, state=state, base_url=base_url, sleep=lambda s: None
        )

    def batch(state: Path) -> None:
        options = BatchOptions(model="prisma-v3.0", language="hi-IN", format="transcribe")
        result = client(state).batch_transcribe(PCM_WAV, options)
        assert result.text == "ok" and not result.call.cache_hit

    def speak(state: Path, tag: str) -> None:
        c = client(state)
        for i in range(3):
            c.tts(f"नमस्ते {tag} {i}", Timbre(model="timbre-v3.0", voice="Shivani", language="hi-IN"))

    errors: list[BaseException] = []

    def guarded(fn: object, *args: object) -> None:
        try:
            fn(*args)  # type: ignore[operator]
        except BaseException as exc:  # noqa: BLE001 - reported by the assertion below
            errors.append(exc)

    threads = [
        threading.Thread(target=guarded, args=(batch, states[0])),
        threading.Thread(target=guarded, args=(speak, states[1], "a")),
        threading.Thread(target=guarded, args=(speak, states[2], "b")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert not errors, errors


def test_batch_requests_share_the_key_lock_with_tts(api_server: tuple[str, Overlap], tmp_path: Path) -> None:
    base_url, seen = api_server
    run_batch_beside_tts(base_url, [tmp_path] * 3)
    assert (seen.total, seen.peak) == (10, 1)


def test_control_batch_and_tts_on_separate_locks_do_overlap(
    api_server: tuple[str, Overlap], tmp_path: Path
) -> None:
    base_url, seen = api_server
    run_batch_beside_tts(base_url, [tmp_path / str(i) for i in range(3)])
    assert seen.total == 10 and seen.peak >= 2


def test_two_callers_of_the_same_uncached_call_send_one_request(
    server: tuple[str, Overlap], tmp_path: Path
) -> None:
    """The second caller misses the cache, waits for the lock, and must look again once inside it."""
    base_url, seen = server
    ready = threading.Barrier(2)
    hits: list[bool] = []

    def call() -> None:
        client = GnaniClient(api_key="test-key-not-real", credit_cap=10.0, state=tmp_path, base_url=base_url)
        ready.wait(timeout=10)
        speech = client.tts("नमस्ते", Timbre(model="timbre-v3.0", voice="Shivani", language="hi-IN"))
        hits.append(speech.call.cache_hit)

    threads = [threading.Thread(target=call) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert sorted(hits) == [False, True]
    assert seen.total == 1
    statuses = [json.loads(line)["status"] for line in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert statuses == [200, "cache_hit"]
