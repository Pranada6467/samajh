# Samajh

Samajh is a Hindi and Hinglish voice callback for lenders and their compliance reviewers: it asks a borrower, in their own words, what they bought with their loan, and plain code compares the answer with the lender's record, so a human reviewer gets quotes and audio offsets to look at, never a verdict.

Status in one line: it runs end to end on synthetic data with Timbre-voiced customers, **no person has spoken to the phone yet**, and the call and the phone are not independently verified (details under "Status" below).

<img src="references/pilots/p3b-artifacts/phone-case-1280-light.png" alt="Reviewer case page for a synthetic phone call: the lender's record on the left; on the right each place the customer's words differ from the record, with the quote, the turn and a play link at that point in the recording" width="640">

*A case page for one synthetic phone call (synthetic record, Timbre customer voice), rendered during the P3b build. A flag is evidence for a human to review, not a finding. The reviewer pages are still being changed.*

## Three numbers (amounts that skip a place-value group)

All three are on synthetic or public speech, not on real callers, and all use the wording the independent verification allows (`references/reviews/iter2/verify-P6.md`, "Wording for a public submission"; `CLAUDE.md`, "Gnani API facts").

1. **40 of 68, against 0 of 68.** On a held-out synthetic set built to stress amounts that skip a place-value group (TTS audio, simulated 8 kHz phone audio), Prisma v3.0 `transcribe` wrote a different amount for 40 of 68 such amounts (59%, 95% CI 47-70) and for 0 of 68 matched controls. Its `verbatim` output of the same audio had the right number words in all 40, and v2.5 `transcribe` wrote none wrong. 26 of the 40 are wrong under any reading ("one lakh three hundred" written as 1,300; "five crore twenty-six thousand" as 5,26,000); the other 14 are "X lakh Y" phrases that colloquial Hindi may mean differently. The 68 are 24% of the set by design, so this is not a rate of how often amounts go wrong.
2. **224 of 280.** Accepting an amount only when Prisma v3.0 and v2.5 `transcribe` agree accepted 224 of 280 synthetic clips with no wrong amount accepted. The rule was written into the experiment plan before any audio was voiced (`verify-P6.md`, finding 3); a cheaper variant was chosen on these same sets and is not claimed.
3. **113 of 124.** The same rule accepted 113 of 124 public Hindi read or extempore recordings (IndicVoices and Kathbath) with no wrong amount accepted. 107 of the 124 are from the datasets' train splits, which Gnani may have trained on, so this may be optimistic; only 4 of the recordings skip a group (v3.0 was wrong on 1: too few for a rate).

Sources: counts in `eval/amounts_v2/tables-tts.md` (phone condition, from line 207) and `eval/amounts_v2/tables-realvoice.md` (phone condition, from line 128), recomputed independently in `verify-P6.md`.

## Gnani models and endpoints used

Base URL `https://api.vachana.ai`, one key in the `X-API-Key-ID` header, held by a backend proxy.

- **Prisma STT v3.0 (`prisma-v3.0`) and v2.5 (`prisma-v2.5`)** through `POST /stt/v3` (REST, clips of 30 s or less): `format=transcribe`, language set per call. v3.0 reads every customer turn; v2.5 gives a second reading when the customer says a figure.
- **Prisma Batch** (`prisma-v3.0`, `/stt/v3/batch/jobs`, two speakers): the whole call after it ends, for segment times that give each quote its audio offset.
- **Timbre TTS v3.0** (`timbre-v3.0`, `POST /api/v1/tts/inference`, 8 kHz, voice Shivani): the bot's lines, and the synthetic customers used in testing.
- Not used: streaming, voice cloning, Agent Builder. Extraction after the call uses `openai/gpt-6-luna` through OpenRouter, and the dialogue's turn classifier uses `mistralai/mistral-small-3.2-24b-instruct` (`DESIGN.md` section 7).

## Why two Prisma models

The difference above is between the two models on one kind of amount: v3.0 `transcribe` wrote a different number for amounts that skip a place-value group, while its `verbatim` output of the same audio had the right words and v2.5 wrote none wrong. Which stage causes it is not established. So Samajh asks both models when the customer says a figure, accepts the amount only when they agree, and otherwise asks again.

What the agreement rule adds depends on the data. **On the held-out synthetic set it adds nothing measured:** v2.5 `transcribe` alone wrote no wrong amount (0 of 280; 268 right, 12 refused), while agreement accepted 224, so there it costs 44 more re-asks (on the 68 skipped-group amounts, 22 accepted against 66 for v2.5 alone). **The case for it rests on the 124 public recordings** (`tables-realvoice.md`, phone condition, lines 197-201): v2.5 alone accepted 119 and wrote a wrong amount on 4 (for example 500 as 100); v3.0 alone accepted 123 and was wrong on 3; agreement accepted 113 with 0 wrong, because the two readings differed on each of the 6 clips where either was wrong. That is 4 and 3 wrong against 0 on one small set, mostly from train splits and with only 6 clips at stake, so it is a reason to keep the check, not a measured gain. On a figure turn the dialogue is given v2.5's reading first and reads back v2.5's figure when the two differ; v3.0 is the reading for every other turn (it refused fewer of these recordings: 1 of 124, against 5 for v2.5).

## What one completed call costs (estimate)

One whole hero call (Hindi, the P1 run on 2026-11-10, session `20261110T103108-9f2e34f8dfdf`: 15 customer turns, a 157.47 s recording, tier `refer`). Gnani credits come from the client's own rates, 0.010 per audio second and 0.002 per TTS character (`samajh/clients/defaults.toml`); no API reports cost, so these are estimates, each possibly 20% off or more, and the dashboard has not been read. The turn and read-back figures are the per-request estimates in the call's session log (`.samajh/sessions/20261110T103108-9f2e34f8dfdf/session.json`); the Batch figure is the `batch.billed` row for 157.47 s in `.samajh/ledger.jsonl`, the file that `uv run python -m samajh.clients.gnani ledger` totals (a local read).

| Part | Quantity | Arithmetic | Credits |
|---|---|---|---|
| Turn STT, v3.0 (15 readings) and v2.5 (2 readings) | 26.80 s + 2.64 s = 29.44 s | 29.44 x 0.010 | 0.294 |
| Prisma Batch, whole recording (assumed to bill like STT) | 157.47 s | 157.47 x 0.010 | 1.575 |
| Timbre, one read-back made on the call | 54 characters | 54 x 0.002 | 0.108 |
| **Total** | | | **about 1.98** |

The 24 fixed bot lines in that call came from the cache (1,612 characters, 3.22 credits if voiced fresh); they are made once for all calls (101 lines, about 13 credits). The LLM that reads the transcript after the call cost $0.00171 per transcript on the frozen set (144 transcripts, $0.24589; `DESIGN.md` section 7), and the hero call's own 21 extraction requests cost $0.00134 in the ledger. The turn classifier that runs during the call is not included: its 15 requests across the three calls in that time window cost under $0.0005 together. Caveats: Timbre voices speak short answers, so a person talking longer costs more STT and Batch; the call ran on the dialogue as it was before P2's fix round, whose lines are still changing; and one call is not an average.

## Run it

Needs the setup below (Python 3.11, `uv`, `ffmpeg`, keys in `.env`). The phone spends Gnani credits and needs `GNANI_API_KEY`:

```
uv run python -m samajh.server --port 8085
```

Open `http://127.0.0.1:8085/` in Chrome and place a call. To see the dialogue as text, with no audio, no key and no credits (the call is being fixed, so it may change or break):

```
uv run python -m samajh.dialogue play --record tests/dialogue/fixtures/record_gold_loan.json --lang hi
```

---

## About this project

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
| The Gnani amounts finding (P6) | Built and independently verified: every number reproduced and the freeze order confirmed. Result at the top and below |
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
