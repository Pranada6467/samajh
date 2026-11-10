"""The run: every cell once, nothing paid twice, clean stops, and no result reused for another request."""

from __future__ import annotations

from collections import Counter

import pytest
from evalkit_bench import ROWS, write_manifest

from samajh.clients.errors import CapExceeded, LockTimeout, ServerError
from samajh.evalkit.runner import current_rows, jobs, run_spend

# 16 items x 2 conditions x 2 models, plus the fold-0 half (8 items) under babble10 on v3.0.
CELLS = 16 * 4 + 8
CLIPS = 16


def test_a_full_run_transcribes_every_cell_once(bench):
    summary = bench.run()
    assert (summary.planned, summary.transcribed, summary.voiced) == (CELLS, CELLS, CLIPS)
    assert (summary.pending, summary.errors, summary.stopped) == (0, 0, None)
    assert len(bench.client.stt_calls) == CELLS and len(bench.client.tts_calls) == CLIPS
    assert len(set(bench.client.stt_calls)) == CELLS


def test_a_second_run_makes_no_calls(bench):
    bench.run()
    calls = len(bench.client.stt_calls), len(bench.client.tts_calls)
    summary = bench.run()
    assert (summary.already_done, summary.transcribed, summary.voiced) == (CELLS, 0, 0)
    assert (len(bench.client.stt_calls), len(bench.client.tts_calls)) == calls


def test_a_crash_resumes_without_repeating_a_paid_call(bench):
    real_stt = bench.client.stt

    def dying_stt(audio, options):
        if len(bench.client.stt_calls) == 30:
            raise KeyboardInterrupt
        return real_stt(audio, options)

    bench.client.stt = dying_stt
    with pytest.raises(KeyboardInterrupt):
        bench.run()
    bench.client.stt = real_stt
    summary = bench.run()
    assert summary.pending == 0 and summary.already_done == 30
    assert len(bench.client.stt_calls) == CELLS and len(set(bench.client.stt_calls)) == CELLS
    assert len(bench.client.tts_calls) == CLIPS


def test_the_budget_stops_the_run_and_a_larger_one_finishes_it(bench):
    first = bench.run(budget_credits=0.2)
    assert first.stopped is not None and "budget" in first.stopped
    assert first.pending > 0 and first.spent_credits <= 0.2
    assert run_spend(bench.store, bench.ledger) == pytest.approx(first.spent_credits)
    second = bench.run()
    assert second.pending == 0 and second.stopped is None
    assert len(set(bench.client.stt_calls)) == len(bench.client.stt_calls) == CELLS
    assert len(bench.client.tts_calls) == CLIPS


def test_spend_is_what_the_ledger_holds_for_this_run(bench):
    summary = bench.run()
    assert summary.spent_credits == pytest.approx(bench.ledger.total_credits())
    assert run_spend(bench.store, bench.ledger) == pytest.approx(bench.ledger.total_credits())


def test_the_clients_credit_cap_stops_the_run_cleanly(bench):
    bench.client.fail_next = [CapExceeded(unit="credits", cap=1, spent=1, estimate=0.1)]
    summary = bench.run()
    assert summary.stopped is not None and "CapExceeded" in summary.stopped
    assert bench.run().pending == 0


def test_a_failed_cell_is_recorded_skipped_and_retried_on_the_next_run(bench):
    bench.run(max_items=1)
    bench.client.fail_next = [ServerError(status=504, code="UPSTREAM_TIMEOUT", message="slow", attempts=5)]
    first = bench.run()
    assert (first.errors, first.pending, first.stopped) == (1, 1, None)
    assert [row.error for row in bench.store.error_rows()] == ["ServerError"]
    second = bench.run()
    assert (second.transcribed, second.pending) == (1, 0)


def test_cells_failing_in_a_row_stop_the_run(bench):
    bench.client.fail_next = [ServerError(status=504, code=None, message="down", attempts=5)] * 50
    summary = bench.run(max_consecutive_errors=3)
    assert summary.errors == 3 and summary.stopped == "3 cells failed in a row"


def test_a_busy_lock_is_waited_out(bench):
    bench.client.fail_next = [LockTimeout("busy"), LockTimeout("busy")]
    assert bench.run().pending == 0


def test_a_lock_that_stays_busy_stops_the_run(bench):
    bench.client.fail_next = [LockTimeout("busy")] * 3
    summary = bench.run()
    assert summary.stopped == "the Gnani lock stayed busy" and summary.transcribed == 0


def test_each_condition_sends_its_own_audio(bench):
    bench.run()
    rows = bench.store.stt_rows()
    for row in rows:
        assert row.text == f"heard {row.audio_sha256[:12]}"
    per_clip = Counter((row.clip_sha256, row.condition, row.audio_sha256) for row in rows)
    audio_of = {(clip, condition): audio for clip, condition, audio in per_clip}
    assert len(audio_of) == len(per_clip)
    for (clip, condition), audio in audio_of.items():
        assert (audio == clip) == (condition == "clean16k")
    assert len(set(audio_of.values())) == len(audio_of)


def test_max_items_runs_a_prefix_of_the_manifest(bench):
    summary = bench.run(max_items=3)
    assert {row.item_id for row in bench.store.stt_rows()} == {row["id"] for row in ROWS[:3]}
    assert summary.pending == 0


def test_editing_a_condition_reruns_its_cells_and_drops_the_stale_results(bench):
    bench.run()
    before = {row.fingerprint for row in bench.store.stt_rows()}
    bench.raw["conditions"]["babble10"][0]["snr_db"] = 5
    summary = bench.run()
    assert (summary.already_done, summary.transcribed, summary.voiced) == (CELLS - 8, 8, 0)
    current = current_rows(bench.store, jobs(bench.items, bench.experiment))
    assert len(current) == CELLS
    fresh = [row for row in current.values() if row.fingerprint not in before]
    assert len(fresh) == 8 and all(row.steps[0]["snr_db"] == 5 for row in fresh)
    assert len(bench.store.stt_rows()) == CELLS + 8


def test_a_changed_text_is_voiced_and_transcribed_again(bench):
    bench.run()
    changed = [dict(row) for row in ROWS]
    changed[0]["text"] = "a different sentence"
    bench.digest = write_manifest(bench.manifest, changed)
    bench.raw["manifest_sha256"] = bench.digest
    summary = bench.run()
    cells_of_item = sum(1 for job in jobs(bench.items, bench.experiment) if job.item.id == ROWS[0]["id"])
    assert (summary.voiced, summary.transcribed) == (1, cells_of_item)
    current = current_rows(bench.store, jobs(bench.items, bench.experiment))
    assert len(current) == CELLS
    assert len({row.clip_sha256 for row in bench.store.stt_rows() if row.item_id == ROWS[0]["id"]}) == 2


def test_a_cleared_audio_store_is_refilled_from_the_client(bench):
    bench.run(max_items=1)
    for path in (bench.audio_root / "clips").iterdir():
        path.unlink()
    bench.raw["conditions"]["babble10"][0]["snr_db"] = 5
    summary = bench.run(max_items=1)
    assert (summary.transcribed, summary.pending) == (1, 0)
    assert len(bench.client.tts_calls) == 2
    assert len(list((bench.audio_root / "clips").iterdir())) == 1
