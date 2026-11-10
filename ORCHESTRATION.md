# Samajh build — orchestration rules and iteration log

Every worker reads this file, `CLAUDE.md` and `DESIGN.md` before starting. `DESIGN.md` is the product spec; this file is how we build it.

## Roles and models (set by the user)

| Work | Model | Effort |
|---|---|---|
| Orchestrating: planning, writing instructions for subagents, deciding | Fable (`claude-fable-5-2`) | high |
| Building: writing code, tests, data | Opus (`model: "opus"`) | medium |
| Verifying: independent review, attacks, reproduction | Opus (`model: "opus"`) | high |
| Fact and claims research, documentation updates | Sonnet | default |

Changed by the user on 2026-11-10 (iteration 2). Fable is used only to give instructions: the coordinator and each execution manager (an Orca worker) run on Fable and do not write the product code or run the review themselves. An execution manager owns one work package, splits it into small tasks, and hands each to a subagent with `model` and `effort` set on the `Agent` call as in the table: Opus medium to build, a separate Opus high subagent that wrote none of the code to verify. This replaces any older line in a task spec that says to do the work yourself or names Fable for building or reviewing.

## The loop, per work package

1. **Plan.** Load `pstack-architect`. Sketch types, signatures and module layout before code. Write the plan into your final report, not into a new file.
2. **Verify claims.** Every external fact the plan relies on (an API parameter, a regulation paragraph, a library behaviour) is checked against a primary source or a live call before code depends on it. Unverified facts are marked `[unverified]` in code comments and in your report.
3. **Build.** Spawn builder subagents (Fable, medium). Small verifiable units, tests alongside.
4. **Review.** Spawn an independent reviewer subagent (Fable, high) that did not write the code. It runs the tests, tries to break the change, and reports. Fix what it proves. Then report.

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
- **Gnani concurrency is 1 for the whole key.** Only a worker whose spec says "live Gnani access: yes" may call `api.vachana.ai`. Everyone else works offline. All calls go through the shared client once it exists (cross-process lock, cache, ledger).
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

- Gnani API: the "Gnani API facts" section of `CLAUDE.md` now matches `references/pilots/api-probe-iter1.md`, which stays the evidence (measured live) and wins if the two ever differ. In short: `codemix` is a `format` value on v3.0; v2.5 `format=transcribe` gives digits beyond Hindi and English; a second simultaneous REST request gets an instant 429; a WebSocket streaming session does not occupy the one active-request slot; no API surface reports credit cost.
- Regulation and cases: `references/claims/claims-ledger.md` and `references/claims/design-corrections.md`. `DESIGN.md` is v2 and already applies them.
- Extraction LLM: `openai/gpt-6-luna`, not the W2 default (`mistralai/mistral-small-3.2-24b-instruct`); the reasons and numbers are in `references/pilots/W5-extractor-report.md` §2.4 and `DESIGN.md` §7. It rejects the `temperature` parameter (OpenRouter answers 404), so call it through `samajh.pipeline.default_llm()`.
- Client signatures and caveats: `references/pilots/W2-clients-report.md`. Never run `tests/clients/probes/gnani_probe.py` (it bypasses the lock).
- Workers hit account usage limits. Keep subagent use lean: one planner pass, builders, one reviewer pass.

---

## Iteration log

### Iteration 1 — text path and clients (started 2026-11-10)

Goal: everything that needs no audio loop. At the end, a transcript goes in and a flagged case with evidence comes out, the gold set is frozen, and the Gnani and LLM clients are proven live.

| WP | Scope | Owns | Wave | Status |
|---|---|---|---|---|
| W1 core | types, amount normaliser, rule engine | `samajh/types.py`, `samajh/amounts/`, `samajh/rules/`, `tests/core/` | A | W1 and W1b (which replaced W1 after a usage-limit stall): done. 1,223 core tests pass (after the amounts parser fix, which added `cross_check`), ruff clean. The post-review fixes have not had a second independent review. Report: `references/pilots/W1-core-report.md` |
| W2 clients | Gnani client (STT/TTS, lock, backoff, cache, ledger, cap) and OpenRouter client | `samajh/clients/`, `tests/clients/` | A | Done |
| W3 claims | Verify regulatory and Gnani-API claims against primary sources | `references/claims/` | A | Done |
| W4 scenarios | 144 scenarios (36 base cases x 4 languages), gold verdicts, hash freeze | `samajh/scenarios/`, `data/scenarios/`, `tests/scenarios/` | B (after W1) | Done. 144 scenarios, frozen at version 3 (`gold.jsonl` sha256 beginning `14e49b58`), 50 tests. Gold agrees with the rule engine on 144 of 144, reached partly by a coordinator decision on 8 scenarios (premium "I don't know"), made before any audio or LLM extraction. One independent review (of version 1); no reviewer has seen versions 2 or 3. The frozen set is for final measurement only, never for tuning. Report: `data/scenarios/W4-report.md` |
| W5 extractor | LLM extraction to strict schema with quoted spans, text-path eval | `samajh/extract/`, `tests/extract/`, `eval/text_path/` | B (after W1, W2) | W5 and W5b done. The original W5 worker stopped on the usage limit; W5b reviewed its code, fixed the 7 findings, ran the frozen set once and wrote the report. 176 tests pass (`tests/extract/`), ruff clean. OpenRouter ledger total 0.52 USD of the 3 USD budget (whole project, all workers). The extraction model is `openai/gpt-6-luna`. Results are on scripted text only (no speech), Tamil and Kannada not human-reviewed, and the reviewer's fixes have had no second independent review. Report: `references/pilots/W5-extractor-report.md` |
| W7 voice transport | FastAPI proxy, browser phone, turn-taking measured REST vs streaming | `samajh/server/`, `web/`, `tests/server/` | A2 (started early, independent of the core) | Done. 183 offline tests and 1 live test; about 10 estimated credits. The reviewer's 11 findings are fixed but not re-reviewed. REST per turn with a 700 ms browser end-of-speech detector is the shipped path; streaming was measured and not built (TTS clips only, no human speech; no human has used the phone). Report: `references/pilots/voice-loop-iter1.md` |
| W8 audio eval harness | phone-line transforms, resumable voicing/STT runner, amounts test set at scale | `samajh/audio/`, `samajh/evalkit/`, `tests/audio/`, `tests/evalkit/`, `eval/amounts/`, `data/amounts/` | A2 (started early, independent of the core) | Done. 417 tests; 2,640 transcriptions; 93.74 estimated credits. The reviewer's 8 findings are fixed but not re-reviewed. Report: `eval/amounts/REPORT.md` (TTS audio only) |
| W9 dialogue | call state machine and prompt scripts in four languages | `samajh/dialogue/`, `tests/dialogue/`, `data/prompts/` | — | W9 and W9b done. The original W9 worker stopped on the usage limit before its review; W9b, who wrote none of the original code, reviewed it, fixed 11 proven defects and finished it. 671 tests pass (`tests/dialogue/`), ruff clean; `tests/core` and `tests/server` (1,483 tests) still pass. Gnani credits 0; OpenRouter about USD 0.02. Tested on synthetic text only (replies written by an LLM, no speech); no fluent human has read any language's lines, Tamil and Kannada are not human-reviewed, and the review's fixes have had no second independent review. Not connected to the phone, which still runs `StubDialogue` until the adapter is written in iteration 2. Report: `references/pilots/W9-dialogue-report.md` |

Iteration 1 build complete 2026-11-10. Independent review in progress: two verifiers and a judge, reports under references/reviews/iter1/.

W7 and W8 have live Gnani access, through the shared client lock (`samajh/clients/gnani`).

Estimated Gnani credits used so far: about 115 of the 1,000 cap (W2 11.58, W7 about 10, W8 93.74). The ledger itself read 113.80 estimated credits when the W8 report was written and 114 when the W7 report was written, other workers included. The figures are client estimates, not dashboard readings.

Then: when the independent verifier and judge review finishes, iteration 2 (the voice path: the adapter between the browser phone and `samajh/dialogue`, voicing the lines, human audio) is planned.

---

## Coordinator handoff (written 2026-11-10 ~16:00 IST; update this section whenever state changes)

A new coordinator session starts here. Read this section, then `references/reviews/iter1/judge.md` (the iteration-2 plan) and the two verifier reports beside it.

### How the user wants the work run
- The coordinator (Fable) orchestrates only: plans, writes instructions, decides, reports. It keeps its own context small.
- **Use Orca's orchestration for work packages**: `orca orchestration worker-start --spec-file <spec> --task-title "<title>" --worktree current --agent claude --model claude-fable-5-2 --effort high`. Each Orca worker is a Fable sub-orchestrator for one package. It does not write product code: it splits the package and briefs `Agent` subagents, **Opus medium to build, a separate Opus high to verify**, Sonnet for research and documentation. Guide: `orca skills get orchestration`. End the turn after starting workers; Orca wakes the coordinator. Never poll.
- Loop per package and per iteration: plan, verify claims, build, review. After each iteration an independent verifier and a judge review work and direction before the next iteration starts.
- Parallelise freely where lanes (owned paths) do not overlap. Only one request at a time can use the Gnani key; the client's lock enforces it, but never run an evaluation during a live demo call.
- Documentation is updated as soon as a result makes it stale, by Sonnet subagents. Reports are at most two pages.
- Local checkpoint commits after each finished package (the coordinator commits; workers never run state-changing git). Check staged diffs for the two keys before committing.
- Budgets: Gnani credits capped at 1,000 in total (about 115 estimated used before iteration 2, plus P6 and P1 spend: read `uv run python -m samajh.clients.gnani ledger`); OpenRouter cheap models by default.

### Lessons from this session
- Workers stop without warning when the account's 5-hour usage limit is reached, and a stopped worker does not wake on `send`. Stop it (`worker-stop`, then `worker-release`), commit a WIP checkpoint, and start a fresh worker with a "resume from what is on disk" spec. Fewer workers at once last longer.
- Use a quoted heredoc (`<<'EOF'`) for spec files: unquoted backticks get executed by the shell.
- Publish a short contract file early (`references/pilots/<package>-contract.md`) when other packages code against a package's types.

### Decisions in force (coordinator, 2026-11-10; details in DESIGN.md section 15 and the judge's report)
- Product languages are Hindi and Hinglish. Tamil and Kannada stay in the code as experimental, appear only in an appendix, and get no new effort.
- One product family (loan with credit-life cover). No second family.
- Outcome is a four-tier triage (`refer`, `incomplete`, `understanding_gap`, `clear`), not "any flag means review".
- Each amount turn gets two Prisma readings (v2.5 and v3.0); disagreement leads to a re-ask, and every amount is read back.
- Extraction model `openai/gpt-6-luna`, after the call; the dialogue's live fallback uses `mistralai/mistral-small-3.2-24b-instruct`.
- The scripted teach-back versus yes/no comparison (E1) is not a headline: it is true by construction. It is to be replaced by evaluation v2 (package P5).
- The lead Gnani finding is Prisma v3.0's number formatting of skipped-group amounts and two-model agreement as a confidence signal.

### Iteration 2 state
Plan: `references/reviews/iter1/judge.md` "Iteration 2 plan, ranked". Specs: the coordinator's scratchpad is not durable, so each package's scope is restated in its report once written.

| Package | Scope | Lane | State |
|---|---|---|---|
| P3a | Decision chain v2: tiers, case summary, verifier fixes, approximate and hedged answers | `samajh/types.py`, `samajh/rules`, `samajh/amounts`, `samajh/extract`, `samajh/pipeline.py`, `eval/text_path`, `tests/core`, `tests/extract` | Building (Opus medium, direct subagent of the coordinator); contract at `references/pilots/P3a-contract.md`; needs an Opus high verification when it reports |
| P2 | Call v2: third parties learn nothing, refusals, short opening, "took nothing" branch, payment-frequency question, line export for the user | `samajh/dialogue`, `data/prompts`, `tests/dialogue` | Building; contract at `references/pilots/P2-contract.md`; needs verification |
| P1 | One real Hindi/Hinglish call on the browser phone to a case file (adapter, two readings, Timbre prompts, Batch offsets, replay) | `samajh/server` (not `review_routes.py`), `web/` (not `web/review`), `tests/server` | Building; needs verification; depends on P2 and P3a landing |
| P6 | Gnani amounts finding: held-out TTS set, real voices from IndicVoices and Kathbath (local only), bug report for Gnani | `eval/amounts_v2`, `data/amounts_v2`, `samajh/evalkit` | Building; needs verification |
| P3b | Loan-book sampler, reach funnel, reviewer queue, half-yearly 85Y report page | `samajh/ops`, `web/review`, `samajh/server/review_routes.py`, `tests/ops`, `data/loanbook` | Partly built, paused; restart when P3a's types are in place |
| P4 | 20 improvised human calls in Hindi and Hinglish from brief cards | needs the user and consenting friends | Not started; needs P1 and P2 |
| P5 | Evaluation v2: persona-driven customers the builders did not script, matched closed arm, voiced end to end | new | Not started; needs P1, P2, P3a |
| P7 | 60-second demo, two-page brief, written submission, last claims recheck | new | Last |

When P1, P2, P3a, P3b and P6 are built and verified: full suite green, docs synced, checkpoint commit, then the iteration-2 verifier and judge, then iteration 3 (P4, P5, P7 and whatever the judge ranks).

### Waiting on the user
- A Hindi and Hinglish wording review of `references/pilots/P2-lines-for-review.md` once P2 writes it.
- The human calls (P4).
- One reading of the STT and TTS totals on the Gnani dashboard (app.gnani.ai) to turn credit estimates into measurements.
- Rotating the Gnani and OpenRouter keys when the build is finished (both were pasted into a chat transcript).
