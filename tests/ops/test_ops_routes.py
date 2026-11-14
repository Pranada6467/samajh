from __future__ import annotations

from pathlib import Path

import pytest
from opskit import add_reviewer
from serverkit import FakeSpeech
from starlette.testclient import TestClient

from samajh.ops import wording
from samajh.ops.batch import load_batch
from samajh.ops.model import Draw
from samajh.ops.store import OpsStore
from samajh.ops.views import AttemptLogView, BatchView, CaseView, QueueView, ReportView
from samajh.server import create_app
from samajh.server.review_routes import BAD_DISPOSITION

SESSION_ID = "20261110T142233-9f2c4e1ab07d"


def _client(state: Path, signed_in: bool = True) -> TestClient:
    headers = add_reviewer(state) if signed_in else {}
    return TestClient(
        create_app(gnani=FakeSpeech(), state=state, web_dir=None, clips_dir=None), headers=headers
    )


@pytest.fixture
def client(state: Path) -> TestClient:
    return _client(state)


def _digest(client: TestClient, case_id: str) -> str:
    return client.get(f"/api/review/cases/{case_id}").json()["case_digest"]


def _decide(client: TestClient, case_id: str, **body) -> CaseView:
    body.setdefault("case_digest", _digest(client, case_id))
    reply = client.post(f"/api/review/cases/{case_id}/disposition", json=body)
    assert reply.status_code == 200, reply.text
    return CaseView.model_validate(reply.json())


def test_every_page_gets_the_contract_it_reads(client: TestClient) -> None:
    batch = BatchView.model_validate(client.get("/api/review/batch").json())
    queue = QueueView.model_validate(client.get("/api/review/queue").json())
    log = AttemptLogView.model_validate(client.get("/api/review/attempts").json())
    draws = [Draw.model_validate(d) for d in client.get("/api/review/draws").json()]
    report = ReportView.model_validate(client.get("/api/review/report").json())

    assert batch.simulated and batch.simulated_notice == wording.SIMULATED_NOTICE
    assert batch.access_notice == wording.ACCESS_NOTICE and "token" in batch.access_notice
    assert batch.meta.book.synthetic and report.batch == batch
    assert len(queue.items) == batch.referred == batch.open_cases == report.open_referrals.count > 0
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
        "Concern supported by the file (reviewer's view)",
        "Concern not supported by the file (reviewer's view)",
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
    body = {"decision": "concern_supported", "note": "n", "case_digest": "0" * 64}
    assert client.post("/api/review/cases/TEST-CALL-x/disposition", json=body).status_code == 409


def test_only_a_referred_call_is_a_case(client: TestClient, store: OpsStore) -> None:
    not_referred = next(s.call.call_id for s in load_batch(store).completed if not s.referred)
    body = {"decision": "concern_supported", "note": "n", "case_digest": "0" * 64}
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

    second = _decide(
        client, case_id, decision="concern_supported", note="customer confirmed", reviewer="R. Two"
    )
    assert second.disposition.decision_label == "Concern supported by the file (reviewer's view)"
    assert second.disposition.final
    assert [d.decision for d in second.history] == ["call_customer", "concern_supported"]

    restarted = _client(state)  # a new server over the same state directory
    assert CaseView.model_validate(restarted.get(f"/api/review/cases/{case_id}").json()) == second
    queue = QueueView.model_validate(restarted.get("/api/review/queue").json())
    assert queue.items[-1].case_id == case_id and queue.items[-1].disposition == second.disposition
    assert all(i.disposition is None for i in queue.items[:-1])

    after = ReportView.model_validate(restarted.get("/api/review/report").json())
    rows = {row.key: row.value.count for row in after.referrals}
    referred = before.batch.referred
    assert rows == {
        "concern_supported": 1,
        "concern_not_supported": 0,
        "call_customer": 0,
        "needs_information": 0,
        "none": referred - 1,
    }
    assert (after.supported_of_decided.count, after.supported_of_decided.n) == (1, 1)
    assert after.batch.open_cases == after.open_referrals.count == referred - 1 == before.batch.open_cases - 1


@pytest.mark.parametrize(
    "body",
    [
        {"decision": "guilty", "note": "a note", "case_digest": "x"},
        {"decision": "concern_supported", "note": "   ", "case_digest": "x"},
        {"decision": "concern_supported", "note": "n"},
        {"decision": "concern_supported", "note": "n", "case_digest": "x", "case_id": "other"},
    ],
)
def test_an_invalid_decision_is_refused_without_repeating_it_and_nothing_is_recorded(
    client: TestClient, store: OpsStore, body
) -> None:
    case_id = QueueView.model_validate(client.get("/api/review/queue").json()).items[0].case_id
    reply = client.post(f"/api/review/cases/{case_id}/disposition", json=body)
    assert reply.status_code == 422
    assert reply.json()["error"]["message"] == BAD_DISPOSITION  # names the fields, repeats nothing sent
    assert store.dispositions() == ()


def test_an_unknown_case_id_is_not_repeated_in_the_error(client: TestClient) -> None:
    probe = "TEST-CALL-<script>alert(1)</script>"
    reply = client.get(f"/api/review/cases/{probe}")
    assert reply.status_code == 404 and "script" not in reply.text and probe not in reply.text
