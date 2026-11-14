"""Behaviour of samajh.human on invented sessions and invented gold (no card content)."""

from __future__ import annotations

import csv
import json
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

from samajh.evalkit.score import wilson
from samajh.human import notes as notes_mod
from samajh.human import score as score_mod
from samajh.human.__main__ import main
from samajh.human.sessions import attach_gold, load_gold, load_sessions
from samajh.human.stats import per100, spread
from samajh.human.wer import char_counts, refs, wer_report, word_counts

REPO = Path(__file__).resolve().parents[2]
CUTS = {"yes_no": 700.0, "short": 800.0, "amount": 1000.0, "open": 1100.0}


def bot(seq, *, key="x.ask", step="open_recall", listen="open", browser=None, superseded=False, outcome=None):
    return {
        "seq": seq,
        "at": float(seq),
        "type": "bot",
        "text": "t",
        "superseded": superseded,
        "listen": listen,
        "lines": [
            {
                "key": key,
                "text": "t",
                "tags": {"step": step},
                "tts": {"cache_hit": seq % 2 == 0, "synth_ms": 10.0 * (seq + 1)},
            }
        ],
        "tags": {"outcome": outcome} if outcome else {},
        "synth_ms": 5.0,
        "browser": browser,
    }


def cust(
    seq,
    reply_to,
    *,
    text="haan",
    degraded=False,
    superseded=False,
    pauses=(),
    stt_ms=100.0,
    source="mic",
    second=None,
    browser=None,
    cache_key=None,
    http_status=200,
):
    readings = [
        {
            "role": "primary",
            "model": "prisma-v3.0",
            "ok": True,
            "text": text,
            "attempts": 1,
            "cache_key": cache_key,
            "http_status": http_status,
        }
    ]
    if second is not None:
        readings.append(second)
    return {
        "seq": seq,
        "at": float(seq),
        "type": "customer",
        "source": source,
        "reply_to": reply_to,
        "superseded": superseded,
        "transcript": text,
        "readings": readings,
        "degraded": degraded,
        "audio": f"audio/customer-{seq:03d}.wav",
        "latency": {"stt_ms": stt_ms, "dialogue_ms": 3.0, "server_ms": 200.0},
        "pauses": {"pauses_ms": list(pauses)},
        "browser": browser,
        "classifier": {"ran": True, "label": "yes", "latency_ms": 400.0, "degraded": True},
    }


def write_session(root: Path, sid: str, events, case=None) -> Path:
    d = root / sid
    d.mkdir(parents=True)
    (d / "session.json").write_text(
        json.dumps(
            {
                "session_id": sid,
                "created_at": "2026-11-14T10:00:00+00:00",
                "params": {"language": "hi"},
                "events": events,
            }
        )
    )
    if case is not None:
        (d / "case.json").write_text(json.dumps(case))
    return d


def case(tier, flags=(), gaps=(), outcome="completed", degraded=()):
    return {
        "status": "ready",
        "tier": tier,
        "call_outcome": outcome,
        "degraded_turns": list(degraded),
        "result": {
            "products": [{"flags": [{"rule_id": r} for r in flags], "gaps": [{"rule_id": r} for r in gaps]}],
            "case_flags": [],
            "case_gaps": [],
        },
    }


def gold(cid, cls, tier, *, outcome="completed", kind="k", call=(), gap=()):
    return {
        "id": cid,
        "card_id": cid,
        "kind": kind,
        "class": cls,
        "expected_outcome": outcome,
        "expected_tier": tier,
        "refer_grounds_from_call": [{"rule": r, "because": "-"} for r in call],
        "refer_grounds_from_record": [],
        "gap_grounds": [{"rule": r, "because": "-"} for r in gap],
    }


def scored(tmp_path, sessions_spec, golds):
    root = tmp_path / "sessions"
    log = tmp_path / "log.csv"
    with log.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "time", "card_id", "speaker_initials", "language", "setup", "session_id", "note"])
        for sid, card_id, events, c in sessions_spec:
            write_session(root, sid, events, c)
            w.writerow(["d", "t", card_id, "XX", "hi", "", sid, ""])
    g = tmp_path / "gold.jsonl"
    g.write_text("\n".join(json.dumps(x) for x in golds))
    from samajh.human.sessions import load_call_log

    ss = load_sessions([root], tmp_path)
    attach_gold(ss, load_gold(g), load_call_log(log))
    return ss


SID = ["20261114T100000-00000000000" + str(i) for i in range(10)]


def test_degraded_turn_voids_session_and_excludes_it_from_class_rates(tmp_path):
    ss = scored(
        tmp_path,
        [
            (SID[0], "C1", [bot(0), cust(1, 0)], case("refer")),
            (SID[1], "C2", [bot(0), cust(1, 0, degraded=True)], case("refer")),
        ],
        [gold("C1", "problem", "refer"), gold("C2", "problem", "refer")],
    )
    text = score_mod.report(ss, ["x"], CUTS, None)
    assert "| problem | 1 | referred (completed) | " + per100(1, 1) in text
    assert f"Void sessions: {per100(1, 2)}. Ids: {SID[1]}." in text


def test_case_degraded_turns_also_void(tmp_path):
    ss = scored(
        tmp_path,
        [(SID[0], "C1", [bot(0), cust(1, 0)], case("refer", degraded=[1]))],
        [gold("C1", "problem", "refer")],
    )
    assert ss[0].void()


def test_card_mismatch_is_no_match_and_missed_problem(tmp_path):
    ss = scored(
        tmp_path, [(SID[0], "C1", [bot(0), cust(1, 0)], case("clear"))], [gold("C1", "problem", "refer")]
    )
    assert score_mod.match(ss[0]) is False
    text = score_mod.report(ss, ["x"], CUTS, None)
    assert "| problem | 1 | missed (completed, tier not refer) | " + per100(1, 1) in text


def test_grounds_matched_missing_unmappable_and_extra(tmp_path):
    ss = scored(
        tmp_path,
        [(SID[0], "C1", [bot(0), cust(1, 0)], case("refer", flags=["kind", "consent"]))],
        [gold("C1", "problem", "refer", call=["kind", "premium", "not_a_rule"])],
    )
    g = score_mod.grounds(ss[0])
    assert g["matched"] == ["kind"] and g["missing"] == ["premium"] and g["unmappable"] == ["not_a_rule"]
    assert g["n"] == 2 and g["extra"] == ["consent"]


def test_gap_ground_matches_a_gap(tmp_path):
    ss = scored(
        tmp_path,
        [(SID[0], "C1", [bot(0), cust(1, 0)], case("understanding_gap", gaps=["cover"]))],
        [gold("C1", "knowledge_gap_only", "understanding_gap", gap=["cover"])],
    )
    assert score_mod.grounds(ss[0])["matched"] == ["cover"]


def test_unmatched_session_is_no_card(tmp_path):
    ss = scored(
        tmp_path, [(SID[0], "ZZ", [bot(0), cust(1, 0)], case("clear"))], [gold("C1", "problem", "refer")]
    )
    assert ss[0].gold is None
    assert "| no card |" in score_mod.report(ss, ["x"], CUTS, None)


def test_wrong_party_loan_named(tmp_path):
    ss = scored(
        tmp_path,
        [
            (
                SID[0],
                "W1",
                [
                    bot(0, key="right_party.ask", step="right_party_check"),
                    cust(1, 0),
                    bot(2, key="context.loan", step="x", outcome="wrong_party"),
                ],
                None,
            ),
            (
                SID[1],
                "W2",
                [
                    bot(0, key="right_party.ask", step="right_party_check"),
                    cust(1, 0),
                    bot(2, key="close.bye", step="close", outcome="wrong_party"),
                ],
                None,
            ),
        ],
        [
            gold("W1", "procedural", None, outcome="wrong_party"),
            gold("W2", "procedural", None, outcome="wrong_party"),
        ],
    )
    assert [s.loan_named() for s in ss] == [True, False]
    assert all(score_mod.match(s) for s in ss)
    text = score_mod.report(ss, ["x"], CUTS, None)
    assert "| procedural | 2 | loan named | " + per100(1, 2) in text


def test_per100_uses_wilson():
    lo, hi = wilson(3, 10)
    assert per100(3, 10) == f"30 per 100 (3/10; 95% CI {100 * lo:.0f}-{100 * hi:.0f})"
    assert per100(0, 0) == "n/a (n = 0)"


def test_spread_median_p90_max():
    s = spread([10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110])
    assert s == {"median": 60, "p90": 100, "max": 110, "n": 11}


def test_split_take_counts_once_and_as_split(tmp_path):
    events = [
        bot(0, listen="open"),
        cust(1, 0, superseded=True, pauses=[300]),
        bot(2, superseded=True),
        cust(3, 0, pauses=[1200, 300]),
        bot(4),
    ]
    ss = scored(tmp_path, [(SID[0], "C1", events, case("clear"))], [gold("C1", "no_problem", "clear")])
    assert [c["seq"] for c in ss[0].customers()] == [3]
    text = score_mod.pauses(ss, CUTS)
    assert "| open | 1100.0 | 1 | 1 | 1 | 0 |" in text
    assert "| mic | 1 | 0 | 0 | 0 | 1 | 0 |" in text


def test_talk_over_counted(tmp_path):
    br = {"bot_start_ms": 900.0, "talk_over": [{"start_ms": 100, "ms": 250}, {"start_ms": 900, "ms": 150}]}
    ss = scored(
        tmp_path,
        [(SID[0], "C1", [bot(0, browser=br), cust(1, 0), bot(2, browser={"talk_over": []})], case("clear"))],
        [gold("C1", "no_problem", "clear")],
    )
    out = "\n".join(score_mod.talk_over(ss))
    assert "with browser data: 2; with >= 1 talk-over run: 1; runs: 2; total 400 ms" in out


def test_ledger_504_then_200_counted(tmp_path):
    ss = scored(
        tmp_path,
        [(SID[0], "C1", [bot(0), cust(1, 0, cache_key="K1")], case("clear"))],
        [gold("C1", "no_problem", "clear")],
    )
    ledger = tmp_path / "ledger.jsonl"
    rows = [
        {
            "provider": "gnani",
            "kind": "stt",
            "status": 504,
            "cache_key": "K1",
            "ts": "2026-11-14T10:00:01+00:00",
        },
        {
            "provider": "gnani",
            "kind": "stt",
            "status": 200,
            "cache_key": "K1",
            "ts": "2026-11-14T10:00:31+00:00",
        },
        {
            "provider": "gnani",
            "kind": "stt",
            "status": 200,
            "cache_key": "K1",
            "ts": "2026-11-15T10:00:00+00:00",
        },
        {
            "provider": "gnani",
            "kind": "stt",
            "status": "cache_hit",
            "cache_key": "K1",
            "ts": "2026-11-14T10:00:40+00:00",
        },
    ]
    ledger.write_text("\n".join(json.dumps(r) for r in rows))
    out = "\n".join(score_mod.stt_health(ss, score_mod.read_ledger(ledger)))
    assert "1 readings found, 1 with more than one HTTP attempt; attempt statuses: 200: 1, 504: 1" in out


def test_two_readings_are_four_disjoint_counts(tmp_path):
    def two(agreed, ok, error=None):
        sec = {"role": "second", "model": "prisma-v2.5", "ok": ok, "error": error, "text": ""}
        c = cust(1, 0, second=sec)
        c["readings_agreed"] = agreed
        return c

    spec = [
        (SID[0], "C1", [bot(0), two(True, True)], None),
        (SID[1], "C1", [bot(0), two(False, True)], None),
        (SID[2], "C1", [bot(0), two(False, False, "timeout")], None),  # missing, not "differed"
        (SID[3], "C1", [bot(0), two(None, True)], None),
    ]
    out = "\n".join(score_mod.two_readings(scored(tmp_path, spec, [])))
    assert (
        "Turns with two readings: 4; both read and agreed: 1; both read and differed: 1; "
        "second reading missing: 1 (timeout: 1); null (no figure in either reading): 1." in out
    )


def test_latency_split_by_source_with_classifier_rows(tmp_path):
    second = {"role": "second", "model": "prisma-v2.5", "ok": True, "text": ""}
    c = cust(1, 0, second=second)
    c["latency"]["second_stt_ms"] = 2500.0
    c["classifier"]["wait_ms"] = 150.0
    f = cust(3, 2, source="file", stt_ms=700.0)
    f["classifier"] = {"ran": True, "label": None, "degraded": True, "latency_ms": 900.0}
    events = [bot(0), c, bot(2, browser={"bot_start_ms": 1234.0}), f, bot(4)]
    lat = "\n".join(score_mod.latency(scored(tmp_path, [(SID[0], "C1", events, None)], [])))
    assert "| bot_start_ms (browser) | mic | 1234 | 1234 | 1234 | 1 |" in lat
    assert "| STT primary (stt_ms) | mic | 100 | 100 | 100 | 1 |" in lat
    assert "| STT primary (stt_ms) | file | 700 | 700 | 700 | 1 |" in lat
    assert f"| {score_mod.WAIT} | mic | 150 | 150 | 150 | 1 |" in lat
    assert f"| {score_mod.WAIT} | file | n/a (not logged)" in lat
    assert f"| {score_mod.BEGIN} | file | 900 | 900 | 900 | 1 |" in lat
    assert "| STT second (second_stt_ms) | mic | 2500 | 2500 | 2500 | 1 |" in lat
    assert "void sessions included" in lat
    assert "Classifier labels (turns where it ran): (no label, degraded): 1, yes: 1; degraded: 2." in lat


def test_old_format_session_loads_and_says_not_logged(tmp_path):
    old = {
        "seq": 1,
        "at": 1.0,
        "type": "customer",
        "source": "file",
        "reply_to": 0,
        "transcript": "haan",
        "readings": [{"role": "primary", "model": "prisma-v3.0", "text": "haan"}],
    }
    ss = scored(tmp_path, [(SID[0], "C1", [{"seq": 0, "type": "bot", "lines": []}, old], None)], [])
    text = score_mod.report(ss, ["x"], CUTS, None)
    assert f"| {score_mod.WAIT} | all | n/a (not logged)" in text
    assert "| bot_start_ms (browser) | file | n/a (not logged)" in text
    assert "Ledger: n/a (not logged)" in text
    assert "prisma-v3.0 http_status: not logged: 1" in text


def test_http_status_labels(tmp_path):
    a = cust(1, 0, http_status=None)
    a["readings"][0]["cache_hit"] = True
    b = cust(1, 0, http_status=None)
    b["readings"][0].update(ok=False, error="gnani_busy")
    ss = scored(tmp_path, [(SID[0], "C1", [bot(0), a], None), (SID[1], "C1", [bot(0), b], None)], [])
    out = "\n".join(score_mod.stt_health(ss, None))
    assert "prisma-v3.0 http_status: cache hit: 1, failed, no status: 1" in out


def test_failed_steps_counted(tmp_path):
    err = {"seq": 2, "at": 2.0, "type": "error", "stage": "stt", "status": 503, "code": "gnani_busy"}
    err2 = {"seq": 3, "at": 3.0, "type": "error", "stage": "tts", "status": 502, "code": "upstream"}
    ss = scored(tmp_path, [(SID[0], "C1", [bot(0), cust(1, 0), err, dict(err, seq=4), err2], None)], [])
    out = "\n".join(score_mod.failed_steps(ss))
    assert (
        "Error events (stage / code / HTTP status to the phone): 3; stt / gnani_busy / 503: 2, tts / upstream / 502: 1."
        in out
    )
    assert f"- {SID[0]}: 3" in out


def test_ledger_window_counts_rows_without_cache_key(tmp_path):
    ss = scored(tmp_path, [(SID[0], "C1", [bot(0), cust(1, 0, cache_key="K1")], None)], [])
    rows = [
        {
            "provider": "gnani",
            "kind": "stt",
            "status": 504,
            "cache_key": None,
            "ts": "2026-11-14T10:00:02+00:00",
        },
        {
            "provider": "gnani",
            "kind": "stt",
            "status": 200,
            "cache_key": "K1",
            "ts": "2026-11-14T10:00:03+00:00",
        },
        {
            "provider": "gnani",
            "kind": "stt",
            "status": 429,
            "cache_key": "X",
            "ts": "2026-11-14T09:00:00+00:00",
        },
        {
            "provider": "gnani",
            "kind": "tts",
            "status": 500,
            "cache_key": "T",
            "ts": "2026-11-14T10:00:04+00:00",
        },
    ]
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("\n".join(json.dumps(r) for r in rows))
    out = "\n".join(score_mod.stt_health(ss, score_mod.read_ledger(ledger)))
    assert "time windows (created_at to last event + 120 s), by status: 200: 1, 504: 1." in out
    assert "other process using the account" in out


def test_grounds_dedupe_and_record_column(tmp_path):
    g = gold("C1", "problem", "refer", call=["kind", "kind", "premium"])
    g["refer_grounds_from_record"] = [{"rule": "bundling"}, {"rule": "loan_funded"}, {"rule": "bundling"}]
    ss = scored(
        tmp_path, [(SID[0], "C1", [bot(0), cust(1, 0)], case("refer", flags=["kind", "bundling"]))], [g]
    )
    gr = score_mod.grounds(ss[0])
    assert gr["n"] == 2 and gr["matched"] == ["kind"]
    assert gr["record_n"] == 2 and gr["record_matched"] == ["bundling"]
    assert "| 1 of 2 | premium |  | 1 of 2 |" in score_mod.report(ss, ["x"], CUTS, None)


def test_pause_note_under_200(tmp_path):
    ss = scored(tmp_path, [(SID[0], "C1", [bot(0), cust(1, 0)], None)], [])
    assert "Pauses under 200 ms are not measured." in "\n".join(score_mod.pauses(ss, CUTS))


def test_score_cli_writes_report(tmp_path):
    write_session(tmp_path / "s", SID[0], [bot(0), cust(1, 0)], case("clear"))
    out = tmp_path / "r.md"
    assert (
        main(
            [
                "score",
                "--sessions",
                str(tmp_path / "s"),
                "--cards",
                str(tmp_path / "none"),
                "--log",
                str(tmp_path / "none.csv"),
                "--ledger",
                str(tmp_path / "none"),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    assert "Sessions: 1; counted customer turns: 1" in out.read_text()


def test_wer_and_cer_counts():
    assert word_counts("एक दो तीन चार", "एक दो पाँच चार") == (1, 4)
    assert word_counts("Haan, ji.", "haan ji") == (0, 2)
    assert char_counts("ab cd", "abce") == (1, 4)


def test_refs_template_skips_year_answer_and_keeps_references(tmp_path):
    events = [
        bot(0, key="identity.year", step="second_check"),
        cust(1, 0, text="secret"),
        bot(2, key="recall.ask"),
        cust(3, 2, text="pachaas hazaar"),
    ]
    d = write_session(tmp_path / "s", SID[0], events)
    out = tmp_path / "refs.csv"
    sessions = load_sessions([d], tmp_path)
    from samajh.server import samajh_dialogue

    year_step = samajh_dialogue._YEAR_STEP
    sessions[0].events[0]["lines"][0]["tags"]["step"] = year_step
    assert refs(sessions, out) == 1
    rows = list(csv.DictReader(out.open()))
    assert rows[0]["turn"] == "3" and rows[0]["asked_key"] == "recall.ask" and "secret" not in out.read_text()
    rows[0]["reference"] = "पचास हज़ार"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    refs(sessions, out)
    assert next(iter(csv.DictReader(out.open())))["reference"] == "पचास हज़ार"


def test_wer_report_amount_accuracy_on_session_rows(tmp_path):
    second = {
        "role": "second",
        "model": "prisma-v2.5",
        "ok": True,
        "text": "पचास हज़ार",
        "literal": "पचास हज़ार",
    }
    d = write_session(tmp_path / "s", SID[0], [bot(0), cust(1, 0, text="₹40,000", second=second)])
    out = tmp_path / "refs.csv"
    refs(load_sessions([d], tmp_path), out)
    rows = list(csv.DictReader(out.open()))
    rows[0]["reference"] = "पचास हज़ार"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    text = wer_report(out, [tmp_path / "s"], tmp_path)
    assert "| prisma-v3.0 text | 1 | 1.000 (2/2) |" in text and per100(0, 1) in text
    assert "| prisma-v2.5 literal | 1 | 0.000 (0/2) |" in text and per100(1, 1) in text


# ---------------------------------------------------------------- notes


class FakeClient:
    def __init__(self):
        self.calls = []

    def stt(self, audio, options):
        self.calls.append(options.model)
        call = SimpleNamespace(cache_hit=False, est_credits=0.01)
        return SimpleNamespace(text=f"text {options.model}", literal=None, call=call)


def sine_wav(path: Path, seconds: float = 1.0, rate: int = 16000) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(
            b"".join(
                struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate)))
                for i in range(int(seconds * rate))
            )
        )


needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def test_notes_refuses_out_inside_tracked_tree(tmp_path, capsys):
    (tmp_path / "in").mkdir()
    target = REPO / "samajh" / "human_notes_should_not_exist"
    assert main(["notes", "--in", str(tmp_path / "in"), "--lang", "hi", "--out", str(target)]) == 2
    assert not target.exists()
    assert "refused" in capsys.readouterr().err


@pytest.mark.skipif(
    not (REPO.parent / REPO.name.upper()).exists() and not Path(str(REPO).upper()).exists(),
    reason="case-sensitive filesystem",
)
def test_check_out_refuses_other_case_spelling_of_repo():
    other = Path(str(REPO).upper()) / "SAMAJH" / "x"
    with pytest.raises(notes_mod.Refused):
        notes_mod.check_out(other)


def test_check_out_allows_ignored_and_outside_paths(tmp_path):
    notes_mod.check_out(tmp_path / "x")
    ignored = subprocess.run(
        ["git", "-C", str(REPO), "check-ignore", "-q", ".samajh-human/notes/x"], check=False
    ).returncode
    if ignored == 0:
        notes_mod.check_out(REPO / ".samajh-human" / "notes" / "x")


@needs_ffmpeg
def test_notes_writes_four_readings_and_keeps_reference(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    sine_wav(src / "a.wav")
    (src / "bad.ogg").write_bytes(b"not audio")
    out = tmp_path / "out"
    fake = FakeClient()
    lines: list[str] = []
    run = lambda: notes_mod.run_notes(
        src, "hi", out, max_credits=10, dry_run=False, client_factory=lambda: fake, echo=lines.append
    )
    assert run() == 0
    readings = [json.loads(x) for x in (out / "readings.jsonl").read_text().splitlines()]
    assert len(readings) == 4 and sorted(fake.calls) == ["prisma-v2.5"] * 2 + ["prisma-v3.0"] * 2
    assert {(r["condition"], r["model"]) for r in readings} == {
        (c, m) for c in ("16k", "8k") for m in ("prisma-v3.0", "prisma-v2.5")
    }
    assert (out / "audio" / "a.16k.wav").exists() and (out / "audio" / "a.8k.wav").exists()
    with wave.open(str(out / "audio" / "a.8k.wav")) as w:
        assert w.getframerate() == 8000
    assert any("skip bad.ogg" in x for x in lines)
    rows = list(csv.DictReader((out / "references.csv").open()))
    rows[0]["reference"] = "typed"
    rows.append(dict(rows[0], note="gone", reference="old typed"))  # a note not in this run
    with (out / "references.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with (out / "readings.jsonl").open("a") as f:
        f.write(json.dumps({"note": "gone", "condition": "16k", "model": "prisma-v3.0", "ok": True}) + "\n")
    run()
    refs_after = {r["note"]: r["reference"] for r in csv.DictReader((out / "references.csv").open())}
    assert refs_after == {"a": "typed", "gone": "old typed"}
    kept_readings = [json.loads(x) for x in (out / "readings.jsonl").read_text().splitlines()]
    assert len(kept_readings) == 5 and sum(r["note"] == "gone" for r in kept_readings) == 1


@needs_ffmpeg
def test_notes_dry_run_and_credit_cap_make_no_call(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    sine_wav(src / "a.wav", seconds=2.0)
    fake = FakeClient()
    assert (
        notes_mod.run_notes(
            src,
            "hi-en",
            tmp_path / "o",
            max_credits=10,
            dry_run=True,
            client_factory=lambda: fake,
            echo=lambda _: None,
        )
        == 0
    )
    with pytest.raises(notes_mod.Refused):
        notes_mod.run_notes(
            src,
            "hi-en",
            tmp_path / "o2",
            max_credits=0.05,
            dry_run=False,
            client_factory=lambda: fake,
            echo=lambda _: None,
        )
    assert fake.calls == [] and not (tmp_path / "o2").exists()


@needs_ffmpeg
def test_notes_wer_reads_readings_beside_csv(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    sine_wav(src / "a.wav")
    out = tmp_path / "out"
    notes_mod.run_notes(
        src, "hi", out, max_credits=10, dry_run=False, client_factory=FakeClient, echo=lambda _: None
    )
    rows = list(csv.DictReader((out / "references.csv").open()))
    rows[0]["reference"] = "text prisma-v3.0"
    with (out / "references.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    text = wer_report(out / "references.csv", [], tmp_path)
    assert "| prisma-v3.0 text 8k | 1 | 0.000 (0/2) |" in text
    assert "| prisma-v2.5 text 16k | 1 | 0.500 (1/2) |" in text


def test_ended_early_and_no_case_are_not_misses(tmp_path):
    ss = scored(
        tmp_path,
        [
            (SID[0], "C1", [bot(0), cust(1, 0)], case("refer")),
            (SID[1], "C2", [bot(0), cust(1, 0)], case("clear")),
            (SID[2], "C3", [bot(0), cust(1, 0)], case("incomplete", outcome="no_go_ahead")),
            (SID[3], "C4", [bot(0), cust(1, 0)], None),
            (SID[4], "K1", [bot(0), cust(1, 0)], case("refer")),
        ],
        [gold(c, "problem", "refer") for c in ("C1", "C2", "C3", "C4")]
        + [gold("K1", "knowledge_gap_only", "understanding_gap", kind="kg")],
    )
    text = score_mod.report(ss, ["x"], CUTS, None)
    assert "| problem | 4 | referred (completed) | " + per100(1, 4) in text
    assert "| problem | 4 | missed (completed, tier not refer) | " + per100(1, 4) in text
    assert "| problem | 4 | ended early or no case | " + per100(2, 4) in text
    assert "| knowledge_gap_only | 1 | completed, other tier | " + per100(0, 1) in text
    assert "| kg | knowledge_gap_only | 1 | referred (completed) | " + per100(1, 1) in text
    assert "completed / refer" in text


def test_null_expected_tier_renders_dash(tmp_path):
    ss = scored(
        tmp_path,
        [(SID[0], "W1", [bot(0), cust(1, 0)], None)],
        [gold("W1", "procedural", None, outcome="wrong_party")],
    )
    assert "wrong_party / - |" in score_mod.report(ss, ["x"], CUTS, None)
