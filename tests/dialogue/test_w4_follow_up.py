"""Iteration 4, W4 checkpoint 3: one follow-up for a half answer (consent: what or how; kind: what it is called)."""

from __future__ import annotations

import re

import pytest
from dialogue_kit import CUSTOMERS, play, product, record

from samajh.dialogue import LINES, Outcome, load_prompts
from samajh.dialogue.lint import lint_line
from samajh.rules.checks import _method_only
from samajh.rules.halves import method_only, missing_half
from samajh.types import ConsentMethod, DontKnow, Evidence, GapReason, Language, Stated, TurnId, Unclear

HI = Language.hi
BEFORE_CONSENT = CUSTOMERS[HI].happy()[:-1]
HOW_ONLY = ["मैंने ब्रांच में फॉर्म पर दस्तखत किए थे।", "मैंने OTP से confirm किया था।",
            "App में box tick किया और agree दबा दिया।", "बैंक की रिकॉर्डेड कॉल पर हाँ कह दी थी।"]  # fmt: skip
FOLLOW_KEYS = ("consent.follow_what", "consent.follow_how", "kind.follow_what")


def at_consent(*replies):
    return play(record(product()), HI, [*BEFORE_CONSENT, *replies])


@pytest.mark.parametrize("reply", HOW_ONLY)
def test_a_how_only_reply_gets_the_what_follow_up_once_then_closes(reply):
    asked = at_consent(reply)
    assert asked.end is None and asked.keys[-1] == "consent.follow_what"
    assert asked.utterances[-1].lines[0].asks is not None
    done = at_consent(reply, "बीमा के लिए")
    assert done.end is not None and done.end.outcome is Outcome.completed
    assert done.keys.count("consent.follow_what") == 1


def test_a_what_only_reply_gets_the_how_follow_up():
    assert at_consent("बीमा के लिए हाँ कहा था").keys[-1] == "consent.follow_how"


@pytest.mark.parametrize("reply", ["बीमा के लिए हाँ कहा था, फॉर्म पर साइन किया था", "पता नहीं", "मुझे याद नहीं"])
def test_both_halves_or_dont_know_get_no_follow_up(reply):
    keys = at_consent(reply).keys
    assert not any(key in FOLLOW_KEYS for key in keys)


def test_a_second_half_answer_gets_no_second_follow_up():
    call = at_consent("मैंने OTP से confirm किया था।", "OTP से ही किया था")
    assert call.end is not None and call.end.outcome is Outcome.completed
    assert sum(key in FOLLOW_KEYS for key in call.keys) == 1


def test_an_unusable_follow_up_reply_is_not_re_asked():
    call = at_consent("मैंने OTP से confirm किया था।", "हम्म")
    assert call.end is not None and "consent.reask" not in call.keys


@pytest.mark.parametrize("language", list(Language))
@pytest.mark.parametrize("key", FOLLOW_KEYS)
def test_every_follow_up_line_is_lint_clean_and_holds_no_record_value(language, key):
    template = load_prompts(language).templates[key]
    assert lint_line(key, template) == []
    text = load_prompts(language).render(key)
    assert not re.search(r"\d", text)
    rec = product()
    for value in ("52000", "52,000", "500000", "5,00,000", "credit", "Namoona", rec["provider"], "बावन", "पचास"):
        assert value not in text, (language, key, value)
    assert LINES[key].asks is not None


def test_the_kind_follow_up_fires_once_on_a_figure_and_not_on_a_name():
    rec = record(product())
    opening = CUSTOMERS[HI].happy()[:4]
    half = play(rec, HI, [*opening, "बावन हज़ार कटे थे बस"])
    assert half.keys[-1] == "kind.follow_what", half.keys
    again = play(rec, HI, [*opening, "बावन हज़ार कटे थे बस", "पैसे कटे थे"])
    assert again.keys.count("kind.follow_what") == 1 and again.end is None
    named = play(rec, HI, [*opening, "वो बीमा था"])
    assert "kind.follow_what" not in named.keys


def test_tamil_gets_no_follow_up():
    ta = CUSTOMERS[Language.ta]
    call = play(record(product()), Language.ta, ta.happy())
    assert not any(key in FOLLOW_KEYS for key in call.keys)


def test_method_only_agrees_with_the_rules_predicate():
    ev, other = Evidence(quote="OTP से", turn_id=TurnId(9)), Evidence(quote="बीमा", turn_id=TurnId(7))
    method = Stated[ConsentMethod](value=ConsentMethod.otp, evidence=ev)
    cases = [
        (Unclear(evidence=ev), method),
        (Unclear(), method),
        (Unclear(evidence=other), method),
        (Unclear(reason=GapReason.extraction_failed), method),
        (DontKnow(evidence=ev), method),
        (Stated[bool](value=True, evidence=ev), method),
        (Unclear(evidence=ev), Unclear(evidence=ev)),
    ]
    for given, how in cases:
        assert method_only(given, how) == _method_only(given, how)
    assert missing_half(Unclear(evidence=ev), method) == "what"
    assert missing_half(Stated[bool](value=True, evidence=ev), Unclear(evidence=ev)) == "how"


def test_one_is_no_figure_and_what_it_does_is_a_kind_half():
    assert at_consent("मैंने एक बार OTP डाला था बस").keys[-1] == "consent.follow_what"
    opening = CUSTOMERS[HI].happy()[:4]
    rec = record(product())
    assert play(rec, HI, [*opening, "कुछ हुआ तो लोन चुका देगा"]).keys[-1] == "kind.follow_what"
    assert "kind.follow_what" not in play(rec, HI, [*opening, "बीमा था, कुछ हुआ तो लोन चुका देगा"]).keys
    assert "kind.follow_what" not in play(rec, HI, [*opening, "बीमार पड़े तो काम आएगा, ऐसा बीमा"]).keys
