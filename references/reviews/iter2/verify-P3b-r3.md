# P3b fix round 2: independent verification (round 3)

Saved by the P3b sub-orchestrator on 2026-11-10 from the verifier's final message, unchanged. The five defects it lists were then worked on and checked again by another independent verifier: that check is in `verify-P3b-r4.md` (nothing is appended to this file; an earlier version of this note said it would be).

Verifier: independent, Opus. I wrote none of the code. No Gnani or OpenRouter calls, nothing sent to 8085/8086, no git writes, nothing written to the repo's `.samajh/`. The only repo files I added are `references/reviews/iter2/probes/p3b_r3_*.py`. Everything else (state, the 41 real session folders copied without audio, a repo copy for mutations) is under the scratchpad's `verifier/` folder.

HEAD was 993edf4 at both start and end. The ops code (`samajh/ops`, `web/review`) did not change during my run: the files' modification times are all before I started. `samajh/rules/checks.py` and `engine.py` became modified while I worked. My recounts use the same core on both sides, so no result depends on that.

## Verdict: sound with conditions

The chain, dates, window, recount, idempotency, readings line and tiles all hold on new inputs. Five defects remain. Four inputs make ingest raise. One session can be both "skipped" and counted. The report's limits contradict its phone calls. A float error decides the 1.25 boundary. A half-written log line corrupts the store.

## Claims

1. **Fails.** I tried 35 hostile shapes, each alone on a copy of a 110-loan batch (seed 4711), plus 40 sessions together and the 41 real copies. 29 shapes were skipped with a reason in words. 2 were linked, and both are legitimate (`readings_agreed: "yes"`; `recording.sha256: 5`). **4 raised and stopped ingest:**
   - A completed, ready case file on a drawn loan with a valid book block and `"models": {"extraction": "gpt-6"}` (or `["gpt-6"]`) gives `AttributeError: 'str' object has no attribute 'get'` in `sessions._analysis`. Only `ValueError`, `KeyError` and `TypeError` are caught.
   - The same file with `"started_at": "9999-12-31T23:59:59+00:00"` or `"0001-01-01T00:00:00+14:00"` gives `OverflowError: date value out of range` in `_one` (`case.started.astimezone(IST)`).
   - **"Exactly one place" fails.** Take a session already linked as a completed call. Its case file is later rebuilt ready with another analysis, for example `"models": {"extraction": {"model": "another-model"}}`. The next ingest lists it as skipped ("the case file's analysed call differs…; nothing was changed"). Its attempt stays counted. The page then says it "did not bring in 10: they are in no count here, not even the reach figures", and the attempt log shows the session both as an attempt and under "not brought in". The server rebuilds a case on POST, so this path is real.
2. **Holds.** In a copy, I added a fake value to `Outcome`. `test_every_dialogue_outcome_has_an_attempt_outcome` failed (`1 failed, 156 passed`).
3. **Holds, with one durability defect.**
   - Failed then ready works for a first attempt, a third (limit) attempt and an outside call (a never-drawn book loan): each became completed and analysed, with no orphan call file.
   - Ready then failed, and ready with another analysis, were each skipped with a reason; no store file changed apart from `ingest.json`.
   - A crash between saving the call and logging the supersede converges on the next ingest.
   - **Defect:** a crash in the middle of an append leaves a partial last line. The next append is glued onto it, and the store becomes unreadable. Reproduce: append `{"attempt_id": "D-2027-02-10/x/half", "draw_` with no newline to `attempts.jsonl`, then ingest one new session. `load_batch` and `python -m samajh.ops report` both fail with `ValidationError: 1 validation error for Attempt … Invalid JSON: expected ':' at line 1 column 47`.
4. **Holds.** A second and third ingest left store hashes and the report identical in 8 states. A second `run` (in-process and through the CLI) changed nothing. After a `run`, the next ingest may rewrite `ingest.json`, because a skipped session's reason now names the new last attempt. That change is legitimate.
5. **Holds.** A never-drawn loan with a book block, and one without, are both outside as "the loan was not drawn in this batch".
6. **Holds.** I checked from the raw files (numbers 1..k, times rising, nothing after a terminal outcome, at most 3, draw day, India day equal to the day count):
   - S1: 15 phone sessions, then the CLI `run`. The simulator continued the chains and added nothing after `do_not_call`, at the limit, or after a day-30 no-answer.
   - S2/S2b: 22 sessions after runs. Before the last attempt: skipped. After completed, terminal or at the limit: skipped. Same day 09:xx IST against a simulated 11:00: skipped. Same day 15:xx: linked, and the next run continued.
   - S3: 14 sessions in 6 shapes, including folder order opposite to time and a late-arriving earlier session.
   - S4: 118 random sessions interleaved with runs, giving 85 attempts (29 phone).
   - No completed call ever became "not reached".
   - **Consequence (by the contract, but worth knowing):** two sessions on one loan get the same call date when the server picks it before either is ingested. If the second is a day later on the wall clock but earlier in the day in India time, the retry is refused: "the call is dated 2027-01-27T09:27:00+05:30, not after … 2027-01-27T18:26:00+05:30".
7. **Holds.** All 8 refusals had a reason (sale date, day count, batch, draw, record id, not on the book, before the sale, before the draw). No negative day appeared anywhere.
8. **Holds.**
   - Day 31 completed: `completed_late`, not counted. Day 45 no-answer: `not_reached_in_time`.
   - A session started at 20:00 UTC with `call_date` = sale + 30 is logged at `…T01:30+05:30`, day 30, and counted.
   - The timing note reads "2 of 26 attempts were made after day 30 from the sale, all of them phone calls…".
9. **Holds.** See the recount table below.
10. **The counts hold; the wording fails.**
    - Microphone, file, both, none and absent were counted correctly: `1, 1, 1, 1, 27`, equal to my recount from the case files. The 7 real case files carry no `customer_audio` and are reported as "not recorded in the case file".
    - **But** in a batch with phone calls, the report still says "The loan book, the customers and the calls are synthetic and simulated…" and "Customer replies come from scripted phrase banks. They are text only: no speech was recorded or transcribed." Both lines appear on the rendered report next to the phone note.
11. **Partly holds.** Skipped sessions are on the attempt log and in the report, with the count of the last ingest. The sentence "they are in no count here" is false in the 1(c) case.
12. **Holds.**
    - "finding" appears 0 times and the banned list finds 0 hits in system text. I scanned 71 views over 6 states (phone, outside, late, wide sampling, decisions), every JSON key, `web/review` js/html/css, `data/loanbook/README.md`, the CLI output of ingest, verify and report, and 36 rendered pages.
    - The only hits are a customer's own words in transcripts, "Refund तो नहीं मिलता…".
    - Lint mutations M-r3-28, 29 and 30 were caught.
13. **Holds, except one float edge.**
    - I ran 11 schedules: exactly 1.25 (4/5 against 4/4) is narrow; 1.286 is wide; 1.222 is narrow; rate 1.0 alone, one draw at 5%, a draw with nobody eligible, and same-rate rounding (2.5×) all behave correctly. The range is always stated. A wide report shows no interval in the JSON or on the page.
    - The comment's arithmetic checks: bias factor 0.05573, Kish 1.0125, widening 0.62%.
    - **Failure:** draws at 1/3, 2/5 and 5/12 (exactly 5/4) compute a ratio of `1.2500000000000002` and are called wide. The statement then reads "(the highest is 1.25 times the lowest; this report shows intervals only when the highest is at most 1.25 times the lowest)".
14. **52 mutations: 44 caught, 8 survived.** M6 (`add_draw` chaining) and M12 (UTC time of day, and `india_day` in UTC) are now caught. Survived:
    - M-r3-36: `review.js` separator changed. No test reads `review.js`.
    - M-r3-50: the "sold" tile shows the eligible count. Only the demo state is tested, and there every sale is covered.
    - M-r3-07: `at <= last.at` changed to `<` (equal times accepted).
    - M-r3-09: `next_number` returns len+1 (equivalent in practice).
    - M-r3-11: the supersede guard on `completed_not_analysed` dropped (still blocked by the equality check).
    - M-r3-17: `0 <=` dropped from `in_window` (only a backup check).
    - M-r3-33: text shown when `ok` is false.
    - M-r3-49: tie for the most common gap goes to the last row.
15. **Holds.**
    - 15 reading shapes gave 30 amount-quote lines. All matched the view byte for byte and appeared in the rendered page text; one matched only after the browser collapsed white space. The shapes were: all four closings, `other`, missing, null and absent agreement, one reading, a timed-out second reading, empty text, odd unicode and HTML (`<b>` rendered as text), `followed_by: "banana"`, non-Prisma model names, and second reading listed first.
    - `readingsLine` computes nothing.
    - Notes: `readings_agreed` accepts `"yes"`, `"on"` and `1` as true (pydantic lax mode). A timed-out second reading is closed as "differ", which is what the case file records. A reading whose text contains " · " makes the line ambiguous.
16. **Holds.** The tiles equal the tables in all 10 recounted states and on 3 rendered report pages, including s_uncovered: sold 150, eligible 107. The synthetic label is on the strip, and the tiles show counts only.
17. **Tests:** `157 passed in 5.63s` at the start and `157 passed in 5.48s` at the end.
    - `p3b_r2_sampler`: 8,493 draws, 12,565 attempts, `FAILURES: 0`.
    - `p3b_r2_ingest`: runs. All its sessions become outside the sample, because its case files have no `book` block; that requirement is the deliberate change. `do_not_call` and `written_requested` no longer raise.
    - `p3b_r2_mixed_order`: prints nothing. It is vacuous now, because no phone attempt gets linked without a book block.
    - `p3b_r2_recount`: stops at line 143 with `KeyError: 'findings'`. The key is now `rules`, a legitimate rename. With only that key patched (in scratch), it checks 167 rows with 1 mismatch: it counts 16 raw `outside.jsonl` lines against 15 sessions, because one line is a supersede. The probe is stale; the report is right.
    - `p3b_r2_wording`: 0 banned hits, 0 "finding".
18. **Rendered.** I ran review-only servers on 8097 and 8098 and dumped page text with headless Chrome: 36 pages over 3 states. No "undefined", "NaN", "null" or empty brackets, no console errors, no banned words.

## Recount (`p3b_r3_recount.py`; core used only for tier, flags, gaps and summarise)

| State | Rows | Mismatches |
|---|---|---|
| A: 26 linked phone, late, rebuilds, outside | 124 | 0 |
| real copies + A | 124 | 0 |
| S1, S2, S2b, S3, S4 (phone and simulated interleaved) | 124 each | 0 |
| s_pages (A + simulated + 4 decisions) | 124 | 0 |
| s_readings (15 phone referrals) | 124 | 0 |
| s_uncovered (wide chances, 43 uncovered sales) | 124 | 0 |
| 11 sampling schedules | 124 each | 1 (the float edge in 13) |

## Not checked

`run --analysis llm`; ingest running at the same time as a live call; pages at phone width or in dark mode (I read text only); the committed `p3b-artifacts`.

## Wording

**May say:**
- "A loan's attempts stay in time order with unique numbers, whichever writes first. This was checked on phone sessions and simulated calls interleaved over four new books."
- "No attempt goes after a chain-ending outcome or beyond three attempts."
- "Calls dated before the sale or the draw, or with a book block that disagrees with the book, are refused with a reason."
- "A phone call after day 30 is logged and shown, never counted, and the report gives its number."
- "Every report number and tile was recounted from the raw files on ten states and matched."
- "The readings line copies the case file's texts byte for byte, and the page computes nothing."
- "The word 'finding' appears on no page."

**May not say:**
- "Ingest never stops on a session." (1a, 1b)
- "Each session ends in exactly one place." (1c)
- "Skipped sessions are in no count." (1c)
- "The store survives any interrupted write." (3)
- The limit sentences "no speech was recorded or transcribed" and "the calls are … simulated" for any batch with phone calls.
- "Tested with real customers."
- Any share as describing a real lender.

## Probes (all in `references/reviews/iter2/probes/`; each writes only under its state argument)

- `p3b_r3_kit.py`: shared helpers and the raw-file invariant check (imported only).
- `uv run python …/p3b_r3_ingest.py <state> [<copied real sessions>]`: claims 1, 3, 4, 5, 7, 8, 10, 11.
- `uv run python …/p3b_r3_chain.py <state>`: claim 6, including the CLI `run`.
- `uv run python …/p3b_r3_recount.py <state> [<state> …]`: claims 9 and 16 and the interval checks (read only).
- `uv run python …/p3b_r3_sampling.py <state>`: claim 13.
- `uv run python …/p3b_r3_readings.py <state>`: claim 15. It leaves a state and `expected_lines.json` for rendering.
- `uv run python …/p3b_r3_wording.py <state> [<state> …]`: claim 12. It runs the CLI on a copy, `<first>/../wording_cli`.
- `uv run python …/p3b_r3_pages.py <state> <page dumps dir>`: claims 15, 16 and 18 on rendered text. The dumps come from a review-only server on 8097/8098 plus a headless-Chrome text dump. I kept both scripts outside the repo as scratch tools, `verifier/review_server.py` and `verifier/dump_pages.mjs`.
- `.venv/bin/python …/p3b_r3_mutate.py <repo copy> <python>`: claim 14. It refuses to run on the working tree.
