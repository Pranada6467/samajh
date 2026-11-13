"""Iteration 3, round 2: three fixes after a voiced call and verify-call.md part 2.

1. An explicit first-person claim with a tail (a question, a go-on word, chatter, an account that someone else had the
   phone) passes at the opening and at the who-check, unless the reply puts someone else in the speaker's place.
2. "mera no. hata do bhai" at the opening: a removal request with an address form is a do-not-call, not a relative.
3. At the go-ahead, an echo of the bot's time phrase or a short delay ("15 minute baad") gets one re-ask, not an end.

Builder-written typed inputs, Hindi and Hinglish (Devanagari and romanised), men and women borrowers; none taken from
the verifier's probe files. Arms: the word lists alone, a classifier that raises, and fixed labels.
"""

from __future__ import annotations

import pytest
from dialogue_kit import NO_CHECK, YEAR_POLICY, play, product, record
from test_p2_round3 import Labels

from samajh.clients.errors import TransportError
from samajh.dialogue import Outcome, load_prompts
from samajh.dialogue.interpret import claim_with_tail, short_delay_or_echo
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.types import Language

HI, HE = Language.hi, Language.hi_en
MEN, WOMAN = "Sameer Kalpit", "Sunita Udaharan"
LENDER_WORDS = ("Udaharan Bank", "लोन", "loan")
NAMING = ("disclosure.who", "disclosure.reask", "verify.after_loan", "context.loan", "open_recall", "kind.",
          "read_back", "close.verify")  # fmt: skip


def labelled(label: str) -> LlmFallbackInterpreter:
    return LlmFallbackInterpreter(Labels(lambda reply, stage: label))


def raises() -> LlmFallbackInterpreter:
    return LlmFallbackInterpreter(Labels(error=TransportError("down")))


ARMS = {"rules": lambda: None, "raises": raises}


def arms_with(*labels: str) -> dict:
    return {**ARMS, **{label: (lambda label=label: labelled(label)) for label in labels}}


def run(replies, factory, name=MEN, identity=NO_CHECK):
    reader = factory()
    extra = {"interpreter": reader} if reader is not None else {}
    language = HE if replies[-1].isascii() else HI
    return play(record(product(), name=name), language, replies, identity=identity, **extra)


def keys_after(call, turns: int) -> list[str]:
    return [line.key for utterance in call.utterances[turns + 1 :] for line in utterance.lines]


def names_nothing(keys) -> bool:
    return not any(key.startswith(NAMING) for key in keys)


# --- 1. claims with a tail ---------------------------------------------------------------------------------------

# (borrower, reply): each holds an explicit first-person claim and a tail outside the old closed vocabulary.
CLAIMS = [
    (MEN, "हां भाई, मैं ही समीर हूँ. क्या issue है?"),
    (MEN, "main Sameer hoon, kya baat hai?"),
    (MEN, "समीर बोल रहा हूँ, बताइए किस बारे में"),
    (MEN, "jee main hi hoon Sameer, bolo kya kaam hai"),
    (MEN, "हाँ हाँ मैं समीर ही हूँ, आप कहाँ से बोल रहे हैं?"),
    (MEN, "I am Sameer, tell me what this is"),
    (MEN, "अरे मैं ही हूँ यार, बोलो जल्दी क्या हुआ"),
    (MEN, "हाँ सर, मैं समीर, क्या हुआ?"),
    (WOMAN, "जी, मैं सुनीता बोल रही हूँ, क्या बात है?"),
    (WOMAN, "main Sunita hoon madam, bataiye kya hua"),
    (WOMAN, "हाँ दीदी, मैं ही बात कर रही हूँ, पूछिए जो पूछना है"),
    (WOMAN, "Sunita here, go on, what is it"),
]
# A claim beside a past-tense account that someone else had the phone (mostly a who-check reply).
ACCOUNTS = [
    (MEN, "माफ़ कीजिए, बच्चे ने फ़ोन ले लिया था, मैं समीर ही बोल रहा हूँ"),
    (MEN, "biwi ne phone utha liya tha, main Sameer hoon, aage boliye"),
    (MEN, "मेरी पत्नी ने फ़ोन उठा लिया था, मैं समीर हूँ, बोलिए"),
    (WOMAN, "माफ़ कीजिए, पति के पास फ़ोन था, मैं सुनीता ही बोल रही हूँ"),
    (WOMAN, "haan main hi hoon, beti ne phone utha liya tha, ab poochiye"),
    (WOMAN, "मैं ही हूँ जी, बेटे के हाथ में फ़ोन था, अब बताइए क्या पूछ रहे थे"),
]
# Replies that look like a claim but put someone else in the speaker's place, hedge, deny, or ask whom the caller wants.
NOT_CLAIMS = [
    (MEN, "मैं उनका भाई हूँ, बताइए"),
    (MEN, "मैं समीर का भाई हूँ, क्या बात है"),
    (MEN, "मैं सुरेश बोल रहा हूँ, क्या काम है"),
    (MEN, "main Suresh hoon, kya kaam hai"),
    (MEN, "मैं ही हूँ, आप किससे बात करना चाहते हैं?"),
    (MEN, "शायद मैं ही हूँ, बोलिए"),
    (MEN, "मान लीजिए मैं ही समीर हूँ"),
    (MEN, "समीर बाहर गए हैं, मैं बोल रहा हूँ"),
    (MEN, "मैं ही बोल रहा हूँ, समीर सो रहे हैं"),
    (MEN, "main Sameer ki wife hoon, boliye"),
    (MEN, "मैं बेटा बोल रहा हूँ, बताइए"),
    (MEN, "हाँ मैं ही हूँ, मेरा बेटा बात करेगा"),
    (MEN, "Sameer nahi, main bhai hoon"),
    (WOMAN, "अब मैं बोल रही हूँ, उनकी बेटी"),
    (WOMAN, "मैं सुनीता की बहू हूँ, बताइए"),
    (WOMAN, "main hi hoon, unki beti, kya hua"),
    (WOMAN, "हाँ मैं बोल रही हूँ, उनकी जगह, बोलिए"),
]


def _id(case) -> str:
    return case[1][:24]


@pytest.mark.parametrize("case", CLAIMS + ACCOUNTS, ids=_id)
def test_the_word_list_reads_a_claim_with_a_tail(case):
    name, reply = case
    assert claim_with_tail(reply, HE if reply.isascii() else HI, name.split()[0])


@pytest.mark.parametrize("case", NOT_CLAIMS, ids=_id)
def test_the_word_list_refuses_a_claim_that_puts_someone_else_in_place(case):
    name, reply = case
    assert not claim_with_tail(reply, HE if reply.isascii() else HI, name.split()[0])


OPENING_ARMS = arms_with("who_or_why", "answer", "yes", "unclear", "confirms_self")


@pytest.mark.parametrize("arm", OPENING_ARMS)
@pytest.mark.parametrize("case", CLAIMS, ids=_id)
def test_a_claim_with_a_tail_passes_at_the_name_question(arm, case):
    name, reply = case
    call = run([reply], OPENING_ARMS[arm], name=name)
    assert call.end is None and call.state.speaker_confirmed, call.keys
    assert call.keys[-1] == "disclosure.go_ahead" and "right_party.reask" not in call.keys, call.keys


@pytest.mark.parametrize("arm", OPENING_ARMS)
@pytest.mark.parametrize("case", CLAIMS[::3], ids=_id)
def test_a_claim_with_a_tail_passes_at_the_direct_question(arm, case):
    name, reply = case
    call = run(["हाँ जी", reply], OPENING_ARMS[arm], name=name)
    assert call.end is None and call.state.speaker_confirmed and call.keys[-1] == "disclosure.go_ahead", call.keys


@pytest.mark.parametrize("case", CLAIMS[:4], ids=_id)
def test_a_wrong_person_label_still_ends_a_claim_at_the_opening(case):
    name, reply = case
    call = run([reply], lambda: labelled("wrong_person"), name=name)
    assert call.end.outcome is Outcome.wrong_party and call.state.speaker_confirmed is False


@pytest.mark.parametrize("arm", arms_with("confirms_self", "yes", "who_or_why"))
@pytest.mark.parametrize("case", NOT_CLAIMS, ids=_id)
def test_no_lookalike_passes_at_the_opening(arm, case):
    name, reply = case
    call = run([reply, "हम्म"], arms_with("confirms_self", "yes", "who_or_why")[arm], name=name)
    assert not call.state.speaker_confirmed and names_nothing(call.keys), call.keys


# With the year of birth on, this round changes nothing at the name question (a `confirms_self` label there still
# goes to the go-ahead before the year: C-y08, known and not fixed here).
@pytest.mark.parametrize("arm", arms_with("who_or_why", "answer"))
def test_with_the_year_of_birth_a_claim_with_a_tail_names_nothing_before_the_year(arm):
    call = run(["हां भाई, मैं ही समीर हूँ. क्या issue है?"], arms_with("who_or_why", "answer")[arm],
               identity=YEAR_POLICY)  # fmt: skip
    assert call.end is None and names_nothing(call.keys), call.keys


PASS = ["हाँ जी, बोल रहा हूँ"]
TO_WHO_CHECK = {
    "go_ahead": [*PASS, "हेलो? जी, क्या है?"],
    "kind": [*PASS, "हाँ ठीक है", "बस एक एफडी ली थी", "मैं तो अभी आया हूँ, क्या पूछ रहे हो?"],
}


def _woman(replies: list[str], name: str) -> list[str]:
    if name != WOMAN:
        return replies
    return [r.replace("बोल रहा हूँ", "बोल रही हूँ").replace("आया हूँ", "आई हूँ") for r in replies]


@pytest.mark.parametrize("arm", arms_with("confirms_self", "yes", "answer"))
@pytest.mark.parametrize("where", TO_WHO_CHECK)
@pytest.mark.parametrize("case", CLAIMS + ACCOUNTS, ids=_id)
def test_a_claim_with_a_tail_resumes_at_the_who_check(arm, where, case):
    name, reply = case
    setup = _woman(TO_WHO_CHECK[where], name)
    factory = arms_with("confirms_self", "yes", "answer")[arm]
    assert run(setup, factory, name=name).keys[-1] == "right_party.who_check"
    call = run([*setup, reply], factory, name=name)
    assert call.end is None and call.keys[-1] != "right_party.who_check", call.keys


@pytest.mark.parametrize("arm", arms_with("confirms_self", "yes"))
@pytest.mark.parametrize("where", TO_WHO_CHECK)
@pytest.mark.parametrize("case", NOT_CLAIMS, ids=_id)
def test_a_lookalike_at_the_who_check_ends_and_names_nothing(arm, where, case):
    name, reply = case
    setup = _woman(TO_WHO_CHECK[where], name)
    call = run([*setup, reply], arms_with("confirms_self", "yes")[arm], name=name)
    assert call.end is not None and call.end.outcome is Outcome.wrong_party, call.keys
    assert names_nothing(keys_after(call, len(setup))) and call.end.speaker_confirmed is False


@pytest.mark.parametrize("arm", arms_with("confirms_self"))
@pytest.mark.parametrize("reply", ["हाँ", "जी हाँ बोलिए", "haan ji batao"])
def test_a_bare_yes_at_the_who_check_still_ends(arm, reply):
    call = run([*TO_WHO_CHECK["kind"], reply], arms_with("confirms_self")[arm])
    assert call.end.outcome is Outcome.wrong_party and call.end.speaker_confirmed is False


@pytest.mark.parametrize("arm", ARMS)
def test_a_claim_with_a_stop_at_the_who_check_ends_as_asked_unconfirmed(arm):
    call = run([*TO_WHO_CHECK["kind"], "मैं ही हूँ, पर दोबारा फ़ोन मत करना"], ARMS[arm])
    assert call.end.outcome is Outcome.do_not_call and call.end.speaker_confirmed is False, call.keys


def test_a_wrong_person_label_at_the_who_check_ends_a_claim():
    call = run([*TO_WHO_CHECK["kind"], "हाँ भाई मैं ही हूँ, बेटे के हाथ में फ़ोन था"], lambda: labelled("wrong_person"))
    assert call.end.outcome is Outcome.wrong_party


# --- 2. a removal request with an address form at the opening ---------------------------------------------------

REMOVALS = ["mera no. hata do bhai", "मेरा नंबर हटा दो भाई", "list se hatao yaar", "mera number delete karo sir",
            "भैया मेरा नं. लिस्ट से हटा दीजिए", "number hata do madam", "दीदी मेरा नंबर हटाइए"]  # fmt: skip


@pytest.mark.parametrize("arm", arms_with("remove_number", "unclear"))
@pytest.mark.parametrize("reply", REMOVALS)
def test_a_removal_with_an_address_form_is_a_do_not_call_from_an_unconfirmed_speaker(arm, reply):
    for name in (MEN, WOMAN):
        call = run([reply], arms_with("remove_number", "unclear")[arm], name=name)
        assert call.end.outcome is Outcome.do_not_call and call.end.speaker_confirmed is False, call.keys
        assert call.keys[-1] == "end.do_not_call" and names_nothing(call.keys)


def test_the_do_not_call_end_names_nothing():
    for language in (HI, HE):
        text = load_prompts(language).render("end.do_not_call")  # the line takes no slot: no name, no lender
        assert not any(word in text for word in LENDER_WORDS), text


@pytest.mark.parametrize("arm", ARMS)
def test_a_relatives_number_is_still_a_third_party(arm):
    call = run(["mere bhai ka number hata do"], ARMS[arm])
    assert call.end.outcome is Outcome.wrong_party


# --- 3. the go-ahead and a short delay or an echo ----------------------------------------------------------------

DELAYS = ["15 minute baad", "दो-तीन मिनट?", "do teen minute baat kar sakte hain", "थोड़ी देर", "thodi der baad",
          "दो तीन मिनट बात करें", "ek minute ruko", "पाँच मिनट बाद"]  # fmt: skip
CLEAR_LATER = ["15 minute baad call karna", "kal karna", "शाम को कॉल कीजिए", "बाद में कॉल करना", "5 minute baad karna"]
GO_AHEAD_ARMS = arms_with("call_back", "unclear", "asks_repeat")


def realistic(delay_label: str):
    """A classifier that gives `delay_label` to a delay reply and a plain reading to anything else."""

    def pick(reply: str, stage: str) -> str:
        if short_delay_or_echo(reply, HE if reply.isascii() else HI):
            return delay_label
        if "नहीं" in reply:
            return "refuse"
        if "बाद में" in reply or "बजे" in reply:
            return "call_back"
        return "yes" if "go_ahead" in stage else "answer"

    return lambda: LlmFallbackInterpreter(Labels(pick))


REALISTIC_ARMS = {**ARMS, **{label: realistic(label) for label in ("call_back", "unclear", "asks_repeat")}}


@pytest.mark.parametrize("reply", DELAYS)
def test_the_word_list_reads_a_delay_or_an_echo(reply):
    assert short_delay_or_echo(reply, HE if reply.isascii() else HI)


@pytest.mark.parametrize("reply", [*CLEAR_LATER, "abhi nahi, 10 minute baad", "busy hoon 5 minute", "नहीं, दो मिनट भी नहीं"])
def test_a_clear_later_or_a_refusal_is_no_delay(reply):
    assert not short_delay_or_echo(reply, HE if reply.isascii() else HI)


@pytest.mark.parametrize("arm", GO_AHEAD_ARMS)
@pytest.mark.parametrize("reply", DELAYS)
def test_a_delay_at_the_go_ahead_gets_one_re_ask_then_a_yes_goes_on(arm, reply):
    call = run([*PASS, reply], GO_AHEAD_ARMS[arm])
    assert call.end is None and call.keys[-1] == "disclosure.reask", call.keys
    on = run([*PASS, reply, "हाँ ठीक है"], GO_AHEAD_ARMS[arm])
    assert on.end is None and on.keys[-1] == "open_recall.ask", on.keys


@pytest.mark.parametrize("arm", REALISTIC_ARMS)
def test_after_the_re_ask_a_later_ends_as_a_call_back_and_a_refusal_as_declined(arm):
    later = run([*PASS, "15 minute baad", "बाद में कॉल करना, अभी बिज़ी हूँ"], REALISTIC_ARMS[arm])
    assert later.end.outcome is Outcome.call_back_later, later.keys
    refused = run([*PASS, "15 minute baad", "नहीं, बात नहीं करनी"], REALISTIC_ARMS[arm])
    assert refused.end.outcome is Outcome.declined, refused.keys


@pytest.mark.parametrize("arm", ARMS)
def test_the_delay_re_ask_happens_once_per_call(arm):
    call = run([*PASS, "15 minute baad", "थोड़ी देर"], ARMS[arm])
    assert call.end.outcome is Outcome.no_go_ahead and call.keys.count("disclosure.reask") == 1, call.keys
    # Asked again once already for an unclear reply: the delay still gets its one re-ask, then no more.
    twice = run([*PASS, "हम्म", "15 minute baad", "दो-तीन मिनट"], ARMS[arm])
    assert twice.end.outcome is Outcome.no_go_ahead and twice.keys.count("disclosure.reask") == 2, twice.keys


@pytest.mark.parametrize("arm", arms_with("call_back"))
@pytest.mark.parametrize("reply", CLEAR_LATER)
def test_a_clear_later_at_the_go_ahead_still_ends_as_a_call_back(arm, reply):
    call = run([*PASS, reply, "शाम छह बजे"], arms_with("call_back")[arm])
    assert call.end.outcome is Outcome.call_back_later and "disclosure.reask" not in call.keys, call.keys


@pytest.mark.parametrize("arm", ARMS)
def test_a_refusal_at_the_go_ahead_still_ends_declined(arm):
    call = run([*PASS, "नहीं, मुझे बात नहीं करनी"], ARMS[arm])
    assert call.end.outcome is Outcome.declined


def test_with_the_year_of_birth_a_delay_is_re_asked_before_the_year():
    call = run(["मैं ही बोल रहा हूँ", "15 minute baad", "हाँ जी"], ARMS["rules"], identity=YEAR_POLICY)
    assert call.end is None and call.keys.count("disclosure.reask") == 1 and call.keys[-1] == "second_check.ask", (
        call.keys
    )
