"""A call on a loan that `samajh.ops` drew from the synthetic loan book, from the phone to ingest.

`samajh.ops` is used as a library to build a batch in `tmp_path`. No network: the speech client
is faked and the extraction model fails every request (the fields become unclear).
"""

from __future__ import annotations

import inspect
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from serverkit import FakeSpeech, make_wav
from starlette.testclient import TestClient
from test_casefile import FailingLlm, wait_case
from test_samajh_dialogue import answer

from samajh.clients.errors import ServerError
from samajh.ops import book as books
from samajh.ops import sampler
from samajh.ops.batch import load_batch
from samajh.ops.model import Attempt, AttemptOutcome, SimulatedCall
from samajh.ops.sessions import ingest, packaged_records
from samajh.ops.store import OpsStore
from samajh.server import create_app
from samajh.server.dialogue import Heard
from samajh.server.loanbook import IST, LoanBook, attempt_limit
from samajh.server.records import PACKAGED_DIR, load_book
from samajh.server.samajh_dialogue import samajh_factory
from samajh.server.sessionlog import SessionStore
from samajh.server.settings import load_settings

BOOK = load_book(PACKAGED_DIR)
SETTINGS = load_settings().model_copy(
    update={"fallback": load_settings().fallback.model_copy(update={"enabled": False})}
)
AS_OF = date(2027, 1, 11)
TESTED = {"premium", "cover", "term", "kind", "provider", "consent", "cancel", "paid", "required", "products"}


@pytest.fixture
def batch(state: Path) -> OpsStore:
    """A batch over the packaged loan book with one draw on 11 January 2027."""
    meta, loans = books.load_book()
    store = OpsStore(state / "ops")
    store.init(meta, loans, date(2027, 1, 1), date(2027, 6, 30), datetime(2026, 11, 10, tzinfo=UTC))
    store.add_draw(sampler.draw(loans, meta, AS_OF, sampler.DEFAULT_RATE, meta.seed, after=None))
    return store


def drawn_hindi(store: OpsStore):
    """The first drawn loan whose borrower speaks Hindi, with its book entry."""
    loans = {loan.record.loan_id: loan for loan in store.book()}
    (draw,) = store.draws()
    return next(
        loans[x.loan_id] for x in draw.drawn if loans[x.loan_id].record.borrower.language.value == "hi"
    )


def not_drawn(store: OpsStore) -> str:
    (draw,) = store.draws()
    picked = {x.loan_id for x in draw.drawn}
    return next(loan.record.loan_id for loan in store.book() if loan.record.loan_id not in picked)


def phone_for(fake: FakeSpeech, state: Path) -> TestClient:
    fake.transcripts.clear()
    return TestClient(
        create_app(
            gnani=fake,
            state=state,
            web_dir=None,
            clips_dir=None,
            dialogues={"samajh": samajh_factory(BOOK, SETTINGS, loans=LoanBook(state))},
            records=BOOK,
            settings=SETTINGS,
            llm=FailingLlm,
        )
    )


def create(phone: TestClient, **params: str):
    return phone.post("/api/sessions", json={"params": params})


def problem(response, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code


def run_call(phone: TestClient, fake: FakeSpeech, state: Path, sid: str, bot: dict) -> None:
    """Answer as the informed Hindi customer until the bot ends the call."""
    params = SessionStore(state / "sessions").load(sid).params
    twin = samajh_factory(BOOK, SETTINGS, loans=LoanBook(state))(params)
    step, turns = twin.start(), 0
    record = BOOK.get(params["record"]) if "record" in params else LoanBook(state).resolve(params)[0]
    twin_year = record.record.borrower.dob.year
    while not bot["end_call"]:
        assert turns < 60 and phone.get(bot["audio_url"]).status_code == 200
        reply = answer("hi", step.say, second_check=str(twin_year))
        fake.transcripts.append(reply)
        clip = make_wav(0.5 + turns / 100, tone=200 + turns)
        turn = phone.post(f"/api/sessions/{sid}/turns?source=file&reply_to={bot['seq']}", content=clip)
        assert turn.status_code == 200, turn.text
        step = twin.step(step.state, Heard(text=reply, second=reply if step.say.second_reading else None))
        bot, turns = turn.json()["bot"], turns + 1
    assert phone.get(bot["audio_url"]).status_code == 200


def test_a_loan_book_call_reaches_a_case_file_and_ingest_links_it_to_its_draw(
    fake: FakeSpeech, state: Path, batch: OpsStore
) -> None:
    loan = drawn_hindi(batch)
    loan_id = loan.record.loan_id
    phone = phone_for(fake, state)
    created = create(phone, loan=loan_id, language="hi")
    assert created.status_code == 201, created.text
    sid, bot = created.json()["session_id"], created.json()["bot"]
    log = SessionStore(state / "sessions").load(sid)
    assert log.params == {
        "loan": loan_id,
        "language": "hi",
        "batch_id": batch.meta().batch_id,
        "draw_id": "D-2027-01-11",
        "sold_on": loan.sold_on.isoformat(),
        "call_date": "2027-01-11",  # the draw's day plus no attempts so far
    }
    # Spoken: the borrower's first name, never the "(synthetic)" marker.
    assert loan.record.borrower.name.split()[0] in bot["text"] and "synthetic" not in bot["text"]

    run_call(phone, fake, state, sid, bot)
    phone.post(f"/api/sessions/{sid}/case")
    case = wait_case(phone, sid)

    assert case["status"] == "ready", case["steps"]
    assert (case["loan_id"], case["record_id"]) == (loan_id, loan_id)
    assert case["book"] == {
        "batch_id": batch.meta().batch_id,
        "draw_id": "D-2027-01-11",
        "sold_on": loan.sold_on.isoformat(),
        "call_date": "2027-01-11",
        "day_since_sale": (AS_OF - loan.sold_on).days,
    }
    assert case["started_at"] == log.created_at  # wall clock, from the session
    turns = len(case["turns"])
    assert case["customer_audio"] == {"mic": 0, "file": turns, "none": 0}
    assert all(t["source"] == "file" for t in case["turns"])
    lender = batch.meta().book.lender_name
    assert lender.endswith("(synthetic)")
    assert lender.removesuffix(" (synthetic)") in json.dumps(case["transcript"], ensure_ascii=False)
    assert lender not in json.dumps(case["transcript"], ensure_ascii=False)

    found = ingest(batch, state / "sessions", packaged_records())

    assert (len(found.linked), len(found.outside)) == (1, 0)
    (attempt,) = [a for a in batch.attempts() if a.loan_id == loan_id]
    assert attempt.draw_id == "D-2027-01-11" and attempt.source.kind == "phone_session"
    assert attempt.source.session_id == sid and attempt.outcome is AttemptOutcome.completed
    sampled = next(s for s in load_batch(batch).sampled if s.loan.record.loan_id == loan_id)
    assert sampled.draw.draw_id == "D-2027-01-11" and sampled.attempts == (attempt,)
    # The attempt's day (and so Sampled.status) is ops' to compute: today's ingest reads it from
    # `started_at` (wall clock), the rewrite in progress from `book.call_date`. Not asserted here.

    # After ingest: the session and its case are still readable; another call on the loan is not.
    assert phone.get(f"/api/sessions/{sid}").status_code == 200
    assert phone.get(f"/api/sessions/{sid}/case").json()["status"] == "ready"
    assert phone.post(f"/api/sessions/{sid}/case").json()["status"] == "ready"
    calls = (len(fake.stt_calls), len(fake.tts_calls))
    problem(create(phone, loan=loan_id, language="hi"), 409, "attempts_ended")
    assert (len(fake.stt_calls), len(fake.tts_calls)) == calls


def test_a_failed_case_rebuilt_after_ingest_keeps_its_times_and_link(
    fake: FakeSpeech, state: Path, batch: OpsStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    loan_id = drawn_hindi(batch).record.loan_id
    phone = phone_for(fake, state)
    created = create(phone, loan=loan_id, language="hi").json()
    run_call(phone, fake, state, created["session_id"], created["bot"])
    sid = created["session_id"]
    monkeypatch.setattr(fake, "batch_error", ServerError(status=500, code=None, message="Batch answered 500"))
    phone.post(f"/api/sessions/{sid}/case")
    failed = wait_case(phone, sid)
    assert failed["status"] == "failed"
    ingest(batch, state / "sessions", packaged_records())  # a failed case is an attempt too

    monkeypatch.setattr(fake, "batch_error", None)
    phone.post(f"/api/sessions/{sid}/case")
    rebuilt = wait_case(phone, sid)

    assert rebuilt["status"] == "ready"
    keep = ("started_at", "book", "loan_id", "record_id", "customer_audio")
    assert {k: rebuilt[k] for k in keep} == {k: failed[k] for k in keep}


def test_a_restart_between_creation_and_a_turn_keeps_the_link(
    fake: FakeSpeech, state: Path, batch: OpsStore
) -> None:
    loan_id = drawn_hindi(batch).record.loan_id
    created = create(phone_for(fake, state), loan=loan_id, language="hi", call_date="2027-01-14").json()
    sid = created["session_id"]
    # A new draw after creation does not move the session; a new server run reads the stored link.
    meta, loans = books.load_book()
    batch.add_draw(sampler.draw(loans, meta, date(2027, 1, 18), sampler.DEFAULT_RATE, meta.seed, after=AS_OF))
    again = phone_for(fake, state)

    run_call(again, fake, state, sid, created["bot"])

    log = SessionStore(state / "sessions").load(sid)
    assert log.status == "ended" and log.params["call_date"] == "2027-01-14"
    assert log.params["draw_id"] == "D-2027-01-11"


def test_every_reason_a_call_may_not_be_placed_is_refused_before_anything_is_spoken(
    fake: FakeSpeech, state: Path, batch: OpsStore
) -> None:
    loan = drawn_hindi(batch)
    loan_id, window_end = loan.record.loan_id, loan.sold_on + timedelta(days=30)
    phone = phone_for(fake, state)
    cases = [
        ({"loan": "syn-pl-1"}, 422, "invalid_loan_id"),
        ({"loan": "SYN-PL-990101-9999"}, 404, "loan_not_on_book"),
        ({"loan": not_drawn(batch)}, 409, "loan_not_drawn"),
        ({"loan": loan_id, "call_date": "11/01/2027"}, 422, "invalid_call_date"),
        ({"loan": loan_id, "call_date": "2027-02-30"}, 422, "invalid_call_date"),
        ({"loan": loan_id, "call_date": "2027-01-10"}, 409, "before_draw"),
        ({"loan": loan_id, "call_date": (window_end + timedelta(days=1)).isoformat()}, 409, "outside_window"),
        ({"loan": loan_id, "record": "hero"}, 422, "record_and_loan"),
        ({"loan": loan_id, "draw_id": "D-2027-01-11"}, 422, "invalid_params"),
    ]
    for params, status, code in cases:
        response = create(phone, language="hi", **params)
        problem(response, status, code)
        assert "syn-pl-1" not in response.text and "11/01/2027" not in response.text  # no echo
    # The last day of the window is still open.
    assert create(phone, loan=loan_id, language="hi", call_date=window_end.isoformat()).status_code == 201

    # A logged attempt that asked for a later call: only after its day; one that ended: refused.
    batch.add_attempt(attempt(loan, 1, date(2027, 1, 13), AttemptOutcome.call_back_later))
    problem(create(phone, loan=loan_id, language="hi", call_date="2027-01-12"), 409, "before_last_attempt")
    # The attempt's own day is refused too: ingest could not put the call after that attempt.
    problem(create(phone, loan=loan_id, language="hi", call_date="2027-01-13"), 409, "before_last_attempt")
    defaulted = create(phone, loan=loan_id, language="hi")
    assert defaulted.status_code == 201
    stored = SessionStore(state / "sessions").load(defaulted.json()["session_id"]).params
    assert stored["call_date"] == "2027-01-14"  # the day after the attempt (as_of + 1 is earlier)
    batch.add_attempt(attempt(loan, 2, date(2027, 1, 14), AttemptOutcome.declined))
    problem(create(phone, loan=loan_id, language="hi"), 409, "attempts_ended")

    sessions = sorted((state / "sessions").iterdir())
    assert len(sessions) == 2  # only the two calls that were allowed


def attempt(loan, number: int, day: date, outcome: AttemptOutcome, hour: int = 11) -> Attempt:
    """A logged attempt on `loan`, at `hour` India time on `day`."""
    loan_id = loan.record.loan_id
    return Attempt(
        attempt_id=f"D-2027-01-11/{loan_id}/{number}",
        draw_id="D-2027-01-11",
        loan_id=loan_id,
        number=number,
        at=datetime(day.year, day.month, day.day, hour, tzinfo=IST),
        day_since_sale=(day - loan.sold_on).days,
        language=loan.record.borrower.language,
        source=SimulatedCall(script="test"),
        outcome=outcome,
        right_party_confirmed=outcome is not AttemptOutcome.no_answer,
    )


def stored_call_date(state: Path, response) -> str:
    assert response.status_code == 201, response.text
    return SessionStore(state / "sessions").load(response.json()["session_id"]).params["call_date"]


def test_the_default_call_date_counts_the_attempts_already_logged(
    fake: FakeSpeech, state: Path, batch: OpsStore
) -> None:
    loan = drawn_hindi(batch)
    phone = phone_for(fake, state)
    # Two no-answer attempts, both on the draw's day: the day after them is 12 January, but the
    # simulator's rule (draw day + attempts so far) gives the 13th, which is later.
    batch.add_attempt(attempt(loan, 1, AS_OF, AttemptOutcome.no_answer, hour=10))
    batch.add_attempt(attempt(loan, 2, AS_OF, AttemptOutcome.no_answer, hour=16))

    assert stored_call_date(state, create(phone, loan=loan.record.loan_id, language="hi")) == "2027-01-13"
    listed = next(
        row for row in phone.get("/api/loans").json()["loans"] if row["loan_id"] == loan.record.loan_id
    )
    assert listed["call_date"] == "2027-01-13"


def test_a_last_attempt_late_on_day_30_leaves_no_day_to_call(
    fake: FakeSpeech, state: Path, batch: OpsStore
) -> None:
    loan = drawn_hindi(batch)
    day_30 = loan.sold_on + timedelta(days=30)
    phone = phone_for(fake, state)
    batch.add_attempt(attempt(loan, 1, day_30, AttemptOutcome.no_answer, hour=23))

    problem(create(phone, loan=loan.record.loan_id, language="hi"), 409, "outside_window")
    explicit = create(phone, loan=loan.record.loan_id, language="hi", call_date=day_30.isoformat())
    problem(explicit, 409, "before_last_attempt")
    assert loan.record.loan_id not in [row["loan_id"] for row in phone.get("/api/loans").json()["loans"]]
    assert not (state / "sessions").exists()


def test_a_session_on_a_day_the_server_accepts_is_linked_by_ingest_not_skipped(
    fake: FakeSpeech, state: Path, batch: OpsStore
) -> None:
    """The verifier's finding 1: a retry attempt logged late in the day, then a call on the
    server's default date. Ingest must put the call after the attempt."""
    loan = drawn_hindi(batch)
    batch.add_attempt(attempt(loan, 1, AS_OF + timedelta(days=2), AttemptOutcome.no_answer, hour=23))
    phone = phone_for(fake, state)
    created = create(phone, loan=loan.record.loan_id, language="hi")
    assert stored_call_date(state, created) == (AS_OF + timedelta(days=3)).isoformat()
    sid = created.json()["session_id"]
    run_call(phone, fake, state, sid, created.json()["bot"])
    phone.post(f"/api/sessions/{sid}/case")
    assert wait_case(phone, sid)["status"] == "ready"

    found = ingest(batch, state / "sessions", packaged_records())

    assert (len(found.linked), len(found.skipped)) == (1, 0), found
    numbers = [a.number for a in batch.attempts() if a.loan_id == loan.record.loan_id]
    assert numbers == [1, 2]


def test_a_loan_with_as_many_attempts_as_the_simulator_allows_is_refused_and_unlisted(
    fake: FakeSpeech, state: Path, batch: OpsStore
) -> None:
    loan = drawn_hindi(batch)
    loan_id = loan.record.loan_id
    limit = attempt_limit()
    assert limit >= 2
    phone = phone_for(fake, state)
    for number in range(1, limit):  # retry outcomes, all on the draw's day
        batch.add_attempt(attempt(loan, number, AS_OF, AttemptOutcome.no_answer, hour=8 + number))
    assert loan_id in [row["loan_id"] for row in phone.get("/api/loans").json()["loans"]]
    assert create(phone, loan=loan_id, language="hi").status_code == 201  # limit - 1: one more is allowed

    batch.add_attempt(attempt(loan, limit, AS_OF, AttemptOutcome.call_back_later, hour=8 + limit))
    problem(create(phone, loan=loan_id, language="hi"), 409, "attempt_limit")
    problem(create(phone, loan=loan_id, language="hi", call_date="2027-01-20"), 409, "attempt_limit")
    assert loan_id not in [row["loan_id"] for row in phone.get("/api/loans").json()["loans"]]


def test_an_ended_chain_is_refused_as_ended_before_the_limit_is_counted(
    fake: FakeSpeech, state: Path, batch: OpsStore
) -> None:
    loan = drawn_hindi(batch)
    limit = attempt_limit()
    for number in range(1, limit):
        batch.add_attempt(attempt(loan, number, AS_OF, AttemptOutcome.no_answer, hour=8 + number))
    batch.add_attempt(attempt(loan, limit, AS_OF, AttemptOutcome.declined, hour=8 + limit))

    problem(create(phone_for(fake, state), loan=loan.record.loan_id, language="hi"), 409, "attempts_ended")


def test_the_attempt_limit_is_the_simulators_and_follows_a_change_there(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from samajh.ops import model as ops_model
    from samajh.ops import simulate

    simulators = inspect.signature(simulate.run_draw).parameters["max_attempts"].default
    assert attempt_limit() == simulators

    if hasattr(ops_model, "MAX_ATTEMPTS"):
        monkeypatch.setattr(ops_model, "MAX_ATTEMPTS", simulators + 2)
    else:

        def run_draw(store, draw, customers, analyse, max_attempts: int = simulators + 2, workers: int = 1):
            raise AssertionError("not called")

        monkeypatch.setattr(simulate, "run_draw", run_draw)
    assert attempt_limit() == simulators + 2


def test_the_loan_listing_reads_the_store_once(
    fake: FakeSpeech, state: Path, batch: OpsStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    reads: list[str] = []
    real = OpsStore.attempts

    def counted(self):
        reads.append("attempts")
        return real(self)

    monkeypatch.setattr(OpsStore, "attempts", counted)
    loans = phone_for(fake, state).get("/api/loans").json()["loans"]

    assert len(loans) > 1 and reads == ["attempts"]


@pytest.mark.parametrize(
    ("params", "code"),
    [
        ({"loan": "SYN-PL-२७०१११-0001"}, "invalid_loan_id"),  # Devanagari digits
        ({"loan": "SYN-PL-270111-０００１"}, "invalid_loan_id"),  # full-width digits
        ({"call_date": "20270120"}, "invalid_call_date"),  # date.fromisoformat takes this one
        ({"call_date": "2027-W03-3"}, "invalid_call_date"),  # and this one
        ({"call_date": "२०२७-०१-२०"}, "invalid_call_date"),
    ],
)
def test_only_ascii_ids_and_dates_in_the_one_form_are_taken(
    fake: FakeSpeech, state: Path, batch: OpsStore, params: dict[str, str], code: str
) -> None:
    loan_id = drawn_hindi(batch).record.loan_id
    problem(create(phone_for(fake, state), language="hi", **({"loan": loan_id} | params)), 422, code)
    assert not (state / "sessions").exists()


@pytest.mark.parametrize("link", ["draw_id", "call_date", "batch_id", "sold_on"])
def test_a_packaged_record_session_refuses_link_params(
    fake: FakeSpeech, state: Path, batch: OpsStore, link: str
) -> None:
    value = {"draw_id": "D-2027-01-11", "call_date": "2027-01-11", "batch_id": batch.meta().batch_id,
             "sold_on": "2027-01-05"}[link]  # fmt: skip
    problem(
        create(phone_for(fake, state), record="hero", language="hi", **{link: value}), 422, "invalid_params"
    )
    assert not (state / "sessions").exists()


def test_with_no_batch_a_loan_is_refused_and_the_packaged_records_still_work(
    fake: FakeSpeech, state: Path
) -> None:
    phone = phone_for(fake, state)
    problem(create(phone, loan="SYN-PL-270104-0001", language="hi"), 409, "no_batch")
    assert phone.get("/api/loans").json()["loans"] == []
    assert not fake.stt_calls and not fake.tts_calls
    for record in ("hero", "informed", "third-party"):
        assert create(phone, record=record, language="hi").status_code == 201


def test_packaged_records_with_a_batch_are_unchanged(fake: FakeSpeech, state: Path, batch: OpsStore) -> None:
    phone = phone_for(fake, state)
    created = create(phone, record="hero", language="hi")
    assert created.status_code == 201
    sid = created.json()["session_id"]
    assert SessionStore(state / "sessions").load(sid).params == {"record": "hero", "language": "hi"}
    run_call(phone, fake, state, sid, created.json()["bot"])
    phone.post(f"/api/sessions/{sid}/case")
    case = wait_case(phone, sid)
    assert (case["record_id"], case["book"]) == ("hero", None)
    assert case["started_at"] == SessionStore(state / "sessions").load(sid).created_at


def test_the_loan_listing_shows_callable_drawn_loans_and_no_tested_value(
    fake: FakeSpeech, state: Path, batch: OpsStore
) -> None:
    phone = phone_for(fake, state)
    loans = phone.get("/api/loans").json()["loans"]
    (draw,) = batch.draws()
    assert [row["loan_id"] for row in loans] == [x.loan_id for x in draw.drawn]
    for row in loans:
        assert set(row) == {
            "loan_id", "first_name", "language", "birth_year", "lender_name", "batch_id", "draw_id",
            "sold_on", "call_date", "day_since_sale",
        }  # fmt: skip
        assert not any(word in key for key in row for word in TESTED)
        assert row["lender_name"].endswith("(synthetic)") and row["call_date"] == "2027-01-11"


def test_prepare_voices_a_loan_book_customer_from_the_simulators_script(
    fake: FakeSpeech, state: Path, batch: OpsStore, tmp_path: Path
) -> None:
    from samajh.server.prepare import loan_persona, prepare

    loan_id = drawn_hindi(batch).record.loan_id
    persona = loan_persona(state, loan_id)
    turns = prepare(persona, tmp_path / "voiced", fake, state=state)

    manifest = json.loads((tmp_path / "voiced" / "call.json").read_text(encoding="utf-8"))
    assert manifest["params"] == {"loan": loan_id, "language": "hi"} and manifest["synthetic"] is True
    assert len(turns) > 5 and all((tmp_path / "voiced" / t["file"]).is_file() for t in turns)
    assert not (state / "sessions").exists()  # preparing places no call
