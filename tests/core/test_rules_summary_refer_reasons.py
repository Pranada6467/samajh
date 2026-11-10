"""Every refer-tier flag reason has a summary line: `summarise` never raises on one (P3c fix F)."""

from test_rules_engine import product, record, run, said

from samajh.rules import summarise
from samajh.rules.summary import ISSUE
from samajh.types import FLAG_TIER, FlagReason, Tier

# Keyed per flag in `summary._key`, not through ISSUE.
KEYED_IN_KEY = {FlagReason.feature_contradicted, FlagReason.sale_concern, FlagReason.answers_conflict}


def test_every_refer_tier_reason_has_an_issue_or_its_own_branch():
    refer = {reason for reason, tier in FLAG_TIER.items() if tier is Tier.refer}
    assert refer - set(ISSUE) - KEYED_IN_KEY == set()


def test_a_confirmed_cover_figure_that_differs_gets_one_refer_line():
    result = run({}, {"cover_inr": said(100_000), "cover_readback": said(True)})
    assert [f.reason for f in result.all_flags()] == [FlagReason.cover_differs_confirmed]
    assert result.tier is Tier.refer
    (line,) = summarise(record(product()), result).lines
    assert line.tier is Tier.refer
    assert line.title == (
        "Customer said ₹1,00,000 and confirmed it at the read-back; the record shows cover of ₹5,00,000."
    )
    assert line.record_value == "cover ₹5,00,000"
