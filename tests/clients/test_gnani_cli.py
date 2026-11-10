from __future__ import annotations

import io
import json
import wave
from pathlib import Path

import pytest
import respx

from samajh.clients._runtime import Ledger, LedgerEntry
from samajh.clients.gnani.__main__ import main

KEY = "test-key-not-real"


@pytest.fixture
def state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr("samajh.clients.gnani.client.load_env", lambda: None)
    monkeypatch.setenv("SAMAJH_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("GNANI_API_KEY", KEY)
    monkeypatch.setenv("GNANI_CREDIT_CAP", "10")
    return tmp_path / "state"


def pcm_wav(seconds: float) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x01\x00" * round(seconds * 8000))
    return buf.getvalue()


def test_voices(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["voices", "--model", "timbre-v3.0"]) == 0
    voices = json.loads(capsys.readouterr().out)
    assert len(voices) == 13
    assert {"name": "Shivani", "model": "timbre-v3.0", "gender": "F", "language": None} in voices
    assert main(["voices"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 86


def test_ledger_summary(state: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def row(**fields: object) -> LedgerEntry:
        base = {
            "ts": "2026-11-10T00:00:00+00:00",
            "provider": "gnani",
            "model": "m",
            "attempt": 1,
            "seconds": 0.1,
            "cache_hit": False,
            "cache_key": "k",
        }
        return LedgerEntry.model_validate({**base, **fields})

    ledger = Ledger(state / "ledger.jsonl")
    for entry in [
        row(kind="stt", status=429, audio_seconds=2.0, error_code="RATE_LIMITED"),
        row(kind="stt", status=200, audio_seconds=2.0, est_credits=0.02, attempt=2),
        row(kind="stt", status="cache_hit", audio_seconds=2.0, attempt=0, cache_hit=True),
        row(kind="tts", status=200, chars=40, est_credits=0.08),
        row(kind="batch.create", status=201, audio_seconds=13.0),
        row(kind="batch.start", status=409, audio_seconds=13.0, error_code="JOB_ALREADY_STARTED"),
        row(kind="batch.billed", status=200, audio_seconds=13.0, est_credits=0.13, attempt=0),
        row(kind="chat", provider="openrouter", status=200, usd=0.5),
    ]:
        ledger.append(entry)
    assert main(["ledger"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "rows": 7,
        "cache_hits": 1,
        "live_attempts": {
            "batch.billed 200": 1,
            "batch.create 201": 1,
            "batch.start 409": 1,
            "stt 200": 1,
            "stt 429": 1,
            "tts 200": 1,
        },
        "audio_seconds": 15.0,
        "chars": 40,
        "est_credits_spent": 0.23,
        "credit_cap": 10.0,
        "remaining": 9.77,
    }


def test_tts_then_stt(
    state: Path, tmp_path: Path, respx_mock: respx.MockRouter, capsys: pytest.CaptureFixture[str]
) -> None:
    respx_mock.post("https://api.vachana.ai/api/v1/tts/inference").respond(
        content=pcm_wav(1.0), headers={"content-type": "audio/wav"}
    )
    stt = respx_mock.post("https://api.vachana.ai/stt/v3").respond(
        json={
            "success": True,
            "transcript": "नमस्ते",
            "model": "prisma-v3.0",
            "detected_language_code": "hi-IN",
        }
    )
    out = tmp_path / "tmp" / "hello.wav"
    assert main(["tts", "नमस्ते", "--out", str(out)]) == 0
    spoken = json.loads(capsys.readouterr().out)
    assert spoken["audio_seconds"] == 1.0 and "audio" not in spoken and out.read_bytes() == pcm_wav(1.0)
    assert main(["stt", str(out), "--language", "hi-IN,en-IN", "--keyterm", "EMI", "--keyterm", "KFS"]) == 0
    heard = json.loads(capsys.readouterr().out)
    assert heard["text"] == "नमस्ते" and heard["call"]["cache_hit"] is False
    body = stt.calls.last.request.content
    assert b"hi-IN,en-IN" in body and b'["EMI", "KFS"]' in body


def test_errors_exit_1_with_one_line(
    state: Path, tmp_path: Path, respx_mock: respx.MockRouter, capsys: pytest.CaptureFixture[str]
) -> None:
    respx_mock.post("https://api.vachana.ai/api/v1/tts/inference").respond(
        401, json={"detail": {"error_code": "INVALID_API_KEY", "message": "Unauthorized", "status_code": 401}}
    )
    clip = tmp_path / "clip.wav"
    clip.write_bytes(pcm_wav(1.0))
    for argv in (
        ["tts", "नमस्ते", "--out", str(tmp_path / "x.wav")],
        ["tts", " ", "--out", str(tmp_path / "x.wav")],
        ["tts", "नमस्ते", "--out", str(tmp_path / "x.wav"), "--voice", "Nalini"],
        ["stt", str(clip), "--model", "prisma-v2.5", "--keyterm", "EMI"],
        ["stt", str(tmp_path / "missing.wav")],
    ):
        assert main(argv) == 1
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err.startswith("error: ") and captured.err.count("\n") == 1
        assert KEY not in captured.err
