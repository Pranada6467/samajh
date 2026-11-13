"""A borrower saying their own first name in the other script from the record's is the same name.

The fault (2026-11-13): with the record's first name in Latin letters, "मैं ही रामप्रसाद हूँ" at the direct question was
read as another name, so the claim was doubted and the call ended `not_confirmed`, even with the classifier saying
`confirms_self`. The comparison now holds across Devanagari and Latin spellings of one name and stays strict on
consonants and written vowels: a different name, or the borrower's relative, never passes.

Builder-written typed inputs; arms: the word lists alone and a classifier that labels every turn `confirms_self`.
"""

from __future__ import annotations

import pytest
from dialogue_kit import NO_CHECK, play, product, record
from test_p2_round3 import Labels

from samajh.dialogue import Outcome
from samajh.dialogue.interpret import claim_with_tail, doubts_claim
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.types import Language

HI, HE = Language.hi, Language.hi_en

# (the record's first name in Latin, the name said in Devanagari). The first block failed before the fix.
NAMES = [
    ("Ramprasad", "रामप्रसाद"), ("Bhupendra", "भूपेंद्र"), ("Bhupendra", "भूपेन्द्र"), ("Mamta", "ममता"),
    ("Ganesh", "गणेश"), ("Kamla", "कमला"), ("Laxmi", "लक्ष्मी"), ("Krishna", "कृष्ण"), ("Krishna", "कृष्णा"),
    ("Arun", "अरुण"), ("Pranav", "प्रणव"), ("Champa", "चंपा"), ("Gyanendra", "ज्ञानेन्द्र"), ("Aditya", "आदित्य"),
    ("Rajendra", "राजेंद्र"), ("Surendra", "सुरेन्द्र"), ("Sarla", "सरला"), ("Kiran", "किरण"), ("Rajkumar", "राजकुमार"),
    ("Ramkishan", "रामकिशन"), ("Jagdish", "जगदीश"), ("Sapna", "सपना"), ("Farhan", "फ़रहान"), ("Zoya", "ज़ोया"),
    ("Ramesh", "रमेश"), ("Sameer", "समीर"), ("Meena", "मीना"), ("Suresh", "सुरेश"), ("Mahesh", "महेश"),
    ("Santosh", "संतोष"), ("Lakshmi", "लक्ष्मी"), ("Anand", "आनन्द"), ("Sanjay", "संजय"), ("Pooja", "पूजा"),
    ("Priya", "प्रिया"), ("Sunita", "सुनीता"), ("Geeta", "गीता"), ("Seema", "सीमा"), ("Usha", "उषा"),
    ("Kavita", "कविता"), ("Deepak", "दीपक"), ("Mukesh", "मुकेश"), ("Sushila", "सुशीला"), ("Shyam", "श्याम"),
    ("Siddharth", "सिद्धार्थ"), ("Pushpa", "पुष्पा"), ("Nirmala", "निर्मला"), ("Shanti", "शांति"), ("Vandana", "वंदना"),
    ("Gaurav", "गौरव"), ("Ritu", "ऋतु"), ("Manju", "मंजू"), ("Kamal", "कमल"), ("Durga", "दुर्गा"), ("Radha", "राधा"),
]  # fmt: skip
# "हाँ भाई, मैं ही <name> हूँ, क्या बात है?" is left out: an address form that is also a kin word plus a question word is
# doubted for every name in either script (`P2-report.md` §8a, the known failing pattern), not a script mismatch.
CLAIMS = ("मैं ही {} हूँ", "{} ही हूँ", "हाँ, मैं ही {} हूँ, क्या बात है?", "हाँ भाई, मैं ही {} हूँ, बोलिए")

# (the record's first name in Devanagari, the name said in Latin letters).
NAMES_LATIN_SAID = [
    ("रामप्रसाद", "Ramprasad"), ("भूपेंद्र", "Bhupendra"), ("ममता", "Mamta"), ("ममता", "Mamata"), ("गणेश", "Ganesh"),
    ("कमला", "Kamla"), ("रमेश", "Ramesh"), ("समीर", "Sameer"), ("मीना", "Meena"), ("कृष्ण", "Krishna"),
    ("लक्ष्मी", "Laxmi"), ("सुनीता", "Sunita"),
]  # fmt: skip
CLAIMS_LATIN = ("main hi {} hoon", "{} hi hoon", "haan, main hi {} hoon, kya baat hai?", "haan bhai, main hi {} hoon, boliye")

# (the record's first name, a reply that must not pass as the borrower's own claim).
OTHERS = [
    ("Ramesh", "मैं ही सुरेश हूँ"), ("Ramesh", "मैं ही राकेश हूँ"), ("Ramesh", "मैं ही राजेश हूँ"), ("Ramesh", "मैं ही महेश हूँ"),
    ("Ramesh", "मैं सुरेश हूँ"), ("Ramesh", "मैं रमेश का भाई हूँ"), ("Ramesh", "main hi Suresh hoon"),
    ("Meena", "मैं ही मीरा हूँ"), ("Meena", "मैं ही रीना हूँ"), ("Kamla", "मैं ही कमल हूँ"), ("Kamal", "मैं ही कमला हूँ"),
    ("Sunita", "मैं ही सुमिता हूँ"), ("Anil", "मैं ही सुनील हूँ"), ("Sunil", "मैं ही अनिल हूँ"), ("Mohan", "मैं ही रोहन हूँ"),
    ("Priya", "मैं ही पूजा हूँ"), ("Pooja", "मैं ही प्रिया हूँ"), ("Ram", "मैं ही रमा हूँ"), ("Shiv", "मैं ही शिवा हूँ"),
    ("Mamta", "मैं ममता की बहन हूँ"), ("Ramprasad", "मैं रामप्रसाद का बेटा हूँ"), ("Ganesh", "मैं ही गणपत हूँ"),
    ("Bhupendra", "मैं ही सुरेन्द्र हूँ"), ("Rajesh", "मैं ही रमेश हूँ"), ("रमेश", "main hi Rakesh hoon"),
]  # fmt: skip


def confirms_self() -> LlmFallbackInterpreter:
    return LlmFallbackInterpreter(Labels(lambda reply, stage: "confirms_self"))


ARMS = {"rules": lambda: None, "confirms_self": confirms_self}


def run(first_name: str, replies: list[str], arm: str):
    reader = ARMS[arm]()
    extra = {"interpreter": reader} if reader is not None else {}
    language = HE if replies[-1].isascii() else HI
    return play(record(product(), name=f"{first_name} Kalpit"), language, replies, identity=NO_CHECK, **extra)


def passed(call) -> bool:
    return call.end is None and call.state.speaker_confirmed and call.keys[-1] == "disclosure.go_ahead"


def _said(cases, forms):
    return [(name, form.format(said)) for name, said in cases for form in forms]


SAID_DEVANAGARI = _said(NAMES, CLAIMS)
SAID_LATIN = _said(NAMES_LATIN_SAID, CLAIMS_LATIN)


def _id(case) -> str:
    return f"{case[0]}:{case[1]}"


@pytest.mark.parametrize("case", SAID_DEVANAGARI + SAID_LATIN, ids=_id)
def test_the_own_name_in_the_other_script_is_a_claim_not_a_doubt(case):
    name, reply = case
    language = HE if reply.isascii() else HI
    assert not doubts_claim(reply, language, name)
    assert claim_with_tail(reply, language, name)


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("case", SAID_DEVANAGARI + SAID_LATIN, ids=_id)
def test_the_own_name_in_the_other_script_passes_at_the_direct_question(arm, case):
    name, reply = case
    call = run(name, ["हाँ जी", reply], arm)
    assert passed(call), (call.end and call.end.outcome, call.keys)


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("case", SAID_DEVANAGARI[::3] + SAID_LATIN[::3], ids=_id)
def test_the_own_name_in_the_other_script_passes_at_the_name_question(arm, case):
    name, reply = case
    call = run(name, [reply], arm)
    assert passed(call), (call.end and call.end.outcome, call.keys)


@pytest.mark.parametrize("case", OTHERS, ids=_id)
def test_another_name_or_a_relative_is_a_doubt(case):
    name, reply = case
    assert doubts_claim(reply, HE if reply.isascii() else HI, name)


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("case", OTHERS, ids=_id)
def test_another_name_or_a_relative_never_passes_at_the_direct_question(arm, case):
    name, reply = case
    call = run(name, ["हाँ जी", reply], arm)
    assert not call.state.speaker_confirmed and call.end is not None, call.keys
    assert call.end.outcome in (Outcome.wrong_party, Outcome.not_confirmed), call.end.outcome


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("case", OTHERS, ids=_id)
def test_another_name_or_a_relative_never_passes_at_the_name_question(arm, case):
    name, reply = case
    call = run(name, [reply, "हम्म"], arm)
    assert not call.state.speaker_confirmed, call.keys
    assert "disclosure.go_ahead" not in call.keys, call.keys
