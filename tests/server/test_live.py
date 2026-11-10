"""One short Samajh call against the real Gnani API and OpenRouter, to its case file. Costs credits
on a cold cache (about 0.2: one turn, the bot's lines, Batch on a 12 s recording):
`uv run pytest tests/server/test_live.py -m live`."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from samajh.clients.gnani import wav_sample_rate, wav_seconds
from samajh.server import create_app
from samajh.server.replay import load_script, replay_call
from samajh.server.sessionlog import BotEvent, CustomerEvent, SessionStore

CALL = Path(__file__).resolve().parents[1] / "fixtures" / "server" / "calls" / "third-party"


@pytest.mark.live
def test_a_short_samajh_call_on_the_real_api_reaches_a_case_file(tmp_path: Path) -> None:
    script = load_script(CALL)  # the borrower's husband answers and says so: one turn
    # Sessions go to a temp directory; the clients keep their shared lock, cache and ledger.
    with TestClient(create_app(profile="patient", state=tmp_path, web_dir=None)) as phone:
        result = replay_call(phone, script, case=True, case_timeout=600)

    log = result.log
    customers = [e for e in log.events if isinstance(e, CustomerEvent)]
    assert not [e for e in log.events if e.type == "error"]
    assert len(customers) == 1 and customers[0].readings[0].model == "prisma-v3.0"
    assert customers[0].transcript.strip() and customers[0].latency is not None
    assert all(e.audio for e in log.events if isinstance(e, BotEvent))
    assert (log.status, log.ended_reason, log.closed) == ("ended", "dialogue", True)

    call = SessionStore(tmp_path / "sessions").read_recording(log.session_id)
    assert call is not None and wav_sample_rate(call) == 8000
    assert wav_seconds(call) == pytest.approx(log.events[-1].rec_end, abs=1e-3)

    case = result.case
    assert case["status"] == "ready", case["steps"]
    assert case["recording"]["sha256"] == hashlib.sha256(call).hexdigest()
    assert case["call_outcome"] in ("wrong_party", "not_confirmed") and case["tier"] != "clear"
    assert case["batch_segments"] >= 2 and case["turns"][0]["segments"]
    # The lender is never named to the person who said he is not the borrower.
    assert "नमूना" not in " ".join(e.text for e in log.events if isinstance(e, BotEvent))
