# Samajh build — orchestration rules and iteration log

Every worker reads this file, `CLAUDE.md` and `DESIGN.md` before starting. `DESIGN.md` is the product spec; this file is how we build it.

## Roles and models (set by the user)

| Work | Model | Effort |
|---|---|---|
| Planning, architecture, reviewing | Fable (`claude-fable-5-2`) | high |
| Writing code | Fable (`claude-fable-5-2`) | medium |
| Fact and claims research | Sonnet | default |

An execution manager (an Orca worker) owns one work package. It does not write the bulk of the code itself. It runs the loop below with its own subagents, passing `model` and `effort` on each `Agent` call as in the table.

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
- Client signatures and caveats: `references/pilots/W2-clients-report.md`. Never run `tests/clients/probes/gnani_probe.py` (it bypasses the lock).
- Workers hit account usage limits. Keep subagent use lean: one planner pass, builders, one reviewer pass.

---

## Iteration log

### Iteration 1 — text path and clients (started 2026-11-10)

Goal: everything that needs no audio loop. At the end, a transcript goes in and a flagged case with evidence comes out, the gold set is frozen, and the Gnani and LLM clients are proven live.

| WP | Scope | Owns | Wave | Status |
|---|---|---|---|---|
| W1 core | types, amount normaliser, rule engine | `samajh/types.py`, `samajh/amounts/`, `samajh/rules/`, `tests/core/` | A | W1 and W1b (which replaced W1 after a usage-limit stall): done. 1,100 core tests pass, ruff clean. The post-review fixes have not had a second independent review. Report: `references/pilots/W1-core-report.md` |
| W2 clients | Gnani client (STT/TTS, lock, backoff, cache, ledger, cap) and OpenRouter client | `samajh/clients/`, `tests/clients/` | A | Done |
| W3 claims | Verify regulatory and Gnani-API claims against primary sources | `references/claims/` | A | Done |
| W4 scenarios | 96 scenarios, gold verdicts, hash freeze | `samajh/scenarios/`, `data/scenarios/`, `tests/scenarios/` | B (after W1) | In progress (Wave B) |
| W5 extractor | LLM extraction to strict schema with quoted spans, text-path eval | `samajh/extract/`, `tests/extract/`, `eval/text_path/` | B (after W1, W2) | In progress (Wave B) |
| W7 voice transport | FastAPI proxy, browser phone, turn-taking measured REST vs streaming | `samajh/server/`, `web/`, `tests/server/` | A2 (started early, independent of the core) | In progress |
| W8 audio eval harness | phone-line transforms, resumable voicing/STT runner, amounts test set at scale | `samajh/audio/`, `samajh/evalkit/`, `tests/audio/`, `tests/evalkit/`, `eval/amounts/`, `data/amounts/` | A2 (started early, independent of the core) | Done. 417 tests; 2,640 transcriptions; 93.74 estimated credits. The reviewer's 8 findings are fixed but not re-reviewed. Report: `eval/amounts/REPORT.md` (TTS audio only) |
| W9 dialogue | call state machine and prompt scripts in four languages | `samajh/dialogue/`, `tests/dialogue/`, `data/prompts/` | — | In progress |

W7 and W8 have live Gnani access, through the shared client lock (`samajh/clients/gnani`).

Estimated Gnani credits used so far: about 105 of the 1,000 cap (W2 11.58, W8 93.74; W7 not yet reported). The ledger itself read 113.80 estimated credits when the W8 report was written, other workers included. The figures are client estimates, not dashboard readings.

Then: independent verifier and judge review the iteration before iteration 2 (voice path and browser phone) is planned.
