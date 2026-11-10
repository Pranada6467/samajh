# P3b fix round 2: independent verification (round 4)

Saved by the P3b sub-orchestrator on 2026-11-10 from the verifier's final message, unchanged below the line. It checks the fixes for the five defects of round 3 (`verify-P3b-r3.md`), on the working tree at 993edf4 plus uncommitted edits. The `samajh/ops/book.py` change it mentions at 21:01 IST is the sub-orchestrator's README note ("The rendered pages"), text only. What was done about the defects it lists is in `references/pilots/P3b-fix2-report.md`.

---

P3b round 4: independent verification (my own inputs; I wrote none of the code)

- **Who:** independent verifier, Opus. I wrote none of the P3b code.
- **Time:** started 20:58 IST, finished 21:11 IST.
- **HEAD:** `993edf4` at start and end. The working tree has uncommitted edits.
- **`uv run pytest tests/ops -q`:** `278 passed` at start, `278 passed` at end.
- **What I touched:** no network, nothing on 8085/8086, no git writes, nothing under the repo's `.samajh/`. The only repo files I added are `references/reviews/iter2/probes/p3b_r4_*.py`. All state and the repo copy are under `/private/tmp/claude-501/-Users-masterpanda-projects-gnani-voice-ai-challenge/35526bbf-cd9b-4eb6-bdbc-144b68e7c617/scratchpad/verifier-r4/`.
- **A file changed under me:** another worker changed `samajh/ops/book.py` at 21:01 IST, during my run. The hostile-shape probe ran before that; every later probe ran on the new file. `samajh/ops/sessions.py` was last modified at 20:56, before I started.

**Verdict: sound with conditions.** All five defects from round 3 are fixed on new inputs:
- ingest no longer raises on hostile files;
- a changed session stays where it is and is never listed as skipped;
- the limits match the phone calls;
- the exact 5/4 boundary is decided correctly;
- a torn last line is set aside into `.torn`.

What remains:
- A brought-in session whose folder is deleted is listed nowhere, and the ingest note then miscounts.
- The phone-only limit sentence speaks of "the simulation".
- Skip reasons have no length limit.
- Two mutants survive `tests/ops`.

**Claims**

1. **Holds.** 61 hostile shapes, each alone in a fresh copy of a 90-loan batch (seed 60606), plus all of them in one run.
   - Ingest always returned. Every folder ended in exactly one list, and every skipped one had a reason in words.
   - A sound later session on another loan was linked every time.
   - `load_batch`, `build_report` and `attempt_log_view` worked every time, and a second ingest changed no store file.
   - Shapes covered: models as int, list or dict; started_at at 1999-12-31, 2000-01-01, 2100-12-31, 2100-12-31-14:00 (UTC 2101), naive, an int, "NaN", a +23:59 offset, nanoseconds; NaN, Infinity and -Infinity literals; a 400-digit int; nesting 5,000 and 100,000 deep; a 10 MB loan_id; duplicate keys; a BOM; empty and whitespace-only files; a JSON array or null; result as a string, `{}` or a list; odd turns, odd transcript, odd book block; a directory named case.json; chmod 000; a dangling symlink; a symlinked folder; a symlink to /etc/hosts; a folder name that is not a session id; session.json only; a session_id that differs from its folder.
   - Defects that are not crashes:
     - (a) A skip reason quotes the input whole. With `"loan_id": "L"*10_000_000` the reason is `loan 'LLLL…' is not on this batch's book`, and `ingest.json` grows to 10,000,212 bytes. The `[:300]` cap applies only to unexpected exceptions, not to `_Skip` reasons.
     - (b) `"result": {}` on a ready, completed case is skipped with "case file could not be read: loan_id: Field required". The field is the result's loan_id, not the top-level one.
   - My invalid-UTF-8 shape was a no-op in this probe; claim 2 covers it.

2. **Fails, in one input.** 23 single changes, 3 sequences and a CLI run, on a 70-loan batch (seed 31337).
   - What held: in 21 of the 23 single changes the session stayed in its place and was listed under `changed` with what differs, never under skipped. The store was unchanged apart from `ingest.json`, and the report moved only in `phone_sessions_changed`.
   - Changes tried: another analysis, another outcome, ready to failed, running, malformed, invalid UTF-8, chmod 000, case.json deleted, call_date shifted, book removed, another batch, another language, customer_audio, speaker_confirmed false, an outside call's outcome changed or its file deleted, an outside call given a book block, no_response becoming completed, an outside call becoming an attempt.
   - Sequences: change then change back leaves nothing in `changed`. Changing twice keeps it in `changed`. Failed → ready superseded to completed; → failed → ready with another model was kept and listed as changed, and the report did not move.
   - The CLI `ingest` and `report` agree with in-process.
   - **Failing input:** link session A (ready, completed), then `rm -rf sessions/<A>` and ingest again.
     - A stays as attempt 1 and is counted.
     - It is in none of linked, outside, skipped or changed.
     - The note says "The last ingest saw 6 phone session(s) and brought in every one (4 as attempts, 2 outside the sample)", while the store holds 5 phone attempts and 2 outside.
   - **Not listed as changed, by design:**
     - Readings added to a case file whose saved call has none (the documented legacy equivalence in `_same_call`).
     - A different `models` on a `failed` case: the attempt records no analysis.

3. **Holds, with one wording defect.** I built 6 batches: simulated only; simulated plus 5 phone attempts; only 1 outside call; only 6 phone attempts; 4 phone attempts after day 30; the same plus simulated.
   - I scanned every string of the report, batch, queue, attempt-log and case views.
   - No "synthetic and simulated", "Simulated batch" or unqualified "no speech" sentence appears next to a phone call. With no phone call, nothing mentions phone, Prisma or microphone. The stated counts of simulated, phone and outside calls, and of late calls, equal my raw recount. There is no "none by design".
   - **Defect:** with 0 simulated attempts (the outside-only, phone-only and late-phone batches), the limits still say "The share of calls flagged under each rule follows from the mix of customers the simulation assumes and, for phone calls, …".

4. **Holds.** 13 schedules on a hand-built book, with `fractions.Fraction` as the oracle.
   - Six were exactly 5/4 but are not exact in floats: 5/6 vs 2/3, 15/17 vs 12/17, 9/28 vs 9/35, 7/40 vs 7/50, 30/47 vs 24/47, 5/53 vs 4/53. All are narrow: intervals shown and "about the same chance".
   - Just above (154/123, 49/39, 93/74) is wide, with no interval anywhere in the report JSON.
   - Just below (56/45) is narrow.
   - Two three-draw schedules with exact 5/4 extremes are narrow.

5. **Holds.** All four logs (attempts, outside, dispositions, draws), 6 fragment kinds each: mid-key, a Hindi string cut inside a UTF-8 character, a bare `{`, whitespace only, a NUL, and a valid line without newline.
   - After each, a second and third fragment were glued on before the next append.
   - Reads worked before and after each append. No entry was lost or duplicated, the new entry was kept, the fragments went to `<log>.torn`, and the report built. A valid line without newline was kept as an entry.
   - Six processes appending 25 dispositions each, with a torn tail present: all exit codes 0, and 151 = 1 + 150 entries, no duplicates.
   - **A torn line in the middle (a different fault):** `store.attempts()` or `dispositions()` and `build_report` raise `ValidationError: 1 validation error for Attempt` (or `Disposition`). The store is unreadable until someone fixes the line by hand.

6. **Holds.**
   - **Strict booleans (8 inputs):**
     - `readings_agreed` "yes", 1, "true", 0, [true] or null each gave "two readings, not compared as amounts in the case file". true gave "same amount, read back"; false gave "differ, read back".
     - A reading's `ok` of "false", 1, "yes", null, {} or false hid the text; absent or true showed it.
   - **speaker_confirmed (10 loans):**
     - false on do_not_call, human_requested or call_back_later gave `request_unconfirmed`, and the loan was retried.
     - Three of them in a row hit the limit, and the 4th was skipped.
     - true or absent mapped as before.
     - completed with false was skipped as a contradiction.
   - The funnel exits equal my raw recount, `request_unconfirmed` has its own row (2), and do_not_call is 2, the confirmed and absent cases only.
   - Note: `written_requested` with speaker_confirmed false stays `written_requested`, which ends the chain; it is not in `UNCONFIRMED_REQUESTS`.
   - In the repo copy, adding `r4_fake` to `samajh.dialogue.machine.Outcome` made `test_every_dialogue_outcome_has_an_attempt_outcome` fail.

7. **Holds.** New book, seed 4242, 140 loans, 3 draws. Phone ingest, `run_draw` and more phone sessions interleaved: 104 attempts (34 phone), 46 skipped.
   - The raw-file invariants are clean: numbers 1..k, times rising, nothing after a chain-ending outcome, at most 3, on the call date in India time even for sessions started 18:00–23:59 UTC.
   - All 10 calls dated before the sale or the draw were refused with a reason.
   - 5 calls after day 30 were logged and not counted; the other late ones were refused by the chain rules, with reasons.
   - `p3b_r3_recount.py` gives 126 rows and 0 mismatches on each of 7 of my states. None is near the 1.25 edge, so its float line does not matter there.
   - "finding" appears 0 times in the view JSON, the store files, `web/review`, `data/loanbook/README.md` and the CLI report.

8. **15 mutations: 13 caught, 2 survived.**
   - Caught: torn line not set aside; ratio compared in floats; only ValueError/KeyError/TypeError caught; a changed session listed as skipped; the started_at text check dropped; request_unconfirmed mapped to do_not_call; a reading's text shown when ok is false; lax `ok`; lax `readings_agreed`; the year check dropped; request_unconfirmed not retryable; an outside-only batch given the simulated limits; a changed analysed call not noticed.
   - **Survived:**
     - `at <= last.at` changed to `<`. With it, two sessions on one loan with the same call date and India time are both linked with equal times: `[(1,'2027-04-03T11:00:00+05:30','no_answer'), (2,'2027-04-03T11:00:00+05:30','completed')]`. The unmutated code refuses the second with a reason, as it should.
     - The "sold" tile showing the eligible count.

**Not checked:** rendered pages in a browser (I read view JSON only); `run --analysis llm`; ingest during a live call; the CLI `run`; the committed `p3b-artifacts`.

**Wording**

May say:
- "Ingest returned on 61 hostile case-file shapes, alone and together; each session folder ended in exactly one list, with a reason when skipped."
- "A session already brought in stays where it is and is counted when its case file later changes, becomes unreadable or loses case.json; it is listed as changed, never as skipped."
- "With phone calls in a batch, the limits say how many calls were simulated and how many were phone sessions, matching a recount from the raw files."
- "Inclusion chances are compared as exact fractions; exactly 1.25 counts as narrow."
- "A torn last line in any log is set aside into `<log>.torn`, and no entry is lost, including with appends from several processes."
- "A request from a speaker not confirmed as the borrower is retried, counts towards the three-attempt limit, and is never counted as do-not-call."

May not say:
- "Every session brought in is listed when its case file changes." A deleted session folder is listed nowhere, and the note then miscounts.
- "The store survives any damaged line." A bad line in the middle makes it unreadable.
- "The phone-only limits are exact." They mention "the simulation" when no attempt was simulated.
- "Skip reasons are short." One can be 10 MB.
- "Tested with real customers", or any share as describing a real lender.

**Probes** (in `references/reviews/iter2/probes/`; each writes only under the path it is given; `S=…/scratchpad/verifier-r4`)
- `uv run python …/p3b_r4_hostile.py $S/hostile`: claim 1
- `uv run python …/p3b_r4_changes.py $S/changes`: claim 2, including the CLI
- `uv run python …/p3b_r4_limits.py $S/limits`: claim 3
- `uv run python …/p3b_r4_ratio.py $S/ratio`: claim 4
- `uv run python …/p3b_r4_torn.py $S/torn`: claim 5
- `uv run python …/p3b_r4_speaker.py $S/speaker`: claim 6
- `uv run python …/p3b_r4_sweep.py $S/sweep`, then `p3b_r3_recount.py $S/sweep/w`: claim 7
- `uv run python …/p3b_r4_equal_time.py $S/equal`: the equal-time edge behind the surviving M7. It imports the working tree through `p3b_r3_kit`; to test a mutated copy, run the copy's own probe files.
- `.venv/bin/python …/p3b_r4_mutate.py $S/repo .venv/bin/python`: claim 8. It refuses to run on the working tree.
