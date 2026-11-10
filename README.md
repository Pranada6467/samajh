# Samajh

Samajh is a post-sale understanding callback for Indian lenders: a teach-back-style comprehension check. The customer explains in their own words, in their own language, what they bought with their loan, and plain code compares that against the bank's records; every mismatch becomes evidence a human can review.

It is built for Gnani AI's Great Indian AI Internship Challenge on Prisma STT and Timbre TTS, and targets the post-sale feedback duty in RBI para 85Y (commercial banks) and 101Y (NBFCs), in force from 1 January 2027. All data is synthetic. The product languages are Hindi and Hinglish; Tamil and Kannada stay in the code as experimental.

## Status (2026-11-10, end of iteration 2's build wave)

Iteration 1 built the parts and was reviewed by two verifiers and a judge (`references/reviews/iter1/`): continue with changes, 69 of 100 against the idea's 84, because the parts had never been joined into one call. Iteration 2 joins them. The state of each package is in `ORCHESTRATION.md`, "Coordinator handoff". In short:

| Part | State |
|---|---|
| The call on the browser phone, to a case file (P1) | Built. A whole Samajh call (disclosure, questions, read-backs, close) runs through the real HTTP API and in headless Chrome and ends in a case file with a tier, a short summary and every quote with its audio offset. Customer voices are Timbre audio: **no person has spoken to the phone.** Not independently verified; its prepared calls must be re-voiced when the call's lines are final |
| The call itself, `samajh/dialogue` (P2) | **Fix round in progress.** Built as call v2 (short opening, third-party and refusal handling, a branch for "I took nothing"). An independent verifier on fresh inputs found it not ready for a live line: the loan was named to 16 of 64 third parties, and 25 of 45 refusals got the next question with the word lists alone (16 of 45 with the LLM fallback). The fix makes the classifier the primary judge at the opening and adds safe defaults and new outcomes. Text only; no fluent human has read the lines |
| The decision chain (P3a) | Built and independently verified (sound with conditions); the conditions are fixed and not yet re-verified. Four tiers: `refer`, `incomplete`, `understanding_gap`, `clear` |
| Loan book, reviewer queue, half-yearly report (P3b) | Built and independently verified (sound with conditions; every number in its report recounted and matched); the conditions are fixed and not yet re-verified. Over a synthetic 200-loan book with simulated customers, so no share it shows says anything about a real lender. Phone calls enter the queue, but the phone cannot yet call a loan from the loan book |
| The Gnani amounts finding (P6) | Built and independently verified: every number reproduced and the freeze order confirmed. Result below |
| Human calls (P4), evaluation of Samajh on customers the builders did not script (P5), demo and submission (P7) | Not started |

What is measured so far, each with what limits it:
- **Prisma v3.0 and amounts that skip a place-value group (held-out, TTS audio).** On a held-out set of 280 synthetic Hindi and Hinglish sentences, on simulated 8 kHz phone audio, v3.0 `transcribe` wrote a different amount for 40 of 68 skipped-group amounts (59%, 95% CI 47-70) and for 0 of 68 matched controls. Its `verbatim` output of the same audio had the right number words in all 40, and v2.5 `transcribe` wrote none wrong. 14 of the 40 are "X lakh Y" phrases that colloquial Hindi may mean differently; 26 are wrong under any reading. Accepting an amount only when v3.0 and v2.5 agree accepted 224 of 280 synthetic clips and 113 of 124 public Hindi recordings, with no wrong amount accepted; the recordings are mostly from training splits of public datasets and only 4 skip a group, so they are a separate, possibly optimistic result. Details and the full list of what is not claimed: `CLAUDE.md` ("Gnani API facts"), `eval/amounts_v2/`, `references/reviews/iter2/verify-P6.md`.
- **The decision chain on scripted text (not speech).** The frozen scenario set (144 calls written by the team, 36 base cases; Hindi and Hinglish are 72 calls) was rerun after P3a's changes (one live pass, then cache-only reruns after each fix round): of 38 Hindi and Hinglish calls with a customer problem, 2 ended `clear` or `understanding_gap` (1 of 19 base cases: a wrong cancellation window, which is `understanding_gap` by design); of 18 informed customers on a compliant record, 0 were referred; of 16 informed customers with a fault on the lender's record, 8 were referred. Gold agrees with the rule engine on 144 of 144 partly because of a coordinator decision on 8 scenarios. Report: `eval/text_path/runs/frozen__openai-gpt-6-luna.md`. The teach-back against yes/no comparison (E1) is retired as a headline because it is true by construction.
- **Gnani API behaviour** measured live, including that the one-request limit is per account and not per key (`references/pilots/api-probe-iter1.md`, `CLAUDE.md`).

Not verified: anything on human speech (no human voice recording exists); anything in Tamil or Kannada (no fluent reviewer); the bot's wording (no fluent human has read a line; nobody has listened to the voice); the end-of-speech thresholds (not set on human audio); the whole-suite test run (see "Run the tests").

## Set up

Needs Python 3.11, [uv](https://docs.astral.sh/uv/) and `ffmpeg` on the path.

```
uv sync
cp .env.example .env     # then fill in GNANI_API_KEY and OPENROUTER_API_KEY
```

`.env` is gitignored. Never commit or print a key.

## Run the phone

Needs the setup above and `GNANI_API_KEY` in `.env`. Every call spends Gnani credits.

```
uv run python -m samajh.server --port 8085
```

Then open `http://127.0.0.1:8085/` in Chrome, pick a record and a language (Hindi or Hinglish) and place the call. The record picker holds three packaged demo records; a loan from the loan book cannot be called yet. The server runs the Samajh dialogue by default (the three-question `stub` dialogue stays for tests: `replay --dialogue stub`). It binds 127.0.0.1 only; `--allow-host NAME` admits another host name. Optionally pre-make the bot's fixed lines so a call finds them in the cache: `uv run python -m samajh.server.prompts build --lang hi --lang hi-en`. To run a whole call without a microphone, with the server running:

```
uv run python -m samajh.server.replay tests/fixtures/server/calls/hero --url http://127.0.0.1:8085 --out OUT
```

The prepared calls in `tests/fixtures/server/calls/` were voiced against the call before P2 and will stop with `script_drift` until they are re-voiced (`references/pilots/P1-report.md`, section 4).

Gnani allows one active request per account. Do not run an evaluation while a call is live: a live turn waits 5 s for the lock, then fails with `gnani_busy`. Session logs, recordings and case files are written under `.samajh/sessions/`.

## Run the review pages

The reviewer queue, case pages, attempt log and half-yearly report read a batch from `.samajh/ops`. Build the simulated batch (scripted customers and extraction, no model, no network), then start the phone server and open `http://127.0.0.1:8085/review/`:

```
uv run python -m samajh.ops demo
uv run python -m samajh.ops ingest      # bring finished phone sessions into the batch
```

`uv run python -m samajh.ops --help` lists `book`, `init`, `draw`, `run`, `ingest`, `verify` and `report`. Every page says that the book, the customers and the calls are simulated.

## Play a call in the terminal

The dialogue runs as text, with no audio and no Gnani call. You type the customer's replies:

```
uv run python -m samajh.dialogue play --record tests/dialogue/fixtures/record_gold_loan.json --lang hi
```

`--lang` is `hi`, `hi-en`, `ta` or `kn`; `--help` lists the rest (`--llm` adds the optional LLM fallback and sends the question and your reply to OpenRouter, so type only synthetic text; `first || second` gives one turn two transcripts). `samajh/dialogue` is being fixed (P2), so expect it to change or to break for a while.

## Run the tests

```
uv run pytest                  # offline tests only (live tests are deselected)
uv run pytest tests/core -q    # or one folder at a time
uv run ruff check samajh tests
```

The whole tree collected 4,443 tests on 2026-11-10 (3 live ones deselected) after `tests/server/test_prompts.py` was renamed to `test_server_prompts.py` (the rename is staged, not committed; before it, two files with that basename stopped collection). **The full suite has not been run as one, and it is not known to be green.** Collected per folder: core 1,708, extract 251, scenarios 50, ops 73, server 310, clients 297, audio 32, evalkit 799, dialogue 923 before the fix round (`samajh/dialogue` is being changed by P2's fix round, so its tests may be red until it reports). The package reports give the passes at the time each package finished.

`uv run pytest -m live` makes real Gnani and OpenRouter calls and costs credits; the client refuses to go past `GNANI_CREDIT_CAP` (1000 in `.env.example`). To see what the client has spent: `uv run python -m samajh.clients.gnani ledger` (a local read; about 295 of 1,000 credits by estimate, no dashboard reading yet). Never run `tests/clients/probes/gnani_probe.py`: it bypasses the lock.

## Documents

| File | What it is |
|---|---|
| `DESIGN.md` | The current design (v3): problem, rule, call flow, rules and tiers, evaluation, what we can and can't claim |
| `ORCHESTRATION.md` | Build rules, the iteration log and the coordinator handoff (where a new session starts) |
| `USER-GUIDE.md` | What the project's owner personally needs to do |
| `CLAUDE.md` | Project instructions for coding agents, including the verified Gnani API facts and a map of the files |
| `RESEARCH.md` | Research on the challenge, Gnani products, the market and all idea directions |
| `IDEAS-HILLCLIMB.md` | The 5-round evaluation that chose this idea |
| `references/reviews/` | Independent reviews: iteration 1 (two verifiers and the judge) and iteration 2 (P6 verification, probes) |
| `references/claims/` | Claims ledger, design corrections and the quote checker (saved sources are local-only) |
| `references/pilots/` | Package reports and contracts (P1, P2, P3a and the iteration 1 reports), the Gnani API probe, the transport report, rendered reviewer pages (`p3b-artifacts/`) |
| `eval/amounts_v2/`, `eval/amounts/` | The held-out and the development spoken-amounts evaluations (TTS audio; real voices for the held-out one) |
| `eval/text_path/` | The text-path evaluation of the extractor and the decision chain: rerunnable scripts and `runs/` reports. Scripted text only, no speech |
| `data/scenarios/` | The frozen scenario set (`gold.jsonl`, `calls.jsonl`, `FROZEN.json`), its datasheet and changelog. Synthetic; for final measurement only |
| `data/loanbook/` | The synthetic 200-loan book behind the reviewer pages, with its README |
| `references/real-voice-datasets.md` | Licensed real-voice Indic datasets for evaluation |
