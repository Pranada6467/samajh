"""Evidence bundles: export, verify from the bundle alone, and tampering caught at the right file.
Fake Gnani, fake LLM, no network."""

from __future__ import annotations

import itertools
import json
import re
import shutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ops"))

from opskit import add_reviewer
from serverkit import FakeSpeech
from starlette.testclient import TestClient
from test_casefile import phone_for, run_call, wait_case

from samajh.evidence.__main__ import main as evidence
from samajh.evidence.bundle import MANIFEST, verify_bundle
from samajh.evidence.case_seal import seal_case
from samajh.evidence.decisions import case_digest
from samajh.evidence.digest import digest, sha256_hex
from samajh.ops.__main__ import main as ops
from samajh.ops.batch import load_batch
from samajh.ops.model import Decision, Disposition
from samajh.ops.sessions import ingest, packaged_records
from samajh.ops.store import OpsStore
from samajh.server import create_app


def _fake() -> FakeSpeech:
    return FakeSpeech(["पचास हज़ार", "दो हज़ार", "बीमा"])


@pytest.fixture(scope="module")
def demo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    state = tmp_path_factory.mktemp("demo") / "state"
    assert ops(["demo", "--state", str(state)]) == 0
    return state


NEW = "20261120T120000"  # a session id time after the evidence epoch
OLD = "20261110T120000"  # one before it


@contextmanager
def session_ids(prefix: str) -> Iterator[None]:
    """Phone sessions made inside get ids `<prefix>-<12 hex>`: dated where the test needs them."""
    import samajh.server.app as app_module

    counter = itertools.count(1)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(app_module, "new_session_id", lambda: f"{prefix}-{next(counter):012x}")
        yield


@pytest.fixture(scope="module")
def phone_base(demo: Path, tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    """The demo batch plus one phone call (hero record, a session dated after the evidence epoch)
    built to a sealed case, ingested (outside the sample, a referral) and decided once through the
    review API with a reviewer token."""
    state = Path(shutil.copytree(demo, tmp_path_factory.mktemp("phone") / "state"))
    fake = _fake()
    phone = phone_for(fake, state)
    with session_ids(NEW):
        sid = run_call(phone, fake)
    phone.post(f"/api/sessions/{sid}/case")
    assert wait_case(phone, sid)["status"] == "ready"
    ingest(OpsStore(state / "ops"), state / "sessions", packaged_records())
    client = TestClient(create_app(gnani=FakeSpeech(), state=state, web_dir=None, clips_dir=None),
                        headers=add_reviewer(state))  # fmt: skip
    page = client.get(f"/api/review/cases/{sid}").json()
    body = {"decision": "call_customer", "note": "listen again", "case_digest": page["case_digest"]}
    assert client.post(f"/api/review/cases/{sid}/disposition", json=body).status_code == 200
    return state, sid


@pytest.fixture
def phone_state(phone_base: tuple[Path, str], tmp_path: Path) -> tuple[Path, str]:
    state, sid = phone_base
    return Path(shutil.copytree(state, tmp_path / "state")), sid


def _export(state: Path, case_id: str, out: Path, *extra: str) -> int:
    return evidence(["export", "--case", case_id, "--out", str(out), "--state", str(state), *extra])


@pytest.fixture
def bundle(phone_state: tuple[Path, str], tmp_path: Path) -> Path:
    state, sid = phone_state
    out = tmp_path / "bundle"
    assert _export(state, sid, out, "--with-recording") == 0
    assert verify_bundle(out).code == 0, verify_bundle(out).mismatch
    return out


def _referred_demo_case(state: Path) -> str:
    batch = load_batch(OpsStore(state / "ops"))
    return batch.referrals[0].call.call_id


def _rehash(out: Path) -> None:
    """Rewrite the manifest's file list and root after an edit, as a careful tamperer would."""
    m = json.loads((out / MANIFEST).read_bytes())
    for row in m["files"]:
        data = (out / row["path"]).read_bytes()
        row["sha256"], row["bytes"] = sha256_hex(data), len(data)
    m.pop("root_sha256")
    m["root_sha256"] = digest(m)
    (out / MANIFEST).write_text(json.dumps(m, indent=2, ensure_ascii=False))


def _first(out: Path) -> str:
    v = verify_bundle(out)
    assert v.code == 1, (v.unverifiable, v.warnings)
    return v.mismatch


def _flip(path: Path, at: int = -10) -> None:
    data = bytearray(path.read_bytes())
    data[at] ^= 1
    path.write_bytes(bytes(data))


# --- export and verify ---------------------------------------------------------------


def test_a_demo_case_exports_and_verifies(demo: Path, tmp_path: Path, capsys) -> None:
    case_id = _referred_demo_case(demo)
    out = tmp_path / "b"
    assert _export(demo, case_id, out) == 0
    assert "root_sha256" in capsys.readouterr().out
    assert evidence(["verify", str(out)]) == 0
    m = json.loads((out / MANIFEST).read_bytes())
    assert (
        m["source"] == "simulated" and json.loads((out / "recording.json").read_bytes())["included"] is False
    )
    quotes = json.loads((out / "quotes/quotes.json").read_bytes())
    assert all(q["clip"] is None for q in quotes)


def test_a_phone_case_exports_without_the_recording_and_verifies(phone_state, tmp_path: Path) -> None:
    state, sid = phone_state
    out = tmp_path / "b"
    assert _export(state, sid, out) == 0
    assert evidence(["verify", str(out)]) == 0
    assert not (out / "recording").exists() and not (out / "session" / "audio").exists()
    quotes = json.loads((out / "quotes/quotes.json").read_bytes())
    assert quotes and all(q["clip"] for q in quotes)
    assert len(list((out / "decisions/decisions.jsonl").read_text().splitlines())) == 1
    m = json.loads((out / MANIFEST).read_bytes())
    assert m["digests"]["case_digest"] == case_digest(state / "ops", state / "sessions", sid)
    assert m["source_checks"] == {
        "decisions": "verified",
        "session": "verified",
        "case": "verified",
        "call_ledger": "verified",
    } | {k: v for k, v in m["source_checks"].items() if k == "changed_after_seal"}


def test_a_phone_case_with_the_recording_verifies_and_holds_the_audio(bundle: Path) -> None:
    assert (bundle / "recording/call.wav").is_file()
    assert list((bundle / "session/audio").glob("*.wav"))
    assert json.loads((bundle / "recording.json").read_bytes())["included"] is True


def test_export_refuses_a_non_empty_dir_and_an_unknown_case(phone_state, tmp_path: Path) -> None:
    state, sid = phone_state
    full = tmp_path / "full"
    full.mkdir()
    (full / "x").write_text("x")
    assert _export(state, sid, full) == 2
    assert _export(state, "no-such-case", tmp_path / "new") == 2 and not (tmp_path / "new").exists()


def test_export_refuses_a_source_that_is_already_inconsistent(phone_state, tmp_path: Path) -> None:
    state, sid = phone_state
    _flip(state / "sessions" / sid / "call.wav")
    assert _export(state, sid, tmp_path / "b") == 1 and not (tmp_path / "b").exists()


# --- tampering: each caught at the right file ------------------------------------------


def test_one_byte_of_a_clip(bundle: Path) -> None:
    _flip(bundle / "quotes/q01.wav")
    assert "quotes/q01.wav" in _first(bundle)
    _rehash(bundle)
    assert "quotes/q01.wav" in _first(bundle)  # the clip no longer matches quotes.json / its cut


def test_one_byte_of_call_wav(bundle: Path) -> None:
    _flip(bundle / "recording/call.wav")
    assert "recording/call.wav" in _first(bundle)
    _rehash(bundle)
    assert "recording/call.wav" in _first(bundle)


def test_one_byte_of_an_event_audio_file(bundle: Path) -> None:
    audio = min((bundle / "session/audio").glob("customer-*.wav"))
    _flip(audio)
    _rehash(bundle)
    assert f"session/audio/{audio.name}" in _first(bundle)


def test_an_edited_quote_text(bundle: Path) -> None:
    path = bundle / "quotes/quotes.json"
    quotes = json.loads(path.read_bytes())
    quotes[0]["quote"] = "कुछ और"
    path.write_text(json.dumps(quotes, ensure_ascii=False))
    assert "quotes/quotes.json" in _first(bundle)
    _rehash(bundle)
    assert "quotes/quotes.json item 1" in _first(bundle)


def test_an_edited_event(bundle: Path) -> None:
    path = bundle / "session/events.json"
    events = json.loads(path.read_bytes())
    customer = next(e for e in events if e.get("type") == "customer")
    customer["transcript"] = "नहीं"
    path.write_text(json.dumps(events, ensure_ascii=False))
    _rehash(bundle)
    assert f"session/events.json event seq {customer['seq']}" in _first(bundle)


def test_two_chain_lines_swapped(bundle: Path) -> None:
    path = bundle / "session/chain.jsonl"
    lines = path.read_bytes().splitlines(keepends=True)
    lines[3], lines[4] = lines[4], lines[3]
    path.write_bytes(b"".join(lines))
    _rehash(bundle)
    assert "session/chain.jsonl entry 3" in _first(bundle)


def test_a_chain_line_deleted(bundle: Path) -> None:
    path = bundle / "session/chain.jsonl"
    lines = path.read_bytes().splitlines(keepends=True)
    del lines[2]
    path.write_bytes(b"".join(lines))
    _rehash(bundle)
    assert "session/chain.jsonl entry 2" in _first(bundle)


def test_a_decision_line_case_id_changed(bundle: Path) -> None:
    path = bundle / "decisions/decisions.jsonl"
    row = json.loads(path.read_bytes())
    row["case_id"] = "another-case"
    path.write_text(json.dumps(row) + "\n")
    _rehash(bundle)
    assert "decisions/decisions.jsonl" in _first(bundle)


def test_manifest_edited_without_recomputing_root(bundle: Path) -> None:
    m = json.loads((bundle / MANIFEST).read_bytes())
    m["case_id"] = "other"
    (bundle / MANIFEST).write_text(json.dumps(m))
    assert "root_sha256" in _first(bundle)


def test_an_extra_file(bundle: Path) -> None:
    (bundle / "quotes/q99.wav").write_bytes(b"RIFF")
    assert "quotes/q99.wav" in _first(bundle)


def test_a_listed_file_deleted(bundle: Path) -> None:
    (bundle / "recording.json").unlink()
    assert "recording.json" in _first(bundle)


def test_a_symlink_is_refused(bundle: Path, tmp_path: Path) -> None:
    (tmp_path / "outside").write_text("x")
    (bundle / "link").symlink_to(tmp_path / "outside")
    assert "symlink" in _first(bundle)


def test_a_resealed_case_whose_session_head_no_longer_matches(bundle: Path) -> None:
    path = bundle / "case/case.json"
    case = json.loads(path.read_bytes())
    case["tier"] = "clear"
    case["seal"]["inputs"]["session_head"] = "a" * 64
    path.write_bytes(seal_case(json.dumps(case).encode()))
    sealed = json.loads(path.read_bytes())["seal"]
    m = json.loads((bundle / MANIFEST).read_bytes())
    d = m["digests"]
    d["case_content_sha256"], d["case_inputs_sha256"] = sealed["content_sha256"], sealed["inputs_sha256"]
    d["session_head"] = "a" * 64
    from samajh.evidence.decisions import CASE_TAG
    from samajh.evidence.digest import tagged

    d["case_digest"] = tagged(CASE_TAG, d["call_record_sha256"], d["case_content_sha256"])
    (bundle / MANIFEST).write_text(json.dumps(m))
    _rehash(bundle)
    problem = _first(bundle)
    assert "case/case.json" in problem and "session_head" in problem


# --- decisions -------------------------------------------------------------------------


def test_a_decision_made_before_the_case_was_rebuilt_is_a_warning(demo: Path, tmp_path: Path, capsys) -> None:
    state = Path(shutil.copytree(demo, tmp_path / "state"))
    case_id = _referred_demo_case(state)
    store = OpsStore(state / "ops")
    store.add_disposition(Disposition(
        case_id=case_id, decision=Decision.call_customer, note="n", reviewer="R",
        recorded_at="2027-02-01T00:00:00Z", case_digest="e" * 64,  # the digest of an earlier version
        reviewer_auth="token",
    ))  # fmt: skip
    out = tmp_path / "b"
    assert _export(state, case_id, out) == 0
    capsys.readouterr()
    assert evidence(["verify", str(out)]) == 4
    assert (
        "WARNING: decision on log line 1 was made on a different version of this case"
        in capsys.readouterr().out
    )


def test_a_new_decision_line_stripped_of_its_prev_is_refused(demo: Path, tmp_path: Path) -> None:
    from samajh.evidence.decisions import verify_dispositions

    log = tmp_path / "d.jsonl"
    log.write_text(json.dumps({"case_id": "c", "case_digest": "f" * 64}) + "\n")
    ok, problem, _ = verify_dispositions(log)
    assert not ok and problem == "line 1 has a case digest but no prev_sha256"


# --- legacy and the withheld reply ------------------------------------------------------


@pytest.fixture(scope="module")
def old_base(demo: Path, tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    """The demo batch plus one phone call whose session id is dated before the evidence epoch."""
    state = Path(shutil.copytree(demo, tmp_path_factory.mktemp("old") / "state"))
    fake = _fake()
    phone = phone_for(fake, state)
    with session_ids(OLD):
        sid = run_call(phone, fake)
    phone.post(f"/api/sessions/{sid}/case")
    assert wait_case(phone, sid)["status"] == "ready"
    ingest(OpsStore(state / "ops"), state / "sessions", packaged_records())
    return state, sid


def _strip_chain_and_seal(d: Path) -> None:
    data = json.loads((d / "session.json").read_bytes())
    data.pop("chain")
    (d / "session.json").write_text(json.dumps(data, ensure_ascii=False))
    (d / "chain.jsonl").unlink()
    case = json.loads((d / "case.json").read_bytes())
    case.pop("seal")
    (d / "case.json").write_text(json.dumps(case, ensure_ascii=False))


def test_a_new_session_stripped_of_its_chain_and_seal_is_a_mismatch(
    phone_state, tmp_path: Path, capsys
) -> None:
    state, sid = phone_state
    _strip_chain_and_seal(state / "sessions" / sid)
    assert evidence(["check", "--state", str(state)]) == 1
    assert "dated after the evidence epoch but has no chain" in capsys.readouterr().out
    assert _export(state, sid, tmp_path / "b") == 1 and not (tmp_path / "b").exists()


def test_a_new_bundle_stripped_of_its_chain_and_seal_is_a_mismatch(bundle: Path) -> None:
    from samajh.evidence.decisions import CASE_TAG
    from samajh.evidence.digest import tagged

    (bundle / "session/chain.jsonl").unlink()
    case = json.loads((bundle / "case/case.json").read_bytes())
    case.pop("seal")
    (bundle / "case/case.json").write_text(json.dumps(case, ensure_ascii=False))
    m = json.loads((bundle / MANIFEST).read_bytes())
    m["files"] = [r for r in m["files"] if r["path"] != "session/chain.jsonl"]
    d = m["digests"]
    for key in (
        "case_content_sha256",
        "case_inputs_sha256",
        "session_head",
        "session_entries",
        "session_seal",
    ):
        d[key] = None
    d["case_digest"] = tagged(CASE_TAG, d["call_record_sha256"], "none")
    (bundle / MANIFEST).write_text(json.dumps(m))
    _rehash(bundle)
    assert "dated after the evidence epoch" in _first(bundle)


def test_an_old_session_without_a_chain_exports_as_unverifiable(old_base, tmp_path: Path, capsys) -> None:
    state, sid = Path(shutil.copytree(old_base[0], tmp_path / "state")), old_base[1]
    d = state / "sessions" / sid
    data = json.loads((d / "session.json").read_bytes())
    data.pop("chain")
    (d / "session.json").write_text(json.dumps(data, ensure_ascii=False))
    (d / "chain.jsonl").unlink()
    case = json.loads((d / "case.json").read_bytes())
    case.pop("seal")  # a case file of that time had no seal either
    (d / "case.json").write_text(json.dumps(case, ensure_ascii=False))
    out = tmp_path / "b"
    assert _export(state, sid, out) == 0
    assert json.loads((out / MANIFEST).read_bytes())["source_checks"]["session"] == "unverifiable"
    capsys.readouterr()
    assert evidence(["verify", str(out)]) == 3
    assert "UNVERIFIABLE" in capsys.readouterr().out


def test_the_year_of_birth_reply_appears_nowhere_in_the_bundle(demo: Path, tmp_path: Path) -> None:
    from test_identity_server import YEAR, play
    from test_identity_server import phone_for as identity_phone

    state = Path(shutil.copytree(demo, tmp_path / "state"))
    fake = _fake()
    phone = identity_phone(fake, state)
    reply = "उन्नीस सौ चौरासी"
    sid, said = play(phone, fake, YEAR, record="hero", second_check=reply)
    assert reply in said
    phone.post(f"/api/sessions/{sid}/case")
    assert wait_case(phone, sid)["status"] == "ready"
    ingest(OpsStore(state / "ops"), state / "sessions", packaged_records())
    out = tmp_path / "b"
    assert _export(state, sid, out) == 0
    assert verify_bundle(out).code == 0, verify_bundle(out).mismatch
    events = json.loads((out / "session/events.json").read_bytes())
    assert any(e.get("withheld") for e in events)
    for f in out.rglob("*"):
        if f.is_file():
            assert reply.encode() not in f.read_bytes(), f
            if f.suffix != ".wav":  # a digest or a timestamp may hold the digits by chance
                assert not re.search(rb"(?<![0-9a-f:.T-])1984(?![0-9a-f])", f.read_bytes()), f


def test_check_on_a_missing_or_empty_dir_is_a_usage_error(tmp_path: Path) -> None:
    assert evidence(["check", "--state", str(tmp_path / "nope")]) == 2
    assert evidence(["check", "--state", str(tmp_path)]) == 2


def test_check_counts_a_whole_state(phone_state, capsys) -> None:
    state, sid = phone_state
    assert evidence(["check", "--state", str(state)]) == 0
    assert "1 verified" in capsys.readouterr().out
    _flip(state / "sessions" / sid / "call.wav")
    assert evidence(["check", "--state", str(state)]) == 1


# --- the fix round's attacks -------------------------------------------------------------


def test_a_phone_bundle_relabelled_simulated(bundle: Path) -> None:
    m = json.loads((bundle / MANIFEST).read_bytes())
    m["source"], m["session_id"] = "simulated", None
    (bundle / MANIFEST).write_text(json.dumps(m))
    _rehash(bundle)
    assert "differs from the call record's 'phone_session'" in _first(bundle)


def test_a_phone_bundle_missing_its_case_file(bundle: Path) -> None:
    (bundle / "case/case.json").unlink()
    m = json.loads((bundle / MANIFEST).read_bytes())
    m["files"] = [r for r in m["files"] if r["path"] != "case/case.json"]
    (bundle / MANIFEST).write_text(json.dumps(m))
    _rehash(bundle)
    assert "case/case.json is missing" in _first(bundle)


def test_an_edited_call_record_is_caught_in_the_state_and_the_bundle(
    phone_state, bundle: Path, tmp_path, capsys
) -> None:
    state, sid = phone_state
    call = state / "ops" / "calls" / f"{sid}.json"
    call.write_bytes(call.read_bytes().replace(b'"analysis"', b'"analysis" ', 1))
    assert evidence(["check", "--state", str(state)]) == 1
    assert "sha256 differs from its line in calls.chain.jsonl" in capsys.readouterr().out
    assert _export(state, sid, tmp_path / "b2") == 1 and not (tmp_path / "b2").exists()
    from samajh.evidence.decisions import CASE_TAG
    from samajh.evidence.digest import tagged

    raw = (bundle / "case/call-record.json").read_bytes() + b"\n"
    (bundle / "case/call-record.json").write_bytes(raw)
    m = json.loads((bundle / MANIFEST).read_bytes())
    d = m["digests"]
    d["call_record_sha256"] = sha256_hex(raw)
    d["case_digest"] = tagged(CASE_TAG, d["call_record_sha256"], d["case_content_sha256"])
    (bundle / MANIFEST).write_text(json.dumps(m))
    _rehash(bundle)
    assert "the entry's sha256 differs from case/call-record.json" in _first(bundle)


def test_a_call_file_with_no_ledger_line(phone_state, capsys) -> None:
    state, sid = phone_state
    ledger = state / "ops" / "calls.chain.jsonl"
    lines = ledger.read_bytes().splitlines(keepends=True)
    kept = [x for x in lines if json.loads(x)["call_id"] != sid]
    assert len(kept) == len(lines) - 1
    ledger.write_bytes(b"".join(kept))
    assert evidence(["check", "--state", str(state)]) == 1
    assert "MISMATCH: calls.chain.jsonl" in capsys.readouterr().out  # a broken link, or the head file


def test_dropped_quotes_are_caught(bundle: Path) -> None:
    path = bundle / "quotes/quotes.json"
    path.write_text(json.dumps(json.loads(path.read_bytes())[:1], ensure_ascii=False))
    _rehash(bundle)
    assert "a quote of case/case.json evidence is missing" in _first(bundle)


def test_a_withheld_stub_on_an_ordinary_reply(bundle: Path) -> None:
    path = bundle / "session/events.json"
    events = json.loads(path.read_bytes())
    e = next(x for x in events if x.get("type") == "customer")
    events[e["seq"]] = {"seq": e["seq"], "type": "customer", "reply_to": e.get("reply_to"), "withheld": True,
                        "sha256": digest(e)}  # fmt: skip
    path.write_text(json.dumps(events, ensure_ascii=False))
    _rehash(bundle)
    assert "withheld, but it is not a reply to the year-of-birth question" in _first(bundle)


@pytest.mark.parametrize("shape", ["clip", "quotes", "chain"])
def test_malformed_files_are_a_mismatch_not_a_traceback(bundle: Path, shape: str) -> None:
    if shape == "clip":
        (bundle / "quotes/q01.wav").write_bytes(b"not a wav")
        q = json.loads((bundle / "quotes/quotes.json").read_bytes())
        for x in q:
            if x["clip"] == "quotes/q01.wav":
                x["clip_sha256"] = sha256_hex(b"not a wav")
        (bundle / "quotes/quotes.json").write_text(json.dumps(q, ensure_ascii=False))
    elif shape == "quotes":
        (bundle / "quotes/quotes.json").write_text('{"n": 1}')
    else:
        c = json.loads((bundle / "decisions/chain.json").read_bytes())
        c["lines"] = {"a": 1}
        (bundle / "decisions/chain.json").write_text(json.dumps(c))
    _rehash(bundle)
    assert "malformed" in _first(bundle)


def test_a_duplicate_manifest_row(bundle: Path) -> None:
    m = json.loads((bundle / MANIFEST).read_bytes())
    m["files"].append(dict(m["files"][0]))
    m.pop("root_sha256")
    m["root_sha256"] = digest(m)
    (bundle / MANIFEST).write_text(json.dumps(m))
    assert "listed twice" in _first(bundle)


def test_check_reports_an_unledgered_old_call_as_unverifiable(demo: Path, tmp_path: Path, capsys) -> None:
    state = Path(shutil.copytree(demo, tmp_path / "state"))
    batch = state / "ops" / "batch.json"
    meta = json.loads(batch.read_bytes())
    meta["created_at"] = "2026-11-10T00:00:00Z"
    batch.write_text(json.dumps(meta))
    (state / "ops" / "calls.chain.jsonl").unlink()
    (state / "ops" / "calls.chain.head.json").unlink()
    assert evidence(["check", "--state", str(state)]) == 3
    assert "UNVERIFIABLE: call" in capsys.readouterr().out
    meta["created_at"] = "2027-01-01T00:00:00Z"
    batch.write_text(json.dumps(meta))
    assert evidence(["check", "--state", str(state)]) == 1
    assert "dated after the evidence epoch but has no ledger line" in capsys.readouterr().out
