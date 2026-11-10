"""P2 round 3, wave 4: the birth year in romanised Hindi number words reads as it does in Devanagari."""

from __future__ import annotations

import pytest
from dialogue_kit import play, product, record
from test_p2_round3 import interp

from samajh.amounts._lexicon import HI_NUM
from samajh.dialogue import Expecting, Outcome, RuleInterpreter
from samajh.dialogue._lexicon import _ROMAN_HI
from samajh.types import Language

HI, HE = Language.hi, Language.hi_en
OPEN = ["हाँ जी, बोल रहा हूँ", "हाँ"]
ARMS = ["rules", "raises"]  # the word lists alone, and a classifier that always fails
LANGS = [HI, HE]


def at_year(reply, dob="1984-06-15", lang=HI, arm="rules", before=()):
    return play(record(product(), dob=dob), lang, [*OPEN, *before, reply], **interp(arm))


@pytest.mark.parametrize("value", range(100))
def test_every_romanised_number_word_reads_as_its_devanagari_word(value):
    rules = RuleInterpreter()

    def year(text):
        return rules.interpret(text, language=HI, expecting=Expecting.birth_year).year

    devanagari = year(f"उन्नीस सौ {HI_NUM[value]}")
    # "एक" is also a filler word, so "उन्नीस सौ एक" reads as 1900 in either script; no borrower is 125.
    assert devanagari == (1900 if value == 1 else 1900 + value)
    for spelling in _ROMAN_HI.split()[value].split("|"):
        assert year(f"unnees sau {spelling}") == devanagari, spelling


RIGHT = [
    ("1984-06-15", "unnees sau chaurasi"), ("1984-06-15", "Unnis sau chourasi."), ("1984-06-15", "chaurasee"),
    ("1984-06-15", "chaurasi mein"), ("1984-06-15", "main chaurasi ka hoon"),
    ("1984-06-15", "Mera janm unnis sau chaurasi mein hua tha"), ("1976-01-02", "unnees sau chhihattar"),
    ("1976-01-02", "chhiyattar mein"), ("1991-11-30", "unnis sau ikyaanave"), ("1991-11-30", "ikyanbe ka hoon"),
    ("1968-03-09", "unnees sau adsath"), ("1968-03-09", "arsath mein hua tha"), ("2002-08-20", "do hazaar do"),
    ("2002-08-20", "mera janam do hajaar do mein hua"), ("1955-05-05", "pachpan ka hoon ji"),
    ("1984-06-15", "unnees sau chaurasi, pandrah june"),
]  # fmt: skip


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", [*ARMS, "sensible"])
@pytest.mark.parametrize(("dob", "reply"), RIGHT)
def test_the_right_year_in_romanised_hindi_passes(dob, reply, arm, lang):
    call = at_year(reply, dob, lang, arm)
    assert call.end is None and call.keys[-1] == "open_recall.ask", call.keys


WRONG = [
    ("1984-06-15", "unnees sau tirasi"), ("1984-06-15", "pachaasi mein"), ("1976-01-02", "unnees sau sattar"),
    ("1991-11-30", "baanave ka hoon"), ("2002-08-20", "do hazaar teen"),
]  # fmt: skip
TWO_OR_HEDGED = [
    "chaurasi ya pachaasi", "unnis sau chaurasi, nahi pachasi", "shayad chaurasi", "chaurasi hoga",
    "chaurasi, hai na?", "unnees sau chaurasi ya tirasi",
]  # fmt: skip
SOMEONE_ELSE = ["unka chaurasi hai", "papa ka janm unnis sau chaurasi mein hua tha", "unki chaurasi ki hai"]


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize(("dob", "reply"), WRONG)
def test_a_wrong_year_in_romanised_hindi_fails_at_once(dob, reply, arm, lang):
    call = at_year(reply, dob, lang, arm)
    assert call.end.outcome is Outcome.second_check_failed and len(call.utterances) == 4


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", TWO_OR_HEDGED)
def test_two_years_or_a_guess_in_romanised_hindi_end_the_check(reply, arm, lang):
    call = at_year(reply, lang=lang, arm=arm)
    assert call.end.outcome is Outcome.second_check_failed and len(call.utterances) == 4


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", SOMEONE_ELSE)
def test_a_romanised_year_about_someone_else_does_not_pass(reply, arm, lang):
    call = at_year(reply, lang=lang, arm=arm)
    assert call.end is not None and call.end.speaker_confirmed is False
    assert "open_recall.ask" not in call.keys


@pytest.mark.parametrize("arm", ARMS)
def test_no_year_gets_one_reask_then_a_romanised_year_passes(arm):
    call = at_year("unnees sau chaurasi", arm=arm, before=["yaad nahi aa raha"])
    assert call.keys.count("second_check.reask") == 1 and call.keys[-1] == "open_recall.ask"
