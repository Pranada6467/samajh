from __future__ import annotations

from pathlib import Path

import pytest
from serverkit import FakeSpeech
from starlette.testclient import TestClient

from samajh.ops import wording
from samajh.ops.batch import load_batch
from samajh.ops.model import Attempt, AttemptOutcome, CallRecord, Draw, PhoneSession
from samajh.ops.simulate import scripted_analysis
from samajh.ops.store import OpsStore
from samajh.ops.views import AttemptLogView, BatchView, CaseView, QueueView, ReportView
from samajh.server import create_app

SESSION_ID = "20261110T142233-9f2c4e1ab07d"


def _client(state: Path) -> TestClient:
    return TestClient(create_app(gnani=FakeSpeech(), state=state, web_dir=None, clips_dir=None))


@pytest.fixture
def client(state: Path) -> TestClient:
    return _client(state)


def _decide(client: TestClient, case_id: str, **body) -> CaseView:
    reply = client.post(f"/api/review/cases/{case_id}/disposition", json=body)
    assert reply.status_code == 200, reply.text
    return CaseView.model_validate(reply.json())


def test_every_page_gets_the_contract_it_reads(client: TestClient) -> None:
    batch = BatchView.model_validate(client.get("/api/review/batch").json())
    queue = QueueView.model_validate(client.get("/api/review/queue").json())
    log = AttemptLogView.model_validate(client.get("/api/review/attempts").json())
    draws = [Draw.model_validate(d) for d in client.get("/api/review/draws").json()]
    report = ReportView.model_validate(client.get("/api/review/report").json())

    assert batch.meta.simulated and batch.simulated_notice == wording.SIMULATED_NOTICE
    assert batch.meta.book.synthetic and report.batch == batch
    assert len(queue.items) == batch.referred == batch.awaiting_review > 0
    assert len(log.loans) == batch.sampled == sum(len(d.drawn) for d in draws)
    assert [d.draw_id for d in log.draws] == [d.draw_id for d in draws]
    assert all(d.verified for d in log.draws)
    assert {i.case_id for i in queue.items} == {loan.case_id for loan in log.loans if loan.case_id}
    assert all(loan.tier == "refer" for loan in log.loans if loan.case_id)
    assert all((loan.tier is not None) == (loan.status == "completed") for loan in log.loans)
    assert report.limits == wording.LIMITS

    case = CaseView.model_validate(client.get(f"/api/review/cases/{queue.items[0].case_id}").json())
    assert case.tier == "refer" and case.tier_label == "Referred for review"
    assert case.refer_lines and case.severity == queue.items[0].severity
    assert all(line.tier == "refer" for line in case.refer_lines)
    assert case.refer_lines[0].title == queue.items[0].headline
    assert case.call.simulated and case.call.recording_url is None
    assert case.call.analysis == "scripted extraction, no model"
    assert [d.label for d in case.decisions] == [
        "Established by reviewer",
        "Not established",
        "Call the customer",
        "Needs more information",
    ]
    cited = {line.quote.turn_id for line in (*case.refer_lines, *case.other_lines) if line.quote}
    assert cited and {t.turn_id for t in case.transcript if t.cited} == cited
    assert "dob" not in client.get(f"/api/review/cases/{case.case_id}").text


def test_a_server_with_no_batch_says_so(tmp_path: Path) -> None:
    client = _client(tmp_path / "empty")
    for path in ("batch", "queue", "attempts", "draws", "report", "cases/TEST-CALL-x"):
        reply = client.get(f"/api/review/{path}")
        assert reply.status_code == 409, path
        assert "no review batch yet" in reply.json()["error"]["message"]
    body = {"decision": "established", "note": "n", "reviewer": "r"}
    assert client.post("/api/review/cases/TEST-CALL-x/disposition", json=body).status_code == 409


def test_only_a_referred_call_is_a_case(client: TestClient, store: OpsStore) -> None:
    not_referred = next(s.call.call_id for s in load_batch(store).completed if not s.referred)
    body = {"decision": "established", "note": "n", "reviewer": "r"}
    for case_id in (not_referred, "TEST-CALL-SYN-GL-000000-9999-tb", "..%2Fbatch"):
        assert client.get(f"/api/review/cases/{case_id}").status_code == 404
        assert client.post(f"/api/review/cases/{case_id}/disposition", json=body).status_code == 404
    assert store.dispositions() == ()


def test_a_decision_persists_and_a_later_one_replaces_it_while_the_history_keeps_both(
    client: TestClient, state: Path
) -> None:
    before = ReportView.model_validate(client.get("/api/review/report").json())
    case_id = QueueView.model_validate(client.get("/api/review/queue").json()).items[0].case_id

    first = _decide(
        client, case_id, decision="call_customer", note="  ask about the form  ", reviewer="R. One"
    )
    assert first.disposition.decision == "call_customer" and not first.disposition.final
    assert first.disposition.note == "ask about the form" and len(first.history) == 1

    second = _decide(client, case_id, decision="established", note="customer confirmed", reviewer="R. Two")
    assert second.disposition.decision_label == "Established by reviewer" and second.disposition.final
    assert [d.decision for d in second.history] == ["call_customer", "established"]

    restarted = _client(state)  # a new server over the same state directory
    assert CaseView.model_validate(restarted.get(f"/api/review/cases/{case_id}").json()) == second
    queue = QueueView.model_validate(restarted.get("/api/review/queue").json())
    assert queue.items[-1].case_id == case_id and queue.items[-1].disposition == second.disposition
    assert all(i.disposition is None for i in queue.items[:-1])

    after = ReportView.model_validate(restarted.get("/api/review/report").json())
    rows = {row.key: row.value.count for row in after.referrals}
    referred = before.batch.referred
    assert rows == {
        "established": 1,
        "not_established": 0,
        "call_customer": 0,
        "needs_information": 0,
        "awaiting": referred - 1,
    }
    assert (after.established_of_decided.count, after.established_of_decided.n) == (1, 1)
    assert after.batch.awaiting_review == referred - 1 == before.batch.awaiting_review - 1


@pytest.mark.parametrize(
    "body",
    [
        {"decision": "guilty", "note": "n", "reviewer": "r"},
        {"decision": "established", "note": "   ", "reviewer": "r"},
        {"decision": "established", "note": "n", "reviewer": ""},
        {"decision": "established", "note": "n"},
        {"decision": "established", "note": "n", "reviewer": "r", "case_id": "other"},
    ],
)
def test_an_invalid_decision_is_refused_and_nothing_is_recorded(
    client: TestClient, store: OpsStore, body
) -> None:
    case_id = QueueView.model_validate(client.get("/api/review/queue").json()).items[0].case_id
    assert client.post(f"/api/review/cases/{case_id}/disposition", json=body).status_code == 422
    assert store.dispositions() == ()


def test_a_call_from_a_phone_session_shows_its_audio_offsets_and_recording(
    client: TestClient, store: OpsStore
) -> None:
    """The schema takes a real phone session unchanged: only `source` and the turn times differ."""
    batch = load_batch(store)
    referred = batch.referrals[0]
    untried = next(s for s in batch.sampled if s.status == "unreachable")
    turns = tuple(
        turn.model_copy(update={"start_s": 2.0 * i, "end_s": 2.0 * i + 1.5})
        for i, turn in enumerate(referred.call.transcript.turns)
    )
    # The same words, as if spoken on the phone by the customer of a loan not yet reached.
    transcript = referred.call.transcript.model_copy(
        update={"call_id": SESSION_ID, "loan_id": untried.loan.record.loan_id, "turns": turns}
    )
    source = PhoneSession(session_id=SESSION_ID, recording_sha256="0" * 64)
    attempt = Attempt(
        attempt_id=f"{untried.draw.draw_id}/{untried.drawn.loan_id}/{len(untried.attempts) + 1}",
        draw_id=untried.draw.draw_id,
        loan_id=untried.drawn.loan_id,
        number=len(untried.attempts) + 1,
        at=untried.attempts[-1].at,
        day_since_sale=untried.attempts[-1].day_since_sale + 1,
        language=transcript.language,
        source=source,
        outcome=AttemptOutcome.completed,
        right_party_confirmed=True,
        dialogue_outcome="completed",
        call_id=SESSION_ID,
    )
    result = referred.call.result.model_copy(update={"loan_id": transcript.loan_id, "call_id": SESSION_ID})
    store.save_call(
        CallRecord(
            call_id=SESSION_ID,
            attempt_id=attempt.attempt_id,
            loan_id=attempt.loan_id,
            source=source,
            transcript=transcript,
            result=result,
            analysis=scripted_analysis.__name__,
        )
    )
    store.add_attempt(attempt)

    case = CaseView.model_validate(client.get(f"/api/review/cases/{SESSION_ID}").json())
    assert not case.call.simulated and case.call.source == source
    assert case.call.recording_url == f"/api/sessions/{SESSION_ID}/recording.wav"
    assert [(t.start_s, t.end_s) for t in case.transcript] == [(t.start_s, t.end_s) for t in turns]
    quote = case.refer_lines[0].quote
    spoken = next(t for t in turns if t.id == quote.turn_id)
    assert (quote.start_s, quote.end_s) == (spoken.start_s, spoken.end_s) != (None, None)

    queue = QueueView.model_validate(client.get("/api/review/queue").json())
    assert not next(i for i in queue.items if i.case_id == SESSION_ID).simulated
    log = AttemptLogView.model_validate(client.get("/api/review/attempts").json())
    logged = next(loan for loan in log.loans if loan.loan_id == attempt.loan_id)
    assert logged.status == "completed" and logged.case_id == SESSION_ID
    assert (logged.attempts[-1].session_id, logged.attempts[-1].simulated) == (SESSION_ID, False)
