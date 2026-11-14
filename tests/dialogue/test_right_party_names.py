"""The right-party check and the borrower's name (iteration 4): behaviour in played calls, no second check.

A genuine borrower who says their own name in the other script or spelling passes; a speaker who names someone else
never hears the lender or the loan. Two arms: the word lists alone, and a classifier that labels every turn
`confirms_self` (the label that used to be overruled by `doubts_claim`). Builder-written inputs; the measured rates on
a held-out set written by the independent checker are in `references/pilots/iter4-W1-names-report.md`.
"""

from __future__ import annotations

import re

import pytest
from dialogue_kit import NO_CHECK, play, product, record
from test_p2_round3 import Labels

from samajh.dialogue import Outcome
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.types import Language

HI, HE = Language.hi, Language.hi_en
ARMS = ("rules", "confirms_self")
NAMED = re.compile(r"Udaharan|लोन|loan|बीमा|policy|premium|प्रीमियम|कवर|cover", re.IGNORECASE)


def run(first_name: str, replies: list[str], arm: str, language: Language = HI):
    extra = {"interpreter": LlmFallbackInterpreter(Labels(lambda reply, stage: "confirms_self"))} if arm != "rules" else {}
    return play(record(product(), name=f"{first_name} Kalpit"), language, replies, identity=NO_CHECK, **extra)


def named_to(call) -> bool:
    """Did any bot line after the first one name the lender or the loan?"""
    return any(NAMED.search(line.text) for line in call.lines[1:])


# The review's failing names (iteration 4 review §3 item 1) and the P5b and P5 replies of `eval/p5/REPORT.md` §9-10.
GENUINE = [
    ("Kavitha", ["हाँ, मैं ही कविता हूँ"]),
    ("Shiva", ["हाँ, मैं ही शिव हूँ"]),
    ("Surinder", ["जी, सुरेन्द्र बोल रहा हूँ"]),
    ("Mahender", ["हाँ, मैं ही महेंद्र हूँ"]),
    ("Pinky", ["हाँ जी, मैं पिंकी बोल रही हूँ"]),
    ("Mamta", ["हाँ", "जी हाँ, मैं ही ममता हूँ, बताइए।"]),
    ("Balram", ["हाँ", "जी हाँ, मैं ही बलराम हूँ।"]),
    ("Rukhsana", ["हाँ", "हाँ, मैं ही रुखसाना हूँ।"]),
    ("Omprakash", ["हाँ", "जी हाँ, मैं ही ओमप्रकाश हूँ।"]),
    ("Kunal", ["हाँ", "हाँ, मैं ही कुणाल हूँ।"]),
    ("Ramprasad", ["हाँ, मैं रामप्रसाद बोल रहा हूँ।", "जी हाँ, मैं ही रामप्रसाद हूँ।"]),
    ("Bhupendra", ["हाँ, भूपेंद्र बोल रहा हूँ। कौन?", "हाँ भाई, मैं ही भूपेंद्र हूँ।"]),
]


@pytest.mark.parametrize("arm", ARMS)
def test_a_genuine_borrower_saying_their_own_name_passes(arm):
    failed = []
    for name, replies in GENUINE:
        call = run(name, replies, arm)
        if not call.state.check_passed:
            failed.append((name, call.end and call.end.outcome, call.keys))
    assert failed == []


@pytest.mark.parametrize("arm", ARMS)
def test_hinglish_spelling_variants_of_the_name_pass(arm):
    for name, reply in [("Kavitha", "haan main hi Kavita hoon"), ("Surinder", "ji, Surender bol raha hoon"),
                        ("Pinky", "haan main Pinki bol rahi hoon")]:  # fmt: skip
        call = run(name, [reply], arm, HE)
        assert call.state.check_passed, (name, reply, call.keys)


# A speaker who names someone else: another name (near misses included), a relative with a name, a male/female pair.
OTHERS = [
    ("Ramesh", "मैं उनकी पत्नी सुनीता हूँ"),
    ("Ramesh", "नहीं, मैं राजेश बोल रहा हूँ"),
    ("Ramesh", "हाँ, मैं ही राजेश हूँ"),
    ("Ramesh", "जी, राकेश बोल रहा हूँ"),
    ("Ramesh", "मैं सुरेश हूँ"),
    ("Sunita", "हाँ जी, सुनील बोल रहा हूँ"),
    ("Meena", "हाँ, मैं मीनल बोल रही हूँ"),
    ("Amit", "हाँ, मैं ही अमिता हूँ"),
    ("Kamal", "हाँ, मैं ही कमला हूँ"),
    ("Ramesh", "haan main Rajesh bol raha hoon"),
]


@pytest.mark.parametrize("arm", ARMS)
def test_a_speaker_who_names_someone_else_never_hears_the_loan(arm):
    leaked = []
    for name, reply in OTHERS:
        call = run(name, [reply, "हाँ", "हाँ जी"], arm, HE if reply.isascii() else HI)
        if call.state.check_passed or named_to(call):
            leaked.append((name, reply, call.keys))
    assert leaked == []


@pytest.mark.parametrize("arm", ARMS)
def test_another_name_at_the_name_question_ends_the_call_at_once(arm):
    call = run("Ramesh", ["हाँ, मैं ही राजेश हूँ"], arm)
    assert call.end is not None and call.end.outcome is Outcome.wrong_party
    assert not call.state.speaker_confirmed


def test_a_common_word_in_a_claim_frame_is_not_another_name():
    for reply in ("हाँ, पर मैं अभी बिज़ी हूँ", "मैं फ्री हूँ, बोलिए", "हाँ, मैं ठीक हूँ"):
        call = run("Ramesh", [reply], "rules")
        assert call.end is None or call.end.outcome is not Outcome.wrong_party, (reply, call.end and call.end.outcome)


def test_the_borrower_with_a_surname_passes():
    call = run("Kavitha", ["हाँ, मैं कविता शर्मा बोल रही हूँ"], "rules")
    assert call.state.check_passed, call.keys


# Fix round after the independent check (`references/reviews/iter4/verify-W1-names.md`): its failing classes, written
# here as fresh builder inputs, not copied from its set.
@pytest.mark.parametrize("arm", ARMS)
def test_a_compound_name_said_in_two_words_passes_and_one_part_alone_is_someone_else(arm):
    for name, reply in [("Lakshminarayan", "haan ji, Laxmi Narayan bol raha hoon"),
                        ("Shivashankar", "हाँ, मैं ही शिव शंकर हूँ")]:  # fmt: skip
        call = run(name, [reply], arm, HE if reply.isascii() else HI)
        assert call.state.check_passed, (name, reply, call.keys)
    for name, reply in [("Lakshminarayan", "हाँ जी, मैं लक्ष्मी बोल रही हूँ"), ("Shivashankar", "जी, शंकर बोल रहा हूँ")]:
        call = run(name, [reply, "हाँ"], arm)
        assert call.end is not None and call.end.outcome is Outcome.wrong_party, (name, reply, call.keys)


@pytest.mark.parametrize("arm", ARMS)
def test_spelling_conventions_of_one_name_pass_in_either_script_and_frame(arm):
    for name, spoken in [("Jothi", "ज्योति"), ("Jothi", "Jyothi"), ("Dnyaneshwar", "ज्ञानेश्वर"), ("Mary", "मैरी"),
                         ("Francis", "फ्रांसिस"), ("Ayesha", "Aisha"), ("Balasubramanian", "बालसुब्रमण्यम")]:  # fmt: skip
        language = HE if spoken.isascii() else HI
        for frame in ("हाँ जी, {} बोल रही हूँ", "मैं ही {} हूँ", "मैं {} हूँ"):
            call = run(name, [frame.format(spoken), "हाँ जी"], arm, language)
            assert call.state.check_passed, (name, frame.format(spoken), call.keys)


@pytest.mark.parametrize("arm", ARMS)
def test_a_bare_other_name_at_the_direct_question_ends_the_call(arm):
    call = run("Rajesh", ["हाँ जी", "राजू"], arm)
    assert call.end is not None and call.end.outcome is Outcome.wrong_party, call.keys
    assert not named_to(call)
