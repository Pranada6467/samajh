"""Iteration 3 fix round (after references/reviews/iter3/verify-call.md). One test group per fault class.

Builder-written inputs, Hindi and Hinglish (Devanagari and romanised), typed text; none is taken from the verifier's
probe files. Arms: the word lists alone ("rules"), a classifier that raises ("raises"), and fixed classifier labels
(a label chosen to be as unhelpful as possible for the class).
"""

from __future__ import annotations

import pytest
from dialogue_kit import LENDER, NO_CHECK, YEAR_POLICY, play, product, record
from test_p2_round3 import Labels

from samajh.clients.errors import TransportError
from samajh.dialogue import Outcome, identity_record, load_prompts
from samajh.dialogue.interpret import Expecting, RuleInterpreter, _near_numbers
from samajh.dialogue.lint import lint_line
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.identity import CheckKind, IdentityPolicy
from samajh.types import Language

HI, HE = Language.hi, Language.hi_en
YEAR2 = IdentityPolicy(second_check=CheckKind.year_of_birth, attempts=2)
# Lines that name the lender, the loan or a figure.
NAMING = ("verify.after_loan", "context.loan", "disclosure.reask", "kind.reask", "open_recall", "read_back",
          "teach_back.intro_nth", "required_for_loan", "close.verify")  # fmt: skip


# W4: the context classifier is now asked about the setup claim too; it answers that one as a classifier would, so a
# fixed label still lands on the turn under test.
SETUP_CLAIMS = ("हाँ जी, बोल रहा हूँ", "हाँ जी, बोल रही हूँ")


def _setup_or(label: str, reply: str, stage: str) -> str:
    if "first_name" in stage and reply in SETUP_CLAIMS:
        return "confirms_self"
    return "yes" if "go_ahead" in stage and reply == "हाँ ठीक है" else label


def labelled(label: str) -> LlmFallbackInterpreter:
    return LlmFallbackInterpreter(Labels(lambda reply, stage: _setup_or(label, reply, stage)))


def raises() -> LlmFallbackInterpreter:
    return LlmFallbackInterpreter(Labels(error=TransportError("down")))


ARMS = {"rules": lambda: None, "raises": raises}


def arms_with(*labels: str) -> dict:
    return {**ARMS, **{label: (lambda label=label: labelled(label)) for label in labels}}


def run(replies, arm_factory, identity=NO_CHECK):
    reader = arm_factory()
    extra = {"interpreter": reader} if reader is not None else {}
    language = HE if replies[-1].isascii() else HI
    return play(record(product()), language, replies, identity=identity, **extra)


def keys_after(call, turns: int) -> list[str]:
    """Line keys the bot said after the first `turns` customer replies."""
    return [line.key for utterance in call.utterances[turns + 1 :] for line in utterance.lines]


def names_nothing(keys) -> bool:
    return not any(key.startswith(NAMING) for key in keys)


PASS = ["हाँ जी, बोल रहा हूँ"]  # an explicit claim: passes, then the go-ahead
AT_KIND = [*PASS, "हाँ ठीक है", "बस एक एफडी ली थी"]  # the kind question
AT_PAYMENT = [*AT_KIND, "एफडी है", "बावन हज़ार", "हाँ सही है"]  # the payment-source question
AT_READ_BACK = [*AT_KIND, "एफडी है", "बावन हज़ार"]  # the premium read-back


# --- 1. takeover at the go-ahead --------------------------------------------------------------------------

GO_AHEAD_THIRD_PARTY = ["हाँ बोलिए, मैं उनका भतीजा हूँ", "अभी उनकी पत्नी बोल रही हूँ, बताइए",
                        "haan ji, main unka beta bol raha hoon, kya kaam hai", "papa ne phone pakda diya, boliye"]  # fmt: skip
GO_AHEAD_SIGNS = ["हेलो? जी, क्या है?", "hello hello, kaun bol raha hai?", "हेलो, किसको चाहिए था?",
                  "हाँ जी, आप किससे बात कर रहे थे?", "main abhi aaya hoon, kya baat hai"]  # fmt: skip


@pytest.mark.parametrize("arm", arms_with("yes", "confirms_self", "answer"))
@pytest.mark.parametrize("reply", GO_AHEAD_THIRD_PARTY)
def test_a_third_party_at_the_go_ahead_ends_whatever_the_label(arm, reply):
    call = run([*PASS, reply], arms_with("yes", "confirms_self", "answer")[arm])
    assert call.end is not None and call.end.outcome is Outcome.wrong_party, call.keys
    assert names_nothing(keys_after(call, 1)) and call.end.speaker_confirmed is False


@pytest.mark.parametrize("arm", arms_with("yes", "confirms_self", "answer", "who_or_why"))
@pytest.mark.parametrize("reply", GO_AHEAD_SIGNS)
def test_a_sign_at_the_go_ahead_gets_the_who_check_and_a_bare_yes_then_ends(arm, reply):
    factory = arms_with("yes", "confirms_self", "answer", "who_or_why")[arm]
    call = run([*PASS, reply], factory)
    assert call.keys[-1] == "right_party.who_check", call.keys
    ended = run([*PASS, reply, "हाँ जी"], factory)
    assert ended.end.outcome is Outcome.wrong_party and names_nothing(keys_after(ended, 1)), ended.keys


@pytest.mark.parametrize("arm", ARMS)
def test_a_self_claim_after_a_go_ahead_who_check_puts_the_go_ahead_again(arm):
    call = run([*PASS, "हेलो? जी, क्या है?", "अरे मैं ही हूँ", "हाँ ठीक है"], ARMS[arm])
    assert call.end is None and "disclosure.reask" in call.keys and call.keys[-1] == "open_recall.ask", (
        call.keys
    )


# --- 2. whom / just arrived / know nothing, after the pass ------------------------------------------------

NEWCOMER = ["जी, आपको किससे बात करनी है?", "kis se baat karni thi aapko?", "who are you looking for?",
            "aap kisko dhoondh rahe ho?", "मैं तो अभी अभी आई हूँ, क्या पूछ रहे हो?", "just came in, what is this about?",
            "किस बारे में? मुझे कुछ नहीं पता", "kaun chahiye aapko bhai?"]  # fmt: skip
POSITIONS = {"kind": AT_KIND, "payment": AT_PAYMENT, "read_back": AT_READ_BACK}


@pytest.mark.parametrize("arm", arms_with("answer", "who_or_why", "dont_know"))
@pytest.mark.parametrize("where", POSITIONS)
@pytest.mark.parametrize("reply", NEWCOMER)
def test_a_newcomer_sign_after_the_pass_gets_the_who_check_and_names_nothing(arm, where, reply):
    setup = POSITIONS[where]
    call = run([*setup, reply], arms_with("answer", "who_or_why", "dont_know")[arm])
    assert call.keys[-1] == "right_party.who_check", call.keys
    assert names_nothing(keys_after(call, len(setup)))


@pytest.mark.parametrize("arm", ARMS)
def test_knowing_nothing_at_a_read_back_is_a_sign_but_not_at_a_question_about_the_sale(arm):
    assert run([*AT_READ_BACK, "मुझे इसका कुछ नहीं पता"], ARMS[arm]).keys[-1] == "right_party.who_check"
    answer = run([*AT_KIND, "मुझे इसके बारे में कुछ नहीं पता"], ARMS[arm])
    assert answer.end is None and answer.keys[-1] != "right_party.who_check", answer.keys


@pytest.mark.parametrize("arm", arms_with("answer"))
@pytest.mark.parametrize("name", ["मैं सुरेश बोल रहा हूँ", "Suresh speaking", "मेरा नाम दिनेश है", "myself Mahesh"])
def test_a_speaker_naming_themself_as_someone_else_is_never_an_answer(arm, name):
    call = run([*AT_KIND, "हाँ जी", name], arms_with("answer")[arm])
    assert call.keys[-1] == "right_party.who_check", call.keys


@pytest.mark.parametrize("reply", ["मेरे बेटे ने भरे थे", "मेरी पत्नी ने बताया था", "mere bhai ne diya tha"])
def test_a_weak_sign_a_label_let_pass_lets_no_naming_line_play_before_the_who_check(reply):
    call = run([*AT_PAYMENT, reply, "एक बार", "हाँ ज़रूरी बोला था"], lambda: labelled("answer"))
    said = keys_after(call, len(AT_PAYMENT))
    assert "right_party.who_check" in said, said
    assert names_nothing(said[: said.index("right_party.who_check")])
    resumed = run([*AT_PAYMENT, reply, "एक बार", "मैं ही हूँ"], lambda: labelled("answer"))
    assert resumed.end is None and resumed.keys[-1] == "required_for_loan.ask", resumed.keys


# --- 3. self-claims at the who-check, word lists alone ----------------------------------------------------

TO_WHO_CHECK = [*AT_KIND, "हेलो? क्या पूछ रहे थे?"]
CLAIMS = ["अरे मैं ही हूँ, रमेश", "हाँ भाई, मैं ही रमेश हूँ, बोलो", "arre main hi hoon yaar", "मैं रमेश ही हूँ जी",
          "बच्चे ने फ़ोन ले लिया था, मैं रमेश बोल रहा हूँ", "meri beti ne phone utha liya tha, main Ramesh hoon",
          "बेटे ने फ़ोन उठा लिया था मैं ही बोल रहा हूँ", "नहीं नहीं, मैं ख़ुद हूँ"]  # fmt: skip
NOT_CLAIMS = ["हाँ", "जी हाँ बोलिए", "मैं रमेश का भाई", "मैं रमेश की वाइफ़ बोल रही हूँ", "main unka beta hoon",
              "मेरी बेटी ने फ़ोन उठाया था, अब वो बोल रही है", "उनके बेटे ने फ़ोन उठाया था, मैं बोल रहा हूँ",
              "मैं सुरेश बोल रहा हूँ"]  # fmt: skip


@pytest.mark.parametrize("arm", arms_with("confirms_self"))
@pytest.mark.parametrize("reply", CLAIMS)
def test_a_natural_self_claim_at_the_who_check_resumes_in_every_arm(arm, reply):
    call = run([*TO_WHO_CHECK, reply], arms_with("confirms_self")[arm])
    assert call.end is None and call.keys[-1].startswith("kind."), call.keys


@pytest.mark.parametrize("arm", arms_with("confirms_self", "yes"))
@pytest.mark.parametrize("reply", NOT_CLAIMS)
def test_anything_but_an_own_first_person_claim_at_the_who_check_ends(arm, reply):
    call = run([*TO_WHO_CHECK, reply], arms_with("confirms_self", "yes")[arm])
    assert call.end.outcome is Outcome.wrong_party and names_nothing(keys_after(call, len(TO_WHO_CHECK))), (
        call.keys
    )


# --- 4. a weak sign of the speaker's own relative -----------------------------------------------------------

WEAK = ["मेरे भाई ने कहा था ये लेना पड़ेगा", "मेरी वाइफ़ ने भरे थे पैसे", "mere papa ne sign kiya tha"]


@pytest.mark.parametrize("label", ["third_party_handoff", "wrong_person"])
@pytest.mark.parametrize("reply", WEAK)
def test_a_weak_sign_with_an_end_label_gets_the_who_check_not_the_end(label, reply):
    call = run([*AT_PAYMENT, reply], lambda: labelled(label))
    assert call.end is None and call.keys[-1] == "right_party.who_check", call.keys


@pytest.mark.parametrize("label", ["third_party_handoff", "wrong_person"])
def test_a_strong_sign_with_an_end_label_still_ends(label):
    call = run([*AT_PAYMENT, "मैं उनका छोटा भाई हूँ"], lambda: labelled(label))
    assert call.end.outcome is Outcome.wrong_party


# --- 5. hedges at the direct question -----------------------------------------------------------------------

HEDGES = ["हाँ, वही मान लीजिए", "हाँ जी वही हैं", "haan wahi hai ji", "samajh lo haan", "जी, कह सकते हैं"]


@pytest.mark.parametrize("arm", arms_with("yes", "confirms_self"))
@pytest.mark.parametrize("first", ["हाँ", "yes"])
@pytest.mark.parametrize("reply", HEDGES)
def test_a_hedge_at_the_direct_question_never_passes(arm, first, reply):
    call = run([first, reply], arms_with("yes", "confirms_self")[arm])
    assert call.end is not None and call.end.outcome is Outcome.not_confirmed, call.keys
    assert call.state.speaker_confirmed is False and "disclosure.who" not in call.keys


# --- 6. the year of birth -----------------------------------------------------------------------------------

YEAR_HEDGES = ["1984 के आसपास", "takriban 1984", "उन्नीस सौ चौरासी के करीब", "lagbhag chaurasi", "about 1984"]


@pytest.mark.parametrize("arm", arms_with("answer"))
@pytest.mark.parametrize("reply", YEAR_HEDGES)
def test_a_hedged_year_is_a_guess_and_uses_the_attempt(arm, reply):
    one = run(["जी", reply], arms_with("answer")[arm], identity=YEAR_POLICY)
    assert one.end.outcome is Outcome.second_check_failed, one.keys
    two = run(["जी", reply], arms_with("answer")[arm], identity=YEAR2)
    assert two.end is None and two.keys[-1] == "second_check.reask" and two.state.check_attempts == 1


@pytest.mark.parametrize("arm", arms_with("answer"))
@pytest.mark.parametrize(
    "correction", ["नहीं नहीं, चौरासी", "nahi nahi, 1984", "नहीं जी, उन्नीस सौ चौरासी", "चौरासी"]
)
def test_a_leading_no_before_the_right_year_at_the_retry_is_the_year(arm, correction):
    call = run(["जी", "उन्नीस सौ पचासी", correction], arms_with("answer")[arm], identity=YEAR2)
    assert call.end is None and call.state.speaker_confirmed, call.keys


def test_a_no_word_is_never_read_as_a_number():
    for word in ("nahi", "nahin", "naheen", "nahee", "nhi", "nai", "नहीं", "नही", "नहि", "ना", "nope"):
        assert _near_numbers(f"{word} चौरासी", HI)[0].split()[0] == word
    heard = RuleInterpreter().interpret("नहीं नहीं, चौरासी", language=HI, expecting=Expecting.birth_year)
    assert heard.year == 84 and not heard.two_years
    guess = RuleInterpreter().interpret("चौरासी, नहीं पचासी", language=HI, expecting=Expecting.birth_year)
    assert guess.year is None and guess.two_years


# --- 7. do-not-call: remove my number -----------------------------------------------------------------------

REMOVE = ["mera number hata do please", "list se hatao mera number", "मेरा नंबर लिस्ट से हटा दीजिए",
          "number delete kar dijiye", "हटाइए मेरा नंबर अपनी लिस्ट से", "apni list se nikaal do mujhe", "remove my number pls"]  # fmt: skip


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("policy", [NO_CHECK, YEAR_POLICY], ids=["none", "year"])
@pytest.mark.parametrize("reply", REMOVE)
def test_remove_my_number_ends_as_do_not_call(arm, policy, reply):
    call = run([reply], ARMS[arm], identity=policy)
    assert call.end.outcome is Outcome.do_not_call and LENDER not in " ".join(u.text for u in call.utterances)


def test_taking_money_out_is_not_a_removal():
    call = run([*AT_KIND, "एफडी है, एक साल बाद पैसे निकाल सकते हैं"], ARMS["rules"])
    assert call.end is None


# --- 8. explicit claims at the name question, classifier failing ---------------------------------------------

EXPLICIT = ["जी, मैं ही रमेश हूँ", "हाँ जी, रमेश बोल रहा हूँ", "मैं रमेश हूँ जी, बोलिए", "haan main Ramesh hi bol raha hoon",
            "ji main Ramesh hoon", "yes, Ramesh speaking", "जी हाँ, मैं हूँ रमेश"]  # fmt: skip


@pytest.mark.parametrize("arm", arms_with("confirms_self", "yes"))
@pytest.mark.parametrize("reply", EXPLICIT)
def test_an_explicit_claim_passes_at_the_name_question_and_at_the_direct_question(arm, reply):
    factory = arms_with("confirms_self", "yes")[arm]
    at_once = run([reply], factory)
    assert at_once.state.speaker_confirmed and at_once.keys[-1] == "disclosure.go_ahead", at_once.keys
    after = run(["हाँ जी", reply], factory)
    assert after.state.speaker_confirmed and after.keys[-1] == "disclosure.go_ahead", after.keys


# --- 9. gender-neutral right-party lines --------------------------------------------------------------------


@pytest.mark.parametrize("language", [HI, HE])
@pytest.mark.parametrize("key", ["right_party.reask", "right_party.who_check"])
def test_the_right_party_lines_have_no_gendered_verb(language, key):
    text = load_prompts(language).templates[key]
    assert not any(form in text for form in ("बोल रहे", "बोल रही", "बोल रहा", "रहे हैं"))
    assert "{first_name} जी हैं" in text


# --- 10. the identity record after a later takeover ---------------------------------------------------------


@pytest.mark.parametrize("policy", [NO_CHECK, YEAR_POLICY], ids=["none", "year"])
def test_the_identity_sentence_says_when_the_call_later_ended_as_a_wrong_party(policy):
    setup = AT_KIND if policy is NO_CHECK else ["हाँ जी", "1984", "हाँ ठीक है", "बस एक एफडी ली थी"]
    call = run([*setup, "हेलो? क्या पूछ रहे थे?", "हाँ"], ARMS["rules"], identity=policy)
    assert call.end.outcome is Outcome.wrong_party
    record_ = identity_record(call.state)
    assert record_.passed is True and "ended it as a wrong party" in record_.sentence
    assert not any(ch.isdigit() for ch in record_.sentence)
    clean = run(AT_KIND, ARMS["rules"])
    assert "wrong party" not in identity_record(clean.state).sentence


# --- 11. the bot-line lint: credential paraphrases ----------------------------------------------------------

CREDENTIAL_LINES = ["आपके फ़ोन पर आया कोड बता दीजिए", "मैसेज में आए छह अंक बोलिए", "phone pe aaya code bata dijiye",
                    "अपनी माँ का शादी से पहले का नाम बताइए", "apni mummy ka naam bataiye", "your mother's maiden name please",
                    "कार्ड के पीछे के तीन अंक", "CVV bata dijiye", "एमपिन बताइए", "ATM pin boliye", "खाते का नंबर बताइए",
                    "account no bata dijiye"]  # fmt: skip


@pytest.mark.parametrize("line", CREDENTIAL_LINES)
def test_a_credential_paraphrase_cannot_be_a_bot_line(line):
    assert lint_line("context.loan", line)


def test_a_credential_word_may_stand_in_a_denial_line_only():
    denial = "हम आपसे कभी कोड, मैसेज वाला नंबर या माँ का नाम नहीं माँगेंगे।"
    assert lint_line("disclosure.never_ask", denial) == []
    assert lint_line("disclosure.never_ask", "अपना कोड बताइए") != []


# --- 13. figures after the amounts lane: romanised words and bounds ------------------------------------------

AT_PREMIUM = ["yes, speaking", "haan theek hai", "bas ek FD li thi", "FD hai"]


@pytest.mark.parametrize("said, words", [("bavan hazaar", "fifty two thousand"), ("pachpan hazaar diye the",
                                                                                   "fifty five thousand")])  # fmt: skip
def test_a_romanised_premium_is_read_back_at_once(said, words):
    call = run([*AT_PREMIUM, said], ARMS["rules"])
    assert call.keys[-1] == "read_back.confirm" and words in call.utterances[-1].text


@pytest.mark.parametrize("said", ["pachaas hazaar tak", "up to 52,000", "बावन हज़ार तक"])
def test_a_premium_said_as_a_bound_is_asked_again(said):
    call = run([*AT_PREMIUM, said], ARMS["rules"])
    assert call.keys[-1] == "premium.reask" and call.state.premiums == (), call.keys


def test_a_cover_said_as_a_bound_is_read_back():
    replies = [*AT_PREMIUM, "bavan hazaar", "haan sahi", "loan se kat gaya", "ek baar", "haan zaroori bola tha",
               "nahi bataya", "paanch lakh tak milega"]  # fmt: skip
    call = run(replies, ARMS["rules"])
    assert call.keys[-1] == "read_back.cover_confirm" and "five lakh" in call.utterances[-1].text
