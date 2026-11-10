# Held-out amounts: Prisma v3.0 and v2.5 on amounts that skip a place-value group

Evidence for "Three numbers" in `README.md`. Wording follows `references/reviews/iter2/verify-P6.md`, which reproduced the headline numbers independently (the skipped-stratum agreement counts, the 50-item split and the 9-of-68 figure come from the tables). Counts: `tables-tts.md` (phone, from line 207) and `tables-realvoice.md` (phone, from line 128). Intervals are 95% Wilson. "Phone" is the same audio through simulated 8 kHz mu-law. The audio is Timbre TTS or public recordings, never real callers.

## Question

Does Prisma v3.0 `transcribe` write wrong digits for an amount that skips a place-value group ("one lakh three hundred": no thousands)? The first set (240 sentences, `eval/amounts/REPORT.md`) suggested it; this set tests that on new sentences with matched controls.

## Set, and the freeze

280 Hindi and Hinglish sentences, 24 carriers, 13 Timbre voices: 68 skipped-group, 68 matched controls (same carrier, voice and leading group, with the trailing figure moved into the missing group, e.g. 400,900 against 409,000; 68 of 68 pairs), 96 general, 32 fraction, 16 large. The skipped stratum is 24% of the set by design. The manifest (sha256 `1beea924…`) was written at 06:39 UTC on 2026-11-10, the first audio request is at 06:41 UTC (file times and the call ledger; git alone does not show it, because the set was first committed after the run), and `experiment.toml` fixed the reference scheme and decision rule before any audio. Scoring used the amount parser at commit 59c12d9, which reads text only; no keyterms, topic or bias were sent. The set is held out for amounts and carriers, not for number phrasing. A "silent wrong" amount is a reading that returns an amount other than gold; a refusal is not wrong, and v3.0's 5 malformed outputs count as refusals, which favours v3.0.

## Matched comparison

| Phone audio, 68 pairs | skipped | matched control |
|---|---|---|
| v3.0 `transcribe`, wrong amount | 40 (59%, 47-70) | 0 (0-5) |
| v3.0 `verbatim`, wrong amount | 1 (1%, 0-8) | 0 (0-5) |
| v2.5 `transcribe`, wrong amount | 0 (0-5) | 0 (0-5) |

On a held-out synthetic set built to stress amounts that skip a place-value group, Prisma v3.0 `transcribe` wrote a different amount for 40 of 68 such amounts (59%, 95% CI 47-70) on simulated 8 kHz phone audio, and for 0 of 68 matched controls (exact McNemar p = 1.8e-12). Its `verbatim` output of the same audio had the right number words in all 40 (91-100), and v2.5 wrote none wrong. On clean 16 kHz audio: 39 of 68 and 0 of 68. The 68 are not a rate of how often amounts go wrong; no pooled rate is claimed.

Of the 40, 26 are wrong under any reading ("one lakh three hundred" as 1,300; "five crore twenty-six thousand" as 5,26,000; "दो हज़ार बारह" as 2,000; "four lakh nine hundred" as 4,09,000). The other 14 are an "X lakh Y" phrase with Y under 100 written as X lakh Y thousand ("तीन लाख चालीस" as 3,40,000); colloquial Hindi may mean that as 3.4 lakh, so whether they count is an open question for a native speaker. Of the 50 skipped items whose phrase has no such reading, 24 were wrong (48%, 35-61) against 0 of their 50 controls.

## Real voices, apart

124 public Hindi recordings (IndicVoices 88, Kathbath 36; 90 read, 34 extempore). Only 4 skip a group, from 3 speakers: v3.0 `transcribe` was wrong on 1 (5,006 as 5,600), too few for a rate. Overall, silent wrong: v3.0 3 of 124 (2%, 1-7), v2.5 4 of 124 (3%, 1-8); no difference between the models is shown (McNemar p = 1 on 5 discordant clips). Caveats: 107 of 124 are from train splits that Gnani may have trained on, so accuracy may be optimistic; 103 golds are multiples of 100 and only 15 clips are 1,000 or more and not a multiple of 1,000; the parser had to find exactly one amount in the reference, which leaves out harder phrasings; the clips are solo phone-app recordings, not call audio.

## The agreement rule, and what it adds over v2.5 alone (phone)

Rule: accept an amount only when v3.0 and v2.5 `transcribe` give the same one.

| Data | v2.5 alone: accepted, wrong | v3.0 alone: accepted, wrong | Agreement: accepted, wrong |
|---|---|---|---|
| 280 synthetic clips | 268, 0 | 275, 40 | 224 (80%, 75-84), 0 |
| the 68 skipped | 66, 0 | 63, 40 | 22, 0 |
| 124 public recordings | 119, 4 | 123, 3 | 113 (91%, 85-95), 0 |

Accepting an amount only when v3.0 and v2.5 agree accepted 224 of 280 synthetic clips and 113 of 124 public read or extempore Hindi recordings, with no wrong amount accepted. **On the synthetic set it adds nothing measured over v2.5 alone** (0 wrong of 268), and costs 44 more re-asks and a second request. **The case for it rests on the public recordings:** v2.5 alone accepted 4 wrong (for example 500 as 100), v3.0 alone 3, and the two readings differed on each of the 6 clips where either was wrong. That is one small set, mostly train splits, with 6 clips at stake: a reason to keep the check, not a measured gain. A cheaper variant (v3.0 against v2.5's `output.literal`) was chosen on these same sets and is not claimed.

## Failure cases and limits

- 23 of the 68 skipped amounts were right. Wrong by shape (phone): lakh and units 16 of 18, lakh and hundreds 8 of 18, thousand and units 4 of 20, crore and thousands 12 of 12. The outcome (right, refused or wrong) differs between the clean and phone copy on 9 of 68 skipped items; the verifier counts 7 that change between wrong and not wrong.
- v3.0 `transcribe` wrote no wrong amount on the 96 general, 32 fraction or 16 large items. The 12 crore-and-thousand failures fall outside the retail band, and some skipped amounts are not ones a borrower would say.
- The frozen parser reads "एक लाख एक" as 1,00,000; the one `verbatim` miss (gold 100,001) is that clip, whose words are right, so the miss is the parser's. The shape matches v3.0's own error, so a correlated error is possible.
- Wilson and McNemar treat clips as independent, but there are 13 voices and 24 carriers and the two copies are the same clips, so intervals are optimistic. With 40 against 0 the conclusion survives.
- Gnani Timbre voiced the clips and Gnani Prisma read them; only the 124 public recordings step outside that loop.

## Not claimed

A pooled rate (6 of 1,358 public utterances skip a group); "v3.0 gets 14% (or 1 in 7) of amounts wrong"; any per-call, retail-band or field rate; a "proven formatting bug" (the measured fact is that the `verbatim` words are right; the cause is an inference); "fails whenever an amount skips a group"; "tested on real callers"; "validated" for any scheme.

## Reproduce

- Freeze: `sha256sum` of `data/amounts_v2/amounts-v2.jsonl` against `amounts-v2.sha256`.
- Tables, offline from stored transcripts: `uv run python eval/amounts_v2/analyze.py tts` and `… realvoice` (the real-voice rows and audio stay on the author's machine). Independent recomputation: `references/reviews/iter2/probes/p6_recompute.py tts|realvoice`.
- Fresh run of the synthetic set: `uv run python -m samajh.evalkit run eval/amounts_v2/experiment.toml`. The real-voice set uses `realvoice.toml` and audio that stays on the author's machine. Both sets together cost 136.5 estimated credits by the client's own rates, not a dashboard reading.
- Minimal reproduction for Gnani: `references/pilots/gnani-number-formatting-report.md`.
