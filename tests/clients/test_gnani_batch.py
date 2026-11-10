from __future__ import annotations

import io
import json
import wave
from pathlib import Path

import httpx
import pytest
import respx

from samajh.clients._runtime import Ledger
from samajh.clients.errors import ApiError, CapExceeded, InvalidRequest
from samajh.clients.gnani import BatchOptions, BatchTimeout, GnaniClient

KEY = "test-key-not-real"
JOBS = "https://api.vachana.ai/stt/v3/batch/jobs"
S3 = "https://gnaniasraudios.s3.amazonaws.com/synthetic/transcript.json?X-Amz-Signature=fake"
OPTIONS = BatchOptions(model="prisma-v3.0", language="hi-IN", format="transcribe", num_speakers=2)
TRANSCRIPT = {
    "file_id": "file-1",
    "job_id": "job-1",
    "original_path": "audio.wav",
    "language_code": "hi-IN",
    "duration_seconds": 13.12,
    "model": "prisma-v3.0",
    "mode": "transcribe",
    "segments": [
        {
            "segment_id": 0,
            "start_time": 0,
            "end_time": 6.1,
            "text": "नमस्ते।",
            "speaker_id": 1,
            "confidence": None,
            "language_detected": "hi-IN",
        },
        {
            "segment_id": 1,
            "start_time": 6.8,
            "end_time": 13.12,
            "text": "",
            "speaker_id": -1,
            "confidence": None,
            "language_detected": None,
        },
    ],
    "full_transcript": "नमस्ते।",
    "created_at": "2026-11-10T00:00:00Z",
    "engine": "go-batch-asr",
}


def pcm_wav(seconds: float) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x01\x00" * round(seconds * 8000))
    return buf.getvalue()


WAV = pcm_wav(13.0)


class Crash(Exception):
    """Stands in for the process dying mid-job."""


class Sleeps(list[float]):
    def __call__(self, seconds: float) -> None:
        self.append(seconds)


@pytest.fixture
def sleeps() -> Sleeps:
    return Sleeps()


@pytest.fixture
def client(tmp_path: Path, sleeps: Sleeps) -> GnaniClient:
    return GnaniClient(api_key=KEY, credit_cap=10.0, state=tmp_path, sleep=sleeps)


def job(status: str) -> dict[str, object]:
    return {"job_id": "job-1", "status": status, "progress": {"total_files": 1, "percent": 0}}


def file_row(status: str = "COMPLETED", error: str | None = None) -> dict[str, object]:
    return {
        "job_id": "job-1",
        "data": [
            {
                "file_id": "file-1",
                "original_path": "audio.wav",
                "status": status,
                "duration_seconds": "13.12",
                "transcript_url": S3 if status == "COMPLETED" else None,
                "error_message": error,
            }
        ],
        "pagination": {},
    }


def routes(router: respx.MockRouter, *polls: str) -> dict[str, respx.Route]:
    return {
        "create": router.post(JOBS).respond(201, json=job("CREATED")),
        "start": router.post(f"{JOBS}/job-1/start").respond(202, json=job("STARTING")),
        "poll": router.get(f"{JOBS}/job-1").mock(
            side_effect=[httpx.Response(200, json=job(s)) for s in polls]
        ),
        "files": router.get(f"{JOBS}/job-1/files").respond(json=file_row()),
        "transcript": router.get(S3).respond(json=TRANSCRIPT),
    }


def kinds(state: Path) -> list[tuple[str, object]]:
    return [(e.kind, e.status) for e in Ledger(state / "ledger.jsonl").entries()]


def test_full_job(client: GnaniClient, respx_mock: respx.MockRouter, sleeps: Sleeps, tmp_path: Path) -> None:
    r = routes(respx_mock, "IN_PROGRESS", "COMPLETED")
    b = client.batch_transcribe(WAV, OPTIONS)

    assert (b.text, b.duration_seconds, b.language, b.model) == ("नमस्ते।", 13.12, "hi-IN", "prisma-v3.0")
    assert (b.job_id, b.file_id) == ("job-1", "file-1")
    first, empty = b.segments
    assert (first.index, first.start, first.end, first.speaker, first.language) == (0, 0.0, 6.1, 1, "hi-IN")
    assert (empty.speaker, empty.language) == (None, None)
    assert b.call.cache_hit is False and b.call.est_credits == pytest.approx(0.13)

    create = r["create"].calls.last.request
    assert create.headers["x-api-key-id"] == KEY
    assert b'name="files"; filename="audio.wav"' in create.content and WAV in create.content
    head, _, rest = create.content.partition(b'name="config"\r\nContent-Type: application/json\r\n\r\n')
    assert head and json.loads(rest.split(b"\r\n", 1)[0]) == {
        "model": "prisma-v3.0",
        "language_code": "hi-IN",
        "format": "transcribe",
        "with_diarization": True,
        "with_denoise": False,
        "num_speakers": 2,
    }
    assert [c.request.headers.get("x-api-key-id") for c in respx_mock.calls] == [KEY] * 5 + [None]
    assert "x-api-key-id" not in r["transcript"].calls.last.request.headers

    assert kinds(tmp_path) == [
        ("batch.create", 201),
        ("batch.start", 202),
        ("batch.billed", 200),
        ("batch.poll", 200),
        ("batch.poll", 200),
        ("batch.files", 200),
        ("batch.transcript", 200),
    ]
    assert client.credits_spent() == pytest.approx(0.13)
    billed = [e.kind for e in Ledger(tmp_path / "ledger.jsonl").entries() if e.est_credits]
    assert billed == ["batch.billed"]
    # First poll about 2 s after start, later ones every 10 s; every request at least 1.5 s after the last.
    assert [s for s in sleeps if s in (2.0, 10.0)] == [2.0, 10.0]
    assert sum(1 for s in sleeps if 1.4 < s <= 1.5) >= 4
    assert not list((tmp_path / "batch").glob("*.json"))

    again = client.batch_transcribe(WAV, OPTIONS)
    assert len(respx_mock.calls) == 6
    assert again.call.cache_hit is True
    assert again.model_dump(exclude={"call"}) == b.model_dump(exclude={"call"})
    assert kinds(tmp_path)[-1] == ("batch.transcript", "cache_hit")
    for path in (p for p in tmp_path.rglob("*") if p.is_file()):
        assert KEY.encode() not in path.read_bytes()


def test_changed_options_or_audio_start_a_new_job(client: GnaniClient, respx_mock: respx.MockRouter) -> None:
    r = routes(respx_mock, *["COMPLETED"] * 3)
    client.batch_transcribe(WAV, OPTIONS)
    client.batch_transcribe(WAV, OPTIONS.model_copy(update={"diarize": False}))
    client.batch_transcribe(pcm_wav(12.0), OPTIONS)
    assert r["create"].call_count == 3


def test_crash_after_create_resumes_the_same_job(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    r = routes(respx_mock, "CREATED", "COMPLETED")
    r["start"].mock(side_effect=[Crash(), httpx.Response(202, json=job("STARTING"))])
    with pytest.raises(Crash):
        client.batch_transcribe(WAV, OPTIONS)
    (resume,) = (tmp_path / "batch").glob("*.json")
    assert json.loads(resume.read_text()) == {"job_id": "job-1"}

    b = GnaniClient(api_key=KEY, credit_cap=10.0, state=tmp_path, sleep=lambda s: None).batch_transcribe(
        WAV, OPTIONS
    )
    assert b.job_id == "job-1"
    assert (r["create"].call_count, r["start"].call_count) == (1, 2)
    assert not resume.exists()


def test_crash_while_running_resumes_by_polling(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    r = routes(respx_mock)
    r["poll"].mock(
        side_effect=[
            Crash(),
            httpx.Response(200, json=job("IN_PROGRESS")),
            httpx.Response(200, json=job("COMPLETED")),
        ]
    )
    with pytest.raises(Crash):
        client.batch_transcribe(WAV, OPTIONS)
    assert client.batch_transcribe(WAV, OPTIONS).job_id == "job-1"
    assert (r["create"].call_count, r["start"].call_count) == (1, 1)


def test_resume_of_a_vanished_job_starts_fresh(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    r = routes(respx_mock)
    r["poll"].mock(
        side_effect=[
            Crash(),
            httpx.Response(404, json={"detail": "Not Found"}),
            httpx.Response(200, json=job("COMPLETED")),
        ]
    )
    with pytest.raises(Crash):
        client.batch_transcribe(WAV, OPTIONS)
    client.batch_transcribe(WAV, OPTIONS)
    assert (r["create"].call_count, r["start"].call_count) == (2, 2)


def test_failed_job_raises_and_forgets_the_job(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    r = routes(respx_mock, "FAILED")
    r["files"].respond(json=file_row("FAILED", "could not decode audio"))
    with pytest.raises(ApiError) as err:
        client.batch_transcribe(WAV, OPTIONS)
    assert (err.value.status, err.value.code, err.value.message) == (0, "FAILED", "could not decode audio")
    assert r["transcript"].call_count == 0
    assert not list((tmp_path / "batch").glob("*.json")) and not list((tmp_path / "cache").rglob("*.json"))


def test_start_409_means_already_started(client: GnaniClient, respx_mock: respx.MockRouter) -> None:
    r = routes(respx_mock, "COMPLETED")
    r["start"].respond(409, json={"error": "INVALID_STATE", "message": "already started"})
    assert client.batch_transcribe(WAV, OPTIONS).text == "नमस्ते।"


def test_rate_limited_poll_is_retried(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    limited = {"detail": {"error_code": "RATE_LIMITED", "message": "Rate limit exceeded", "status_code": 429}}
    r = routes(respx_mock)
    r["poll"].mock(
        side_effect=[httpx.Response(429, json=limited), httpx.Response(200, json=job("COMPLETED"))]
    )
    assert client.batch_transcribe(WAV, OPTIONS).call.attempts == 6
    assert ("batch.poll", 429) in kinds(tmp_path)


def test_timeout_keeps_the_job_for_a_later_resume(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    r = routes(respx_mock, *["IN_PROGRESS"] * 3, "COMPLETED")
    with pytest.raises(BatchTimeout) as err:
        client.batch_transcribe(WAV, OPTIONS, timeout=20.0)
    assert (err.value.job_id, err.value.status) == ("job-1", "IN_PROGRESS")
    assert r["poll"].call_count == 3
    assert client.batch_transcribe(WAV, OPTIONS).job_id == "job-1"
    assert r["create"].call_count == 1


def test_cap_and_input_refusals(tmp_path: Path, respx_mock: respx.MockRouter) -> None:
    client = GnaniClient(api_key=KEY, credit_cap=0.1, state=tmp_path, sleep=lambda s: None)
    with pytest.raises(CapExceeded):
        client.batch_transcribe(WAV, OPTIONS)
    for audio, audio_format in ((b"", "wav"), (b"ID3fake", "mp3"), (b"not a wav", "wav")):
        with pytest.raises(InvalidRequest):
            client.batch_transcribe(audio, OPTIONS, audio_format=audio_format)  # type: ignore[arg-type]
    assert not respx_mock.calls


# ---------------------------------------------------------------- review fixes

ESTIMATE = 0.13  # 13 s at 0.010 credits per second
STARTED_ALREADY = {"error": "JOB_ALREADY_STARTED", "message": "Job cannot be restarted from state 'COMPLETED'"}
TIMED_OUT = {"error": "Gateway Timeout", "code": "UPSTREAM_TIMEOUT", "message": "upstream timed out"}


def spent(state: Path) -> float:
    return Ledger(state / "ledger.jsonl").total_credits()


def billed_rows(state: Path) -> list[tuple[str, object, int, float | None]]:
    rows = Ledger(state / "ledger.jsonl").entries()
    return [(e.kind, e.status, e.attempt, e.audio_seconds) for e in rows if e.est_credits]


@pytest.mark.parametrize(
    "start",
    [
        [httpx.Response(202, json=job("STARTING"))],
        [httpx.Response(409, json=STARTED_ALREADY)],
        [httpx.ReadTimeout("the start took effect but its answer was lost"), httpx.Response(409, json=STARTED_ALREADY)],
    ],
    ids=["202", "409", "timeout-then-409"],
)
def test_a_job_that_ran_is_billed_exactly_once(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path, start: list[object]
) -> None:
    r = routes(respx_mock, "COMPLETED")
    r["start"].mock(side_effect=start)
    b = client.batch_transcribe(WAV, OPTIONS)
    assert b.call.est_credits == pytest.approx(ESTIMATE)
    assert spent(tmp_path) == pytest.approx(ESTIMATE)
    assert billed_rows(tmp_path) == [("batch.billed", 200, 0, 13.0)]

    assert client.batch_transcribe(WAV, OPTIONS).call.cache_hit is True
    assert spent(tmp_path) == pytest.approx(ESTIMATE)
    assert r["create"].call_count == 1


def test_start_that_fails_on_every_attempt_is_billed_by_the_rerun_that_finds_it_running(
    tmp_path: Path, respx_mock: respx.MockRouter
) -> None:
    def fresh() -> GnaniClient:
        return GnaniClient(api_key=KEY, credit_cap=10.0, state=tmp_path, sleep=lambda s: None)

    r = routes(respx_mock, "IN_PROGRESS", "COMPLETED")
    r["start"].respond(504, json=TIMED_OUT)
    with pytest.raises(ApiError) as err:
        fresh().batch_transcribe(WAV, OPTIONS)
    assert err.value.status == 504 and spent(tmp_path) == 0.0

    assert fresh().batch_transcribe(WAV, OPTIONS).job_id == "job-1"
    assert (r["create"].call_count, r["start"].call_count) == (1, 5)
    assert spent(tmp_path) == pytest.approx(ESTIMATE)
    assert billed_rows(tmp_path) == [("batch.billed", 200, 0, 13.0)]


def test_a_job_interrupted_after_it_was_billed_is_not_billed_again(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    r = routes(respx_mock)
    r["poll"].mock(side_effect=[Crash(), Crash(), httpx.Response(200, json=job("COMPLETED"))])
    for _ in range(2):
        with pytest.raises(Crash):
            client.batch_transcribe(WAV, OPTIONS)
    (resume,) = (tmp_path / "batch").glob("*.json")
    assert json.loads(resume.read_text()) == {"job_id": "job-1", "billed": True}
    client.batch_transcribe(WAV, OPTIONS)
    assert spent(tmp_path) == pytest.approx(ESTIMATE)


def test_completed_job_without_a_transcript_url_is_kept_and_resumed(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    r = routes(respx_mock, "COMPLETED", "COMPLETED")
    no_url = file_row()
    no_url["data"][0]["transcript_url"] = None  # type: ignore[index]
    r["files"].mock(side_effect=[httpx.Response(200, json=no_url), httpx.Response(200, json=file_row())])
    with pytest.raises(ApiError):
        client.batch_transcribe(WAV, OPTIONS)
    assert len(list((tmp_path / "batch").glob("*.json"))) == 1

    assert client.batch_transcribe(WAV, OPTIONS).job_id == "job-1"
    assert (r["create"].call_count, r["start"].call_count) == (1, 1)
    assert spent(tmp_path) == pytest.approx(ESTIMATE)
    assert not list((tmp_path / "batch").glob("*.json"))


@pytest.mark.parametrize("file_status", ["FAILED", "SKIPPED", "CANCELLED"])
def test_completed_job_with_a_failed_file_forgets_the_job(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path, file_status: str
) -> None:
    r = routes(respx_mock, "COMPLETED")
    r["files"].respond(json=file_row(file_status, "could not decode audio"))
    with pytest.raises(ApiError) as err:
        client.batch_transcribe(WAV, OPTIONS)
    assert err.value.code == file_status
    assert not list((tmp_path / "batch").glob("*.json"))


def test_key_in_default_headers_of_an_injected_client_never_reaches_the_storage_host(
    tmp_path: Path, respx_mock: respx.MockRouter
) -> None:
    http = httpx.Client(headers={"X-API-Key-ID": KEY})
    client = GnaniClient(api_key=KEY, credit_cap=10.0, state=tmp_path, sleep=lambda s: None, http=http)
    r = routes(respx_mock, "COMPLETED")
    client.batch_transcribe(WAV, OPTIONS)
    assert "x-api-key-id" not in r["transcript"].calls.last.request.headers
    assert r["files"].calls.last.request.headers["x-api-key-id"] == KEY


def test_a_redirect_from_the_storage_host_is_not_followed(tmp_path: Path, respx_mock: respx.MockRouter) -> None:
    http = httpx.Client(follow_redirects=True)
    client = GnaniClient(api_key=KEY, credit_cap=10.0, state=tmp_path, sleep=lambda s: None, http=http)
    r = routes(respx_mock, "COMPLETED")
    r["transcript"].respond(307, headers={"location": "https://elsewhere.example/t.json"})
    other = respx_mock.route(host="elsewhere.example").respond(json=TRANSCRIPT)
    with pytest.raises(ApiError):
        client.batch_transcribe(WAV, OPTIONS)
    assert other.call_count == 0


def test_cache_key_covers_the_base_url(tmp_path: Path, respx_mock: respx.MockRouter) -> None:
    mock_base = "http://mock.invalid"
    mock_jobs = f"{mock_base}/stt/v3/batch/jobs"
    r = routes(respx_mock, "COMPLETED")
    create = respx_mock.post(mock_jobs).respond(201, json=job("CREATED"))
    respx_mock.post(f"{mock_jobs}/job-1/start").respond(202, json=job("STARTING"))
    respx_mock.get(f"{mock_jobs}/job-1").respond(json=job("COMPLETED"))
    respx_mock.get(f"{mock_jobs}/job-1/files").respond(json=file_row())
    for base_url in (mock_base, "https://api.vachana.ai"):
        client = GnaniClient(
            api_key=KEY, credit_cap=10.0, state=tmp_path, sleep=lambda s: None, base_url=base_url
        )
        assert client.batch_transcribe(WAV, OPTIONS).call.cache_hit is False
    assert (create.call_count, r["create"].call_count) == (1, 1)


@pytest.mark.parametrize("audio_format", ["webm", "WAV", ""])
def test_batch_refuses_an_unknown_audio_format(
    client: GnaniClient, respx_mock: respx.MockRouter, audio_format: str
) -> None:
    with pytest.raises(InvalidRequest, match="audio_format"):
        client.batch_transcribe(WAV, OPTIONS, audio_format=audio_format)  # type: ignore[arg-type]
    assert not respx_mock.calls


def at_the_cap(state: Path) -> None:
    from samajh.clients._runtime import LedgerEntry

    Ledger(state / "ledger.jsonl").append(
        LedgerEntry(
            ts="2026-11-10T00:00:00+00:00", provider="gnani", kind="stt", model="prisma-v3.0", status=200,
            attempt=1, seconds=0.1, cache_hit=False, cache_key="k", est_credits=10.0,
        )
    )


def test_ledger_at_the_cap_refuses_create_before_any_request(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    routes(respx_mock, "COMPLETED")
    at_the_cap(tmp_path)
    with pytest.raises(CapExceeded):
        client.batch_transcribe(WAV, OPTIONS)
    assert not respx_mock.calls


def test_ledger_at_the_cap_refuses_the_start_of_a_resumed_created_job(
    client: GnaniClient, respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    r = routes(respx_mock, "CREATED", "CREATED", "COMPLETED")
    r["start"].mock(side_effect=[Crash(), httpx.Response(202, json=job("STARTING"))])
    with pytest.raises(Crash):
        client.batch_transcribe(WAV, OPTIONS)
    at_the_cap(tmp_path)
    with pytest.raises(CapExceeded):
        client.batch_transcribe(WAV, OPTIONS)
    assert (r["create"].call_count, r["start"].call_count, r["poll"].call_count) == (1, 1, 1)
    assert len(list((tmp_path / "batch").glob("*.json"))) == 1
