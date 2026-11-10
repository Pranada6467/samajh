from __future__ import annotations

import threading
from datetime import timedelta
from pathlib import Path

import pytest
from opskit import (
    COMPLETED,
    DECLINED_AFTER_CHECKS,
    NO_ANSWER,
    NOW,
    SOLD,
    coached,
    customer,
    loan,
    open_batch,
    other_consent_method,
    run_batch,
)

from samajh.ops import book as books
from samajh.ops.__main__ import main
from samajh.ops.batch import load_batch
from samajh.ops.model import Decision, FinalStatus, Tier
from samajh.ops.report import build_report
from samajh.ops.simulate import run_draw, scripted_analysis
from samajh.ops.store import NoBatch, OpsStore
from samajh.ops.views import DispositionIn, Proportion, queue_view, record_disposition
from samajh.scenarios.model import DONT_KNOW
from samajh.types import RuleId


def _files(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_running_the_whole_batch_again_changes_nothing(state: Path) -> None:
    before = _files(state)
    assert main(["demo", "--state", str(state)]) == 0
    assert _files(state) == before


def test_a_call_already_saved_is_not_analysed_again(store: OpsStore) -> None:
    def must_not_run(call, record):
        raise AssertionError("analysed a call that was already saved")

    customers = {c.loan_id: c for c in books.generate_book(85)[2]}
    for drawn in store.draws():
        run_draw(store, drawn, customers, must_not_run)


def test_a_call_that_cannot_be_analysed_is_left_for_the_next_run(tmp_path: Path) -> None:
    loans = [loan(1), loan(2)]
    customers = {c.loan_id: c for c in (customer(loans[0], COMPLETED), customer(loans[1], COMPLETED))}
    store, drawn = open_batch(tmp_path / "ops", loans, SOLD + timedelta(days=5))

    def fails_on_the_second(call, record):
        if record.loan_id == loans[1].record.loan_id:
            raise RuntimeError("model output was not valid")
        return scripted_analysis(call, record)

    with pytest.raises(RuntimeError, match="1 call"):
        run_draw(store, drawn, customers, fails_on_the_second)
    statuses = {s.loan.record.loan_id: s.status for s in load_batch(store).sampled}
    assert statuses == {
        loans[0].record.loan_id: FinalStatus.completed,
        loans[1].record.loan_id: FinalStatus.not_attempted,
    }
    run_draw(store, drawn, customers, scripted_analysis)
    assert all(s.status is FinalStatus.completed for s in load_batch(store).sampled)


def test_the_funnel_of_the_demo_batch_adds_up(store: OpsStore) -> None:
    report = build_report(store, NOW)
    funnel = report.funnel
    stages = {row.key: row.value for row in funnel.stages}
    assert funnel.sampled == 80 == report.batch.sampled
    assert all(row.value.n == funnel.sampled for row in (*funnel.stages, *funnel.exits))
    assert stages["completed"].count + sum(row.value.count for row in funnel.exits) == funnel.sampled
    assert {row.key for row in funnel.exits} == {s.value for s in FinalStatus} - {"completed"}
    counts = [stages[k].count for k in ("attempted", "reached", "right_party_confirmed", "completed")]
    assert counts == sorted(counts, reverse=True)
    assert funnel.attempts == len(store.attempts()) >= stages["attempted"].count
    assert sum(row.value.count for row in report.tiers) == stages["completed"].count == report.batch.completed
    assert all(d.verified for d in report.draws)
    assert report.paragraph == "85Y" and report.period_label == "1 January 2027 to 30 June 2027"
    for breakdown in report.breakdowns:
        assert sum(row.sampled for row in breakdown.rows) == funnel.sampled
        assert sum(row.completed for row in breakdown.rows) == stages["completed"].count


def test_a_hand_built_batch_gives_the_counts_and_intervals_worked_out_by_hand(tmp_path: Path) -> None:
    a, b, c, d, e = (loan(n) for n in range(1, 6))
    customers = [
        customer(a, COMPLETED),  # states everything: no finding
        coached(b, NO_ANSWER, COMPLETED),  # reached on the second attempt: referred
        customer(c, NO_ANSWER, NO_ANSWER, NO_ANSWER),  # never answers
        customer(d, DECLINED_AFTER_CHECKS),
        customer(e, COMPLETED, cover_inr=DONT_KNOW),  # understanding gap
    ]
    store = run_batch(tmp_path / "ops", [a, b, c, d, e], customers, SOLD + timedelta(days=10))
    report = build_report(store, NOW)

    funnel = report.funnel
    assert (funnel.sampled, funnel.attempts) == (5, 8)
    assert {row.key: row.value.count for row in funnel.stages} == {
        "attempted": 5,
        "reached": 4,
        "right_party_confirmed": 4,
        "completed": 3,
    }
    assert {row.key: row.value.count for row in funnel.exits if row.value.count} == {
        "unreachable": 1,
        "declined": 1,
    }
    completed = funnel.stages[-1].value  # 3 of 5: Wilson 95% is 0.2307 to 0.8824
    assert (completed.count, completed.n, completed.share) == (3, 5, 0.6)
    assert completed.low == pytest.approx(0.2307, abs=5e-4) and completed.high == pytest.approx(
        0.8824, abs=5e-4
    )

    tiers = {row.tier: row.value for row in report.tiers}
    assert {tier: value.count for tier, value in tiers.items()} == {
        Tier.refer: 1,
        Tier.understanding_gap: 1,
        Tier.incomplete: 0,
        Tier.clear: 1,
    }
    one_of_three = tiers[Tier.refer]  # 1 of 3: Wilson 95% is 0.0615 to 0.7923
    assert one_of_three.n == 3 and one_of_three.share == pytest.approx(1 / 3)
    assert one_of_three.low == pytest.approx(0.0615, abs=5e-4)
    assert one_of_three.high == pytest.approx(0.7923, abs=5e-4)

    findings = {f.rule_id: f for f in report.findings}
    assert RuleId.evidence not in findings and len(findings) == len(RuleId) - 1
    flagged = {rule: (f.flagged.count, f.flagged.n, f.undecided, f.referred) for rule, f in findings.items()}
    assert flagged.pop(RuleId.cover) == (1, 3, 0, 0)
    assert flagged.pop(RuleId.sale_conduct) == (1, 3, 0, 1)
    assert set(flagged.values()) == {(0, 3, 0, 0)}
    assert findings[RuleId.cover].understanding and findings[RuleId.cover].may_engage == "may engage para 85Y"
    assert (
        not findings[RuleId.sale_conduct].understanding and findings[RuleId.sale_conduct].may_engage is None
    )
    assert report.findings[0].rule_id is RuleId.cover  # understanding rules first, most common first

    (item,) = report.policy_review
    assert (
        item.sentence
        == "1 of 3 customers who completed the call did not state the cover amount on the record"
    )
    assert item.highest is None  # no branch or channel has 5 completed calls

    assert report.timing.first_attempt_days == (10, 10, 10)
    assert (report.timing.completed_within_window.count, report.timing.attempts_after_window) == (3, 0)
    assert {row.key: row.value.count for row in report.referrals} == {
        "established": 0,
        "not_established": 0,
        "call_customer": 0,
        "needs_information": 0,
        "awaiting": 1,
    }
    assert report.established_of_decided == Proportion(count=0, n=0, share=None, low=None, high=None)
    assert (report.batch.referred, report.batch.awaiting_review) == (1, 1)


def test_attempts_after_day_30_are_counted_as_outside_the_window(tmp_path: Path) -> None:
    a = loan(1)
    store = run_batch(tmp_path / "ops", [a], [customer(a, NO_ANSWER, COMPLETED)], SOLD + timedelta(days=30))
    timing = build_report(store, NOW).timing
    assert timing.first_attempt_days == (30, 30, 30)
    assert timing.attempts_after_window == 1
    assert (timing.completed_within_window.count, timing.completed_within_window.n) == (0, 1)


def test_the_queue_holds_only_referrals_open_first_then_severity_then_days_left(tmp_path: Path) -> None:
    week = timedelta(days=7)
    old_high, new_high, old_medium, gap, decided, none = (
        loan(1, SOLD),
        loan(2, SOLD + week),
        loan(3, SOLD - week),
        loan(4, SOLD),
        loan(5, SOLD - week),
        loan(6, SOLD),
    )
    customers = [
        coached(old_high, COMPLETED),
        coached(new_high, COMPLETED),
        other_consent_method(old_medium, COMPLETED),
        customer(gap, COMPLETED, cover_inr=DONT_KNOW),
        coached(decided, COMPLETED),
        customer(none, COMPLETED),
    ]
    loans = [old_high, new_high, old_medium, gap, decided, none]
    store = run_batch(tmp_path / "ops", loans, customers, SOLD + timedelta(days=14))

    def case_of(of) -> str:
        return next(i.case_id for i in queue_view(load_batch(store)).items if i.loan_id == of.record.loan_id)

    def decide(of, decision: Decision) -> None:
        record_disposition(
            store, case_of(of), DispositionIn(decision=decision, note="seen", reviewer="R1"), NOW
        )

    decide(decided, Decision.not_established)
    decide(new_high, Decision.call_customer)  # not a final decision: the case stays open

    items = queue_view(load_batch(store)).items
    assert [i.loan_id for i in items] == [b.record.loan_id for b in (old_high, new_high, old_medium, decided)]
    assert [i.severity for i in items] == ["high", "high", "medium", "high"]
    assert [i.days_left_in_window for i in items] == [16, 23, 9, 9]
    assert [i.disposition.final if i.disposition else None for i in items] == [None, False, None, True]
    assert items[0].headline == "How the sale was handled: customer says they were told what to answer."
    assert items[0].may_engage == () and items[2].may_engage == ("may engage para 85G",)
    assert all(i.simulated for i in items)


def test_the_store_is_idempotent_and_refuses_another_book_or_a_conflicting_entry(store: OpsStore) -> None:
    meta = store.meta()
    assert store.init(meta.book, store.book(), meta.period_start, meta.period_end, NOW) == meta
    other_meta, other_loans, _ = books.generate_book(86)
    with pytest.raises(ValueError, match="another book"):
        store.init(other_meta, other_loans, meta.period_start, meta.period_end, NOW)

    attempts, draws = store.attempts(), store.draws()
    store.add_attempt(attempts[0])
    store.add_draw(draws[0])
    assert (store.attempts(), store.draws()) == (attempts, draws)
    with pytest.raises(ValueError, match="different entry"):
        store.add_attempt(attempts[0].model_copy(update={"day_since_sale": 99}))
    with pytest.raises(ValueError, match="another book"):
        store.add_draw(draws[0].model_copy(update={"book_sha256": other_meta.sha256}))


@pytest.mark.parametrize("call_id", ["../batch", "a/b", "..", "", "x.json", "a b"])
def test_a_call_id_that_is_not_a_plain_name_is_refused(store: OpsStore, call_id: str) -> None:
    with pytest.raises(ValueError, match="not a call id"):
        store.call(call_id)


def test_an_empty_store_says_it_has_no_batch(tmp_path: Path) -> None:
    with pytest.raises(NoBatch):
        load_batch(OpsStore(tmp_path / "ops"))


def test_appends_from_many_threads_are_all_kept_once(store: OpsStore) -> None:
    template = store.attempts()[0]
    new = [
        template.model_copy(update={"attempt_id": f"D-test/{template.loan_id}/{n}", "number": n})
        for n in range(50, 90)
    ]
    before = len(store.attempts())
    threads = [threading.Thread(target=store.add_attempt, args=(a,)) for a in new + new]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(store.attempts()) == before + len(new)
