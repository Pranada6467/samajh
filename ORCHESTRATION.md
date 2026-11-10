# Samajh build — orchestration rules and iteration log

Every worker reads this file, `CLAUDE.md` and `DESIGN.md` before starting. `DESIGN.md` is the product spec; this file is how we build it.

## Roles and models (set by the user)

| Work | Model | Effort |
|---|---|---|
| Orchestrating: planning, writing instructions for subagents, deciding | Fable (`claude-fable-5-2`) | high |
| Building: writing code, tests, data | Opus (`model: "opus"`) | medium |
| Verifying: independent review, attacks, reproduction | Opus (`model: "opus"`) | high |
| Fact and claims research, documentation updates | Sonnet | default |

Set by the user on 2026-11-10 (iteration 2): Fable only orchestrates; Opus medium builds; a separate Opus high verifies; Sonnet researches and documents. The coordinator and each execution manager (an Orca worker) run on Fable and do not write the product code or run the review themselves. An execution manager owns one work package, splits it into small tasks, and hands each to a subagent with `model` and `effort` set on the `Agent` call as in the table: Opus medium to build, a separate Opus high subagent that wrote none of the code to verify. This replaces any older line in a task spec that says to do the work yourself or names Fable for building or reviewing.

In the iteration 2 build wave the coordinator ran Opus builders and verifiers directly as its own subagents, because Orca workers kept stopping on the usage limit. From iteration 3 it again uses Orca workers as Fable sub-orchestrators, one per package.

## The loop, per work package

1. **Plan.** Load `pstack-architect`. Sketch types, signatures and module layout before code. Write the plan into your final report, not into a new file.
2. **Verify claims.** Every external fact the plan relies on (an API parameter, a regulation paragraph, a library behaviour) is checked against a primary source or a live call before code depends on it. Unverified facts are marked `[unverified]` in code comments and in your report.
3. **Build.** Spawn builder subagents (Opus, medium). Small verifiable units, tests alongside.
4. **Review.** Spawn an independent verifier subagent (Opus, high) that did not write the code and is given fresh inputs, not the builder's own probe sets. It runs the tests, tries to break the change, and reports. Fix what it proves. Then report.

## Standards (pstack)

Load `pstack-poteto-mode` at the start. These principles are binding:
- `prove-it-works`: run the real thing before you say done. "Tests pass" must include the command and its output.
- `boundary-discipline` and `type-system-discipline`: parse external data at the edge (API responses, LLM output, env), trust typed values inside. Illegal states unrepresentable.
- `laziness-protocol` and `subtract-before-you-add`: the smallest code that meets the spec. No speculative abstraction.
- `test-behavior-not-implementation`.
- `explain-the-number`: every metric has n, the gold standard, the audio source, and what limits it.
- `make-operations-idempotent`: every script can be rerun after a crash; cached calls are never repeated.

## Hard rules

- **Stay in your lane.** Edit only the paths your spec lists. Need a change elsewhere? Ask the coordinator (`orca orchestration ask`), do not edit.
- **Do not `git commit`, `git add` or `git stash`.** Several workers share this checkout. The coordinator handles git.
- **Secrets.** Keys live in `.env` (gitignored). Read them from the environment. Never print, log, cache or write a key anywhere, including test fixtures and reports.
- **Gnani concurrency is 1 for the whole account** (not per key: a second key from the same account got the same 429, 6 of 6 trials). Only a worker whose spec says "live Gnani access: yes" may call `api.vachana.ai`. Everyone else works offline. All calls go through the shared client once it exists (cross-process lock, cache, ledger).
- **Credits.** Total cap 1,000 across the project. Your spec gives your budget. Stop and ask before exceeding it.
- **OpenRouter.** Cheap models by default. Use an expensive model only when a measured result shows the cheap one fails, and say so in your report.
- **Synthetic data only.** No real phone numbers, account numbers, Aadhaar, PAN or names of real people. Generated IDs obey formats but are obviously fake. Ombudsman cases are templates with invented parties.
- **Honesty.** Report failures and skipped steps plainly. No accuracy claim without a metric and a gold standard. Tamil and Kannada content has no fluent human reviewer yet: label it `not human-reviewed`.
- **Agent Builder is out of scope.** Speech APIs only.
- **Documentation.** When your work makes a document stale, say so in your report with the exact lines; the coordinator has a Sonnet agent update it at once.

## Stack

Python 3.11, `uv` for the environment, `pydantic` v2 for types, `pytest`, `ruff`, `httpx`. FastAPI for the backend (iteration 2). Package name `samajh`. Runtime state (cache, ledger, locks) under `.samajh/` (gitignored). `ffmpeg` is installed. The coordinator owns `pyproject.toml` and `uv.lock`: the environment already has pydantic, httpx, filelock, python-dotenv, fastapi, uvicorn, pytest, ruff and respx. Run things with `uv run`. Need another dependency? Ask the coordinator.

## Final report format (your `worker_done` message)

1. What you built (paths).
2. Evidence: exact commands run and their real output (test counts, metrics with n).
3. Claims verified, with source; claims still unverified.
4. Failures, known gaps, and anything you changed from the spec and why.
5. Credits and OpenRouter spend, if any.
6. What the next iteration should do in your area.

## Verified facts that override older documents

- Gnani API: the "Gnani API facts" section of `CLAUDE.md` now matches `references/pilots/api-probe-iter1.md`, which stays the evidence (measured live) and wins if the two ever differ. In short: `codemix` is a `format` value on v3.0; v2.5 `format=transcribe` gives digits beyond Hindi and English; a second simultaneous REST request gets an instant 429, even on a second key of the same account; a WebSocket streaming session does not occupy the one active-request slot; no API surface reports credit cost.
- Regulation and cases: `references/claims/claims-ledger.md` and `references/claims/design-corrections.md`. `DESIGN.md` is v3 and applies them.
- Extraction LLM: `openai/gpt-6-luna`, not the W2 default (`mistralai/mistral-small-3.2-24b-instruct`); the reasons and numbers are in `references/pilots/W5-extractor-report.md` §2.4 and `DESIGN.md` §7. It rejects the `temperature` parameter (OpenRouter answers 404), so call it through `samajh.pipeline.default_llm()`.
- Client signatures and caveats: `references/pilots/W2-clients-report.md`. Never run `tests/clients/probes/gnani_probe.py` (it bypasses the lock).
- Workers hit account usage limits. Keep subagent use lean: one planner pass, builders, one verifier pass.
- Subagents cannot write new report files with the Write tool (the harness answers "Subagents should return findings as text, not write report files"). A builder returns its report in its final message, or edits a report file that already exists; the coordinator saves the text. Say this in every brief.

---

## Iteration log

### Iteration 1 — text path and clients (2026-11-10)

Goal: everything that needs no audio loop. At the end, a transcript goes in and a flagged case with evidence comes out, the gold set is frozen, and the Gnani and LLM clients are proven live. All eight packages are done and were reviewed by two independent verifiers and a judge (`references/reviews/iter1/`).

| WP | Scope | Owns | Status |
|---|---|---|---|
| W1 core | types, amount normaliser, rule engine | `samajh/types.py`, `samajh/amounts/`, `samajh/rules/`, `tests/core/` | Done (W1, then W1b after a usage-limit stall). Extended by P3a in iteration 2 (1,708 tests collected in `tests/core` on 2026-11-10; 1,223 at the end of iteration 1). Report: `references/pilots/W1-core-report.md` |
| W2 clients | Gnani client (STT/TTS, lock, backoff, cache, ledger, cap) and OpenRouter client | `samajh/clients/`, `tests/clients/` | Done. Report: `references/pilots/W2-clients-report.md` |
| W3 claims | Verify regulatory and Gnani-API claims against primary sources | `references/claims/` | Done. `check_quotes.py` reports 3 spans not found (all under D5.10, quotes of pilot lines that `DESIGN.md` v2 rewrote): stale against the design, no claim fails |
| W4 scenarios | 144 scenarios (36 base cases x 4 languages), gold verdicts, hash freeze | `samajh/scenarios/`, `data/scenarios/`, `tests/scenarios/` | Done. Frozen at version 3 (`gold.jsonl` sha256 beginning `14e49b58`), 50 tests. Gold agrees with the rule engine on 144 of 144, reached partly by a coordinator decision on 8 scenarios (premium "I don't know"), made before any audio or LLM extraction. One independent review (of version 1); none of versions 2 and 3. Report: `data/scenarios/W4-report.md` |
| W5 extractor | LLM extraction to strict schema with quoted spans, text-path eval | `samajh/extract/`, `tests/extract/`, `eval/text_path/` | Done (W5, finished by W5b after a usage-limit stall). Extended by P3a (251 tests collected on 2026-11-10). Extraction model `openai/gpt-6-luna`. Text only, scripted customers. Report: `references/pilots/W5-extractor-report.md` |
| W7 voice transport | FastAPI proxy, browser phone, turn-taking measured REST vs streaming | `samajh/server/`, `web/`, `tests/server/` | Done. REST per turn is the shipped path; streaming was measured and not built (TTS clips only). Extended by P1. Report: `references/pilots/voice-loop-iter1.md` |
| W8 audio eval harness | phone-line transforms, resumable voicing/STT runner, amounts test set at scale | `samajh/audio/`, `samajh/evalkit/`, `tests/audio/`, `tests/evalkit/`, `eval/amounts/`, `data/amounts/` | Done. 2,640 transcriptions, 93.74 estimated credits, TTS audio only. Report: `eval/amounts/REPORT.md` |
| W9 dialogue | call state machine and prompt scripts in four languages | `samajh/dialogue/`, `tests/dialogue/`, `data/prompts/` | Done (W9, finished by W9b). Its behaviour is superseded by P2 (below); `references/pilots/W9-dialogue-report.md` is history |

Review of iteration 1 (2026-11-10): the judge's verdict is continue with changes, 69 of 100 today (the idea scored 84), about 79 after iteration 2 without human recordings and 82 with 20 human calls. Its ranked plan is the iteration 2 plan.

W7 and W8 had live Gnani access, through the shared client lock (`samajh/clients/gnani`); in iteration 2 so did P1 and P6.

Estimated Gnani credits used: about 295 of the 1,000 project cap (5,000 on the account), by the coordinator's estimate on 2026-11-10 after iteration 2's build wave. The ledger file (`uv run python -m samajh.clients.gnani ledger`, a local read) showed 275.79 when it was read for this update, so the two figures differ by about 20 and the gap is not explained. Both are client estimates at 0.010 credits per STT audio second and 0.002 per TTS character, not dashboard readings; no dashboard reading has been taken.

---

## Coordinator handoff (rewritten 2026-11-10, end of iteration 2's build wave; update whenever state changes)

A new coordinator session starts here.

### Start here (eight steps)
1. **Read:** this section; `references/reviews/iter1/judge.md` (verdict, ranked plan); `references/reviews/iter2/verify-P6.md` (what a good verification looks like); `references/pilots/` `P3a-report.md` + `P3a-contract.md`, `P2-report.md` + `P2-contract.md` (its section 5 is as built and wins), `P1-report.md`; the rendered P3b pages in `p3b-artifacts/` and `data/loanbook/README.md` (there is no P3b report file); `eval/amounts_v2/`; `git log --oneline -30`.
2. **Check what is running:** `git status --short` (a builder is editing `samajh/dialogue`, `data/prompts` and `tests/dialogue` for the P2 fix round: leave them alone until it reports); `lsof -i :8085` (a phone server); `uv run python -m samajh.clients.gnani ledger` (credits, a local read); Orca workers via `orca skills get orchestration`.
3. **Land the P2 fix round:** `uv run pytest tests/dialogue -q`, then a separate Opus-high verifier on inputs the builder never saw (the probes in `references/reviews/iter2/probes/p2_*.py` are the last verifier's; extend them). Do not accept builder-run counts.
4. **Re-voice P1, then verify it:** `uv run python -m samajh.server.prompts build --lang hi --lang hi-en`; `uv run python -m samajh.server.prepare <persona> tests/fixtures/server/calls/<persona>` for `hero`, `informed`, `third-party`; rerun the replays (`P1-report.md` section 4); Opus-high verifier.
5. **Re-verify the P3a and P3b fix rounds** (Opus high, fresh inputs, `references/reviews/iter2/probes/`).
6. **Join the phone to the loan book:** the phone has three packaged records (`samajh/server/records/`); a loan drawn by `samajh.ops` must be callable and its case must enter the queue (`uv run python -m samajh.ops ingest`).
7. **Close iteration 2:** `uv run pytest` (whole tree), sync the documents, checkpoint commit (check the staged diff for the two keys), then the iteration-2 verifier and judge.
8. **Launch iteration 3 with Orca workers, one per package (P5, P4 preparation, P7):** write the spec with a quoted heredoc (`<<'EOF'`), run `orca orchestration worker-start --spec-file <spec> --task-title "<title>" --worktree current --agent claude --model claude-fable-5-2 --effort high`, end the turn (Orca wakes you; never poll). The worker briefs Opus-medium builders and a separate Opus-high verifier through `Agent` with `model` and `effort` set, and tells every subagent to return its report as text. P4 starts only on the user's go signal (`USER-GUIDE.md`).

### How the user wants the work run
Fable (the coordinator and each Orca worker) only orchestrates; Opus medium builds; a separate Opus high that wrote none of the code verifies on fresh inputs; Sonnet researches and documents. After each iteration an independent verifier and a judge review work and direction. Parallelise where owned paths do not overlap; one request at a time can use the Gnani account. The coordinator commits (workers never run state-changing git). Reports are at most two pages. Documentation is updated as soon as a result makes it stale. In the iteration 2 wave the coordinator ran Opus builders and verifiers as its own subagents, because Orca workers kept stopping on a usage limit.

### Lessons so far
- **Usage limits:** a worker stops without warning at the account's 5-hour limit and does not wake on `send`. `worker-stop`, `worker-release`, commit a WIP checkpoint, start a fresh worker with a "resume from what is on disk" spec. Fewer workers at once last longer.
- **Report files:** subagents cannot write new report files (the harness answers "Subagents should return findings as text, not write report files"). Builders return the report as text or edit an existing file; the coordinator saves it. Two P6 reports wait in the coordinator's scratchpad for that reason.
- **Two keys add no capacity:** Gnani's limit is per account. With two keys from one account, one request on each at the same moment, exactly one succeeded and the other got 429 "Only 1 active request is allowed at a time", in 6 of 6 trials with the order shuffled (2026-11-10). `GNANI_API_KEY_LIVE` in `.env` is a spare only.
- **Quoting:** spec files use a quoted heredoc (unquoted backticks get executed by the shell). A document that quotes a verifier or a report copies its allowed wording and does not paraphrase a number.
- **Builder counts are not evidence:** P2's own probe sets read 0 where a verifier's fresh inputs found 16 of 64 and 25 of 45 (table below).

### Decisions in force (details: `DESIGN.md` section 15)
- Hindi and Hinglish are the product languages; Tamil and Kannada are experimental (appendix only, no new effort). One product family.
- Outcome is a four-tier triage (`refer`, `incomplete`, `understanding_gap`, `clear`). A flag is evidence for review, never a finding. A confidently stated wrong cover figure is `refer` only after a confirmed read-back of that figure, `incomplete` if unconfirmed, `understanding_gap` if hedged or unknown; term and cancellation window stay `understanding_gap`. A "took nothing" denial is `refer` only if it stands (if the customer later names a product matching the record it becomes `recall_not_named`). A retraction in a later clause never yields a stated value.
- Each amount turn gets two Prisma readings (v3.0 and v2.5); a disagreement leads to a re-ask and every amount is read back. The lead Gnani finding is v3.0's number formatting of skipped-group amounts and two-model agreement as a confidence signal, in the wording of `verify-P6.md` (also in `CLAUDE.md`).
- Extraction model `openai/gpt-6-luna`, after the call; the dialogue's live classifier uses `mistralai/mistral-small-3.2-24b-instruct`.
- E1 (scripted teach-back against yes/no) is not a headline: it is true by construction. P5 replaces it.
- Loan book: draws do not overlap; no call attempt after day 30; reviewer decision labels are neutral and carry no intervals. Human-call material lives in `.samajh-human/` (gitignored).

### Iteration 2 state
Plan: `references/reviews/iter1/judge.md`, "Iteration 2 plan, ranked". "Independently verified" means an Opus-high subagent that wrote none of the code (2026-11-10); its results reached the coordinator as messages, except P6's (a file).

| Package | Scope (lane) | State |
|---|---|---|
| P3a | Decision chain v2: tiers, case summary, hedged and approximate answers, conflicts, retractions (`samajh/types.py`, `rules`, `amounts`, `extract`, `pipeline.py`, `eval/text_path`) | Built; verified, sound with conditions; the conditions are fixed in two fix rounds; **the fixes are not re-verified** |
| P3b | Loan-book sampler, reach funnel, reviewer queue, half-yearly 85Y report (`samajh/ops`, `web/review`, `server/review_routes.py`, `data/loanbook`) | Built; verified, sound with conditions (every report number recounted and matched); the conditions are fixed; **the fixes are not re-verified**. Real phone sessions enter the queue and report; **the phone cannot yet call a loan from the book** |
| P6 | Gnani amounts finding: held-out TTS set, public real voices (local only), bug report (`eval/amounts_v2`, `data/amounts_v2`, `samajh/evalkit`) | Built; verified (`verify-P6.md`): every number reproduced, freeze order confirmed; the reports follow the verifier's wording; 136.5 estimated credits. Two reports are not yet in the repo |
| P1 | One Hindi/Hinglish call on the browser phone to a case file (`samajh/server`, `web/`) | Built: a whole Samajh call reaches a case file through the real HTTP API and in headless Chrome (Timbre customer voices; no person has spoken to the phone). **Not verified**; prepared calls must be re-voiced when P2's lines are final |
| P2 | Call v2: third parties learn nothing, refusals, short opening, "took nothing" branch, payment frequency, cover read-back (`samajh/dialogue`, `data/prompts`) | Built; verification said **not ready for a live line**: on the verifier's fresh inputs the loan was named to 16 of 64 third parties and 25 of 45 refusals got the next question with rules alone (16 of 45 with the LLM fallback). **A structural fix round is in progress** (the classifier becomes the primary judge at the opening, safe defaults, new outcomes) |
| P4 | 20 improvised human calls from brief cards | Not started; needs P1 and P2 verified and the user |
| P5 | Evaluation v2: customers the builders did not script, voiced end to end, matched closed arm | Not started; needs P1, P2, P3a |
| P7 | 60-second demo, two-page brief, written submission, last claims recheck | Last |

`USER-GUIDE.md` is written (a guide worker, kept open in Orca). **Remaining in iteration 2:** steps 3 to 7 above.

**Whole-suite collection, fixed 2026-11-10:** `tests/server/test_prompts.py` shared a basename with `tests/dialogue/test_prompts.py` and stopped collection; it is now `tests/server/test_server_prompts.py`. `uv run pytest --collect-only` collects 4,443 of 4,446 (3 live tests deselected) while the P2 fix round is still editing `tests/dialogue`. Collected, not run: the suite is not yet known to be green.

**A report and the code disagree on the order of the two readings.** `P2-contract.md` section 5 asks the server to pass v2.5 first on amount turns (iteration 1 verifier finding H4, `references/reviews/iter1/verifier-voice-and-dialogue.md`: on the 240 real Prisma pairs of the development amounts set, the held figure was wrong 2 times with v2.5 first against 16 with v3.0 first). The code passes v3.0 first (`readings()` in `samajh/server/samajh_dialogue.py`). Decide it when P1 is re-verified; the evidence is on the development set, not the held-out one.

**Credits:** about 295 of the 1,000 project cap (5,000 on the account) by the coordinator's estimate; the ledger file read 275.79 when checked for this update, and the gap is unexplained. Estimates, not dashboard readings. **Open for the next judge:** the call asks almost nothing about risk, while 85Y speaks of features and risks; whether to add a risk question.

### Waiting on the user
- **A Hindi and Hinglish wording review** of `references/pilots/P2-lines-for-review.md`: hold it until the P2 fix round lands; the coordinator regenerates the file and says when.
- **A language question:** does "teen lakh chalis" mean 3,40,000 or 3,00,040? It decides whether 14 of the 40 held-out number-formatting failures count (`verify-P6.md`, finding 2).
- **A go-ahead to copy two P6 reports from the coordinator's scratchpad into the repo:** `eval/amounts_v2/REPORT.md` and `references/pilots/gnani-number-formatting-report.md`.
- The human calls (P4): recruit one to three consenting friends now; the calls wait for P1 and P2 verified.
- One reading of the STT and TTS totals on the Gnani dashboard (app.gnani.ai); the closing date and submission steps from the challenge page; rotating the Gnani and OpenRouter keys when the build is finished (both were pasted into a chat transcript).
