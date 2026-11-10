"""What the phone shows of a turn read twice: whether the readings agreed and what the bot did next.

Both come from fields (`readings_agreed`, `followed_by`) on the turn response, the session log and
the case file's `turns[]`, never from text parsed in the browser. Also: every line key and every
`Expecting` value the dialogue has today passes through the adapter, and the calls that end in
`do_not_call` or `written_requested` reach a case file. Fake Gnani, failing LLM, no network.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from pathlib import Path

import pytest
from serverkit import FakeSpeech, make_wav
from starlette.testclient import TestClient
from test_casefile import FailingLlm, wait_case
from test_loanbook import batch, drawn_hindi  # noqa: F401 - `batch` is a fixture
from test_samajh_dialogue import answer

from samajh import dialogue as core
from samajh.clients.errors import BadResponse, ServerError
from samajh.clients.llm import LlmResult
from samajh.dialogue import LINES, Expecting
from samajh.ops.store import OpsStore
from samajh.server import create_app
from samajh.server import samajh_dialogue as adapter
from samajh.server.audio import normalise_turn
from samajh.server.casefile import new_case
from samajh.server.dialogue import BotLine, BotUtterance, Heard, Step
from samajh.server.loanbook import LoanBook
from samajh.server.records import PACKAGED_DIR, load_book
from samajh.server.samajh_dialogue import followed_by, samajh_factory
from samajh.server.sessionlog import BotLineLog, SessionStore
from samajh.server.settings import load_settings
from samajh.types import Language

BOOK = load_book(PACKAGED_DIR)
SETTINGS = load_settings().model_copy(
    update={"fallback": load_settings().fallback.model_copy(update={"enabled": False})}
)
V30, V25 = "prisma-v3.0", "prisma-v2.5"
PACKAGED_CALLS = Path(__file__).resolve().parents[1] / "fixtures" / "server" / "calls"

# A turn's readings: one text both models give, or (v3.0's text, v2.5's text or the error it raises).
Readings = str | tuple[str, str | Exception]


def phone_for(fake: FakeSpeech, state: Path) -> TestClient:
    fake.transcripts.clear()
    return TestClient(
        create_app(
            gnani=fake,
            state=state,
            web_dir=None,
            clips_dir=None,
            dialogues={"samajh": samajh_factory(BOOK, SETTINGS, loans=LoanBook(state))},
            records=BOOK,
            settings=SETTINGS,
            llm=FailingLlm,
        )
    )


def asks(step: Step) -> tuple[str, str | None]:
    last = step.say.lines[-1]
    return last.tags["step"], last.tags.get("asks")


def drive(
    phone: TestClient,
    fake: FakeSpeech,
    state: Path,
    params: dict[str, str],
    reply: Callable[[Step], Readings | None],
    interpreter=None,
) -> tuple[str, list[dict]]:
    """A whole call. `reply(step)` gives the readings of the answer to the twin's step, or None for
    the informed customer's answer heard alike by both models. Returns the session id and every
    turn response."""
    created = phone.post("/api/sessions", json={"params": params})
    assert created.status_code == 201, created.text
    sid, bot = created.json()["session_id"], created.json()["bot"]
    stored = SessionStore(state / "sessions").load(sid).params
    twin = samajh_factory(BOOK, SETTINGS, loans=LoanBook(state), interpreter=interpreter)(stored)
    step, responses = twin.start(), []
    record = BOOK.get(params["record"]) if "record" in params else LoanBook(state).resolve(stored)[0]
    while not bot["end_call"]:
        assert len(responses) < 60 and phone.get(bot["audio_url"]).status_code == 200
        readings = reply(step)
        if readings is None:
            readings = answer(params["language"], step.say, second_check=str(record.record.borrower.dob.year))
        fake.model_transcripts, fake.model_errors = {}, {}
        if isinstance(readings, str):
            primary, second = readings, readings
            fake.transcripts.append(readings)
        else:
            primary, theirs = readings
            fake.model_transcripts = {V30: [primary]}
            if isinstance(theirs, Exception):
                fake.model_errors = {V25: theirs}
                second = ""
            else:
                fake.model_transcripts[V25] = [theirs]
                second = theirs
        clip = make_wav(0.5 + len(responses) / 100, tone=200 + len(responses))
        turn = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to={bot['seq']}", content=clip)
        assert turn.status_code == 200, turn.text
        fake.model_transcripts, fake.model_errors = {}, {}
        responses.append(turn.json())
        step = twin.step(step.state, Heard(text=primary, second=second if step.say.second_reading else None))
        bot = turn.json()["bot"]
    assert phone.get(bot["audio_url"]).status_code == 200
    return sid, responses


def premium_answers(*answers: Readings) -> Callable[[Step], Readings | None]:
    """The n-th time the premium is asked (question or say-again), the n-th of `answers`."""
    left = list(answers)

    def reply(step: Step) -> Readings | None:
        if asks(step) == ("teach_back", "premium") and left:
            return left.pop(0)
        return None

    return reply


def figure_turns(responses: list[dict]) -> list[dict]:
    return [r["customer"] for r in responses if r["customer"]["readings_agreed"] is not None]


def case_of(phone: TestClient, sid: str) -> dict:
    phone.post(f"/api/sessions/{sid}/case")
    case = wait_case(phone, sid)
    assert case["status"] == "ready", case["steps"]
    return case


# --- the two fields, over HTTP and in the case file --------------------------------


def test_readings_that_agree_are_read_back(fake: FakeSpeech, state: Path) -> None:
    phone = phone_for(fake, state)
    sid, responses = drive(phone, fake, state, {"record": "hero", "language": "hi"},
                           premium_answers(("52,000", "बावन हज़ार")))  # fmt: skip

    (premium, *_) = figure_turns(responses)
    assert [r["model"] for r in premium["readings"]] == [V30, V25]
    assert [r["text"] for r in premium["readings"]] == ["52,000", "बावन हज़ार"]
    assert (premium["readings_agreed"], premium["followed_by"]) == (True, "read_back")
    case_turn = next(t for t in case_of(phone, sid)["turns"] if t["seq"] == premium["seq"])
    assert (case_turn["readings_agreed"], case_turn["followed_by"]) == (True, "read_back")


def test_readings_that_differ_are_asked_again_then_read_back_when_they_agree(
    fake: FakeSpeech, state: Path
) -> None:
    phone = phone_for(fake, state)
    sid, responses = drive(phone, fake, state, {"record": "hero", "language": "hi"},
                           premium_answers(("1,300", "एक लाख तीन सौ"), ("1,00,300", "एक लाख तीन सौ")))  # fmt: skip

    first, again = figure_turns(responses)[:2]
    assert (first["readings_agreed"], first["followed_by"]) == (False, "asked_again")
    assert (again["readings_agreed"], again["followed_by"]) == (True, "read_back")
    asked_next = responses[[r["customer"]["seq"] for r in responses].index(first["seq"])]["bot"]["lines"][-1]
    assert asked_next["key"] == "premium.say_again"
    log = phone.get(f"/api/sessions/{sid}").json()
    stored = {e["seq"]: e for e in log["events"] if e["type"] == "customer"}
    assert (stored[first["seq"]]["readings_agreed"], stored[first["seq"]]["followed_by"]) == (
        False,
        "asked_again",
    )
    turns = {t["seq"]: t for t in case_of(phone, sid)["turns"]}
    assert [(turns[c["seq"]]["readings_agreed"], turns[c["seq"]]["followed_by"]) for c in (first, again)] == [
        (False, "asked_again"),
        (True, "read_back"),
    ]


def test_readings_that_differ_twice_are_read_back_with_the_figure_the_call_acted_on(
    fake: FakeSpeech, state: Path
) -> None:
    phone = phone_for(fake, state)
    sid, responses = drive(phone, fake, state, {"record": "hero", "language": "hi"},
                           premium_answers(("1,300", "एक लाख तीन सौ"), ("1,300", "एक लाख तीन सौ")))  # fmt: skip

    first, again = figure_turns(responses)[:2]
    assert (first["readings_agreed"], first["followed_by"]) == (False, "asked_again")
    assert (again["readings_agreed"], again["followed_by"]) == (False, "read_back")
    assert again["acted_on"] == "second" and again["transcript"] == "एक लाख तीन सौ"
    reply = next(r for r in responses if r["customer"]["seq"] == again["seq"])["bot"]
    assert reply["lines"][-1]["key"] == "read_back.confirm" and "1,300" not in reply["text"]
    turn = next(t for t in case_of(phone, sid)["turns"] if t["seq"] == again["seq"])
    assert (turn["readings_agreed"], turn["followed_by"], turn["acted_on"]) == (False, "read_back", V25)


def test_a_missing_second_reading_is_never_agreement(fake: FakeSpeech, state: Path) -> None:
    phone = phone_for(fake, state)
    down = ServerError(status=504, code=None, message="v2.5 answered 504")
    sid, responses = drive(phone, fake, state, {"record": "hero", "language": "hi"},
                           premium_answers(("52,000", down), ("52,000", down)))  # fmt: skip

    first, again = figure_turns(responses)[:2]
    assert [r["ok"] for r in first["readings"]] == [True, False] and first["readings"][1]["error"]
    assert first["readings_agreed"] is False and first["acted_on"] == "primary"
    assert first["followed_by"] == "asked_again"
    assert (again["readings_agreed"], again["followed_by"]) == (False, "read_back")
    turn = next(t for t in case_of(phone, sid)["turns"] if t["seq"] == first["seq"])
    assert (turn["readings_agreed"], turn["followed_by"]) == (False, "asked_again")


def test_a_turn_read_once_or_with_no_figure_has_no_agreement(fake: FakeSpeech, state: Path) -> None:
    phone = phone_for(fake, state)
    _, responses = drive(phone, fake, state, {"record": "hero", "language": "hi"}, lambda step: None)

    once = [r["customer"] for r in responses if len(r["customer"]["readings"]) == 1]
    plain_yes = [r["customer"] for r in responses
                 if len(r["customer"]["readings"]) == 2 and r["customer"]["transcript"] == "हाँ, सही है"]  # fmt: skip
    assert once and all(c["readings_agreed"] is None for c in once)
    assert plain_yes and all(c["readings_agreed"] is None for c in plain_yes)
    assert {c["followed_by"] for r in responses for c in [r["customer"]]} <= {
        "read_back",
        "asked_again",
        "other",
    }


# --- followed_by and the listen kinds over every key and Expecting value ---------------


def test_followed_by_is_read_from_the_last_line_of_the_reply() -> None:
    read_back = {
        "read_back.confirm",
        "read_back.confirm_about",
        "read_back.cover_confirm",
        "read_back.reconfirm",
    }
    asked_again = {
        "premium.reask",
        "premium.say_again",
        "cover.reask",
        "cover.say_again",
        "read_back.restate",
    }
    for key, spec in LINES.items():
        line = BotLineLog(key=key, text="x", tags={"step": spec.step.value})
        wanted = "read_back" if key in read_back else "asked_again" if key in asked_again else "other"
        assert followed_by([line]) == wanted, key
        # Only the last line counts: a bridge after a read-back line is not a read-back.
        assert (
            followed_by([line, BotLineLog(key="kind.ask", text="x", tags={"step": "teach_back"})]) == "other"
        )
    assert followed_by([]) == "other"
    assert followed_by([BotLineLog(key="stub.q1", text="x")]) == "other"


# The listen kind of every `Expecting` value, chosen here on purpose (reasons in samajh_dialogue).
LISTEN = {
    Expecting.identity: "yes_no",
    Expecting.go_ahead: "yes_no",
    Expecting.confirmation: "yes_no",
    Expecting.stop_check: "yes_no",
    Expecting.birth_year: "short",
    Expecting.amount: "amount",
    Expecting.open: "open",
    Expecting.told: "open",
    Expecting.either_or: "open",
    Expecting.callback_time: "open",
}


def test_every_expecting_value_has_a_listen_kind_chosen_on_purpose() -> None:
    assert set(LISTEN) == set(Expecting)  # a new value fails here until it is placed
    for expects, kind in LISTEN.items():
        assert adapter._LISTEN.get(expects.value, "open") == kind, expects
        assert (expects.value in adapter._MAY_CARRY_A_FIGURE) == (
            expects in {Expecting.amount, Expecting.confirmation}
        )
    assert set(LISTEN.values()) == set(SETTINGS.turn_taking)


@pytest.mark.parametrize("language", ["hi", "hi-en", "ta", "kn"])
def test_every_line_key_passes_through_the_adapter(language: str) -> None:
    pack = core.load_prompts(Language(language))
    for key, spec in LINES.items():
        slots = {name: "1" if name == "ordinal" else "राम" for name in spec.slots}
        line = core.Line(key=key, slots=slots, text=pack.render(key, **slots), step=spec.step, asks=spec.asks,
                         product_id="P1" if spec.asks else None)  # fmt: skip
        (made,) = adapter._bot_lines(line)
        assert (made.key, made.text, made.tags["step"]) == (key, line.text, spec.step.value)
        assert made.tags.get("asks") == (spec.asks.value if spec.asks else None)


# --- the new outcomes reach a case file --------------------------------------------

DO_NOT_CALL = "मुझे दोबारा कॉल मत करना, मेरा नंबर हटा दीजिए"
WRITTEN = "ये सब मुझे लिखकर भेज दीजिए"


def at_kind(said: str) -> Callable[[Step], Readings | None]:
    return lambda step: said if asks(step) == ("teach_back", "kind") else None


@pytest.mark.parametrize(("said", "outcome"), [(DO_NOT_CALL, "do_not_call"), (WRITTEN, "written_requested")])
def test_a_call_ending_in_a_new_outcome_reaches_a_case_file_on_a_packaged_record(
    fake: FakeSpeech, state: Path, said: str, outcome: str
) -> None:
    phone = phone_for(fake, state)
    sid, responses = drive(phone, fake, state, {"record": "hero", "language": "hi"}, at_kind(said))

    assert responses[-1]["customer"]["transcript"] == said and responses[-1]["ended"]
    case = case_of(phone, sid)
    assert case["call_outcome"] == outcome and case["book"] is None and case["tier"] != "clear"


@pytest.mark.parametrize(("said", "outcome"), [(DO_NOT_CALL, "do_not_call"), (WRITTEN, "written_requested")])
def test_a_call_ending_in_a_new_outcome_reaches_a_case_file_on_a_loan_book_loan(
    fake: FakeSpeech,
    state: Path,
    batch: OpsStore,  # noqa: F811 - the fixture
    said: str,
    outcome: str,
) -> None:
    loan_id = drawn_hindi(batch).record.loan_id
    phone = phone_for(fake, state)
    sid, responses = drive(phone, fake, state, {"loan": loan_id, "language": "hi"}, at_kind(said))

    assert responses[-1]["ended"]
    case = case_of(phone, sid)
    assert case["call_outcome"] == outcome and case["loan_id"] == loan_id and case["book"]["draw_id"]


# --- the prepared demo call in which the two models disagree ----------------------

AMOUNT_CHECK = PACKAGED_CALLS / "amount-check"


class PremiumOnlyLlm:
    """An extraction model that judges only the premium: a stated amount whose span is the first
    rupee figure of the reply, and a read-back the customer confirms. Every other request fails as
    a bad model output does (the field becomes unclear)."""

    def complete(self, schema, messages, *, model=None, max_tokens=1024):
        reply = re.search(r"Customer's reply: <<<(.*?)>>>", messages[1].content, re.DOTALL).group(1)
        name = schema.__name__
        figure = re.search(r"₹?[0-9][0-9,]*", reply)
        if name == "SpanReply" and figure and "2,012" in reply:
            output = {"status": "stated", "span": figure.group(0), "clauses": [1]}
        elif name == "ReadbackReply" and reply.startswith("हाँ"):
            output = {"status": "stated", "confirms": True, "clauses": [1], "corrected_amount_span": None}
        elif name == "ScreenReply":
            output = {"claims": [], "concerns": []}
        elif name == "ChangeReply":
            output = {"change": "none", "first_clauses": [], "final_clauses": []}
        else:
            raise BadResponse("the fake model judges the premium only")
        return LlmResult(value=schema.model_validate(output), model="fake", prompt_tokens=0, completion_tokens=0,
                         usd=0.0, cache_hit=True, attempts=0, generation_id=None)  # fmt: skip


def measured_speech(fake: FakeSpeech, persona) -> None:
    """The fake hears each prepared clip as its call.json text, except a clip whose text the
    persona measured: v3.0 and v2.5 then write what they wrote on the real line."""
    manifest = json.loads((AMOUNT_CHECK / "call.json").read_text(encoding="utf-8"))
    said = {
        hashlib.sha256(normalise_turn((AMOUNT_CHECK / t["file"]).read_bytes(), 8000)).hexdigest(): t["text"]
        for t in manifest["turns"]
    }
    real = fake.stt

    def stt(audio, options, **kw):
        text = said[hashlib.sha256(audio).hexdigest()]
        v30, v25 = persona.measured.get(text, (text, text))
        fake.model_transcripts = {options.model: [v30 if options.model == V30 else v25]}
        try:
            return real(audio, options, **kw)
        finally:
            fake.model_transcripts = {}

    fake.stt = stt


def test_the_prepared_demo_call_asks_again_and_reads_back_the_right_figure(
    fake: FakeSpeech, state: Path, tmp_path: Path
) -> None:
    from samajh.server.prepare import PERSONAS
    from samajh.server.replay import load_script, replay_call

    persona = PERSONAS["amount-check"]
    measured_speech(fake, persona)
    phone = TestClient(create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, llm=PremiumOnlyLlm,
                                  dialogues={"samajh": samajh_factory(BOOK, SETTINGS)}, records=BOOK,
                                  settings=SETTINGS))  # fmt: skip
    script = load_script(AMOUNT_CHECK)
    assert script.params == {"record": "amount-check", "language": "hi"}

    result = replay_call(phone, script, case=True, out=tmp_path / "out")

    log = result.log
    customers = [e for e in log.events if e.type == "customer" and not e.superseded]
    replies = {e.seq: log.events[e.seq + 1] for e in customers}
    asked = [(e.transcript, replies[e.seq].lines[-1].key) for e in customers]
    premium = [i for i, e in enumerate(customers) if len(e.readings) == 2 and e.readings_agreed is False]
    assert len(premium) == 2  # the premium, and the same words said again
    first, again = (customers[i] for i in premium)
    assert [r.text for r in first.readings] == ["2,000 रुपये रुपये दिए थे।", "₹2,012 दिए थे"]
    assert [r.model for r in first.readings] == [V30, V25]
    assert (first.followed_by, again.followed_by) == ("asked_again", "read_back")
    assert asked[premium[0]][1] == "premium.say_again" and asked[premium[1]][1] == "read_back.confirm"
    read_back = replies[again.seq].lines[-1].text
    assert "दो हज़ार बारह" in read_back and "दो हज़ार रुपये" not in read_back
    confirmed = customers[premium[1] + 1]
    assert (
        confirmed.transcript == "हाँ, सही है" and replies[confirmed.seq].lines[-1].tags["step"] != "read_back"
    )
    assert log.ended_reason == "dialogue" and result.case["call_outcome"] == "completed"

    case = result.case
    assert case["status"] == "ready", case["steps"]
    (product,) = case["result"]["products"]
    # The premium check passed against the record (2,012): the figure the call acted on and read
    # back. Every other field is unclear (the fake model judges the premium only), so the case is
    # not clear; that is not what this test is about.
    assert "premium" in product["passed"]
    assert not [x for x in product["flags"] + product["gaps"] if x["rule_id"] == "premium"]
    assert not [e for e in case["evidence"] if e["rule_id"] == "premium"]


# --- the packaged personas against today's dialogue ---------------------------------

INTENDED = {
    "hero": "completed",
    "informed": "completed",
    "third-party": "wrong_party",
    "amount-check": "completed",
}


@pytest.mark.parametrize("name", sorted(INTENDED))
def test_each_packaged_persona_reaches_its_intended_outcome(name: str) -> None:
    from samajh.server.prepare import PERSONAS, script

    persona = PERSONAS[name]
    call = samajh_factory(BOOK, SETTINGS)(persona.params() | {"fallback": "off"})
    step, keys = call.start(), []
    while not step.say.end_call:
        assert len(keys) < 60
        reply = persona.reply(step.say)
        keys.append(step.say.lines[-1].key)
        primary, second = persona.measured.get(reply, (reply, reply))
        step = call.step(step.state, Heard(text=primary, second=second if step.say.second_reading else None))

    assert step.say.tags["outcome"] == INTENDED[name]
    assert [t["answers"] for t in script(persona)] == keys
    if name == "amount-check":  # the premium is asked (not carried from open recall), said again, read back
        assert keys[keys.index("premium.ask") :][:3] == [
            "premium.ask",
            "premium.say_again",
            "read_back.confirm",
        ]
        manifest = json.loads((AMOUNT_CHECK / "call.json").read_text(encoding="utf-8"))
        assert [t["answers"] for t in manifest["turns"]] == keys  # the voiced call is today's script


def test_a_persona_reply_for_a_new_key_is_its_own_not_the_fallback() -> None:
    from samajh.server.prepare import PERSONAS

    def said(key: str, step: str, asks: str | None, listen: str = "open"):
        tags = {"step": step} | ({"asks": asks} if asks else {})
        return BotUtterance(lines=(BotLine(text="x", key=key, tags=tags),), language="hi-IN", listen=listen)

    for name in ("hero", "informed", "amount-check"):
        persona = PERSONAS[name]
        # "shall I ask on, or stop here?": a bare yes would be no answer to an either-or.
        assert (
            persona.reply(said("stop_check.disengaged", "close", None, "yes_no")) != persona.replies["yes_no"]
        )
    assert PERSONAS["informed"].reply(said("cover.say_again", "teach_back", "cover", "amount")) == "five lakh"
    assert (
        PERSONAS["amount-check"].reply(said("cover.say_again", "teach_back", "cover", "amount")) == "एक लाख"
    )


# --- degraded turns ----------------------------------------------------------------


class FailsOnce:
    """The word lists, except that reading `fail_on` raises, as a classifier that fails does."""

    def __init__(self, fail_on: str) -> None:
        self.rules, self.fail_on, self.failed = core.RuleInterpreter(), fail_on, 0

    def interpret(self, text, *, language, expecting, question):
        if text == self.fail_on and self.failed < 2:  # once for the server's call, once for its twin
            self.failed += 1
            raise TimeoutError("the classifier did not answer in time")
        return self.rules.interpret(text, language=language, expecting=expecting, question=question)


def phone_with(fake: FakeSpeech, state: Path, interpreter) -> TestClient:
    fake.transcripts.clear()
    factory = samajh_factory(BOOK, SETTINGS, interpreter=interpreter)
    return TestClient(create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, llm=FailingLlm,
                                 dialogues={"samajh": factory}, records=BOOK, settings=SETTINGS))  # fmt: skip


def test_a_turn_read_without_the_classifier_is_marked_everywhere(fake: FakeSpeech, state: Path) -> None:
    kind = "एफडी है, लोन के लिए ज़रूरी था"
    interpreter = FailsOnce(kind)
    phone = phone_with(fake, state, interpreter)
    sid, responses = drive(
        phone, fake, state, {"record": "hero", "language": "hi"}, at_kind(kind), interpreter
    )

    marked = [r["customer"] for r in responses if r["customer"]["degraded"]]
    assert [c["transcript"] for c in marked] == [kind]
    log = phone.get(f"/api/sessions/{sid}").json()
    stored = [e for e in log["events"] if e["type"] == "customer"]
    assert [e["transcript"] for e in stored if e["degraded"]] == [kind]
    case = case_of(phone, sid)
    (turn,) = [t for t in case["turns"] if t["degraded"]]
    assert turn["seq"] == marked[0]["seq"] and case["degraded_turns"] == [turn["turn_id"]]
    # The case file's head carries the list, from the session alone: a case file whose later steps
    # fail (or one still running) still says the call is void, so samajh.ops never counts it.
    head = new_case(SessionStore(state / "sessions").load(sid), BOOK.get("hero"))
    assert head.status == "running" and head.degraded_turns == case["degraded_turns"]


def test_a_call_with_no_degraded_turn_says_so(fake: FakeSpeech, state: Path) -> None:
    phone = phone_with(fake, state, core.RuleInterpreter())
    sid, responses = drive(phone, fake, state, {"record": "hero", "language": "hi"}, lambda step: None)

    assert not any(r["customer"]["degraded"] for r in responses)
    case = case_of(phone, sid)
    assert case["degraded_turns"] == [] and not any(t["degraded"] for t in case["turns"])


# --- speaker_confirmed -------------------------------------------------------------


class StandIn:
    """A dialogue state with `speaker_confirmed` set to `value`, or without it (`absent`)."""

    def __init__(self, value: object = "absent") -> None:
        if value != "absent":
            self.speaker_confirmed = value


def test_speaker_confirmed_is_read_from_the_state_and_never_guessed() -> None:
    assert [adapter.speaker_confirmed(StandIn(v)) for v in (True, False, "absent")] == [True, False, None]
    assert adapter.speaker_confirmed(StandIn("yes")) is None  # not a bool: unknown
    today = samajh_factory(BOOK, SETTINGS)({"record": "hero", "language": "hi"}).start()
    expected = getattr(core.CallState.model_validate_json(today.state), "speaker_confirmed", None)
    assert today.speaker_confirmed is expected


@pytest.mark.parametrize("value", [True, False, "absent"])
def test_speaker_confirmed_reaches_the_session_and_the_case_file(
    fake: FakeSpeech, state: Path, monkeypatch: pytest.MonkeyPatch, value: object
) -> None:
    real = adapter.speaker_confirmed
    monkeypatch.setattr(adapter, "speaker_confirmed", lambda state: real(StandIn(value)))
    wanted = None if value == "absent" else value
    phone = phone_for(fake, state)
    sid, responses = drive(phone, fake, state, {"record": "hero", "language": "hi"}, at_kind(DO_NOT_CALL))

    assert responses[-1]["ended"] and responses[-1]["outcome"] == "do_not_call"
    assert responses[-1]["speaker_confirmed"] is wanted
    assert phone.get(f"/api/sessions/{sid}").json()["speaker_confirmed"] is wanted
    assert case_of(phone, sid)["speaker_confirmed"] is wanted


def _declines_at_go_ahead(step: Step) -> Readings | None:
    return "नहीं, अभी बात नहीं करनी" if asks(step)[0] == "disclosure" else None


@pytest.mark.parametrize(
    ("reply", "outcome", "wanted"),
    [(at_kind(DO_NOT_CALL), "do_not_call", True), (_declines_at_go_ahead, "declined", False)],
)
def test_the_real_dialogue_says_whether_the_birth_year_check_was_passed(
    fake: FakeSpeech, state: Path, reply, outcome: str, wanted: bool
) -> None:
    """The round 3 dialogue carries `speaker_confirmed`: True after the year of birth was given,
    False (not unknown) for a call that ended before the check."""
    phone = phone_for(fake, state)
    sid, responses = drive(phone, fake, state, {"record": "hero", "language": "hi"}, reply)

    assert responses[-1]["ended"] and responses[-1]["outcome"] == outcome
    assert responses[-1]["speaker_confirmed"] is wanted
    assert phone.get(f"/api/sessions/{sid}").json()["speaker_confirmed"] is wanted
    assert case_of(phone, sid)["speaker_confirmed"] is wanted
