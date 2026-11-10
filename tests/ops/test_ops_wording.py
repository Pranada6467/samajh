from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from opskit import COMPLETED, SOLD, coached, loan, open_batch, phone_case, put_case

from samajh.ops import wording
from samajh.ops.batch import load_batch
from samajh.ops.model import AttemptOutcome, Decision, FinalStatus
from samajh.ops.report import build_report
from samajh.ops.sessions import ingest
from samajh.ops.store import OpsStore
from samajh.ops.views import attempt_log_view, batch_view, case_view, queue_view
from samajh.types import GapReason, RuleId, Tier

REPO = Path(__file__).resolve().parents[2]
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
        "Findings: features and risks",
        "No finding was counted in this batch",
        "each finding is listed",
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
        Tier.clear: "Nothing to refer",
    }
    assert wording.DECISION_LABEL == {
        Decision.concern_supported: "Concern supported by the file (reviewer's view)",
        Decision.concern_not_supported: "Concern not supported by the file (reviewer's view)",
        Decision.call_customer: "Call the customer",
        Decision.needs_information: "Needs more information",
    }
    assert set(wording.GROUP) == set(wording.SERIOUSNESS) == set(RuleId)
    assert wording.SERIOUSNESS[RuleId.kind] < wording.SERIOUSNESS[RuleId.term]
    assert wording.may_engage("85G") == "may engage para 85G"
    assert wording.may_engage("internal") is None


def _every_view(store: OpsStore) -> list:
    """Every view a reviewer can open on this store: batch, queue, each case page, attempt log, report."""
    batch = load_batch(store)
    queue = queue_view(batch)
    views = [batch_view(batch), queue, attempt_log_view(batch), build_report(store, batch.meta.created_at)]
    return views + [case_view(batch, item.case_id) for item in queue.items]


def _phone_state(root: Path) -> OpsStore:
    """A hand-built batch with a phone referral, a referred call outside the sample, a phone attempt
    that ended early and a session folder left out."""
    a, b = loan(1), loan(2)
    store, _ = open_batch(root / "ops", [a, b], SOLD + timedelta(days=3))
    sessions = root / "sessions"
    put_case(sessions, phone_case(store, a, coached(a, COMPLETED), SOLD + timedelta(days=5)))
    put_case(sessions, phone_case(store, b, None, SOLD + timedelta(days=6), "no_response"))
    put_case(sessions, phone_case(store, b, coached(b, COMPLETED), None))  # no book block: outside
    (sessions / "20261110T000000-00000000beef").mkdir(parents=True)
    found = ingest(store, sessions, lambda record_id: None)
    assert (len(found.linked), len(found.outside), len(found.skipped)) == (2, 1, 1), found
    return store


def test_every_label_in_every_generated_view_is_allowed(
    store: OpsStore, mixed_state: Path, tmp_path: Path
) -> None:
    """Demo batch, mixed-rate batch (intervals withheld) and a batch with phone sessions in it."""
    stores = [store, OpsStore(mixed_state / "ops"), _phone_state(tmp_path)]
    views = [view for each in stores for view in _every_view(each)]
    assert len(views) > 15
    assert any(view.__class__.__name__ == "CaseView" and not view.call.simulated for view in views)
    skip = frozenset(CUSTOMER_WORDS)
    shown = [s for view in views for s in _strings(view.model_dump(mode="json"), skip)]
    assert [s for s in shown if wording.banned_in(s)] == []
    # A bare "established" reads as a conclusion about the sale; the decisions say whose view they are.
    assert [s for s in shown if re.search(r"\bestablished\b", s, re.IGNORECASE)] == []


@pytest.mark.parametrize(
    "path",
    sorted(p for p in (REPO / "web" / "review").iterdir() if p.suffix in (".js", ".html"))
    + [REPO / "data" / "loanbook" / "README.md"],
    ids=lambda p: p.name,
)
def test_the_review_pages_and_the_book_readme_hold_no_banned_word(path: Path) -> None:
    """The whole file, code and text: a page heading or a README line that says "finding" fails."""
    text = path.read_text(encoding="utf-8")
    assert [(m, line) for line in text.splitlines() for m in wording.banned_in(line)] == []


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
