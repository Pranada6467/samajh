# Samajh

Samajh is a post-sale understanding callback for Indian lenders: a teach-back-style comprehension check. The customer explains in their own words, in their own language, what they bought with their loan, and plain code compares that against the bank's records; every mismatch becomes a flag a human can act on.

It is built for Gnani AI's Great Indian AI Internship Challenge on Prisma STT and Timbre TTS, and targets the post-sale feedback duty in RBI para 85Y (commercial banks) and 101Y (NBFCs), in force from 1 January 2027. All data is synthetic.

## Status (iteration 1, 2026-11-10)

Done:
- The Gnani client (STT, TTS, Batch) and the OpenRouter LLM client in `samajh/clients/`, proven against the live APIs. They share a cross-process lock, a cache, a ledger and a credit cap.
- Claims verified: regulatory and case claims were checked against saved primary sources (`references/claims/`), and Gnani API behaviour was measured live (`references/pilots/api-probe-iter1.md`).
- The core: types, the amount normaliser and the rule engine (`samajh/types.py`, `samajh/amounts/`, `samajh/rules/`). W1b took it over after a usage-limit stall. 1,223 core tests pass (after the amounts parser fix) and ruff is clean. One independent review was done; the fixes made after it have not had a second one. Known gaps are in `references/pilots/W1-core-report.md` §7.
- W7, voice transport (`samajh/server/`, `web/`, `tests/server/`): a FastAPI backend that owns the Gnani key and a browser phone. A full stub call (three fixed Hindi questions, each echoing what was heard) runs end to end through the HTTP API and in a headless Chrome with a WAV file as the microphone. Turn-taking was measured: REST per turn with a 700 ms end-of-speech detector in the browser is the shipped path, and Prisma WebSocket streaming was not faster at the same silence threshold, so it is not built in. 183 offline tests and 1 live test pass; the reviewer's 11 findings are fixed and not re-reviewed. **TTS clips only, no human speech, and no human has used the phone yet** (real microphone, echo, noisy rooms, Safari and mobile browsers are untested). Report: `references/pilots/voice-loop-iter1.md`.
- W8, the audio evaluation harness and the first evaluation (`samajh/audio/`, `samajh/evalkit/`, `eval/amounts/`, `data/amounts/`): done. Headline: on 240 Timbre-voiced sentences over simulated phone audio, our amount parser read the rupee amount right on 221 (Prisma v3.0, 92%) and 214 (Prisma v2.5, 89%) of them, most v3.0 failures were confident wrong amounts, and v2.5 and v3.0 agreeing was right 199 times in 200. **This is TTS audio only: no human speech was used, so it says nothing about real callers.** Report: `eval/amounts/REPORT.md`. The reviewer's fixes have not had a second review. The parser was fixed afterwards against the same 240 sentences and rescored offline (v3.0 phone 221 to 222, v2.5 phone 214 to 224; TTS audio, n = 240): **those after-fix numbers are tuned on this set, not a held-out result**. The report's tables describe the parser before the fix.
- W4, scenarios (`samajh/scenarios/`, `data/scenarios/`, `tests/scenarios/`): 144 synthetic scenarios (36 hand-written base cases in Hindi, Hinglish, Tamil and Kannada) with hand-written gold, each with a scripted teach-back call and a scripted yes/no call. Frozen at version 3 (`gold.jsonl` sha256 beginning `14e49b58`); 50 tests. The rule engine agrees with gold on 144 of 144 scenarios, on perfect beliefs and on the scripted-extraction path. **That agreement was reached partly by a coordinator decision** that resolved the one disagreement (a customer who says they do not know the premium; 8 scenarios) in the engine's favour, made before any audio or LLM extraction was run on the set. It is not independent confirmation of the engine on those 8. One independent model review agreed with 35 of 36 base cases at version 1; no reviewer has seen versions 2 or 3, no human has reviewed any of it, and Tamil and Kannada have no fluent reviewer. Speech is templated. **The frozen set is for final measurement only: never use it to tune prompts, parsers or rules.** Report: `data/scenarios/W4-report.md`; datasheet: `data/scenarios/README.md`.

In progress (nothing in this list is finished). The original W5 and W9 workers stopped on the usage limit; replacements are running:
- W5b, the LLM extractor, with a text-path evaluation (replaces W5).
- W9b, dialogue: the call state machine and the prompt scripts in four languages (`samajh/dialogue/`, `data/prompts/`) (replaces W9).

Not built yet: the half-yearly view. The core builds evidence packs as data (`EvidencePack`), but no view of them exists yet.

No end-to-end evaluation of Samajh itself exists yet: the stub call is a transport test with fixed questions, not the Samajh dialogue. The amounts evaluation above is the only evaluation run so far; the scenario set is built and frozen, but the extractor and call-flow evaluations (E1, E2) have not been run on it. No human voice recordings exist, so there are no results on human speech.

## Set up

Needs Python 3.11 and [uv](https://docs.astral.sh/uv/).

```
uv sync
cp .env.example .env     # then fill in GNANI_API_KEY and OPENROUTER_API_KEY
```

`.env` is gitignored. Never commit or print a key.

## Run the phone

Needs the setup above, `ffmpeg` on the path, and `GNANI_API_KEY` in `.env`.

```
uv run python -m samajh.server --port 8085
```

Then open `http://127.0.0.1:8085/` in Chrome. The call is the stub dialogue (three fixed Hindi questions). The server binds 127.0.0.1 only; `--allow-host NAME` admits another host name, for a phone on the LAN. To run a whole call without a microphone, with the server running:

```
uv run python -m samajh.server.replay tests/fixtures/server/stub-call --url http://127.0.0.1:8085
```

Gnani allows one active request per key. Do not run an evaluation while a call is live: a live turn waits 5 s for the key, then fails with `gnani_busy` (3 of 12 phone turns did, TTS clips only, while the amounts evaluation ran). The session log is written under `.samajh/sessions/`.

## Run the tests

```
uv run pytest            # offline tests only
uv run pytest -m live    # real Gnani and OpenRouter calls; costs credits
uv run ruff check samajh tests
```

The live tests spend Gnani credits; the client refuses to go past `GNANI_CREDIT_CAP` (1000 in `.env.example`). To see what the client has spent: `uv run python -m samajh.clients.gnani ledger`. Gnani allows one active request per key, so run only one thing that calls it at a time, and never run `tests/clients/probes/gnani_probe.py` (it bypasses the lock).

## Documents

| File | What it is |
|---|---|
| `DESIGN.md` | The current design (v2): problem, rule, call flow, rules, evaluation, what we can and can't claim |
| `ORCHESTRATION.md` | Build rules and the iteration log |
| `CLAUDE.md` | Project instructions for coding agents, including the verified Gnani API facts |
| `RESEARCH.md` | Research on the challenge, Gnani products, the market and all idea directions |
| `IDEAS-HILLCLIMB.md` | The 5-round evaluation that chose this idea |
| `references/claims/` | Claims ledger, design corrections and the quote checker (saved sources are local-only) |
| `references/pilots/` | Measured pilots: amounts, the Gnani API probe, the client report, the W7 voice loop (`voice-loop-iter1.md`) |
| `data/scenarios/` | The frozen scenario set (`gold.jsonl`, `calls.jsonl`, `FROZEN.json`), its datasheet (`README.md`), `CHANGELOG.md` and the W4 report (`W4-report.md`). Synthetic; for final measurement only |
| `eval/amounts/REPORT.md` | The spoken-amounts and phone-line evaluation: 240 TTS sentences, Prisma v2.5 and v3.0 (TTS audio only) |
| `references/real-voice-datasets.md` | Licensed real-voice Indic datasets for evaluation |
