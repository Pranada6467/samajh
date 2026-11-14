# W7: Prisma and Samajh against open, reproducible baselines — full report

Plan, fixed before each run, with every dated change: `PLAN.md`. Published figures: `PUBLISHED.md`. How to rerun:
`REPRODUCE.md`. Generated tables: `tables-amounts.md`, `tables-fleurs.md`, `tables-partc.md` (and `results-*.json`).
Every figure below gives its set, n, audio condition and treatment. All audio in the amounts set is Gnani Timbre
TTS; no figure here is a claim about real callers, and nothing here is a benchmark of Gnani's product beyond these
sets. "Open baseline" means open weights run locally; Gemini is a **closed reference**, not an open baseline.
Sarvam's speech API is not on OpenRouter and the project has no key, so it is left out.

## Systems as run
| id | model | how | licence |
|---|---|---|---|
| `whisper-large-v3` | OpenAI Whisper large-v3, MLX fp16 conversion `mlx-community/whisper-large-v3-mlx` @ `49e6aa28…` | local, greedy, `language=hi`, no fallback | Apache-2.0 (weights), MIT (conversion) |
| `indicwhisper-hi` | AI4Bharat IndicWhisper (Vistaar), Hindi Whisper-medium checkpoint `whisper-medium-hi_alldata_multigpu` from `hindi_models.zip` (sha256 `e409b7d5…`) | local, transformers fp32 on MPS, greedy, `language=hi` | MIT |
| `gemini-3-flash` | `google/gemini-3-flash-preview` via OpenRouter, fixed prompt (verbatim, spoken script, numbers as words) | API | closed |
| Prisma v3.0 / v2.5 | `transcribe` rows from P6 (Part A); new `verbatim` rows (Part B) | API | closed (system under study) |

Not run, and why: **IndicConformer-600M** (the gated repo refused this account: 403 "not in the authorized list");
**Gemini 3.1 Pro** (stopped after 153 clips for cost, USD 4.94: its reasoning ran to the 8,192-token ceiling on a
tenth of clips; rows kept as `gemini-3.1-pro-partial`, used in no comparison; no Pro output was scored before the
switch). Library versions, revisions and settings: `runs/*/<system>.meta.json` and `REPRODUCE.md`.

Training-data overlap: IndicWhisper's Vistaar training data includes Kathbath; 36 of the 124 public amount clips are
Kathbath (train split), so its public-clip figures are probably partly in-sample. Whisper's and Gemini's training
data are not public. 107 of the 124 public clips come from train splits Gnani may also have trained on (P6).

## Part A: the amount finding against open models

Same audio files as P6 (each open row's `audio_sha256` equals the Prisma row's), **phone condition only**
(simulated 8 kHz mu-law; the clean copies were not run for the open models: machine time). Every output is read
by the frozen parser (commit 59c12d9) exactly as P6 read Prisma: the parser reads digits and Hindi or English number
words written in Latin or Devanagari as far as its lexicon goes; nothing is rewritten before parsing. A reading is
right, wrong (an amount that is not gold), no amount, or ambiguous (the parser found more than one); the last two
are not counted as wrong.

### Held-out synthetic set, 280 TTS clips, phone: skipped-group amounts and matched controls
| system | skipped: right | skipped: wrong | control: right | control: wrong | skipped vs control (wrong only on skipped / only on control, exact p) |
|---|---|---|---|---|---|
| Prisma v3.0 `transcribe` | 23/68 (34%, 24-46) | 40/68 (59%, 47-70) | 68/68 | 0/68 (0-5) | 40 / 0, p = 1.8e-12 |
| Prisma v2.5 `transcribe` | 66/68 (97%) | 0/68 (0-5) | 66/68 | 0/68 | 0 / 0 |
| Whisper large-v3 | 23/68 (34%, 24-46) | 33/68 (49%, 37-60) | 43/68 (63%, 51-74) | 13/68 (19%, 12-30) | 24 / 4, p = 0.00018 |
| IndicWhisper | 44/68 (65%, 53-75) | 15/68 (22%, 14-33) | 42/68 (62%, 50-72) | 16/68 (24%, 15-35) | 9 / 10, p = 1 |
| Gemini 3 Flash (closed ref.) | 60/68 (88%, 78-94) | 8/68 (12%, 6-22) | 68/68 (95-100) | 0/68 (0-5) | 8 / 0, p = 0.0078 |

All 280: right / wrong / no amount / ambiguous — v3.0 T 235 / 40 / 0 / 5; v2.5 T 268 / 0 / 0 / 12; Whisper
179 / 50 / 2 / 49; IndicWhisper 184 / 49 / 3 / 44; Gemini 3 Flash 271 / 9 / 0 / 0. Against Prisma on the same 68
skipped clips (exact McNemar on right, only-this-system / only-Prisma): Whisper vs v3.0 11 / 11 (p = 1), vs v2.5
1 / 44 (p = 2.6e-12); IndicWhisper vs v3.0 27 / 6 (p = 0.0003), vs v2.5 2 / 24 (p = 1e-5); Gemini vs v3.0 38 / 1
(p = 1.5e-10), vs v2.5 1 / 7 (p = 0.07).

**Wrong amounts read by hand** (the independent checker read every one; synthetic text):
| system | wrong (all 280) | a different number | the right number in a form the parser cannot read |
|---|---|---|---|
| Whisper large-v3 | 50 | 44 | 6 (misspellings: लाग, क्रोड, करोर, क्रोज, नौसो) |
| IndicWhisper | 49 | 33 | 16 (13 English number words in Devanagari, e.g. "टू लैक टू थाउसेंट"; and "एक लाख एक", the gold sentence word for word, which the frozen parser reads as 1,00,000) |
| Gemini 3 Flash | 9 | 8 | 1 ("एक लाख एक", as above) |
Leaving those out, genuine wrong amounts on skipped / control: Whisper 29 / 11, IndicWhisper 13 / 8, Gemini 7 / 0.
So IndicWhisper's and Whisper's raw "wrong" counts partly measure the frozen parser, which was built on Prisma's
output style and cannot read transliterated English number words; Prisma never writes them.

**Does an open model make the skipped-group error?** Counting only a skipped amount written exactly as its matched
control's figure: **Whisper large-v3 yes, 10 times, all "X lakh Y" with Y under 100** ("तीन लाख चालीस" → 3,40,000,
"four lakh eleven" → 4,11,000); its lakh-and-hundreds errors are another shape (Western millions: "two lakh two
hundred" → 2,200,000), which it also makes on controls ("four lakh seven thousand" → 4,007,000). **Gemini 3 Flash
yes, 5 times, all "X lakh Y"**, written in words ("तीन लाख चालीस हजार"). **IndicWhisper: no exact case**; its
skipped errors are mishearings ("two lakh fourteen" → "दो लाख चौवन"). Every exact skipped-group error from another
model falls in the "X lakh Y, Y under 100" class that P6 left open as possibly colloquial (3.4 lakh): two independent
models reading those 14 of v3.0's 40 the same way supports that caveat. None of them wrote the other 26 (lakh and
hundreds, crore and thousands, lakh dropped) as v3.0 did. No open model matched v2.5 `transcribe` on these clips
(IndicWhisper right on 44 of 68 skipped against 66).

### Public recordings, 124 clips (IndicVoices 88, Kathbath 36), phone
| system | right | wrong | no amount | ambiguous | vs v3.0 T on right (only / only, p) | vs v2.5 T |
|---|---|---|---|---|---|---|
| Prisma v3.0 `transcribe` | 120 (97%, 92-99) | 3 (2%, 1-7) | 0 | 1 | | |
| Prisma v2.5 `transcribe` | 115 (93%, 87-96) | 4 (3%, 1-8) | 3 | 2 | | |
| Whisper large-v3 | 85 (69%, 60-76) | 6 (5%, 2-10) | 11 | 22 | 1 / 36, p = 5.5e-10 | 4 / 34, p = 6e-7 |
| IndicWhisper | 111 (90%, 83-94) | 1 (1%, 0-4) | 4 | 8 | 0 / 9, p = 0.004 | 6 / 10, p = 0.45 |
| Gemini 3 Flash (closed ref.) | 117 (94%, 89-97) | 6 (5%, 2-10) | 0 | 1 | 1 / 4, p = 0.38 | 6 / 4, p = 0.75 |
Only 4 public clips skip a group (v3.0 T wrong on 1, every other system wrong on 0): too few for a rate.

### A third reading in the agreement rule (phone)
Reference rule (P6): accept when v3.0 and v2.5 `transcribe` agree. Schemes fixed in `PLAN.md` before the run.
| set | scheme | accepted | wrong accepted | re-asks |
|---|---|---|---|---|
| 280 synthetic | 1 reference | 224 | 0 | 56 |
| | 2 unanimous + IndicWhisper | 155 | 0 | 125 |
| | 3 majority with IndicWhisper | 252 | 0 | 28 |
| | 4 IndicWhisper = v2.5 | 181 | 0 | 99 |
| | 2 unanimous + Whisper | 159 | 0 | 121 |
| | 3 majority with Whisper | 254 | **10** | 26 |
| | 2 unanimous + Gemini | 222 | 0 | 58 |
| | 3 majority with Gemini | 278 | **5** | 2 |
| | 4 Gemini = v2.5 | 260 | 0 | 20 |
| 124 public | 1 reference | 113 | 0 | 11 |
| | 2 unanimous + IndicWhisper | 105 | 0 | 19 |
| | 3 majority with IndicWhisper | 120 | **1** | 4 |
| | 2 unanimous + Whisper | 81 | 0 | 43 |
| | 3 majority with Whisper | 117 | **1** | 7 |
| | 2 unanimous + Gemini | 110 | 0 | 14 |
| | 3 majority with Gemini | 123 | **3** | 1 |
| | 4 Gemini = v2.5 | 113 | 2 | 11 |

**Answer to the product question:** on these two sets the reference rule already accepted no wrong amount, so a
third reading could not lower wrong accepts; it could only move re-asks. Requiring all three to agree added re-asks
with every third reading (69 more on the synthetic set with IndicWhisper, 8 more on the public set). Taking a
majority of three cut re-asks but let wrong amounts through with every third reading on at least one set (IndicWhisper
1 on the public set, Whisper 10 and 1, Gemini 5 and 3). Nothing measured here argues for adding an open model as a
third reading to the call.

## Part B: Prisma on FLEURS hi_in test
FLEURS `hi_in` test (read speech, CC-BY-4.0), 417 of 418 utterances (one over Prisma's 30 s limit left out). Prisma
`verbatim` and Gemini on a seeded 250 subset (budget); the open models on the seeded 100-clip `gemini100` sample (this
machine's memory; see `PLAN.md`). Corpus WER/CER, 95% percentile bootstrap over utterances. Three text treatments,
the same for every system: `raw` (whitespace split, nothing removed), `norm` (`wer.normalise()`: NFC, lower-case,
every Unicode punctuation or symbol character, danda included, to a space) against the `raw transcription` column,
`norm-tx` (the same against FLEURS's pre-normalised `transcription` column). Numbers are not converted: FLEURS writes
some as digits, Prisma `verbatim` and Gemini write words.

**100-clip sample, every system on the same clips (WER %, CER % in brackets of the norm row)**
| system | 16 kHz raw | 16 kHz norm | 16 kHz norm-tx | phone raw | phone norm | phone norm-tx |
|---|---|---|---|---|---|---|
| Prisma v2.5 `verbatim` | 21.0 | 11.6 [9.8-13.8] (CER 5.1) | 11.3 | 21.5 | 12.3 [10.3-14.4] (5.6) | 11.7 |
| Prisma v3.0 `verbatim` | 21.9 | 12.2 [10.2-14.6] (5.8) | 12.2 | 22.1 | 12.8 [10.5-15.6] (6.3) | 12.7 |
| IndicWhisper (open) | 22.5 | 14.4 [11.3-17.7] (7.1) | 13.9 | 23.7 | 15.8 [12.5-19.3] (8.4) | 15.3 |
| Whisper large-v3 (open) | 36.2 | 28.7 [26.2-31.4] (12.2) | 28.4 | 36.7 | 29.2 [26.6-32.0] (12.5) | 28.9 |
| Gemini 3 Flash (closed ref.) | 21.1 | 12.9 [10.8-15.3] (10.1) | 12.1 | 21.3 | 12.9 [10.5-15.7] (9.6) | 12.2 |

**250 subset (Prisma and Gemini only), norm WER:** 16 kHz: v2.5 10.9 [9.9-12.1], v3.0 11.8 [10.4-13.1], Gemini 11.6
[10.1-13.1]; phone: 11.5 [10.2-12.7], 12.5 [11.0-14.0], 11.9 [10.5-13.4]. The 50-clip `open50` scope is in the tables.

**How the text is normalised moves WER by about 8 to 10 points** for every system here (raw against norm: Prisma
v3.0 9.6, v2.5 9.3, Gemini 8.4, IndicWhisper 8.1, Whisper 7.5), more than any gap between Prisma, IndicWhisper and
Gemini; the choice of reference column moves it by 0.6 or less. No output was empty, and no system's WER is dominated
by a few utterances (its 3 worst carry 8 to 20% of its edits). **Published figures** (`PUBLISHED.md`,
each under its source's own normalisation and inference setup, not recomputed here): Whisper large-v3 17.0 (OpenAI's
README chart, against the `transcription` column) and 28.87 (Voxtral report); IndicWhisper 15.0, 11.4 or 10.5 (three
conflicting Vistaar tables); Gemini 3 Flash 8.7 (SraVaani, jiwer with lower-casing and punctuation removal);
IndicConformer none found on FLEURS. Our Whisper rerun (greedy, temperature 0, no fallback, MLX fp16, 100 clips,
norm-tx 28.4) sits near Voxtral's 28.87. The gap to OpenAI's 17.0 is mostly the scorer's normaliser: as a
sensitivity check run by the independent checker after the results (not pre-declared), the Whisper paper's Appendix C
normaliser (which maps Unicode categories M, S and P to spaces, so it also strips Devanagari vowel signs and the
virama) against the `transcription` column gives our Whisper rerun 17.5, and shrinks every system (Prisma v2.5 6.7,
v3.0 7.6, IndicWhisper 9.3, Gemini 11.0). None of our figures is a FLEURS test score: each is on a seeded 100 or 250
of the 417 clips, and published figures sit beside them only as context. Our IndicWhisper 14.4 is the medium
checkpoint, which may not be the one Vistaar reports.

## Part C: a generic LLM voice agent against the Samajh call (synthetic text)
Design and fixed prompt: `PLAN.md` Part C. B0 = a generic agent (`qwen/qwen3-235b-a22b-2507`, open weights) prompted
on the pattern of LiveKit's `outbound-caller-python` `agent.py` and given the lender's record, Samajh's four outcome
labels with their definitions, the ten fields and a quote rule; B1 = B0 plus one coached line ("ask the borrower to
tell you each detail in their own words before you mention it"). Customers: the 160 synthetic W3 customers and their
writers' replies; a router (`mistral-small-3.2`) maps each agent turn to topics and code picks the W3 reply.
Router check (blind hand-labels by an independent checker, three rounds, each on fresh utterances): stated values
disagreed on 12 of 60, then 6 of 40, then 4 of 40 (10.0%, Wilson upper bound 23%) after fixes; the counted run used
the third version. W3 open arm = the Samajh call (W3, commit 9c67da6). Different models: the comparison is of two
systems, not of design alone.

| arm, cell (r, a) | problem: missed (of 80) | problem: referred on ground | knowledge gap found (of 48) | false referral, no problem (of 80) |
|---|---|---|---|---|
| B0 (0, 0) | 17 [14-31%] + 4 no_report (human transfer) | 59 | 33 [55-80%] | 2 |
| Samajh open arm, a = 0 (W3) | 0 | 80 | 45 [83-98%] | 1 (C018) |
| B0 (1, 0)* | 18 + 3 no_report | 59 | 23 [34-62%] | 0 |
| B1 coached (1, 0)*, 88 dk customers | 13 of 40 + 2 no_report | 24 of 40 | 34 [57-82%] | 1 |
| B0 (0.5, 0.5) | 40 + 1 no_report | 33 | 20 [29-56%] | 17 (13 knowledge-gap, 4 informed) |
| Samajh open arm, a = 0.5 (W3) | see W3 | 44 | 3 | see W3 |
\* r = 1 assumes customers say yes to a figure they cannot recall; the Samajh call states none, so r does not touch it.

- Paired exact McNemar on knowledge-gap customers, B0 against the Samajh open arm (a = 0): at (0, 0) 3 found only
  by B0, 15 only by Samajh, p = 0.0075; at (1, 0) 2 and 24, p = 1.1e-5. B1 at (1, 0): 3 and 14, p = 0.013.
- Leading statements (reader-confirmed, random 40 of B0 (0, 0) calls): 39 of 40 calls stated a record value under
  test before the customer had said it (97.5%, 87-100); 37 of 40 leaving out the bare product name.
- Third parties (40 scripted relatives who say the borrower is not at home): B0 named the loan, product or a figure
  in 0 of 40 (it named the lender in 4); the Samajh call in 0 of 40 (two lines, ends `wrong_party`). The script never
  asks what the call is about, so this test is weak.
- B0's reports list a finding on almost every field: 115 of 160 calls carry 9 or 10, and 814 findings say
  `belief=false` on fields that are not false; ground match does not penalise this, which favours B0. Its reports
  would not serve as an evidence pack as they stand.
- At (0.5, 0.5) B0 found more knowledge gaps than the Samajh call (20 against 3; 17 B0-only, 0 Samajh-only),
  because the Samajh call hears "check your records" as a refusal and ends `declined` (W3's open finding), at the
  cost of 13 false referrals of knowledge-gap customers and 40 problem misses.
- Prediction (written before the run): "leads in at least half its calls" held; "at (1, 0) its knowledge-gap finds
  fall below the Samajh arm's interval" held (23 of 48 [34-62] against 45 of 48 [83-98]), and the (0, 0) row, which
  needs no recognition assumption, points the same way; the third-party part was refuted (0 of 40).
- Spend: USD 0.97 counted (plus about 0.10 dry runs). Independent recomputation: 0 disagreements over 568 calls.

## Wording
**Allowed** (each with its set, n, condition): "On the same 68 simulated-phone skipped-group amounts (TTS audio,
Hindi and Hinglish, scored by our frozen parser), Whisper large-v3 wrote 33 wrong amounts, IndicWhisper 15 and
Gemini 3 Flash 8, against 40 for Prisma v3.0 `transcribe` and 0 for v2.5; of these, 4, 2 and 1 are the right number in
a form our parser cannot read." "Whisper and Gemini also wrote some 'X lakh Y' amounts as X lakh Y thousand (10 and
5), the reading we left open as possibly colloquial." "No open model matched v2.5 `transcribe` on these clips."
"Adding a third reading as a majority vote accepted wrong amounts (Whisper 10, Gemini 5 of 280); requiring all three
to agree accepted none and asked again more often." "On 160 synthetic Hindi and Hinglish text customers, a generic
LLM caller (qwen3-235b, prompted from the LiveKit outbound-caller example and given Samajh's own outcome labels) stated
a record value before the customer did in 39 of a random 40 calls (read by hand). With customers who never agree to
what they don't know, it found 33 of 48 knowledge gaps against 45 of 48 for Samajh's open call (McNemar p = 0.008), and
referred 59 of 80 customers with a false belief (4 more were handed to a human without a report) against 80 of 80.
Different models; text, not speech; replies set by rule." "On 100 seeded FLEURS hi_in test clips, with NFC, lower-case
and punctuation removed, WER was: Prisma v2.5 verbatim 11.6, v3.0 12.2, Gemini 3 Flash 12.9, IndicWhisper 14.4,
Whisper large-v3 28.7; numbers are not converted; read speech, not calls." "How the text is normalised changes WER by
about 8 to 10 points for every system here; under the Whisper paper's normaliser, which also strips Devanagari vowel
signs, our Whisper large-v3 rerun gives 17.5, near OpenAI's published 17.0."

**Forbidden:** "Prisma is better (or worse) than Whisper / open models" in general; "open models don't have the Prisma
bug" or "only Prisma fails on skipped groups"; any open-model accuracy without "TTS audio, Hindi/Hinglish, frozen
59c12d9 parser, which cannot read transliterated English number words"; public-clip figures for IndicWhisper without
its train-split caveat; "validated" for any scheme; "Samajh beats generic LLM agents" (one model, one prompt; the
generic agent did better at a = 0.5); "a generic agent leaks loan details to relatives" (0 of 40); any (1, 0) figure
without "assuming customers agree to figures they can't recall"; "Samajh never names the lender to a third party" as
a general claim; "real customers", "speech" (Part C), a pooled rate, "mis-selling"; any figure called "FLEURS Hindi
WER" without "100 (or 250) of 417 clips"; "normalisation moves WER by 9 points" as one fixed number; "our Whisper rerun
is worse than published" or "inference setup explains the gap"; a direct comparison of our numbers with 17.0, 8.7 or
10.5-15.0; the 17.5 as a pre-declared result (it is a post-hoc sensitivity check).

## Independent checks
A fresh Opus checker that wrote no code recomputed every figure from the raw rows with its own scripts
(`scratchpad/final-check/recompute_a.py`, `recompute_c.py`): Part A 0 disagreements (every outcome count, all
McNemar tests, all schemes; audio hashes equal over 840 + 372 rows); Part C 0 disagreements over 568 calls and both
McNemar tests; Part B 0 disagreements (108 table rows, 120 cells and 15,900 per-utterance counts in
`results-b.json`; bootstrap endpoints within 0.31 points with another RNG; audio hashes equal over 500 keys; both
seeds reproduce the subset and the 100-clip sample). It read every Part A wrong amount and all 80 third-party calls and 40 sampled B0
calls by hand.
