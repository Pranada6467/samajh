"""A whole Samajh call through the HTTP API, then its case file. Fake Gnani, fake LLM, no network."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pytest
from serverkit import FakeSpeech, make_wav
from starlette.testclient import TestClient
from test_samajh_dialogue import answer, waits_for_a_figure

from samajh.clients.errors import BadResponse, ConfigError, ServerError
from samajh.server import create_app
from samajh.server.dialogue import Heard, Step, stub_factory
from samajh.server.records import PACKAGED_DIR, load_book
from samajh.server.samajh_dialogue import samajh_factory
from samajh.server.settings import load_settings

BOOK = load_book(PACKAGED_DIR)
SETTINGS = load_settings().model_copy(
    update={"fallback": load_settings().fallback.model_copy(update={"enabled": False})}
)


class FailingLlm:
    """Every extraction request fails as a bad model output does: the fields become unclear."""

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, schema, messages, **options):
        self.calls += 1
        raise BadResponse("the fake model answered nothing usable")


def phone_for(fake: FakeSpeech, state: Path, llm=None) -> TestClient:
    fake.transcripts.clear()  # each turn queues the reply it should be heard as
    return TestClient(
        create_app(
            gnani=fake,
            state=state,
            web_dir=None,
            clips_dir=None,
            dialogues={"samajh": samajh_factory(BOOK, SETTINGS)},
            records=BOOK,
            settings=SETTINGS,
            llm=llm or FailingLlm,
        )
    )


def run_call(
    phone: TestClient,
    fake: FakeSpeech,
    record: str = "hero",
    language: str = "hi",
    hang_up_after=None,
    asked: list[Step] | None = None,
    **instead: str,
):
    """Answer every prompt as the scripted informed customer does (`instead` as in `answer`), with
    a distinct clip per turn, until the bot ends the call. A text twin of the dialogue picks each
    reply; `asked` collects the twin's step for each prompt that was answered."""
    created = phone.post("/api/sessions", json={"params": {"record": record, "language": language}})
    assert created.status_code == 201, created.text
    sid, bot = created.json()["session_id"], created.json()["bot"]
    twin = samajh_factory(BOOK, SETTINGS)({"record": record, "language": language})
    step = twin.start()
    turns = 0
    while not bot["end_call"]:
        assert phone.get(bot["audio_url"]).status_code == 200
        if hang_up_after is not None and turns == hang_up_after:
            assert phone.post(f"/api/sessions/{sid}/end", json={}).status_code == 200
            return sid
        reply = answer(language, step.say, **instead)
        if asked is not None:
            asked.append(step)
        fake.transcripts.append(reply)
        clip = make_wav(0.5 + turns / 100, tone=200 + turns)
        turn = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to={bot['seq']}", content=clip)
        assert turn.status_code == 200, turn.text
        step = twin.step(step.state, Heard(text=reply, second=reply if step.say.second_reading else None))
        bot = turn.json()["bot"]
        turns += 1
    assert phone.get(bot["audio_url"]).status_code == 200
    return sid


def wait_case(phone: TestClient, sid: str, seconds: float = 20.0) -> dict:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        case = phone.get(f"/api/sessions/{sid}/case").json()
        if case["status"] != "running":
            return case
        time.sleep(0.05)
    raise AssertionError("the case job did not finish")


def test_a_whole_call_reaches_a_case_file_with_every_turn_placed(fake: FakeSpeech, state: Path) -> None:
    phone = phone_for(fake, state)
    asked: list[Step] = []
    sid = run_call(phone, fake, asked=asked)
    figure_prompts = [waits_for_a_figure(step) for step in asked]
    started = phone.post(f"/api/sessions/{sid}/case")
    assert started.status_code == 200 and started.json()["status"] == "running"

    case = wait_case(phone, sid)

    assert case["status"] == "ready", case["steps"]
    assert [s["name"] for s in case["steps"]] == [
        "transcript",
        "recording",
        "batch",
        "align",
        "extract",
        "summary",
    ]
    call_wav = (state / "sessions" / sid / "call.wav").read_bytes()
    assert case["recording"]["sha256"] == hashlib.sha256(call_wav).hexdigest()
    assert case["call_outcome"] == "completed" and case["record_id"] == "hero"
    # The fake model failed every request, so nothing the customer said could be decided; the
    # hero record's own missing consent makes it a referral whatever was said. Never clear.
    assert case["tier"] == case["summary"]["tier"] == "refer"
    assert case["models"]["stt_primary"] == {"model": "prisma-v3.0", "format": "transcribe"}
    assert case["models"]["batch"]["model"] == "prisma-v3.0" and case["models"]["batch"]["diarize"] is True
    turns = case["turns"]
    assert turns and all(t["start_s"] is not None and t["end_s"] > t["start_s"] for t in turns)
    assert all(t["segments"] and t["speaker"] in (0, 1) for t in turns)
    # The whole transcript is kept, bot turns included, so the call can enter the review batch.
    whole = case["transcript"]["turns"]
    assert {t["speaker"] for t in whole} == {"bot", "customer"}
    spoken = {t["id"]: (t["start_s"], t["end_s"]) for t in whole if t["speaker"] == "customer"}
    assert spoken == {t["turn_id"]: (t["start_s"], t["end_s"]) for t in turns}
    twice = [t for t in turns if len(t["readings"]) == 2]
    assert {r["model"] for t in twice for r in t["readings"]} == {"prisma-v3.0", "prisma-v2.5"}
    # Read twice: exactly the answers to prompts at which the dialogue waits for a figure.
    assert [len(t["readings"]) == 2 for t in turns] == figure_prompts
    # The premium answer holds a figure both readings agree on, and is read back; the yes at the
    # read-back and the informed customer's cover answer (no figure in it) hold none.
    assert [(t["readings_agreed"], t["followed_by"]) for t in twice] == [
        (True, "read_back"),
        (None, "other"),
        (None, "other"),
    ], [t["text"] for t in twice]
    assert all(t["readings_agreed"] is None for t in turns if len(t["readings"]) == 1)
    assert len(case["latency"]) == len(turns) and all(row["tts_ms"] is not None for row in case["latency"])
    quoted = [e for e in case["evidence"] if e["turn_id"] is not None]
    assert all(e["start_s"] is not None for e in quoted)
    assert len(fake.batch_calls) == 1 and fake.batch_calls[0][0] == call_wav


def test_starting_the_case_again_returns_it_and_runs_nothing_twice(fake: FakeSpeech, state: Path) -> None:
    llm = FailingLlm()
    phone = phone_for(fake, state, llm=lambda: llm)
    sid = run_call(phone, fake)
    phone.post(f"/api/sessions/{sid}/case")
    first = wait_case(phone, sid)
    calls = llm.calls

    again = phone.post(f"/api/sessions/{sid}/case").json()

    assert again == first and llm.calls == calls and len(fake.batch_calls) == 1


def test_the_case_closes_the_call_so_no_take_can_replace_a_turn(fake: FakeSpeech, state: Path) -> None:
    phone = phone_for(fake, state)
    sid = run_call(phone, fake)
    phone.post(f"/api/sessions/{sid}/case")
    wait_case(phone, sid)
    log = phone.get(f"/api/sessions/{sid}").json()
    last = [e for e in log["events"] if e["type"] == "customer"][-1]

    take = phone.post(
        f"/api/sessions/{sid}/turns?source=file&reply_to={last['reply_to']}&part=2", content=make_wav(1.5)
    )

    assert take.status_code == 409 and take.json()["error"]["code"] == "turn_out_of_order"
    assert log["closed"] is True


@pytest.mark.parametrize(
    ("break_it", "step"),
    [
        (
            lambda fake: setattr(
                fake, "batch_error", ServerError(status=500, code=None, message="Batch answered 500")
            ),
            "batch",
        ),
        (None, "extract"),
    ],
)
def test_a_failed_step_is_named_and_the_case_is_never_ready(
    fake: FakeSpeech, state: Path, break_it, step
) -> None:
    def no_key():
        raise ConfigError("OPENROUTER_API_KEY is not set")

    phone = phone_for(fake, state, llm=None if break_it else no_key)
    if break_it:
        break_it(fake)
    sid = run_call(phone, fake)
    phone.post(f"/api/sessions/{sid}/case")

    case = wait_case(phone, sid)

    assert case["status"] == "failed" and step in case["failed"]
    failed = next(s for s in case["steps"] if s["name"] == step)
    assert failed["ok"] is False and failed["error"]
    if step == "batch":
        assert "align" in case["failed"]  # never ran
    else:
        assert case["failed"] == ["extract", "summary"] and case["tier"] is None


def test_a_call_hung_up_early_still_gets_a_case_and_it_is_not_clear(fake: FakeSpeech, state: Path) -> None:
    phone = phone_for(fake, state)
    sid = run_call(phone, fake, hang_up_after=3)
    phone.post(f"/api/sessions/{sid}/case")

    case = wait_case(phone, sid)

    assert case["call_outcome"] == "in_progress" and case["ended_reason"] == "hangup"
    assert case["status"] == "ready" and case["tier"] != "clear"


def test_the_third_party_call_ends_early_and_its_case_is_not_clear(fake: FakeSpeech, state: Path) -> None:
    phone = phone_for(fake, state)
    created = phone.post("/api/sessions", json={"params": {"record": "third-party", "language": "hi"}}).json()
    sid, bot = created["session_id"], created["bot"]
    for reply in ["नहीं, मैं उनकी पत्नी बोल रही हूँ", "नहीं, मैं उनकी पत्नी हूँ, वो घर पर नहीं हैं"]:
        if bot["end_call"]:
            break
        phone.get(bot["audio_url"])
        fake.transcripts.append(reply)
        bot = phone.post(
            f"/api/sessions/{sid}/turns?source=file&reply_to={bot['seq']}",
            content=make_wav(0.6, tone=300 + len(reply)),
        ).json()["bot"]
    assert bot["end_call"]
    phone.get(bot["audio_url"])
    phone.post(f"/api/sessions/{sid}/case")

    case = wait_case(phone, sid)

    assert case["call_outcome"] in ("wrong_party", "not_confirmed") and case["tier"] != "clear"


def test_a_case_before_the_call_ends_or_for_the_stub_is_refused(fake: FakeSpeech, state: Path) -> None:
    phone = phone_for(fake, state)
    sid = phone.post("/api/sessions", json={"params": {"record": "hero", "language": "hi"}}).json()[
        "session_id"
    ]

    assert phone.post(f"/api/sessions/{sid}/case").json()["error"]["code"] == "session_active"
    assert phone.get(f"/api/sessions/{sid}/case").json()["error"]["code"] == "case_not_started"

    stub = TestClient(
        create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, dialogues={"stub": stub_factory})
    )
    other = stub.post("/api/sessions", json={"dialogue": "stub"}).json()["session_id"]
    stub.post(f"/api/sessions/{other}/end", json={})
    assert stub.post(f"/api/sessions/{other}/case").json()["error"]["code"] == "no_case_file"


def test_a_job_left_running_by_a_stopped_server_is_rerun_by_the_next_request(
    fake: FakeSpeech, state: Path
) -> None:
    phone = phone_for(fake, state)
    sid = run_call(phone, fake)
    phone.post(f"/api/sessions/{sid}/case")
    wait_case(phone, sid)
    path = state / "sessions" / sid / "case.json"
    path.write_text(path.read_text().replace('"status": "ready"', '"status": "running"', 1))

    restarted = phone_for(fake, state)  # a new server run: no job thread for this call

    assert wait_case(restarted, sid)["status"] == "ready"
    assert len(fake.batch_calls) == 2  # the fake has no cache; the real client would answer from it


def test_customer_audio_counts_the_take_that_replaced_another_and_not_the_one_replaced(
    fake: FakeSpeech, state: Path
) -> None:
    """A take sent from the file picker, replaced by a longer take from the microphone: the case
    counts the microphone take only (the verifier's surviving mutant e)."""
    phone = phone_for(fake, state)
    created = phone.post("/api/sessions", json={"params": {"record": "hero", "language": "hi"}}).json()
    sid, bot = created["session_id"], created["bot"]
    twin = samajh_factory(BOOK, SETTINGS)({"record": "hero", "language": "hi"})
    step, turns = twin.start(), 0
    while not bot["end_call"]:
        phone.get(bot["audio_url"])
        reply = answer("hi", step.say)
        if turns == 0:  # the first answer: a short file take, then the whole answer from the mic
            fake.transcripts += ["हाँ", reply]
            first = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to={bot['seq']}&part=1",
                               content=make_wav(0.3, tone=150))  # fmt: skip
            assert first.status_code == 200, first.text
            turn = phone.post(f"/api/sessions/{sid}/turns?source=mic&reply_to={bot['seq']}&part=2",
                              content=make_wav(0.9, tone=160))  # fmt: skip
        else:
            fake.transcripts.append(reply)
            turn = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to={bot['seq']}",
                              content=make_wav(0.5 + turns / 100, tone=200 + turns))  # fmt: skip
        assert turn.status_code == 200, turn.text
        step = twin.step(step.state, Heard(text=reply, second=reply if step.say.second_reading else None))
        bot, turns = turn.json()["bot"], turns + 1
    phone.get(bot["audio_url"])
    log = phone.get(f"/api/sessions/{sid}").json()
    assert [e["superseded"] for e in log["events"] if e["type"] == "customer"].count(True) == 1

    case = case_of_call(phone, sid)

    assert case["customer_audio"] == {"mic": 1, "file": turns - 1, "none": 0}
    assert len(case["turns"]) == turns and case["turns"][0]["source"] == "mic"


def case_of_call(phone: TestClient, sid: str) -> dict:
    phone.post(f"/api/sessions/{sid}/case")
    case = wait_case(phone, sid)
    assert case["status"] == "ready", case["steps"]
    return case
