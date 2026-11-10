"""One whole stub call against the real Gnani API. Costs credits on a cold cache:
`uv run pytest tests/server/test_live.py -m live`."""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from samajh.clients.gnani import wav_sample_rate, wav_seconds
from samajh.server import create_app
from samajh.server.replay import replay_call, turn_files
from samajh.server.sessionlog import BotEvent, CustomerEvent, SessionStore

TURNS = Path(__file__).resolve().parents[1] / "fixtures" / "server" / "stub-call"


@pytest.mark.live
def test_a_full_stub_call_on_the_real_api(tmp_path: Path) -> None:
    files = turn_files(TURNS)  # three 8 kHz mono Hindi answers, in name order
    assert len(files) == 3
    # Sessions go to a temp directory; the Gnani client keeps its shared lock, cache and ledger.
    with TestClient(create_app(profile="patient", state=tmp_path, web_dir=None)) as phone:
        result = replay_call(phone, files, dialogue="stub", line_rate=8000)

    log = result.log
    customers = [e for e in log.events if isinstance(e, CustomerEvent)]
    bots = [e for e in log.events if isinstance(e, BotEvent)]
    assert not [e for e in log.events if e.type == "error"]
    assert len(customers) == 3 and all(e.transcript.strip() for e in customers)
    assert len(bots) == 4 and all(e.audio and e.audio_seconds and e.tts for e in bots)
    assert (log.status, log.ended_reason) == ("ended", "dialogue")

    for event in customers:
        assert event.stt is not None and event.latency is not None
        latency = event.latency.model_dump()
        assert set(latency) == {"normalise_ms", "stt_ms", "dialogue_ms", "server_ms", "eos_wait_ms"}
        assert all(latency[k] is not None for k in ("normalise_ms", "stt_ms", "dialogue_ms", "server_ms"))
        assert latency["eos_wait_ms"] is None  # file-driven turns have no end-of-speech wait
    assert [t.stt_ms for t in result.turns] == [e.latency.stt_ms for e in customers]

    call = SessionStore(tmp_path / "sessions").read_recording(log.session_id)
    assert call is not None and wav_sample_rate(call) == 8000
    total = log.events[-1].rec_end
    assert wav_seconds(call) == pytest.approx(total, abs=1e-3)
    assert log.recording is not None and log.recording.seconds == pytest.approx(total, abs=1e-3)
    assert result.recording_seconds == log.recording.seconds
