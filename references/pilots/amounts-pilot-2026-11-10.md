# Spoken-amounts pilot — 2026-11-10

**Question:** does Prisma write Indian spoken amounts (lakh/crore, fractions, Tamil/Kannada) as the right number?

**Setup:** 20 sentences (8 Hindi, 4 Hinglish, 4 Tamil, 4 Kannada), each containing one amount spoken as words. Voiced once with Timbre v3.0 (voice Shivani, 16 kHz). The phone-line condition is 8 kHz G.711 μ-law (ffmpeg). Prisma REST with the language set (Hinglish → `hi-IN`). Scripts: `pilot.py`, `score.py`; raw transcripts: `results.json`. 20 TTS + 80 STT calls, run one at a time; 0 × 429, 2 × 504 (v2.5 Kannada). Median latency: TTS 0.8 s, STT 0.3 s.

## Results (exact match on the rupee amount)

| Config | Audio | Transcripts with digits | Naive digit read ✓ | Fraction-aware parser ✓ |
|---|---|---|---|---|
| v2.5 `format=transcribe` | phone 8 kHz | 16/20 (2 words-only, 2 timeouts) | 11/16 | **16/16** |
| v3.0 `format=transcribe` | clean 16 kHz | 20/20 | 18/20 | **20/20** |
| v3.0 `format=transcribe` | phone 8 kHz | 19/20 | 17/19 | 18/19 |
| v3.0 `indic-auto` (default verbatim) | phone 8 kHz | 0/20 — numbers stay as words | — | words correct in 19/20 (manual check) |

## Findings

1. **Inverse text normalisation (ITN) leaves the fraction word and converts only the base number**, so the digit string is numerically wrong: `सवा 2,00,000` (gold 2,25,000), `साढ़े 3,000` (3,500), `पौने 2,00,000` (1,75,000), `ஒன்றரை ₹1,00,000` (1,50,000), `இரண்டரை ₹1,00,00,000` (2.5 crore read as 1 crore). This happens on both models, on clean and phone audio; v2.5 does it more often (5 cases vs 2 on v3.0). Any pipeline that reads the digits gets these amounts wrong.
2. **A 30-line fraction-aware parser fixes every ITN case** (`score.py`): apply sawa/saadhe/paune/dedh/dhai and the Tamil/Kannada 1.5/2.5 words to the number's unit.
3. **One genuine recognition miss:** on the phone line, v3.0 dropped "पौने" entirely ("उन्होंने 2,00,000", and "दो लाख" in `indic-auto`); v2.5 kept it. No parser can recover this; only a read-back ("Paune do lakh, yaani ek lakh pachhattar hazaar — sahi hai?") catches it.
4. **The docs understate v2.5:** `format=transcribe` produced digits in Tamil and Kannada too (docs say Hindi/English only).
5. **v3.0 `indic-auto` keeps numbers as words** (including Hinglish English numbers written in Devanagari, e.g. "ट्वेंटी फ़ाइव थाउज़ेंड"), so it needs a full word-to-number parser for each language.

## Caveats
TTS audio only (one voice); clean TTS flatters STT. n = 20, one run. No self-recorded speech yet. Credit cost not measured: responses carry no credit headers. Read the balance at app.gnani.ai to get the cost of these 100 calls.

## What this means for the 85Y build
Amounts are the riskiest field, and the failure is systematic and fixable: use `format=transcribe` + the fraction-aware parser + a spoken read-back of every critical amount. Report naive vs fixed accuracy for v2.5 and v3.0, on TTS and on self-recorded audio.

## Credit cost (dashboard, 2026-11-10)
2.96 credits (₹2.96) for 98 billed requests (78 STT + 20 TTS; the two 504s were not billed) = ~₹0.03 per request. The chart split is roughly STT ≈ 1.7 and TTS ≈ 1.2, so about 0.02 credits per STT call (~3 s clips) and about 0.06 per TTS call. At these rates the full 3-week plan (~1,010 TTS + ~5,560 STT) costs about 180 credits, roughly 4% of the 5,000. Credits are not a constraint.
