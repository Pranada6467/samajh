# P3b fix round 2: independent verification (round 5, a short re-check)

Saved by the P3b sub-orchestrator on 2026-11-10 from the verifier's final message, unchanged below the line. It checks only the fixes made after round 4 (`verify-P3b-r4.md`), on the working tree at 993edf4 plus uncommitted edits. Nothing was changed in `samajh/ops` after it: the cases it lists as failing are open.

---

P3b round 5 re-check (independent verifier; I wrote none of this code). Start 21:15 IST, end 21:19 IST, 2026-11-10. HEAD 993edf4. The working tree has uncommitted edits from other workers.

**Verdict:** sound with conditions. All five fixes held on my own inputs except two narrow cases: when the sessions directory itself is missing, the attempt-log note gives counts that disagree with the store; and with 0 simulated attempts, two fixed sentences still say "Simulated" / "simulated book". Separately, a list or string `result` is skipped with the prefix "result:" rather than "result.", because there is no field inside it to name.

**Claims**
1. Folder gone: holds on 8 states, fails on 1 (the missing directory).
   - What held:
     - 4 folders deleted in one run (2 attempts, 2 outside calls, one of them the superseded attempt) while 2 new sessions arrived. All stayed linked or outside, were listed under changed with the words "the session folder is no longer in the sessions directory; the version brought in first is kept", and none was skipped.
     - Note counts (5 attempts, 3 outside) matched my raw recount of attempts.jsonl and outside.jsonl.
     - A second ingest changed no store file.
     - A FILE put in place of a deleted folder was listed as changed.
     - Folders that came back unchanged: changed list empty.
     - A folder that came back with a different language: changed "(language)".
     - All folders deleted: 8 changed, store unchanged, and the CLI `ingest` and `report` both exit 0.
     - In every state where I checked it, every folder plus every stored session was in exactly one of linked, outside or skipped. `attempt_log_view`, `build_report` and the case views did not raise.
   - Failing input: delete the sessions directory itself after the store holds 5 attempts and 3 outside calls, then call `ingest` (or run the CLI `ingest --state`).
     - Nothing raises and no store file changes.
     - But ingest.json is overwritten with empty lists, so `attempt_log_view(...).ingest_note` says "The last ingest saw 0 phone session(s) and brought in every one (0 as attempts, 0 outside the sample)." `log.changed` is `()` and the report's `phone_sessions_changed` is 0.
     - The same report's limits and the batch `phone_note` both say "8 phone session(s)", so the note and the store disagree.
2. Limits wording: holds in part, on 4 batches (phone attempts only, one outside call only, late phone attempts only, phone plus simulated). No string speaks of "the simulation" or claims the batch is text-only. With 36 simulated attempts the simulation sentence is present and its count matches my recount (36). No banned word (finding, refund, proven, verdict, violat, breach, fraud, mis-sell or mis-sold, guilty, non-compliant) appeared in the report, batch, queue, attempt-log or case views (transcripts excluded). Two sentences remain with 0 simulated attempts, in the batch view and the report:
   - "Synthetic batch: the loan book and the customers are synthetic. Calls marked Simulated were scripted; calls marked Phone call were made on the browser phone with synthetic records."
   - "Synthetic date: the report is dated by the simulated book's clock, the day of the last call attempt."
   Neither says a call was simulated, but both name simulation when nothing was simulated.
3. Reason cap: holds on 11 long values. I fed 900-character values into loan_id, record_id, call_outcome, batch_id and draw_id: each reason was exactly 300 characters, ending in "…". A long language or status gives a short pydantic reason (82–83 characters). A long session_id gives "case file names another session". The changed reason with 400-character model keys and a 2,000-character turn was 72 characters. The longest reason I saw was 300, under `Ingested.skipped`. I checked `Ingested`, `ingest.json`, the attempt log and the CLI lines: none exceeded 300. A short reason was unchanged ("the case file names batch 'B-x', not this batch (B-2027H1-72b4433b)"). One input not run: the long (236-character) folder name was created but not traced in the output. A long exception message was not tried.
4. Bad result shapes: holds on 6 inputs, with the wording caveat above.
   - `{}` gives "case file could not be read: result.loan_id: Field required"; `{"loan_id":5}` gives "result.loan_id: Input should be a valid string"; a wrong product gives "result.products.0.product_id: Field required".
   - `[1,2]` and `"x"` give "case file could not be read: result: Input should be a valid dictionary or instance of CaseResult". The prefix is "result:", not "result.".
   - Ingest did not stop, and the sound session that came after them was linked.
   - When a linked session's result later became `{}`, it stayed linked and was listed as changed. `load_batch`, `build_report`, `attempt_log_view` and the case views did not raise.
5. Same call date and India time: holds on 6 inputs. I tried both folder orders, either outcome first, and once with identical `started_at`. Each time the loan had exactly 1 attempt and the second session was skipped with a reason ("not after the loan's last logged attempt" or "the loan's attempts had already ended").

Regression: `uv run pytest tests/ops -q` gives "288 passed in 6.77s". `p3b_r4_hostile.py` and `p3b_r4_torn.py` both give FAILURES: 0.

**Not checked:** a long exception message as a reason; the long folder name's reason; the folder-gone case with a superseded session that later comes back different; a byte-for-byte comparison of CLI `report` against the in-process report (I checked only exit codes).

**Wording** (from what I ran only)
- May say: "A session already brought in stays counted, and is listed as changed, when its folder is deleted or replaced by a file (8 states; raw-store recount)."
- May say: "Every skip or change reason was at most 300 characters on the inputs tried, with cut reasons ending in …"
- May say: "A malformed `result` is skipped with the field named, and ingest goes on."
- May not say: "The attempt-log note always agrees with the store." It reads 0 and 0 when the sessions directory is missing.
- May not say: "No page mentions simulation when nothing was simulated."

**Probes**
- `/Users/masterpanda/projects/gnani-voice-ai-challenge/references/reviews/iter2/probes/p3b_r5_all.py`: run `uv run python references/reviews/iter2/probes/p3b_r5_all.py <scratchpad>/verifier-r5/all`. It reported 11 failures: 2 for the claim 4 prefix and 9 for the claim 2 sentences.
- `/Users/masterpanda/projects/gnani-voice-ai-challenge/references/reviews/iter2/probes/p3b_r5_extra.py`: run `uv run python references/reviews/iter2/probes/p3b_r5_extra.py <scratchpad>/verifier-r5/all <scratchpad>/verifier-r5/extra`. It covers the missing directory, the folder-gone wording and identical `started_at`.
- All state is under `/private/tmp/claude-501/-Users-masterpanda-projects-gnani-voice-ai-challenge/35526bbf-cd9b-4eb6-bdbc-144b68e7c617/scratchpad/verifier-r5/`.
