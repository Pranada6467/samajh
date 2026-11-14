"""Iteration 4, W4 checkpoint 1: a context-aware classifier decides at the opening; the year never reaches a model.

A fake LLM records every request and answers a label chosen per stage. Typed text, Hindi."""

from __future__ import annotations

from types import SimpleNamespace

from dialogue_kit import NO_CHECK, YEAR_POLICY, play, product, record

from samajh.clients.errors import TransportError
from samajh.dialogue import Outcome
from samajh.dialogue.interpret import Expecting, RuleInterpreter
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.types import Language

HI = Language.hi
SAMEER = "Sameer Kalpit"


class Recorder:
    """A fake `LlmClient`: `labels` maps a stage word ("first_name", "go_ahead", ...) to a label; records requests."""

    def __init__(self, labels: dict[str, str] | None = None, error: Exception | None = None) -> None:
        self.labels, self.error, self.calls = labels or {}, error, []

    def complete(self, schema, messages, **kwargs):
        self.calls.append(messages)
        if self.error:
            raise self.error
        content = messages[-1].content
        stage = content.split("\n")[0]
        label = next((v for k, v in self.labels.items() if k in stage), "unclear")
        return SimpleNamespace(value=schema(label=label))

    def contents(self) -> str:
        return "\n".join(m.content for call in self.calls for m in call)


SENSIBLE = {"first_name": "confirms_self", "go_ahead": "yes", "question": "answer"}


def call(replies, llm, *, name="Ramesh Kalpit", identity=NO_CHECK):
    return play(record(product(), name=name), HI, replies, interpreter=LlmFallbackInterpreter(llm), identity=identity)


def test_the_context_reaches_the_prompt():
    llm = Recorder({"first_name": "yes"})
    call(["हाँ जी", "जी, मैं रमेश बोल रहा हूँ"], llm)
    second = llm.calls[1][-1].content
    assert "Borrower's first name on the record: Ramesh" in second
    assert "Previous reply: हाँ जी" in second and "Previous question:" in second
    assert "रमेश: the borrower's name" in second
    assert "Allowed labels:" in second and "answer" not in second.split("Allowed labels:")[1].split("\n")[0]


def test_a_different_name_is_hinted():
    llm = Recorder({"first_name": "confirms_self"})
    call(["हाँ, मैं ही राजेश हूँ"], llm)
    assert all("राजेश: a different first name" in c[-1].content for c in llm.calls)


def test_a_tight_claim_now_reaches_the_classifier():
    llm = Recorder(SENSIBLE)
    c = call(["हाँ जी, मैं ही रमेश हूँ"], llm)
    assert len(llm.calls) == 1 and c.state.speaker_confirmed and c.keys[-1] == "disclosure.go_ahead"


def test_vetoes_never_reach_the_classifier_and_end_as_before():
    for reply, outcome in [("मुझे बात नहीं करनी", Outcome.declined), ("मेरा नंबर हटा दो", Outcome.do_not_call),
                           ("वो घर पर नहीं हैं", Outcome.wrong_party)]:  # fmt: skip
        llm = Recorder({"first_name": "confirms_self"})
        c = call([reply], llm)
        rules = play(record(product()), HI, [reply], identity=NO_CHECK)
        assert llm.calls == [] and c.end.outcome is outcome and rules.end.outcome is outcome, reply


def test_a_claim_with_a_trailing_question_passes_on_confirms_self():
    reply = "हां भाई, मैं ही समीर हूँ. क्या issue है?"
    c = call([reply], Recorder(SENSIBLE), name=SAMEER)
    assert c.end is None and c.state.speaker_confirmed and c.keys[-1] == "disclosure.go_ahead"
    assert c.state.degraded_turns == ()


def test_a_claim_with_a_trailing_question_on_unclear_is_not_judged_and_voids_the_session():
    # The coordinator's clarification: on a failure or `unclear` the call behaves as today (the word lists' claim with
    # a tail), with the turn marked degraded, so the server voids the session.
    c = call(["हां भाई, मैं ही समीर हूँ. क्या issue है?"], Recorder({"first_name": "unclear"}), name=SAMEER)
    assert c.state.degraded_turns != ()


def test_a_classifier_failure_on_a_settled_claim_keeps_todays_reading_marked_degraded():
    c = call(["हाँ जी, बोल रहा हूँ"], Recorder(error=TransportError("down")))
    rules = play(record(product()), HI, ["हाँ जी, बोल रहा हूँ"], identity=NO_CHECK)
    assert c.keys == rules.keys and c.state.degraded_turns != ()


def test_another_name_beats_a_confirms_self_label():
    c = call(["हाँ, मैं ही राजेश हूँ"], Recorder({"first_name": "confirms_self"}))
    assert c.end.outcome is Outcome.wrong_party and not c.end.speaker_confirmed


def test_a_relation_word_is_a_veto_and_the_classifier_is_not_asked():
    llm = Recorder({"first_name": "confirms_self"})
    c = call(["मैं उनकी पत्नी बोल रही हूँ"], llm)
    assert c.end.outcome is Outcome.wrong_party and llm.calls == []


def test_a_yes_label_gets_the_direct_question_then_passes():
    llm = Recorder({"first_name": "yes"})
    once = call(["हाँ जी"], llm)
    assert once.keys[-1] == "right_party.reask" and not once.state.speaker_confirmed
    twice = call(["हाँ जी", "हाँ जी"], Recorder({"first_name": "yes"}))
    assert twice.state.speaker_confirmed and twice.keys[-1] == "disclosure.go_ahead"


def test_a_hedged_claim_does_not_pass_on_confirms_self():
    c = call(["शायद मैं ही हूँ, बोलिए", "हम्म"], Recorder({"first_name": "confirms_self"}))
    assert not c.state.speaker_confirmed


def test_old_signature_interpreters_still_run_a_whole_call():
    class Old:
        def __init__(self) -> None:
            self.rules, self.seen = RuleInterpreter(), []

        def interpret(self, text, *, language, expecting, question):
            self.seen.append(expecting)
            return self.rules.interpret(text, language=language, expecting=expecting, question=question)

    old = Old()
    replies = ["हाँ जी, बोल रहा हूँ", "हाँ", "1984", "एक बीमा लिया था"]
    c = play(record(product()), HI, replies, interpreter=old)
    r = play(record(product()), HI, replies)
    assert c.keys == r.keys and c.end is None and Expecting.birth_year in old.seen


def test_the_year_never_reaches_the_classifier_and_a_loose_own_year_passes():
    llm = Recorder(SENSIBLE)
    replies = ["हाँ जी, बोल रहा हूँ", "हाँ", "मेरा जन्म 1984 में हुआ था"]
    c = play(record(product()), HI, replies, interpreter=LlmFallbackInterpreter(llm), identity=YEAR_POLICY)
    assert c.end is None and c.keys[-1] == "open_recall.ask", c.keys
    assert all("birth_year" not in call_[-1].content for call_ in llm.calls)
    assert "1984" not in llm.contents()  # never the year, not even as a previous exchange
    after = play(record(product()), HI, [*replies, "आज बहुत गर्मी है"], interpreter=LlmFallbackInterpreter(
        last := Recorder(SENSIBLE)), identity=YEAR_POLICY)  # fmt: skip
    assert after.end is None and "1984" not in last.contents() and "second_check" not in last.contents()


def test_someone_elses_year_does_not_pass():
    llm = Recorder(SENSIBLE)
    c = play(record(product()), HI, ["हाँ जी, बोल रहा हूँ", "हाँ", "इनका जन्म 1984 में हुआ था"],
             interpreter=LlmFallbackInterpreter(llm), identity=YEAR_POLICY)  # fmt: skip
    assert "open_recall.ask" not in c.keys and not c.state.check_passed
    assert all("1984" not in call_[-1].content for call_ in llm.calls)


def test_the_ordinary_path_year_reply_is_never_sent():
    llm = Recorder({"first_name": "yes"})
    c = play(record(product()), HI, ["हाँ जी", "मेरा जन्म 1984 में हुआ था"], interpreter=LlmFallbackInterpreter(llm),
             identity=YEAR_POLICY)  # fmt: skip
    assert c.state.check_passed and len(llm.calls) == 1


# --- fix round ------------------------------------------------------------------------------------------------------


def test_a_claim_then_who_is_calling_passes_on_confirms_self():
    for reply in ["हाँ मैं ही रमेश बोल रहा हूँ, आप कौन बोल रहे हो?", "haan main Ramesh hoon, kaun bol raha hai"]:
        c = call([reply], Recorder({"first_name": "confirms_self"}))
        assert c.end is None and c.state.speaker_confirmed, (reply, c.keys)


def test_only_a_whom_question_gets_the_direct_question_and_a_relation_still_ends():
    asked = call(["हाँ मैं ही हूँ, आप किससे बात करना चाहते हैं?"], Recorder({"first_name": "confirms_self"}))
    assert asked.end is None and asked.keys[-1] == "right_party.reask"
    ends = call(["मैं उनका बेटा हूँ, आप किससे बात करना चाहते हैं?"], Recorder({"first_name": "confirms_self"}))
    assert ends.end.outcome is Outcome.wrong_party


def test_name_hints_skip_ordinary_words():
    llm = Recorder({"first_name": "yes"})
    call(["जी, मैं बात कर रही हूँ"], llm)
    assert "a different first name" not in llm.calls[0][-1].content


def test_a_long_name_said_without_its_final_vowel_passes():
    c = call(["हाँ जी मैं सत्यनारायण ही हूँ"], Recorder({"first_name": "confirms_self"}), name="Satyanarayana Rao")
    assert c.state.speaker_confirmed
    from samajh.dialogue._names import NameMatch, judge_name

    assert judge_name("Amit", "Amita") is NameMatch.other and judge_name("Vijay", "Vijaya") is NameMatch.other


def test_a_chatty_own_year_passes_and_someone_elses_does_not():
    base = ["हाँ जी, बोल रहा हूँ", "हाँ"]
    ok = play(record(product()), HI, [*base, "साल? 1984 है, ये क्यों पूछ रहे हो"], identity=YEAR_POLICY,
              interpreter=LlmFallbackInterpreter(Recorder(SENSIBLE)))  # fmt: skip
    assert ok.state.check_passed and ok.keys[-1] == "open_recall.ask"
    no = play(record(product()), HI, [*base, "उनका 1984 का है"], identity=YEAR_POLICY,
              interpreter=LlmFallbackInterpreter(Recorder(SENSIBLE)))  # fmt: skip
    assert not no.state.check_passed
