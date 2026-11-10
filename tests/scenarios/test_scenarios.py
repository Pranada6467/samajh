"""The scenario set: what a consumer of data/scenarios can rely on.

Expected values here come from the task and the claims check, not from running the generator.
"""

import json
import os
import re
import shutil
import string
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from samajh.amounts import format_inr
from samajh.scenarios import build
from samajh.scenarios.model import (
    NOT_HUMAN_REVIEWED,
    CustomerState,
    Remedy,
    ScenarioClass,
    YesNoAnswer,
    YesNoDisposition,
    YesNoOutcome,
)
from samajh.scenarios.phrases import BANKS
from samajh.types import (
    CallStep,
    DontKnow,
    Evidence,
    Language,
    Question,
    RuleId,
    Speaker,
    Stated,
    Unclear,
    Verdict,
)

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data" / "scenarios"
SCENARIOS = build.load_scenarios(DATA)
CALLS = {c.id: c for c in build.load_calls(DATA)}
BY_TAG = {tag: [s for s in SCENARIOS if tag in s.tags] for s in SCENARIOS for tag in s.tags}
STEP_ORDER = list(CallStep)
ALWAYS_ASKED = {
    Question.kind,
    Question.premium,
    Question.payment_source,
    Question.required_for_loan,
    Question.cover,
    Question.term,
    Question.cancel_window,
    Question.features,
    Question.consent,
}

# --- size and shape ----------------------------------------------------------


def test_every_base_case_appears_once_in_each_language():
    assert len(SCENARIOS) == 144
    assert len({s.id for s in SCENARIOS}) == 144
    per_base = Counter(s.base for s in SCENARIOS)
    assert len(per_base) == 36 and set(per_base.values()) == {4}
    for base in per_base:
        assert {s.language for s in SCENARIOS if s.base == base} == set(Language)


def test_gold_is_the_same_in_every_language_of_a_base_case():
    for base in {s.base for s in SCENARIOS}:
        variants = [s for s in SCENARIOS if s.base == base]
        assert len({v.gold.model_dump_json() for v in variants}) == 1
        assert len({json.dumps([b.model_dump(mode="json") for b in v.beliefs]) for v in variants}) == 1


def test_each_checked_rule_has_violating_and_non_violating_cases():
    checked = {RuleId.kind, RuleId.premium, RuleId.consent, RuleId.bundling, RuleId.loan_funded, RuleId.belief_mismatch}
    for rule in checked:
        classes = {s.scenario_class for s in SCENARIOS if s.target_rule is rule}
        assert ScenarioClass.violating in classes, rule
        assert classes & {ScenarioClass.compliant, ScenarioClass.near_miss}, rule
    for rule in checked | {RuleId.cover, RuleId.term, RuleId.cancel_window, RuleId.recall, RuleId.sale_conduct}:
        flagged = [s for s in SCENARIOS if rule in {r for _, r in s.gold.flag_keys()}]
        not_flagged = [s for s in SCENARIOS if rule not in {r for _, r in s.gold.flag_keys()}]
        assert flagged and not_flagged, rule


def test_all_three_verdicts_occur():
    assert {s.gold.verdict for s in SCENARIOS} == set(Verdict)


# --- the cases the claims check requires -------------------------------------


def test_required_risk_mitigant_with_provider_choice_is_not_flagged():
    cases = BY_TAG["risk-mitigant-with-choice"]
    assert len(cases) == 4
    for s in cases:
        (product,) = s.record.products
        assert product.required_for_loan and product.risk_mitigant and product.provider_choice_offered
        assert s.beliefs[0].required_for_loan is True and s.beliefs[0].provider_choice_offered is True
        assert s.gold.verdict is Verdict.clear


@pytest.mark.parametrize("tag", ["sold-as-fd", "sold-as-security-deposit"])
def test_product_sold_as_a_deposit_flags_kind_and_belief(tag):
    cases = BY_TAG[tag]
    assert len(cases) >= 4
    for s in cases:
        flags = {r for _, r in s.gold.flag_keys()}
        assert {RuleId.kind, RuleId.belief_mismatch} <= flags


def test_savings_product_required_for_the_loan_flags_bundling_whatever_choice_was_offered():
    for s in BY_TAG["sold-as-security-deposit"]:
        assert RuleId.bundling in {r for _, r in s.gold.flag_keys()}
    not_a_mitigant = [s for s in SCENARIOS if not s.record.products[0].risk_mitigant]
    assert not_a_mitigant
    for s in not_a_mitigant:
        assert s.record.products[0].required_for_loan
        assert RuleId.bundling in {r for _, r in s.gold.flag_keys()}


def test_premium_from_the_loan_with_and_without_consent():
    for s in BY_TAG["loan-funded-without-consent"]:
        (product,) = s.record.products
        assert product.paid_from_loan and product.consent is None
        assert {RuleId.loan_funded, RuleId.consent} <= {r for _, r in s.gold.flag_keys()}
    with_consent = BY_TAG["loan-funded-with-consent"]
    assert any(s.gold.verdict is Verdict.clear for s in with_consent)
    for s in with_consent:
        (product,) = s.record.products
        assert product.paid_from_loan and product.consent is not None
        assert RuleId.loan_funded not in {r for _, r in s.gold.flag_keys()}


def test_consent_on_file_but_customer_unaware_flags_consent():
    cases = BY_TAG["consent-on-file-customer-unaware"]
    assert len(cases) == 4
    for s in cases:
        assert s.record.products[0].consent is not None
        assert s.beliefs[0].consent_given is False
        assert RuleId.consent in {r for _, r in s.gold.flag_keys()}


def test_coached_customers_pass_the_yes_no_call_and_are_never_clear():
    cases = BY_TAG["coached"]
    assert len(cases) == 12
    for s in cases:
        assert s.yes_no is YesNoDisposition.coached
        assert CALLS[s.id].yes_no.outcome is YesNoOutcome.confirmed
        assert s.gold.verdict is Verdict.flag_for_review
        assert s.template is not None


def test_premium_tolerance_cases_sit_on_either_side_of_one_percent():
    for tag, inside in (("premium-within-tolerance", True), ("premium-just-outside-tolerance", False)):
        cases = BY_TAG[tag]
        assert len(cases) == 4
        for s in cases:
            recorded, believed = s.record.products[0].premium_inr, s.beliefs[0].premium_inr
            gap = abs(believed - recorded) / recorded
            assert (gap <= 0.01) is inside and gap < 0.02
            assert (RuleId.premium in {r for _, r in s.gold.flag_keys()}) is not inside


def test_dont_know_customers_are_unclear_or_flagged_never_clear():
    cases = BY_TAG["dont-know"]
    assert {s.gold.verdict for s in cases} == {Verdict.unclear_needs_human, Verdict.flag_for_review}


FRACTION_WORDS = {
    Language.hi: ["सवा", "साढ़े", "पौने", "डेढ़", "ढाई"],
    Language.hi_en: ["सवा", "साढ़े", "पौने", "डेढ़", "ढाई", "and a half"],
    Language.ta: ["ஒன்றரை", "இரண்டரை", "ஒன்றேகால்", "முக்கால்", "ஏழரை"],
    Language.kn: ["ಒಂದೂವರೆ", "ಎರಡೂವರೆ", "ಒಂದೂಕಾಲು", "ಮುಕ್ಕಾಲು", "ಏಳೂವರೆ"],
}


@pytest.mark.parametrize("language", list(Language))
def test_customers_say_amounts_with_fraction_words(language):
    said = " ".join(
        t.text
        for s in SCENARIOS
        if s.language is language
        for t in CALLS[s.id].teach_back.transcript.turns
        if t.speaker is Speaker.customer
    )
    for word in FRACTION_WORDS[language]:
        assert word in said, word


# --- gold integrity ----------------------------------------------------------

INSURER_WON = {"PUN-L-013-1617-0583", "NOI-L-036-1819-0337", "JPR-L-041-1920-0004", "AHD-L-021-1617-0367"}
REMEDY_IN_AWARD = {  # references/claims/findings-B.md
    "BHP-L-021-1617-0529": Remedy.refund,
    "Baramulla DCDRC CC 33/2025": Remedy.refund,
    "PUN-L-041-1617-0649": Remedy.other,
    "BNG-L-033-1617-0600": Remedy.conversion,
    "BHP-L-013-1617-0436": Remedy.conversion,
    "BNG-L-041-1617-0797": Remedy.conversion,
    "PUN-L-036-1617-0228": Remedy.refund,
    "BHP-L-021-1617-0456": Remedy.conversion,
    "AHD-L-001-1617-0203": Remedy.refund,
    "CHD-L-019-1718-1436": Remedy.refund,
    "PUN-L-009-1617-0009": Remedy.partial_refund,
}


def test_templates_are_customer_relief_awards_with_the_remedy_the_award_ordered():
    templated = [s for s in SCENARIOS if s.template]
    assert {s.template.case for s in templated} == set(REMEDY_IN_AWARD)
    for s in templated:
        assert s.template.case not in INSURER_WON
        assert s.template.remedy is REMEDY_IN_AWARD[s.template.case]
        assert s.template.remedy_note


def test_compliant_and_near_miss_scenarios_are_synthetic():
    for s in SCENARIOS:
        if s.scenario_class is not ScenarioClass.violating:
            assert s.template is None, s.id


def test_class_matches_gold():
    for s in SCENARIOS:
        target_flagged = s.target_rule in {r for _, r in s.gold.flag_keys()}
        assert target_flagged is (s.scenario_class is ScenarioClass.violating), s.id
        if s.scenario_class is ScenarioClass.compliant:
            assert s.gold.verdict is Verdict.clear, s.id


def test_gold_verdict_cannot_contradict_its_flags():
    row = json.loads((DATA / build.GOLD_FILE).read_text(encoding="utf-8").splitlines()[0])
    row["gold"]["products"][0]["flags"] = ["kind"]
    with pytest.raises(ValueError, match="does not follow"):
        type(SCENARIOS[0]).model_validate(row)


def test_building_the_set_never_loads_the_rule_engine():
    code = (
        "import sys; from samajh.scenarios import build; build.generate(); "
        "sys.exit(1 if any(m == 'samajh.rules' or m.startswith('samajh.rules.') for m in sys.modules) else 0)"
    )
    assert subprocess.run([sys.executable, "-c", code], cwd=REPO, check=False).returncode == 0


# --- synthetic data only -----------------------------------------------------


def test_ids_are_format_valid_and_obviously_fake():
    for s in SCENARIOS:
        assert re.fullmatch(r"TEST-LN-\d{3}", s.record.loan_id)
        assert s.record.borrower.name.endswith("(synthetic)")
        assert all(p.provider.endswith("(synthetic)") for p in s.record.products)
        call = CALLS[s.id]
        assert call.teach_back.transcript.call_id == f"TEST-CALL-{s.id}-tb"
        assert call.yes_no.transcript.call_id == f"TEST-CALL-{s.id}-yn"
    assert len({s.record.loan_id for s in SCENARIOS}) == 144


def test_no_long_digit_run_that_could_be_a_phone_or_account_number():
    for call in CALLS.values():
        for transcript in (call.teach_back.transcript, call.yes_no.transcript):
            for turn in transcript.turns:
                assert not re.search(r"\d{5,}", turn.text), turn.text


def test_tamil_and_kannada_are_labelled_not_human_reviewed():
    for s in SCENARIOS:
        expected = s.language in (Language.ta, Language.kn)
        assert (s.text_review == NOT_HUMAN_REVIEWED) is expected
        assert CALLS[s.id].text_review == s.text_review
        assert "no human reviewer" in s.text_review or s.text_review == NOT_HUMAN_REVIEWED


# --- the scripted calls ------------------------------------------------------

SCRIPT_RANGES = {
    Language.hi: [(0x0900, 0x097F)],
    Language.hi_en: [(0x0900, 0x097F), (0x41, 0x5A), (0x61, 0x7A)],
    Language.ta: [(0x0B80, 0x0BFF)],
    Language.kn: [(0x0C80, 0x0CFF)],
}
NEUTRAL = set(string.digits + " ,.?!:-")


@pytest.mark.parametrize("language", list(Language))
def test_every_turn_is_written_in_the_scripts_of_its_language(language):
    ranges = SCRIPT_RANGES[language]
    for s in SCENARIOS:
        if s.language is not language:
            continue
        for transcript in (CALLS[s.id].teach_back.transcript, CALLS[s.id].yes_no.transcript):
            for turn in transcript.turns:
                stray = {
                    ch for ch in turn.text if ch not in NEUTRAL and not any(lo <= ord(ch) <= hi for lo, hi in ranges)
                }
                assert not stray, (s.id, turn.id, stray, turn.text)


def test_no_turn_has_an_unfilled_slot():
    for call in CALLS.values():
        for transcript in (call.teach_back.transcript, call.yes_no.transcript):
            for turn in transcript.turns:
                assert turn.text.strip() and "{" not in turn.text and "None" not in turn.text, turn.text


def test_teach_back_call_follows_the_call_flow():
    for s in SCENARIOS:
        turns = CALLS[s.id].teach_back.transcript.turns
        assert [t.speaker for t in turns] == [Speaker.bot, Speaker.customer] * (len(turns) // 2)
        steps = [STEP_ORDER.index(t.step) for t in turns]
        assert steps == sorted(steps), s.id
        assert {t.step for t in turns} >= set(CallStep) - {CallStep.read_back}
        product, belief = s.record.products[0], s.beliefs[0]
        asked = [t for t in turns if t.speaker is Speaker.bot and t.asks and t.step is not CallStep.read_back]
        for t in asked:
            assert (t.product_id is None) is (t.asks is Question.consent), (s.id, t.asks)
        assert not any(t.asks or t.product_id for t in turns if t.speaker is Speaker.customer)
        required = product.required_for_loan or belief.required_for_loan is True
        expected = ALWAYS_ASKED | ({Question.provider_choice} if required else set())
        assert Counter(t.asks for t in asked) == Counter(expected), s.id
        recall = turns[[t.step for t in turns].index(CallStep.open_recall)]
        assert recall.asks is None, "the open question names no product"
        read_backs = [t for t in turns if t.step is CallStep.read_back and t.speaker is Speaker.bot]
        if isinstance(belief.premium_inr, int):
            (read_back,) = read_backs
            assert read_back.asks is Question.premium and read_back.product_id == product.id
            assert format_inr(belief.premium_inr) in read_back.text
        else:
            assert not read_backs


def _evidence(value):
    if isinstance(value, Evidence):
        yield value
    elif isinstance(value, Stated | DontKnow) or (isinstance(value, Unclear) and value.evidence):
        yield value.evidence


QUESTION_OF_FIELD = {
    "kind": Question.kind,
    "premium": Question.premium,
    "payment_source": Question.payment_source,
    "required_for_loan": Question.required_for_loan,
    "provider_choice_offered": Question.provider_choice,
    "cover": Question.cover,
    "term": Question.term,
    "cancel_allowed": Question.cancel_window,
    "cancel_window": Question.cancel_window,
    "consent_given": Question.consent,
    "consent_method": Question.consent,
    "feature_probe": Question.features,
}


def test_every_extracted_answer_quotes_the_whole_reply_to_its_question():
    for s in SCENARIOS:
        call = CALLS[s.id].teach_back
        turns = {t.id: t for t in call.transcript.turns}
        (answers,) = call.extraction.products
        for name, question in QUESTION_OF_FIELD.items():
            for evidence in _evidence(getattr(answers, name)):
                reply, asked = turns[evidence.turn_id], turns[evidence.turn_id - 1]
                assert reply.speaker is Speaker.customer and evidence.quote == reply.text, (s.id, name)
                assert asked.asks is question and asked.step is not CallStep.read_back, (s.id, name)
        for evidence in _evidence(answers.premium_readback):
            assert turns[evidence.turn_id - 1].step is CallStep.read_back
        for extra in (*answers.volunteered_claims, *call.extraction.sale_concerns):
            assert extra.evidence.quote in turns[extra.evidence.turn_id].text
        assert [c.concern for c in call.extraction.sale_concerns] == list(s.concerns)


def test_stated_amounts_are_the_words_the_customer_said():
    for s in SCENARIOS:
        call = CALLS[s.id].teach_back
        bank, belief = BANKS[s.language], s.beliefs[0]
        (answers,) = call.extraction.products
        for name, value, table in (
            ("premium", belief.premium_inr, bank.amounts),
            ("cover", belief.cover_inr, bank.amounts),
            ("term", belief.term_months, bank.durations),
        ):
            answer = getattr(answers, name)
            if isinstance(value, int):
                assert answer.value == table[value] and answer.value in answer.evidence.quote, (s.id, name)
            else:
                assert not isinstance(answer, Stated), (s.id, name)


def test_yes_no_call_is_confirmed_only_when_every_answer_is_yes():
    for s in SCENARIOS:
        call = CALLS[s.id].yes_no
        assert len(call.replies) == 5
        all_yes = all(r.answer is YesNoAnswer.yes for r in call.replies)
        assert (call.outcome is YesNoOutcome.confirmed) is all_yes
        if s.yes_no is not YesNoDisposition.truthful:
            assert all_yes, s.id
        if s.yes_no is YesNoDisposition.truthful and s.customer_state is CustomerState.informed:
            assert all(r.answer is not YesNoAnswer.no for r in call.replies), s.id


def test_a_truthful_customer_who_names_another_product_or_denies_consent_is_not_confirmed():
    for s in SCENARIOS:
        if s.yes_no is not YesNoDisposition.truthful:
            continue
        belief = s.beliefs[0]
        if belief.consent_given is False or belief.kind in ("deposit", "investment", "dont_know"):
            assert CALLS[s.id].yes_no.outcome is YesNoOutcome.not_confirmed, s.id


def test_phrase_banks_agree_on_keys_and_slots():
    reference = BANKS[Language.hi]
    slots = re.compile(r"\{(\w+)\}")
    for language, bank in BANKS.items():
        assert bank.customer.keys() == reference.customer.keys(), language
        assert bank.bot.keys() == reference.bot.keys(), language
        for table in ("amounts", "durations", "windows", "years"):
            assert getattr(bank, table).keys() == getattr(reference, table).keys(), (language, table)
        for key, variants in bank.customer.items():
            wanted = {frozenset(slots.findall(v)) for v in reference.customer[key]}
            assert {frozenset(slots.findall(v)) for v in variants} == wanted, (language, key)
        for key, text in bank.bot.items():
            assert set(slots.findall(text)) == set(slots.findall(reference.bot[key])), (language, key)


# --- build, freeze, verify ---------------------------------------------------


def test_files_on_disk_and_the_generator_match_the_frozen_hashes():
    assert build.verify(DATA) == []
    frozen = json.loads((DATA / build.FROZEN_FILE).read_text(encoding="utf-8"))
    assert frozen["count"] == 144 and frozen["frozen_on"]
    assert frozen["history"][-1]["sha256"][build.GOLD_FILE] == frozen["files"][build.GOLD_FILE]["sha256"]


def test_every_frozen_hash_is_logged_in_the_changelog():
    frozen = json.loads((DATA / build.FROZEN_FILE).read_text(encoding="utf-8"))
    changelog = (DATA / "CHANGELOG.md").read_text(encoding="utf-8")
    for entry in frozen["history"]:
        assert entry["sha256"][build.GOLD_FILE] in changelog


def test_build_is_byte_identical_under_another_hash_seed():
    code = "from samajh.scenarios import build; print(build.generate().sha256())"
    outputs = {
        subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO,
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        for seed in ("0", "1", "12345")
    }
    assert len(outputs) == 1
    assert str(build.generate().sha256()) == outputs.pop().strip()


def test_verify_fails_when_a_file_is_edited(tmp_path):
    copy = tmp_path / "scenarios"
    shutil.copytree(DATA, copy)
    gold = copy / build.GOLD_FILE
    gold.write_bytes(gold.read_bytes().replace(b'"clear"', b'"flag_for_review"', 1))
    problems = build.verify(copy)
    assert len(problems) == 1 and build.GOLD_FILE in problems[0] and "on disk" in problems[0]


def test_verify_fails_without_a_freeze(tmp_path):
    build.write(tmp_path)
    assert build.verify(tmp_path) == [f"{build.FROZEN_FILE} is missing: the set is not frozen"]


def test_build_refuses_to_replace_a_frozen_file_that_would_change(tmp_path):
    copy = tmp_path / "scenarios"
    shutil.copytree(DATA, copy)
    frozen_path = copy / build.FROZEN_FILE
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    frozen["files"][build.GOLD_FILE]["sha256"] = "0" * 64
    frozen_path.write_text(json.dumps(frozen), encoding="utf-8")
    with pytest.raises(SystemExit, match="refusing to write"):
        build.write(copy)
    build.write(copy, force=True)


def test_verify_command_exits_non_zero_on_a_mismatch(tmp_path):
    copy = tmp_path / "scenarios"
    shutil.copytree(DATA, copy)
    command = [sys.executable, "-m", "samajh.scenarios", "--dir", str(copy), "verify"]
    assert subprocess.run(command, cwd=REPO, check=False, capture_output=True).returncode == 0
    with (copy / build.CALLS_FILE).open("ab") as handle:
        handle.write(b"\n")
    assert subprocess.run(command, cwd=REPO, check=False, capture_output=True).returncode == 1


FIRST_FREEZE_GOLD_SHA256 = "08b147008d07c0ec917bee3ee16f16e77fa9abd24a5defbee014b6b712264405"


def test_freeze_history_starts_at_the_first_freeze():
    """Deleting FROZEN.json and freezing again would restart the history; this pins where it began."""
    frozen = json.loads((DATA / build.FROZEN_FILE).read_text(encoding="utf-8"))
    assert frozen["history"][0]["sha256"][build.GOLD_FILE] == FIRST_FREEZE_GOLD_SHA256
    assert frozen["version"] == len(frozen["history"])


def test_datasheet_counts_are_the_generated_counts():
    from samajh.scenarios.__main__ import STATS_BEGIN, STATS_END, stats

    readme = (DATA / "README.md").read_text(encoding="utf-8")
    block = readme.split(STATS_BEGIN)[1].split(STATS_END)[0].strip()
    assert block == stats(DATA).strip()


# --- an evasive customer gives no answer -------------------------------------

YES_WORDS = {
    Language.hi: ("हाँ", "जी हाँ"),
    Language.hi_en: ("हाँ", "जी हाँ", "Yes"),
    Language.ta: ("ஆமா", "சரி"),
    Language.kn: ("ಹೌದು", "ಸರಿ"),
}


def test_an_evasive_customer_never_says_yes_to_a_question_a_yes_would_answer():
    closed = {Question.required_for_loan, Question.provider_choice, Question.cancel_window, Question.features}
    checked = 0
    for s in SCENARIOS:
        if s.beliefs[0].kind != "evasive":
            continue
        turns = CALLS[s.id].teach_back.transcript.turns
        for bot, reply in zip(turns[::2], turns[1::2], strict=True):
            if bot.asks in closed:
                assert not reply.text.startswith(YES_WORDS[s.language]), (s.id, reply.text)
                checked += 1
    assert checked == 12  # C03 in four languages: required, cancel, money back


def test_a_customer_who_does_not_know_what_they_agreed_to_names_no_method():
    method_words = ("साइन", "दस्तख़त", "sign", "ओटीपी", "OTP", "கையெழுத்து", "ஓடிபி", "ಸಹಿ", "ಒಟಿಪಿ")
    for s in SCENARIOS:
        if s.beliefs[0].consent_given == "dont_know":
            (consent,) = (
                reply
                for bot, reply in zip(
                    CALLS[s.id].teach_back.transcript.turns[::2],
                    CALLS[s.id].teach_back.transcript.turns[1::2],
                    strict=True,
                )
                if bot.asks is Question.consent
            )
            assert not any(word in consent.text for word in method_words), (s.id, consent.text)


# --- gold against the rule engine, after the freeze --------------------------

# Gold and the engine agree on every scenario on perfect input since version 3. A change here
# means the engine or the gold changed: update CHANGELOG.md and the datasheet with it.
PREMIUM_DONT_KNOW = {f"{base}-{language.value}" for base in ("U09", "U10") for language in Language}


@pytest.mark.parametrize("path", ["beliefs", "extraction"])
def test_gold_and_rule_engine_agree_on_perfect_input(path):
    from samajh.scenarios import consistency

    comparisons = consistency.check(SCENARIOS, tuple(CALLS.values()), path)
    differing = {c.scenario_id for c in comparisons if not (c.agrees and c.unclear_agrees)}
    assert differing == set()
    engine_flags_on_clear_gold = [
        c.scenario_id for c, s in zip(comparisons, SCENARIOS, strict=True) if s.gold.verdict is Verdict.clear and c.engine_flags
    ]
    assert engine_flags_on_clear_gold == []


def test_a_customer_who_does_not_know_the_premium_is_flagged_on_premium():
    """Coordinator decision of 2026-11-10: "I don't know what it cost" is a flag, not unclear."""
    cases = [s for s in SCENARIOS if s.beliefs[0].premium_inr == "dont_know"]
    assert {s.id for s in cases} == PREMIUM_DONT_KNOW
    for s in cases:
        assert ("P1", RuleId.premium) in s.gold.flag_keys(), s.id
        assert ("P1", RuleId.premium) not in s.gold.unclear_keys(), s.id
        assert s.gold.verdict is Verdict.flag_for_review, s.id
