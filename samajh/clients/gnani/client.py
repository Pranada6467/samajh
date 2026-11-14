"""The only door to the Gnani speech APIs: cache, cross-process single flight, retry, ledger, cap.

The key allows one request in flight, so every request to the API host holds `<state>/gnani.lock`.
"""

from __future__ import annotations

import json
import math
import os
import random
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypeVar, get_args

import httpx
from pydantic import BaseModel, ValidationError

from samajh.clients._runtime import (
    Attempt,
    Cache,
    Ledger,
    LedgerEntry,
    RetryPolicy,
    cache_key,
    check_api_key,
    load_defaults,
    load_env,
    send_with_retry,
    single_flight,
    state_dir,
)
from samajh.clients.errors import ApiError, BadResponse, CapExceeded, ClientError, ConfigError, InvalidRequest
from samajh.clients.gnani.tally import tally_for
from samajh.clients.gnani.types import (
    AudioFormat,
    BatchOptions,
    BatchTranscript,
    CallInfo,
    PrismaV25,
    PrismaV30,
    Segment,
    Speech,
    Timbre,
    Transcript,
)
from samajh.clients.gnani.wav import fix_wav_header, wav_sample_rate, wav_seconds

STT_PATH = "/stt/v3"
TTS_PATH = "/api/v1/tts/inference"
BATCH_PATH = "/stt/v3/batch/jobs"
MAX_STT_SECONDS = 30.0
BATCH_MIN_GAP = 1.5  # batch routes answer 429 "Rate limit exceeded" to calls under about 1 s apart
BATCH_FIRST_POLL = 2.0  # a 13 s clip completed 1.2 s after start
BATCH_FAILED = frozenset({"PARTIAL_FAILURE", "FAILED", "START_FAILED", "CANCELLED"})
FILE_FAILED = frozenset({"FAILED", "SKIPPED", "CANCELLED"})
# All six seen live on 2026-11-10 (timbre-v3.0, 8000 Hz), one call each.
CONTENT_TYPES = {
    "wav": "audio/wav",
    "raw": "application/octet-stream",
    "mp3": "audio/mpeg",
    "ogg": "audio/ogg",
    "mulaw": "audio/basic",
    "alaw": "audio/alaw",
}

T = TypeVar("T")


class BatchTimeout(ClientError):
    """The batch job was not finished within `timeout`. The resume file is kept: call again to go on."""

    def __init__(self, *, job_id: str, status: str, timeout: float) -> None:
        self.job_id, self.status, self.timeout = job_id, status, timeout
        super().__init__(f"batch job {job_id} still {status} after {timeout:g}s; call again to resume")


# ---------------------------------------------------------------- wire models (extra fields ignored)


class _SttOutput(BaseModel):
    literal: str | None = None


class _SttWire(BaseModel):
    success: Literal[True]
    transcript: str
    model: str | None = None
    request_id: str | None = None
    detected_language_code: str | None = None
    truncated: bool = False
    output: _SttOutput | None = None


class _JobWire(BaseModel):
    job_id: str
    status: str


class _FileWire(BaseModel):
    file_id: str
    status: str
    transcript_url: str | None = None
    error_message: str | None = None


class _FilesWire(BaseModel):
    data: list[_FileWire]


class _SegmentWire(BaseModel):
    segment_id: int
    start_time: float
    end_time: float
    text: str
    speaker_id: int | None = None
    language_detected: str | None = None


class _BatchWire(BaseModel):
    file_id: str
    job_id: str
    model: str
    duration_seconds: float
    language_code: str | None = None
    segments: list[_SegmentWire]
    full_transcript: str


W = TypeVar("W", bound=BaseModel)


def _parse(model: type[W], body: bytes) -> W:
    try:
        return model.model_validate_json(body)
    except ValidationError as exc:
        fields = ", ".join(".".join(map(str, e["loc"])) or "<body>" for e in exc.errors()[:5])
        # Field names only: the body may be large, and nothing from the wire belongs in a message.
        raise BadResponse(f"{model.__name__.strip('_')}: body does not parse (at: {fields})") from None


def parse_error(response: httpx.Response) -> tuple[str | None, str]:
    """(code, message) from any of Gnani's five error body shapes or a non-JSON body. Never raises."""
    code, message = _error_parts(response)
    return code, message[:300]


def _error_parts(response: httpx.Response) -> tuple[str | None, str]:
    """`parse_error` before the message is cut, so a caller can redact first."""
    try:
        body = response.json()
    except Exception:  # noqa: BLE001 - must not raise whatever the proxy sent
        return None, response.text
    if not isinstance(body, dict):
        return None, str(body)
    detail, error = body.get("detail"), body.get("error")
    code: Any = None
    message: Any = body.get("message")
    if isinstance(detail, dict):  # gateway
        code, message = detail.get("error_code"), detail.get("message")
    elif isinstance(detail, list) and detail and isinstance(detail[0], dict):  # FastAPI validation
        first = detail[0]
        loc = first.get("loc")
        where = ".".join(map(str, loc)) if isinstance(loc, list) else ""
        code, message = first.get("type"), f"{where}: {first.get('msg')}"
    elif isinstance(detail, str):
        message = detail
    elif isinstance(error, dict):  # STT
        code, message = error.get("type"), error.get("message")
    elif isinstance(error, str):  # batch, 504
        code = body.get("code") or error
    return (str(code) if code else None), str(message if message is not None else body)


def credit_cap_from_env() -> float:
    """`GNANI_CREDIT_CAP` if set, else `[gnani].credit_cap` in defaults.toml."""
    raw = os.environ.get("GNANI_CREDIT_CAP")
    try:
        return float(raw) if raw else float(load_defaults()["gnani"]["credit_cap"])
    except (KeyError, ValueError):
        raise ConfigError("credit cap missing or not a number (GNANI_CREDIT_CAP / defaults.toml)") from None


def _language_code(language: str | tuple[str, ...]) -> str:
    return language if isinstance(language, str) else ",".join(language)


def _stt_fields(options: PrismaV30 | PrismaV25) -> dict[str, str]:
    fields = {
        "model": options.model,
        "language_code": _language_code(options.language),
        "format": options.format,
    }
    if isinstance(options, PrismaV30):
        if options.keyterms:
            fields["keyterms"] = json.dumps(options.keyterms, ensure_ascii=False)
        if options.topic is not None:
            fields["topic"] = options.topic
    elif options.bias_list:
        fields["bias_list"] = json.dumps(options.bias_list, ensure_ascii=False)
        fields["bias_score"] = str(options.bias_score)
    return fields


def _batch_config(options: BatchOptions) -> dict[str, Any]:
    config: dict[str, Any] = {
        "model": options.model,
        "language_code": _language_code(options.language),
        "with_diarization": options.diarize,
        "with_denoise": options.denoise,
    }
    if options.format is not None:
        config["format"] = options.format
    if options.num_speakers is not None:
        config["num_speakers"] = options.num_speakers
    if options.keyterms:
        config["keyterms"] = list(options.keyterms)
    return config


def _check_audio_format(audio_format: str) -> None:
    # The value becomes a file-name extension, which is how the server picks its decoder.
    if audio_format not in get_args(AudioFormat):
        allowed = ", ".join(get_args(AudioFormat))
        raise InvalidRequest(f"audio_format {audio_format!r} is not one of {allowed}")


def _file_part(audio: bytes, audio_format: AudioFormat) -> tuple[str, bytes, str]:
    # The server picks the decoder from the file-name extension, not from the content type.
    return (
        f"audio.{audio_format}",
        audio,
        "audio/wav" if audio_format == "wav" else "application/octet-stream",
    )


_TtsDecode = Callable[[Mapping[str, Any], bytes], tuple[Mapping[str, Any], bytes, float | None]]


class GnaniClient:
    def __init__(
        self,
        *,
        api_key: str,
        credit_cap: float,
        state: Path | None = None,
        base_url: str = "https://api.vachana.ai",
        http: httpx.Client | None = None,
        retry: RetryPolicy = RetryPolicy(),  # noqa: B008 - frozen dataclass
        timeout: float = 30.0,
        lock_timeout: float = 600.0,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
        stt_credits_per_second: float | None = None,
        tts_credits_per_char: float | None = None,
    ) -> None:
        check_api_key(api_key, "Gnani")
        if not (math.isfinite(credit_cap) and credit_cap >= 0):
            raise ConfigError(f"credit_cap must be a finite number >= 0, got {credit_cap!r}")
        rates = load_defaults()["gnani"] if None in (stt_credits_per_second, tts_credits_per_char) else {}
        self._api_key = api_key
        self._credit_cap = credit_cap
        self._state = state or state_dir()
        self._base_url = base_url.rstrip("/")
        # No default headers: the key is added per request in `_api`, so it cannot reach another host.
        self._http = http or httpx.Client()
        self._retry, self._timeout, self._lock_timeout = retry, timeout, lock_timeout
        self._sleep, self._rng = sleep, rng or random.Random()
        self._stt_rate = (
            rates["stt_credits_per_second"] if stt_credits_per_second is None else stt_credits_per_second
        )
        self._tts_rate = (
            rates["tts_credits_per_char"] if tts_credits_per_char is None else tts_credits_per_char
        )
        self._cache = Cache(self._state / "cache" / "gnani")
        self._ledger = Ledger(self._state / "ledger.jsonl")
        self._tally = tally_for(self._ledger.path)
        self._lock = self._state / "gnani.lock"
        self._last_batch = float("-inf")

    @classmethod
    def from_env(cls, **overrides: Any) -> GnaniClient:
        load_env()
        if "api_key" not in overrides:
            key = os.environ.get("GNANI_API_KEY", "").strip()
            if not key:
                raise ConfigError("GNANI_API_KEY is not set (put it in .env)")
            overrides["api_key"] = key
        if "credit_cap" not in overrides:
            overrides["credit_cap"] = credit_cap_from_env()
        return cls(**overrides)

    def credits_spent(self) -> float:
        return self._tally.gnani_credits()

    def warm_ledger(self) -> None:
        """Read the whole ledger once now, so the first capped request pays only for new rows."""
        self._tally.totals()

    # ------------------------------------------------------------ public calls

    def stt(
        self, audio: bytes, options: PrismaV30 | PrismaV25, *, audio_format: AudioFormat = "wav"
    ) -> Transcript:
        _check_audio_format(audio_format)
        if not audio:
            raise InvalidRequest("audio is empty")
        seconds = wav_seconds(audio) if audio_format == "wav" else None
        if seconds is not None and seconds > MAX_STT_SECONDS:
            raise InvalidRequest(f"clip is {seconds:.2f}s; Prisma REST takes at most {MAX_STT_SECONDS:g}s")
        fields = _stt_fields(options)
        key = cache_key(
            "gnani.stt.v1",
            {"base_url": self._base_url, "path": STT_PATH, "audio_format": audio_format, "fields": fields},
            audio,
        )

        def decode(meta: Mapping[str, Any], body: bytes) -> _SttWire:
            return _parse(_SttWire, body)

        wire, call = self._rest(
            kind="stt",
            model=options.model,
            key=key,
            # A clip of unknown length is charged at the longest the API accepts.
            estimate=(MAX_STT_SECONDS if seconds is None else seconds) * self._stt_rate,
            units={"audio_seconds": seconds},
            send=lambda: self._api(
                "POST", STT_PATH, data=fields, files={"audio_file": _file_part(audio, audio_format)}
            ),
            meta_of=lambda response: {},
            decode=decode,
        )
        return Transcript(
            text=wire.transcript,
            literal=wire.output.literal if wire.output else None,
            # [unverified] the docs say a clip under 0.1 s comes back without `model`.
            model=wire.model or options.model,
            detected_language=wire.detected_language_code,
            request_id=wire.request_id,
            truncated=wire.truncated,
            call=call,
        )

    def _tts_request(self, text: str, options: Timbre) -> tuple[dict[str, Any], str, _TtsDecode]:
        """The body, cache key and decoder of a Timbre request: shared by `tts` and `tts_cached`."""
        if not text.strip():
            raise InvalidRequest("text is empty")
        body = {
            "text": text,
            "voice": options.voice,
            "model": options.model,
            "language": options.language,
            "speed": options.speed,
            "audio_config": {"sample_rate": options.sample_rate, "container": options.container},
        }
        key = cache_key("gnani.tts.v1", {"base_url": self._base_url, "path": TTS_PATH, "body": body}, b"")

        def decode(meta: Mapping[str, Any], audio: bytes) -> tuple[Mapping[str, Any], bytes, float | None]:
            expected = CONTENT_TYPES[options.container]
            if not audio or not str(meta.get("content_type") or "").lower().startswith(expected):
                raise BadResponse(f"Timbre: body is not {expected}")
            if options.container == "wav":
                seconds = wav_seconds(audio)
                if not seconds or wav_sample_rate(audio) != options.sample_rate:
                    raise BadResponse(f"Timbre: body is not a non-empty {options.sample_rate} Hz PCM WAV")
                return meta, fix_wav_header(audio), seconds
            if options.container == "raw":
                # [unverified] raw is taken to be PCM s16le mono, like the WAV payload.
                return meta, audio, len(audio) / 2 / options.sample_rate
            if options.container in ("mulaw", "alaw"):
                return meta, audio, len(audio) / 8000  # one byte per sample at 8000 Hz
            return meta, audio, None

        return body, key, decode

    def tts_cached(self, text: str, options: Timbre) -> bool:
        """True if `tts(text, options)` would be answered from the cache. No request, no lock, no
        ledger row. An entry that no longer parses is a miss, as it is for `tts`."""
        _, key, decode = self._tts_request(text, options)
        entry = self._cache.get(key)
        if entry is None:
            return False
        try:
            decode(entry.meta, entry.body)
        except BadResponse:
            return False
        return True

    def tts(self, text: str, options: Timbre) -> Speech:
        body, key, decode = self._tts_request(text, options)
        (meta, audio, seconds), call = self._rest(
            kind="tts",
            model=options.model,
            key=key,
            estimate=len(text) * self._tts_rate,
            units={"chars": len(text)},
            send=lambda: self._api("POST", TTS_PATH, json=body),
            meta_of=lambda response: {
                "content_type": response.headers.get("content-type"),
                "request_id": response.headers.get("x-api-request-id"),
            },
            decode=decode,
        )
        return Speech(
            audio=audio,
            content_type=meta.get("content_type") or CONTENT_TYPES[options.container],
            container=options.container,
            sample_rate=options.sample_rate,
            audio_seconds=seconds,
            request_id=meta.get("request_id"),
            call=call,
        )

    def batch_transcribe(
        self,
        audio: bytes,
        options: BatchOptions,
        *,
        audio_format: AudioFormat = "wav",
        poll_interval: float = 10.0,
        timeout: float = 900.0,
    ) -> BatchTranscript:
        _check_audio_format(audio_format)
        seconds = wav_seconds(audio) if audio_format == "wav" else None
        if seconds is None:
            raise InvalidRequest("batch input must be a PCM WAV: its duration is needed for the credit guard")
        config = _batch_config(options)
        key = cache_key(
            "gnani.batch.v1",
            {"base_url": self._base_url, "config": config, "audio_format": audio_format},
            audio,
        )
        hit = self._cached(key, "batch.transcript", options.model, {"audio_seconds": seconds}, _batch_decode)
        if hit is not None:
            return _batch_result(*hit)
        batch_dir = self._state / "batch"
        # One job per input on this machine: a second process waits here, then finds the cache entry.
        # This is a different file from gnani.lock, which is only ever held for one request.
        with single_flight(batch_dir / f"{key}.lock", timeout=timeout + self._lock_timeout):
            hit = self._cached(
                key, "batch.transcript", options.model, {"audio_seconds": seconds}, _batch_decode
            )
            if hit is not None:
                return _batch_result(*hit)
            job = _BatchJob(self, key, options.model, seconds, batch_dir / f"{key}.json")
            return _batch_result(*job.run(audio, audio_format, config, poll_interval, timeout))

    # ------------------------------------------------------------ plumbing

    def _api(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return self._http.request(
            method,
            self._base_url + path,
            headers={"X-API-Key-ID": self._api_key},
            timeout=self._timeout,
            follow_redirects=False,
            **kwargs,
        )

    def _presigned_get(self, url: str) -> httpx.Response:
        """For pre-signed storage URLs: the signature is in the URL and the key must not be sent."""
        request = self._http.build_request("GET", url, timeout=self._timeout)
        # An injected client may carry the key in its default headers.
        request.headers.pop("X-API-Key-ID", None)
        return self._http.send(request, follow_redirects=False)

    def _parse_error(self, response: httpx.Response) -> tuple[str | None, str]:
        code, message = _error_parts(response)
        # Redact before the cut: a key that straddles it would otherwise survive in part.
        message = message.replace(self._api_key, "<key>")[:300]
        return (code.replace(self._api_key, "<key>") if code else None), message

    def _row(self, kind: str, model: str, key: str, units: Mapping[str, Any], **fields: Any) -> None:
        self._ledger.append(
            LedgerEntry(
                ts=datetime.now(UTC).isoformat(timespec="seconds"),
                provider="gnani",
                kind=kind,
                model=model,
                cache_key=key,
                **units,
                **fields,
            )
        )

    def _cached(
        self,
        key: str,
        kind: str,
        model: str,
        units: Mapping[str, Any],
        decode: Callable[[Mapping[str, Any], bytes], T],
    ) -> tuple[T, CallInfo] | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        try:
            value = decode(entry.meta, entry.body)
        except BadResponse:
            return None  # an entry that no longer parses is a miss
        self._row(kind, model, key, units, status="cache_hit", attempt=0, seconds=0.0, cache_hit=True)
        return value, CallInfo(cache_hit=True, cache_key=key, seconds=0.0, est_credits=0.0, attempts=0)

    def _check_cap(self, estimate: float) -> None:
        spent = self._tally.gnani_credits()
        if spent + estimate > self._credit_cap:
            raise CapExceeded(unit="credits", cap=self._credit_cap, spent=spent, estimate=estimate)

    def _send(
        self,
        send: Callable[[], httpx.Response],
        *,
        kind: str,
        model: str,
        key: str,
        units: Mapping[str, Any],
        estimate: float = 0.0,
    ) -> tuple[httpx.Response, CallInfo]:
        """`send_with_retry` with one ledger row per attempt. `estimate` lands on the 2xx row only."""
        attempts = 0

        def on_attempt(attempt: Attempt) -> None:
            nonlocal attempts
            attempts = attempt.number
            ok = isinstance(attempt.status, int) and 200 <= attempt.status < 300
            self._row(
                kind,
                model,
                key,
                units,
                status=attempt.status,
                attempt=attempt.number,
                seconds=round(attempt.seconds, 4),
                cache_hit=False,
                est_credits=estimate if ok else 0.0,
                error_code=attempt.error_code,
            )

        started = time.monotonic()
        response = send_with_retry(
            send,
            policy=self._retry,
            parse_error=self._parse_error,
            on_attempt=on_attempt,
            sleep=self._sleep,
            rng=self._rng,
        )
        seconds = round(time.monotonic() - started, 4)
        info = CallInfo(
            cache_hit=False, cache_key=key, seconds=seconds, est_credits=estimate, attempts=attempts
        )
        return response, info

    def _rest(
        self,
        *,
        kind: str,
        model: str,
        key: str,
        estimate: float,
        units: Mapping[str, Any],
        send: Callable[[], httpx.Response],
        meta_of: Callable[[httpx.Response], dict[str, Any]],
        decode: Callable[[Mapping[str, Any], bytes], T],
    ) -> tuple[T, CallInfo]:
        """The call sequence from the `_runtime` module docstring."""
        hit = self._cached(key, kind, model, units, decode)
        if hit is not None:
            return hit
        with single_flight(self._lock, timeout=self._lock_timeout):
            hit = self._cached(key, kind, model, units, decode)
            if hit is not None:
                return hit
            self._check_cap(estimate)
            response, info = self._send(send, kind=kind, model=model, key=key, units=units, estimate=estimate)
            meta = {"kind": kind, "model": model, **meta_of(response)}
            value = decode(meta, response.content)
            self._cache.put(key, meta, response.content)
        return value, info


def _batch_decode(meta: Mapping[str, Any], body: bytes) -> _BatchWire:
    return _parse(_BatchWire, body)


def _batch_result(wire: _BatchWire, call: CallInfo) -> BatchTranscript:
    return BatchTranscript(
        segments=tuple(
            Segment(
                index=s.segment_id,
                start=s.start_time,
                end=s.end_time,
                text=s.text,
                # [unverified] the docs say an empty segment carries speaker_id -1.
                speaker=None if s.speaker_id is None or s.speaker_id < 0 else s.speaker_id,
                language=s.language_detected,
            )
            for s in wire.segments
        ),
        text=wire.full_transcript,
        duration_seconds=wire.duration_seconds,
        language=wire.language_code,
        model=wire.model,
        job_id=wire.job_id,
        file_id=wire.file_id,
        call=call,
    )


class _BatchJob:
    """One run of create/resume -> start -> poll -> files -> transcript for one cache key."""

    def __init__(self, client: GnaniClient, key: str, model: str, seconds: float, resume: Path) -> None:
        self.c, self.key, self.model, self.resume = client, key, model, resume
        self.units = {"audio_seconds": seconds}
        self.estimate = seconds * client._stt_rate
        self.attempts = 0
        self.billed = False
        self.started = time.monotonic()

    def request(
        self, kind: str, method: str, path: str, *, guard: bool = False, **kwargs: Any
    ) -> httpx.Response:
        """One batch API request under the key lock. Waiting happens before the lock is taken."""
        c = self.c
        gap = BATCH_MIN_GAP - (time.monotonic() - c._last_batch)
        if gap > 0:
            c._sleep(gap)
        try:
            with single_flight(c._lock, timeout=c._lock_timeout):
                if guard:
                    c._check_cap(self.estimate)
                response, info = c._send(
                    lambda: c._api(method, path, **kwargs),
                    kind=kind,
                    model=self.model,
                    key=self.key,
                    units=self.units,
                )
        finally:
            c._last_batch = time.monotonic()
        self.attempts += info.attempts
        return response

    def bill_once(self, job_id: str) -> None:
        """Record the job's credits: one ledger row per job, however its start request went."""
        if self.billed:
            return
        self.c._row(
            "batch.billed",
            self.model,
            self.key,
            self.units,
            status=200,
            attempt=0,
            seconds=0.0,
            cache_hit=False,
            est_credits=self.estimate,
        )
        self.resume.write_text(json.dumps({"job_id": job_id, "billed": True}))
        self.billed = True

    def status(self, job_id: str) -> str:
        return _parse(_JobWire, self.request("batch.poll", "GET", f"{BATCH_PATH}/{job_id}").content).status

    def run(
        self,
        audio: bytes,
        audio_format: AudioFormat,
        config: dict[str, Any],
        poll_interval: float,
        timeout: float,
    ) -> tuple[_BatchWire, CallInfo]:
        job_id, status = self.resume_job()
        if job_id is None:
            created = self.request(
                "batch.create",
                "POST",
                BATCH_PATH,
                guard=True,
                files=[
                    ("config", (None, json.dumps(config, ensure_ascii=False), "application/json")),
                    ("files", _file_part(audio, audio_format)),
                ],
            )
            job_id, status = _parse(_JobWire, created.content).job_id, "CREATED"
            self.resume.write_text(json.dumps({"job_id": job_id}))
        if status == "CREATED":
            try:
                self.request("batch.start", "POST", f"{BATCH_PATH}/{job_id}/start", guard=True)
            except ApiError as exc:
                # 409 JOB_ALREADY_STARTED (seen live): the job was started by an earlier attempt
                # whose response was lost. Polling tells the truth either way.
                if exc.status != 409:
                    raise
            status = "STARTING"
        # Reached after a 2xx start, a 409 start, or a resumed job that is past CREATED.
        self.bill_once(job_id)
        wait, waited = min(BATCH_FIRST_POLL, poll_interval), 0.0
        while status != "COMPLETED" and status not in BATCH_FAILED:
            if max(waited, time.monotonic() - self.started) >= timeout:
                raise BatchTimeout(job_id=job_id, status=status, timeout=timeout)
            self.c._sleep(wait)
            waited, wait = waited + wait, poll_interval
            status = self.status(job_id)
        try:
            files = _parse(
                _FilesWire, self.request("batch.files", "GET", f"{BATCH_PATH}/{job_id}/files").content
            )
            file = files.data[0] if files.data else None
        except ClientError:
            if status == "COMPLETED":
                raise
            file = None  # the job failed anyway; its status is the better error
        if status != "COMPLETED" or file is None or file.status != "COMPLETED" or not file.transcript_url:
            # A COMPLETED job whose listing is not ready yet keeps its resume file: forgetting it
            # would make the next call create and pay for a second job.
            if status in BATCH_FAILED or (file is not None and file.status in FILE_FAILED):
                self.resume.unlink(missing_ok=True)
            raise ApiError(
                status=0,
                code=status if status != "COMPLETED" or file is None else file.status,
                message=(file.error_message if file else None)
                or f"batch job {job_id} produced no transcript",
                attempts=self.attempts,
            )
        url = file.transcript_url
        response, info = self.c._send(
            lambda: self.c._presigned_get(url),
            kind="batch.transcript",
            model=self.model,
            key=self.key,
            units=self.units,
        )
        wire = _parse(_BatchWire, response.content)
        self.c._cache.put(
            self.key, {"kind": "batch", "model": self.model, "job_id": job_id}, response.content
        )
        self.resume.unlink(missing_ok=True)
        return wire, CallInfo(
            cache_hit=False,
            cache_key=self.key,
            seconds=round(time.monotonic() - self.started, 4),
            est_credits=self.estimate,
            attempts=self.attempts + info.attempts,
        )

    def resume_job(self) -> tuple[str | None, str]:
        """(job id, status) of the job a crashed run left behind, or (None, "") to start fresh."""
        try:
            saved = json.loads(self.resume.read_bytes())
            job_id = saved["job_id"]
        except (OSError, ValueError, KeyError, TypeError):
            return None, ""
        if not isinstance(job_id, str):
            return None, ""
        try:
            status = self.status(job_id)
        except ApiError as exc:
            if exc.status != 404:
                raise
            self.resume.unlink(missing_ok=True)
            return None, ""
        self.billed = saved.get("billed") is True
        return job_id, status
