"""The Samajh call behind the transport's `Dialogue` protocol. No network: the LLM client is faked."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from samajh.amounts import format_inr, spoken_amount
from samajh.clients.errors import ClientError, ConfigError
from samajh.dialogue import LINES, PRODUCT_QUESTIONS, Intent, Interpretation
from samajh.server import samajh_dialogue as adapter
from samajh.server.dialogue import BotLine, BotUtterance, Heard, Step
from samajh.server.records import PACKAGED_DIR, CallRecord, RecordBook, load_book
from samajh.server.samajh_dialogue import (
    PIECE_TAG,
    call_outcome,
    call_state,
    call_transcript,
    samajh_factory,
    spoken_pieces,
)
from samajh.server.sessionlog import (
    BotEvent,
    BotLineLog,
    CustomerEvent,
    ErrorEvent,
    SessionLog,
    SttSettings,
    TtsSettings,
    lay_out,
)
from samajh.server.settings import load_settings
from samajh.types import Language, Speaker



def _dialogue_kit():
    """The scripted customers of the dialogue's own tests, so these calls follow its questions."""
    if "dialogue_kit" not in sys.modules:
        path = Path(__file__).resolve().parents[1] / "dialogue" / "dialogue_kit.py"
        spec = importlib.util.spec_from_file_location("dialogue_kit", path)
        sys.modules["dialogue_kit"] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules["dialogue_kit"])
    return sys.modules["dialogue_kit"]


CUSTOMERS = _dialogue_kit().CUSTOMERS
SETTINGS = load_settings()
BOOK = load_book(PACKAGED_DIR)
SPOKEN = {"hi": "hi-IN", "hi-en": "hi-en", "ta": "ta-IN", "kn": "kn-IN"}


@pytest.fixture(autouse=True)
def no_openrouter_key(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Every test starts with no key configured; the list holds each attempt to build the client."""
    attempts: list[dict] = []

    def from_env(**overrides):
        attempts.append(overrides)
        raise ConfigError("OPENROUTER_API_KEY is not set")

    monkeypatch.setattr(adapter.LlmClient, "from_env", from_env)
    return attempts


def dialogue(record: str = "hero", language: str = "hi", book: RecordBook = BOOK, **params: str):
    return samajh_factory(book, SETTINGS)({"record": record, "language": language, **params})


def play(call, replies: list[str], second=lambda reply: reply) -> list[Step]:
    """Answer each prompt with the next reply until they run out or the bot ends the call."""
    steps = [call.start()]
    for reply in replies:
        if steps[-1].say.end_call:
            break
        asked = steps[-1].say
        heard = Heard(text=reply, second=second(reply) if asked.second_reading else None)
        steps.append(call.step(steps[-1].state, heard))
    return steps


def answer(language: str, asked: BotUtterance, **instead: str) -> str:
    """What an informed, willing customer says to a prompt, chosen by the tags of its last line
    (so the script follows the dialogue's questions whatever their order). `instead` replaces
    the reply to one kind of prompt, as in `premium="पचपन हज़ार"`."""
    customer = CUSTOMERS[Language(language)]
    last = asked.lines[-1].tags
    replies = {q.value: reply for q, reply in zip(PRODUCT_QUESTIONS, customer.answers, strict=False)}
    replies |= {"consent": customer.consent, "open_recall": customer.recall, "second_check": customer.year}
    replies |= {"right_party_check": customer.identity, "read_back": customer.confirm} | instead
    for tag in (last["step"], last.get("asks")):
        if tag in ("read_back", "right_party_check", "second_check", "open_recall"):
            return replies[tag]
    if asked.listen == "yes_no":
        return customer.go_ahead
    return replies.get(last.get("asks", ""), customer.dont_know)


def converse(call, language: str, second=lambda reply: reply, **instead: str) -> tuple[list[Step], list[str]]:
    """A whole call with the customer of `answer`: every step and every reply."""
    steps, replies = [call.start()], []
    while not steps[-1].say.end_call and len(steps) < 80:
        asked = steps[-1].say
        replies.append(answer(language, asked, **instead))
        heard = Heard(text=replies[-1], second=second(replies[-1]) if asked.second_reading else None)
        steps.append(call.step(steps[-1].state, heard))
    return steps, replies


def lines_of(steps: list[Step]) -> list[BotLine]:
    return [line for step in steps for line in step.say.lines]


def outcome(steps: list[Step]) -> str | None:
    return steps[-1].say.tags.get("outcome") if steps[-1].say.end_call else None


# --- a whole call -------------------------------------------------------------


@pytest.mark.parametrize("language", ["hi", "hi-en"])
def test_a_whole_call_runs_from_the_hero_record_to_the_end(language: str) -> None:
    steps, _ = converse(dialogue(language=language), language)
    hero = BOOK.get("hero")

    assert outcome(steps) == "completed" and steps[-1].say.tags == {"outcome": "completed"}
    assert not any(step.say.end_call for step in steps[:-1])
    for step in steps:
        assert step.say.language == SPOKEN[language]
        for line in step.say.lines:
            assert line.key in LINES and len(line.text) <= 600
            assert line.tags["step"] and None not in line.tags.values()
    (opening,) = steps[0].say.lines
    assert opening.tags == {"step": "right_party_check"} and "Ramesh" in opening.text
    assert hero.lender_name not in opening.text
    after_yes = steps[1].say.lines  # the disclosure: several lines, each its own clip
    assert len(after_yes) > 1 and "disclosure.who" in [line.key for line in after_yes]
    assert hero.lender_name in steps[1].say.text
    asked = {line.tags.get("asks") for line in lines_of(steps)}
    assert asked >= {q.value for q in PRODUCT_QUESTIONS} | {"consent"}
    assert {line.tags.get("product_id") for line in lines_of(steps)} == {None, "P1"}


@pytest.mark.parametrize("language", ["hi", "hi-en"])
def test_only_the_amount_and_read_back_prompts_ask_for_a_second_reading(language: str) -> None:
    steps, _ = converse(dialogue(language=language), language)
    asks_premium = [step.say.lines[-1].tags.get("asks") == "premium" for step in steps]

    assert [step.say.second_reading for step in steps] == asks_premium
    assert sum(asks_premium) >= 2  # the premium question and its read-back
    assert {step.say.listen for step in steps if step.say.second_reading} == {"amount", "yes_no"}
    assert [step.say.listen for step in steps[:3]] == ["yes_no", "yes_no", "short"]
    assert "open" in {step.say.listen for step in steps}


def test_a_missing_second_reading_is_accepted_and_the_call_still_ends() -> None:
    steps, _ = converse(dialogue(), "hi", second=lambda reply: "")

    assert outcome(steps) is not None
    assert any(step.say.second_reading for step in steps)


def test_a_fresh_dialogue_continues_a_call_from_the_stored_state() -> None:
    steps, replies = converse(dialogue(language="hi-en"), "hi-en")

    assert dialogue(language="hi-en").start() == steps[0]
    assert len(steps) == len(replies) + 1
    for before, reply, after in zip(steps, replies, steps[1:], strict=False):
        heard = Heard(text=reply, second=reply if before.say.second_reading else None)
        assert dialogue(language="hi-en").step(before.state, heard) == after


def test_a_finished_call_takes_no_more_turns() -> None:
    steps, _ = converse(dialogue(), "hi")
    with pytest.raises(ValueError, match="ended"):
        dialogue().step(steps[-1].state, Heard(text="हाँ"))


@pytest.mark.parametrize(
    "params",
    [
        {"record": "nobody", "language": "hi"},
        {"record": "hero", "language": "fr"},
        {"record": "hero"},
        {"language": "hi"},
        {"record": "hero", "language": "hi", "fallback": "maybe"},
        {"record": "hero", "language": "hi", "voice": "Shivani"},
    ],
)
def test_bad_params_are_a_value_error(params: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        samajh_factory(BOOK, SETTINGS)(params)


@pytest.mark.parametrize("language", ["ta", "kn"])
def test_tamil_and_kannada_still_start(language: str) -> None:
    said = dialogue(language=language).start().say
    assert said.language == SPOKEN[language] and said.listen == "yes_no" and not said.end_call


def test_the_family_member_call_ends_before_the_lender_is_named() -> None:
    steps = play(dialogue("third-party"), [CUSTOMERS[Language.hi].wrong_person])

    assert outcome(steps) == "wrong_party"
    assert BOOK.get("third-party").lender_name not in " ".join(line.text for line in lines_of(steps))


# --- no record value reaches a bot line ----------------------------------------


def _twin_of_hero() -> RecordBook:
    """The hero's call plan (name, birth year, lender) with every tested value changed."""
    hero = BOOK.get("hero").model_dump(mode="json")
    hero["record"] |= {"lender_type": "nbfc", "loan_kind": "personal", "sanctioned_inr": 830000}
    hero["record"]["products"][0] |= {
        "provider": "Kalpit Suraksha (synthetic)",
        "premium_inr": 18750,
        "cover_inr": 275000,
        "term_months": 36,
        "paid_from_loan": False,
        "required_for_loan": True,
        "risk_mitigant": False,
        "provider_choice_offered": True,
        "cancel_window_days": None,
        "features": ["one_time_payment"],
        "consent": {"method": "otp", "at": "2026-09-03"},
    }
    return RecordBook([CallRecord.model_validate(hero)])


@pytest.mark.parametrize("language", ["hi", "hi-en"])
def test_the_bot_says_the_same_words_whatever_the_record_holds(language: str) -> None:
    customer = CUSTOMERS[Language(language)]
    _, informed = converse(dialogue(language=language), language)
    scripts = [
        informed,
        [customer.identity, customer.go_ahead, customer.year, customer.recall, customer.dont_know,
         customer.repeat, customer.correction, customer.filler, "", *customer.answers,
         customer.consent, customer.reject, customer.corrected, customer.confirm],
    ]  # fmt: skip
    for replies in scripts:
        ours = play(dialogue(language=language), replies)
        twin = play(dialogue(language=language, book=_twin_of_hero()), replies)
        assert len(ours) > 4 and [step.say for step in ours] == [step.say for step in twin]


@pytest.mark.parametrize("language", ["hi", "hi-en"])
def test_no_bot_line_holds_a_tested_value_of_the_record(language: str) -> None:
    lang = Language(language)
    product = BOOK.get("hero").record.products[0]
    # The customer says 55,000; the record says 52,000.
    steps, _ = converse(dialogue(language=language), language, premium=CUSTOMERS[lang].corrected)

    assert outcome(steps) == "completed"
    spoken = " ".join(line.text for line in lines_of(steps)).casefold()
    banned = [product.provider, BOOK.get("hero").record.loan_id, "1984"]
    for amount in (product.premium_inr, product.cover_inr):
        banned += [str(amount), format_inr(amount), spoken_amount(amount, lang)]
    # The read-back carries the customer's own figure.
    assert format_inr(55000) in spoken or spoken_amount(55000, lang).casefold() in spoken
    assert [value for value in banned if value.casefold() in spoken] == []


# --- the interpreter ----------------------------------------------------------


class _FailingLlm:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, *args, **kwargs):
        self.calls += 1
        raise ClientError("no network in tests")


def test_fallback_off_reads_with_the_rules_and_builds_no_client(no_openrouter_key: list[dict]) -> None:
    steps, _ = converse(dialogue(fallback="off"), "hi")

    assert outcome(steps) == "completed"
    assert no_openrouter_key == []


def test_without_a_key_the_rules_read_every_turn(no_openrouter_key: list[dict]) -> None:
    factory = samajh_factory(BOOK, SETTINGS)
    call = factory({"record": "hero", "language": "hi"})
    first = call.start()
    assert no_openrouter_key == []  # not when the factory runs, not when the call starts

    steps, _ = converse(call, "hi")
    converse(factory({"record": "informed", "language": "hi-en"}), "hi-en")

    assert steps[0] == first and outcome(steps) == "completed"
    assert steps == converse(dialogue(fallback="off"), "hi")[0]
    assert len(no_openrouter_key) == 1  # looked for once, for all calls


def test_with_a_key_the_fallback_client_gets_a_short_timeout_and_one_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm, built = _FailingLlm(), []
    monkeypatch.setattr(adapter.LlmClient, "from_env", lambda **kw: built.append(kw) or llm)
    call = dialogue()
    first = call.start()
    assert built == []

    steps, _ = converse(call, "hi")

    assert len(built) == 1 and steps[0] == first
    assert built[0]["timeout"] == SETTINGS.fallback.timeout_s and built[0]["retry"].max_attempts == 1
    # Some reply of a whole call is plain words to the rules, so the LLM is asked. It fails, and
    # the call goes on to its end without it.
    assert llm.calls >= 1 and outcome(steps) is not None


def test_the_fallback_switch_in_the_settings_turns_it_off(no_openrouter_key: list[dict]) -> None:
    off = SETTINGS.model_copy(update={"fallback": SETTINGS.fallback.model_copy(update={"enabled": False})})
    steps, _ = converse(samajh_factory(BOOK, off)({"record": "hero", "language": "hi"}), "hi")

    assert outcome(steps) == "completed" and no_openrouter_key == []


def test_an_injected_interpreter_reads_every_turn(no_openrouter_key: list[dict]) -> None:
    class Deaf:
        turns = 0

        def interpret(self, text, *, language, expecting, question):
            self.turns += 1
            return Interpretation(intent=Intent.silence)

    deaf = Deaf()
    call = samajh_factory(BOOK, SETTINGS, interpreter=deaf)({"record": "hero", "language": "hi"})
    steps, replies = converse(call, "hi")

    assert outcome(steps) not in (None, "completed") and deaf.turns == len(replies) <= 3
    assert no_openrouter_key == []


def test_the_two_readings_are_ordered_in_one_place() -> None:
    assert adapter.readings(Heard(text="बावन हज़ार", second="पचपन हज़ार")) == ("बावन हज़ार", "पचपन हज़ार")
    assert adapter.readings(Heard(text="बावन हज़ार", second="")) == ("बावन हज़ार", "")
    assert adapter.readings(Heard(text="हाँ")) == ("हाँ", None)


# --- silence ------------------------------------------------------------------


def test_silence_gets_no_line_of_the_adapters_own_and_the_call_still_ends() -> None:
    customer = CUSTOMERS[Language.hi]
    steps = play(dialogue(), [customer.identity, customer.go_ahead, customer.year, *[""] * 200])

    assert outcome(steps) is not None and 5 < len(steps) < 100
    assert all(line.key in LINES for line in lines_of(steps))


# --- long lines ---------------------------------------------------------------


def test_a_short_line_is_one_piece_and_a_long_one_splits_at_sentence_ends() -> None:
    assert spoken_pieces("क्या हम आगे बढ़ें?") == ("क्या हम आगे बढ़ें?",)
    sentence = "यह एक लंबा वाक्य है जो बार बार आता है।"
    text = " ".join([sentence] * 40)

    pieces = spoken_pieces(text)

    assert len(pieces) > 1 and " ".join(pieces) == text
    assert all(len(piece) <= 600 and piece.endswith("।") for piece in pieces)
    assert all(len(piece) + 1 + len(sentence) > 600 for piece in pieces[:-1])  # each is full


def test_a_sentence_or_a_word_over_the_limit_is_still_cut_to_fit() -> None:
    words = " ".join(["शब्द"] * 300)
    assert all(len(piece) <= 600 for piece in spoken_pieces(words))
    assert " ".join(spoken_pieces(words)) == words
    assert "".join(spoken_pieces("अ" * 1500)) == "अ" * 1500
    assert [len(piece) for piece in spoken_pieces("अ" * 1500)] == [600, 600, 300]


def _long_lender_book() -> RecordBook:
    hero = BOOK.get("hero")
    lender = " ".join(["नमूना बैंक की एक बहुत लंबी नाम वाली शाखा।"] * 16).rstrip("।")
    return RecordBook([hero.model_copy(update={"lender_name": lender})])


def test_a_dialogue_line_over_600_characters_is_spoken_as_several_lines() -> None:
    book = _long_lender_book()
    assert len(book.get("hero").lender_name) > 600
    steps, _ = converse(dialogue(book=book), "hi")

    assert outcome(steps) == "completed"
    who = [line for line in steps[1].say.lines if line.key == "disclosure.who"]
    assert len(who) > 1 and all(len(line.text) <= 600 for line in lines_of(steps))
    assert [line.tags[PIECE_TAG] for line in who] == [f"{k}/{len(who)}" for k in range(1, len(who) + 1)]
    assert len({(line.key, line.tags["step"]) for line in who}) == 1
    state = adapter.core.CallState.model_validate_json(steps[1].state)
    assert " ".join(line.text for line in who) in [turn.text for turn in state.turns]


# --- the call read back out of its log ------------------------------------------


def _log(steps: list[Step], replies: list[str], *, silent: frozenset[int] = frozenset()) -> SessionLog:
    """The log the transport would hold: every line 1.5 s long, every customer turn 2 s, and no
    audio for the customer turns in `silent` (their index among the customer turns)."""
    events: list = []

    def bot(step: Step) -> None:
        lines = [
            BotLineLog(key=line.key, text=line.text, tags=dict(line.tags), start_s=1.65 * k, end_s=1.65 * k + 1.5)
            for k, line in enumerate(step.say.lines)
        ]
        events.append(
            BotEvent(seq=len(events), at=0.0, audio=f"audio/bot-{len(events):03d}.wav",
                     audio_seconds=lines[-1].end_s, text=step.say.text, lines=lines,
                     language=step.say.language, end_call=step.say.end_call)
        )  # fmt: skip

    bot(steps[0])
    for k, (reply, step) in enumerate(zip(replies, steps[1:], strict=False)):
        heard = k not in silent
        events.append(
            CustomerEvent(seq=len(events), at=0.0, source="file" if heard else "none", transcript=reply,
                          audio=f"audio/customer-{len(events):03d}.wav" if heard else None,
                          audio_seconds=2.0 if heard else None)
        )  # fmt: skip
        bot(step)
    lay_out(events)
    return SessionLog(
        session_id="20261110T142233-9f2c4e1ab07d", created_at="2026-11-10T14:22:33+00:00", dialogue="samajh",
        params={"record": "hero", "language": "hi"}, line_rate=8000, stt=SttSettings(), tts=TtsSettings(),
        events=events, dialogue_state=steps[-1].state,
    )  # fmt: skip


def test_the_transcript_places_every_turn_in_the_recording() -> None:
    steps, replies = converse(dialogue(), "hi")
    log = _log(steps, replies)

    transcript = call_transcript(log)

    assert transcript.call_id == log.session_id and transcript.loan_id == "LN-DEMO-0001"
    starts = [turn.start_s for turn in transcript.turns]
    assert None not in starts and len(starts) == len(call_state(log).turns)
    assert starts == sorted(starts) and all(t.end_s > t.start_s for t in transcript.turns)
    customers = [event for event in log.events if isinstance(event, CustomerEvent)]
    said = [turn for turn in transcript.turns if turn.speaker is Speaker.customer]
    assert [(t.start_s, t.end_s, t.text) for t in said] == [
        (e.rec_start, e.rec_end, e.transcript) for e in customers
    ]
    # The disclosure is the second bot event: its second line starts one line and one gap in.
    disclosure = log.events[2]
    second = next(turn for turn in transcript.turns if turn.text == disclosure.lines[1].text)
    assert second.start_s == pytest.approx(disclosure.rec_start + 1.65)
    assert second.end_s == pytest.approx(disclosure.rec_start + 3.15)
    assert call_outcome(log) == "completed" and call_state(log).plan.loan_id == "LN-DEMO-0001"


def test_takes_that_were_replaced_and_failed_turns_are_in_no_transcript() -> None:
    log = _log(*converse(dialogue(), "hi"))
    clean = call_transcript(log)
    early_take = log.events[1].model_copy(update={"transcript": "हाँ", "superseded": True})
    early_reply = log.events[2].model_copy(update={"superseded": True})
    failed = ErrorEvent(seq=0, at=0.0, stage="stt", status=502, code="gnani_failed", message="x", audio=None)
    events = [log.events[0], early_take, early_reply, failed, *log.events[1:]]
    for seq, event in enumerate(events):
        event.seq = seq
    for event in (early_take, early_reply):
        event.rec_start = event.rec_end = None

    assert call_transcript(log.model_copy(update={"events": events})) == clean


def test_a_turn_with_no_audio_keeps_no_position() -> None:
    customer = CUSTOMERS[Language.hi]
    replies = [customer.identity, "", customer.go_ahead]
    log = _log(play(dialogue(), replies), replies, silent=frozenset({1}))
    for line in log.events[0].lines:
        line.start_s = line.end_s = None  # the opening prompt's audio was never fetched

    turns = call_transcript(log).turns

    assert (turns[0].start_s, turns[0].end_s) == (None, None)
    silent = [turn for turn in turns if turn.speaker is Speaker.customer][1]
    assert (silent.text, silent.start_s, silent.end_s) == ("", None, None)
    assert call_outcome(log) == "in_progress"


def test_pieces_of_one_long_line_are_one_transcript_turn() -> None:
    log = _log(*converse(dialogue(book=_long_lender_book()), "hi"))
    disclosure = log.events[2]
    pieces = [line for line in disclosure.lines if line.key == "disclosure.who"]
    whole = " ".join(piece.text for piece in pieces)

    (who,) = [turn for turn in call_transcript(log).turns if turn.text == whole]

    assert who.text == " ".join(piece.text for piece in pieces)
    assert who.start_s == pytest.approx(disclosure.rec_start + pieces[0].start_s)
    assert who.end_s == pytest.approx(disclosure.rec_start + pieces[-1].end_s)


def test_a_log_that_does_not_match_its_state_is_refused() -> None:
    log = _log(*converse(dialogue(), "hi"))

    with pytest.raises(ValueError, match="customer turns"):
        call_transcript(log.model_copy(update={"events": log.events[:-2] + log.events[-1:]}))
    with pytest.raises(ValueError, match="no dialogue state"):
        call_state(log.model_copy(update={"dialogue_state": None}))

