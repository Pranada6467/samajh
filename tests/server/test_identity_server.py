"""The right-party setting on the server (P8 contract sections 4 and 7): `[identity]` in the settings, a
session request's `identity` (the demo picker), the routes, the case file, and the rule that the expected
answer never reaches the case file, a response or a reviewer-facing field. No network."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from serverkit import FakeSpeech, make_wav
from starlette.testclient import TestClient
from test_casefile import FailingLlm, wait_case
from test_samajh_dialogue import answer

from samajh.amounts import spoken_amount
from samajh.clients.gnani import Segment
from samajh.identity import IdentityPolicy, describe
from samajh.server import create_app
from samajh.server.dialogue import Heard
from samajh.server.records import PACKAGED_DIR, load_book
from samajh.server.samajh_dialogue import WITHHELD, samajh_factory
from samajh.server.sessionlog import SessionStore
from samajh.server.settings import load_settings, parse_settings
from samajh.types import Language

BOOK = load_book(PACKAGED_DIR)
SETTINGS = load_settings().model_copy(
    update={"fallback": load_settings().fallback.model_copy(update={"enabled": False})}
)
YEAR = {"second_check": "year_of_birth", "attempts": 1}


class Recorded(TestClient):
    """A TestClient that keeps every response body it got."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.bodies: list[tuple[str, bytes, str]] = []

    def request(self, method, url, *args, **kwargs):
        response = super().request(method, url, *args, **kwargs)
        self.bodies.append((f"{method} {url}", response.content, response.headers.get("content-type", "")))
        return response


def phone_for(fake: FakeSpeech, state: Path, settings=SETTINGS, llm=FailingLlm) -> Recorded:
    fake.transcripts.clear()
    app = create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, llm=llm,
                     dialogues={"samajh": samajh_factory(BOOK, settings)}, records=BOOK, settings=settings)  # fmt: skip
    return Recorded(app)


def play(phone: TestClient, fake: FakeSpeech, identity: dict | None, record: str = "hero", **instead: str):
    """A whole call as the informed customer, with a distinct clip per turn. Returns the session id
    and every reply the customer gave (what the fake STT heard)."""
    body: dict[str, Any] = {"params": {"record": record, "language": "hi"}}
    if identity is not None:
        body["identity"] = identity
    created = phone.post("/api/sessions", json=body)
    assert created.status_code == 201, created.text
    sid, bot = created.json()["session_id"], created.json()["bot"]
    stored = SessionStore(phone.app.state.sessions.store.root).load(sid).params
    twin = samajh_factory(BOOK, SETTINGS)(stored)
    step, replies = twin.start(), []
    while not bot["end_call"]:
        assert phone.get(bot["audio_url"]).status_code == 200
        reply = answer("hi", step.say, **instead)
        replies.append(reply)
        fake.transcripts.append(reply)
        clip = make_wav(0.5 + len(replies) / 100, tone=200 + len(replies))
        turn = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to={bot['seq']}", content=clip)
        assert turn.status_code == 200, turn.text
        step = twin.step(step.state, Heard(text=reply, second=reply if step.say.second_reading else None))
        bot = turn.json()["bot"]
    assert phone.get(bot["audio_url"]).status_code == 200
    return sid, replies


# --- the setting --------------------------------------------------------------------


def test_the_shipped_settings_have_no_second_check() -> None:
    assert load_settings().identity == IdentityPolicy()


def test_settings_read_the_identity_table_through_the_menu() -> None:
    text = Path(load_settings.__wrapped__.__globals__["DEFAULT_FILE"]).read_text(encoding="utf-8")
    year = text.replace('second_check = "none"', 'second_check = "year_of_birth"').replace(
        "attempts = 1", "attempts = 2"
    )
    assert parse_settings(year).identity.second_check.value == "year_of_birth"
    assert parse_settings(year).identity.attempts == 2
    for bad in ('second_check = "pin_code"', 'second_check = "ask their mother\'s name"'):
        with pytest.raises(ValueError):
            parse_settings(text.replace('second_check = "none"', bad))
    with pytest.raises(ValueError):
        parse_settings(text.replace("call_back_line = true", 'call_back_line = true\nquestion = "free text"'))
    with pytest.raises(ValueError):
        parse_settings(text.replace("attempts = 1", "attempts = 3"))


@pytest.mark.parametrize(
    "identity",
    [
        {"second_check": "pin_code"},
        {"second_check": "year_of_birth", "attempts": 3},
        {"second_check": "year_of_birth", "attempts": "2"},
        {"question": "what is your mother's name?"},
        {"prior_notice": "yes"},
    ],
)
def test_a_session_request_outside_the_menu_is_refused(fake: FakeSpeech, state: Path, identity: dict) -> None:
    phone = phone_for(fake, state)
    refused = phone.post(
        "/api/sessions", json={"params": {"record": "hero", "language": "hi"}, "identity": identity}
    )
    assert refused.status_code == 422 and refused.json()["error"]["code"] == "invalid_identity"
    assert not list((state / "sessions").glob("*/session.json")) if (state / "sessions").exists() else True


def test_the_identity_cannot_be_smuggled_in_the_params(fake: FakeSpeech, state: Path) -> None:
    phone = phone_for(fake, state)
    params = {"record": "hero", "language": "hi", "identity": json.dumps(YEAR)}
    refused = phone.post("/api/sessions", json={"params": params})
    assert refused.status_code == 422 and refused.json()["error"]["code"] == "invalid_params"


@pytest.mark.parametrize(("identity", "asked"), [(None, False), (YEAR, True)])
def test_the_session_runs_under_the_setting_it_was_given(
    fake: FakeSpeech, state: Path, identity: dict | None, asked: bool
) -> None:
    phone = phone_for(fake, state)
    sid, _ = play(phone, fake, identity)
    log = SessionStore(state / "sessions").load(sid)
    keys = [line.key for event in log.events if event.type == "bot" for line in event.lines]
    assert ("second_check.ask" in keys) is asked
    assert ("identity" in log.params) is (identity is not None)
    # The year question listens for a short answer; no second check never asks it.
    listens = [event.listen for event in log.events if event.type == "bot"]
    assert listens[:3] == (["yes_no", "yes_no", "short"] if asked else ["yes_no", "yes_no", "open"])


def test_a_server_whose_lender_set_the_year_asks_it_without_a_request_setting(
    fake: FakeSpeech, state: Path
) -> None:
    settings = SETTINGS.model_copy(update={"identity": IdentityPolicy.model_validate(YEAR)})
    phone = phone_for(fake, state, settings)
    created = phone.post("/api/sessions", json={"params": {"record": "hero", "language": "hi"}})
    assert created.status_code == 201
    sid = created.json()["session_id"]
    bot = created.json()["bot"]
    fake.transcripts.append("हाँ जी, बोल रहा हूँ")
    turn = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to={bot['seq']}", content=make_wav(0.5))
    assert turn.json()["bot"]["lines"][-1]["key"] == "disclosure.go_ahead"
    fake.transcripts.append("हाँ, ठीक है")
    turn = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to={turn.json()['bot']['seq']}",
                      content=make_wav(0.6, tone=300))  # fmt: skip
    assert turn.json()["bot"]["lines"][-1]["key"] == "second_check.ask"


# --- the routes --------------------------------------------------------------------


def test_the_menu_lists_each_option_with_its_honest_description(fake: FakeSpeech, state: Path) -> None:
    menu = phone_for(fake, state).get("/api/identity/menu").json()
    assert [o["id"] for o in menu["options"]] == ["none", "year_of_birth"]
    none, year = menu["options"]
    assert none["attempts"] == [1] and year["attempts"] == [1, 2]
    assert none["descriptions"]["1"] == describe(IdentityPolicy())
    assert year["descriptions"]["2"] == describe(IdentityPolicy.model_validate(YEAR | {"attempts": 2}))
    for text in [*none["descriptions"].values(), *year["descriptions"].values()]:
        assert "right-party check, not identity verification" in text
    assert menu["default"]["second_check"] == "none" and menu["default"]["description"] == describe(
        IdentityPolicy()
    )


@pytest.mark.parametrize("lang", ["hi", "hi-en", "ta", "kn"])
def test_the_notice_route_renders_the_record_lenders_notice(fake: FakeSpeech, state: Path, lang: str) -> None:
    got = phone_for(fake, state).get(f"/api/identity/notice?record=hero&lang={lang}")
    assert got.status_code == 200
    body = got.json()
    hero = BOOK.get("hero")
    assert body["mocked"] is True and body["label"] == "SMS, mocked: not sent" and body["shown"] is True
    assert hero.lender_name in body["text"] and body["language"] == lang
    assert str(hero.record.borrower.dob.year) not in got.text and "Ramesh" not in got.text
    assert (body["review"] == "not human-reviewed") is (lang in ("ta", "kn"))


@pytest.mark.parametrize(
    ("query", "status"),
    [("record=nobody&lang=hi", 404), ("record=hero&lang=xx", 422), ("lang=hi", 422),
     ("record=hero&loan=SYN-PL-270104-0001&lang=hi", 422), ("record=hero&lang=hi&extra=1", 422),
     ("loan=SYN-PL-270104-0001&lang=hi", 409)],
)  # fmt: skip
def test_the_notice_route_refuses_bad_queries(fake: FakeSpeech, state: Path, query: str, status: int) -> None:
    got = phone_for(fake, state).get(f"/api/identity/notice?{query}")
    assert got.status_code == status, got.text
    assert "nobody" not in got.text and "extra" not in got.text


# --- the case file ------------------------------------------------------------------


@pytest.mark.parametrize(("identity", "check"), [(None, None), (YEAR, "year_of_birth")])
def test_the_case_file_carries_the_identity_record_and_description(
    fake: FakeSpeech, state: Path, identity: dict | None, check: str | None
) -> None:
    phone = phone_for(fake, state)
    sid, _ = play(phone, fake, identity)
    phone.post(f"/api/sessions/{sid}/case")
    case = wait_case(phone, sid)

    record = case["identity"]
    policy = IdentityPolicy() if identity is None else IdentityPolicy.model_validate(identity)
    assert record["check_used"] == check and record["passed"] is True
    assert record["attempts_allowed"] == (1 if check else 0) and record["attempts_used"] == (
        1 if check else 0
    )
    assert record["prior_notice_shown"] is True and record["prior_notice_mocked"] is True
    assert "right-party check, not identity verification" in record["sentence"]
    assert case["identity_description"] == describe(policy)
    assert case["speaker_confirmed"] is True and case["call_outcome"] == "completed"


def _year_forms(year: int) -> list[re.Pattern[str]]:
    """The birth year as digits and as the number words for it (Hindi and Hinglish, formal and as
    years are said: "उन्नीस सौ चौरासी", "nineteen eighty four")."""
    words = [spoken_amount(year, Language.hi), spoken_amount(year, Language.hi_en),
             "उन्नीस सौ चौरासी", "nineteen eighty four", "nineteen eighty-four"]  # fmt: skip
    return [
        re.compile(rf"(?<![0-9]){year}(?![0-9])"),
        *(re.compile(re.escape(w), re.IGNORECASE) for w in words),
    ]


def _hits(value: Any, forms: list[re.Pattern[str]], path: str = "") -> list[str]:
    """Every JSON path whose value holds the year (a hex digest is not a year)."""
    if isinstance(value, dict):
        return [hit for key, item in value.items() for hit in _hits(item, forms, f"{path}.{key}")]
    if isinstance(value, list):
        return [hit for i, item in enumerate(value) for hit in _hits(item, forms, f"{path}[{i}]")]
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, int):
        return [path] if forms[0].fullmatch(str(value)) else []
    if isinstance(value, str):
        if re.fullmatch(r"[0-9a-f]{16,}", value):
            return []
        return [path] if any(form.search(value) for form in forms) else []
    return []


class RecordingLlm(FailingLlm):
    """Keeps every message sent to the extraction model, then fails as a bad model output does."""

    def __init__(self) -> None:
        super().__init__()
        self.sent: list[str] = []

    def complete(self, schema, messages, **options):
        self.sent += [m.content for m in messages]
        return super().complete(schema, messages, **options)


@pytest.mark.parametrize("year_said", ["उन्नीस सौ चौरासी", "1984"], ids=["words", "digits"])
def test_the_expected_answer_appears_nowhere_it_was_not_already(
    fake: FakeSpeech, state: Path, year_said: str
) -> None:
    """A year-of-birth call to a ready case file, the customer saying the year in words or as
    digits. The record's birth year (digits and words) is searched for in every file the server
    wrote, every response body it sent and every message given to the extraction model. The
    customer's reply to the year question is withheld (`samajh_dialogue.WITHHELD`) in the turn
    response, the session log's events, `GET /api/sessions/{id}`, the case file (turn text,
    readings, the Batch segment over it, the transcript) and the extractor's input.

    Where the year may still be:
    * the session log's `dialogue_state` and `dialogue_undo` (`session.json` on disk): the dialogue's
      state keeps the expected answer (`CallState.plan`) and the customer's words (its turns) so a
      call resumes after a restart. No response serves them (`GET /api/sessions/{id}` leaves both
      out) and the case file never copies them. With no second check the plan keeps nothing of it.
    * the call's audio (`customer-NNN.wav`, `call.wav`): the reply is spoken there. Not searched.
    * the demo player's cheat sheet, kept on purpose: the packaged records' `description` ("Play
      Ramesh, born 1984") in `GET /api/records`, and `birth_year` in `GET /api/loans`, written for the
      person who plays the customer on the phone. Not reviewer-facing, not in any file the server writes.
    The record itself is not stored: the session log names the record by id only.
    """
    llm = RecordingLlm()
    phone = phone_for(fake, state, llm=lambda: llm)
    sid, said = play(phone, fake, YEAR, record="hero", second_check=year_said)
    assert year_said in said  # the customer did give the year
    # Batch hears the reply in the segment over its turn, as the real one would.
    log = SessionStore(state / "sessions").load(sid)
    asked = {e.seq: e for e in log.events if e.type == "bot"}
    (year_turn,) = [
        e
        for e in log.events
        if e.type == "customer" and asked[e.reply_to].lines[-1].key == "second_check.ask"
    ]
    assert year_turn.transcript == WITHHELD and year_turn.audio  # withheld on disk; the audio stays
    fake.batch_segments = lambda seconds: [
        Segment(index=0, start=0.0, end=year_turn.rec_start, text="…", speaker=0, language="hi"),
        Segment(
            index=1,
            start=year_turn.rec_start,
            end=year_turn.rec_end,
            text=year_said,
            speaker=1,
            language="hi",
        ),
        Segment(index=2, start=year_turn.rec_end, end=seconds, text="…", speaker=0, language="hi"),
    ]
    phone.post(f"/api/sessions/{sid}/case")
    case = wait_case(phone, sid)
    assert case["status"] == "ready" and case["identity"]["passed"] is True
    (kept,) = [t for t in case["turns"] if t["withheld"]]
    assert kept["seq"] == year_turn.seq and kept["start_s"] is not None and kept["text"] == WITHHELD
    assert [s["text"] for s in kept["segments"]] == [WITHHELD] and kept["speaker"] == 1
    assert WITHHELD in [t["text"] for t in case["transcript"]["turns"]]
    assert llm.sent  # the extractor was asked about the other replies
    phone.get(f"/api/sessions/{sid}")
    phone.get("/api/identity/menu")
    phone.get("/api/identity/notice?record=hero&lang=hi")
    phone.get("/api/records")
    forms = _year_forms(BOOK.get("hero").record.borrower.dob.year)

    found: dict[str, list[str]] = {"extraction model input": _hits(llm.sent, forms)}
    for name, body, kind in phone.bodies:
        if "json" in kind:
            found[name] = _hits(json.loads(body), forms)
    written = [p for p in state.rglob("*") if p.is_file() and p.suffix in (".json", ".jsonl", ".txt", ".md")]
    assert any(p.name == "case.json" for p in written) and any(p.name == "session.json" for p in written)
    for path in written:
        data = json.loads(path.read_text(encoding="utf-8")) if path.suffix == ".json" else path.read_text()
        if path.name == "session.json":
            state_json = json.loads(data.pop("dialogue_state"))
            assert (
                state_json["plan"]["birth_year"] == BOOK.get("hero").record.borrower.dob.year
            )  # where it is
            data.pop("dialogue_undo", None)
        found[str(path.relative_to(state))] = _hits(data, forms)
    cheat_sheet = {f".records[{i}].description" for i in range(len(BOOK.ids()))}
    assert (
        set(found.pop("GET /api/records")) <= cheat_sheet
    )  # the demo player's instructions, kept on purpose
    assert {where: hits for where, hits in found.items() if hits} == {}


def test_with_no_second_check_the_call_keeps_nothing_of_the_birth_year(fake: FakeSpeech, state: Path) -> None:
    phone = phone_for(fake, state)
    sid, said = play(phone, fake, None)
    log = SessionStore(state / "sessions").load(sid)
    assert json.loads(log.dialogue_state)["plan"]["birth_year"] is None
    assert not any("चौरासी" in reply for reply in said)  # never asked, so never said
