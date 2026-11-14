# Samajh

**One-page pitch:** [PITCH.md](PITCH.md)

Samajh is a Hindi and Hinglish voice callback for lenders and their compliance reviewers: it asks a borrower, in their own words, what they bought with their loan; a language model turns the answer into fixed fields, every quote is checked against what was said, and plain code compares the fields with the lender's record, so a human reviewer gets the discrepancy, the quote and an audio offset to look at, never a verdict.

Status in one line: it runs end to end on synthetic data. Customer voices in the prepared calls are Timbre audio; the only human audio is two practice calls by one builder (not scored), and human calls by the team start on 2026-11-15. The call's latest full independent check (typed text, not speech) found it ready for consenting testers playing customers, with the classifier on and degraded sessions voided, and not ready for anyone else. Iteration 4 (2026-11-14) added name matching, a context-aware opening, a live language switch, pre-made lines, a tamper-evident evidence bundle, a human-session kit and open baselines; each part had one independent check on typed text, replayed TTS audio or fake sessions, and nothing has met a human voice yet.

<img src="references/pilots/p3b-artifacts/phone-case-1280-light.png" alt="Reviewer case page for a synthetic phone call on a loan drawn from the synthetic loan book, referred for review: the lender's record on the left; on the right the two places the customer's words differ from the record, each with the quote, the turn and a play link at that point in the recording, and under one understanding-gap quote a line with the two Prisma readings" width="640">

*A case page for one synthetic phone call (a loan drawn from the synthetic loan book, prepared Timbre customer audio), rendered on 2026-11-13 at commit 2568759: a call referred on what the customer said. A flag is evidence for a human to review, not a finding. The reviewer pages have changed since this picture (a token sign-in, a seal on each case).*

## Three numbers (amounts that skip a place-value group)

All three are on synthetic or public speech, not on real callers, and all use the wording the independent verification allows (`references/reviews/iter2/verify-P6.md`, "Wording for a public submission").

1. **40 of 68, against 0 of 68.** On a held-out synthetic set built to stress amounts that skip a place-value group (TTS audio, simulated 8 kHz phone audio), Prisma v3.0 `transcribe` wrote a different amount for 40 of 68 such amounts (59%, 95% CI 47-70) and for 0 of 68 matched controls. Its `verbatim` output of the same audio had the right number words in all 40, and v2.5 `transcribe` wrote none wrong. 26 of the 40 are wrong under any reading ("one lakh three hundred" written as 1,300; "five crore twenty-six thousand" as 5,26,000); the other 14 are "X lakh Y" phrases that colloquial Hindi may mean differently. The 68 are 24% of the set by design, so this is not a rate of how often amounts go wrong.
2. **224 of 280.** Accepting an amount only when Prisma v3.0 and v2.5 `transcribe` agree accepted 224 of 280 synthetic clips with no wrong amount accepted. The rule was written into the experiment plan before any audio was voiced (`verify-P6.md`, finding 3); a cheaper variant was chosen on these same sets and is not claimed.
3. **113 of 124.** The same rule accepted 113 of 124 public Hindi read or extempore recordings (IndicVoices and Kathbath) with no wrong amount accepted. 107 of the 124 are from the datasets' train splits, which Gnani may have trained on, so this may be optimistic; only 4 of the recordings skip a group (v3.0 was wrong on 1: too few for a rate).

Sources: `eval/amounts_v2/tables-tts.md` (phone condition, from line 207) and `eval/amounts_v2/tables-realvoice.md` (phone condition, from line 128), recomputed independently in `verify-P6.md`.

**Against open models (iteration 4, `eval/openbench/REPORT.md`; independently recomputed, 0 disagreements).** On the same 68 simulated-phone skipped-group amounts (TTS audio, Hindi and Hinglish, scored by our frozen parser), Whisper large-v3 wrote 33 wrong amounts, IndicWhisper 15 and Gemini 3 Flash 8, against 40 for Prisma v3.0 `transcribe` and 0 for v2.5; of these, 4, 2 and 1 are the right number in a form our parser cannot read. Whisper and Gemini also wrote some "X lakh Y" amounts as X lakh Y thousand (10 and 5), the reading we left open as possibly colloquial. No open model matched v2.5 `transcribe` on these clips. Adding a third reading as a majority vote accepted wrong amounts (Whisper 10, Gemini 5 of 280); requiring all three to agree accepted none and asked again more often. This is not "Prisma is better than open models": the sets are TTS audio and the parser was built on Prisma's output style.

## Gnani models and endpoints used

Base URL `https://api.vachana.ai`, one key in the `X-API-Key-ID` header, held by a backend proxy.

- **Prisma STT v3.0 (`prisma-v3.0`) and v2.5 (`prisma-v2.5`)** through `POST /stt/v3` (REST, clips of 30 s or less): `format=transcribe`, language set per call. v3.0 reads every customer turn; v2.5 gives a second reading where the call expects a figure (for example the premium). On right-party replies v3.0 gets the borrower's first name as its one `keyterm`.
- **Prisma Batch** (`prisma-v3.0`, `/stt/v3/batch/jobs`, two speakers): the whole call after it ends, for segment times that give each quote its audio offset.
- **Timbre TTS v3.0** (`timbre-v3.0`, `POST /api/v1/tts/inference`, 8 kHz, voice Shivani): the bot's lines, and the synthetic customers used in testing.
- **Prisma streaming** (`/stt/v3/stream`) is built into the server and **off by default**; REST is the shipped path. Its billing is unknown.
- Not used: voice cloning, Agent Builder. Extraction after the call uses `openai/gpt-6-luna` through OpenRouter, and the dialogue's turn classifier uses `mistralai/mistral-small-3.2-24b-instruct` (`DESIGN.md` section 7).

## Why two Prisma models

The difference above is between the two models on one kind of amount: v3.0 `transcribe` wrote a different number for amounts that skip a place-value group, while its `verbatim` output of the same audio had the right words and v2.5 wrote none wrong. Which stage causes it is not established. So Samajh asks both models when the customer says a figure, accepts the amount only when they agree, and otherwise asks again.

What the agreement rule adds depends on the data. **On the held-out synthetic set it adds nothing measured:** v2.5 `transcribe` alone wrote no wrong amount (0 of 280; 268 right, 12 refused), while agreement accepted 224, so there it costs 44 more re-asks. **The case for it rests on the 124 public recordings** (`tables-realvoice.md`, phone condition, lines 197-201): v2.5 alone accepted 119 and wrote a wrong amount on 4 (for example 500 as 100); v3.0 alone accepted 123 and was wrong on 3; agreement accepted 113 with 0 wrong, because the two readings differed on each of the 6 clips where either was wrong. That is one small set, mostly from train splits and with only 6 clips at stake, so it is a reason to keep the check, not a measured gain. On a figure turn the dialogue is given v2.5's reading first and reads back v2.5's figure when the two differ; v3.0 is the reading for every other turn.

## What one completed call costs (estimate)

One whole hero call (Hindi, 2026-11-10: 15 customer turns, a 157.47 s recording, tier `refer`) came to about **1.98 estimated Gnani credits**: turn STT 0.294, Prisma Batch 1.575 (assumed to bill like STT), one read-back 0.108, at 0.010 credits per audio second and 0.002 per TTS character (`samajh/clients/defaults.toml`). No API reports cost, so each rate may be 20% off or more and the dashboard has not been read. The fixed lines are made once for all calls (now at server start). The extraction LLM cost $0.00171 per transcript on the frozen set (`DESIGN.md` section 7). One call is not an average, and the bot's lines will change after the wording review. The project ledger reads about 548.82 of the 1,000-credit cap on 2026-11-14 (`uv run python -m samajh.clients.gnani ledger`, a local read; the estimates, not dashboard readings).

## Run it

Needs the setup below (Python 3.11, `uv`, `ffmpeg`, keys in `.env`). The phone spends Gnani credits and needs `GNANI_API_KEY`; the classifier and extraction need OpenRouter credit:

```
uv run python -m samajh.server --port 8085
```

Open `http://127.0.0.1:8085/` in Chrome and place a call. The first start makes every fixed bot line before it accepts a call (see "Run the phone"). To see the dialogue as text, with no audio, no key and no credits:

```
uv run python -m samajh.dialogue play --record tests/dialogue/fixtures/record_gold_loan.json --lang hi
```

---

## About this project

Samajh is a post-sale understanding callback for Indian lenders. The customer explains in their own words, in their own language, what they bought with their loan; a language model turns the answers into fixed fields, and plain code compares them against the bank's records. Where an answer conflicts with the record, the case becomes evidence a human can review; gaps in understanding are counted in the half-yearly report.

It is built for Gnani AI's Great Indian AI Internship Challenge on Prisma STT and Timbre TTS, and targets the post-sale feedback duty in RBI para 85Y (commercial banks) and 101Y (NBFCs), in force from 1 January 2027: a mechanism to seek feedback within 30 days of a sale, to check that customers understood the product's features and risks, and a half-yearly report on the findings. 85Y sets no channel and does not require random sampling, call-backs or an independent unit; it names call-backs and surveys as examples. All data is synthetic. The product languages are Hindi and Hinglish; Tamil and Kannada stay in the code as experimental and are not human-reviewed.

**Team:** Pranav Pandian and Sambhav Jain.

## Status (2026-11-14, code at commit 1282a1c)

Iteration 1 built the parts. Iteration 2 joined them into one call; each package was checked by an independent verifier that wrote none of the code, on inputs the builder never saw (`references/reviews/iter2/`). Iteration 3 added the right-party setting, fix rounds for the call and the decision chain, and the first evaluation on customers the builders did not script, on text (`references/reviews/iter3/`, `eval/p5/REPORT.md`). An independent technical review (internal) then found the decision back end sound and the voice front end a prototype never tuned on speech. **Iteration 4 answers it.** Each part below had one independent check and one fix round, on typed text, replayed TTS audio or fake sessions (the fix rounds rerun inputs already seen); two small follow-ups are checked by their builder only. Offline suite: 8,874 passed, 3 deselected (live).

| Part | State |
|---|---|
| The call on the browser phone, to a case file (P1, W2, W5) | Built; P1b independently verified sound (`verify-P1b-r2.md`). A whole call (disclosure, questions, read-backs, close) runs through the real HTTP API and ends in a case file with a tier, a short summary and every quote with its audio offset. Iteration 4: every fixed line is pre-made at server start (`[prewarm]`), a reply's lines play as they are made, the credit-cap check no longer reads the whole ledger on each request, and each turn logs STT status, TTS time, the classifier's record, the browser's end-of-speech marks, talk-over and the phone's own `bot_start_ms`. In headless Chrome with a synthetic microphone (4 packaged calls, 46 turns, TTS audio) `bot_start_ms` had a median of 2,795 ms before and 1,904 ms after the first two changes, and 1,822 ms at the end (a classifier that was partly down, because OpenRouter had run out of credit). Barge-in is not built; the loop is half duplex. No agent has used a real microphone or looked at the page by eye; one builder's two practice calls by microphone (2026-11-10) had a median of 3,441 ms (20 turns, not scored) |
| The call itself, `samajh/dialogue` (P2, W1, W4) | Built; independent verification on typed text, not speech. Latest full verdict (`references/reviews/iter3/verify-call.md`): **ready for consenting testers playing customers, with the classifier on and degraded sessions voided; not ready for anyone else.** The right-party check is a lender setting (P8, `samajh/identity/`): the default is none, which asks "are you <first name> yourself?" and treats a person who says yes twice as the borrower (5 of 5 such false claimants passed); the year of birth is the lender's opt-in. This is a right-party check, not identity verification. **Iteration 4:** the name is judged by a script-neutral phonetic distance over a first-name lexicon, so "Kavitha", Shiva, Surinder, Mahender and Pinky pass and a known different name ends the call (W1, `references/reviews/iter4/verify-W1-names.md`); a classifier that sees the stage, the borrower's first name and the previous exchange decides at the opening, with word lists as hard vetoes; a request for another language switches the call live (Tamil, Kannada, English) or ends it with the language recorded; a half answer to the consent or kind question gets one follow-up; "check your records" is a deferral, asked once more and not a refusal; each slot is asked at most twice (W4, `tests/dialogue/probes/w4/CHECKER-REPORT.md`). Verifiers' wording is in `DESIGN.md` §11. Known limits: the classifier must be on and a session with a degraded turn is void; nicknames (Bala, Raju) still end the call, and a role word with no relation-list entry ("मैं manager बोल रहा हूँ") still passes at the opening; a refusal worded as a question can be read as a deferral with word lists alone (2 of 7); in the year-of-birth setting an explicit claimant still hears the lender named before the year; no fluent reviewer has read the lines (77 per language, six of them new) and nothing has been tested on speech |
| The decision chain (P3a) | Built and independently verified on typed text: `verify-P3a-r3.md` (sound with conditions); `references/reviews/iter3/verify-chain.md` ("sound with conditions, with one regression to fix before use"; after its recheck "holds with conditions") and `verify-chain-r2.md` ("sound with conditions"; after its recheck "the three fixes hold, with conditions"). Two fixes made after that recheck are **not re-verified**. Four tiers: `refer`, `incomplete`, `understanding_gap`, `clear`. A referral shows whether it rests on what the customer said or on the lender's record alone (P3c; its fixes were confirmed by the coordinating worker only). Verifier's wording: "On 23 typed withdrawals that hold a marker word (one-clause, punctuated or carried from recall), none ended `clear`." "On 10 typed corrections away from the record, the taken-back value was never the stated answer." Known limits: a withdrawal is a rule the code applies, not a guarantee; v2.5 returned a single clause on 246 of 246 real clips (`references/pilots/prisma-punctuation-note.md`), so the clause-based rule is largely inert on speech. Three extraction faults found by W3 are open: a term phrase ("जब तक लोन चलेगा") not parsed in 9 of 56 replies, one consent reply read as no usable answer, one flag ranking |
| Loan book, reviewer queue, half-yearly report, evidence (P3b, W6) | Built and independently verified (sound with conditions in five rounds, latest `verify-P3b-r5.md`), over a synthetic 200-loan book with simulated customers: no share it shows says anything about a real lender. **Iteration 4 (W6):** a hash chain over each session, a seal on each case file, decisions chained and bound to the case they were made on, and `uv run python -m samajh.evidence export | verify | check`; the review routes need a bearer token. Verified on 47 kinds of tampering by an independent checker (ten were missed and then fixed; the fix builder reran them). Allowed: "detects a change made after the fact unless the chain heads and seals are rebuilt too"; "a default bundle carries no text of the year-of-birth reply"; "retention is off by default". It is tamper-evident, not tamper-proof: someone who rebuilds every chain, seal, head file and manifest is not detected, so keep a copy of the bundle's `root_sha256` elsewhere. The session, case and recording routes are not behind the token yet; the reviewer sign-in was not exercised in a browser |
| The Gnani amounts finding (P6) and open baselines (W7) | Built and independently verified: every number reproduced and the freeze order confirmed (P6); W7 recomputed with 0 disagreements. Results at the top |
| Evaluation on customers the builders did not script (P5, W3) | **P5**, run on text on 2026-11-13: 60 synthetic Hindi and Hinglish customers whose replies were written by two outside models, the open call against a matched yes/no-style script (`eval/p5/REPORT.md`; recomputed, `verify-P5.md`: "PASS"). At level 0, of 26 customers with a problem none ended `clear` or `understanding_gap` (misled customers 13 of 14 referred and 1 incomplete); the closed script missed none either (both caught 25, closed only 1, open only 0; exact McNemar p = 1.0), so **P5 shows no advantage over a yes/no call**. P5b (24 fresh customers) found the name fault W1 answers; P5 and P5b were not rerun after W1 and W4. **W3** (`eval/acq/REPORT.md`; 160 synthetic customers, one counted run of a plan frozen in advance, recomputed): "On synthetic Hindi and Hinglish text written by two outside models from beliefs alone, at a = 0 the open call referred 80 of 80 problem customers on a gold ground and turned 45 of 48 customers' own 'don't know' into an understanding gap on the right field." Where customers say yes to what they cannot recall, a yes/no call confirms those knowledge gaps (the yes/no side is computed from an assumed recognition bias, not observed). "Under this harness's matched-deference model, the open call can find a false belief the yes/no call confirms only when the customer says it in another field's answer (1 of 80, C126, at a = 0.25 and 0.5); and as built it found fewer, because a customer who leaves it to the lender's records is heard as declining the call." So the claim that the open call resists a customer who just agrees is **retired**. **W7 Part C** (text, replies set by rule): a generic LLM caller stated a record value before the customer did in 39 of a random 40 calls (read by hand); with customers who never agree to what they do not know it found 33 of 48 knowledge gaps against 45 of 48 for Samajh's open call (McNemar p = 0.008), and referred 59 of 80 customers with a false belief (4 more were handed to a human without a report) against 80 of 80. Different models; at a = 0.5 the generic agent found more, because the call then read a deferral as a refusal (changed in W4; not rerun). Not claimed: a pooled rate, real customers, a prevalence, any result on speech, "mis-selling found" |
| Human calls (P4) | The team's own work from 2026-11-15, with the kit W2 built (`samajh/human`: per-turn timings, `score`, `refs`, `wer`, `notes`; the runbook `references/pilots/iter4-human-session-runbook.md`). No counted call yet: 24 brief cards are written, and the two practice calls of 2026-11-10 are the only calls by a person |

What is measured so far, each with what limits it:
- **Prisma v3.0 and amounts that skip a place-value group** (held-out, TTS audio) and **the open-model comparison**: above. Details and the list of what is not claimed: `eval/amounts_v2/REPORT.md`, `eval/openbench/REPORT.md`, `references/reviews/iter2/verify-P6.md`.
- **Prisma on read speech.** On 100 seeded clips (of 417) of the FLEURS `hi_in` test set (NFC, lower-case, punctuation removed, numbers not converted; not a FLEURS test score), WER was: Prisma v2.5 `verbatim` 11.6, v3.0 12.2, Gemini 3 Flash 12.9, IndicWhisper 14.4, Whisper large-v3 28.7. How the text is normalised changes WER by about 8 to 10 points for every system here. Read speech, not calls (`eval/openbench/REPORT.md`).
- **The decision chain on scripted text (not speech).** The frozen scenario set (144 calls written by the team, 36 base cases; Hindi and Hinglish are 72 calls) was rerun after P3a's changes: of 38 Hindi and Hinglish calls with a customer problem, 2 ended `clear` or `understanding_gap` (1 of 19 base cases: a wrong cancellation window, which is `understanding_gap` by design); of 18 informed customers on a compliant record, 0 were referred; of 16 informed customers with a fault on the lender's record, 8 were referred (6 on what the customer said, 2 on the record alone). Gold agrees with the rule engine on 144 of 144 partly because of a coordinator decision on 8 scenarios. Report: `eval/text_path/runs/frozen__openai-gpt-6-luna.md`.
- **Names in the right-party check** (typed text, 256 openings written by the checker before it read the matcher): before the fix 10 of 147 genuine borrowers were rejected by name (6.8 per 100 [3.7-12.1]) and the loan or lender was named to 0 of 103 unambiguous third parties [0.0-3.6]. After the fix round, on the same set (so not a held-out result), 1 of 147 (Bala, ambiguous; 0 of 146 unambiguous) and 0 of 103.
- **The call's new behaviours** (W4's checker, synthetic typed text): "On 30 synthetic typed language requests, the call switched live for 14 of 14 requests for Tamil, Kannada or English, and ended with `language_switch` for 15 of 15 requests for Telugu, Marathi or Bengali." "A negated 'again' in an answer was read as a call-back 0 of 18 times (2 of 18 before)." "After a deferral the call asks once more and moves on (18 of 18)." "A half answer to the consent question now gets one follow-up for the missing half: 14 of 15 typed cases, against 0 of 15 before." "With the classifier on, no customer reply to the birth-year question was sent to any model (0 of 40 classifier requests on 20 year-check calls)": this is at the year question; the classifier's context still holds earlier turns. The case file also withholds that reply and the Batch segments that overlap it in time; the on-disk dialogue state and the audio still hold it.
- **Gnani API behaviour** measured live, including that the one-request limit is per account and not per key (`references/pilots/api-probe-iter1.md`).

Not verified: anything on human speech (the only human audio is two unscored practice calls by one builder); a real microphone, speaker echo, a room, or any browser but headless Chrome; anything in Tamil or Kannada (no fluent reviewer); the bot's wording (no fluent human has read a line, and no listening pass has been done); the end-of-speech thresholds (not set on human audio); streaming speech-to-text beyond TTS clips (off by default); the reviewer sign-in in a browser. Not built: barge-in and real telephony.

## Set up

Needs Python 3.11, [uv](https://docs.astral.sh/uv/) and `ffmpeg` on the path.

```
uv sync
cp .env.example .env     # then fill in GNANI_API_KEY and OPENROUTER_API_KEY
```

`.env` is gitignored. Never commit or print a key.

## Run the phone

Needs the setup above and `GNANI_API_KEY` in `.env` (and OpenRouter credit for the classifier). Every call spends Gnani credits.

```
uv run python -m samajh.server --port 8085 [--state DIR]
```

Then open `http://127.0.0.1:8085/` in Chrome, pick a record and a language (Hindi or Hinglish) and place the call. **At start the server makes every fixed bot line** and every first-name line of the records in the record book, in Hindi, Hinglish, Tamil and Kannada at 8 kHz, before it accepts a call. A line it cannot make, or an estimate over `max_credits` (40) in `samajh/server/settings.toml`, stops the start and names what to run by hand; with no Gnani key it only warns. `uv run python -m samajh.server.prompts check --lang hi --lang hi-en --lang ta --lang kn` lists what is missing and makes no request. The record picker holds four packaged demo records and, when a batch has been drawn (`uv run python -m samajh.ops demo`), a group "Synthetic loan book (drawn loans)" whose loans can be called. `SAMAJH_RECORDS_DIR` names one more directory of records. The page also has a picker for the lender's right-party setting (None, the default, or Year of birth with one or two attempts) and shows the mocked written notice ("SMS, mocked: not sent"). The server runs the Samajh dialogue by default. It binds 127.0.0.1 only; `--allow-host NAME` admits another host name. Streaming speech-to-text is off (`[streaming] enabled = false`). To run a whole call without a microphone, with the server running:

```
uv run python -m samajh.server.replay tests/fixtures/server/calls/hero --url http://127.0.0.1:8085 --out OUT
```

Gnani allows one active request per account. Do not run an evaluation while a call is live: a live turn waits 5 s for the lock, then fails with `gnani_busy`. Session logs, recordings and case files are written under `.samajh/sessions/` (or `--state`).

## Run the review pages

The reviewer queue, case pages, attempt log and half-yearly report read a batch from `<state>/ops`. Build the simulated batch (scripted customers and extraction, no model, no network), add a reviewer, then start the phone server and open `http://127.0.0.1:8085/review/`:

```
uv run python -m samajh.ops demo
uv run python -m samajh.ops ingest                   # bring finished phone sessions into the batch
uv run python -m samajh.ops reviewer add NAME        # prints a token once; the page asks for it
uv run python -m samajh.evidence export --case ID --out DIR   # then: ... verify DIR
```

`uv run python -m samajh.ops --help` lists `book`, `init`, `draw`, `run`, `ingest`, `verify`, `report`, `reviewer` and `retention` (off unless `--days` is given; without `--delete` it only lists). Every page says that the book, the customers and the calls are simulated.

## Human sessions

`uv run python -m samajh.human score | refs | wer | notes` scores a day of human calls (per-turn timings, outcome and tier against a brief card's gold, counts per 100 by kind of customer with Wilson intervals, never pooled), builds a sheet of reference transcripts, computes word and character error rates per reading, and runs WhatsApp voice notes through both Prisma models. Commands, in order: `references/pilots/iter4-human-session-runbook.md`. Everything a person says stays under `.samajh-human/`, which git ignores.

## Play a call in the terminal

The dialogue runs as text, with no audio and no Gnani call. You type the customer's replies:

```
uv run python -m samajh.dialogue play --record tests/dialogue/fixtures/record_gold_loan.json --lang hi
```

`--lang` is `hi`, `hi-en`, `ta` or `kn`; `--help` lists the rest (`--llm` adds the LLM classifier and sends the question and your reply to OpenRouter, so type only synthetic text; `first || second` gives one turn two transcripts). `play` takes `--identity none|year_of_birth`, `--attempts 1|2` and `--no-call-back-line`.

## Run the tests

```
uv run pytest                  # offline tests only (live tests are deselected)
uv run pytest tests/core -q    # or one folder at a time
uv run ruff check samajh tests
```

The whole offline suite at commit 1282a1c: 8,874 passed, 3 deselected (live). Most tests are parametrized cases, many of them typed phrases patched in fix rounds, so the count measures phrases, not behaviour. `uv run pytest -m live` makes real Gnani and OpenRouter calls and costs credits; the client refuses to go past `GNANI_CREDIT_CAP` (1000 in `.env.example`). Never run `tests/clients/probes/gnani_probe.py`: it bypasses the lock.

## Documents

| File | What it is |
|---|---|
| `DESIGN.md` | The current design (v3): problem, rule, call flow, rules and tiers, evaluation, what we can and can't claim |
| `references/reviews/` | Independent verification reports: iteration 2 (P1b, P2 rounds 2 to 4, P3a, P3b and P6), iteration 3 (`verify-call.md` and `verify-call-r2.md` for the call and the right-party setting, `verify-chain.md` and `verify-chain-r2.md` for the decision chain, `verify-P5.md` for P5) and iteration 4 (`verify-W1-names.md`) |
| `references/claims/` | Claims ledger and the quote checker (saved sources are local-only) |
| `references/pilots/` | Package reports (P1 to P3 and P8; `P8-report.md` is the right-party setting as built; `iter4-W1` to `W7` reports for iteration 4), the Gnani API probe, the transport report, the number-formatting report for Gnani, the human-session runbook, rendered reviewer pages (`p3b-artifacts/`) |
| `eval/amounts_v2/`, `eval/amounts/` | The held-out and the development spoken-amounts evaluations (TTS audio; real voices for the held-out one) |
| `eval/openbench/`, `data/openbench/` | Open baselines (W7): the amounts finding and Prisma against open speech models, Prisma on FLEURS, and a generic LLM-agent baseline; `REPRODUCE.md` |
| `eval/acq/`, `data/acq/` | W3: 160 synthetic customers, the open call against a yes/no call with recognition bias and acquiescence as parameters; `REPORT.md` |
| `eval/p5/`, `data/p5/`, `data/p5b/` | P5: synthetic customers the builders did not script, run on text; `REPORT.md` and the run data |
| `eval/text_path/` | The text-path evaluation of the extractor and the decision chain. Scripted text only, no speech |
| `data/scenarios/`, `data/names/`, `data/loanbook/` | The frozen scenario set (for final measurement only), the first-name lexicon for the right-party check, the synthetic 200-loan book |
| `references/real-voice-datasets.md` | Licensed real-voice Indic datasets for evaluation |
