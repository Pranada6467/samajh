"""Verifier probe: the Gnani client against a local fake server. Offline: every request goes to
127.0.0.1, with a fake key and a temporary state directory. Nothing here can reach api.vachana.ai.

    uv run python references/reviews/iter1/probes/gnani_client_offline.py

Checks: (1) two and four processes are serialised by the lock, and are not when the state dirs
differ; (2) a cache hit makes no request; (3) the credit guard refuses before any request;
(4) retries are bounded and Retry-After is capped; (5) a process killed mid-request, and one killed
mid-backoff, leave a ledger that parses, a free lock and no half cache entry; (6) what the guard
costs per call on a ledger the size of the project's.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

from samajh.clients._runtime import Ledger, RetryPolicy
from samajh.clients.errors import ApiError, CapExceeded, ClientError
from samajh.clients.gnani import GnaniClient, PrismaV30

HEADER = b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00"


def wav(seconds: float, fill: int = 1) -> bytes:
    body = bytes([fill, 0]) * int(8000 * seconds)
    return HEADER + b"data" + len(body).to_bytes(4, "little") + body


class Fake:
    """Counts requests and overlap; `mode` picks the answer."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.now = self.peak = self.total = 0
        self.mode = "ok"
        self.delay = 0.0
        self.keys_seen: set[str] = set()


def serve(fake: Fake) -> tuple[ThreadingHTTPServer, str]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.rfile.read(int(self.headers.get("content-length", 0)))
            fake.keys_seen.add(self.headers.get("X-API-Key-ID", ""))
            with fake.lock:
                fake.now += 1
                fake.total += 1
                fake.peak = max(fake.peak, fake.now)
                mode = fake.mode
            time.sleep(fake.delay)
            with fake.lock:
                fake.now -= 1
            if mode == "ok":
                status, body, extra = 200, {"success": True, "transcript": "हाँ", "model": "prisma-v3.0"}, {}
            elif mode == "504":
                status, body, extra = 504, {"error": "Gateway Timeout"}, {}
            elif mode == "429-day":
                status, body, extra = 429, {"detail": {"error_code": "RATE_LIMITED", "message": "x"}}, {"Retry-After": "86400"}
            else:
                status, body, extra = 400, {"error": {"type": "BAD", "message": "no"}}, {}
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            for name, value in extra.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


CALLER = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[4])
from gnani_client_offline import wav
from samajh.clients.gnani import GnaniClient, PrismaV30
client = GnaniClient(api_key="fake-key-for-the-probe", credit_cap=50.0, state=Path(sys.argv[2]), base_url=sys.argv[1])
t = client.stt(wav(1.0, int(sys.argv[3])), PrismaV30(language="hi-IN", format="transcribe"))
print(t.call.attempts, t.call.cache_hit)
"""
OPTIONS = PrismaV30(language="hi-IN", format="transcribe")


def spawn(url: str, state: Path, fill: int) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-c", CALLER, url, str(state), str(fill), str(Path(__file__).parent)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )  # fmt: skip


def client(url: str, state: Path, **kwargs) -> GnaniClient:
    return GnaniClient(api_key="fake-key-for-the-probe", state=state, base_url=url, **kwargs)


def main() -> None:
    fake = Fake()
    server, url = serve(fake)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # 1. serialisation across processes
        fake.delay = 0.4
        for label, n, shared in (("2 processes, one state dir", 2, True), ("4 processes, one state dir", 4, True),
                                 ("control: 4 processes, 4 state dirs", 4, False)):  # fmt: skip
            fake.peak = fake.total = 0
            started = time.monotonic()
            procs = [spawn(url, tmp / (f"shared{n}" if shared else f"own{k}"), 10 + k) for k in range(n)]
            outs = [p.communicate(timeout=60) for p in procs]
            ok = all(p.returncode == 0 for p in procs)
            print(f"1. {label}: all succeeded {ok}, requests {fake.total}, peak in flight {fake.peak}, "
                  f"wall {time.monotonic() - started:.2f}s")  # fmt: skip
            if not ok:
                print(outs)
        fake.delay = 0.0

        # 2. cache hit: no request, even with the server gone
        state = tmp / "cache"
        c = client(url, state, credit_cap=50.0)
        fake.total = 0
        first = c.stt(wav(1.0, 7), OPTIONS)
        second = c.stt(wav(1.0, 7), OPTIONS)
        dead = client("http://127.0.0.1:9", state, credit_cap=50.0)  # nothing listens on port 9
        try:
            third = dead.stt(wav(1.0, 7), OPTIONS)
            third_hit = third.call.cache_hit
        except ClientError as error:  # the base URL is part of the cache key
            third_hit = f"miss ({type(error).__name__}): the base URL is in the cache key"
        print(f"2. same call twice: requests {fake.total}; hits {first.call.cache_hit}, {second.call.cache_hit}; "
              f"credits booked {first.call.est_credits}, {second.call.est_credits}; other base URL: {third_hit}")  # fmt: skip
        rows = list(Ledger(state / "ledger.jsonl").entries())
        print(f"   ledger rows {[(r.status, r.attempt, r.est_credits) for r in rows]}")
        print(f"   key header reached the fake server as sent: {fake.keys_seen == {'fake-key-for-the-probe'}}; "
              f"key in any state file: {any(b'fake-key-for-the-probe' in p.read_bytes() for p in tmp.rglob('*') if p.is_file())}")  # fmt: skip

        # 3. credit guard: 1 s clips cost 0.010 each; the cap is 0.025
        state = tmp / "cap"
        c = client(url, state, credit_cap=0.025)
        fake.total = 0
        results = []
        for k in range(4):
            try:
                c.stt(wav(1.0, 20 + k), OPTIONS)
                results.append("sent")
            except CapExceeded as error:
                results.append(f"refused(spent={error.spent:.3f}, estimate={error.estimate:.3f})")
        hit = c.stt(wav(1.0, 20), OPTIONS).call.cache_hit
        print(f"3. cap 0.025, four 1 s clips: {results}; requests {fake.total}; a cached clip still answers at the cap: {hit}")
        unknown = b"not a wav at all" * 10
        try:
            client(url, tmp / "cap2", credit_cap=0.25).stt(unknown, OPTIONS, audio_format="wav")
            print("   a non-WAV body under a 0.25 cap: sent")
        except CapExceeded as error:
            print(f"   a non-WAV body is charged as 30 s: refused, estimate {error.estimate:.2f}")

        # 4. retries are bounded
        for mode in ("504", "429-day", "400"):
            fake.mode, fake.total = mode, 0
            slept: list[float] = []
            c = client(url, tmp / f"retry-{mode}", credit_cap=50.0, sleep=slept.append)
            try:
                c.stt(wav(1.0, 40), OPTIONS)
            except ApiError as error:
                rows = list(Ledger(tmp / f"retry-{mode}" / "ledger.jsonl").entries())
                print(f"4. always {mode}: {type(error).__name__} after {error.attempts} attempts, requests {fake.total}, "
                      f"sleeps {[round(s, 1) for s in slept]}, ledger rows {len(rows)}, credits booked "
                      f"{sum(r.est_credits for r in rows)}")  # fmt: skip
        slept = []
        c = GnaniClient(api_key="fake-key-for-the-probe", credit_cap=50.0, state=tmp / "dead",
                        base_url="http://127.0.0.1:9", sleep=slept.append, http=httpx.Client())  # fmt: skip
        try:
            c.stt(wav(1.0, 41), OPTIONS)
        except ClientError as error:
            print(f"4. connection refused: {type(error).__name__}: {error}; sleeps {[round(s, 1) for s in slept]}")
        print(f"   worst case one call can hold the lock at the defaults: 5 attempts x 30 s timeout = 150 s, plus backoff "
              f"of up to {sum(min(30.0, 2.0 ** k) for k in range(4)):.0f} s, or up to 120 s when the server sends Retry-After")
        fake.mode = "ok"

        # 5. a process killed mid-request, and one killed mid-backoff
        for label, mode, delay, wait in (("mid-request", "ok", 3.0, 1.0), ("mid-backoff", "504", 0.0, 1.2)):
            state = tmp / f"kill-{mode}"
            fake.mode, fake.delay, fake.total = mode, delay, 0
            proc = spawn(url, state, 60)
            time.sleep(wait)
            os.kill(proc.pid, signal.SIGKILL)
            proc.wait()
            fake.mode, fake.delay = "ok", 0.0
            raw = (state / "ledger.jsonl").read_bytes().splitlines() if (state / "ledger.jsonl").exists() else []
            parsed = list(Ledger(state / "ledger.jsonl").entries())
            started = time.monotonic()
            again = client(url, state, credit_cap=50.0, lock_timeout=5.0).stt(wav(1.0, 60), OPTIONS)
            leftovers = [p.name for p in (state / "cache").rglob("*.tmp")] if (state / "cache").exists() else []
            print(f"5. killed {label}: requests the server saw before the kill {fake.total - 1}; ledger lines {len(raw)}, "
                  f"all parse {len(raw) == len(parsed)}, rows {[(r.status, r.est_credits) for r in parsed]}; "
                  f"next call got the lock in {time.monotonic() - started:.2f}s, cache_hit {again.call.cache_hit}; "
                  f"temp files left {leftovers}")  # fmt: skip
        print("   a request the server had accepted when the client died leaves no ledger row: if Gnani bills it, the ledger under-counts by that call")

        # 6. cost of the guard on a ledger the size of the project's
        real = Path(os.environ.get("SAMAJH_REAL_LEDGER", Path(__file__).resolve().parents[4] / ".samajh" / "ledger.jsonl"))
        if real.exists():
            ledger = Ledger(real)
            started = time.monotonic()
            total = ledger.total_credits()
            seconds = time.monotonic() - started
            lines = sum(1 for _ in real.open("rb"))
            print(f"6. project ledger (read only): {lines} lines, {real.stat().st_size / 1e6:.1f} MB; total_credits() = {total:.2f} "
                  f"in {seconds * 1000:.0f} ms, paid before every uncached call while the lock is held")  # fmt: skip
    server.shutdown()


if __name__ == "__main__":
    main()
