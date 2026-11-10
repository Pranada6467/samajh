# Spoken rupee amounts: Timbre voice, phone line, Prisma, parser (E3 and E5)

Run date 2026-11-10. Work package W8. Every number below comes from `eval/amounts/run/stt.jsonl` through `eval/amounts/analyze.py`; the tables between `BEGIN`/`END` markers are generated, not typed.

**Read this first: every clip is a Timbre TTS voice. No human speech was used. Clean TTS flatters a recogniser, so these numbers are an upper bound on what a real caller would get, and the Tamil and Kannada sentences are `not human-reviewed`.**

## Summary

All figures are exact match on the rupee amount, on TTS audio, with Wilson 95% intervals in brackets. The denominators are sentences.

1. **On phone audio with `format=transcribe`, the parser reads 221 of 240 amounts on Prisma v3.0 (92%, 88-95) and 214 of 240 on v2.5 (89%, 85-92).** Reading Prisma's digits naively gets 220 (92%, 87-95) on v3.0 and 156 (65%, 59-71) on v2.5. On no clip in these cells was the naive reading right and the parser wrong. On v2.5 the parser recovers 58 sentences on phone audio, 43 of them fractions.
2. **The two models fail in different ways, and that matters more than the 7-sentence gap between them** (22 sentences right only on v3.0, 15 only on v2.5, McNemar p = 0.32: no difference established).
   - v2.5 mostly gives **no answer**: 20 of its 26 phone failures. 22 of the 26 are on the parser's side: Prisma wrote the amount in a readable but partly formatted shape that the parser does not compose yet. With those fixed v2.5 would read 236 of 240. That is a ceiling from my labels, not a measurement.
   - v3.0 mostly gives **a wrong amount**: 17 of its 19 phone failures. Its `transcribe` formatting writes wrong digits and the words are gone. 8 of the 19 are proven formatting errors (v3.0's own `verbatim` output of the same sentence has the right words), 9 more have the same shape but no word output to prove it. The parser can fix one of the 19.
3. **New finding: v3.0 `transcribe` mis-formats amounts that skip a group** ("three lakh two hundred" becomes 3,02,000; "छह हज़ार पच्चीस" becomes 6,250). On phone audio it reads 6 of 16 such amounts (38%, 18-61) against 161 of 164 other non-fraction amounts (98%, 95-99). v2.5 reads 15 of the same 16. Some Tamil and Kannada fractions go the same way (half a lakh written 5,00,000). These are confident wrong amounts that only a read-back, or a second reading, can catch.
4. **Two readings that agree are almost always right.** On phone audio the v2.5 and v3.0 readings gave the same amount for 200 of 240 sentences and 199 of those were right (the one miss is a sentence whose written form is suspect). In the 40 cases where they differed or one gave no answer, at least one was right 37 times. Prisma returns no confidence score; agreement between two readings is a measured stand-in, at this n and on TTS audio only.
5. **Asking v3.0 for words and parsing them is at least as good as asking it for digits**: `codemix` 123 of 128 (96%) and `verbatim` 122 of 128 (95%) against `transcribe` 119 of 128 (93%) on the same sentences. The difference is not established (7 against 3 discordant sentences, p = 0.34). The kind of failure is what changes: 4 of the 5 `codemix` failures are parser gaps, which are fixable, where the `transcribe` failures are not.
6. **E5: the phone channel costs nothing measurable here, and only babble at 5 dB does.** mu-law at 8 kHz against clean 16 kHz: 214 against 216 on v2.5, 221 against 221 on v3.0. The band-limit, street noise at 10 and 5 dB and babble at 10 dB each stay within 4 sentences of phone audio on the same sentences. Under babble at 5 dB v3.0 falls from 102 to 93 of 112 (12 sentences lost, 3 gained, p = 0.035 before any correction for the ten comparisons in that table) and v2.5 from 102 to 97 (p = 0.27).
7. **Kannada is the weakest language on v2.5** (48 of 60 on phone audio), mostly because v2.5 spells Kannada numbers in ways the parser's word table lacks (ಅರುವತ್ತು, ನಾನ್ನೂರು, tens written with a virama). Section 4 lists each one.
8. Section 4 lists 14 parser gaps and 12 partly formatted shapes. Three of them make the parser return a **wrong amount** and should be fixed first.

What this does not show: anything about human callers. See section 5.

### What this changes for the build

- **Keep the read-back on every critical amount.** On v3.0, the design's model, 17 of 19 phone failures are a wrong amount held with no warning, and the parser cannot see them.
- **Take two readings and compare them.** Prisma gives no confidence score. v2.5 and v3.0 agreeing was right 199 times in 200 here. A disagreement, or a missing answer, is the signal to ask again before reading back. Cheaper variants are in section 2.6.
- **Consider `codemix` or `verbatim` plus the parser as the main path on v3.0**, with `transcribe` as the second reading. The word path fails where the parser can be fixed.
- **Fix the three wrong-amount parser gaps first** (section 4), then the Kannada spellings.
- `DESIGN.md` section 6 ("Amounts") and E3 in section 9 still describe the 20-sentence pilot and call `transcribe` plus the fraction rule sufficient. Both are stale against this report.

## 1. What was measured

| | |
|---|---|
| Question | E3: is the amount heard right, naive digit reading against the `samajh.amounts` parser, Prisma v2.5 against v3.0. E5: does it survive phone audio and noise |
| Test set | `data/amounts/amounts-v1.jsonl`, 240 sentences, 60 per language (hi, hi-en, ta, kn), 15 per stratum (plain, lakh/crore compounds, fractions, two-digit counts 21 to 99). Generated by `samajh/evalkit/amounts/grammar.py` from seed 20261110 and frozen by sha256 `62b0dd71…5e0d76` before any audio was made. The runner refuses a manifest with another hash |
| Gold | The integer the generator used to build the sentence. One amount per sentence |
| Metric | Exact match on whole rupees. No partial credit. A method that gives no answer is wrong |
| Voices | One Timbre voice per sentence, 4 voices per language (timbre-v3.0 and timbre-v2.5, female and male per the docs), rotated inside each stratum by a seeded shuffle. 16 kHz WAV |
| Audio conditions | `clean16k` as Timbre made it. `phone`: 8 kHz G.711 mu-law round trip. `narrowband`: 8 kHz, 300 to 3400 Hz band-limit, mu-law (a GSM-like band, not a GSM codec). `babble10`, `babble5`, `street10`, `street5`: synthetic noise added to the 16 kHz clip at 10 or 5 dB SNR, then the phone step |
| Speech-to-text | Prisma REST `/stt/v3`, `prisma-v2.5` and `prisma-v3.0`. Main format `transcribe` with the language set (Hinglish sent as `hi-IN`). On subsets: v3.0 `verbatim`, v3.0 `codemix`, v3.0 `transcribe` with `indic-auto`, v2.5 `verbatim` |
| Methods scored | `naive`: the first digit string in the transcript, times a unit word directly after it (the pilot's rule). `parser`: `samajh.amounts.parse_amount`, default mode. Both see the transcript and the language only |
| Intervals | Wilson 95% on each cell. The same sentences are reused across conditions and models, so cells are not independent samples: compare two cells with the paired counts, not by overlapping intervals |

Design of the matrix (2,640 transcriptions; the budget did not allow the full cross):

- All 240 sentences: both models, `transcribe`, `clean16k` and `phone`.
- Noise: each sentence is heard under two of the four noise cells. Fold 0 (8 of each 15, 32 sentences per language) gets `babble10` and `street5`; fold 1 (7 of each 15, 28 per language) gets `street10` and `babble5`. A noise cell is not the same sentences as its neighbour.
- Formats on `phone`, fold 0: v3.0 `verbatim`, `codemix`, and `transcribe` with `indic-auto`.
- Fold 1: v2.5 `verbatim` on `phone`, and both models on `narrowband`.
- v2.5 `transcribe` also returns `literal`, its wording before number formatting. It is scored as a second output of the same call at no cost.

### Coverage and spend

<!-- BEGIN coverage -->
| planned cells | transcribed | missing | clips voiced | ledger estimate for this run (credits) |
| --- | --- | --- | --- | --- |
| 2640 | 2640 | 0 | 240 | 93.74 |

Parser scored: sha256 `efbd312d3bc7c33e…` over `samajh/amounts/*.py` as they were when this table was generated. ffmpeg 8.1.2, transform version 1.
<!-- END coverage -->

The run spent an estimated **93.74 credits** against a budget of 120: 20.62 for 240 Timbre clips (10,312 characters, 665 s of audio) and 73.12 for 2,640 Prisma calls (7,312 audio seconds). The figure is the sum of the ledger rows whose cache key this run recorded: 2,880 paid calls, and 16 answers of 504 for which the ledger charges nothing (the pilot's dashboard reading found 504s unbilled). The first 20 sentences cost 6.57 credits, which extrapolated to 95 to 107 for the full run before it was started. The whole ledger stood at 113.80 estimated credits when this was written, other workers included. No OpenRouter call was made: the carrier sentences are hand-written templates.

Prisma v2.5 answered 504 on 15 of 1,184 calls, 14 of them Tamil or Kannada; each succeeded on the second attempt after a wait of about 30 s (inferred from the ledger times: a `Retry-After` the client honours). v3.0 did so once in 1,456 calls.

## 2. Results

### 2.1 Naive digit reading against the parser (all 240 sentences)

<!-- BEGIN headline -->
| stt | condition | naive digit reading | parser | parser only ✓ | naive only ✓ | McNemar p |
| --- | --- | --- | --- | --- | --- | --- |
| v2.5 transcribe item | clean16k | 157/240 (65%, 59-71) | 216/240 (90%, 86-93) | 59 | 0 | 3.5e-18 |
| v3.0 transcribe item | clean16k | 217/240 (90%, 86-94) | 221/240 (92%, 88-95) | 4 | 0 | 0.12 |
| v2.5 transcribe item | phone | 156/240 (65%, 59-71) | 214/240 (89%, 85-92) | 58 | 0 | 6.9e-18 |
| v3.0 transcribe item | phone | 220/240 (92%, 87-95) | 221/240 (92%, 88-95) | 1 | 0 | 1 |
<!-- END headline -->

Paired contrasts of the parser's score, each on identical sentences:

<!-- BEGIN contrasts -->
| parser, A against B | sentences | A | B | A only ✓ | B only ✓ | McNemar p |
| --- | --- | --- | --- | --- | --- | --- |
| v3.0 transcribe against v2.5 transcribe | clean16k, all | 221/240 (92%, 88-95) | 216/240 (90%, 86-93) | 19 | 14 | 0.49 |
| v3.0 transcribe against v2.5 transcribe | phone, all | 221/240 (92%, 88-95) | 214/240 (89%, 85-92) | 22 | 15 | 0.32 |
| phone against clean16k | v2.5 transcribe, all | 214/240 (89%, 85-92) | 216/240 (90%, 86-93) | 2 | 4 | 0.69 |
| phone against clean16k | v3.0 transcribe, all | 221/240 (92%, 88-95) | 221/240 (92%, 88-95) | 2 | 2 | 1 |
| v3.0 codemix against v3.0 transcribe | phone, fold 0 | 123/128 (96%, 91-98) | 119/128 (93%, 87-96) | 7 | 3 | 0.34 |
| v3.0 verbatim against v3.0 transcribe | phone, fold 0 | 122/128 (95%, 90-98) | 119/128 (93%, 87-96) | 7 | 4 | 0.55 |
| v3.0 indic-auto against v3.0 language set | phone, fold 0, transcribe | 118/128 (92%, 86-96) | 119/128 (93%, 87-96) | 0 | 1 | 1 |
| v2.5 literal against v2.5 transcribe text | phone, all | 219/240 (91%, 87-94) | 214/240 (89%, 85-92) | 11 | 6 | 0.33 |
<!-- END contrasts -->

"parser only ✓" counts sentences the parser got right and the naive reading got wrong on the same clip and model; "naive only ✓" is the reverse. McNemar's exact test uses those two counts.

### 2.2 By language

<!-- BEGIN by_language -->
| language | stt | condition | naive digit reading | parser | parser only ✓ | naive only ✓ | McNemar p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hi | v2.5 transcribe item | clean16k | 47/60 (78%, 66-87) | 59/60 (98%, 91-100) | 12 | 0 | 0.00049 |
| hi | v3.0 transcribe item | clean16k | 55/60 (92%, 82-96) | 56/60 (93%, 84-97) | 1 | 0 | 1 |
| hi | v2.5 transcribe item | phone | 47/60 (78%, 66-87) | 59/60 (98%, 91-100) | 12 | 0 | 0.00049 |
| hi | v3.0 transcribe item | phone | 56/60 (93%, 84-97) | 56/60 (93%, 84-97) | 0 | 0 | 1 |
| hi-en | v2.5 transcribe item | clean16k | 42/60 (70%, 57-80) | 54/60 (90%, 80-95) | 12 | 0 | 0.00049 |
| hi-en | v3.0 transcribe item | clean16k | 59/60 (98%, 91-100) | 59/60 (98%, 91-100) | 0 | 0 | 1 |
| hi-en | v2.5 transcribe item | phone | 42/60 (70%, 57-80) | 53/60 (88%, 78-94) | 11 | 0 | 0.00098 |
| hi-en | v3.0 transcribe item | phone | 58/60 (97%, 89-99) | 58/60 (97%, 89-99) | 0 | 0 | 1 |
| ta | v2.5 transcribe item | clean16k | 30/60 (50%, 38-62) | 55/60 (92%, 82-96) | 25 | 0 | 6e-08 |
| ta | v3.0 transcribe item | clean16k | 53/60 (88%, 78-94) | 53/60 (88%, 78-94) | 0 | 0 | 1 |
| ta | v2.5 transcribe item | phone | 30/60 (50%, 38-62) | 54/60 (90%, 80-95) | 24 | 0 | 1.2e-07 |
| ta | v3.0 transcribe item | phone | 53/60 (88%, 78-94) | 54/60 (90%, 80-95) | 1 | 0 | 1 |
| kn | v2.5 transcribe item | clean16k | 38/60 (63%, 51-74) | 48/60 (80%, 68-88) | 10 | 0 | 0.002 |
| kn | v3.0 transcribe item | clean16k | 50/60 (83%, 72-91) | 53/60 (88%, 78-94) | 3 | 0 | 0.25 |
| kn | v2.5 transcribe item | phone | 37/60 (62%, 49-73) | 48/60 (80%, 68-88) | 11 | 0 | 0.00098 |
| kn | v3.0 transcribe item | phone | 53/60 (88%, 78-94) | 53/60 (88%, 78-94) | 0 | 0 | 1 |
<!-- END by_language -->

### 2.3 By audio condition (E5)

Parser, `transcribe`, language set. Blank cells were not run.

<!-- BEGIN conditions_parser -->
| language | stt | clean16k | phone | narrowband | street10 | street5 | babble10 | babble5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hi | v2.5 transcribe item | 59/60 (98%, 91-100) | 59/60 (98%, 91-100) | 27/28 (96%, 82-99) | 27/28 (96%, 82-99) | 32/32 (100%, 89-100) | 32/32 (100%, 89-100) | 26/28 (93%, 77-98) |
| hi | v3.0 transcribe item | 56/60 (93%, 84-97) | 56/60 (93%, 84-97) | 25/28 (89%, 73-96) | 25/28 (89%, 73-96) | 31/32 (97%, 84-99) | 31/32 (97%, 84-99) | 20/28 (71%, 53-85) |
| hi-en | v2.5 transcribe item | 54/60 (90%, 80-95) | 53/60 (88%, 78-94) | 24/28 (86%, 69-94) | 27/28 (96%, 82-99) | 30/32 (94%, 80-98) | 28/32 (88%, 72-95) | 25/28 (89%, 73-96) |
| hi-en | v3.0 transcribe item | 59/60 (98%, 91-100) | 58/60 (97%, 89-99) | 27/28 (96%, 82-99) | 27/28 (96%, 82-99) | 32/32 (100%, 89-100) | 32/32 (100%, 89-100) | 27/28 (96%, 82-99) |
| ta | v2.5 transcribe item | 55/60 (92%, 82-96) | 54/60 (90%, 80-95) | 26/28 (93%, 77-98) | 25/28 (89%, 73-96) | 29/32 (91%, 76-97) | 29/32 (91%, 76-97) | 23/28 (82%, 64-92) |
| ta | v3.0 transcribe item | 53/60 (88%, 78-94) | 54/60 (90%, 80-95) | 27/28 (96%, 82-99) | 27/28 (96%, 82-99) | 27/32 (84%, 68-93) | 26/32 (81%, 65-91) | 25/28 (89%, 73-96) |
| kn | v2.5 transcribe item | 48/60 (80%, 68-88) | 48/60 (80%, 68-88) | 24/28 (86%, 69-94) | 24/28 (86%, 69-94) | 23/32 (72%, 55-84) | 25/32 (78%, 61-89) | 23/28 (82%, 64-92) |
| kn | v3.0 transcribe item | 53/60 (88%, 78-94) | 53/60 (88%, 78-94) | 24/28 (86%, 69-94) | 23/28 (82%, 64-92) | 25/32 (78%, 61-89) | 27/32 (84%, 68-93) | 21/28 (75%, 57-87) |
<!-- END conditions_parser -->

Naive digit reading, same cells:

<!-- BEGIN conditions_naive -->
| language | stt | clean16k | phone | narrowband | street10 | street5 | babble10 | babble5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hi | v2.5 transcribe item | 47/60 (78%, 66-87) | 47/60 (78%, 66-87) | 21/28 (75%, 57-87) | 21/28 (75%, 57-87) | 26/32 (81%, 65-91) | 26/32 (81%, 65-91) | 20/28 (71%, 53-85) |
| hi | v3.0 transcribe item | 55/60 (92%, 82-96) | 56/60 (93%, 84-97) | 24/28 (86%, 69-94) | 25/28 (89%, 73-96) | 31/32 (97%, 84-99) | 31/32 (97%, 84-99) | 20/28 (71%, 53-85) |
| hi-en | v2.5 transcribe item | 42/60 (70%, 57-80) | 42/60 (70%, 57-80) | 21/28 (75%, 57-87) | 22/28 (79%, 60-90) | 24/32 (75%, 58-87) | 23/32 (72%, 55-84) | 18/28 (64%, 46-79) |
| hi-en | v3.0 transcribe item | 59/60 (98%, 91-100) | 58/60 (97%, 89-99) | 27/28 (96%, 82-99) | 27/28 (96%, 82-99) | 32/32 (100%, 89-100) | 31/32 (97%, 84-99) | 27/28 (96%, 82-99) |
| ta | v2.5 transcribe item | 30/60 (50%, 38-62) | 30/60 (50%, 38-62) | 14/28 (50%, 33-67) | 13/28 (46%, 30-64) | 16/32 (50%, 34-66) | 16/32 (50%, 34-66) | 13/28 (46%, 30-64) |
| ta | v3.0 transcribe item | 53/60 (88%, 78-94) | 53/60 (88%, 78-94) | 26/28 (93%, 77-98) | 26/28 (93%, 77-98) | 27/32 (84%, 68-93) | 26/32 (81%, 65-91) | 25/28 (89%, 73-96) |
| kn | v2.5 transcribe item | 38/60 (63%, 51-74) | 37/60 (62%, 49-73) | 18/28 (64%, 46-79) | 17/28 (61%, 42-76) | 19/32 (59%, 42-74) | 21/32 (66%, 48-80) | 17/28 (61%, 42-76) |
| kn | v3.0 transcribe item | 50/60 (83%, 72-91) | 53/60 (88%, 78-94) | 24/28 (86%, 69-94) | 23/28 (82%, 64-92) | 26/32 (81%, 65-91) | 27/32 (84%, 68-93) | 21/28 (75%, 57-87) |
<!-- END conditions_naive -->

Pooled over the four languages:

<!-- BEGIN conditions_pooled -->
| stt | method | clean16k | phone | narrowband | street10 | street5 | babble10 | babble5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2.5 transcribe item | naive | 157/240 (65%, 59-71) | 156/240 (65%, 59-71) | 74/112 (66%, 57-74) | 73/112 (65%, 56-73) | 85/128 (66%, 58-74) | 86/128 (67%, 59-75) | 68/112 (61%, 51-69) |
| v2.5 transcribe item | parser | 216/240 (90%, 86-93) | 214/240 (89%, 85-92) | 101/112 (90%, 83-94) | 103/112 (92%, 85-96) | 114/128 (89%, 82-93) | 114/128 (89%, 82-93) | 97/112 (87%, 79-92) |
| v3.0 transcribe item | naive | 217/240 (90%, 86-94) | 220/240 (92%, 87-95) | 101/112 (90%, 83-94) | 101/112 (90%, 83-94) | 116/128 (91%, 84-95) | 115/128 (90%, 83-94) | 93/112 (83%, 75-89) |
| v3.0 transcribe item | parser | 221/240 (92%, 88-95) | 221/240 (92%, 88-95) | 103/112 (92%, 85-96) | 102/112 (91%, 84-95) | 115/128 (90%, 83-94) | 116/128 (91%, 84-95) | 93/112 (83%, 75-89) |
<!-- END conditions_pooled -->

Each degraded condition against `phone` on the same sentences (parser). This is the comparison to read for E5, because a noise cell holds only half of the sentences:

<!-- BEGIN noise_paired -->
| stt | condition | parser, this condition | parser, phone, same sentences | phone only ✓ | condition only ✓ | McNemar p |
| --- | --- | --- | --- | --- | --- | --- |
| v2.5 transcribe item | narrowband | 101/112 (90%, 83-94) | 102/112 (91%, 84-95) | 2 | 1 | 1 |
| v2.5 transcribe item | street10 | 103/112 (92%, 85-96) | 102/112 (91%, 84-95) | 1 | 2 | 1 |
| v2.5 transcribe item | street5 | 114/128 (89%, 82-93) | 112/128 (88%, 81-92) | 2 | 4 | 0.69 |
| v2.5 transcribe item | babble10 | 114/128 (89%, 82-93) | 112/128 (88%, 81-92) | 1 | 3 | 0.62 |
| v2.5 transcribe item | babble5 | 97/112 (87%, 79-92) | 102/112 (91%, 84-95) | 9 | 4 | 0.27 |
| v3.0 transcribe item | narrowband | 103/112 (92%, 85-96) | 102/112 (91%, 84-95) | 1 | 2 | 1 |
| v3.0 transcribe item | street10 | 102/112 (91%, 84-95) | 102/112 (91%, 84-95) | 1 | 1 | 1 |
| v3.0 transcribe item | street5 | 115/128 (90%, 83-94) | 119/128 (93%, 87-96) | 5 | 1 | 0.22 |
| v3.0 transcribe item | babble10 | 116/128 (91%, 84-95) | 119/128 (93%, 87-96) | 3 | 0 | 0.25 |
| v3.0 transcribe item | babble5 | 93/112 (83%, 75-89) | 102/112 (91%, 84-95) | 12 | 3 | 0.035 |
<!-- END noise_paired -->

### 2.4 What the parser does when it is not right

A wrong amount is the dangerous outcome: the system holds a number and nothing tells it the number is wrong. No answer is cheaper: the bot asks again.

<!-- BEGIN outcomes -->
| stt | condition | n | correct | no answer (re-ask) | wrong amount (only a read-back catches it) |
| --- | --- | --- | --- | --- | --- |
| v2.5 transcribe item | clean16k | 240 | 216 | 20/240 (8%, 5-13) | 4/240 (2%, 1-4) |
| v3.0 transcribe item | clean16k | 240 | 221 | 1/240 (0%, 0-2) | 18/240 (8%, 5-12) |
| v2.5 transcribe item | phone | 240 | 214 | 20/240 (8%, 5-13) | 6/240 (2%, 1-5) |
| v3.0 transcribe item | phone | 240 | 221 | 2/240 (1%, 0-3) | 17/240 (7%, 4-11) |
| v2.5 transcribe item | narrowband | 112 | 101 | 9/112 (8%, 4-15) | 2/112 (2%, 0-6) |
| v3.0 transcribe item | narrowband | 112 | 103 | 1/112 (1%, 0-5) | 8/112 (7%, 4-13) |
| v2.5 transcribe item | street10 | 112 | 103 | 9/112 (8%, 4-15) | 0/112 (0%, 0-3) |
| v3.0 transcribe item | street10 | 112 | 102 | 2/112 (2%, 0-6) | 8/112 (7%, 4-13) |
| v2.5 transcribe item | street5 | 128 | 114 | 10/128 (8%, 4-14) | 4/128 (3%, 1-8) |
| v3.0 transcribe item | street5 | 128 | 115 | 1/128 (1%, 0-4) | 12/128 (9%, 5-16) |
| v2.5 transcribe item | babble10 | 128 | 114 | 12/128 (9%, 5-16) | 2/128 (2%, 0-6) |
| v3.0 transcribe item | babble10 | 128 | 116 | 0/128 (0%, 0-3) | 12/128 (9%, 5-16) |
| v2.5 transcribe item | babble5 | 112 | 97 | 11/112 (10%, 6-17) | 4/112 (4%, 1-9) |
| v3.0 transcribe item | babble5 | 112 | 93 | 5/112 (4%, 2-10) | 14/112 (12%, 8-20) |
<!-- END outcomes -->

### 2.5 Formats and language detection (phone audio)

First table: fold 0. Second table: fold 1. `literal` is v2.5's wording before number formatting. The naive reading scores 0 on `literal`, `verbatim` and `codemix` by construction, because those outputs contain no digits.

<!-- BEGIN formats -->
| language | stt | output | naive | parser |
| --- | --- | --- | --- | --- |
| hi | v2.5 transcribe item | text | 26/32 (81%, 65-91) | 32/32 (100%, 89-100) |
| hi | v2.5 transcribe item | literal | 0/32 (0%, 0-11) | 32/32 (100%, 89-100) |
| hi | v3.0 transcribe item | text | 31/32 (97%, 84-99) | 31/32 (97%, 84-99) |
| hi | v3.0 verbatim item | text | 0/32 (0%, 0-11) | 32/32 (100%, 89-100) |
| hi | v3.0 codemix item | text | 0/32 (0%, 0-11) | 32/32 (100%, 89-100) |
| hi | v3.0 transcribe indic-auto | text | 30/32 (94%, 80-98) | 31/32 (97%, 84-99) |
| hi-en | v2.5 transcribe item | text | 21/32 (66%, 48-80) | 28/32 (88%, 72-95) |
| hi-en | v2.5 transcribe item | literal | 0/32 (0%, 0-11) | 30/32 (94%, 80-98) |
| hi-en | v3.0 transcribe item | text | 32/32 (100%, 89-100) | 32/32 (100%, 89-100) |
| hi-en | v3.0 verbatim item | text | 0/32 (0%, 0-11) | 31/32 (97%, 84-99) |
| hi-en | v3.0 codemix item | text | 0/32 (0%, 0-11) | 32/32 (100%, 89-100) |
| hi-en | v3.0 transcribe indic-auto | text | 32/32 (100%, 89-100) | 32/32 (100%, 89-100) |
| ta | v2.5 transcribe item | text | 16/32 (50%, 34-66) | 28/32 (88%, 72-95) |
| ta | v2.5 transcribe item | literal | 0/32 (0%, 0-11) | 29/32 (91%, 76-97) |
| ta | v3.0 transcribe item | text | 27/32 (84%, 68-93) | 27/32 (84%, 68-93) |
| ta | v3.0 verbatim item | text | 0/32 (0%, 0-11) | 30/32 (94%, 80-98) |
| ta | v3.0 codemix item | text | 0/32 (0%, 0-11) | 30/32 (94%, 80-98) |
| ta | v3.0 transcribe indic-auto | text | 27/32 (84%, 68-93) | 27/32 (84%, 68-93) |
| kn | v2.5 transcribe item | text | 20/32 (62%, 45-77) | 24/32 (75%, 58-87) |
| kn | v2.5 transcribe item | literal | 0/32 (0%, 0-11) | 22/32 (69%, 51-82) |
| kn | v3.0 transcribe item | text | 29/32 (91%, 76-97) | 29/32 (91%, 76-97) |
| kn | v3.0 verbatim item | text | 0/32 (0%, 0-11) | 29/32 (91%, 76-97) |
| kn | v3.0 codemix item | text | 0/32 (0%, 0-11) | 29/32 (91%, 76-97) |
| kn | v3.0 transcribe indic-auto | text | 28/32 (88%, 72-95) | 28/32 (88%, 72-95) |

| language | stt | output | naive | parser |
| --- | --- | --- | --- | --- |
| hi | v2.5 transcribe item | text | 21/28 (75%, 57-87) | 27/28 (96%, 82-99) |
| hi | v2.5 transcribe item | literal | 0/28 (0%, 0-12) | 28/28 (100%, 88-100) |
| hi | v3.0 transcribe item | text | 25/28 (89%, 73-96) | 25/28 (89%, 73-96) |
| hi | v2.5 verbatim item | text | 0/28 (0%, 0-12) | 28/28 (100%, 88-100) |
| hi-en | v2.5 transcribe item | text | 21/28 (75%, 57-87) | 25/28 (89%, 73-96) |
| hi-en | v2.5 transcribe item | literal | 0/28 (0%, 0-12) | 27/28 (96%, 82-99) |
| hi-en | v3.0 transcribe item | text | 26/28 (93%, 77-98) | 26/28 (93%, 77-98) |
| hi-en | v2.5 verbatim item | text | 0/28 (0%, 0-12) | 27/28 (96%, 82-99) |
| ta | v2.5 transcribe item | text | 14/28 (50%, 33-67) | 26/28 (93%, 77-98) |
| ta | v2.5 transcribe item | literal | 0/28 (0%, 0-12) | 28/28 (100%, 88-100) |
| ta | v3.0 transcribe item | text | 26/28 (93%, 77-98) | 27/28 (96%, 82-99) |
| ta | v2.5 verbatim item | text | 0/28 (0%, 0-12) | 28/28 (100%, 88-100) |
| kn | v2.5 transcribe item | text | 17/28 (61%, 42-76) | 24/28 (86%, 69-94) |
| kn | v2.5 transcribe item | literal | 0/28 (0%, 0-12) | 23/28 (82%, 64-92) |
| kn | v3.0 transcribe item | text | 24/28 (86%, 69-94) | 24/28 (86%, 69-94) |
| kn | v2.5 verbatim item | text | 0/28 (0%, 0-12) | 23/28 (82%, 64-92) |
<!-- END formats -->

<!-- BEGIN literal_check -->
`literal` of v2.5 transcribe equals the v2.5 verbatim transcript of the same phone clip, ignoring punctuation and spaces, in 112 of 112 items (fold 1).
<!-- END literal_check -->

Pooled over the four languages (fold 0, n = 128 sentences; fold 1, n = 112):

<!-- BEGIN formats_pooled -->
| tags.fold | stt | output | naive | parser |
| --- | --- | --- | --- | --- |
| 0 | v2.5 transcribe item | text | 83/128 (65%, 56-73) | 112/128 (88%, 81-92) |
| 0 | v2.5 transcribe item | literal | 0/128 (0%, 0-3) | 113/128 (88%, 82-93) |
| 0 | v3.0 transcribe item | text | 119/128 (93%, 87-96) | 119/128 (93%, 87-96) |
| 0 | v3.0 verbatim item | text | 0/128 (0%, 0-3) | 122/128 (95%, 90-98) |
| 0 | v3.0 codemix item | text | 0/128 (0%, 0-3) | 123/128 (96%, 91-98) |
| 0 | v3.0 transcribe indic-auto | text | 117/128 (91%, 85-95) | 118/128 (92%, 86-96) |

| tags.fold | stt | output | naive | parser |
| --- | --- | --- | --- | --- |
| 1 | v2.5 transcribe item | text | 73/112 (65%, 56-73) | 102/112 (91%, 84-95) |
| 1 | v2.5 transcribe item | literal | 0/112 (0%, 0-3) | 106/112 (95%, 89-98) |
| 1 | v3.0 transcribe item | text | 101/112 (90%, 83-94) | 102/112 (91%, 84-95) |
| 1 | v2.5 verbatim item | text | 0/112 (0%, 0-3) | 106/112 (95%, 89-98) |
<!-- END formats_pooled -->

What `indic-auto` detected:

<!-- BEGIN detected -->
| item language | detected_language_code | clips |
| --- | --- | --- |
| hi | hi-IN | 32 |
| hi-en | hi-IN | 32 |
| kn | kn-IN | 32 |
| ta | ta-IN | 32 |
<!-- END detected -->

### 2.6 Two readings of one clip as a confidence signal

Prisma gives no confidence score. This table asks whether agreement between two readings can stand in for one. "Same amount" means both parser answers exist and are equal.

<!-- BEGIN agreement -->
| two readings of the same clip | sentences | n | same amount from both: how often right | different, or one has no answer | of those, at least one right |
| --- | --- | --- | --- | --- | --- |
| v2.5 transcribe and v3.0 transcribe | phone, all | 240 | 199/200 (100%, 97-100) | 40 | 37 |
| v2.5 transcribe and its own literal | phone, all | 240 | 208/212 (98%, 95-99) | 28 | 17 |
| v3.0 transcribe and v3.0 verbatim | phone, fold 0 | 128 | 115/116 (99%, 95-100) | 12 | 11 |
| v3.0 transcribe and v3.0 codemix | phone, fold 0 | 128 | 116/117 (99%, 95-100) | 11 | 10 |
<!-- END agreement -->

The first row costs a second STT call per turn (about 0.2 s here, and the key allows one request at a time, so the two calls run one after the other). The second row is free: v2.5 returns `literal` with every `transcribe` call. It is the weakest check, because the same parser gap hits both readings: of its 4 agreements on a wrong amount, 3 are parser gaps (section 4) and 1 is the suspect Tamil sentence.

### 2.7 By stratum and by voice (phone audio)

<!-- BEGIN strata -->
| tags.stratum | stt | naive digit reading | parser | parser only ✓ | naive only ✓ | McNemar p |
| --- | --- | --- | --- | --- | --- | --- |
| plain | v2.5 transcribe item | 47/60 (78%, 66-87) | 56/60 (93%, 84-97) | 9 | 0 | 0.0039 |
| plain | v3.0 transcribe item | 57/60 (95%, 86-98) | 57/60 (95%, 86-98) | 0 | 0 | 1 |
| lakh_crore | v2.5 transcribe item | 50/60 (83%, 72-91) | 53/60 (88%, 78-94) | 3 | 0 | 0.25 |
| lakh_crore | v3.0 transcribe item | 51/60 (85%, 74-92) | 52/60 (87%, 76-93) | 1 | 0 | 1 |
| fraction | v2.5 transcribe item | 9/60 (15%, 8-26) | 52/60 (87%, 76-93) | 43 | 0 | 2.3e-13 |
| fraction | v3.0 transcribe item | 54/60 (90%, 80-95) | 54/60 (90%, 80-95) | 0 | 0 | 1 |
| irregular_21_99 | v2.5 transcribe item | 50/60 (83%, 72-91) | 53/60 (88%, 78-94) | 3 | 0 | 0.25 |
| irregular_21_99 | v3.0 transcribe item | 58/60 (97%, 89-99) | 58/60 (97%, 89-99) | 0 | 0 | 1 |
<!-- END strata -->

Parser by language and stratum:

<!-- BEGIN strata_by_language -->
| language | stt | condition | plain | lakh_crore | fraction | irregular_21_99 |
| --- | --- | --- | --- | --- | --- | --- |
| hi | v2.5 transcribe item | clean16k | 15/15 (100%, 80-100) | 15/15 (100%, 80-100) | 14/15 (93%, 70-99) | 15/15 (100%, 80-100) |
| hi | v3.0 transcribe item | clean16k | 13/15 (87%, 62-96) | 14/15 (93%, 70-99) | 14/15 (93%, 70-99) | 15/15 (100%, 80-100) |
| hi | v2.5 transcribe item | phone | 15/15 (100%, 80-100) | 15/15 (100%, 80-100) | 14/15 (93%, 70-99) | 15/15 (100%, 80-100) |
| hi | v3.0 transcribe item | phone | 13/15 (87%, 62-96) | 14/15 (93%, 70-99) | 14/15 (93%, 70-99) | 15/15 (100%, 80-100) |
| hi-en | v2.5 transcribe item | clean16k | 15/15 (100%, 80-100) | 13/15 (87%, 62-96) | 12/15 (80%, 55-93) | 14/15 (93%, 70-99) |
| hi-en | v3.0 transcribe item | clean16k | 15/15 (100%, 80-100) | 14/15 (93%, 70-99) | 15/15 (100%, 80-100) | 15/15 (100%, 80-100) |
| hi-en | v2.5 transcribe item | phone | 15/15 (100%, 80-100) | 13/15 (87%, 62-96) | 11/15 (73%, 48-89) | 14/15 (93%, 70-99) |
| hi-en | v3.0 transcribe item | phone | 15/15 (100%, 80-100) | 13/15 (87%, 62-96) | 15/15 (100%, 80-100) | 15/15 (100%, 80-100) |
| ta | v2.5 transcribe item | clean16k | 15/15 (100%, 80-100) | 11/15 (73%, 48-89) | 15/15 (100%, 80-100) | 14/15 (93%, 70-99) |
| ta | v3.0 transcribe item | clean16k | 15/15 (100%, 80-100) | 12/15 (80%, 55-93) | 13/15 (87%, 62-96) | 13/15 (87%, 62-96) |
| ta | v2.5 transcribe item | phone | 15/15 (100%, 80-100) | 11/15 (73%, 48-89) | 14/15 (93%, 70-99) | 14/15 (93%, 70-99) |
| ta | v3.0 transcribe item | phone | 15/15 (100%, 80-100) | 12/15 (80%, 55-93) | 14/15 (93%, 70-99) | 13/15 (87%, 62-96) |
| kn | v2.5 transcribe item | clean16k | 11/15 (73%, 48-89) | 14/15 (93%, 70-99) | 11/15 (73%, 48-89) | 12/15 (80%, 55-93) |
| kn | v3.0 transcribe item | clean16k | 14/15 (93%, 70-99) | 13/15 (87%, 62-96) | 11/15 (73%, 48-89) | 15/15 (100%, 80-100) |
| kn | v2.5 transcribe item | phone | 11/15 (73%, 48-89) | 14/15 (93%, 70-99) | 13/15 (87%, 62-96) | 10/15 (67%, 42-85) |
| kn | v3.0 transcribe item | phone | 14/15 (93%, 70-99) | 13/15 (87%, 62-96) | 11/15 (73%, 48-89) | 15/15 (100%, 80-100) |
<!-- END strata_by_language -->

Parser by voice. Each voice spoke 15 sentences of its language, and a sentence has one voice only, so a voice's score is also the score of its 15 sentences:

<!-- BEGIN voices -->
| language | voice | v2.5 transcribe item | v3.0 transcribe item |
| --- | --- | --- | --- |
| hi | Avinash (v3.0) | 15/15 (100%, 80-100) | 14/15 (93%, 70-99) |
| hi | Deepak (v2.5) | 15/15 (100%, 80-100) | 14/15 (93%, 70-99) |
| hi | Shivani (v3.0) | 14/15 (93%, 70-99) | 14/15 (93%, 70-99) |
| hi | Nalini (v2.5) | 15/15 (100%, 80-100) | 14/15 (93%, 70-99) |
| hi-en | Riyaa (v3.0) | 12/15 (80%, 55-93) | 15/15 (100%, 80-100) |
| hi-en | Poorvi (v2.5) | 14/15 (93%, 70-99) | 15/15 (100%, 80-100) |
| hi-en | Yashraj (v3.0) | 14/15 (93%, 70-99) | 14/15 (93%, 70-99) |
| hi-en | Shubham (v3.0) | 13/15 (87%, 62-96) | 14/15 (93%, 70-99) |
| ta | Prakash (v3.0) | 14/15 (93%, 70-99) | 14/15 (93%, 70-99) |
| ta | Lakshmi (v3.0) | 13/15 (87%, 62-96) | 13/15 (87%, 62-96) |
| ta | Trisha (v2.5) | 14/15 (93%, 70-99) | 13/15 (87%, 62-96) |
| ta | Asmita (v2.5) | 13/15 (87%, 62-96) | 14/15 (93%, 70-99) |
| kn | Kavin (v2.5) | 14/15 (93%, 70-99) | 13/15 (87%, 62-96) |
| kn | Chetana (v3.0) | 14/15 (93%, 70-99) | 13/15 (87%, 62-96) |
| kn | Saanvi (v2.5) | 10/15 (67%, 42-85) | 14/15 (93%, 70-99) |
| kn | Harshad (v3.0) | 10/15 (67%, 42-85) | 13/15 (87%, 62-96) |
<!-- END voices -->

### 2.8 Control: the parser on the written sentences

No audio. This is the ceiling the parser could reach if Prisma returned the sentence exactly as written.

<!-- BEGIN text_control -->
| language | parser on the source sentence (no audio) |
| --- | --- |
| hi | 60/60 (100%, 94-100) |
| hi-en | 60/60 (100%, 94-100) |
| ta | 59/60 (98%, 91-100) |
| kn | 60/60 (100%, 94-100) |
<!-- END text_control -->

### 2.9 Latency and retries seen during the run

One run, one machine, wall time as the client saw it. Not a benchmark.

<!-- BEGIN latency -->
| model | calls | median s | p95 s | calls needing a retry |
| --- | --- | --- | --- | --- |
| prisma-v2.5 | 1184 | 0.21 | 0.37 | 15 |
| prisma-v3.0 | 1456 | 0.21 | 0.33 | 1 |
<!-- END latency -->

## 3. Confusion patterns

Counts are failed cells over all conditions unless a denominator is given. Every one is in [`FAILURES.md`](FAILURES.md).

**Prisma v2.5, `transcribe`**

1. **Fraction word left in front of the unit's digits** (`सवा 2,00,000`, `அரை ₹1,00,00,000`, `ಅರ್ಧ ₹1,00,000`). This is the pilot's finding at scale: on phone audio the naive reading is right on 9 of 60 fraction sentences, the parser on 52.
2. **A count or a tens word left in front of digits.** `பதினோரு ₹1,00,00,000` (11 crore), `नाइंटी ₹1,80,000` (90 lakh 80 thousand), `ಎಪ್ಪತ್ತ್ ₹4,00,000` (74 lakh), `ಅರವತ್ತ್ 6,750` (66,750). 35 cells, 11 sentences. The parser refuses all of them.
3. **Higher groups as digits, lower groups left as words.** `8,00,000 ஐயாயிரத்து ₹500`, `60,00,000 ಮುನ್ನೂರು ರೂಪಾಯಿ`, `4 கோடியே 8,00,000 ஐம்பத்தையாயிரம்`. 30 cells, 8 sentences.
4. **N-and-a-half written as a clock time.** `08:30 100` for साढ़े आठ सौ (850), `01:45 ₹1,00,000` for 1.75 lakh, `03:30 ₹1,00,000`. 16 cells, 5 sentences, Hindi and Kannada.
5. **Hinglish numbers stay as English words in Devanagari** (`वन एंड अ हाफ क्रोर`, `सेवेनटीन थाउज़ंड सेवेंटी`), and "point" decimals are split (`टू प्वाइंट ₹25,00,00,000`, `7.50000000`).
6. **Kannada spellings** the word table lacks: ಅರುವತ್ತು for 60, ನಾನ್ನೂರು for 400, and tens with a virama (ಅರವತ್ತ್ನಾಲ್ಕು, ಎಪ್ಪತ್ತ್ ನಾಲ್ಕು). Whether these are accepted spellings or v2.5's own is `not human-reviewed`.

**Prisma v3.0, `transcribe`**

7. **Decimal plus unit word** (`1.5 crore`, `0.5 கோடி`): 43 of the 120 fraction clips on clean and phone audio. The parser reads these.
8. **Amounts that skip a group are written as another number.** 5,00,200 as `5,00,000` or `5,200`; 3,00,200 as `3,02,000` or `3,200`; 16,00,700 as `16,700`; 6,025 as `6,250`; 19,080 as `19,800`; 20,020 as `20,20`; 45,01,000 as `45,00,000`.

<!-- BEGIN skipped_groups -->
| stt | amount skips a group | parser, phone, non-fraction sentences |
| --- | --- | --- |
| v2.5 transcribe item | no | 147/164 (90%, 84-93) |
| v2.5 transcribe item | yes | 15/16 (94%, 72-99) |
| v3.0 transcribe item | no | 161/164 (98%, 95-99) |
| v3.0 transcribe item | yes | 6/16 (38%, 18-61) |
<!-- END skipped_groups -->

9. **Fractions formatted to the wrong number, mostly Tamil and Kannada.** Half a lakh as `5,00,000` (Tamil and Kannada), three quarters of a crore as `75,00,00,000`, 1.75 lakh as `1,25,000`, the quarter dropped from 2.25 lakh and 1.25 lakh. Hindi: पौने चार सौ (375) as `350`. 9 sentences, proven or unresolved.
10. **The fraction applied and the word kept**: `ಅರ್ಧ 50,00,000` (one cell). v2.5 writes `ಅರ್ಧ ₹1,00,00,000` for the same words. So "a fraction word in front of digits" means "apply it" on v2.5 and can mean "already applied" on v3.0. The parser refused this cell, which is the safe answer.

**Both models, under noise**

11. Words are lost or changed: `Printing.`, `मेरी ईएमआई डेट नहीं`, 79,100 heard as 79,300, a final ನೂರು dropped. 41 failed cells are labelled recognition across all configurations: 40 under noise (24 of them under babble at 5 dB) and one on phone audio (a v3.0 `verbatim` transcript that doubled a unit word).

**One suspect sentence.** `amt-ta-irr-06` (தொண்ணூற்றையாயிரத்து அறுநூறு, 95,600) was heard as 90,600 by every configuration. The fused form for "ninety-five thousand" comes from `spoken_amount` and the builder of the test set had flagged it as doubtful before the run. It is counted as a failure everywhere and labelled `source_or_voice`.

## 4. Failures: recognition against parser gaps

Every failed cell is listed with its transcript in [`FAILURES.md`](FAILURES.md). Each distinct (sentence, transcript) pair was labelled by reading it (`failure_labels.tsv`). Tamil and Kannada labels were made without a fluent reader and are `not human-reviewed`.

The 331 failed cells are 162 distinct (sentence, transcript) pairs on 71 sentences. Labels:

| Label | Meaning | Who can fix it |
|---|---|---|
| `parser_gap` | The number words are intact in the transcript (a spelling variant, a spacing, another script). A reader gets gold; the parser does not | The parser |
| `partial_itn` | Prisma formatted part of the number and left the rest as words. The pieces still determine gold by a composition rule, like the fraction rule the parser already has | The parser, with care: each rule reads a Prisma quirk |
| `prisma_formatting` | Prisma heard the words (its own word output for the same sentence is right: `literal` on v2.5, `verbatim` or `codemix` on v3.0) and wrote digits that are another number. The transcript does not give gold | Only a read-back, or a second reading |
| `unresolved` | v3.0 wrote wrong digits on clean or phone audio and there is no v3.0 word output for that sentence (fold 1). Formatting or recognition; the shapes match the proven formatting errors | Only a read-back, or a second reading |
| `recognition` | The words are wrong or missing | Only a read-back when the parser returns an amount; a re-ask when it returns none |
| `source_or_voice` | Fails under every configuration: the written form or the TTS voice is suspect | The test set |

How the split between `prisma_formatting` and `recognition` was made: by evidence, not by guess. For a v2.5 failure the `literal` of the same call shows what v2.5 heard. For a v3.0 failure the `verbatim` and `codemix` transcripts of the phone clip of the same sentence do (fold 0 only). Where v3.0 was right on phone audio and wrong under a noise condition, the failure is labelled recognition.

Clean and phone audio, `transcribe`, the configuration the design uses:

<!-- BEGIN failure_core -->
| stt | condition | parser now | parser_gap | partial_itn | prisma_formatting | unresolved | recognition | source_or_voice | if both parser-side kinds were fixed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2.5 transcribe item | clean16k | 216/240 (90%, 86-93) | 3 | 18 | 2 | 0 | 0 | 1 | 237/240 (99%, 96-100) |
| v2.5 transcribe item | phone | 214/240 (89%, 85-92) | 3 | 19 | 3 | 0 | 0 | 1 | 236/240 (98%, 96-99) |
| v3.0 transcribe item | clean16k | 221/240 (92%, 88-95) | 0 | 0 | 9 | 9 | 0 | 1 | 221/240 (92%, 88-95) |
| v3.0 transcribe item | phone | 221/240 (92%, 88-95) | 0 | 1 | 8 | 9 | 0 | 1 | 222/240 (92%, 88-95) |
<!-- END failure_core -->

The same breakdown for every output on phone audio (fold 0 has 128 sentences, fold 1 has 112):

<!-- BEGIN failure_formats -->
| fold | stt | output | parser now | parser_gap | partial_itn | prisma_formatting | unresolved | recognition | source_or_voice | if both parser-side kinds were fixed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | v2.5 transcribe item | literal | 113/128 (88%, 82-93) | 13 | 1 | 0 | 0 | 0 | 1 | 127/128 (99%, 96-100) |
| 0 | v2.5 transcribe item | text | 112/128 (88%, 81-92) | 1 | 12 | 2 | 0 | 0 | 1 | 125/128 (98%, 93-99) |
| 0 | v3.0 codemix item | text | 123/128 (96%, 91-98) | 4 | 0 | 0 | 0 | 0 | 1 | 127/128 (99%, 96-100) |
| 0 | v3.0 transcribe indic-auto | text | 118/128 (92%, 86-96) | 0 | 0 | 9 | 0 | 0 | 1 | 118/128 (92%, 86-96) |
| 0 | v3.0 transcribe item | text | 119/128 (93%, 87-96) | 0 | 0 | 8 | 0 | 0 | 1 | 119/128 (93%, 87-96) |
| 0 | v3.0 verbatim item | text | 122/128 (95%, 90-98) | 4 | 0 | 0 | 0 | 1 | 1 | 126/128 (98%, 94-100) |
| 1 | v2.5 transcribe item | literal | 106/112 (95%, 89-98) | 6 | 0 | 0 | 0 | 0 | 0 | 112/112 (100%, 97-100) |
| 1 | v2.5 transcribe item | text | 102/112 (91%, 84-95) | 2 | 7 | 1 | 0 | 0 | 0 | 111/112 (99%, 95-100) |
| 1 | v2.5 verbatim item | text | 106/112 (95%, 89-98) | 6 | 0 | 0 | 0 | 0 | 0 | 112/112 (100%, 97-100) |
| 1 | v3.0 transcribe item | text | 102/112 (91%, 84-95) | 0 | 1 | 0 | 9 | 0 | 0 | 103/112 (92%, 85-96) |
<!-- END failure_formats -->

All failed cells, every configuration and output:

<!-- BEGIN failure_counts -->
| label | sentences | v2.5 transcribe | v2.5 words (literal, verbatim, codemix) | v3.0 transcribe | v3.0 words (literal, verbatim, codemix) |
| --- | --- | --- | --- | --- | --- |
| parser_gap | 24 | 8 wrong amount, 5 no answer | 20 wrong amount, 57 no answer | 0 wrong amount, 1 no answer | 0 wrong amount, 8 no answer |
| partial_itn | 24 | 6 wrong amount, 70 no answer | 0 wrong amount, 4 no answer | 0 wrong amount, 2 no answer | 0 wrong amount, 0 no answer |
| prisma_formatting | 15 | 3 wrong amount, 6 no answer | 0 wrong amount, 0 no answer | 42 wrong amount, 1 no answer | 0 wrong amount, 0 no answer |
| recognition | 22 | 3 wrong amount, 8 no answer | 2 wrong amount, 9 no answer | 14 wrong amount, 4 no answer | 0 wrong amount, 1 no answer |
| source_or_voice | 1 | 2 wrong amount, 2 no answer | 2 wrong amount, 2 no answer | 5 wrong amount, 0 no answer | 2 wrong amount, 0 no answer |
| unresolved | 12 | 0 wrong amount, 0 no answer | 0 wrong amount, 0 no answer | 38 wrong amount, 4 no answer | 0 wrong amount, 0 no answer |
<!-- END failure_counts -->

### Parser gaps, for the owner of `samajh/amounts`

Listed for the core owner; nothing in `samajh/amounts` was edited by this work package. The parser scored is the one hashed in section 1. Order: wrong amounts first, because they are silent.

**Returns a wrong amount (fix first)**

1. **English "X and a half UNIT" in Devanagari.** `वन एंड अ हाफ क्रोर` returns 50,00,000 for 1,50,00,000; `टू एंड अ हाफ लाख` returns 50,000; `सिक्स एंड अ हाफ क्रोर` returns 50,00,000. The parser reads `हाफ UNIT` and ignores `X एंड अ`. 17 cells, v2.5 text and literal. Also seen with the unit spelt `लैक` and the currency spelt `रूपीज़`, `रुपीज़`.
2. **An unknown number word next to a known one is dropped without notice.** `ನಲವತ್ತೊಂಬತ್ತು ಸಾವಿರದ ನಾನ್ನೂರು` returns 49,000 for 49,400; `49,000 ನಾನ್ನೂರು ರೂಪಾಯಿ` returns 49,000; `ಮುನ್ನೂರ ಅರುವತ್ತು ರೂಪಾಯಿ` returns 300 for 360; `64,000 ನಾನ್ನೂರು` returns 64,000 for 64,400. 16 cells. Adding the spellings fixes these cases; the general fix is to refuse when an unread word sits between a number and its currency word.
3. **A fraction word the table lacks, in front of unit digits.** `எழரை 1,00,00,000` returns 1,00,00,000 for 7,50,00,000 (எழரை is ஏழரை with a short vowel). 1 cell.
4. **A garbled v2.5 number is multiplied out.** `6,13,00,020 थाउज़ंड रुपये` returns 61300020000 for 6,13,20,000 and `9,00,014 थाउज़ंड ₹100` returns 900014100 for 9,14,100. These are Prisma's errors (labelled `prisma_formatting`, 3 cells), but the parser could refuse a comma-grouped number whose last group is not 000 followed by a thousand word.

**Returns no answer (safe, but each is a re-ask)**

The generated table has every kind with its count and an example. In short:

- Kannada spellings: ಅರುವತ್ತು (60), ನಾನ್ನೂರು and ನಾನ್ನೂರ (400), tens with a virama, fused or split (ಅರವತ್ತ್ನಾಲ್ಕು, ಎಪ್ಪತ್ತ್ನಾಲ್ಕು, ಐವತ್ತ್ಮೂರು, ಅರವತ್ತ್ ಒಂಬತ್ತು, ಇಪ್ಪತ್ತ್ ಎಂಟು, ಐವತ್ತ್ ನಾಲ್ಕು), ಏಳ್ನೂರ and ಏಳು ನೂರು (700).
- Kannada fractions written as two words: ಒಂದು ಮುಕ್ಕಾಲು (1.75), ಒಂದು ಕಾಲು (1.25).
- Tamil: a bare ஆயிரம் after an ordinary word (`கணக்கிலிருந்து ஆயிரம் ரூபாய்`). This one also fails on the written sentence, so it is a gap with no speech involved. எழரை for ஏழரை. A fraction written `3/4 லட்சம்`.
- Hinglish in Devanagari: `सेवेनटीन थाउज़ंड सेवेंटी`.
- Composition of partly formatted v2.5 output: a count word times the digits of one unit (`பதினோரு ₹1,00,00,000`, `ಎಪ್ಪತ್ತ್ನಾಲ್ಕು ₹1,00,000`, `பதிமூன்று 1,050`); a tens word plus digits that start with the units (`ಅರವತ್ತ್ 9,06,000` is 69,06,000, `नाइंटी ₹4,13,000` is 94,13,000); higher groups in digits plus lower groups in words (`5,00,000 दो सौ`, `8,00,000 ஐயாயிரத்து ₹500`, `60,00,000 ಮುನ್ನೂರು`); a clock time before a unit (`08:30 100` is 850, `01:45 ₹1,00,000` is 1,75,000).

Two cautions on the composition rules. First, each one reads a v2.5 formatting habit, and v3.0 does not share them: `ಅರ್ಧ 50,00,000` on v3.0 already has the half applied. A rule should know which model wrote the text, or refuse when the digits are not a round unit. Second, the clock-time rule would misread a real time said next to an amount; it needs the unit word directly after it.

Simplest route for v2.5: parse `literal` (the words) as well as the text, and accept only when both give the same amount. On phone audio that agreement was right in 208 of 212 sentences; 3 of the 4 misses are gaps 1 and 2 above and the fourth is the suspect Tamil sentence.

<!-- BEGIN parser_gaps -->
| kind | what the parser meets | failed cells | of them a wrong amount | sentences | example transcript | gold | parser said |
| --- | --- | --- | --- | --- | --- | --- | --- |
| parser_gap | tens word written with a virama (ಅರವತ್ತ್, ಎಪ್ಪತ್ತ್ನಾಲ್ಕು ...) is not in the lexicon | 18 | 0 | 6 | ಖಾತೆಯಿಂದ ಎಪ್ಪತ್ತ್ನಾಲ್ಕು ಲಕ್ಷ ರೂಪಾಯಿ ಕಡಿತವಾಯಿತು | 74,00,000 | ambiguous:malformed[] |
| parser_gap | English in Devanagari, 'X एंड अ हाफ UNIT': parser reads only 'हाफ UNIT' and returns half a unit | 17 | 17 | 3 | मेरी ई एम आई वन एंड अ हाफ क्रोर रुपये है। | 1,50,00,000 | 50,00,000 |
| parser_gap | ನಾನ್ನೂರು / ನಾನ್ನೂರ, a spelling of ನಾನೂರು (400), is not in the lexicon | 17 | 0 | 2 | ಪ್ರೀಮಿಯಂ ಎಂದು ನಾನ್ನೂರು ರೂಪಾಯಿ ತೆಗೆದುಕೊಂಡರು | 400 | no_amount |
| parser_gap | ಅರುವತ್ತು, a spelling of ಅರವತ್ತು (60), is not in the lexicon | 12 | 0 | 3 | ಇಎಂಐ ಅರುವತ್ತು ಲಕ್ಷ ಕಟ್ಟುತ್ತಿದ್ದೇನೆ | 60,00,000 | ambiguous:malformed[] |
| parser_gap | ಒಂದು ಮುಕ್ಕಾಲು (1.75) written as two words is not read | 8 | 0 | 2 | ನನಗೆ ಒಂದು ಮುಕ್ಕಾಲು ಲಕ್ಷ ರೂಪಾಯಿ ಸಾಲ ಸಿಕ್ಕಿತು | 1,75,000 | ambiguous:malformed[] |
| parser_gap | a bare ஆயிரம் (one thousand, no count word) after an ordinary word is refused | 6 | 0 | 1 | கணக்கிலிருந்து ஆயிரம் ரூபாய் எடுத்தார்கள் | 1,000 | ambiguous:malformed[] |
| parser_gap | ಅರುವತ್ತು, a spelling of ಅರವತ್ತು (60), is not in the lexicon: the parser drops the word and returns 300 | 6 | 6 | 1 | ಮುನ್ನೂರ ಅರುವತ್ತು ರೂಪಾಯಿ ಪ್ರೀಮಿಯಂ ಕಟ್ಟಿದೆ | 360 | 300 |
| parser_gap | tens word written with a virama (ಅರವತ್ತ್, ಎಪ್ಪತ್ತ್ನಾಲ್ಕು ...) is not in the lexicon; ನಾನ್ನೂರು / ನಾನ್ನೂರ, a spelling of ನಾನೂರು (400), is not in the lexicon | 5 | 0 | 1 | ಅರವತ್ತ್ನಾಲ್ಕು ಸಾವಿರದ ನಾನ್ನೂರು ರೂಪಾಯಿ ಪ್ರೀಮಿಯಂ ಕಟ್ಟಿದೆ | 64,400 | ambiguous:malformed[] |
| parser_gap | ನಾನ್ನೂರು / ನಾನ್ನೂರ, a spelling of ನಾನೂರು (400), is not in the lexicon: the parser drops the word and returns 49,000 | 4 | 4 | 1 | ವಿಮೆ ಮೊತ್ತ ನಲವತ್ತೊಂಬತ್ತು ಸಾವಿರದ ನಾನ್ನೂರು ರೂಪಾಯಿ ಎಂದು ಹೇಳಿದರು | 49,400 | 49,000 |
| parser_gap | ಒಂದು ಕಾಲು (1.25) written as two words is not read | 2 | 0 | 1 | ಇಎಂಐ ಒಂದು ಕಾಲು ಕೋಟಿ ಕಟ್ಟುತ್ತಿದ್ದೇನೆ. | 1,25,00,000 | ambiguous:malformed[] |
| parser_gap | English in Devanagari: सेवेनटीन / सेवेंटी spellings are not in the lexicon | 1 | 0 | 1 | अकाउंट से कटे सेवेनटीन थाउज़ंड सेवेंटी रूपीस | 17,070 | ambiguous:malformed[] |
| parser_gap | எழரை, a short-vowel spelling of ஏழரை (7.5), is not in the lexicon | 1 | 0 | 1 | எழரை கோடி காப்பீடு என்று சொன்னார்கள் | 7,50,00,000 | ambiguous:malformed[] |
| parser_gap | fraction written as 3/4 before the unit is not read | 1 | 0 | 1 | எம்மா, 3/4 லட்சம் கட்டுறேன். | 75,000 | ambiguous:multiple_amounts[3,400000] |
| parser_gap | ನಾನ್ನೂರು / ನಾನ್ನೂರ, a spelling of ನಾನೂರು (400), is not in the lexicon: the parser drops the word and returns 64,000 | 1 | 1 | 1 | ಅರವತ್ತನಾಲ್ಕು ಸಾವಿರದ ನಾನ್ನೂರು ರೂಪಾಯಿ ಪ್ರೀಮಿಯಂ ಕಟ್ಟಿದೆ | 64,400 | 64,000 |
| partial_itn | higher groups as digits, lower groups left as words: add them | 21 | 0 | 5 | उन्होंने बीमा के 5,00,000 दो सौ रुपये लिए। | 5,00,200 | ambiguous:malformed[] |
| partial_itn | v2.5 wrote N-and-a-half / N-and-three-quarters as a clock time before the unit (08:30, 01:45) | 16 | 0 | 5 | 08:30 100 का कवर बताया था। | 850 | ambiguous:malformed[8] |
| partial_itn | v2.5 left the tens word and formatted the rest: tens word + digits compose to gold | 16 | 0 | 6 | ಖಾತೆಯಿಂದ ಎಪ್ಪತ್ತ್ನಾಲ್ಕು ₹1,00,000 ಕಡಿತವಾಯಿತು | 74,00,000 | ambiguous:malformed[100000] |
| partial_itn | v2.5 split 'ninety four lakh ...' into नाइंटी + 4,13,000: tens word + digits | 5 | 0 | 1 | मेरी ई एम आई नाइंटी ₹4,13,000 है | 94,13,000 | ambiguous:multiple_amounts[90,413000] |
| partial_itn | count word left in front of the digits of one unit: count x unit | 5 | 0 | 1 | பதினோரு ₹1,00,00,000 கடன் வாங்கினேன் | 11,00,00,000 | ambiguous:multiple_amounts[11,10000000] |
| partial_itn | v2.5 wrote 'ninety lakh eighty thousand' as नाइंटी + 1,80,000: count word left in front of the digits of one unit: count x unit | 4 | 0 | 1 | नाइंटी ₹1,80,000 का लोन मिला था | 90,80,000 | ambiguous:multiple_amounts[90,180000] |
| partial_itn | count word left in front of the digits of one unit: count x unit, plus ನಾನ್ನೂರು / ನಾನ್ನೂರ, a spelling of ನಾನೂರು (400), is not in the lexicon | 4 | 0 | 1 | ಅರವತ್ತ್ನಾಲ್ಕು 1,000 ನಾನ್ನೂರು ರೂಪಾಯಿ ಪ್ರೀಮಿಯಂ ಕಟ್ಟಿದೆ | 64,400 | ambiguous:malformed[1000] |
| partial_itn | higher groups as digits, lower groups left as words: add them, plus ನಾನ್ನೂರು / ನಾನ್ನೂರ, a spelling of ನಾನೂರು (400), is not in the lexicon | 4 | 0 | 1 | 21,000 ನಾನ್ನೂರ ₹50 ಸಾಲ ತೆಗೆದುಕೊಂಡೆ | 21,450 | ambiguous:multiple_amounts[21000,50] |
| partial_itn | higher groups as digits, lower groups left as words: add them; ನಾನ್ನೂರು / ನಾನ್ನೂರ, a spelling of ನಾನೂರು (400), is not in the lexicon, so the parser drops it and returns 49,000 | 4 | 4 | 1 | ವಿಮೆ ಮೊತ್ತ 49,000 ನಾನ್ನೂರು ರೂಪಾಯಿ ಎಂದು ಹೇಳಿದರು | 49,400 | 49,000 |
| partial_itn | fraction word + unit digits, but எழரை (short vowel) is not in the lexicon: parser returns 1 crore | 1 | 1 | 1 | எழரை 1,00,00,000 காப்பீடு என்று சொன்னார்கள் | 7,50,00,000 | 1,00,00,000 |
| partial_itn | v2.5 wrote 13 thousand 50 as பதிமூன்று + 1,050: count word left in front of the digits of one unit: count x unit | 1 | 0 | 1 | பதிமூன்று 1,050 கடன் வாங்க | 13,050 | ambiguous:multiple_amounts[13,1050] |
| partial_itn | higher groups as digits, lower groups left as words: add them; ನಾನ್ನೂರು / ನಾನ್ನೂರ, a spelling of ನಾನೂರು (400), is not in the lexicon, so the parser drops it and returns 64,000 | 1 | 1 | 1 | 64,000 ನಾನ್ನೂರು ರೂಪಾಯಿ ಪ್ರೀಮಿಯಂ ಕಟ್ಟಿದೆ | 64,400 | 64,000 |
<!-- END parser_gaps -->

## 5. Limits

- **TTS voices only, no human speech.** Timbre audio has studio clarity, no hesitation, no self-correction, no accent variation beyond the 16 voices, and Prisma may have been trained on audio like it. Treat every rate here as an upper bound for real callers. Nothing in this report is an accuracy claim about real calls.
- **The chain is measured, not Prisma alone.** A failure can start in the sentence (a wrong or unnatural word form), in Timbre (a mispronounced number) or in Prisma. Nobody listened to the clips. Where a sentence fails the same way on clean audio under both models, the source or the voice is as likely a cause as the recogniser; section 4 marks those.
- **Tamil and Kannada are `not human-reviewed`**: the sentences, the fraction forms, and my labels on their failures. The canonical word forms come from `samajh.amounts.spoken_amount`, the sibling of the parser under test, so a word table that is wrong in both would not show.
- **The sentences are easier than a call.** One amount per sentence, no second number, no range, no negation, no correction, short carriers. Amounts and carriers are paired at random, so some sentences are implausible (an EMI of 3.25 crore), which may hurt or help a language model inside the recogniser.
- **Noise is synthetic.** `babble` is modulated band-limited noise with no talkers; `street` is rumble and hiss with no horns. The SNR is defined on the 16 kHz clip before the phone step; most of the street noise sits below 300 Hz, so it masks speech less than babble at the same nominal SNR. A noise cell holds half of the sentences, and the two halves differ, so compare a noise cell with `phone` only through the paired counts on its own fold.
- **`narrowband` is a band-limit, not a GSM codec** (this ffmpeg build has no GSM encoder). No packet loss, no AMR, no echo.
- **One run.** Prisma is not guaranteed to return the same transcript twice; every response is cached, so a rerun reproduces these numbers but does not re-measure them.
- **One naive baseline.** "Naive" is the pilot's rule (first digit string, times a unit word after it). A cruder reader that ignores the unit word would score lower on v3.0's `1.5 लाख` shapes.
- **Intervals are per cell and assume independent sentences.** The 240 sentences share one generator, 12 carriers and 4 voices per language, so an interval describes sentences from this generator, not amounts in general. With cells of 15 sentences, most fine-grained differences here are within noise.
- **The p-values are descriptive.** About 50 McNemar tests are shown with no correction for multiplicity. The one below 0.05 outside the naive-against-parser comparisons (v3.0 under babble at 5 dB) would not survive a correction.
- **Voice and sentence are confounded.** Each sentence has one voice, so a voice's score is the score of its 15 sentences. The voice table can show a broken voice, not rank voices.
- **The SNR is over the whole clip, pauses included.** The independent reviewer measured 0.4 to 1.9 dB more over speech-active frames on 16 clips.
- **The failure labels are one reader's.** I assigned them; Tamil and Kannada without fluency. A second annotator was not used.
- **This is now a development set for the parser.** Section 4 hands its failures to the parser's owner. Once those gaps are fixed, a score on this set is in-sample; a clean number needs a new seed (`generate(seed)`), frozen the same way.
- **Credits are estimates.** No API surface reports cost. The spend figure is the client's estimate (0.010 credits per STT second, 0.002 per TTS character), not a dashboard reading.

## 6. Plan for the real-voice check (not run)

Purpose: find out how much of the result above is an artefact of TTS audio. Source of the dataset facts: `references/real-voice-datasets.md` (checked 2026-11-10). Its rules apply: evaluation only, nothing from these datasets in the demo or the repository, a download script is shipped in place of the audio, and the licence and consent statement are cited in the write-up.

| Step | What |
|---|---|
| Dataset | **IndicVoices** (AI4Bharat, CC-BY-4.0, gated on Hugging Face, paid participants with explicit consent), Hindi `valid` split, **solo phone-app recordings only**. The 8 kHz phone-line role-plays in the same dataset are on the never-use list and are skipped. Second source for noisy read speech: **Kathbath** Hindi Noisy-Test-Unknown |
| Subset | Search the reference transcripts (text only, no audio, no credits) for amount words: लाख, हज़ार/हजार, करोड़, सौ, सवा, साढ़े, डेढ़, ढाई, पौने, and digits. Keep clips of at most 30 s (the REST limit) whose transcript names a quantity. Target 150 clips. How many exist is unknown until the search is run; if fewer than 60 are found, the check is reported as underpowered, not padded |
| Gold | Two people read each reference transcript and write the integer by hand; disagreements are resolved before any audio is transcribed, then the file is frozen by hash. Gold must not come from `parse_amount` on the reference transcript: that would hide every parser gap |
| Run | The same runner and experiment file format: a manifest of (id, language, reference text, gold) and a voicing step replaced by "load the dataset clip". Conditions: the clip as recorded, and the 8 kHz mu-law step. Both Prisma models, `transcribe`. About 150 clips x 8 s x 4 cells = 4,800 audio seconds, about 48 credits at the estimate rate |
| Report | The same tables, TTS and human results side by side and never pooled; every failure with its transcript |

What it would show: whether Prisma writes the same partly formatted shapes (a fraction word left in front of digits, a count word left in front of a unit's digits) on spontaneous human speech; the recognition error rate on number words with real accents, microphones and room noise; whether the parser gaps listed in section 4 are the ones that matter on real speech or whether new ones dominate.

What it would not show: anything about loan calls (the speakers talk about their lives, not about a premium); real telephone channels (only our simulated mu-law step); Tamil, Kannada or Hinglish as borrowers speak them (the reference file lists Hindi subsets only; whether the Tamil and Kannada splits have enough amount utterances is `[unverified]`); fractions at the density of this test set (spontaneous speech has few सवा and पौने); amounts as large as loan sizes. Kathbath is read speech, so it says little about hesitation and self-correction.

The stronger check for the product is still E4 in `DESIGN.md`: consenting teammates reading and improvising these same 240 sentences over a real phone, because it allows a paired comparison with the TTS clips of the same text. The public-dataset check comes first because it needs no recruiting.

## 7. Independent review

A reviewer that wrote none of the code (Fable, high effort) attacked the harness while the run was finishing. It was read-only and made no API calls.

What it confirmed, with its own scripts:
- No leak into scoring: changing every item's gold, tags and source text left all 7,424 predictions identical; `correct` equals "an integer equal to the manifest gold" on every row.
- No result reused across cells: 2,640 cells, 2,640 distinct fingerprints, 2,640 distinct client cache keys and 2,640 distinct (audio hash, request) pairs; each cache key recomputed from the bytes on disk matches.
- The audio is what the condition says: `clean16k` is 16 kHz, every other condition is 8 kHz with all samples on the mu-law decode table; 16 real clips measured 9.96 to 10.06 dB and 4.90 to 5.05 dB against targets of 10 and 5.
- The statistics: `wilson` against a root-finding implementation over 45,468 (k, n) pairs and Newcombe's published values; `mcnemar_exact` against the exact binomial. 632 cells of the generated tables recomputed independently: 0 differ.
- The test set: gold recomputed from the text for all 60 fraction items and 90 others; the generator makes no call into the parser; this seed is not an outlier (the parser reads 239 of 240 written sentences, against 238 to 240 for 30 other seeds).

What it proved wrong, and what was done:
- The stratum and voice tables pooled clean and phone clips and so counted each sentence twice. Fixed: both tables now use phone audio only.
- The fingerprint ignored the audio transform version; a torn last line could swallow the next row; two runs at once could each spend the budget; the budget counter missed a call paid before a crash. All four fixed in `samajh/evalkit/runner.py`, each with a test. None had occurred in this run.
- Eight mutants survived the first test suite (for example a fingerprint without the STT format). Tests added for each.
- The parser was edited by its owner while the run was in progress. No score moved, and the report now names the parser's hash.

Not fixed: a 200 answer the client cannot parse is charged and not cached (client, outside this work package). `analyze.py` has no tests of its own; the reviewer's recomputation is its check. The fixes above were not put through a second review.

The ffmpeg version in section 1 was logged by a rerun that made no calls, 40 minutes after the paid run, on the same machine.

## 8. Reproduce

```
uv run python -m samajh.evalkit.amounts --out data/amounts      # regenerates the frozen set byte for byte
uv run python -m samajh.evalkit status eval/amounts/experiment.toml
uv run python -m samajh.evalkit run eval/amounts/experiment.toml    # resumable; finished cells cost nothing
uv run python -m samajh.evalkit score eval/amounts/experiment.toml   # run/scores.jsonl
uv run python eval/amounts/label_failures.py                    # failure_labels.tsv; fails on an unlabelled failure
uv run python eval/amounts/analyze.py                           # rewrites the generated tables and FAILURES.md
```

Audio is kept outside the repository, under `.samajh/evalkit/amounts-v1/`.

## 9. Work package notes

**Plan as built.** Three units behind one manifest format (`id`, `language`, `text`, `gold`, `tags`):
- `samajh/audio/`: `Resample`, `MuLaw`, `BandLimit`, `AddNoise` steps and a content-addressed `AudioStore` (ffmpeg for filtering and noise synthesis, Python for the exact-SNR mix).
- `samajh/evalkit/`: `manifest.py` (frozen manifest), `plan.py` (experiment TOML, arms, seeded voice assignment), `runner.py` (resumable run, run store, budget), `score.py` (predictors that cannot see gold, Wilson, exact McNemar, tables), `scorers.py` (naive and parser), `amounts/grammar.py` (the seeded test set), `__main__.py` (`status`, `run`, `score`).
- `eval/amounts/`: the experiment, `label_failures.py`, `analyze.py`, this report.

**Changed from the spec, and why.**
- One voice per sentence (4 voices per language, rotated within strata), not every sentence in several voices: a second voice per sentence would have cost about 94 more credits.
- The matrix is not the full cross of conditions and configurations (13,440 cells, about 390 credits at this run's mean clip length). Noise cells and format cells run on folds; section 1 says which.
- `narrowband` is a band-limit. This ffmpeg build has no GSM encoder.
- OpenRouter was not used. The carrier sentences are hand-written templates in `grammar.py`.
- The manager wrote `samajh/evalkit` (apart from the generator) directly; builders wrote `samajh/audio` and the test set; one reviewer checked all of it. The four-model architect arena was skipped, as in W2.
- `language = "item+en"` (for example `hi-IN,en-IN` on Hinglish) is supported by the runner and was not run.

**Verified live in this run.** v2.5 `literal` equals v2.5 `verbatim` on the same clip (112 of 112, ignoring punctuation and spacing). v3.0 `indic-auto` returned the item's own locale on 128 of 128 clips, Hinglish as `hi-IN`. v3.0 accepts `codemix` with `hi-IN`, `ta-IN` and `kn-IN`. Through the shared lock this run saw no 429 in 2,896 requests while other workers used the key.

**Still unverified.** The credit rates (estimates; no API surface reports cost). The `Retry-After` on v2.5's 504 (inferred from a 30 s gap in the ledger, header not read). Whether the Kannada spellings v2.5 writes are accepted ones. Voice gender and language (docs only). Everything about human speech.

**For the credit rates.** This run is a larger sample than the pilot for turning the estimates into measurements: 7,312 STT audio seconds in 2,640 calls and 10,312 TTS characters in 240 calls, between 08:47 and 09:12 IST on 2026-11-10. Other workers also used the key in that window, so the dashboard reading has to be taken against the whole ledger (`uv run python -m samajh.clients.gnani ledger`).

**Next.** (1) The parser's owner fixes the gaps in section 4; then a new seed, frozen, for a clean number. (2) The pipeline takes two readings of each amount and treats disagreement as "ask again" (section 2.6). (3) The real-voice check in section 6, then teammates reading these sentences on a real phone. (4) Babble made from overlapped Timbre voices, which is closer to a real crowd than modulated noise. (5) The same runner on the scenario set: the manifest format and the scorer interface are ready for it; it needs a scorer that calls the extractor.
