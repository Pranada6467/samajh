# P3b fix round 2: report

2026-11-10, P3b sub-orchestrator (resumed from disk after the first worker stopped at a usage limit). Working tree at 993edf4 plus uncommitted edits; nothing is committed. Builders: Opus medium. Verifiers: Opus high, separate agents that wrote none of the code, each on its own inputs.

## Status

- **`uv run pytest tests/ops -q`: 288 passed.** `ruff check samajh/ops tests/ops`: clean.
- **Independent verification** after the task list (`verify-P3b-r2.md`), all in `references/reviews/iter2/`:
  - Round 3 (`verify-P3b-r3.md`): sound with conditions, five defects.
  - Round 4 (`verify-P3b-r4.md`): sound with conditions. All five round-3 defects are fixed on new inputs: 61 hostile case files, 23 changes to brought-in sessions, 6 batches for the limits, 13 draw schedules at the 1.25 line, torn lines on all four logs, 15 mutations (13 caught). It found four smaller defects and two untested edges.
  - Round 5 (`verify-P3b-r5.md`, the round-4 fixes only): sound with conditions. The fixes held except in two narrow cases, which are open.
- **Pages re-rendered last**, from the working tree, into `references/pilots/p3b-artifacts/`. `RENDERED.md` there names the commit and the diff hash. They must be rendered once more after P3a lands.

## Each condition

| Condition | State | Checked by |
|---|---|---|
| Ingest never stops on a session; no orphan call file | Fixed: any error on one session is a skip with a reason, nothing written | Round 4: 61 new shapes, none raised |
| Every dialogue outcome has an attempt outcome | Fixed: read from `samajh.dialogue`; a test fails for a new outcome; a run skips that session with a reason | Rounds 3 and 4 added a fake outcome and saw the test fail |
| Never-drawn loan listed as outside the sample | Fixed | Round 3 |
| Session with no case file listed as skipped, with a reason | Fixed | Rounds 3 and 4 |
| No dropped, renumbered or duplicate attempt (order by time) | Fixed | Round 3: 118 sessions interleaved with runs; round 4: 104 attempts on a new book |
| Call dated before the sale or the draw refused | Fixed | Round 4: 10 of 10, each with a reason |
| Phone note says where the audio came from | Fixed: counted from `customer_audio`; absent reads "not recorded in the case file" | Round 3 |
| A phone session on a drawn loan is that loan's attempt | Fixed: needs the `book` block (addition A), rechecked against the book; after day 30 it is logged, shown, never counted, and the report gives the number | Rounds 3 and 4 |
| No "finding" for flag counts; lint | Fixed: the report key `findings` is now `rules` | 0 hits in views, keys, pages, README, CLI (rounds 3 and 4) |
| `report.timing` with late phone attempts | Fixed | Rounds 3 and 4 |
| Sampling statement | Fixed: see below | Round 4: six schedules at exactly 5/4 that floats get wrong are all narrow |
| Tests for M6 and M12 | Fixed | Both mutants caught (round 3) |
| Old probes | Left as they are | `p3b_sampler.py` raises TypeError (the sampler's `after` argument changed); `p3b_recount.py` and `p3b_r2_recount.py` read `findings`. They are the verifiers' files and the changes are not trivial. |
| Re-render and README | Done | See "Pages" |

**Additions.** A (the `book` block), B (`MAX_ATTEMPTS` in `samajh/ops/model.py`) and C (the two-readings line, the tile strip): checked in round 3. D (`speaker_confirmed`): checked in round 4; with it false, do-not-call, speak-to-a-person and call-back-later become `request_unconfirmed`, which is retried, has its own funnel row, counts towards the three attempts and is never in the do-not-call count. E: the five defects are fixed (round 4). F: done.

**Sampling choice.** Chances are "about the same" when the highest is at most 1.25 times the lowest, compared as exact fractions. Then the report says so, with the range, and shows unweighted shares with Wilson intervals. Otherwise it states the range, says the shares are unweighted counts of the calls analysed that do not estimate the share among all sales, and shows no interval. Shares are never weighted. Why 1.25: at that ratio an unweighted share is off by at most 5.6% of the difference between two groups' shares, and an unweighted interval is under 1% too narrow; round 3 checked the arithmetic.

**Fixed after round 4** (`tests/ops/test_ops_verifier_round5.py`, 10 tests, each seen to fail without its fix): a brought-in session whose folder is deleted is listed where it is and under "changed"; with no simulated attempt the limits no longer speak of "the simulation"; a skip or changed reason is at most 300 characters; an empty `result` is named as `result.loan_id`; tests for the equal-time chain edge and the "sold" tile.

## Pages

34 files plus `RENDERED.md`; 32 renders with no overflow, console error, banned word or written-out null. They show 7 referrals of 64 (the committed pages showed 11).

**A correction to the brief.** No committed code gives 11. The code of commit 4180556, which holds the old pages, and of each later commit, gives 7 on the same book, draws and scripted calls. The four calls that differ are customers who said they took nothing and then named the product as insurance when asked: a referral on the old pages, an understanding gap under the rule in the code. The likely cause, not confirmed, is that the old pages were rendered from a working tree with the rules mid-edit. `data/loanbook/README.md`, "The rendered pages", says this.

## Open and not verified

- **Round 5's failing input, verbatim:** "delete the sessions directory itself after the store holds 5 attempts and 3 outside calls, then call `ingest`". Nothing raises and no store file changes, but the attempt-log note says "The last ingest saw 0 phone session(s) and brought in every one (0 as attempts, 0 outside the sample)" while the limits say "8 phone session(s)". Not fixed.
- With 0 simulated attempts two fixed sentences still name simulation ("Calls marked Simulated were scripted; …", "… the simulated book's clock …"). Not fixed.
- **A damaged line in the middle of a log makes the store unreadable** until repaired by hand. Only a torn last line is handled.
- No page in the artifacts shows a phone call as an attempt in the sample, or a two-readings line: none of the 7 case files on this machine has a `book` block or two readings. Both are tested on synthetic case files only.
- No verifier rendered pages after round 3. `run --analysis llm` and ingest during a live call were not checked.
- For the coordinator to decide: `written_requested` from an unconfirmed speaker still ends the chain (it is not in addition D's list); a second session given the same call date is refused when it is earlier in the India day (round 3, claim 6).
- Older probes rerun today: `p3b_r3_ingest`, `chain`, `readings`, `p3b_r2_sampler`, `p3b_r4_hostile`, `limits`, `torn`: 0 failures. `p3b_r3_recount` matches on 54 of 55 states; the other is the schedule 1/3, 2/5, 5/12, where the probe's line 171 compares in floats. `p3b_r4_changes` reports 3: the deleted-folder case, where it expects the old behaviour, and two that round 4 lists as by design.

## Wording

The verifiers' lists in `verify-P3b-r4.md` and `verify-P3b-r5.md` win.

**May say:** "Ingest returned on 61 hostile case-file shapes, alone and together; each session folder ended in exactly one list, with a reason when skipped." "A session already brought in stays counted, and is listed as changed, when its case file changes or its folder is deleted." "Inclusion chances are compared as exact fractions; exactly 1.25 counts as narrow." "A torn last line in any log is set aside, and no entry is lost." "A phone call after day 30 is logged and shown, never counted." "The word 'finding' appears on no page."

**May not say:** "Ingest never stops" as a proven fact (say what was tried). "The store survives any damaged line." "The attempt-log note always agrees with the store." "No page mentions simulation when nothing was simulated." That a phone attempt in the sample is shown on the pages. "Tested with real customers." Any share as describing a real lender.
