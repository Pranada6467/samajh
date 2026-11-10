# Samajh

Samajh is a post-sale understanding callback for Indian lenders: a teach-back-style comprehension check. The customer explains in their own words, in their own language, what they bought with their loan, and plain code compares that against the bank's records; every mismatch becomes a flag a human can act on.

It is built for Gnani AI's Great Indian AI Internship Challenge on Prisma STT and Timbre TTS, and targets the post-sale feedback duty in RBI para 85Y (commercial banks) and 101Y (NBFCs), in force from 1 January 2027. All data is synthetic.

## Status (iteration 1, 2026-11-10)

Done:
- The Gnani client (STT, TTS, Batch) and the OpenRouter LLM client in `samajh/clients/`, proven against the live APIs. They share a cross-process lock, a cache, a ledger and a credit cap.
- Claims verified: regulatory and case claims were checked against saved primary sources (`references/claims/`), and Gnani API behaviour was measured live (`references/pilots/api-probe-iter1.md`).

In progress (nothing in this list is finished):
- Core types, the amount normaliser and the rule engine (`samajh/types.py`, `samajh/amounts/`, `samajh/rules/`). A replacement worker (W1b) took this over after a usage-limit stall.
- W7, voice transport: the FastAPI proxy, the browser phone, and turn-taking measured with REST against streaming (`samajh/server/`, `web/`). Started early, independent of the core.
- W8, audio eval harness: phone-line transforms, a resumable voicing and STT runner, and an amounts test set at scale (`samajh/audio/`, `samajh/evalkit/`, `eval/amounts/`). Started early, independent of the core.

Not started (waiting on the core):
- The 96 test scenarios and their frozen gold set.
- The LLM extractor.

Not built yet: the call flow (the scripted conversation and read-back) and the evidence pack and half-yearly view.

No end-to-end run exists yet. No evaluation has been run, so there are no accuracy results. No human voice recordings exist.

## Set up

Needs Python 3.11 and [uv](https://docs.astral.sh/uv/).

```
uv sync
cp .env.example .env     # then fill in GNANI_API_KEY and OPENROUTER_API_KEY
```

`.env` is gitignored. Never commit or print a key.

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
| `references/pilots/` | Measured pilots: amounts, the Gnani API probe, the client report |
| `references/real-voice-datasets.md` | Licensed real-voice Indic datasets for evaluation |
