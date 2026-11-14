"""The turn classifier's record on `Step.classifier`. Stub interpreters only: no network."""

from __future__ import annotations

import time

import pytest

from samajh import dialogue as core
from samajh.dialogue import CallState, RuleInterpreter
from samajh.server import samajh_dialogue as adapter
from samajh.server.dialogue import ClassifierRecord, Heard
from samajh.server.records import PACKAGED_DIR, load_book
from samajh.server.samajh_dialogue import readings, samajh_factory
from samajh.server.settings import load_settings

SETTINGS = load_settings()
BOOK = load_book(PACKAGED_DIR)
REPLIES = ["हाँ", "हाँ बोलिए", "हाँ ठीक है", "पता नहीं", "पता नहीं"]


class Stub:
    """Word lists, with a chosen label and degraded flag on every reading."""

    def __init__(
        self, label: str | None = "yes", degraded: bool = False, sleep: float = 0.0, fail: bool = False
    ):
        self.label, self.degraded, self.sleep, self.fail = label, degraded, sleep, fail
        self.rules = RuleInterpreter()
        self._model = "stub/model"
        self.begun: list[str] = []

    def begin(self, text, *, language, expecting, question):
        self.begun.append(text)

    def interpret(self, text, *, language, expecting, question=""):
        if self.fail:
            raise RuntimeError("boom")
        time.sleep(self.sleep)
        first = self.rules.interpret(text, language=language, expecting=expecting, question=question)
        return first.model_copy(update={"classifier_label": self.label, "degraded": self.degraded})


def call(stub):
    return samajh_factory(BOOK, SETTINGS, interpreter=stub)({"record": "hero", "language": "hi"})


def test_label_and_degraded_reach_the_step():
    d = call(Stub(label="yes", degraded=True))
    first = d.start()
    assert first.classifier is None
    step = d.step(first.state, Heard(text="हाँ"))
    assert step.classifier == ClassifierRecord(
        ran=True,
        label="yes",
        latency_ms=step.classifier.latency_ms,
        model="stub/model",
        degraded=True,
        wait_ms=step.classifier.wait_ms,
    )
    assert step.classifier.latency_ms is not None


def test_no_label_records_not_ran():
    d = call(Stub(label=None))
    step = d.step(d.start().state, Heard(text="हाँ"))
    assert step.classifier is not None
    assert (step.classifier.ran, step.classifier.label, step.classifier.latency_ms) == (False, None, None)


def test_rule_interpreter_records_not_ran():
    d = samajh_factory(BOOK, SETTINGS, interpreter=RuleInterpreter())({"record": "hero", "language": "hi"})
    step = d.step(d.start().state, Heard(text="हाँ"))
    assert step.classifier == ClassifierRecord(ran=False)


def test_latency_counts_from_prefetch_begin():
    stub = Stub(label="yes")
    d = call(stub)
    state = d.start().state
    d.prefetch(state, "हाँ")
    assert stub.begun == ["हाँ"]
    time.sleep(0.15)
    step = d.step(state, Heard(text="हाँ"))
    assert step.classifier.latency_ms >= 150
    # the begin time was used up: a second step of the same turn counts from interpret again
    again = d.step(state, Heard(text="हाँ"))
    assert again.classifier.latency_ms < 150


def test_latency_without_prefetch_covers_interpret():
    d = call(Stub(label="yes", sleep=0.05))
    step = d.step(d.start().state, Heard(text="हाँ"))
    assert step.classifier.latency_ms >= 50


def test_interpreter_errors_handled_as_before():
    """core.step catches an interpreter's exception and reads the turn by the word lists; the proxy
    lets the exception reach it unchanged, so the turn comes out the same."""
    stub = Stub(fail=True)
    state = call(stub).start().state
    bare_state, bare_said = core.step(CallState.model_validate_json(state), "हाँ", interpreter=stub)
    step = call(stub).step(state, Heard(text="हाँ"))
    assert step.state == bare_state.model_dump_json()
    assert step.say == adapter._step(bare_state, bare_said).say
    assert step.classifier is not None and step.classifier.ran is False


def test_decisions_identical_with_and_without_proxy():
    stub = Stub(label="yes")
    d = call(stub)
    step = d.start()
    bare_state = CallState.model_validate_json(step.state)
    for reply in REPLIES:
        if step.say.end_call:
            break
        heard = Heard(text=reply, second=reply if step.say.second_reading else None)
        text, second = readings(heard)
        bare_state, bare_said = core.step(bare_state, text, second_reading=second, interpreter=stub)
        step = d.step(step.state, heard)
        assert step.state == bare_state.model_dump_json()
        assert step.say == adapter._step(bare_state, bare_said).say


def test_bookkeeping_failure_leaves_turn_intact(monkeypatch: pytest.MonkeyPatch):
    stub = Stub(label="yes")
    state = call(stub).start().state
    good = call(stub).step(state, Heard(text="हाँ"))

    def broken(*args, **kwargs):
        raise ValueError("recorder broke")

    monkeypatch.setattr(adapter._Recording, "_note_interpret", broken)
    bad = call(stub).step(state, Heard(text="हाँ"))
    assert bad.classifier is None
    assert (bad.state, bad.say, bad.heard, bad.degraded) == (good.state, good.say, good.heard, good.degraded)


def test_record_holds_no_text():
    assert set(ClassifierRecord.model_fields) == {"ran", "label", "latency_ms", "model", "degraded", "wait_ms"}


def test_wait_ms_is_the_classifier_time_after_the_readings():
    stub = Stub(label="yes")
    d = call(stub)
    state = d.start().state
    d.prefetch(state, "हाँ")
    time.sleep(0.3)  # the second reading's wait
    step = d.step(state, Heard(text="हाँ"))
    assert step.classifier.wait_ms is not None
    assert step.classifier.wait_ms < step.classifier.latency_ms
    assert step.classifier.latency_ms >= 300 and step.classifier.wait_ms < 300
