"""P8: the right-party check as a lender setting (contract §5 items 1 to 5, and the call with each setting).

Typed text, not speech. Builder-written inputs; the independent verifier's inputs are not here.
"""

from __future__ import annotations

import json
from datetime import date

import pytest
from dialogue_kit import CUSTOMERS, LANGUAGES, LENDER, NO_CHECK, YEAR_POLICY, play, product, record
from test_p2_round3 import Labels

from samajh.clients.errors import TransportError
from samajh.dialogue import LINES, CallState, Outcome, identity_record, load_prompts, start
from samajh.dialogue.lint import lint_line
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.identity import (
    CHECK_LINES,
    MENU,
    CheckKind,
    IdentityPolicy,
    IdentityRecord,
    describe,
    expected_answer,
    parse_policy,
)
from samajh.types import Language, LoanRecord

HI, HE = Language.hi, Language.hi_en
YEAR_2 = IdentityPolicy(second_check=CheckKind.year_of_birth, attempts=2)
QUIET = IdentityPolicy(call_back_line=False)
QUIET_YEAR = IdentityPolicy(second_check=CheckKind.year_of_birth, call_back_line=False)
LOAN_WORDS = ("लोन", "loan", "बीमा", "insurance", "प्रीमियम", "premium", LENDER)
YEAR_WORDS = ("जन्म", "साल", "birth", "year", "सन")

CREDENTIALS = ("otp", "pin", "password", "cvv", "account", "card", "aadhaar", "aadhar", "pan", "date_of_birth",
               "dob", "full_date", "maiden", "mother")  # fmt: skip
UNDER_TEST = ("kind", "premium", "payment", "source", "cover", "term", "cancel", "window", "consent", "provider",
              "choice")  # fmt: skip


def raises() -> LlmFallbackInterpreter:
    return LlmFallbackInterpreter(Labels(error=TransportError("down")))


def labelled(label: str) -> LlmFallbackInterpreter:
    return LlmFallbackInterpreter(Labels(lambda reply, stage: label))


ARMS = {"rules": lambda: None, "raises": raises}


def run(replies, identity=NO_CHECK, reader=None, language=HI, **kw):
    extra = {"interpreter": reader} if reader is not None else {}
    return play(record(product()), language, replies, identity=identity, **extra, **kw)


def text_before(call, key: str) -> str:
    """Everything the bot said before the first line `key` (the whole call if it was never said)."""
    out = []
    for line in call.lines:
        if line.key == key:
            break
        out.append(line.text)
    return " ".join(out)


# --- 1. The menu holds no credential and no record value under test ----------------------------------


def test_the_menu_names_no_credential_and_no_record_value_under_test():
    names = (
        [kind.name.casefold() for kind in CheckKind]
        + [kind.value.casefold() for kind in CheckKind]
        + list(MENU)
    )
    for name in names:
        parts = name.replace("-", "_").split("_")
        assert not any(word in parts or word in name for word in CREDENTIALS if len(word) > 3), name
        assert not set(parts) & {"otp", "pin", "pan", "cvv", "dob"}, name
        assert not set(parts) & set(UNDER_TEST), name
    assert [kind.value for kind in CheckKind] == ["year_of_birth"]  # one member, on purpose (ledger I4)
    assert MENU == ("none", "year_of_birth")


# --- 2. The expected answer is the year and nothing else -----------------------------------------------


def _record_with(**changes) -> LoanRecord:
    base = record(product()).model_dump(mode="json")
    borrower = base["borrower"] | changes.pop("borrower", {})
    products = [base["products"][0] | changes.pop("product", {})]
    return LoanRecord.model_validate(base | {"borrower": borrower, "products": products} | changes)


def test_the_expected_answer_changes_only_with_the_year():
    kind = CheckKind.year_of_birth
    base = expected_answer(kind, _record_with())
    assert base == 1984
    others = [
        _record_with(
            product={
                "premium_inr": 9100,
                "cover_inr": 1,
                "term_months": 6,
                "paid_from_loan": False,
                "cancel_window_days": 15,
                "provider_choice_offered": True,
                "consent": {"method": "otp", "at": "2026-10-19"},
            }
        ),
        _record_with(sanctioned_inr=900000, disbursed_inr=800000),
        _record_with(borrower={"dob": "1984-01-01"}),
        _record_with(borrower={"dob": "1984-12-31"}),
    ]
    for other in others:
        assert expected_answer(kind, other) == base
    assert expected_answer(kind, _record_with(borrower={"dob": "1991-06-15"})) == 1991


def test_with_no_second_check_the_call_keeps_no_birth_year():
    state, _ = start(record(), HI, lender_name=LENDER)
    assert state.identity == NO_CHECK and state.plan.birth_year is None
    assert "1984" not in state.model_dump_json()
    year_state, _ = start(record(), HI, lender_name=LENDER, identity=YEAR_POLICY)
    assert year_state.plan.birth_year == 1984


# --- 3. The setting has no text; the parser keeps to the menu -------------------------------------------


def test_the_policy_has_no_text_field_and_its_default_is_no_second_check():
    for name, field in IdentityPolicy.model_fields.items():
        assert field.annotation is not str, name
    assert IdentityPolicy() == IdentityPolicy(
        second_check=None, attempts=1, prior_notice=True, call_back_line=True
    )
    with pytest.raises(ValueError):
        IdentityPolicy(question="what is your pin code?")  # extra fields are forbidden


@pytest.mark.parametrize("mapping", [
    {"second_check": "pin_code"}, {"second_check": "what is your mother's name?"}, {"second_check": "YEAR_OF_BIRTH"},
    {"second_check": 1}, {"question": "anything"}, {"second_check": "none", "text": "free text"}, {"attempts": 3},
    {"attempts": "2"}, {"attempts": True}, {"attempts": 0}, {"prior_notice": "yes"}, {"call_back_line": 1},
    {"second_check": ["year_of_birth", "pin_code"]},
])  # fmt: skip
def test_the_parser_refuses_anything_outside_the_menu(mapping):
    with pytest.raises(ValueError):
        parse_policy(mapping)


def test_the_parser_reads_the_menu():
    assert parse_policy({}) == IdentityPolicy()
    assert parse_policy({"second_check": "none"}) == IdentityPolicy()
    assert parse_policy({"second_check": "year_of_birth", "attempts": 2}) == YEAR_2
    assert parse_policy({"call_back_line": False, "prior_notice": False}) == IdentityPolicy(
        call_back_line=False, prior_notice=False
    )


def test_the_description_says_plainly_what_each_setting_does():
    none = describe(IdentityPolicy())
    assert "No second check" in none and "affirms twice" in none and "treated as the borrower" in none
    assert "right-party check, not identity verification" in none
    year = describe(YEAR_2)
    assert "year of birth" in year and "two attempts" in year and "family member" in year
    assert "right-party check, not identity verification" in year
    assert "one attempt" in describe(YEAR_POLICY)


# --- 4. Every line a check names exists in each language and passes the lint ----------------------------


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("kind", [None, *CheckKind])
def test_every_line_a_check_names_exists_and_passes_the_lint(language, kind):
    pack = load_prompts(language)
    for key in CHECK_LINES[kind]:
        assert key in LINES and key in pack.templates, (language, key)
        assert lint_line(key, pack.templates[key]) == [], (language, key)
        assert not any(ch.isdigit() for ch in pack.templates[key]), (language, key)


@pytest.mark.parametrize("language", [HI, HE])
@pytest.mark.parametrize("key", ["right_party.who_check", "ack.neutral", "kind.ask_named"])
def test_the_new_lines_pass_the_lint_and_name_no_product(language, key):
    text = load_prompts(language).templates[key]
    assert lint_line(key, text) == [] and not any(ch.isdigit() for ch in text)
    assert not any(word in text for word in LOAN_WORDS)


# --- 5. The record of the check holds no answer -----------------------------------------------------------


def test_the_identity_record_has_no_field_for_an_answer_and_its_sentence_no_digit():
    fields = set(IdentityRecord.model_fields)
    assert fields == {"policy", "check_used", "attempts_allowed", "attempts_used", "passed", "prior_notice_shown",
                      "prior_notice_mocked", "sentence"}  # fmt: skip
    for name, field in IdentityRecord.model_fields.items():
        assert field.annotation is not int or name.startswith("attempts"), name
    with pytest.raises(ValueError):
        IdentityRecord(policy=YEAR_POLICY, check_used=CheckKind.year_of_birth, attempts_allowed=1, attempts_used=1,
                       passed=True, prior_notice_shown=True, sentence="year 1984 matched")  # fmt: skip


@pytest.mark.parametrize("policy, replies, passed, used", [
    (NO_CHECK, ["हाँ जी", "हाँ"], True, 0),
    (NO_CHECK, ["हाँ जी", "नहीं, मैं उनका भाई हूँ"], False, 0),
    (NO_CHECK, ["मुझे बात नहीं करनी"], None, 0),
    (YEAR_POLICY, ["हाँ जी", "उन्नीस सौ चौरासी"], True, 1),
    (YEAR_POLICY, ["हाँ जी", "1985"], False, 1),
    (YEAR_2, ["हाँ जी", "1985", "1984"], True, 2),
    (YEAR_2, ["हाँ जी", "1985", "1990"], False, 2),
    (YEAR_POLICY, ["रॉन्ग नंबर है"], False, 0),
])  # fmt: skip
def test_the_identity_record_of_a_call(policy, replies, passed, used):
    call = run(replies, identity=policy)
    kept = identity_record(call.state)
    assert kept.passed is passed and kept.attempts_used == used and kept.check_used is policy.second_check
    dumped = kept.model_dump_json()
    assert "1984" not in dumped and "चौरासी" not in dumped and "1985" not in dumped
    assert not any(ch.isdigit() for ch in kept.sentence) and kept.prior_notice_mocked is True
    for reply in replies:
        assert reply not in dumped


def test_a_state_saved_before_p8_loads_as_the_year_with_one_attempt():
    state, _ = start(record(), HI, lender_name=LENDER, identity=YEAR_POLICY)
    old = json.loads(state.model_dump_json())
    for name in ("identity", "check_attempts", "check_passed", "recall_named"):
        old.pop(name)
    restored = CallState.model_validate(old)
    assert restored.identity == IdentityPolicy(second_check=CheckKind.year_of_birth, attempts=1)
    assert identity_record(restored).passed is None


# --- The call with no second check (the default) ---------------------------------------------------------


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("replies", [["हाँ जी", "हाँ"], ["हाँ बोलिए", "जी हाँ"], ["हेलो?", "हाँ जी"], ["हाँ", "हाँ जी"],
                                     ["haan ji", "haan"], ["जी", "जी हाँ, बोलिए"]])  # fmt: skip
def test_a_yes_to_the_direct_question_passes(arm, replies):
    call = run(replies, reader=ARMS[arm](), language=HE if replies[0].isascii() else HI)
    assert call.end is None and call.keys[1] == "right_party.reask", call.keys
    assert call.keys[-1] == "disclosure.go_ahead" and call.state.speaker_confirmed
    assert not any(word in text_before(call, "disclosure.who") for word in LOAN_WORDS)


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize(
    "reply", ["हाँ जी, मैं ही बोल रहा हूँ", "जी, बोल रही हूँ", "yes, speaking", "main hi bol raha hoon"]
)
def test_an_explicit_first_person_claim_answers_the_direct_question(arm, reply):
    call = run([reply], reader=ARMS[arm](), language=HE if reply.isascii() else HI)
    assert "right_party.reask" not in call.keys and call.keys[-1] == "disclosure.go_ahead", call.keys


def test_the_disclosure_after_the_pass_carries_the_never_ask_and_the_call_back_lines():
    call = run(["हाँ जी", "हाँ", "हाँ ठीक है"])
    assert call.keys == (
        "right_party.ask", "right_party.reask",
        "disclosure.who", "disclosure.not_sales", "disclosure.recording", "disclosure.never_ask", "verify.short",
        "disclosure.go_ahead",
        "context.loan", "disclosure.rights", "open_recall.ask",
    )  # fmt: skip


@pytest.mark.parametrize("reply", [
    "नहीं, मैं उनका भाई हूँ", "हाँ, मैं उनकी पत्नी", "haan, main unka beta", "हाँ, रमेश की वाइफ बोल रही हूँ",
    "नहीं", "वो बाहर गए हैं", "जी नहीं, गलत नंबर",
])  # fmt: skip
@pytest.mark.parametrize("arm", ARMS)
def test_a_relation_or_a_denial_at_either_step_ends_as_wrong_party(arm, reply):
    language = HE if reply.isascii() else HI
    for prefix in ([], ["हाँ जी"]):
        call = run([*prefix, reply], reader=ARMS[arm](), language=language)
        assert call.end.outcome is Outcome.wrong_party, (prefix, call.keys)
        assert call.end.speaker_confirmed is False and not any(
            w in call.end.utterance.text for w in LOAN_WORDS
        )
        assert "disclosure.who" not in call.keys


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("reply", ["हाँ शायद", "पता नहीं", "हाँ, सुरेश बोल रहा हूँ", "हम्म", "हाँ जी, ये किसका फोन है"])
def test_a_hedge_another_name_or_an_unexplained_reply_at_the_direct_question_is_not_a_pass(arm, reply):
    call = run(["हाँ जी", reply, "हम्म"], reader=ARMS[arm]())
    assert call.end is not None and call.end.outcome in (Outcome.not_confirmed, Outcome.wrong_party), (
        call.keys
    )
    assert "disclosure.who" not in call.keys and not call.end.speaker_confirmed


def test_a_question_at_the_direct_question_is_answered_without_the_loan_and_asked_again():
    call = run(["हाँ जी", "हाँ, क्या बात है?"])
    assert call.end is None and call.keys[-2:] == ("purpose.before_confirm", "right_party.reask"), call.keys
    assert run(["हाँ जी", "हाँ, क्या बात है?", "हाँ जी"]).keys[-1] == "disclosure.go_ahead"


def test_with_the_classifier_failing_an_unsure_yes_at_the_direct_question_is_not_a_pass():
    reply = "हाँ जी, बोलो बोलो जल्दी"  # a yes with go-on words the closed courtesy list does not settle
    call = run(["हाँ जी", reply], reader=raises())
    assert "disclosure.who" not in call.keys and call.state.speaker_confirmed is False


def test_a_stub_classifier_decides_an_unsure_yes():
    reply = "हाँ जी, ठीक है भाई, आगे"
    passes = run(["हाँ जी", reply], reader=labelled("yes"))
    assert passes.keys[-1] == "disclosure.go_ahead", passes.keys
    ends = run(["हाँ जी", reply], reader=labelled("wrong_person"))
    assert ends.end.outcome is Outcome.wrong_party


@pytest.mark.parametrize("language", [HI, HE])
def test_with_no_second_check_no_line_mentions_a_year_and_none_before_the_pass_names_the_loan(language):
    customer = CUSTOMERS[language]
    replies = [
        customer.identity,
        customer.go_ahead,
        customer.recall,
        *customer.product_replies(),
        customer.consent,
    ]
    for opening in ([customer.identity], ["हाँ जी", "हाँ"], ["कौन?", "हाँ"]):
        call = run([*opening, *replies[1:]], language=language)
        assert call.end is not None and call.end.outcome is Outcome.completed, call.keys
        said = " ".join(line.text for line in call.lines).casefold()
        assert not any(word in said for word in YEAR_WORDS), [w for w in YEAR_WORDS if w in said]
        assert not any(key.startswith("second_check") for key in call.keys)
        assert not any(word in text_before(call, "disclosure.who") for word in LOAN_WORDS)


def test_the_call_back_line_can_be_turned_off_under_either_setting():
    assert "verify.short" not in run(["हाँ जी", "हाँ"], identity=QUIET).keys
    assert "verify.short" in run(["हाँ जी", "हाँ"]).keys
    claim = ["हाँ जी, बोल रहा हूँ", "हाँ"]
    assert "verify.short" in run(claim, identity=YEAR_POLICY).keys
    assert "verify.short" not in run(claim, identity=QUIET_YEAR).keys


# --- The year of birth (the lender's opt-in) ---------------------------------------------------------------


@pytest.mark.parametrize("arm", ARMS)
def test_one_attempt_keeps_round_4(arm):
    assert run(["हाँ जी", "1985"], YEAR_POLICY, ARMS[arm]()).end.outcome is Outcome.second_check_failed
    reasked = run(["हाँ जी", "याद नहीं"], YEAR_POLICY, ARMS[arm]())
    assert reasked.end is None and reasked.keys[-1] == "second_check.reask"
    assert run(["हाँ जी", "याद नहीं", "1984"], YEAR_POLICY, ARMS[arm]()).keys[-1] == "disclosure.go_ahead"


@pytest.mark.parametrize("arm", ARMS)
def test_two_attempts_ask_once_more_after_a_wrong_year_and_end_on_the_second(arm):
    retry = run(["हाँ जी", "1985"], YEAR_2, ARMS[arm]())
    assert retry.end is None and retry.keys[-1] == "second_check.reask"
    assert LENDER not in retry.utterances[-1].text
    assert run(["हाँ जी", "1985", "1984"], YEAR_2, ARMS[arm]()).keys[-1] == "disclosure.go_ahead"
    failed = run(["हाँ जी", "1985", "1983"], YEAR_2, ARMS[arm]())
    assert failed.end.outcome is Outcome.second_check_failed and LENDER not in failed.end.utterance.text
    guess = run(["हाँ जी", "शायद चौरासी", "पचासी"], YEAR_2, ARMS[arm]())
    assert guess.end.outcome is Outcome.second_check_failed  # a guess uses an attempt


def test_the_no_year_re_ask_stays_single_with_two_attempts():
    call = run(["हाँ जी", "याद नहीं", "याद नहीं"], YEAR_2)
    assert call.end.outcome is Outcome.second_check_failed
    mixed = run(["हाँ जी", "1985", "याद नहीं", "याद नहीं"], YEAR_2)
    assert mixed.end.outcome is Outcome.second_check_failed and mixed.keys.count("second_check.reask") == 2


def test_the_expected_answer_never_reaches_the_classifier_a_line_or_the_record():
    labels = Labels(lambda reply, stage: "unclear")
    reader = LlmFallbackInterpreter(labels)
    for policy, replies in ((YEAR_POLICY, ["हाँ जी", "1985"]), (YEAR_2, ["हाँ जी", "वो साल याद नहीं", "1985", "1990"]),
                            (NO_CHECK, ["हाँ जी", "हाँ जी भाई", "हम्म"])):  # fmt: skip
        call = run(replies, identity=policy, reader=reader)
        said = " ".join(line.text for line in call.lines)
        assert "1984" not in said and "चौरासी" not in said
        assert "1984" not in identity_record(call.state).model_dump_json()
    assert labels.calls and not any("1984" in sent or "चौरासी" in sent for sent in labels.calls)


def test_the_birth_date_of_the_record_never_reaches_the_case_record_under_any_setting():
    rec = record(product(), dob=str(date(1971, 3, 9)))
    for policy in (NO_CHECK, YEAR_POLICY, YEAR_2):
        call = play(rec, HI, ["हाँ जी", "हाँ", "1971", "हाँ"], identity=policy)
        dumped = identity_record(call.state).model_dump_json()
        assert "1971" not in dumped and "03-09" not in dumped
