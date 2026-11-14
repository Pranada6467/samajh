"""Prisma WebSocket streaming STT (`/stt/v3/stream`) for one customer turn.

The caller (the browser's VAD, through the server) owns the end of speech: it streams PCM with
`send` and ends the turn with `commit`. An open streaming session does not occupy the account's one
REST request slot (measured, api-probe-iter1.md section 5), so this path never takes
`gnani.lock` and never uses the cache. It keeps the client's ledger and credit cap: one
`stt.stream` row per session, written when the session closes.

Billing of streaming is unknown: `est_credits` is the audio seconds sent times the REST STT rate,
an estimate only.

Protocol (verified live in iteration 1, tests/server/probes/turn_taking_probe.py): settings go in
the upgrade headers; the server's first message is a greeting; audio is binary PCM s16le mono in
1,024-byte frames; `{"type": "commit"}` asks for the final; the server sends `speech_start`,
`transcript` (`text`), `error` and `session_end`; close 1008 is a refusal.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field

from samajh.clients._runtime import Ledger, LedgerEntry
from samajh.clients.errors import CapExceeded, ClientError

STREAM_PATH = "/stt/v3/stream"
FRAME_BYTES = 1024
OPEN_ESTIMATE_SECONDS = 30.0  # the cap is checked against one 30 s turn before a session opens


class StreamError(ClientError):
    """The server sent an `error` message, closed the socket, or could not be reached."""

    def __init__(self, *, code: str | int | None, message: str) -> None:
        self.code, self.message = code, message
        super().__init__(f"stream error {code or ''}: {message}")


class StreamTimeout(StreamError):
    """`commit` got no final transcript within its timeout (the server can stay silent)."""


class StreamBudgetExceeded(CapExceeded):
    """The streaming-seconds budget (`max_stream_seconds`) is used up."""


class PrismaStream(BaseModel):
    """Exactly what goes in the upgrade headers. `language` is one locale: v3.0 streaming rejects a
    comma-separated list ("exactly one locale is required", close 1008, 13 of 13 in iteration 1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    model: Literal["prisma-v3.0", "prisma-v2.5"] = "prisma-v3.0"
    language: str = "hi-IN"
    multi_lang: tuple[str, ...] | None = None  # sent as the `multi_lang_codes` header
    format: Literal["verbatim", "transcribe", "codemix", "transliterate"] = "transcribe"
    sample_rate: Literal[8000, 16000] = 8000
    min_silence_ms: int | None = Field(default=2000, ge=0)
    idle_timeout_s: int | None = Field(default=None, ge=1)
    extra_headers: tuple[tuple[str, str], ...] = ()  # for probes only

    def headers(self, api_key: str) -> dict[str, str]:
        h = {
            "x-api-key-id": api_key,
            "model": self.model,
            "language_code": self.language,
            "x-sample-rate": str(self.sample_rate),
            "format": self.format,
        }
        if self.multi_lang:
            h["multi_lang_codes"] = ",".join(self.multi_lang)
        if self.min_silence_ms is not None:
            h["x-min-silence-ms"] = str(self.min_silence_ms)
        if self.idle_timeout_s is not None:
            h["x-idle-timeout-sec"] = str(self.idle_timeout_s)
        h.update(dict(self.extra_headers))
        return h


def stream_language(
    call_language: str, *, model: Literal["prisma-v3.0", "prisma-v2.5"] = "prisma-v3.0"
) -> PrismaStream:
    """Stream options for a call language (`hi`, `hi-en`, `ta`, `kn`).

    Hinglish, probed live on 2026-11-14 (tests/clients/probes/stream_live.py; 2 Hinglish Timbre
    clips, prisma-v3.0, 8 kHz): `language_code=hi-IN` alone gave text identical to REST v3.0 with
    `hi-IN,en-IN` on 2 of 2; adding the header `multi_lang_codes=hi-IN,en-IN` was accepted (no
    error) and changed nothing on 2 of 2; `en-IN` romanised the Hindi words on 2 of 2. So `hi-en`
    streams as `hi-IN`. TTS audio only, n = 2.
    """
    locale = {"hi": "hi-IN", "hi-en": "hi-IN", "ta": "ta-IN", "kn": "kn-IN"}[call_language]
    return PrismaStream(model=model, language=locale)


@dataclass(frozen=True)
class StreamResult:
    text: str  # every transcript segment of the session, in order, joined by a space
    segments: tuple[str, ...]
    split: bool  # more than one segment
    open_ms: float
    first_byte_to_final_ms: float | None  # first audio frame sent to the last final
    commit_to_final_ms: float | None  # from `commit` being called to the last final
    audio_seconds: float
    flush_ms: float | None = None  # from `commit` being called to the commit leaving (queued frames first)


class _Socket(Protocol):
    async def send(self, message: str | bytes) -> None: ...
    async def recv(self) -> str | bytes: ...
    async def close(self) -> None: ...


Connect = Callable[[str, dict[str, str]], Awaitable[_Socket]]


async def _websockets_connect(url: str, headers: dict[str, str]) -> _Socket:
    import websockets

    return await websockets.connect(url, additional_headers=headers, open_timeout=10)  # type: ignore[return-value]


@dataclass
class _State:
    finals: list[tuple[float, str]] = field(default_factory=list)
    error: StreamError | None = None
    closed: bool = False


class StreamSession:
    """One streaming turn. Thread-safe for one caller thread; the socket runs on its own loop thread.

    `send` never blocks on the network: frames are queued to the loop. Use as a context manager, or
    call `abort` on every path that does not reach `commit`.
    """

    def __init__(
        self,
        *,
        url: str,
        options: PrismaStream,
        api_key: str,
        ledger: Ledger,
        stt_rate: float,
        before_open: Callable[[], None] = lambda: None,
        connect: Connect | None = None,
    ) -> None:
        self._url, self._options, self._key = url, options, api_key
        self._ledger, self._rate, self._before_open = ledger, stt_rate, before_open
        self._connect = connect or _websockets_connect
        self._buffer = b""
        self._bytes_sent = 0
        self._hash = hashlib.sha256()
        self._state = _State()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._sock: _Socket | None = None
        self._reader: asyncio.Task[None] | None = None
        self._open_ms = 0.0
        self._first_frame_at: float | None = None
        self._billed = False
        self._finish_lock = threading.Lock()
        self._started = 0.0

    # ---------------------------------------------------------------- public

    def open(self, timeout_s: float = 10.0) -> StreamSession:
        self._before_open()  # cap and budget: raises before any network I/O
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True, name="gnani-stream")
        self._thread.start()
        self._started = time.monotonic()
        try:
            self._run(self._aopen(), timeout_s)
        except Exception as exc:  # noqa: BLE001 - any failure becomes a StreamError
            self._finish(error=self._as_error(exc))
            raise self._as_error(exc) from None
        self._open_ms = (time.monotonic() - self._started) * 1000
        return self

    def send(self, pcm: bytes) -> None:
        """Never blocks: after an upstream error it raises at once and closes the socket (up to
        2 s) on a background thread, since callers send from an event loop."""
        if self._sock is not None and not self._billed and self._state.error:
            err = self._state.error
            threading.Thread(target=self._finish, kwargs={"error": err}, daemon=True).start()
            raise err
        self._raise_if_failed()
        self._buffer += pcm
        cut = len(self._buffer) - len(self._buffer) % FRAME_BYTES
        frames, self._buffer = self._buffer[:cut], self._buffer[cut:]
        if frames:
            self._queue_frames([frames[i : i + FRAME_BYTES] for i in range(0, len(frames), FRAME_BYTES)])

    def commit(self, timeout_s: float = 3.0, *, close: bool = True) -> StreamResult:
        """Ask for the final and wait for it. With `close=False` the socket stays open (and the
        ledger row unwritten) until `close`, so the caller has the text before the close handshake."""
        requested_at = time.monotonic()
        self._raise_if_failed()
        if self._buffer:
            self._queue_frames([self._buffer + bytes(FRAME_BYTES - len(self._buffer))])
            self._buffer = b""
        try:
            sent_at, last_at = self._run(self._acommit(timeout_s), timeout_s + 5)
        except Exception as exc:  # noqa: BLE001 - any failure becomes a StreamError
            err = self._as_error(exc)
            self._finish(error=err)
            raise err from None
        finals = tuple(t for _, t in self._state.finals)
        if close:
            self._finish(error=None)
        return StreamResult(
            text=" ".join(s for s in finals if s).strip(),
            segments=finals,
            split=len(finals) > 1,
            open_ms=round(self._open_ms, 1),
            first_byte_to_final_ms=None
            if self._first_frame_at is None
            else round((last_at - self._first_frame_at) * 1000, 1),
            commit_to_final_ms=round((last_at - requested_at) * 1000, 1),
            audio_seconds=self.audio_seconds,
            flush_ms=round((sent_at - requested_at) * 1000, 1),
        )

    def close(self) -> None:
        """After `commit(close=False)`: close the socket and write the ledger row (no error)."""
        if self._loop is not None:
            self._finish(error=None)

    def abort(self) -> None:
        if self._loop is None:
            return  # never opened: nothing sent, nothing to bill
        self._finish(error=None if self._billed else StreamError(code="aborted", message="aborted"))

    @property
    def audio_seconds(self) -> float:
        return self._bytes_sent / 2 / self._options.sample_rate

    def __enter__(self) -> Self:
        return self.open() if self._sock is None else self

    def __exit__(self, *exc: object) -> None:
        self.abort()

    # ---------------------------------------------------------------- loop side

    def _run(self, coro: Awaitable[Any], timeout: float) -> Any:
        assert self._loop is not None
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout)  # type: ignore[arg-type]

    async def _aopen(self) -> None:
        url = self._url
        self._sock = await self._connect(url, self._options.headers(self._key))
        first = await self._sock.recv()
        self._handle(first)  # a refusal can come as the first message
        if self._state.error:
            raise self._state.error
        self._reader = asyncio.get_running_loop().create_task(self._read())

    async def _read(self) -> None:
        assert self._sock is not None
        try:
            while True:
                self._handle(await self._sock.recv())
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - any close ends the session
            code = getattr(getattr(exc, "rcvd", None), "code", None)
            reason = getattr(getattr(exc, "rcvd", None), "reason", "") or type(exc).__name__
            self._state.closed = True
            if self._state.error is None and code not in (1000, 1001):
                self._state.error = StreamError(code=code, message=self._redact(str(reason))[:300])

    def _handle(self, raw: str | bytes) -> None:
        try:
            message = json.loads(raw)
        except (ValueError, TypeError):
            return
        if not isinstance(message, dict):
            return
        kind = message.get("type")
        if kind == "transcript":
            self._state.finals.append((time.monotonic(), str(message.get("text", "")).strip()))
        elif kind == "error":
            self._state.error = StreamError(
                code=self._redact(str(message.get("code") or "error")),
                message=self._redact(str(message.get("message") or message.get("error") or message))[:300],
            )

    def _queue_frames(self, frames: list[bytes]) -> None:
        """One loop hop for all the frames of one `send`, in order."""
        assert self._loop is not None
        if self._first_frame_at is None:
            self._first_frame_at = time.monotonic()
        for frame in frames:
            self._bytes_sent += len(frame)
            self._hash.update(frame)
        asyncio.run_coroutine_threadsafe(self._asend_many(frames), self._loop)

    async def _asend_many(self, frames: list[bytes]) -> None:
        for frame in frames:
            await self._asend(frame)

    async def _asend(self, message: str | bytes) -> None:
        if self._sock is None or self._state.closed or self._state.error:
            return
        try:
            await self._sock.send(message)
        except Exception as exc:  # noqa: BLE001
            if self._state.error is None:
                self._state.error = StreamError(code="send_failed", message=type(exc).__name__)

    async def _acommit(self, timeout_s: float) -> tuple[float, float]:
        before = len(self._state.finals)
        await self._asend(json.dumps({"type": "commit"}))  # queued after every frame (FIFO loop)
        sent_at = time.monotonic()
        deadline = sent_at + timeout_s
        while time.monotonic() < deadline:
            if self._state.error:
                raise self._state.error
            if len(self._state.finals) > before:
                return sent_at, self._state.finals[-1][0]
            if self._state.closed:
                break
            await asyncio.sleep(0.01)
        raise StreamTimeout(code="commit_timeout", message=f"no final transcript within {timeout_s:g}s")

    async def _aclose(self) -> None:
        if self._reader:
            self._reader.cancel()
        if self._sock is not None:
            try:
                await asyncio.wait_for(self._sock.close(), 2)
            except Exception:  # noqa: BLE001, S110 - closing is best effort
                pass

    # ---------------------------------------------------------------- helpers

    def _raise_if_failed(self) -> None:
        if self._sock is None or self._billed:
            raise StreamError(code="not_open", message="session is not open")
        if self._state.error:
            err = self._state.error
            self._finish(error=err)
            raise err

    def _redact(self, text: str) -> str:
        return text.replace(self._key, "<key>")

    def _as_error(self, exc: BaseException) -> StreamError:
        if isinstance(exc, StreamError):
            return exc
        if isinstance(exc, TimeoutError | asyncio.TimeoutError):
            return StreamTimeout(code="timeout", message="stream operation timed out")
        code = getattr(getattr(exc, "rcvd", None), "code", None) or type(exc).__name__
        return StreamError(code=code, message=self._redact(str(exc))[:300])

    def _finish(self, *, error: StreamError | None) -> None:
        """Close the socket and stop the loop; write the ledger row exactly once."""
        with self._finish_lock:
            if self._billed:
                return
            self._billed = True
        if self._loop is not None:
            try:
                self._run(self._aclose(), 5)
            except Exception:  # noqa: BLE001, S110 - closing is best effort
                pass
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread:
                self._thread.join(2)
        seconds = self.audio_seconds
        code = None if error is None else str(error.code)
        status = 101 if error is None else (error.code if isinstance(error.code, int) else 0)
        self._ledger.append(
            LedgerEntry(
                ts=datetime.now(UTC).isoformat(timespec="seconds"),
                provider="gnani",
                kind="stt.stream",
                model=self._options.model,
                status=status,
                attempt=1,
                seconds=round(time.monotonic() - self._started, 4) if self._started else 0.0,
                cache_hit=False,
                cache_key=self._hash.hexdigest() if self._bytes_sent else "",
                est_credits=round(seconds * self._rate, 6),
                audio_seconds=round(seconds, 3),
                error_code=code,
            )
        )


def stream_session(
    client: Any,
    options: PrismaStream,
    *,
    max_stream_seconds: float | None = None,
    connect: Connect | None = None,
) -> StreamSession:
    """A `StreamSession` that reuses a `GnaniClient`'s key, base URL, ledger, cap and STT rate.

    Before opening: the credit cap is checked against `OPEN_ESTIMATE_SECONDS` of audio, and, when
    `max_stream_seconds` is set, the sum of `audio_seconds` over `stt.stream` ledger rows must be
    below it. Takes no lock and uses no cache.
    """
    base = client._base_url
    url = (
        "wss://" + base[len("https://") :]
        if base.startswith("https://")
        else "ws://" + base[len("http://") :]
        if base.startswith("http://")
        else base
    ) + STREAM_PATH
    ledger: Ledger = client._ledger

    def before_open() -> None:
        client._check_cap(OPEN_ESTIMATE_SECONDS * client._stt_rate)
        if max_stream_seconds is not None:
            used = client._tally.stream_seconds()
            if used >= max_stream_seconds:
                raise StreamBudgetExceeded(
                    unit="stream_seconds", cap=max_stream_seconds, spent=used, estimate=OPEN_ESTIMATE_SECONDS
                )

    return StreamSession(
        url=url,
        options=options,
        api_key=client._api_key,
        ledger=ledger,
        stt_rate=client._stt_rate,
        before_open=before_open,
        connect=connect,
    )
