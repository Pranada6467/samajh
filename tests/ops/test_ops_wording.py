from __future__ import annotations

from collections.abc import Iterator

import pytest

from samajh.ops import wording
from samajh.ops.batch import load_batch
from samajh.ops.model import AttemptOutcome, Decision, FinalStatus, Tier
from samajh.ops.report import build_report
from samajh.ops.store import OpsStore
from samajh.ops.views import case_view, queue_view
from samajh.types import GapReason, RuleId

CUSTOMER_WORDS = {"quote", "text"}  # what the customer or the bot said on the call, shown verbatim


def _strings(value, skip: frozenset[str] = frozenset()) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            if key not in skip:
                yield str(key)
                yield from _strings(item, skip)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _strings(item, skip)


@pytest.mark.parametrize(
    "text",
    [
        "This is mis-selling",
        "Misselling found",
        "the product was mis-sold",
        "a missold policy",
        "mis selling",
        "open a refund case",
        "a refund is owed",
        "Violation of the rule",
        "the lender violated it",
        "a breach",
        "possible fraud",
        "guilty",
        "the verdict",
        "proven",
        "a non-compliant sale",
        "noncompliant",
    ],
)
def test_banned_wording_is_caught_in_any_spelling(text: str) -> None:
    assert wording.banned_in(text)


def test_plain_wording_passes() -> None:
    assert wording.banned_in("Referred for review: the customer described it as a deposit") == []
    assert wording.banned_in("Not established") == []


def test_every_string_in_the_wording_module_is_allowed() -> None:
    public = {name: value for name, value in vars(wording).items() if name.isupper() and name != "BANNED"}
    strings = list(_strings(public))
    assert len(strings) > 80
    assert [s for s in strings if wording.banned_in(s)] == []


def test_every_code_has_its_words_and_the_fixed_labels_are_as_agreed() -> None:
    assert set(wording.RULE_LABEL) == set(wording.RULE_STATEMENT) == set(RuleId)
    assert set(wording.GAP_LABEL) == set(GapReason)
    assert set(wording.OUTCOME_LABEL) == set(AttemptOutcome)
    assert set(wording.STATUS_LABEL) == set(FinalStatus)
    assert wording.TIER_LABEL == {
        Tier.refer: "Referred for review",
        Tier.understanding_gap: "Understanding gap (report only)",
        Tier.incomplete: "Incomplete",
        Tier.clear: "No finding",
    }
    assert wording.DECISION_LABEL == {
        Decision.established: "Established by reviewer",
        Decision.not_established: "Not established",
        Decision.call_customer: "Call the customer",
        Decision.needs_information: "Needs more information",
    }
    assert wording.may_engage("85G") == "may engage para 85G"
    assert wording.may_engage("internal") is None


def test_every_label_in_the_generated_views_is_allowed(store: OpsStore) -> None:
    batch = load_batch(store)
    queue = queue_view(batch)
    views = [build_report(store, batch.meta.created_at), queue]
    views += [case_view(batch, item.case_id) for item in queue.items]
    assert len(views) > 10
    skip = frozenset(CUSTOMER_WORDS)
    shown = [s for view in views for s in _strings(view.model_dump(mode="json"), skip)]
    assert [s for s in shown if wording.banned_in(s)] == []


def test_the_report_says_what_is_simulated_and_what_the_numbers_cannot_show(store: OpsStore) -> None:
    report = build_report(store, load_batch(store).meta.created_at)
    limits = " ".join(report.limits).lower()
    for needed in (
        "synthetic",
        "simulated",
        "phrase banks",
        "no speech",
        "any real lender",
        "sampling",
        "completed the call",
        "request for a person to look",
    ):
        assert needed in limits, needed
    assert "synthetic" in report.batch.simulated_notice
    for item in report.policy_review:
        assert item.sentence.startswith(
            f"{item.value.count} of {item.value.n} customers who completed the call "
        )
