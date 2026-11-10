# P3b fix round: re-verification (round 2)

Saved by the coordinator on 2026-11-10 from the verifier's final message, unchanged.

Verifier: independent, Opus high. I wrote none of the code. No Gnani or OpenRouter calls, nothing sent to port 8085, no edits outside `references/reviews/iter2/probes/p3b_r2_*.py`, no git writes. All state was written under the scratchpad. I copied today's 41 real session folders without audio and never touched the originals.

## Verdict: sound with conditions

Three of the five fixes hold on fresh inputs: neutral labels, no overlap, the 30-day edge for simulated calls. The features-and-risks grouping holds too. Every report number I recounted matches. Ingesting phone sessions is the weak part: it works for the cases it was tested on, and fails on four inputs the builder did not try. One more condition: the committed P3b pages are stale.

## Each fix

1. **Decision labels are neutral and carry no intervals: holds.**
   - All four labels ("Concern supported by the file (reviewer's view)", "Concern not supported…", "Call the customer", "Needs more information") are stored as plain counts with no interval in every report I built. The page says "no interval is given".
   - The project's banned-word list found 0 hits across every view (batch, queue, all case pages, attempt log, report) and the text in `web/review/*.js` and `*.html`.
   - Mutations M8 to M10 (label set to "Established" or "Mis-selling found", intervals put back on decisions) were all caught by the tests.
   - **Condition (wording):** the report still uses "finding(s)" for flag counts: 12 distinct view strings, plus the page headings "Findings: features and risks", "Each finding is listed most serious first", "No finding was counted in this batch" and "Findings by loan kind, branch and channel". This goes against the project rule that a flag is never a finding, and "finding" is not on the banned list.

2. **Draws never overlap: holds.**
   - I ran 420 cases: seeds 1, 7, 2027 and 31337; book sizes 1, 5, 37, 200 and 600; 7 schedules (daily, weekly, every 30, 31 and 45 days, irregular, first draw late); rates 0.05, 0.4 and 1.0. That is 8,493 draws.
   - Results: 0 loans eligible twice, 0 drawn twice, 0 completeness errors. Every draw recomputed to match. At rate 1.0 every loan was drawn exactly once. Reordered or unchained draws failed verification.
   - The store refuses an overlapping draw. A forged draw with a correct link to the previous one is accepted when written, but flagged by `verify`.
   - **Condition:** the sampling statement always claims equal chances. With rates 1.0, 0.05 and 0.4 in one batch it prints "every eligible sale had about the same chance … (between 4.4% and 100.0%)" and "Shares are unweighted because the chances are equal up to rounding". With daily draws at 0.4 the range is 33.3% to 100%. In those cases the unweighted Wilson shares are wrong. The demo is fine (37.5% to 41.7%).
   - Mutation M6 survived: no test covers the store's own check that a draw starts where the last one ended. `verify` still catches the gap.

3. **No attempt after day 30: holds for simulated calls.**
   - 72 batches (3 seeds, 2 sizes, draw gaps of 1, 7, 29, 30, 31 and 33 days, 2 rates), 12,565 attempts, 0 after day 30.
   - All 87 loans whose retries the window cut ended as `not_reached_in_time`. The logged day equals the India-time date of the attempt, which here is also the UTC date.
   - Phone calls are not bound by the rule, by nature. A phone attempt on day 31 is logged and shown honestly (`attempts_after_window` 2 of 92), but `report.timing` still says "none by design".
   - A call at 20:00 UTC on day 30 counts as day 31, by India time. That is consistent, but no test covers it: mutation M12 (UTC instead of India time) survived.

4. **Phone sessions enter the queue and the report: partly holds.**
   - **What works:**
     - The 7 real case files (copied) all became calls outside the sample and were never counted. A second ingest changed nothing (checked in-process and through the CLI).
     - `running` is skipped with a reason. A failed case file becomes `completed_not_analysed`, with no finding.
     - A call completed on day 31 becomes `completed_late`: queued, not counted.
     - A record on neither book is skipped. A decision on a non-referral returns 404; a bad decision returns 422.
   - **What fails:**
     - (a) **A failed case file that is rebuilt.** The server re-runs a failed case on POST, so this path is real. The next ingest raises `ValueError: attempts.jsonl already holds a different entry for D-2027-02-22/SYN-GL-270216-0154/20270221T053000-000000000002` and stops the whole run. It has already saved the call file, which is left with no attempt pointing to it.
     - (b) **The new P2 outcomes `do_not_call` and `written_requested` (uncommitted).** Ingest raises `no attempt outcome for the dialogue outcome 'do_not_call'` and stops.
     - (c) **A loan on the book that was never drawn** is skipped with the wrong reason ("record 'SYN-PL-270104-0002' is neither on the book nor a phone record") instead of being listed as outside the sample, as `data/loanbook/README.md` says it should be.
     - (d) **Sessions with no case file are silently ignored.** 34 of the 41 real session folders have no `case.json` (e.g. `20261110T103734-261d0a69f2ed`, hung up at the go-ahead question). They are not even listed as skipped, so the funnel does not see them as attempts. Some are probably headless replays (inferred).
     - (e) **A phone call after a simulated completion drops the completed call.** `SYN-PL-270106-0005` was completed on day 5; a phone no-answer on day 7 turned it into "Not reached", and its completed call left the counts. In the other order (phone call first, then the simulation), 6 loans got duplicate attempt numbers, and status follows file order, not time.
     - (f) **A call 3 days before the sale is accepted.** It is labelled "Completed after day 30 from the sale" and the first-attempt minimum shows −3. Calls made before the loan's draw date are also accepted silently.
     - (g) **The phone-call note may be false (inferred).** The note says phone calls used "recorded synthetic voices", but session `20261110T112446-f7770ec63c07` has customer audio from the microphone. Ingest never reads where the audio came from.

5. **Features-and-risks grouping: holds.** Rows are sorted by group, then seriousness, then share in 3 reports. The risks group has one rule (`belief_mismatch`), and the risk note says coverage is thin. Mutation M15 was caught.

**Stale artifacts (condition):** `references/pilots/p3b-artifacts/report.json` shows refer 11 of 64 and understanding_gap 29 of 64. Today's code on the same seed gives 7 of 64 and 33 of 64; the change is `recall` referred, 4 then and 0 now. The funnel is identical (80 sampled, 113 attempts). Inferred cause: the P3a commits ff960f7 and b42e023 landed after 4180556. The pages and PDF need re-rendering before they are used as evidence.

## Recount (`p3b_r2_recount.py`; samajh used only for the per-rule `referred` column)

| State | Report rows checked | Mismatches |
|---|---|---|
| demo, seed 85 | 169 | 0 |
| ingested sessions, decisions, outside, late calls | 165 | 0 |
| CLI ingest of the real copies | 169 | 0 |
| edge batches (85/300/gap 31; 4242/60/gap 7) | 163, 167 | 0 |
| mixed rates; daily draws | 141, 208 | 0 |

The rows cover funnel stages and exits, tiers, every rule (flagged, undecided, referred), decisions, open and supported counts, other referrals, timing, sampling (sales in the period, eligible, never-eligible reasons, inclusion range), draws, breakdowns including the "all other rows" comparison, and the policy sentences with their "highest" place.

**The previous verifier's probes:**
- `p3b_recount` matched all 34 funnel, tier and rule rows. It stops at the decision rows because it expects intervals, which the fix removed.
- `p3b_sampler` no longer runs: the API changed from `size` to `rate`.
- `p3b_truth`: 7 referred, all problem customers; 0 others referred; 1 problem customer (wrong cancellation window) came out `understanding_gap`, as P3a designs.

## Tests

- `uv run pytest tests/ops -q`: **72 passed, 1 failed** (73 collected). The failure is `test_every_dialogue_outcome_has_an_attempt_outcome`: the P2 fix round's uncommitted `do_not_call` and `written_requested` have no attempt outcome. It is the same gap as 4(b).
- Mutations in a copy of the repo: 13 of 15 caught; M6 and M12 survived.

## Not checked

The pages in a browser (I read the JS strings, took no screenshots); `run --analysis llm`; a live server (I ran the review router in-process only); ingest running at the same time as a live call; what is in the 34 sessions without a case file beyond one of them.

## Wording

**May say:** "Draws never overlap and no simulated call attempt falls after day 30 from the sale. Checked on 8,493 draws and 12,565 attempts over seeds and schedules the builders did not use." "Reviewer decisions are counted, with no interval, under neutral labels." "Every report number was recounted from the raw files and matched." "Phone calls on records outside the sample are listed and never counted."

**May not say:** "equal chance of selection" without the inclusion range; "phone sessions are fully ingested" (see 4a to 4g); "the phone is joined to the loan book"; "findings" for flag counts; "tested with real customers"; any share or rate as saying something about a real lender; the 11-referral numbers in the committed artifacts as current.

The rule "counts per 100 by kind of customer, never one pooled rate" is written for evaluation. The report has no customer kinds and shows pooled tier shares broken down by loan type, branch and channel. Whether that is enough is a call for the coordinator (inferred).

Probes, all rerunnable, in `references/reviews/iter2/probes/`: `p3b_r2_sampler.py`, `p3b_r2_ingest.py`, `p3b_r2_recount.py`, `p3b_r2_wording.py`, `p3b_r2_mutate.py`, `p3b_r2_mixed_order.py`.
