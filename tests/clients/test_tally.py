from __future__ import annotations

import os
from pathlib import Path

import pytest

from samajh.clients._runtime import Ledger, LedgerEntry
from samajh.clients.errors import CapExceeded
from samajh.clients.gnani import GnaniClient
from samajh.clients.gnani.tally import LedgerTally, tally_for


def row(provider="gnani", kind="stt", credits=0.0, audio=None) -> LedgerEntry:
    return LedgerEntry(
        ts="2026-11-14T00:00:00Z",
        provider=provider,
        kind=kind,
        model="m",
        status=200,
        attempt=1,
        seconds=0.1,
        cache_hit=False,
        cache_key="k",
        est_credits=credits,
        audio_seconds=audio,
    )


def mixed(ledger: Ledger, n: int) -> None:
    for i in range(n):
        if i % 3 == 0:
            ledger.append(row(provider="openrouter", kind="chat", credits=0.0))
        elif i % 3 == 1:
            ledger.append(row(credits=0.1 * (i % 7)))
        else:
            ledger.append(row(kind="stt.stream", credits=0.013, audio=1.7))


def stream_sum(ledger: Ledger) -> float:
    return sum(
        e.audio_seconds or 0.0 for e in ledger.entries() if e.provider == "gnani" and e.kind == "stt.stream"
    )


def test_equals_full_parse_including_bad_lines(tmp_path):
    ledger = Ledger(tmp_path / "l.jsonl")
    mixed(ledger, 300)
    with open(ledger.path, "ab") as f:
        f.write(b"not json\n{}\n")
    mixed(ledger, 30)
    t = LedgerTally(ledger.path)
    assert t.gnani_credits() == ledger.total_credits()
    assert t.stream_seconds() == stream_sum(ledger)


def test_rows_from_another_writer_seen_next_call(tmp_path):
    path = tmp_path / "l.jsonl"
    t = LedgerTally(path)
    assert t.gnani_credits() == 0  # missing file
    mixed(Ledger(path), 10)
    first = t.gnani_credits()
    Ledger(path).append(row(credits=2.5))
    assert t.gnani_credits() == first + 2.5 == Ledger(path).total_credits()


def test_partial_last_line_waits_for_newline(tmp_path):
    path = tmp_path / "l.jsonl"
    Ledger(path).append(row(credits=1.0))
    line = row(credits=4.0).model_dump_json().encode()
    with open(path, "ab") as f:
        f.write(line[:20])
    t = LedgerTally(path)
    assert t.gnani_credits() == 1.0
    with open(path, "ab") as f:
        f.write(line[20:] + b"\n")
    assert t.gnani_credits() == 5.0


def test_truncation_and_replacement_rescan(tmp_path):
    path = tmp_path / "l.jsonl"
    mixed(Ledger(path), 20)
    t = LedgerTally(path)
    t.gnani_credits()
    path.write_bytes(b"")  # truncated
    Ledger(path).append(row(credits=0.5))
    assert t.gnani_credits() == 0.5
    other = tmp_path / "new.jsonl"
    mixed(Ledger(other), 40)
    os.replace(other, path)  # replaced by a longer file
    assert t.gnani_credits() == Ledger(path).total_credits()


def test_cap_refuses_on_tally(tmp_path):
    client = GnaniClient(api_key="k", credit_cap=10.0, state=tmp_path)
    Ledger(tmp_path / "ledger.jsonl").append(row(credits=9.5))
    client._check_cap(0.4)
    with pytest.raises(CapExceeded):
        client._check_cap(0.6)
    assert client.credits_spent() == 9.5


def test_clients_share_one_tally(tmp_path):
    a = GnaniClient(api_key="k", credit_cap=10.0, state=tmp_path)
    b = GnaniClient(api_key="k", credit_cap=10.0, state=tmp_path)
    assert a._tally is b._tally is tally_for(tmp_path / "ledger.jsonl")


def test_unchanged_large_ledger_second_call_reads_little(tmp_path):
    path = tmp_path / "l.jsonl"
    line = row(credits=0.01).model_dump_json().encode() + b"\n"
    path.write_bytes(line * 50_000)
    t = LedgerTally(path)
    assert t.gnani_credits() == Ledger(path).total_credits()
    before = t.bytes_read
    t.gnani_credits()
    assert t.bytes_read - before <= 64
    Ledger(path).append(row(credits=1.0))
    before = t.bytes_read
    t.gnani_credits()
    assert t.bytes_read - before <= 64 + len(line) + 10


def test_warm_ledger_then_spent(tmp_path: Path):
    Ledger(tmp_path / "ledger.jsonl").append(row(credits=0.25))
    c = GnaniClient(api_key="k", credit_cap=10.0, state=tmp_path)
    c.warm_ledger()
    assert c.credits_spent() == 0.25
