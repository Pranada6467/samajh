from __future__ import annotations

import io
import json
import wave
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from samajh.clients._runtime import Ledger, LedgerEntry, RetryPolicy
from samajh.clients.errors import (
    ApiError,
    AuthError,
    BadResponse,
    CapExceeded,
    ConfigError,
    InvalidRequest,
    RateLimited,
    ServerError,
    TransportError,
)
from samajh.clients.gnani import GnaniClient, PrismaV25, PrismaV30, Timbre, parse_error

KEY = "test-key-not-real"
BASE = "https://api.vachana.ai"
STT_URL = f"{BASE}/stt/v3"
TTS_URL = f"{BASE}/api/v1/tts/inference"

V30_BODY = {
    "success": True,
    "request_id": "req-1",
    "transcript": "मेरे लोन से 52,000 रुपये कटे।",
    "model": "prisma-v3.0",
    "processing_time": 0.12,
    "end_to_end_latency": 0.13,
    "detected_language_code": "hi-IN",
}
V25_BODY = {
    "success": True,
    "request_id": "req-2",
    "transcript": "मेरे लोन से 52,000 रुपये कटे।",
    "model": "prisma-v2.5",
    "processing_time": 0.12,
    "end_to_end_latency": 0.13,
    "output": {"literal": "मेरे लोन से बावन हज़ार रुपए कटे।"},
}
BUSY = {
    "detail": {
        "error_code": "RATE_LIMITED",
        "message": "Only 1 active request is allowed at a time. Wait for your current request to finish "
        "before sending another.",
        "status_code": 429,
    }
}
ERROR_SHAPES: list[tuple[Any, str | None, str]] = [
    (
        {"detail": {"error_code": "INVALID_API_KEY", "message": "Unauthorized", "status_code": 401}},
        "INVALID_API_KEY",
        "Unauthorized",
    ),
    (
        {
            "detail": [
                {"type": "missing", "loc": ["body", "language_code"], "msg": "Field required", "input": None}
            ]
        },
        "missing",
        "body.language_code: Field required",
    ),
    ({"detail": "Not Found"}, None, "Not Found"),
    (
        {"success": False, "error": {"type": "MAX_AUDIO_DURATION_EXCEEDED", "message": "too long"}},
        "MAX_AUDIO_DURATION_EXCEEDED",
        "too long",
    ),
    (
        {"success": False, "message": "Invalid request: text is empty", "status_code": 400},
        None,
        "Invalid request: text is empty",
    ),
    (
        {"error": "INVALID_CONFIG", "message": "format is not supported"},
        "INVALID_CONFIG",
        "format is not supported",
    ),
    (
        {"error": "Gateway Timeout", "code": "UPSTREAM_TIMEOUT", "message": "upstream timed out"},
        "UPSTREAM_TIMEOUT",
        "upstream timed out",
    ),
]

V30 = PrismaV30(language="hi-IN", format="transcribe", keyterms=("EMI",))
SHIVANI = Timbre(model="timbre-v3.0", voice="Shivani", language="hi-IN")


def pcm_wav(seconds: float, fill: bytes = b"\x01\x00", rate: int = 8000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(fill * round(seconds * rate))
    return buf.getvalue()


def timbre_wav(seconds: float = 2.4, rate: int = 8000) -> bytes:
    wav = pcm_wav(seconds, rate=rate)
    return wav[:4] + b"\xff" * 4 + wav[8:40] + b"\xff" * 4 + wav[44:]


WAV = pcm_wav(2.0)


class Sleeps(list[float]):
    def __call__(self, seconds: float) -> None:
        self.append(seconds)


@pytest.fixture
def sleeps() -> Sleeps:
    return Sleeps()


@pytest.fixture
def client(tmp_path: Path, sleeps: Sleeps) -> GnaniClient:
    return GnaniClient(api_key=KEY, credit_cap=10.0, state=tmp_path, sleep=sleeps)


def rows(state: Path) -> list[LedgerEntry]:
    return list(Ledger(state / "ledger.jsonl").entries())


# ---------------------------------------------------------------- happy paths


def test_stt_v30_request_and_result(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    route = respx_mock.post(STT_URL).respond(json=V30_BODY)
    t = client.stt(WAV, V30)
    assert (t.text, t.literal, t.detected_language) == ("मेरे लोन से 52,000 रुपये कटे।", None, "hi-IN")
    assert (t.model, t.request_id, t.truncated) == ("prisma-v3.0", "req-1", False)
    assert (t.call.cache_hit, t.call.attempts) == (False, 1)
    assert t.call.est_credits == pytest.approx(2.0 * 0.010)
    request = route.calls.last.request
    assert request.headers["x-api-key-id"] == KEY
    body = request.content
    for name, value in [
        ("model", "prisma-v3.0"),
        ("language_code", "hi-IN"),
        ("format", "transcribe"),
        ("keyterms", '["EMI"]'),
    ]:
        assert f'name="{name}"\r\n\r\n{value}\r\n'.encode() in body
    assert b'name="audio_file"; filename="audio.wav"' in body and WAV in body
    assert b"bias_list" not in body and b"topic" not in body
    (row,) = rows(tmp_path)
    assert (row.provider, row.kind, row.model, row.status, row.attempt) == (
        "gnani",
        "stt",
        "prisma-v3.0",
        200,
        1,
    )
    assert row.audio_seconds == pytest.approx(2.0) and row.est_credits == pytest.approx(0.02)
    assert client.credits_spent() == pytest.approx(0.02)


def test_stt_v25_gives_literal_and_sends_bias(client: GnaniClient, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(STT_URL).respond(json=V25_BODY)
    options = PrismaV25(language="hi-IN", format="transcribe", bias_list=("लोन",), bias_score=1.5)
    t = client.stt(WAV, options, audio_format="mp3")
    assert (t.literal, t.detected_language, t.model) == ("मेरे लोन से बावन हज़ार रुपए कटे।", None, "prisma-v2.5")
    body = route.calls.last.request.content
    assert 'name="bias_list"\r\n\r\n["लोन"]\r\n'.encode() in body
    assert b'name="bias_score"\r\n\r\n1.5\r\n' in body and b'filename="audio.mp3"' in body
    # Unknown duration: the guard assumes the 30 s maximum.
    assert t.call.est_credits == pytest.approx(0.30)


def test_stt_joins_languages_and_tolerates_a_minimal_body(
    client: GnaniClient, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.post(STT_URL).respond(json={"success": True, "request_id": "r", "transcript": ""})
    t = client.stt(WAV, PrismaV30(language=("hi-IN", "en-IN"), format="codemix", topic="loan"))
    assert (t.text, t.model, t.truncated) == ("", "prisma-v3.0", False)
    body = route.calls.last.request.content
    assert b'name="language_code"\r\n\r\nhi-IN,en-IN\r\n' in body and b'name="topic"\r\n\r\nloan\r\n' in body


def test_tts_request_and_result(client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path) -> None:
    raw = timbre_wav(2.4)
    route = respx_mock.post(TTS_URL).respond(
        content=raw, headers={"content-type": "audio/wav", "x-api-request-id": "tts-1"}
    )
    a = client.tts("नमस्ते", SHIVANI)
    assert json.loads(route.calls.last.request.content) == {
        "text": "नमस्ते",
        "voice": "Shivani",
        "model": "timbre-v3.0",
        "language": "hi-IN",
        "speed": 1.0,
        "audio_config": {"sample_rate": 8000, "container": "wav"},
    }
    assert route.calls.last.request.headers["x-api-key-id"] == KEY
    assert (a.content_type, a.container, a.sample_rate, a.request_id) == ("audio/wav", "wav", 8000, "tts-1")
    assert a.audio_seconds == pytest.approx(2.4)
    with wave.open(io.BytesIO(a.audio), "rb") as w:
        assert w.getnframes() == 19200
    assert a.call.est_credits == pytest.approx(len("नमस्ते") * 0.002)
    (row,) = rows(tmp_path)
    assert (row.kind, row.chars, row.status) == ("tts", len("नमस्ते"), 200)
    # The cache keeps what the server sent; the header fix is applied on the way out.
    assert any(p.read_bytes() == raw for p in (tmp_path / "cache" / "gnani").rglob("*.bin"))


@pytest.mark.parametrize(
    ("container", "payload", "seconds"),
    [("mulaw", b"\x7f" * 19200, 2.4), ("raw", b"\x00" * 32000, 2.0), ("mp3", b"ID3fake", None)],
)
def test_tts_other_containers(
    client: GnaniClient, respx_mock: respx.MockRouter, container: Any, payload: bytes, seconds: float | None
) -> None:
    content_type = {"mulaw": "audio/basic", "raw": "application/octet-stream", "mp3": "audio/mpeg"}[container]
    respx_mock.post(TTS_URL).respond(content=payload, headers={"content-type": content_type})
    a = client.tts("नमस्ते", SHIVANI.model_copy(update={"container": container}))
    assert a.audio == payload and a.audio_seconds == seconds


# ---------------------------------------------------------------- cache


def test_repeated_stt_is_a_cache_hit(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    route = respx_mock.post(STT_URL).respond(json=V30_BODY)
    first, second = client.stt(WAV, V30), client.stt(WAV, V30)
    assert route.call_count == 1
    assert second.call.cache_hit is True and (second.call.est_credits, second.call.attempts) == (0.0, 0)
    assert second.model_dump(exclude={"call"}) == first.model_dump(exclude={"call"})
    assert [(r.status, r.cache_hit, r.attempt, r.est_credits) for r in rows(tmp_path)] == [
        (200, False, 1, pytest.approx(0.02)),
        ("cache_hit", True, 0, 0.0),
    ]


def test_repeated_tts_is_a_cache_hit(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    route = respx_mock.post(TTS_URL).respond(
        content=timbre_wav(), headers={"content-type": "audio/wav", "x-api-request-id": "tts-1"}
    )
    first, second = client.tts("नमस्ते", SHIVANI), client.tts("नमस्ते", SHIVANI)
    assert route.call_count == 1
    assert second.call.cache_hit is True
    assert second.model_dump(exclude={"call"}) == first.model_dump(exclude={"call"})
    assert [r.status for r in rows(tmp_path)] == [200, "cache_hit"]


def test_a_cache_entry_that_no_longer_parses_is_a_miss(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    route = respx_mock.post(STT_URL).respond(json=V30_BODY)
    client.stt(WAV, V30)
    for body in (tmp_path / "cache" / "gnani").rglob("*.bin"):
        body.write_bytes(b'{"success": true}')
    assert client.stt(WAV, V30).call.cache_hit is False
    assert route.call_count == 2


@pytest.mark.parametrize(
    ("audio", "options", "audio_format"),
    [
        (WAV, PrismaV25(language="hi-IN", format="transcribe"), "wav"),
        (WAV, V30.model_copy(update={"language": "en-IN"}), "wav"),
        (WAV, V30.model_copy(update={"language": ("hi-IN", "en-IN")}), "wav"),
        (WAV, V30.model_copy(update={"format": "verbatim"}), "wav"),
        (WAV, V30.model_copy(update={"keyterms": ("EMI", "KFS")}), "wav"),
        (WAV, V30.model_copy(update={"keyterms": ()}), "wav"),
        (WAV, V30.model_copy(update={"topic": "loan"}), "wav"),
        (pcm_wav(2.0, fill=b"\x02\x00"), V30, "wav"),
        (WAV, V30, "mp3"),
    ],
)
def test_stt_cache_key_covers_every_input(
    client: GnaniClient, respx_mock: respx.MockRouter, audio: bytes, options: Any, audio_format: Any
) -> None:
    route = respx_mock.post(STT_URL).respond(json=V30_BODY)
    client.stt(WAV, V30)
    assert client.stt(audio, options, audio_format=audio_format).call.cache_hit is False
    assert route.call_count == 2


@pytest.mark.parametrize(
    ("text", "update"),
    [
        ("नमस्ते जी", {}),
        ("नमस्ते", {"voice": "Avinash"}),
        ("नमस्ते", {"model": "timbre-v2.5", "voice": "Nalini"}),
        ("नमस्ते", {"language": "hi-en"}),
        ("नमस्ते", {"sample_rate": 16000}),
        ("नमस्ते", {"container": "raw"}),
        ("नमस्ते", {"speed": 1.1}),
    ],
)
def test_tts_cache_key_covers_every_input(
    client: GnaniClient, respx_mock: respx.MockRouter, text: str, update: dict[str, Any]
) -> None:
    def speak(request: httpx.Request) -> httpx.Response:
        config = json.loads(request.content)["audio_config"]
        if config["container"] == "raw":
            return httpx.Response(200, content=b"\x00" * 320, headers={"content-type": "application/octet-stream"})
        return httpx.Response(
            200, content=timbre_wav(rate=config["sample_rate"]), headers={"content-type": "audio/wav"}
        )

    route = respx_mock.post(TTS_URL).mock(side_effect=speak)
    client.tts("नमस्ते", SHIVANI)
    assert client.tts(text, Timbre(**{**SHIVANI.model_dump(), **update})).call.cache_hit is False
    assert route.call_count == 2


# ---------------------------------------------------------------- retries and errors


def test_429_then_200(
    client: GnaniClient, respx_mock: respx.MockRouter, sleeps: Sleeps, tmp_path: Path
) -> None:
    route = respx_mock.post(STT_URL).mock(
        side_effect=[httpx.Response(429, json=BUSY), httpx.Response(200, json=V30_BODY)]
    )
    t = client.stt(WAV, V30)
    assert route.call_count == 2 and len(sleeps) == 1 and t.call.attempts == 2
    first, second = rows(tmp_path)
    assert (first.status, first.error_code, first.est_credits, first.attempt) == (429, "RATE_LIMITED", 0.0, 1)
    assert (second.status, second.error_code, second.attempt) == (200, None, 2)
    assert second.est_credits == pytest.approx(0.02)


def test_504_forever_is_server_error(tmp_path: Path, respx_mock: respx.MockRouter, sleeps: Sleeps) -> None:
    client = GnaniClient(
        api_key=KEY, credit_cap=10.0, state=tmp_path, sleep=sleeps, retry=RetryPolicy(max_attempts=3)
    )
    gateway = {"error": "Gateway Timeout", "code": "UPSTREAM_TIMEOUT", "message": "upstream timed out"}
    route = respx_mock.post(STT_URL).respond(504, json=gateway)
    with pytest.raises(ServerError) as err:
        client.stt(WAV, V30)
    assert (err.value.status, err.value.code, err.value.attempts) == (504, "UPSTREAM_TIMEOUT", 3)
    assert route.call_count == 3 and len(sleeps) == 2
    assert client.credits_spent() == 0.0


def test_429_forever_is_rate_limited(
    client: GnaniClient, respx_mock: respx.MockRouter, sleeps: Sleeps
) -> None:
    route = respx_mock.post(TTS_URL).respond(429, json=BUSY)
    with pytest.raises(RateLimited) as err:
        client.tts("नमस्ते", SHIVANI)
    assert err.value.code == "RATE_LIMITED"
    assert route.call_count == 5 and len(sleeps) == 4


def test_connect_timeout_forever_is_transport_error(
    client: GnaniClient, respx_mock: respx.MockRouter, sleeps: Sleeps, tmp_path: Path
) -> None:
    route = respx_mock.post(TTS_URL).mock(side_effect=httpx.ConnectTimeout("no route"))
    with pytest.raises(TransportError):
        client.tts("नमस्ते", SHIVANI)
    assert route.call_count == 5 and len(sleeps) == 4
    assert {(r.status, r.error_code) for r in rows(tmp_path)} == {("transport_error", "ConnectTimeout")}


@pytest.mark.parametrize(("body", "code", "message"), ERROR_SHAPES)
def test_400_is_api_error_with_the_code_from_the_body(
    client: GnaniClient,
    respx_mock: respx.MockRouter,
    sleeps: Sleeps,
    body: Any,
    code: str | None,
    message: str,
) -> None:
    route = respx_mock.post(STT_URL).respond(400, json=body)
    with pytest.raises(ApiError) as err:
        client.stt(WAV, V30)
    assert (err.value.status, err.value.code, err.value.message) == (400, code, message)
    assert route.call_count == 1 and sleeps == []


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(502, html="<html><body>Bad Gateway</body></html>"),
        httpx.Response(500, content=b"\xff\xfe\x00"),
        httpx.Response(400, json=[1, 2]),
        httpx.Response(400, json={"detail": []}),
        httpx.Response(400, json={"detail": [{"loc": "x"}], "error": {"type": 7}}),
        httpx.Response(400, json={"error": {"message": None}}),
        httpx.Response(400, content=b""),
    ],
)
def test_parse_error_never_raises(response: httpx.Response) -> None:
    code, message = parse_error(response)
    assert code is None or isinstance(code, str)
    assert isinstance(message, str)


@pytest.mark.parametrize("status", [401, 403])
def test_auth_error_after_one_request(
    client: GnaniClient, respx_mock: respx.MockRouter, sleeps: Sleeps, status: int
) -> None:
    route = respx_mock.post(STT_URL).respond(status, json=ERROR_SHAPES[0][0])
    with pytest.raises(AuthError) as err:
        client.stt(WAV, V30)
    assert err.value.code == "INVALID_API_KEY" and route.call_count == 1 and sleeps == []


@pytest.mark.parametrize(
    "body", [b"<html>ok</html>", b'{"success": true}', b'{"success": false, "transcript": "x"}', b"[]"]
)
def test_malformed_200_is_bad_response_and_not_cached(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path, body: bytes
) -> None:
    route = respx_mock.post(STT_URL).respond(content=body)
    for _ in range(2):
        with pytest.raises(BadResponse):
            client.stt(WAV, V30)
    assert route.call_count == 2
    assert not list((tmp_path / "cache").rglob("*.json"))


@pytest.mark.parametrize(("container", "body"), [("wav", b'{"success":false}'), ("mp3", b"")])
def test_tts_malformed_200_is_bad_response(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path, container: Any, body: bytes
) -> None:
    respx_mock.post(TTS_URL).respond(content=body, headers={"content-type": "application/json"})
    with pytest.raises(BadResponse):
        client.tts("नमस्ते", SHIVANI.model_copy(update={"container": container}))
    assert not list((tmp_path / "cache").rglob("*.json"))


def test_a_failed_call_is_never_cached(client: GnaniClient, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(STT_URL).mock(
        side_effect=[httpx.Response(400, json=ERROR_SHAPES[3][0]), httpx.Response(200, json=V30_BODY)]
    )
    with pytest.raises(ApiError):
        client.stt(WAV, V30)
    assert client.stt(WAV, V30).call.cache_hit is False
    assert route.call_count == 2


# ---------------------------------------------------------------- cap and refusals


def test_cap_refuses_before_the_network_but_cache_still_answers(
    tmp_path: Path, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.post(STT_URL).respond(json=V30_BODY)
    tts_route = respx_mock.post(TTS_URL).respond(content=timbre_wav())
    # 2 s at 0.010 = 0.02 credits: the first call fits under 0.03, a second would cross it.
    client = GnaniClient(api_key=KEY, credit_cap=0.03, state=tmp_path)
    client.stt(WAV, V30)
    with pytest.raises(CapExceeded) as err:
        client.stt(pcm_wav(2.0, fill=b"\x03\x00"), V30)
    assert (err.value.unit, err.value.cap) == ("credits", 0.03)
    assert err.value.spent == pytest.approx(0.02) and err.value.estimate == pytest.approx(0.02)
    with pytest.raises(CapExceeded):
        client.tts("नमस्ते जी, यह एक लंबा वाक्य है", SHIVANI)
    assert route.call_count == 1 and tts_route.call_count == 0
    assert client.stt(WAV, V30).call.cache_hit is True
    assert [r.status for r in rows(tmp_path)] == [200, "cache_hit"]


def test_cap_counts_spend_from_other_processes(tmp_path: Path, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(TTS_URL).respond(content=timbre_wav())
    Ledger(tmp_path / "ledger.jsonl").append(
        LedgerEntry(
            ts="2026-11-10T00:00:00+00:00",
            provider="gnani",
            kind="stt",
            model="prisma-v3.0",
            status=200,
            attempt=1,
            seconds=0.1,
            cache_hit=False,
            cache_key="k",
            est_credits=5.0,
        )
    )
    with pytest.raises(CapExceeded):
        GnaniClient(api_key=KEY, credit_cap=5.0, state=tmp_path).tts("नमस्ते", SHIVANI)
    assert route.call_count == 0


def test_invalid_requests_do_no_io(client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path) -> None:
    with pytest.raises(InvalidRequest):
        client.stt(pcm_wav(30.5), V30)
    with pytest.raises(InvalidRequest):
        client.stt(b"", V30)
    for text in ("", " \n\t"):
        with pytest.raises(InvalidRequest):
            client.tts(text, SHIVANI)
    assert not respx_mock.calls and not list(tmp_path.iterdir())


def test_exactly_30_seconds_is_sent(client: GnaniClient, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(STT_URL).respond(json=V30_BODY)
    assert client.stt(pcm_wav(30.0), V30).call.est_credits == pytest.approx(0.30)


# ---------------------------------------------------------------- config and secrets


def test_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("samajh.clients.gnani.client.load_env", lambda: None)
    monkeypatch.setenv("SAMAJH_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("GNANI_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        GnaniClient.from_env()
    monkeypatch.setenv("GNANI_API_KEY", KEY)
    monkeypatch.delenv("GNANI_CREDIT_CAP", raising=False)
    assert GnaniClient.from_env()._credit_cap == 1000.0
    monkeypatch.setenv("GNANI_CREDIT_CAP", "10")
    assert GnaniClient.from_env()._credit_cap == 10.0
    monkeypatch.setenv("GNANI_CREDIT_CAP", "lots")
    with pytest.raises(ConfigError):
        GnaniClient.from_env()


def test_the_key_is_in_no_file_and_no_error(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    echo = {"detail": {"error_code": "INVALID_API_KEY", "message": f"bad key {KEY}", "status_code": 401}}
    respx_mock.post(STT_URL).mock(
        side_effect=[
            httpx.Response(200, json=V30_BODY),
            httpx.Response(401, json=echo),
            httpx.Response(400, text=f"<html>{KEY}</html>"),
            httpx.Response(200, text=f"not json {KEY}"),
            httpx.ConnectError(f"cannot reach host with {KEY}"),
            httpx.Response(504, json={"error": "Gateway Timeout", "message": KEY}),
            httpx.Response(429, json=BUSY),
            httpx.Response(429, json=BUSY),
            httpx.Response(429, json=BUSY),
        ]
    )
    respx_mock.post(TTS_URL).respond(content=timbre_wav(), headers={"content-type": "audio/wav"})
    client.stt(WAV, V30)
    client.tts("नमस्ते", SHIVANI)
    errors: list[Exception] = []
    for i in range(4):
        with pytest.raises(Exception) as err:
            client.stt(pcm_wav(1.0, fill=bytes([i + 5, 0])), V30)
        errors.append(err.value)
    assert [type(e).__name__ for e in errors] == ["AuthError", "ApiError", "BadResponse", "RateLimited"]
    for error in errors:
        assert KEY not in str(error) and KEY not in repr(error)
    assert KEY not in repr(client) and KEY not in str(vars(client).keys())
    files = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert len(files) >= 4
    for path in files:
        assert KEY.encode() not in path.read_bytes(), path


# ---------------------------------------------------------------- review fixes


def slices(key: str, n: int = 12) -> list[str]:
    return [key[i : i + n] for i in range(len(key) - n + 1)]


@pytest.mark.parametrize(
    "body",
    [
        {"detail": {"error_code": f"BAD_{KEY}", "message": "Unauthorized", "status_code": 400}},
        {"success": False, "error": {"type": KEY, "message": "nope"}},
        {"error": KEY, "message": "nope"},
        # The key crosses the 300-character cut: 15 of its characters come before it.
        {"detail": {"error_code": "X", "message": "x" * 285 + KEY, "status_code": 400}},
        {"detail": "x" * 285 + KEY},
    ],
)
def test_key_in_the_error_code_or_across_the_cut_is_redacted(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path, body: Any
) -> None:
    respx_mock.post(STT_URL).respond(400, json=body)
    with pytest.raises(ApiError) as err:
        client.stt(WAV, V30)
    text = str(err.value) + repr(err.value) + str(err.value.code) + err.value.message
    assert not any(part in text for part in slices(KEY))
    assert len(err.value.message) <= 300
    for path in (p for p in tmp_path.rglob("*") if p.is_file()):
        assert not any(part.encode() in path.read_bytes() for part in slices(KEY)), path


def test_key_across_the_cut_of_a_non_json_body_is_redacted(
    client: GnaniClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.post(STT_URL).respond(400, text="x" * 285 + KEY)
    with pytest.raises(ApiError) as err:
        client.stt(WAV, V30)
    assert not any(part in str(err.value) for part in slices(KEY))


@pytest.mark.parametrize("bad", ["", " ", KEY + "\n", " " + KEY, "a key", "a\tkey", "key\x00x", "key-क"])
def test_malformed_key_is_refused_without_showing_it(tmp_path: Path, bad: str) -> None:
    with pytest.raises(ConfigError) as err:
        GnaniClient(api_key=bad, credit_cap=10.0, state=tmp_path)
    assert not bad.strip() or bad.strip() not in str(err.value)


@pytest.mark.parametrize("cap", [float("nan"), float("inf"), float("-inf"), -1.0])
def test_credit_cap_must_be_finite_and_not_negative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cap: float
) -> None:
    with pytest.raises(ConfigError):
        GnaniClient(api_key=KEY, credit_cap=cap, state=tmp_path)
    monkeypatch.setattr("samajh.clients.gnani.client.load_env", lambda: None)
    monkeypatch.setenv("SAMAJH_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("GNANI_API_KEY", KEY)
    monkeypatch.setenv("GNANI_CREDIT_CAP", str(cap))
    with pytest.raises(ConfigError):
        GnaniClient.from_env()


@pytest.mark.parametrize(
    ("container", "payload", "content_type"),
    [
        ("mp3", b"<html>Bad Gateway</html>", "text/html"),
        ("mp3", b'{"success": false}', None),
        ("raw", b'{"success": false}', None),
        ("wav", timbre_wav(1.0), "text/html"),
        ("wav", timbre_wav(0.0), "audio/wav"),
        ("wav", pcm_wav(0.0), "audio/wav"),
        ("wav", timbre_wav(1.0, rate=48000), "audio/wav"),
    ],
    ids=["mp3-html", "mp3-json-untyped", "raw-json-untyped", "wav-html-type", "wav-streaming-header-only",
         "wav-header-only", "wav-48k-for-8k"],
)
def test_tts_body_that_is_not_the_audio_asked_for_is_bad_response_and_not_cached(
    client: GnaniClient,
    respx_mock: respx.MockRouter,
    tmp_path: Path,
    container: Any,
    payload: bytes,
    content_type: str | None,
) -> None:
    headers = {"content-type": content_type} if content_type else {}
    route = respx_mock.post(TTS_URL).respond(content=payload, headers=headers)
    for _ in range(2):
        with pytest.raises(BadResponse):
            client.tts("नमस्ते", SHIVANI.model_copy(update={"container": container}))
    assert route.call_count == 2
    assert not list((tmp_path / "cache").rglob("*.json"))


def test_a_redirect_is_not_followed_even_by_an_injected_client(
    tmp_path: Path, respx_mock: respx.MockRouter
) -> None:
    client = GnaniClient(
        api_key=KEY, credit_cap=10.0, state=tmp_path, http=httpx.Client(follow_redirects=True)
    )
    respx_mock.post(STT_URL).respond(307, headers={"location": "https://elsewhere.example/stt"})
    respx_mock.post(TTS_URL).respond(307, headers={"location": "https://elsewhere.example/tts"})
    other = respx_mock.route(host="elsewhere.example").respond(json=V30_BODY)
    with pytest.raises(ApiError) as err:
        client.stt(WAV, V30)
    assert err.value.status == 307
    with pytest.raises(ApiError):
        client.tts("नमस्ते", SHIVANI)
    assert other.call_count == 0


def test_cache_key_covers_the_base_url(tmp_path: Path, respx_mock: respx.MockRouter) -> None:
    mock_base = "http://mock.invalid"
    routes = [
        respx_mock.post(f"{mock_base}/stt/v3").respond(json=V30_BODY),
        respx_mock.post(STT_URL).respond(json=V30_BODY),
        respx_mock.post(f"{mock_base}/api/v1/tts/inference").respond(
            content=timbre_wav(), headers={"content-type": "audio/wav"}
        ),
        respx_mock.post(TTS_URL).respond(content=timbre_wav(), headers={"content-type": "audio/wav"}),
    ]
    mock = GnaniClient(api_key=KEY, credit_cap=10.0, state=tmp_path, base_url=mock_base)
    real = GnaniClient(api_key=KEY, credit_cap=10.0, state=tmp_path)
    mock.stt(WAV, V30)
    assert real.stt(WAV, V30).call.cache_hit is False
    mock.tts("नमस्ते", SHIVANI)
    assert real.tts("नमस्ते", SHIVANI).call.cache_hit is False
    assert [r.call_count for r in routes] == [1, 1, 1, 1]


@pytest.mark.parametrize("audio_format", ["webm", "WAV", "", "wav/../x"])
def test_stt_refuses_an_unknown_audio_format(
    client: GnaniClient, respx_mock: respx.MockRouter, audio_format: Any
) -> None:
    with pytest.raises(InvalidRequest):
        client.stt(WAV, V30, audio_format=audio_format)
    assert not respx_mock.calls


def test_a_data_chunk_that_declares_zero_bytes_is_measured_by_its_real_length(
    client: GnaniClient, respx_mock: respx.MockRouter
) -> None:
    wav = pcm_wav(31.0)
    lying = wav[:40] + b"\x00" * 4 + wav[44:]
    with pytest.raises(InvalidRequest):
        client.stt(lying, V30)
    assert not respx_mock.calls
