"""Shared runtime for the API clients: state directory, content-addressed cache, ledger,
cross-process single-flight lock, and the retry loop.

Call sequence every client follows (the reason these pieces exist):

    key = cache_key(namespace, params, payload)
    hit = cache.get(key)                 -> ledger row (cache_hit=True), return; no network, no lock
    with single_flight(lock_path):       (Gnani only: the key allows one request in flight)
        hit = cache.get(key)             (another process may have fetched it while we waited)
        cap check against the ledger     -> CapExceeded before any network I/O
        resp = send_with_retry(...)      -> one ledger row per attempt
        value = parse(resp)              -> BadResponse; nothing cached
        cache.put(key, ...)              (only parsed successes are cached)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import tempfile
import time
import tomllib
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import filelock
import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, ValidationError

from samajh.clients.errors import (
    ApiError,
    AuthError,
    ConfigError,
    LockTimeout,
    RateLimited,
    ServerError,
    TransportError,
)

RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})


def state_dir() -> Path:
    """`$SAMAJH_STATE_DIR` if set, else `<repo root>/.samajh`. Created on demand by the users below."""
    override = os.environ.get("SAMAJH_STATE_DIR")
    return Path(override) if override else Path(__file__).resolve().parents[2] / ".samajh"


def load_env() -> None:
    """Load `<repo root>/.env` into the environment. Variables that are already set win."""
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def load_defaults() -> dict[str, Any]:
    """Parse `samajh/clients/defaults.toml` (measured rates, default model ids)."""
    with (Path(__file__).parent / "defaults.toml").open("rb") as f:
        return tomllib.load(f)


# ---------------------------------------------------------------- cache


def cache_key(namespace: str, params: Mapping[str, Any], payload: bytes) -> str:
    """Hex sha256 of: canonical JSON of {"ns": namespace, "params": params} + NUL + sha256(payload).

    Canonical JSON: sort_keys, compact separators, ensure_ascii=False, UTF-8. `params` must be
    JSON-serialisable and must hold every value that can change the response (model, endpoint
    version, every request option). It must never hold a key or header. `payload` is the audio
    bytes or the UTF-8 text, hashed separately so params and payload cannot bleed into each other.
    """
    head = json.dumps(
        {"ns": namespace, "params": params}, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    digest = hashlib.sha256(payload).hexdigest()
    return hashlib.sha256(head.encode("utf-8") + b"\0" + digest.encode("ascii")).hexdigest()


def check_api_key(api_key: str, name: str) -> None:
    """Raise `ConfigError` (without the key in it) unless the key is printable ASCII with no spaces.

    httpx refuses such a header value with an error that prints the whole value.
    """
    if not api_key or not all(33 <= ord(ch) <= 126 for ch in api_key):
        raise ConfigError(f"{name} API key is empty or has whitespace, control or non-ASCII characters")


def _write_atomic(path: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


@dataclass(frozen=True)
class CacheEntry:
    meta: dict[str, Any]
    body: bytes


class Cache:
    """Files under `root/<key[:2]>/<key>.bin` (body) and `<key>.json` (meta, written last).

    The meta file is the commit marker: `get` returns None unless both files exist and the meta
    parses. Writes are atomic (temp file in the same directory, then `os.replace`), so a crash or
    a concurrent writer never leaves a half entry that reads as a hit.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def _stem(self, key: str) -> Path:
        return self.root / key[:2] / key

    def get(self, key: str) -> CacheEntry | None:
        stem = self._stem(key)
        try:
            meta = json.loads(stem.with_suffix(".json").read_bytes())
            body = stem.with_suffix(".bin").read_bytes()
        except (OSError, ValueError):
            return None
        return CacheEntry(meta=meta, body=body) if isinstance(meta, dict) else None

    def put(self, key: str, meta: Mapping[str, Any], body: bytes) -> None:
        stem = self._stem(key)
        stem.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(stem.with_suffix(".bin"), body)
        _write_atomic(stem.with_suffix(".json"), json.dumps(dict(meta), ensure_ascii=False).encode("utf-8"))


# ---------------------------------------------------------------- ledger


class LedgerEntry(BaseModel):
    """One line of `.samajh/ledger.jsonl`: one attempt, or one cache hit. Never holds a secret."""

    model_config = ConfigDict(extra="forbid")

    ts: str  # UTC ISO 8601
    provider: Literal["gnani", "openrouter"]
    kind: str  # "stt" | "tts" | "batch" | "chat"
    model: str
    status: int | Literal["cache_hit", "transport_error"]
    attempt: int  # 1-based; 0 for a cache hit
    seconds: float  # wall time of this attempt
    cache_hit: bool
    cache_key: str
    est_credits: float = 0.0  # Gnani: estimated, 0 unless the attempt succeeded
    usd: float = 0.0  # OpenRouter: cost reported by the response; an estimate when error_code is cost_missing
    audio_seconds: float | None = None
    chars: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    error_code: str | None = None


class Ledger:
    """Append-only JSONL. Each append is one `os.write` on an `O_APPEND` descriptor, so lines from
    concurrent processes never interleave. Lines that do not parse are skipped when reading."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, entry: LedgerEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, entry.model_dump_json().encode("utf-8") + b"\n")
        finally:
            os.close(fd)

    def entries(self) -> Iterator[LedgerEntry]:
        try:
            lines = self.path.read_bytes().splitlines()
        except FileNotFoundError:
            return
        for line in lines:
            try:
                yield LedgerEntry.model_validate_json(line)
            except ValidationError:
                continue

    def total_credits(self) -> float:
        """Sum of `est_credits` over Gnani rows (the number the credit guard compares to the cap)."""
        return sum(e.est_credits for e in self.entries() if e.provider == "gnani")

    def total_usd(self) -> float:
        return sum(e.usd for e in self.entries())


# ---------------------------------------------------------------- single flight


@contextmanager
def single_flight(lock_path: Path, *, timeout: float) -> Iterator[None]:
    """Hold an exclusive OS file lock. Safe across processes and across threads.

    Raises `LockTimeout` if the lock is not acquired within `timeout` seconds. The lock is held
    for a whole call including its backoff sleeps, so only one caller on the machine is ever
    talking to (or retrying against) the key.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # A fresh, non-thread-local lock per call: filelock is re-entrant per instance, so a shared
    # instance would let a second thread straight in. fallback_to_soft=False fails closed on a
    # filesystem without flock instead of degrading to an existence lock.
    lock = filelock.FileLock(lock_path, mode=0o600, thread_local=False, fallback_to_soft=False)
    try:
        lock.acquire(timeout=timeout)
    except filelock.Timeout:
        raise LockTimeout(f"no lock on {lock_path} within {timeout:g}s") from None
    try:
        yield
    finally:
        lock.release()


# ---------------------------------------------------------------- retry


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay: float = 1.0
    max_delay: float = 30.0

    def delay(self, attempt: int, retry_after: float | None, rng: random.Random) -> float:
        """Seconds to sleep after failed attempt `attempt` (1-based).

        Equal jitter: d = min(max_delay, base_delay * 2**(attempt-1)); sleep d/2 + U(0, d/2).
        A `Retry-After` value raises the floor, capped at `max_delay`.
        """
        d = min(self.max_delay, self.base_delay * 2 ** (attempt - 1))
        wait = d / 2 + rng.uniform(0, d / 2)
        if retry_after is not None:
            wait = max(wait, min(retry_after, self.max_delay))
        return wait


@dataclass(frozen=True)
class Attempt:
    """What the retry loop tells the client about each attempt, for the ledger."""

    number: int  # 1-based
    seconds: float
    status: int | Literal["transport_error"]
    error_code: str | None
    response: httpx.Response | None  # set when the server answered


def send_with_retry(
    send: Callable[[], httpx.Response],
    *,
    policy: RetryPolicy,
    parse_error: Callable[[httpx.Response], tuple[str | None, str]],
    on_attempt: Callable[[Attempt], None],
    sleep: Callable[[float], None],
    rng: random.Random,
) -> httpx.Response:
    """Call `send` until it returns 2xx, a non-retryable status, or the budget is spent.

    - 2xx: return the response.
    - status in RETRYABLE_STATUS, `httpx.TransportError` or `httpx.DecodingError` (a body that
      does not decompress): sleep `policy.delay(...)` and retry,
      at most `policy.max_attempts` attempts in total. After the last one raise `RateLimited`
      (429), `ServerError` (other retryable status) or `TransportError`.
    - 401/403: raise `AuthError` at once. Any other status: raise `ApiError` at once.
    `parse_error(response)` returns (code, message) from the provider's error body and must not
    raise. `on_attempt` is called exactly once per attempt, before any sleep. No sleep follows
    the final attempt.
    """
    number = 0
    while True:
        number += 1
        last = number >= policy.max_attempts
        started = time.monotonic()
        try:
            response = send()
        except (httpx.TransportError, httpx.DecodingError) as exc:
            name = type(exc).__name__
            on_attempt(Attempt(number, time.monotonic() - started, "transport_error", name, None))
            if last:
                # Only the class name: an httpx message can carry the request URL.
                raise TransportError(f"{name} on all {number} attempts") from exc
            sleep(policy.delay(number, None, rng))
            continue
        seconds = time.monotonic() - started
        status = response.status_code
        if 200 <= status < 300:
            on_attempt(Attempt(number, seconds, status, None, response))
            return response
        code, message = parse_error(response)
        on_attempt(Attempt(number, seconds, status, code, response))
        if status in RETRYABLE_STATUS and not last:
            sleep(policy.delay(number, _retry_after(response), rng))
            continue
        if status == 429:
            error = RateLimited
        elif status in RETRYABLE_STATUS:
            error = ServerError
        elif status in (401, 403):
            error = AuthError
        else:
            error = ApiError
        raise error(status=status, code=code, message=message, attempts=number)


def _retry_after(response: httpx.Response) -> float | None:
    """The numeric form only; an HTTP-date `Retry-After` is ignored."""
    try:
        value = float(response.headers.get("retry-after", ""))
    except ValueError:
        return None
    return value if math.isfinite(value) and value >= 0 else None


__all__ = [
    "RETRYABLE_STATUS",
    "ApiError",
    "Attempt",
    "Cache",
    "CacheEntry",
    "Ledger",
    "LedgerEntry",
    "RetryPolicy",
    "cache_key",
    "check_api_key",
    "load_defaults",
    "load_env",
    "send_with_retry",
    "single_flight",
    "state_dir",
]
