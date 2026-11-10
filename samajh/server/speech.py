"""What the transport needs from the Gnani client, and the options it sends."""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Protocol, get_args

import httpx

from samajh.clients._runtime import RetryPolicy
from samajh.clients.gnani import (
    AudioFormat,
    GnaniClient,
    PrismaV25,
    PrismaV30,
    Speech,
    SttLanguage,
    Timbre,
    Transcript,
    TtsLanguage,
)
from samajh.server.sessionlog import LineRate, SttSettings, TtsSettings


class SpeechClient(Protocol):
    def stt(
        self, audio: bytes, options: PrismaV30 | PrismaV25, *, audio_format: AudioFormat = "wav"
    ) -> Transcript: ...

    def tts(self, text: str, options: Timbre) -> Speech: ...


@dataclass(frozen=True)
class ClientProfile:
    retry: RetryPolicy
    timeout: float  # httpx's per-operation timeout: connect, each write, each read
    lock_timeout: float
    deadline: float  # the whole response must have arrived this long after the request went out


# A live turn must not hold the shared key lock for minutes. Worst case for one live call with
# these numbers: two attempts, each at most connect (6 s) + first byte (6 s) + deadline (8 s).
LIVE = ClientProfile(
    RetryPolicy(max_attempts=2, base_delay=0.3, max_delay=1.0), timeout=6.0, lock_timeout=5.0, deadline=8.0
)
PATIENT = ClientProfile(
    RetryPolicy(max_attempts=4, base_delay=1.0, max_delay=8.0),
    timeout=20.0,
    lock_timeout=120.0,
    deadline=60.0,
)


class _DeadlineStream(httpx.SyncByteStream):
    def __init__(self, inner: httpx.SyncByteStream, deadline: float) -> None:
        self._inner, self._deadline = inner, deadline

    def __iter__(self) -> Iterator[bytes]:
        for chunk in self._inner:
            if time.monotonic() > self._deadline:
                raise httpx.ReadTimeout("the response passed its total deadline")
            yield chunk

    def close(self) -> None:
        self._inner.close()


class DeadlineTransport(httpx.BaseTransport):
    """Bounds the time to read a response body. httpx's own timeout restarts with every chunk, so
    a server that sends one byte every few seconds would hold the key lock for as long as it
    liked. The time to the response headers is bounded by the per-operation timeout alone."""

    def __init__(self, total: float, inner: httpx.BaseTransport | None = None) -> None:
        self._total, self._inner = total, inner or httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        deadline = time.monotonic() + self._total
        response = self._inner.handle_request(request)
        assert isinstance(response.stream, httpx.SyncByteStream)
        return httpx.Response(
            response.status_code,
            headers=response.headers,
            stream=_DeadlineStream(response.stream, deadline),
            extensions=response.extensions,
        )

    def close(self) -> None:
        self._inner.close()


def live_client(profile: ClientProfile, **overrides: Any) -> GnaniClient:
    """The real client for this server: the profile's retry, timeouts and total deadline."""
    settings: dict[str, Any] = {
        "retry": profile.retry,
        "timeout": profile.timeout,
        "lock_timeout": profile.lock_timeout,
        "http": httpx.Client(transport=DeadlineTransport(profile.deadline)),
    }
    return GnaniClient.from_env(**(settings | overrides))


def stt_options(settings: SttSettings, bot_language: TtsLanguage) -> PrismaV30 | PrismaV25:
    """The customer answers in the language the bot asked in. ValueError if the model cannot take it."""
    v30 = settings.model == "prisma-v3.0"
    language: str | tuple[str, ...]
    if bot_language == "hi-en":
        language = ("hi-IN", "en-IN") if v30 else "hi-IN"
    elif bot_language == "auto" and v30:
        language = "indic-auto"
    elif bot_language in get_args(SttLanguage):
        language = bot_language
    else:
        raise ValueError(f"{settings.model} cannot transcribe a reply to language {bot_language!r}")
    if v30:
        return PrismaV30(language=language, format=settings.format)
    return PrismaV25(language=language, format=settings.format)


def stt_params(options: PrismaV30 | PrismaV25) -> dict[str, str]:
    """The option set as it goes into `SttCall.params`."""
    language = options.language
    return {
        "language_code": language if isinstance(language, str) else ",".join(language),
        "format": options.format,
    }


def tts_options(settings: TtsSettings, language: TtsLanguage, line_rate: LineRate) -> Timbre:
    return Timbre(
        model=settings.model, voice=settings.voice, language=language, sample_rate=line_rate, container="wav"
    )
