"""Iteration 3: what the round 4 verification left open (verify-P2-r4.md) and product review gains 7 and 8.

(a) refusals at the opening by class; a borrower who is away is never logged as refusing. (b) the who-check
after a takeover sign is a choice question that a bare yes does not answer. (e) the neutral acknowledgement
by position and the named kind question. Builder-written inputs (Hindi and Hinglish, romanised too), typed
text; none is taken from a verifier's input file.
"""

from __future__ import annotations

import pytest
from dialogue_kit import CUSTOMERS, LENDER, NO_CHECK, YEAR_POLICY, play, product, record
from test_p2_round3 import Labels

from samajh.clients.errors import TransportError
from samajh.dialogue import PRODUCT_QUESTIONS, Outcome, load_prompts
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.types import Language

HI, HE = Language.hi, Language.hi_en
LEAK = ("लोन", "loan", "बीमा", "insurance", "प्रीमियम", "premium", LENDER)


def raises() -> LlmFallbackInterpreter:
    return LlmFallbackInterpreter(Labels(error=TransportError("down")))


def labelled(label: str) -> LlmFallbackInterpreter:
    return LlmFallbackInterpreter(Labels(lambda reply, stage: label))


ARMS = {"rules": lambda: None, "raises": raises}


def lang_of(text: str) -> Language:
    return HE if text.isascii() else HI


def run(replies, identity=YEAR_POLICY, reader=None, language=None, rec=None):
    extra = {"interpreter": reader} if reader is not None else {}
    language = language or lang_of(replies[-1])
    return play(rec or record(product()), language, replies, identity=identity, **extra)


class Then:
    """The word lists for the first `setup` turns, then `reader`."""

    def __init__(self, setup: int, reader):
        from dialogue_kit import RULES

        self.left, self.reader, self.rules = setup, reader, RULES

    def interpret(self, text, **kw):
        if self.left > 0:
            self.left -= 1
            return self.rules.interpret(text, **kw)
        return self.reader.interpret(text, **kw)


# --- (a) refusals at the opening ---------------------------------------------------------------------------

FIRST_PERSON_REFUSALS = [
    "नहीं भाई, मुझे इंटरेस्ट नहीं है", "मैं ऐसे फोन पर बात नहीं करती", "हम फोन पे बात नहीं करते जी",
    "मुझे कुछ नहीं चाहिए", "नहीं चाहिए, धन्यवाद", "सर, मैं इंटरेस्टेड नहीं हूँ", "भैया हमें नहीं चाहिए कुछ",
    "दीदी, मैं ऐसी बातें नहीं करती फोन पर", "nahi yaar, interested nahi hu", "main aise calls pe baat nahi karta",
    "mujhe kuch nahi chahiye bhai", "sir not interested hoon", "hum phone pe baat nahi karte", "bhaiya hume nahi chahiye",
]  # fmt: skip
SOMEONE_AWAY = [
    "रमेश जी घर पर नहीं हैं, फोन मत करो", "वो नहीं हैं, बात नहीं करनी", "रमेश यहाँ नहीं रहते, दोबारा कॉल मत करना",
    "रमेश जी अभी नहीं हैं, बाद में करना", "Ramesh ji nahi hain, baad mein bhi phone mat karna",
    "unko nahi chahiye, phone mat karna", "Ramesh bahar gaye hain, mat karo call", "Ramesh nahi hai, unhe interest nahi hai",
]  # fmt: skip
ADDRESS_THEN_BUSY = ["bhai abhi busy hoon, baad mein karna", "सर, अभी फ्री नहीं हूँ", "yaar abhi free nahi hu, kal karna",
                     "भाई साहब, अभी गाड़ी चला रहा हूँ"]  # fmt: skip
OPENINGS = {"name": [], "reask": ["हेलो?"]}


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("policy", [NO_CHECK, YEAR_POLICY], ids=["none", "year"])
@pytest.mark.parametrize("opening", OPENINGS)
@pytest.mark.parametrize("reply", FIRST_PERSON_REFUSALS)
def test_a_first_person_refusal_at_the_opening_is_declined(arm, policy, opening, reply):
    call = run([*OPENINGS[opening], reply], policy, ARMS[arm]())
    assert call.end.outcome is Outcome.declined, call.keys
    assert call.end.speaker_confirmed is False and not any(word in call.end.utterance.text for word in LEAK)


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("policy", [NO_CHECK, YEAR_POLICY], ids=["none", "year"])
@pytest.mark.parametrize("opening", OPENINGS)
@pytest.mark.parametrize("reply", SOMEONE_AWAY)
def test_a_reply_that_the_borrower_is_away_is_never_declined(arm, policy, opening, reply):
    call = run([*OPENINGS[opening], reply], policy, ARMS[arm]())
    assert call.end.outcome is Outcome.wrong_party, call.keys
    assert call.end.speaker_confirmed is False and call.keys[-1] == "end.third_party"


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", ADDRESS_THEN_BUSY)
def test_an_address_form_before_a_busy_predicate_is_not_a_relation(arm, reply):
    assert run([reply], NO_CHECK, ARMS[arm]()).end.outcome is Outcome.call_back_later


@pytest.mark.parametrize("reply, outcome", [
    ("नहीं", Outcome.wrong_party), ("नहीं, मैं रमेश नहीं हूँ", Outcome.wrong_party), ("मैं उनका भाई हूँ", Outcome.wrong_party),
    ("bhai hoon unka", Outcome.wrong_party), ("मैं उनकी वाइफ हूँ, उनको नहीं चाहिए", Outcome.wrong_party),
])  # fmt: skip
def test_a_relation_claim_still_ends_as_wrong_party(reply, outcome):
    assert run([reply], NO_CHECK).end.outcome is outcome


@pytest.mark.parametrize("reply", ["मुझे नहीं चाहिए", "interested nahi hoon", "मैं ऐसी कॉल पे बात नहीं करता"])
def test_the_same_refusal_at_a_stop_check_ends_the_call(reply):
    call = run(["हाँ जी", "1984", "हाँ", "एक बीमा लिया था", "रहने दो", reply])
    assert call.end.outcome is Outcome.declined, call.keys


@pytest.mark.parametrize("reply", ["मुझे ये नहीं चाहिए था, फिर भी डाल दिया", "फ्री नहीं था, पैसे कटे"])
def test_after_the_loan_is_named_the_same_words_are_an_account(reply):
    call = run(["हाँ जी", "1984", "हाँ", "एक बीमा लिया था", "बीमा है", reply])
    assert call.end is None, call.keys


# --- (b) the who-check after a takeover sign ------------------------------------------------------------------

AT_KIND = ["हाँ जी", "1984", "हाँ", "एक बीमा लिया था"]
TAKEOVERS = ["मैं उनका भाई बोल रहा हूँ", "hello, main unki beti hoon, papa bahar gaye", "रुकिए, अब मैं बात कर रहा हूँ"]
SELF_CLAIMS = ["मैं ही बोल रहा हूँ", "हाँ जी, मैं ख़ुद", "मैं Ramesh", "रमेश बोल रहा हूँ", "main hi hoon", "haan khud bol raha hoon",
               "speaking", "नहीं नहीं, मैं ही हूँ"]  # fmt: skip
NOT_CLAIMS = ["हाँ", "जी", "हाँ जी", "ठीक है", "हाँ बोलिए", "haan ji", "shayad", "कोई और", "उनकी जगह मैं",
              "मैं उनका भाई", "पता नहीं", "हम्म", "सुरेश बोल रहा हूँ", "आप कौन?"]  # fmt: skip


def at_who_check(takeover: str, tail: list[str], reader=None):
    replies = [*AT_KIND, takeover, *tail]
    reader = Then(len(AT_KIND), reader) if reader is not None else None
    return run(replies, YEAR_POLICY, reader, language=lang_of(takeover) if not tail else lang_of(tail[-1]))


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("takeover", TAKEOVERS)
def test_the_who_check_is_the_choice_question_and_names_nothing(arm, takeover):
    call = at_who_check(takeover, [], ARMS[arm]())
    assert call.end is None and call.keys[-1] == "right_party.who_check", call.keys
    text = call.utterances[-1].text
    assert "कोई और" in text and not any(word in text for word in LEAK)


@pytest.mark.parametrize("arm", [*ARMS, "confirms_self", "yes"])
@pytest.mark.parametrize("reply", SELF_CLAIMS)
def test_only_an_explicit_self_claim_resumes(arm, reply):
    reader = labelled(arm) if arm in ("confirms_self", "yes") else ARMS[arm]()
    call = at_who_check(TAKEOVERS[0], [reply], reader)
    assert call.end is None and call.keys[-1].startswith("kind."), call.keys


@pytest.mark.parametrize("arm", [*ARMS, "confirms_self", "yes", "answer"])
@pytest.mark.parametrize("reply", NOT_CLAIMS)
def test_a_bare_yes_a_hedge_or_anything_else_ends_as_wrong_party_with_no_re_ask(arm, reply):
    reader = labelled(arm) if arm in ("confirms_self", "yes", "answer") else ARMS[arm]()
    call = at_who_check(TAKEOVERS[0], [reply], reader)
    assert call.end.outcome is Outcome.wrong_party, call.keys
    assert call.end.speaker_confirmed is False and call.keys.count("right_party.who_check") == 1
    assert call.keys[-1] == "end.third_party" and not any(word in call.end.utterance.text for word in LEAK)


@pytest.mark.parametrize("reply, outcome", [
    ("मुझे बात नहीं करनी", Outcome.declined), ("किसी इंसान से बात कराइए", Outcome.human_requested),
    ("दोबारा कॉल मत करना", Outcome.do_not_call), ("बाद में कॉल करना", Outcome.call_back_later),
])  # fmt: skip
def test_a_stop_request_at_the_who_check_ends_as_asked(reply, outcome):
    assert at_who_check(TAKEOVERS[0], [reply]).end.outcome is outcome


def test_the_opening_keeps_a_yes_to_the_direct_question_with_no_second_check():
    # The stricter rule is only for the who-check after a takeover sign.
    call = run(["हाँ जी", "हाँ"], NO_CHECK)
    assert call.end is None and call.keys[-1] == "disclosure.go_ahead"


def test_a_genuine_borrower_who_mentions_a_relative_pays_one_question_and_must_say_it_is_them():
    mention = "मेरे बेटे ने फॉर्म भरा था, बीमा था कुछ"
    asked = run([*AT_KIND[:3], mention])
    assert asked.keys[-1] == "right_party.who_check"
    assert run([*AT_KIND[:3], mention, "जी, मैं ही बोल रहा हूँ"]).end is None
    assert run([*AT_KIND[:3], mention, "हाँ जी"]).end.outcome is Outcome.wrong_party  # the measured cost


# --- (e) the neutral acknowledgement and the named kind question ---------------------------------------------


def _happy(language: Language, recall: str | None = None, answers=None):
    customer = CUSTOMERS[language]
    replies = customer.happy()
    if recall is not None:
        replies[3] = recall
    if answers is not None:
        replies[4 : 4 + len(answers)] = answers
    return play(record(product()), language, replies, identity=YEAR_POLICY)


@pytest.mark.parametrize("language", [HI, HE])
def test_the_acknowledgement_comes_before_every_second_teach_back_question_by_position(language):
    call = _happy(language)
    keys = call.keys
    for k, key in enumerate(keys):
        if key == "ack.neutral":
            following = keys[k + 1]
            question = following.rsplit(".", 1)[0]
            assert question in {q.value for q in PRODUCT_QUESTIONS}, following
            assert PRODUCT_QUESTIONS.index(next(q for q in PRODUCT_QUESTIONS if q.value == question)) % 2 == 1
            assert following.endswith(".ask")
    asked_odd = [q.value for q in PRODUCT_QUESTIONS[1::2]]
    assert keys.count("ack.neutral") == len(asked_odd) - 0  # premium, payment_frequency, provider_choice, ...
    assert all(text == "जी।" for text in (line.text for line in call.lines if line.key == "ack.neutral"))


def test_the_acknowledgement_does_not_depend_on_what_the_customer_said():
    customer = CUSTOMERS[HI]
    other = ["पता नहीं", "बावन हज़ार", "याद नहीं", "पता नहीं", "पता नहीं", "पता नहीं", "पता नहीं", "पता नहीं", "पता नहीं",
             "पता नहीं"]  # fmt: skip
    first = _happy(HI)
    second = _happy(HI, answers=other[:1] + list(customer.answers[1:2]))

    def where(call):
        return [call.keys[k + 1] for k, key in enumerate(call.keys) if key == "ack.neutral"]

    assert where(first) == where(second)


def test_the_acknowledgement_is_never_before_a_stop_check_a_who_check_a_read_back_a_re_ask_or_an_end():
    calls = [
        _happy(HI),
        run([*AT_KIND, "बीमा है", "हम्म", "हम्म", "हम्म"]),
        run([*AT_KIND, "बीमा है", "रहने दो"]),
        run([*AT_KIND, "बीमा है", "मैं उनका भाई बोल रहा हूँ"]),
        run([*AT_KIND, "बीमा है", "बावन हज़ार"]),
    ]
    for call in calls:
        for k, key in enumerate(call.keys):
            if key == "ack.neutral":
                after = call.keys[k + 1]
                assert after.endswith(".ask") and not after.startswith(("stop_check", "right_party", "read_back",
                                                                           "end.", "close.", "bridge"))  # fmt: skip
        for utterance in call.utterances:
            keys = [line.key for line in utterance.lines]
            assert keys[-1] != "ack.neutral"


def test_no_acknowledgement_in_tamil_and_kannada():
    for language in (Language.ta, Language.kn):
        assert "ack.neutral" not in _happy(language).keys


@pytest.mark.parametrize("language", [HI, HE])
def test_the_named_kind_question_follows_a_recall_that_named_something(language):
    named = _happy(language)
    assert "kind.ask_named" in named.keys and "kind.ask" not in named.keys
    affirmed = _happy(language, recall="हाँ, था कुछ" if language is HI else "haan, tha kuch")
    assert "kind.ask" in affirmed.keys and "kind.ask_named" not in affirmed.keys


@pytest.mark.parametrize("recall", ["एक बीमा लिया था", "हाँ एफडी करवाई थी", "बावन हज़ार कटे थे"])
def test_the_named_kind_question_never_echoes_the_customer_or_the_record(recall):
    call = _happy(HI, recall=recall)
    line = next(line for line in call.lines if line.key == "kind.ask_named")
    assert line.text == load_prompts(HI).templates["kind.ask_named"]
    for word in ("बीमा", "एफडी", "बावन", "credit", "क्रेडिट"):
        assert word not in line.text
