"""The evaluation's own arithmetic: what counts as a false clear, a field, a flag."""

import devset
import e1
from scenario import GoldLabels
from scoring import Tally, by_language, score_case, summarise

from samajh.rules import evaluate, to_beliefs
from samajh.types import RawExtraction, RuleId, Verdict

SCENARIOS = {s.id: s for s in devset.scenarios()}


def beliefs(scenario, raw=None):
    return to_beliefs(raw or scenario.gold_raw, scenario.record, scenario.transcript)


def scored(scenario, raw: RawExtraction | None = None, error: str | None = None):
    """Score an extraction of `scenario` as if the pipeline had produced it."""
    if error:
        return score_case(
            scenario.id, scenario.language.value, scenario.gold, beliefs(scenario), None, None, error
        )
    got = beliefs(scenario, raw)
    return score_case(
        scenario.id,
        scenario.language.value,
        scenario.gold,
        beliefs(scenario),
        evaluate(scenario.record, got),
        got,
    )


def with_answers(scenario, **changes) -> RawExtraction:
    product = scenario.gold_raw.products[0].model_dump() | changes
    return RawExtraction.model_validate(scenario.gold_raw.model_dump() | {"products": [product]})


def test_gold_scored_against_itself_is_perfect():
    summary = summarise(scored(s) for s in SCENARIOS.values())
    assert (summary.false_clear.hits, summary.false_clear.n) == (0, 13)
    assert (summary.false_alarm.hits, summary.false_alarm.n) == (0, 7)
    assert summary.all_fields.hits == summary.all_fields.n > 250
    assert summary.precision().rate == summary.recall().rate == 1.0


def test_a_misled_customer_read_as_fine_is_a_false_clear():
    fd = SCENARIOS["hi-02"]  # gold: flag_for_review
    clear = SCENARIOS["hi-01"]
    as_if_clear = score_case(fd.id, "hi", fd.gold, None, clear.perfect, None)
    assert as_if_clear.false_clear
    summary = summarise([as_if_clear])
    assert (summary.false_clear.hits, summary.false_clear.n) == (1, 1)
    assert summary.false_alarm.n == 0
    assert summary.recall().hits == 0 and summary.recall().n == len(fd.gold.flags)


def test_an_unclear_gold_read_as_clear_is_a_false_clear_too():
    unclear = SCENARIOS["en-05"]
    assert unclear.gold.verdict is Verdict.unclear_needs_human
    assert score_case(unclear.id, "hi-en", unclear.gold, None, SCENARIOS["en-01"].perfect, None).false_clear


def test_an_extractor_error_is_never_clear_and_is_counted():
    clear = scored(SCENARIOS["hi-01"], error="ExtractionFailed: boom")
    flagged = scored(SCENARIOS["hi-02"], error="ExtractionFailed: boom")
    summary = summarise([clear, flagged])
    assert summary.errors == 2
    assert summary.false_clear.hits == 0
    assert (summary.false_alarm.hits, summary.false_alarm.n) == (1, 1)
    assert summary.case_verdict.hits == 0
    assert summary.confusion[("clear", "error")] == 1


def test_one_wrong_field_is_one_miss_and_shows_up_as_a_flag_error():
    scenario = SCENARIOS["hi-01"]
    wrong = with_answers(
        scenario,
        kind={
            "status": "stated",
            "value": "deposit",
            "evidence": scenario.gold_raw.products[0].kind.evidence,
        },
    )
    score = scored(scenario, wrong)
    assert [f.name for f in score.fields if not f.ok] == ["kind"]
    assert score.verdict is Verdict.flag_for_review and not score.false_clear
    summary = summarise([score])
    assert summary.flag_fp[RuleId.kind] == 1 and summary.precision(RuleId.kind).rate == 0.0
    assert (summary.false_alarm.hits, summary.false_alarm.n) == (1, 1)


def test_a_question_the_call_never_asked_is_not_a_field():
    scenario = SCENARIOS["hi-01"]  # the provider-choice question is not asked on this call
    names = [f.name for f in scored(scenario).fields]
    assert "provider_choice_offered" not in names
    assert "kind" in names and "recall_items" in names


def test_a_repeated_deposit_claim_is_not_an_error_but_a_new_one_is():
    fd = SCENARIOS["hi-02"]  # the customer calls the product an FD in the kind answer
    quote = fd.gold_raw.products[0].kind.evidence
    repeat = with_answers(fd, volunteered_claims=[{"claim": "is_deposit", "evidence": quote}])
    assert all(f.ok for f in scored(fd, repeat).fields)
    insured = SCENARIOS["hi-01"]
    quote = insured.gold_raw.products[0].kind.evidence
    invented = with_answers(insured, volunteered_claims=[{"claim": "is_deposit", "evidence": quote}])
    assert [f.name for f in scored(insured, invented).fields if not f.ok] == ["volunteered_claims"]


def test_languages_are_reported_apart_and_empty_ones_left_out():
    groups = by_language(scored(SCENARIOS[id]) for id in ("hi-01", "ta-02"))
    assert list(groups) == ["all", "hi", "ta"]
    assert groups["hi"].false_clear.n == 0 and groups["ta"].false_clear.n == 1


def test_a_rate_over_nothing_is_not_a_number():
    assert Tally().rate is None
    assert str(Tally()) == "n/a (n=0)"
    assert str(Tally(1, 3)) == "33.3% (1/3)"


def test_gold_labels_come_from_a_case_result():
    labels = GoldLabels.of(SCENARIOS["hi-02"].perfect)
    assert labels.verdict is Verdict.flag_for_review
    assert ("P1", RuleId.kind) in labels.flags
    assert labels.products == (("P1", Verdict.flag_for_review),)


def test_an_extractor_error_counts_every_gold_field_as_wrong():
    """A call with no extraction must not drop out of the field accuracy."""
    scenario = SCENARIOS["hi-01"]
    fine, failed = scored(scenario), scored(scenario, error="ExtractionFailed: boom")
    assert [f.name for f in failed.fields] == [f.name for f in fine.fields]
    assert not any(f.ok for f in failed.fields)
    summary = summarise([fine, failed])
    assert (summary.all_fields.hits, summary.all_fields.n) == (len(fine.fields), 2 * len(fine.fields))


# --- E1: strata and counts --------------------------------------------------------------------


def test_e1_strata_follow_the_customer_and_the_scripted_yes_no_outcome():
    assert e1.stratum(True, "truthful", True) == "informed"
    assert e1.stratum(False, "coached", True) == "coached"
    assert e1.stratum(False, "acquiescent", True) == "acquiescent"
    assert e1.stratum(False, "truthful", True) == "never_asked"
    assert e1.stratum(False, "truthful", False) == "asked"


def test_e1_reports_each_stratum_apart_and_counts_whole_base_cases():
    def row(base, stratum, yes_no, teach_back, gold_clear=False):
        return e1.E1Row(base, stratum, gold_clear, yes_no, teach_back, teach_back, True)

    rows = [
        row("C01", "coached", False, True),
        row("C01", "coached", False, False),  # one language of C01 missed by the teach-back call
        row("C02", "coached", False, True),
        row("U03", "asked", True, True),
        row("N01", "informed", False, True, gold_clear=True),
    ]
    lines = e1.table(rows).splitlines()
    assert len(lines) == 2 + 3  # header, rule, one line per stratum present: nothing pooled
    coached = next(line for line in lines if line.startswith("| coached"))
    assert "| 3 (2) |" in coached
    assert "| 0/3 calls (0/2 base cases in every language) |" in coached
    assert "| 2/3 calls (1/2 base cases in every language) |" in coached
    informed = next(line for line in lines if line.startswith("| informed"))
    assert "| clear |" in informed and "1/1 calls" in informed
