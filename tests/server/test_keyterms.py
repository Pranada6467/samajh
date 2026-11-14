"""The record's first name goes to Prisma v3.0 as the one keyterm on a reply to a right-party line,
and nowhere else. Fake clients only; no network."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from serverkit import FakeSpeech, make_wav

from samajh.clients.gnani import PrismaV30
from samajh.server.app import create_app
from samajh.server.records import default_book
from samajh.server.settings import load_settings


def test_a_reply_to_a_right_party_line_carries_only_the_first_name_as_keyterm(state: Path) -> None:
    fake = FakeSpeech()
    first = default_book().get("hero").record.borrower.name.split()[0]
    with TestClient(create_app(gnani=fake, state=state, settings=load_settings(), web_dir=None)) as phone:
        made = phone.post("/api/sessions", json={"params": {"record": "hero", "language": "hi"}}).json()
        assert any(line["key"].startswith("right_party.") for line in made["bot"]["lines"])
        sid = made["session_id"]
        turn = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to=0&part=1", content=make_wav(0.5))
        assert turn.status_code == 200, turn.text
        readings = phone.get(f"/api/sessions/{sid}").json()["events"][1]["readings"]

    primary = [options for _, options in fake.stt_calls if isinstance(options, PrismaV30)]
    assert primary and primary[0].keyterms == (first,)
    assert readings[0]["params"]["keyterms"] == "1"
    assert first not in str(readings[0]["params"])
