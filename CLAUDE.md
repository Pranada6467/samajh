# CLAUDE.md

## What this project is
Preparation and build workspace for Gnani AI's **Great Indian AI Internship Challenge** — a student challenge to build a working application on Gnani AI's Indian-language voice models/APIs. Full research lives in `RESEARCH.md`; read it before proposing ideas or architecture.

## The goal
- Build a **genuinely working, measured** voice application on at least one Gnani model or API.
- The user prioritises **build quality** over social engagement, and wants to **learn** while building.
- Target one or two specific award categories (see `RESEARCH.md` §1); a team can win only one award.
- Show understanding of the real Indian voice-AI market (Gnani sells mostly to BFSI, lenders, telecom, insurance, contact centres) — this matters for the interview stage.

## Submission requirements (for reference)
- Working app shown in a public demo video (a strong 60-second cut is valuable).
- Video posted on LinkedIn and/or X tagging Gnani AI with `#GnaniAI` and `#GreatIndianAIInternshipChallenge`.
- Written explanation: title, problem, target users, Gnani models/APIs used (name exact versions), each member's contribution.

## Hard constraints
- **Synthetic data only.** Never use real phone numbers, account numbers, Aadhaar, PAN, or recordings of real calls/people. Generated IDs must obey formats but be obviously fake. Self-recorded clips from consenting teammates are fine.
- **Agent Builder is out of scope.** Use the Speech APIs (STT, TTS, voice cloning) directly.
- Evon LLM is not on the API — use any LLM for reasoning, or self-host Evon.

## Gnani API facts (verified live on 2026-11-10; evidence in `references/pilots/api-probe-iter1.md`)
Where docs.gnani.ai and live behaviour differ, live wins. `[docs]` marks what was read in the docs and not exercised: re-verify it before relying on it.
- Base URL `https://api.vachana.ai`; auth header `X-API-Key-ID` (one key serves STT, TTS and Batch) → browsers can't set it on WebSockets, so use a backend proxy.
- **Prisma STT REST:** `POST /stt/v3` serves both models; the `model` field picks `prisma-v2.5` (the default if omitted) or `prisma-v3.0`. `language_code` is required. Always send `format`: the server's default changes with model and language. Clips ≤30 s inclusive on both models (31 s gives 400 `MAX_AUDIO_DURATION_EXCEEDED`).
- **v2.5:** `format` is `verbatim` or `transcribe`; no `indic-auto`. `format=transcribe` writes numbers as digits for Tamil and Kannada as well as Hindi and English (the docs say Hindi/English only), and the reply's `output.literal` holds the wording before formatting. `output.literal` equals the verbatim wording of the same clip, ignoring punctuation and spaces: 112 of 112 phone-line clips (eval/amounts/REPORT.md, TTS audio). v2.5 answered 504 on 15 of 1,184 calls (1.3%; 14 of the 15 Tamil or Kannada), each succeeding on a second attempt after a wait of about 30 s, inferred from the ledger times with the `Retry-After` header not read; v3.0 did so once in 1,456 calls (eval/amounts/REPORT.md, TTS audio). `bias_list` ≤100 letter-only words `[docs]` is accepted, effect not measured; the substitution map (≤10 `[docs]`) is accepted, effect not shown.
- **v3.0:** `indic-auto` and comma-separated language lists work on REST only (the streaming endpoint rejects the list; see the next bullet). `format` is `verbatim`, `transcribe`, `transliterate` or `codemix` (`codemix` is a `format` value, not a separate option, and v2.5 rejects it). `keyterms` (≤200 `[docs]`) changed the output; `topic` takes free text. `format=transcribe` mis-formats amounts that skip a group ("three lakh two hundred" comes back as 3,02,000, "छह हज़ार पच्चीस" as 6,250): on phone audio the parser read 6 of 16 such amounts against 161 of 164 other non-fraction amounts, and v2.5 read 15 of the 16 (eval/amounts/REPORT.md, TTS audio). These are confident wrong amounts with the words gone, so only a read-back or a second reading catches them.
- **Streaming and Batch:** WebSocket streaming (`/stt/v3/stream`) was measured against REST per turn and is not built into the server; the decision and numbers are in `references/pilots/voice-loop-iter1.md` §1 and §3. On 20 TTS clips (TTS clips only, no human speech) streaming at the server's default 500 ms silence returned the transcript a median 0.78 s after the end of speech, against about 0.71 s for a browser detector at 500 ms plus a REST call (n = 20 each); the default cut all 4 clips with a 600 or 900 ms pause into two segments, and streaming billing is unknown. **Streaming rejects a comma-separated `language_code` on v3.0** (`hi-IN,en-IN` gives "exactly one locale is required", then close 1008; 13 of 13 attempts), contrary to the docs, which say 1 to 4 codes; REST accepts the list. Prisma Batch works end to end (create, start, poll, fetch the transcript from a pre-signed URL) and returns segment start/end times and speaker ids. Segments follow pauses and speaker changes, not sentences: two similar voices joined with no pause came back as one segment (n = 2 TTS clips; nothing yet on real phone audio). Denoising and long-file limits are `[docs]`.
- **Timbre TTS:** `POST /api/v1/tts/inference` works on v2.5 and v3.0 (13 voices on v3.0, 73 on v2.5; no list-voices endpoint). The server doesn't validate `language`. Every WAV has streaming-style size fields that break Python's `wave`; the client repairs them. SSE, WebSocket, number/date/ID normalisation and audio tags (v3.0) are `[docs]`. **Voice cloning** (embeddings + REST/SSE/WebSocket) is `[docs]`.
- No confidence scores (Batch segments carry `confidence: null`) and no word timestamps (Batch gives segment times; REST gives none) — derive confidence from validation and read-back.
- **Concurrency is 1.** A second simultaneous REST request gets an instant 429 `RATE_LIMITED` (0.2 to 0.3 s) with no `Retry-After`: it is rejected, not queued, and STT and TTS share the slot. A WebSocket streaming session does not occupy the slot. Batch routes have a separate 429 for calls less than about 1 s apart. Not established: whether a running Batch job holds the slot. Use the single-flight lock, exponential backoff, and a cache of every response.
- **Credits:** 5,000 on the account; the project caps itself at 1,000. No API surface reports cost (no header, no body field, no usage endpoint); the dashboard at app.gnani.ai is the only source. The client's guard runs on estimates: 0.010 credits per STT audio second and 0.002 per TTS character (`samajh/clients/defaults.toml`), rounded up from one pilot dashboard reading (about 0.0087 and 0.0018, read off a chart, so each could be 20% off or more). Batch is assumed to bill like STT; streaming billing is unknown.
- Unsupported languages `[docs]`: Odia, Assamese, Bhojpuri. Live, v3.0 rejects Assamese (400 `MODEL_UNSUPPORTED_LANGUAGE`), matching the docs; the others were not exercised.
- The challenge page names v2.5 models; v3.0 is newer. Build so either works, and report results for both.

## How to work in this repo
- Prefer the converged design pattern: capture speech → LLM extracts into a strict schema → **deterministic** validation against the official rule/form (no LLM arithmetic) → TTS read-back of critical fields → evidence log → evaluation on a synthetic, rule-derived test set.
- Every accuracy claim needs a metric and a gold standard. Report failure cases honestly; include self-recorded audio, not only TTS audio.
- Ground regulatory claims in primary sources and cite them; flag anything unverified.
- Regulatory and case claims must match `references/claims/claims-ledger.md` (its allowed and banned wording).
- Update documentation as soon as a verified result makes it stale.
- `data/amounts/amounts-v1.jsonl` is now a development set for the amount parser. Scores on it after the parser fixes are in-sample, so a headline amount number needs a fresh frozen set (new seed). All its audio is TTS: no amount figure is a claim about real callers.
- Do not claim "nobody has built this" or "no vendor offers this": adjacent vendors exist (SquadStack, Edesy, Ringg, NuSummit). Say what Samajh adds: an open question before any product is named, a deterministic comparison with the lender's record, an evidence log, a measured evaluation.
- A flag produces an evidence pack for human review, never a "refund case" and never a mis-selling finding: the 85Z refund duty arises only where mis-selling is established, and a flag is not that.
- Avoid saturated themes unless there's a clear, evidenced twist: kirana billing, govt-scheme helpers, generic ASHA intake, scam-call shields, farmer helplines, tutors, interview coaches.
- The spoken-numbers/FASTag direction was explored and dropped (weak demand evidence) — don't revive it without new evidence.
- The women's-safety distress agent ("Pukaar") was explored and dropped (evidence/product mismatch, bot-to-112 risk, concurrency limit, weak Gnani-market fit; `RESEARCH.md` §10b) — don't revive it without new evidence.
- For real-voice STT evaluation, use public consent-based datasets per `references/real-voice-datasets.md` — evaluation only, never in the demo or repo.

## Files
- `DESIGN.md` — **current design (v2): Samajh, the RBI 85Y post-sale understanding callback.** v2 applies the claims check.
- `ORCHESTRATION.md` — build rules and iteration log; every worker reads it.
- `IDEAS-HILLCLIMB.md` — 5-round idea evaluation (scores, verdicts, allowed/banned claims); a note at its top lists what `references/claims/` supersedes.
- `DESIGN-kasauti.md` — Kasauti, an earlier explored proposal (a compliance test suite that red-teams Indian collections voice agents against RBI recovery-call conduct); unreviewed, not the current design.
- `references/claims/` — claims ledger (`claims-ledger.md`), design corrections (`design-corrections.md`), quote checker (`check_quotes.py`). The saved sources (`references/claims/sources/`) are local-only and gitignored.
- `references/pilots/` — measured pilots (spoken-amounts pilot, credit cost). `api-probe-iter1.md` there is the measured live Gnani API behaviour; `W2-clients-report.md` has the client signatures and caveats. `voice-loop-iter1.md` is the W7 voice transport report: the HTTP API, the REST-versus-streaming turn-taking measurements (TTS clips only, no human speech) and the review findings.
- `samajh/` — the package. `clients/` and the core (types, amount normaliser, rules) are done; the core's public surface and the contracts for scenarios and the extractor are in `references/pilots/W1-core-report.md` §3. Voice transport is done (`server/`, with the browser phone in `web/`); scenarios, the extractor and dialogue are in progress; the audio evaluation harness is done (`audio/`, `evalkit/`). **All Gnani calls go through `samajh/clients/gnani`** (cross-process lock, cache, ledger, credit cap) **and all LLM calls through `samajh/clients/llm.py`** (OpenRouter). Never run `tests/clients/probes/gnani_probe.py`: it bypasses the lock.
- `samajh/server/` — the voice transport: a FastAPI backend that owns the Gnani key, runs a call through a `Dialogue` (`dialogue.py`, with a three-question `StubDialogue`), logs sessions and assembles the call recording (`sessionlog.py`), and checks and resamples uploads with ffmpeg (`audio.py`). `replay.py` runs a whole call headless through the same HTTP routes. REST STT per turn, 700 ms end-of-speech detector in the browser. The dialogue worker plugs in with `create_app(dialogues={"samajh": factory})`; the contract is in `references/pilots/voice-loop-iter1.md` §2.
- `web/` — the browser phone (`index.html`, `phone.js` state machine, `vad.js` end-of-speech detector, `capture-worklet.js`, `wav.js`, `api.js`). The server serves it at `/`.
- `tests/server/` — 183 offline tests and 1 live test, plus `vad_check.mjs`, `browser_check.mjs` (headless Chrome with a WAV as the microphone) and `probes/turn_taking_probe.py`. Run `uv run pytest tests/server -q`.
- **Run the phone locally:** `uv run python -m samajh.server --port 8085`, then open `http://127.0.0.1:8085/` (needs `GNANI_API_KEY` in `.env`; `--allow-host NAME` admits another host name, for a phone on the LAN). Headless whole call from prepared audio, with the server running: `uv run python -m samajh.server.replay tests/fixtures/server/stub-call --url http://127.0.0.1:8085`. Do not run an evaluation while a call is live: a live turn waits 5 s for the one-slot key lock and then fails with `gnani_busy` (3 of 12 phone turns did while the amounts evaluation ran). No human has used the phone yet.
- `samajh/audio/` — phone-line audio transforms (resample, mu-law, band-limit, added noise) and a content-addressed audio store. Needs ffmpeg.
- `samajh/evalkit/` — the evaluation harness: frozen manifests, experiment plans, a resumable voicing and STT runner with a budget, scorers (naive and parser), Wilson and McNemar statistics, and the seeded amounts test-set generator (`amounts/grammar.py`). Run it with `uv run python -m samajh.evalkit`.
- `data/amounts/` — the frozen 240-sentence spoken-amounts set (`amounts-v1.jsonl`, sha256 `62b0dd71…5e0d76`; hi, hi-en, ta, kn, 60 each). Text only; Tamil and Kannada not human-reviewed. Audio is kept outside the repo, under `.samajh/evalkit/amounts-v1/`.
- `eval/amounts/` — the amounts and phone-line evaluation: `REPORT.md` (the evidence; TTS audio only), `FAILURES.md`, the experiment file, and the labelling and analysis scripts.
- `RESEARCH.md` — full research: challenge, Gnani products, market, competitive field, past winners, all idea directions, evaluation.
- `references/challenge-entries-github.json` — catalogued public GitHub entries from other participants.
- `references/pvpi-adr-form-v1.3.pdf` — PvPI suspected adverse drug reaction reporting form.
- `references/real-voice-datasets.md` — licensed real-voice Indic eval datasets and the challenge's data-rule wording (reusable).
- `references/helpline-evidence.md` + `references/helpline-sources/` — verified 112/181/CAG facts (from the dropped Pukaar idea).
- `references/dropped/` — designs of dropped ideas, for reference only.
