"""The development set is consistent: its gold extraction gives the verdict its author expected."""

import devset
import pytest

from samajh.types import Verdict

SCENARIOS = {s.id: s for s in devset.scenarios()}
EXPECTED = devset.expectations()


@pytest.mark.parametrize("id", SCENARIOS)
def test_gold_extraction_gives_the_expected_verdict_and_flags(id):
    verdict, flagged_rules = EXPECTED[id]
    perfect = SCENARIOS[id].perfect
    assert perfect.verdict is verdict
    assert {f.rule_id for f in perfect.all_flags()} == flagged_rules


def test_the_set_covers_four_languages_and_all_three_verdicts():
    assert len(SCENARIOS) == 20
    by_language = [s.language.value for s in SCENARIOS.values()]
    assert {language: by_language.count(language) for language in set(by_language)} == {
        "hi": 5, "hi-en": 5, "ta": 5, "kn": 5,
    }  # fmt: skip
    assert {s.gold.verdict for s in SCENARIOS.values()} == set(Verdict)


def test_no_gold_quote_is_ungrounded():
    for scenario in SCENARIOS.values():
        reasons = {g.reason.value for g in scenario.perfect.all_gaps()}
        assert "quote_not_grounded" not in reasons, scenario.id
        assert "value_not_parsed" not in reasons, scenario.id


def test_ids_are_synthetic():
    for scenario in SCENARIOS.values():
        assert scenario.record.loan_id.startswith("LN-DEV-")
        assert "synthetic" in scenario.record.products[0].provider
