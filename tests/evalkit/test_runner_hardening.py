"""Holes an independent review proved in the first version of the runner, each pinned by a test."""

from __future__ import annotations

import filelock
import pytest
from evalkit_bench import ROWS, write_manifest

from samajh.audio import steps as audio_steps
from samajh.clients._runtime import LedgerEntry
from samajh.evalkit.manifest import Item
from samajh.evalkit.plan import assign_voices
from samajh.evalkit.runner import RunStore, StoreBusy, SttRow, current_rows, jobs, run_spend
from samajh.evalkit.score import Prediction, Scorer, score
from samajh.types import Language

CELLS = 16 * 4 + 8


def test_cells_that_differ_only_in_format_or_language_are_separate_requests(bench):
    bench.raw["arms"] = [
        {
            "name": "formats",
            "conditions": ["phone"],
            "stt": [
                {"model": "prisma-v3.0", "format": "transcribe"},
                {"model": "prisma-v3.0", "format": "verbatim"},
                {"model": "prisma-v3.0", "format": "transcribe", "language": "indic-auto"},
                {"model": "prisma-v3.0", "format": "transcribe", "language": "item+en"},
            ],
        }
    ]
    planned = jobs(bench.items, bench.experiment)
    assert len({job.fingerprint for job in planned}) == len(planned) == 16 * 4
    summary = bench.run()
    assert summary.transcribed == 16 * 4 and len(set(bench.client.stt_calls)) == 16 * 4
    for row in bench.store.stt_rows():
        assert (row.request["format"], row.stt.language) == (row.stt.format, row.stt.language)
        assert (row.request["language"] == "indic-auto") == (row.stt.language == "indic-auto")


def test_another_voice_means_another_clip_and_new_transcripts(bench):
    bench.run()
    bench.raw["voices"]["hi"] = [{"model": "timbre-v3.0", "voice": "Kalpana"}]
    summary = bench.run()
    hindi_cells = sum(1 for job in jobs(bench.items, bench.experiment) if job.item.language == Language.hi)
    assert (summary.voiced, summary.transcribed) == (8, hindi_cells)
    current = current_rows(bench.store, jobs(bench.items, bench.experiment))
    assert {row.voice.voice for row in current.values() if row.language == Language.hi} == {"Kalpana"}


def test_two_items_with_the_same_text_keep_their_own_rows(bench):
    rows = [dict(row) for row in ROWS]
    rows[1]["text"] = rows[0]["text"]
    bench.digest = write_manifest(bench.manifest, rows)
    bench.raw["manifest_sha256"] = bench.digest
    bench.run()
    planned = jobs(bench.items, bench.experiment)
    current = current_rows(bench.store, planned)
    assert len(current) == len(planned)
    assert all(row.item_id == job.item.id for job in planned for row in [current[job.cell.key]])


def test_the_budget_also_stops_transcription(bench):
    bench.run(max_items=1)
    (bench.store.root / "stt.jsonl").unlink()
    voiced = run_spend(bench.store, bench.ledger)
    summary = bench.run(max_items=1, budget_credits=voiced + 0.012)
    assert summary.transcribed == 2 and summary.stopped is not None and "budget" in summary.stopped


def test_every_step_of_a_condition_is_applied(bench):
    bench.run()
    rate = {row.condition: bench.client.sample_rates[row.audio_sha256] for row in bench.store.stt_rows()}
    assert rate == {"clean16k": 16000, "phone": 8000, "babble10": 8000}


def test_spend_ignores_what_other_workers_paid(bench):
    bench.ledger.append(
        LedgerEntry(
            ts="2026-01-01T00:00:00+00:00",
            provider="gnani",
            kind="stt",
            model="other",
            status=200,
            attempt=1,
            seconds=0.1,
            cache_hit=False,
            cache_key="a-key-of-another-worker",
            est_credits=5.0,
        )
    )
    summary = bench.run()
    own = sum(row.est_credits for row in bench.store.stt_rows() + bench.store.voice_rows())
    assert summary.spent_credits == pytest.approx(own)
    assert run_spend(bench.store, bench.ledger) == pytest.approx(own)
    assert bench.ledger.total_credits() == pytest.approx(own + 5.0)


def test_a_torn_last_line_does_not_swallow_the_next_row(bench):
    bench.run(max_items=2)
    done = len(bench.store.stt_rows())
    with (bench.store.root / "stt.jsonl").open("ab") as f:
        f.write(b'{"fingerprint": "torn in a cra')
    summary = bench.run()
    assert summary.pending == 0
    assert len(bench.store.stt_rows()) == CELLS and summary.already_done == done
    assert len(current_rows(bench.store, jobs(bench.items, bench.experiment))) == CELLS


def test_a_call_paid_for_before_a_crash_is_counted_after_it(bench):
    bench.client.cache = {}
    real_add = bench.store.add

    def crash_on_the_third_transcript(row):
        if isinstance(row, SttRow) and len(bench.store.stt_rows()) == 2:
            raise KeyboardInterrupt
        real_add(row)

    bench.store.add = crash_on_the_third_transcript
    with pytest.raises(KeyboardInterrupt):
        bench.run()
    bench.store.add = real_add
    summary = bench.run()
    assert summary.pending == 0
    assert summary.spent_credits == pytest.approx(bench.ledger.total_credits())
    assert len(bench.client.cache) == CELLS + 16


def test_a_new_transform_version_reruns_the_cells_that_use_a_transform(bench, monkeypatch):
    bench.run()
    old = {row.fingerprint for row in bench.store.stt_rows()}
    monkeypatch.setattr(audio_steps, "TRANSFORM_VERSION", audio_steps.TRANSFORM_VERSION + 1)
    summary = bench.run()
    clean = sum(1 for job in jobs(bench.items, bench.experiment) if not job.steps)
    assert (summary.already_done, summary.transcribed) == (clean, CELLS - clean)
    current = current_rows(bench.store, jobs(bench.items, bench.experiment))
    assert len(current) == CELLS
    assert all((row.fingerprint in old) == (row.condition == "clean16k") for row in current.values())


def test_a_second_run_on_a_busy_store_is_refused(bench):
    bench.store.root.mkdir(parents=True)
    with filelock.FileLock(bench.store.root / ".run.lock"), pytest.raises(StoreBusy):
        bench.run()
    assert bench.client.tts_calls == []


def test_each_run_is_logged_with_its_tools(bench):
    bench.run(max_items=1)
    bench.run()
    first, second = RunStore(bench.store.root).run_rows()
    assert first.ffmpeg and first.transform_version == audio_steps.TRANSFORM_VERSION
    assert (first.transcribed, second.already_done) == (second.already_done, first.transcribed)
    assert second.transcribed == CELLS - first.transcribed and second.stopped is None
    assert not (bench.store.root / ".run.lock").exists()


def test_the_voice_seed_changes_who_speaks_what(bench):
    assignments = set()
    for seed in range(6):
        bench.raw["voice_seed"] = seed
        voices = assign_voices(bench.items, bench.experiment)
        assignments.add(tuple(voices[row["id"]].voice for row in ROWS))
    assert len(assignments) > 1


def test_a_boolean_never_matches_a_number(bench):
    item = Item(id="x", language=Language.hi, text="एक रुपया", gold={"amount_inr": 1})
    stt_row = next(iter(current_rows(bench.store, []).values()), None)
    assert stt_row is None
    bench.run(max_items=1)
    row = bench.store.stt_rows()[0].model_copy(update={"item_id": "x"})
    methods = {"true": lambda _h: Prediction(value=True), "one": lambda _h: Prediction(value=1)}
    got = {r.method: r.correct for r in score([item], [row], Scorer("s", "amount_inr", methods))}
    assert got == {"true": False, "one": True}
