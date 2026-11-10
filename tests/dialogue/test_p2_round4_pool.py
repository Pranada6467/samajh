"""P2 round 4, item 7: one call's slow classifier never starves another call's turns.

A timed-out classifier degrades only its own turn; requests start at once whatever other calls are
doing; a request whose turn gave up does not hold up later ones. No network: the client is faked.
The measurement at 10 parallel calls (old 4-worker pool against this) is
`tests/dialogue/probes/p2_round4_pool.py`."""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

import pytest
from dialogue_kit import CUSTOMERS, play, record

from samajh.dialogue import Expecting, Intent
from samajh.dialogue import llm_fallback as fb
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.types import Language

HI = Language.hi
Q = "वो क्या है?"
SLOW = "आज बहुत गर्मी है"  # unsettled at the open question: only the classifier can read it


class GatedLlm:
    """Answers "answer" ("yes" at the go-ahead) after `delay` s; a reply in `stuck` waits for `release`."""

    def __init__(self, delay: float = 0.0, stuck: frozenset[str] = frozenset()) -> None:
        self.delay, self.stuck = delay, stuck
        self.release = threading.Event()
        self.asked: list[str] = []
        self._lock = threading.Lock()

    def complete(self, schema, messages, **_):
        reply = messages[-1].content.rsplit("Reply: ", 1)[-1]
        with self._lock:
            self.asked.append(reply)
        if reply in self.stuck:
            self.release.wait(30)
        else:
            time.sleep(self.delay)
        go_ahead = "Stage: go_ahead" in messages[-1].content
        return SimpleNamespace(value=schema(label="yes" if go_ahead else "answer"))


@pytest.fixture
def gated():
    made: list[GatedLlm] = []

    def make(**kwargs) -> GatedLlm:
        made.append(GatedLlm(**kwargs))
        return made[-1]

    yield make
    for llm in made:
        llm.release.set()  # let every stuck request finish so no thread outlives the test


def test_a_timed_out_turn_degrades_only_that_turn_of_that_call(gated):
    llm = gated(stuck=frozenset({SLOW}))
    shared = LlmFallbackInterpreter(llm, timeout_s=0.3)  # one interpreter for all calls, as the server
    happy = CUSTOMERS[HI].happy()
    calls: dict[str, object] = {}

    def other_call() -> None:
        calls["other"] = play(record(), HI, [*happy[:3], "उस दिन बैंक में भीड़ थी", "मेरा बेटा कॉलेज गया है"],
                              interpreter=shared)  # fmt: skip

    other = threading.Thread(target=other_call)
    other.start()
    began = time.monotonic()
    # The slow turn, then "go on", then a turn only the classifier can read.
    slow = play(record(), HI, [*happy[:3], SLOW, "हाँ", "पड़ोस में शादी चल रही है"], interpreter=shared)
    other.join()

    assert time.monotonic() - began < 2.0  # waited once for 0.3 s, not for the stuck request
    assert len(slow.state.degraded_turns) == 1  # only the timed-out turn
    assert "stop_check.decline" in slow.keys  # read by the word lists, degraded: asked once whether to go on
    assert "पड़ोस में शादी चल रही है" in llm.asked  # the next turn was judged by the classifier
    assert calls["other"].state.degraded_turns == ()  # the other call never noticed


def test_ten_parallel_calls_with_three_stuck_starve_nobody(gated):
    stuck_texts = {f"{SLOW} {c}-{t}" for c in range(3) for t in range(4)}
    llm = gated(delay=0.2, stuck=frozenset(stuck_texts))
    shared = LlmFallbackInterpreter(llm, timeout_s=0.6)
    degraded: dict[int, int] = {}

    def call(c: int) -> None:
        count = 0
        for t in range(4):
            text = f"{SLOW} {c}-{t}"
            shared.begin(text, language=HI, expecting=Expecting.open, question=Q)
            heard = shared.interpret(text, language=HI, expecting=Expecting.open, question=Q)
            assert heard.intent is Intent.said  # judged or not, the turn is read and nothing raised
            count += heard.degraded
        degraded[c] = count

    threads = [threading.Thread(target=call, args=(c,)) for c in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert [degraded[c] for c in range(3)] == [4, 4, 4]  # every turn of a stuck call times out
    assert [degraded[c] for c in range(3, 10)] == [0] * 7  # and no other call loses a turn


def test_past_the_live_bound_a_turn_degrades_at_once_instead_of_queueing(gated, monkeypatch):
    monkeypatch.setattr(fb, "_LIVE", threading.BoundedSemaphore(1))
    llm = gated(stuck=frozenset({SLOW}))
    shared = LlmFallbackInterpreter(llm, timeout_s=1.0)
    shared.begin(SLOW, language=HI, expecting=Expecting.open, question=Q)  # holds the one slot

    began = time.monotonic()
    heard = shared.interpret("उस दिन बैंक में भीड़ थी", language=HI, expecting=Expecting.open, question=Q)
    assert time.monotonic() - began < 0.5
    assert heard.degraded and heard.intent is Intent.said
    assert "उस दिन बैंक में भीड़ थी" not in llm.asked  # never sent
    llm.release.set()  # end the held request while the small semaphore is still in place
    assert fb._LIVE.acquire(timeout=5)  # its thread has released the slot: nothing outlives the test
    fb._LIVE.release()
