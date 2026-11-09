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

## Gnani API facts (verify against docs.gnani.ai before relying on them)
- Base URL `https://api.vachana.ai`; auth header `X-API-Key-ID` → browsers can't set it on WebSockets, so use a backend proxy.
- **Prisma STT:** v2.5 (set language; number formatting hi/en only; `bias_list` ≤100 letter-only words; ≤10 substitutions) and v3.0 (`indic-auto` language ID, `codemix`, `keyterms` ≤200, topic hints). REST clips ≤30 s; WebSocket streaming; Batch (segment timestamps, speaker labels, denoising, long files).
- **Timbre TTS:** v2.5/v3.0, REST/SSE/WebSocket, number/date/ID normalisation, audio tags (v3.0). **Voice cloning:** embeddings + REST/SSE/WebSocket.
- No confidence scores or word timestamps on REST/streaming — derive confidence from validation and read-back.
- Expect 429 `RATE_LIMITED`; treat concurrency as 1: single-flight queue, exponential backoff, cache every response.
- 5,000 credits; per-call cost undocumented — measure burn with a few calls before generating test sets.
- Unsupported languages: Odia, Assamese, Bhojpuri.
- The challenge page names v2.5 models; v3.0 is newer. Build so either works, and report results for both.

## How to work in this repo
- Prefer the converged design pattern: capture speech → LLM extracts into a strict schema → **deterministic** validation against the official rule/form (no LLM arithmetic) → TTS read-back of critical fields → evidence log → evaluation on a synthetic, rule-derived test set.
- Every accuracy claim needs a metric and a gold standard. Report failure cases honestly; include self-recorded audio, not only TTS audio.
- Ground regulatory claims in primary sources and cite them; flag anything unverified.
- Avoid saturated themes unless there's a clear, evidenced twist: kirana billing, govt-scheme helpers, generic ASHA intake, scam-call shields, farmer helplines, tutors, interview coaches.
- The spoken-numbers/FASTag direction was explored and dropped (weak demand evidence) — don't revive it without new evidence.
- The women's-safety distress agent ("Pukaar") was explored and dropped (evidence/product mismatch, bot-to-112 risk, concurrency limit, weak Gnani-market fit; `RESEARCH.md` §10b) — don't revive it without new evidence.
- For real-voice STT evaluation, use public consent-based datasets per `references/real-voice-datasets.md` — evaluation only, never in the demo or repo.

## Files
- `DESIGN.md` — **current design (v1): Samajh, the RBI 85Y post-sale understanding callback.**
- `IDEAS-HILLCLIMB.md` — 5-round idea evaluation (scores, verdicts, allowed/banned claims).
- `references/pilots/` — measured pilots (spoken-amounts pilot, credit cost).
- `RESEARCH.md` — full research: challenge, Gnani products, market, competitive field, past winners, all idea directions, evaluation.
- `references/challenge-entries-github.json` — catalogued public GitHub entries from other participants.
- `references/pvpi-adr-form-v1.3.pdf` — PvPI suspected adverse drug reaction reporting form.
- `references/real-voice-datasets.md` — licensed real-voice Indic eval datasets and the challenge's data-rule wording (reusable).
- `references/helpline-evidence.md` + `references/helpline-sources/` — verified 112/181/CAG facts (from the dropped Pukaar idea).
- `references/dropped/` — designs of dropped ideas, for reference only.
