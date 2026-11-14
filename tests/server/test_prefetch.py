"""The turn route starts the dialogue's classifier on the primary transcript before it waits for the
second reading (`Dialogue.prefetch`), and `step` then reuses that call. No network: the speech
client and the LLM are faked."""

from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from serverkit import FakeSpeech
from starlette.testclient import TestClient
from test_casefile import FailingLlm
from test_two_readings import FIFTY_FIVE, FIFTY_TWO, SETTINGS, V25, V30, Call

from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.server import create_app
from samajh.server.records import PACKAGED_DIR, load_book
from samajh.server.samajh_dialogue import samajh_factory

BOOK = load_book(PACKAGED_DIR)
# Plain words to the rules at the open recall question: only the classifier can read it.
UNSETTLED = "उस दिन बैंक में भीड़ थी"
BEFORE_RECALL = ("हाँ जी, बोल रहा हूँ", "हाँ, ठीक है")  # all settled by the rules (no second check)
YEAR = "उन्नीस सौ चौरासी"  # the hero record's birth year, for a call with the year-of-birth check
# The right-party settings a call can run under: the server's default (no second check) and the
# year of birth, with the replies that reach the open recall question under each.
SETTINGS_AND_REPLIES = {
    "none": (None, BEFORE_RECALL),
    "year_of_birth": ({"second_check": "year_of_birth"}, (*BEFORE_RECALL, YEAR)),
}


class CountingLlm:
    """Answers every classifier request with "unclear" and records the reply it was asked about."""

    def __init__(self) -> None:
        self.asked: list[str] = []
        self.first = threading.Event()

    def complete(self, schema, messages, **options):
        self.asked.append(messages[-1].content.rsplit("Reply: ", 1)[-1])
        self.first.set()
        return SimpleNamespace(value=schema.model_validate({"label": "unclear"}))


class Watched:
    """Wraps a dialogue: records each prefetch with how many v2.5 readings had been asked by then."""

    def __init__(self, inner, fake: FakeSpeech, seen: list, prefetch: str = "pass") -> None:
        self.inner, self.fake, self.seen, self.mode = inner, fake, seen, prefetch
        if prefetch == "absent":
            self.prefetch = None  # a dialogue without the method

    def start(self):
        return self.inner.start()

    def step(self, state, heard):
        self.seen.append(("step", heard.text, heard.second))
        return self.inner.step(state, heard)

    def prefetch(self, state, text):
        v25 = sum(options.model == V25 for _, options in self.fake.stt_calls)
        self.seen.append(("prefetch", text, v25))
        if self.mode == "raise":
            raise RuntimeError("prefetch broke")
        self.inner.prefetch(state, text)


def phone(fake: FakeSpeech, state: Path, factory) -> TestClient:
    return TestClient(create_app(gnani=fake, state=state, web_dir=None, clips_dir=None, llm=FailingLlm,
                                 dialogues={"samajh": factory}, records=BOOK, settings=SETTINGS))  # fmt: skip


def test_prefetch_gets_the_primary_transcript_before_the_second_reading_is_asked(
    fake: FakeSpeech, state: Path
) -> None:
    seen: list = []
    inner = samajh_factory(BOOK, SETTINGS)
    call = Call(phone(fake, state, lambda params: Watched(inner(params), fake, seen)), fake, state)
    call.to_premium()
    v25_before = sum(options.model == V25 for _, options in fake.stt_calls)

    call.say(v30=FIFTY_FIVE, v25=FIFTY_TWO)

    assert seen[-2:] == [("prefetch", FIFTY_FIVE, v25_before), ("step", FIFTY_FIVE, FIFTY_TWO)]
    assert sum(options.model == V25 for _, options in fake.stt_calls) == v25_before + 1


@pytest.mark.parametrize("setting", sorted(SETTINGS_AND_REPLIES))
def test_a_classifier_begun_in_prefetch_is_not_asked_again_by_step(
    fake: FakeSpeech, state: Path, setting: str
) -> None:
    identity, before_recall = SETTINGS_AND_REPLIES[setting]
    llm, seen = CountingLlm(), []
    inner = samajh_factory(BOOK, SETTINGS, interpreter=LlmFallbackInterpreter(llm, timeout_s=5.0))

    class WaitsForTheCall(Watched):
        def prefetch(self, state, text):
            super().prefetch(state, text)
            if text == UNSETTLED:  # the classifier was asked from prefetch, before `step` ran
                assert llm.first.wait(5.0)

    call = Call(
        phone(fake, state, lambda params: WaitsForTheCall(inner(params), fake, seen)), fake, state, identity
    )
    for reply in before_recall:
        call.say(reply)
    # The opening asks the classifier (W4); count its calls from the recall turn on.
    assert call.bot["lines"][-1]["key"] == "open_recall.ask"
    before = len(llm.asked)

    turn = call.say(UNSETTLED)

    assert llm.asked[before:] == [UNSETTLED]  # once, from prefetch; `step` used that answer
    assert turn["customer"]["transcript"] == UNSETTLED and not turn["customer"]["degraded"]
    assert [kind for kind, *_ in seen[-2:]] == ["prefetch", "step"]


@pytest.mark.parametrize("mode", ["raise", "absent"])
def test_a_prefetch_that_raises_or_is_missing_never_breaks_a_turn(
    fake: FakeSpeech, state: Path, mode: str
) -> None:
    seen: list = []
    inner = samajh_factory(BOOK, SETTINGS)
    call = Call(phone(fake, state, lambda params: Watched(inner(params), fake, seen, mode)), fake, state)
    first = call.bot["lines"][-1]["key"]

    call.say(BEFORE_RECALL[0])

    assert call.bot["lines"][-1]["key"] != first  # the call moved on
    assert [kind for kind, *_ in seen] == (["prefetch", "step"] if mode == "raise" else ["step"])


def test_no_prefetch_for_an_empty_transcript(fake: FakeSpeech, state: Path) -> None:
    seen: list = []
    inner = samajh_factory(BOOK, SETTINGS)
    call = Call(phone(fake, state, lambda params: Watched(inner(params), fake, seen)), fake, state)

    call.say("")

    assert [kind for kind, *_ in seen] == ["step"]
    assert V30 in {options.model for _, options in fake.stt_calls}
