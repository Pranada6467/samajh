"""P2 round 3, wave 5: a right birth year with a harmless extra word passes; a yes that asks to keep the
call short is a go-ahead. Word lists alone and a failing classifier."""

from __future__ import annotations

import pytest
from dialogue_kit import play, product, record
from test_p2_round3 import interp

from samajh.dialogue import Outcome
from samajh.types import Language

HI, HE = Language.hi, Language.hi_en
IDENTITY = "हाँ जी, बोल रहा हूँ"
ARMS = ["rules", "raises"]
LANGS = [HI, HE]


def call(replies, lang, arm):
    return play(record(product(), dob="1984-06-15"), lang, [IDENTITY, *replies], **interp(arm))


def at_year(replies, lang, arm):
    return call(["हाँ", *replies], lang, arm)


PASS = [
    "उन्नीस सौ चौरासी, और क्या", "अरे उन्नीस सौ चौरासी", "चौरासी वाला साल", "arre yaar, nineteen eighty four",
    "उन्नीस सौ चौरासी भाई", "हाँ जी, चौरासी", "born in eighty four yaar", "चौरासी ही है",
]  # fmt: skip


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", PASS)
def test_the_right_year_with_a_harmless_extra_word_passes_first_time(reply, arm, lang):
    c = at_year([reply], lang, arm)
    assert c.end is None and c.keys[-1] == "open_recall.ask", c.keys
    assert c.state.speaker_confirmed


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", ["उन्नीस सौ उन्यासी", "अरे उन्नीस सौ उन्यासी", "eighty six"])
def test_a_wrong_year_fails_at_once(reply, arm, lang):
    c = at_year([reply], lang, arm)
    assert c.end.outcome is Outcome.second_check_failed and "second_check.reask" not in c.keys
    assert not c.end.speaker_confirmed


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", ["1984 ya 85", "1984 है ना? सही है?", "शायद चौरासी"])
def test_two_years_or_a_guess_end_the_check_without_passing(reply, arm, lang):
    c = at_year([reply], lang, arm)
    assert c.end is not None and c.end.outcome is Outcome.second_check_failed
    assert not c.end.speaker_confirmed


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
def test_a_relation_born_that_year_is_the_wrong_party(arm, lang):
    c = at_year(["पापा 1984 में पैदा हुए थे"], lang, arm)
    assert c.end.outcome is Outcome.wrong_party


SOMEONE_ELSE = [
    "उनका जन्म उन्नीस सौ चौरासी में हुआ था", "unka birth year nineteen eighty four hai", "रमेश का चौरासी है",
    "भैया का तो चौरासी है",
]  # fmt: skip


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", SOMEONE_ELSE)
def test_the_right_year_said_of_someone_else_does_not_pass(reply, arm, lang):
    for replies in ([reply], [reply, reply]):
        c = at_year(replies, lang, arm)
        assert "open_recall.ask" not in c.keys and not c.state.speaker_confirmed, c.keys
    assert c.end is not None and c.end.outcome in (Outcome.wrong_party, Outcome.second_check_failed)


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", ["एक बार फिर बोलिए", "साल? याद नहीं अभी"])
def test_a_reply_with_no_year_is_asked_once_more(reply, arm, lang):
    c = at_year([reply], lang, arm)
    assert c.end is None and c.keys[-1] == "second_check.reask", c.keys
    assert at_year([reply, reply], lang, arm).end.outcome is Outcome.second_check_failed


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", ["हाँ, पर ज़्यादा लंबा मत करना", "haan, zyada lamba mat karna"])
def test_a_yes_that_asks_to_keep_it_short_goes_ahead(reply, arm, lang):
    c = call([reply], lang, arm)
    assert c.end is None and c.keys[-1] == "second_check.ask", c.keys


# Recorded before wave 5 in both arms and both languages: re-asked, then ended the same way.
UNCHANGED = [
    ("हाँ, पर अभी नहीं", None, Outcome.no_go_ahead),
    ("हाँ पर अभी टाइम नहीं है", None, Outcome.no_go_ahead),
    ("नहीं, मत बोलिए", None, Outcome.no_go_ahead),
    ("फ़ोन मत करना", Outcome.do_not_call, Outcome.do_not_call),
    ("haan but abhi nahi, baad mein", None, Outcome.no_go_ahead),
    ("बंद मत कीजिए, बोलिए", None, Outcome.no_go_ahead),
    ("phone mat kaatna, haan pucho", None, Outcome.no_go_ahead),
    ("हाँ, लंबा मत खींचना, पर अभी नहीं", None, Outcome.no_go_ahead),
]  # fmt: skip


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize(("reply", "first", "second"), UNCHANGED)
def test_other_negatives_at_the_go_ahead_read_as_before(reply, first, second, arm, lang):
    once = call([reply], lang, arm)
    assert (once.end.outcome if once.end else None) is first
    if first is None:
        assert once.keys[-1] == "disclosure.reask"
        assert call([reply, reply], lang, arm).end.outcome is second


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
def test_a_yes_with_a_hurry_still_goes_ahead(arm, lang):
    c = call(["हाँ पर जल्दी करिए, दुकान पे हूँ"], lang, arm)
    assert c.end is None and c.keys[-1] == "second_check.ask"


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
def test_ones_own_year_said_with_apna_passes(arm, lang):
    c = at_year(["जी अपना तो 1984 का है"], lang, arm)  # was a re-ask before wave 5
    assert c.end is None and c.keys[-1] == "open_recall.ask", c.keys


# Wave 5 fix 2: the right year said with a leading "ya", as a numeric date, with "तारीख" or with the
# speaker's own whereabouts passes first time; a guess word ends the check; a wrong year still fails.
FIX2_PASS = [
    "Ya, 1984.", "Mera DOB 15-06-1984 hai.", "15/06/84", "मेरी डेट ऑफ़ बर्थ 15-06-1984 है",
    "मेरा जन्म पंद्रह तारीख़ जून चौरासी को हुआ।", "Nineteen eighty four, main abhi office mein hoon toh jaldi kijiye.",
]  # fmt: skip


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", FIX2_PASS)
def test_fix2_the_right_year_in_these_forms_passes_first_time(reply, arm, lang):
    c = at_year([reply], lang, arm)
    assert c.end is None and c.keys[-1] == "open_recall.ask", c.keys
    assert c.state.speaker_confirmed


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", ["Ya, 1986.", "Mera DOB 15-06-1986 hai.", "15/06/86", "उन्नीस सौ उन्यासी"])
def test_fix2_a_wrong_year_in_these_forms_fails_at_once(reply, arm, lang):
    c = at_year([reply], lang, arm)
    assert c.end.outcome is Outcome.second_check_failed and "second_check.reask" not in c.keys


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", ["अंदाज़े से चौरासी।", "andaze se chaurasi", "अंदाज़न चौरासी", "चौरासी या पचासी", "1984 ya 85"])
def test_fix2_a_guess_or_an_or_ends_the_check(reply, arm, lang):
    c = at_year([reply], lang, arm)
    assert c.end is not None and c.end.outcome is Outcome.second_check_failed
    assert not c.end.speaker_confirmed


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", ["वो office में हैं, 1984", "Ramesh office mein hai"])
def test_fix2_someone_else_at_the_office_never_passes(reply, arm, lang):
    c = at_year([reply], lang, arm)
    assert c.end is not None and not c.end.speaker_confirmed
