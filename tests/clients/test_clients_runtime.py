from __future__ import annotations

import itertools
import json
import random
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest

from samajh.clients._runtime import (
    Attempt,
    Cache,
    Ledger,
    LedgerEntry,
    RetryPolicy,
    cache_key,
    load_defaults,
    send_with_retry,
    single_flight,
    state_dir,
)
from samajh.clients.errors import ApiError, AuthError, LockTimeout, RateLimited, ServerError, TransportError

REPO = Path(__file__).resolve().parents[2]


def spawn(code: str, *args: object) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-c", code, *map(str, args)],
        cwd=REPO,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def wait_all(procs: list[subprocess.Popen[str]]) -> None:
    for p in procs:
        _, err = p.communicate(timeout=60)
        assert p.returncode == 0, err


def wait_for(paths: list[Path]) -> None:
    deadline = time.monotonic() + 30
    while not all(p.exists() for p in paths):
        assert time.monotonic() < deadline, "subprocesses never became ready"
        time.sleep(0.01)


# ---------------------------------------------------------------- state dir, defaults


def test_state_dir_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SAMAJH_STATE_DIR", str(tmp_path / "state"))
    assert state_dir() == tmp_path / "state"
    monkeypatch.delenv("SAMAJH_STATE_DIR")
    assert state_dir() == REPO / ".samajh"


def test_load_defaults_has_both_tables() -> None:
    defaults = load_defaults()
    assert isinstance(defaults["gnani"], dict)
    assert isinstance(defaults["llm"], dict)


# ---------------------------------------------------------------- cache_key


def test_cache_key_is_stable_across_dict_ordering() -> None:
    a = cache_key("stt", {"model": "m", "lang": "hi", "opts": {"x": 1, "y": 2}}, b"audio")
    b = cache_key("stt", {"opts": {"y": 2, "x": 1}, "lang": "hi", "model": "m"}, b"audio")
    assert a == b
    assert len(a) == 64 and int(a, 16) >= 0


def test_cache_key_changes_with_every_input() -> None:
    base = cache_key("stt", {"model": "m", "lang": "hi"}, b"audio")
    others = {
        cache_key("tts", {"model": "m", "lang": "hi"}, b"audio"),
        cache_key("stt", {"model": "m2", "lang": "hi"}, b"audio"),
        cache_key("stt", {"model": "m", "lang": "ta"}, b"audio"),
        cache_key("stt", {"model": "m", "lang": "hi", "codemix": True}, b"audio"),
        cache_key("stt", {"model": "m", "lang": "hi"}, b"audio2"),
        cache_key("stt", {"model": "m", "lang": "hi"}, b""),
    }
    assert base not in others
    assert len(others) == 6


def test_cache_key_param_payload_boundary_does_not_collide() -> None:
    keys = {
        cache_key("tts", {"text": "ab"}, b"c"),
        cache_key("tts", {"text": "a"}, b"bc"),
        cache_key("tts", {"text": "abc"}, b""),
        cache_key("tts", {"text": ""}, b"abc"),
        cache_key("tts", {"text": "a\x00"}, b"bc"),
        cache_key("tts", {"text": "a"}, b"\x00bc"),
        cache_key("ttsa", {"text": ""}, b"bc"),
    }
    assert len(keys) == 7


def test_cache_key_handles_non_ascii_params() -> None:
    assert cache_key("tts", {"text": "नमस्ते"}, b"") != cache_key("tts", {"text": "வணக்கம்"}, b"")


# ---------------------------------------------------------------- cache

KEY = "ab" + "0" * 62


def test_cache_miss(tmp_path: Path) -> None:
    assert Cache(tmp_path / "cache").get(KEY) is None


def test_cache_put_then_get(tmp_path: Path) -> None:
    cache = Cache(tmp_path / "cache")
    cache.put(KEY, {"model": "m", "text": "नमस्ते"}, b"\x00\x01body")
    entry = cache.get(KEY)
    assert entry is not None
    assert entry.meta == {"model": "m", "text": "नमस्ते"}
    assert entry.body == b"\x00\x01body"
    assert (tmp_path / "cache" / "ab" / f"{KEY}.bin").is_file()
    assert (tmp_path / "cache" / "ab" / f"{KEY}.json").is_file()
    assert Cache(tmp_path / "cache").get("cd" + "0" * 62) is None


def test_cache_body_without_meta_is_a_miss(tmp_path: Path) -> None:
    cache = Cache(tmp_path)
    cache.put(KEY, {"a": 1}, b"body")
    (tmp_path / "ab" / f"{KEY}.json").unlink()
    assert cache.get(KEY) is None


def test_cache_meta_without_body_is_a_miss(tmp_path: Path) -> None:
    cache = Cache(tmp_path)
    cache.put(KEY, {"a": 1}, b"body")
    (tmp_path / "ab" / f"{KEY}.bin").unlink()
    assert cache.get(KEY) is None


@pytest.mark.parametrize("garbage", [b"{not json", b"", b"[1, 2]", b"\xff\xfe"])
def test_cache_corrupt_meta_is_a_miss(tmp_path: Path, garbage: bytes) -> None:
    cache = Cache(tmp_path)
    cache.put(KEY, {"a": 1}, b"body")
    (tmp_path / "ab" / f"{KEY}.json").write_bytes(garbage)
    assert cache.get(KEY) is None


def test_cache_overwrite_leaves_one_clean_entry(tmp_path: Path) -> None:
    cache = Cache(tmp_path)
    cache.put(KEY, {"v": 1}, b"one")
    cache.put(KEY, {"v": 2}, b"two")
    entry = cache.get(KEY)
    assert entry is not None and (entry.meta, entry.body) == ({"v": 2}, b"two")
    assert sorted(p.name for p in (tmp_path / "ab").iterdir()) == [f"{KEY}.bin", f"{KEY}.json"]


# ---------------------------------------------------------------- ledger


def row(**overrides: object) -> LedgerEntry:
    fields: dict[str, object] = {
        "ts": "2026-11-10T00:00:00Z",
        "provider": "gnani",
        "kind": "stt",
        "model": "prisma-v3.0",
        "status": 200,
        "attempt": 1,
        "seconds": 0.5,
        "cache_hit": False,
        "cache_key": KEY,
    }
    return LedgerEntry.model_validate(fields | overrides)


def test_ledger_missing_file_reads_empty(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.jsonl")
    assert list(ledger.entries()) == []
    assert ledger.total_credits() == 0
    assert ledger.total_usd() == 0


def test_ledger_append_then_read_back(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "nested" / "dir" / "ledger.jsonl")
    rows = [
        row(est_credits=1.5, audio_seconds=3.2),
        row(status="cache_hit", attempt=0, cache_hit=True),
        row(status="transport_error", error_code="ConnectTimeout"),
        row(status=429, error_code="RATE_LIMITED"),
    ]
    for r in rows:
        ledger.append(r)
    assert list(ledger.entries()) == rows


def test_ledger_totals_split_by_unit(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.jsonl")
    ledger.append(row(est_credits=1.5))
    ledger.append(row(est_credits=2.25, kind="tts"))
    ledger.append(row(status=429))
    ledger.append(row(provider="openrouter", kind="chat", model="x/y", usd=0.002, est_credits=99.0))
    ledger.append(row(provider="openrouter", kind="chat", model="x/y", usd=0.003))
    assert ledger.total_credits() == pytest.approx(3.75)
    assert ledger.total_usd() == pytest.approx(0.005)


def test_ledger_skips_garbage_lines(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger(path)
    ledger.append(row(est_credits=1.0))
    with path.open("ab") as f:
        f.write(b"not json at all\n")
        f.write(b'{"ts": "x", "unknown_field": 1}\n')
        f.write(b"\xff\xfe\n")
        f.write(b"\n")
    ledger.append(row(est_credits=2.0))
    assert [e.est_credits for e in ledger.entries()] == [1.0, 2.0]
    assert ledger.total_credits() == pytest.approx(3.0)


LEDGER_WRITER = """
import sys, time
from pathlib import Path
from samajh.clients._runtime import Ledger, LedgerEntry
path, tag, count, ready, go = sys.argv[1], sys.argv[2], int(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])
ledger = Ledger(Path(path))
ready.touch()
while not go.exists():
    time.sleep(0.005)
for i in range(count):
    ledger.append(LedgerEntry(
        ts="2026-11-10T00:00:00Z", provider="gnani", kind="stt", model=tag, status=200, attempt=i + 1,
        seconds=0.1, cache_hit=False, cache_key="k" * 64, est_credits=1.0, error_code="x" * 300,
    ))
"""


def test_ledger_concurrent_appends_from_processes_never_interleave(tmp_path: Path) -> None:
    n_procs, n_lines = 6, 200
    path, go = tmp_path / "ledger.jsonl", tmp_path / "go"
    ready = [tmp_path / f"ready{i}" for i in range(n_procs)]
    procs = [spawn(LEDGER_WRITER, path, f"w{i}", n_lines, ready[i], go) for i in range(n_procs)]
    wait_for(ready)
    go.touch()
    wait_all(procs)

    raw = path.read_bytes().splitlines()
    assert len(raw) == n_procs * n_lines
    parsed = [LedgerEntry.model_validate_json(line) for line in raw]
    seen = {(e.model, e.attempt) for e in parsed}
    assert seen == {(f"w{i}", j + 1) for i in range(n_procs) for j in range(n_lines)}
    assert Ledger(path).total_credits() == pytest.approx(n_procs * n_lines)


# ---------------------------------------------------------------- single flight

LOCK_WORKER = """
import os, sys, time
from pathlib import Path
from samajh.clients._runtime import single_flight
lock, log, ready, go = (Path(a) for a in sys.argv[1:5])
rounds, hold = int(sys.argv[5]), float(sys.argv[6])
ready.touch()
while not go.exists():
    time.sleep(0.005)
for _ in range(rounds):
    with single_flight(lock, timeout=30):
        entered = time.time()
        time.sleep(hold)
        left = time.time()
        with log.open("a") as f:
            f.write(f"{os.getpid()} {entered!r} {left!r}\\n")
"""


def test_single_flight_excludes_across_processes(tmp_path: Path) -> None:
    n_procs, rounds, hold = 2, 3, 0.2
    lock, log, go = tmp_path / "locks" / "gnani.lock", tmp_path / "log", tmp_path / "go"
    ready = [tmp_path / f"ready{i}" for i in range(n_procs)]
    procs = [spawn(LOCK_WORKER, lock, log, ready[i], go, rounds, hold) for i in range(n_procs)]
    wait_for(ready)
    go.touch()
    wait_all(procs)

    records = [line.split() for line in log.read_text().splitlines()]
    assert len(records) == n_procs * rounds
    assert len({pid for pid, _, _ in records}) == n_procs
    intervals = sorted((float(entered), float(left)) for _, entered, left in records)
    for entered, left in intervals:
        assert left - entered >= hold
    for (_, left), (next_entered, _) in itertools.pairwise(intervals):
        assert left <= next_entered, intervals


def test_single_flight_excludes_across_threads(tmp_path: Path) -> None:
    lock = tmp_path / "t.lock"
    guard = threading.Lock()
    inside = 0
    peak = 0
    errors: list[LockTimeout] = []

    def work() -> None:
        nonlocal inside, peak
        try:
            for _ in range(3):
                with single_flight(lock, timeout=30):
                    with guard:
                        inside += 1
                        peak = max(peak, inside)
                    time.sleep(0.03)
                    with guard:
                        inside -= 1
        except LockTimeout as exc:
            errors.append(exc)

    threads = [threading.Thread(target=work) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert errors == []
    assert not any(t.is_alive() for t in threads)
    assert peak == 1


def test_single_flight_times_out_against_a_thread_in_the_same_process(tmp_path: Path) -> None:
    lock = tmp_path / "t.lock"
    outcome: list[str] = []

    def contender() -> None:
        try:
            with single_flight(lock, timeout=0.2):
                outcome.append("acquired")
        except LockTimeout:
            outcome.append("timeout")

    with single_flight(lock, timeout=5):
        t = threading.Thread(target=contender)
        t.start()
        t.join(timeout=10)
    assert outcome == ["timeout"]


LOCK_HOLDER = """
import sys
from pathlib import Path
from samajh.clients._runtime import single_flight
with single_flight(Path(sys.argv[1]), timeout=10):
    Path(sys.argv[2]).touch()
    sys.stdin.read()
"""


def test_single_flight_lock_timeout_when_another_process_holds_it(tmp_path: Path) -> None:
    lock, ready = tmp_path / "gnani.lock", tmp_path / "ready"
    holder = spawn(LOCK_HOLDER, lock, ready)
    try:
        wait_for([ready])
        started = time.monotonic()
        with pytest.raises(LockTimeout), single_flight(lock, timeout=0.3):
            pytest.fail("entered the critical section while another process held the lock")
        assert 0.25 <= time.monotonic() - started < 5
    finally:
        wait_all([holder])
    with single_flight(lock, timeout=5):
        pass


def test_single_flight_releases_when_the_body_raises(tmp_path: Path) -> None:
    lock = tmp_path / "t.lock"
    with pytest.raises(RuntimeError), single_flight(lock, timeout=1):
        raise RuntimeError("boom")
    with single_flight(lock, timeout=1):
        pass


# ---------------------------------------------------------------- retry policy


@pytest.mark.parametrize(
    ("attempt", "d"),
    [(1, 1.0), (2, 2.0), (3, 4.0), (4, 8.0), (5, 16.0), (6, 30.0), (7, 30.0), (20, 30.0)],
)
def test_delay_stays_in_equal_jitter_bounds(attempt: int, d: float) -> None:
    policy = RetryPolicy()
    rng = random.Random(7)
    delays = [policy.delay(attempt, None, rng) for _ in range(300)]
    assert all(d / 2 <= x <= d for x in delays)
    assert max(delays) - min(delays) > d / 4


def test_delay_is_reproducible_with_a_seeded_rng() -> None:
    policy = RetryPolicy(base_delay=0.5, max_delay=4.0)
    a = [policy.delay(n, None, random.Random(3)) for n in range(1, 6)]
    b = [policy.delay(n, None, random.Random(3)) for n in range(1, 6)]
    assert a == b


def test_delay_retry_after_raises_the_floor_up_to_the_cap() -> None:
    policy = RetryPolicy()
    rng = random.Random(1)
    assert all(policy.delay(1, 12.0, rng) == 12.0 for _ in range(50))
    assert all(policy.delay(1, 120.0, rng) == 30.0 for _ in range(50))
    assert all(4.0 <= policy.delay(4, 0.1, rng) <= 8.0 for _ in range(50))


# ---------------------------------------------------------------- send_with_retry


def response(status: int, *, code: str | None = None, headers: dict[str, str] | None = None) -> httpx.Response:
    body = {"error": {"code": code, "message": f"status {status}"}} if code else {"ok": True}
    return httpx.Response(status, json=body, headers=headers)


def parse_error(resp: httpx.Response) -> tuple[str | None, str]:
    error = resp.json().get("error", {})
    return error.get("code"), error.get("message", "")


class Harness:
    """Scripted `send` plus recorders for sleeps and attempts."""

    def __init__(self, *script: httpx.Response | Exception, max_attempts: int = 4) -> None:
        self.script = list(script)
        self.policy = RetryPolicy(max_attempts=max_attempts, base_delay=1.0, max_delay=30.0)
        self.calls = 0
        self.sleeps: list[float] = []
        self.attempts: list[Attempt] = []
        self.events: list[str] = []

    def send(self) -> httpx.Response:
        item = self.script[self.calls]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item

    def on_attempt(self, attempt: Attempt) -> None:
        self.attempts.append(attempt)
        self.events.append("attempt")

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.events.append("sleep")

    def run(self) -> httpx.Response:
        return send_with_retry(
            self.send,
            policy=self.policy,
            parse_error=parse_error,
            on_attempt=self.on_attempt,
            sleep=self.sleep,
            rng=random.Random(0),
        )

    @property
    def statuses(self) -> list[object]:
        return [a.status for a in self.attempts]


def test_retry_success_first_time() -> None:
    ok = response(200)
    h = Harness(ok)
    assert h.run() is ok
    assert (h.calls, h.sleeps, h.statuses) == (1, [], [200])
    only = h.attempts[0]
    assert (only.number, only.error_code, only.response) == (1, None, ok)
    assert only.seconds >= 0


def test_retry_429_then_200() -> None:
    ok = response(200)
    h = Harness(response(429, code="RATE_LIMITED"), ok)
    assert h.run() is ok
    assert h.statuses == [429, 200]
    assert [a.number for a in h.attempts] == [1, 2]
    assert [a.error_code for a in h.attempts] == ["RATE_LIMITED", None]
    assert h.events == ["attempt", "sleep", "attempt"]
    assert len(h.sleeps) == 1 and 0.5 <= h.sleeps[0] <= 1.0


def test_retry_504_until_budget_spent_raises_server_error() -> None:
    h = Harness(*[response(504, code="GATEWAY_TIMEOUT")] * 4)
    with pytest.raises(ServerError) as info:
        h.run()
    assert (info.value.status, info.value.code, info.value.attempts) == (504, "GATEWAY_TIMEOUT", 4)
    assert info.value.message == "status 504"
    assert h.calls == 4
    assert h.statuses == [504] * 4
    assert len(h.sleeps) == 3
    assert h.events == ["attempt", "sleep"] * 3 + ["attempt"]
    for n, slept in enumerate(h.sleeps, start=1):
        assert 2 ** (n - 1) / 2 <= slept <= 2 ** (n - 1)


def test_retry_429_until_budget_spent_raises_rate_limited() -> None:
    h = Harness(*[response(429, code="RATE_LIMITED")] * 4)
    with pytest.raises(RateLimited) as info:
        h.run()
    assert (info.value.status, info.value.code, info.value.attempts) == (429, "RATE_LIMITED", 4)
    assert not isinstance(info.value, ServerError)
    assert len(h.sleeps) == 3


def test_retry_connect_timeout_until_budget_spent_raises_transport_error() -> None:
    h = Harness(*[httpx.ConnectTimeout("timed out")] * 4)
    with pytest.raises(TransportError) as info:
        h.run()
    assert isinstance(info.value.__cause__, httpx.ConnectTimeout)
    assert h.calls == 4
    assert h.statuses == ["transport_error"] * 4
    assert all(a.response is None for a in h.attempts)
    assert len(h.sleeps) == 3


def test_retry_treats_a_body_that_does_not_decode_as_a_transport_error() -> None:
    ok = response(200)
    h = Harness(httpx.DecodingError("bad gzip"), ok)
    assert h.run() is ok
    assert h.statuses == ["transport_error", 200] and h.attempts[0].error_code == "DecodingError"

    h = Harness(*[httpx.DecodingError("bad gzip")] * 4)
    with pytest.raises(TransportError) as info:
        h.run()
    assert isinstance(info.value.__cause__, httpx.DecodingError)
    assert h.statuses == ["transport_error"] * 4 and len(h.sleeps) == 3


def test_retry_recovers_after_transport_error_and_mixed_failures() -> None:
    ok = response(200)
    h = Harness(httpx.ReadTimeout("slow"), response(503), ok)
    assert h.run() is ok
    assert h.statuses == ["transport_error", 503, 200]
    assert len(h.sleeps) == 2


def test_retry_final_error_reflects_the_last_attempt() -> None:
    h = Harness(response(429, code="RATE_LIMITED"), response(500), max_attempts=2)
    with pytest.raises(ServerError) as info:
        h.run()
    assert (info.value.status, info.value.attempts) == (500, 2)


def test_retry_400_raises_api_error_at_once() -> None:
    h = Harness(response(400, code="INVALID_ARGUMENT"), response(200))
    with pytest.raises(ApiError) as info:
        h.run()
    assert type(info.value) is ApiError
    assert (info.value.status, info.value.code, info.value.attempts) == (400, "INVALID_ARGUMENT", 1)
    assert (h.calls, h.sleeps, h.statuses) == (1, [], [400])


@pytest.mark.parametrize("status", [401, 403])
def test_retry_auth_failure_raises_auth_error_at_once(status: int) -> None:
    h = Harness(response(status, code="UNAUTHORIZED"), response(200))
    with pytest.raises(AuthError) as info:
        h.run()
    assert (info.value.status, info.value.attempts) == (status, 1)
    assert (h.calls, h.sleeps) == (1, [])


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_retry_every_retryable_status_is_retried(status: int) -> None:
    h = Harness(response(status), response(200))
    assert h.run().status_code == 200
    assert h.statuses == [status, 200]


def test_retry_honours_numeric_retry_after() -> None:
    h = Harness(
        response(429, headers={"Retry-After": "7"}),
        response(429, headers={"Retry-After": "600"}),
        response(429, headers={"Retry-After": "Wed, 11 Nov 2026 07:28:00 GMT"}),
        response(200),
    )
    h.run()
    assert h.sleeps[0] == 7.0
    assert h.sleeps[1] == 30.0
    assert 2.0 <= h.sleeps[2] <= 4.0


def test_retry_on_attempt_called_once_per_attempt_with_status() -> None:
    h = Harness(httpx.ConnectError("refused"), response(502), response(429, code="RATE_LIMITED"), response(200))
    h.run()
    assert h.calls == len(h.attempts) == 4
    assert [a.number for a in h.attempts] == [1, 2, 3, 4]
    assert h.statuses == ["transport_error", 502, 429, 200]
    assert [a.response.status_code if a.response else None for a in h.attempts] == [None, 502, 429, 200]


def test_retry_single_attempt_budget_never_sleeps() -> None:
    h = Harness(response(503), max_attempts=1)
    with pytest.raises(ServerError) as info:
        h.run()
    assert (info.value.attempts, h.sleeps) == (1, [])


def test_ledger_line_is_plain_json(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    Ledger(path).append(row(est_credits=1.0))
    assert json.loads(path.read_text())["est_credits"] == 1.0
    assert path.stat().st_mode & 0o777 == 0o600
