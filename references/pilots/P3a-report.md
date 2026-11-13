# P3a report: decision chain v2

Builder, 2026-11-10. Took over from three cut-off workers; their committed work (types, tiers, checks, summary, extractor) was kept. Not yet independently verified. Synthetic text only, no speech. Tamil and Kannada not human-reviewed.

## Iteration 3, chain round 2: answers the customer clearly gave (after the first P5 run), 2026-11-13

**Why.** The first unscripted-customer run (P5, open arm, text, level 0) left 5 of 6 well-informed customers `incomplete`. The P5 worker traced six causes. They were fixed by principle: an answer the customer clearly gave is never thrown away, and `incomplete` is only for replies that cannot be used. Nobody in this lane opened a P5 file. Every example was written fresh: by the builder (Opus medium), and again by an independent verifier (Opus high) that wrote none of the code. The verifier ran one round and one recheck. A two-line fix after the recheck was not re-verified. All inputs are typed text, so nothing here is about speech or real callers. Verifier's report and addendum, unchanged: `references/reviews/iter3/verify-chain-r2.md`.

**What changed** (contract: `P3a-contract.md`, "P5 fix round" and "Round 2")
- **(A) Consent answer that gives only the method** (signature, OTP, app click, a yes on a call). The method is now a usable answer. Code, not the model, takes the "what" half from the customer's own naming of the product elsewhere in the same call. If the product was named nowhere, a matching method gives the new flag `consent_product_not_named`, tier `understanding_gap`. A different method still refers. None of this applies after a correction, a withdrawal, a take-back tail, a failed call or an ungrounded quote.
- **(F) "I said yes on the phone."** It is classed as `recorded_call` unless the customer says the call was not recorded. That case is `verbal`, which differs from the record and refers. The comparison with the record stays deterministic. No new consent method was added, because one would reshuffle the ops lane's seeded loan book.
- **(B) Provider choice.** "Nobody told me about another company" counts as a stated "no". On that question, a "no" followed only by a don't-know tail is kept even when the change check says `withdrawn`; this errs toward referral. "I don't know if it was required" is unchanged.
- **(C) Premium "free / zero / I paid nothing".** It is a stated 0 (`PremiumReply.free`, which code maps to 0). A new flag, `premium_said_zero`, refers whenever the record shows a premium. The 0 is not used when the same reply holds another figure, or names the loan, a bank, a deduction or another payer; those replies stay undecided.
- **(D) "The bank paid, I paid nothing."** This is the new `PaymentSource.not_charged`. The new flag `payment_says_not_charged` refers.
- **(E) Money back.**
  - Denials were never misread on either the builder's inputs or the verifier's.
  - The verifier found an older gap: an untimed belief that the money comes back recorded no claim, so the call ended `clear`.
  - The fix is a new `FeatureClaim.money_back`. No record holds it. Code treats it as true for a product with a deposit, any-time refund or after-period withdrawal feature (one table, `MONEY_BACK_VIA`).
  - Only the money-back question reads it. The screening schema is unchanged.
- **Exactness doubt.** "पक्का नहीं पता", "exact yaad nahi" and similar now set the hedge marker on a figure. The marker does not change the tier. Cover is left as it was, because there `hedged` is a tier input.
- **Pins.** The prompt pins for answer requests and wire schemas were reset on purpose. The change-check and screening requests and schemas are unchanged byte for byte. No record value for a field under test reaches the model. The verifier tested this with one call under two records that differ in every field: all 29 requests were byte-identical.

**Verified (verifier's counts, new typed calls)**
- Round 1, 123 calls: 42 of 42 informed replies across the six causes ended `clear`.
- Round 1, consent: 10 of 10 matching method-only consents were `clear`, and 9 of 9 with a different method referred.
- Round 1, premium and payment: 10 of 10 "free / zero" premiums with no payer word referred. 7 of 7 "paid by nobody" replies referred, and 6 of 6 "the bank paid from my loan" replies were `clear`.
- Round 1, mutations: 6 of 6 caught.
- Recheck, 54 calls, money back: 10 of 10 untimed money-back beliefs on insurance referred, and 7 of 7 on a product that does give money back were `clear`. 7 of 7 denials, double negatives included, were `clear`.
- Recheck, provider choice: 7 of 8 "nobody told me, don't know" replies referred and none ended `clear`.
- Recheck, mutations: 3 of 3 caught.
- Neither round found a call ending `clear` on a wrong or withdrawn belief that this round's code caused.

**Built, not verified.** A trailing filler after the don't-know tail ("नहीं कहा था पता नहीं जी") caused the 1 of 8 provider-choice miss; the fix now drops it. The Devanagari spellings of "exact" were added to the doubt list. Builder tests only.

**Frozen text-path set** (144 calls, final code, cache plus 46 paid re-reads of the changed prompts). 2 rows moved against the report before this round, both Tamil or Kannada (experimental): G01-ta consent method verbal → unclear, and G01-kn premium gap → 2,00,000. Both moves now match gold. Neither changed a tier or verdict. No Hindi or Hinglish row moved, and every headline and triage number is unchanged. The 7 rows that moved in this round's first run went back after the final re-reads; that is model reading-to-reading variation on the experimental languages. Reports: `eval/text_path/runs/frozen__openai-gpt-6-luna__before-p5fix.md`, `__p5fix-first.md`, `__p5fix-final.md`, `__p5fix-r2.md`.

**Cost.** $0.00214 → $0.00220 per transcript with nothing cached. LLM spend for the round was about $0.13 (builder about $0.08, verifier $0.046), with no Gnani calls.

**Tests.** `tests/core` + `tests/extract`: 2,738 passed. Whole suite: 2 failed, 8,489 passed, both in other lanes:
- **Server lane:** `tests/server/test_readings_fields.py::test_the_prepared_demo_call_asks_again_and_reads_back_the_right_figure`. Its fake model keys the premium output on `SpanReply`; it needs `PremiumReply` with `"free": false`, a one-line change.
- **P5 lane:** `tests/p5/test_p5_data_dir.py::test_run_refuses_on_the_given_directorys_frozen_file`. It passes when run alone, so it depends on test order.

**Still open**
- "Free" said next to the bank or the loan ("loan ke saath free mila tha") ends `incomplete`, not `refer`: 2 of 12 misled premium replies in round 1.
- An untimed money-back belief said in answer to any other question is not read.
- "मुझे नहीं पता था कि बाहर से भी ले सकते हैं" is read as don't know, so it ends `incomplete`.
- A figure with "nahi" in its own clause ("41300 sahi se nahi pata") is refused by the parser.
- One earlier probe, "41,300, actually, pakka nahi pata.", ends `clear` under one question wording. The verifier judged it a hedge, not a take-back; it now carries the hedge marker.
- Outside this lane:
  - `eval/p5/write_customers.py` builds its allowed set from `ConsentMethod` (unchanged, since no value was added).
  - Any P5 or ops scorer that lists `PaymentSource` or `FeatureClaim` values should learn `not_charged` and `money_back`.
  - The live dialogue may not read back a "free" premium. The rules refer without a read-back.

## Iteration 3 (chain), 2026-11-13

Two Opus-medium builders, one Opus-high verifier that wrote none of the code: one round on new inputs, one recheck of the fixes. A last small fix round after the recheck was not re-verified. All inputs are typed text. Nothing here is about speech or real callers. Verifier: `references/reviews/iter3/verify-chain.md`, report and addendum, unchanged.

**Which text the case file reads.** It reads the dialogue's own turn texts (`casefile.py` `do_transcript` → `call_transcript`). Prisma Batch is used only to align turns to the recording. On ordinary turns the text is v3.0 `transcribe`. On figure turns (premium, cover, read-backs) it is the v2.5 `transcribe` reading whenever v2.5 heard something (`samajh_dialogue.readings`). A carried premium comes from the open-recall turn, so it is v3.0 text.

**How often that text is one clause**, counted with the extractor's clause splitter (`eval/text_path/punctuation_rate.py`, cache only):
- v2.5 `transcribe`, public real-voice clips over six words: one clause in 246 of 246.
- v2.5 `transcribe`, Timbre clips over six words: one clause in 376 of 395.
- v3.0 `transcribe`, public real-voice clips over six words: two or more clauses in 104 of 248.
- v3.0 `transcribe`, Timbre clips over six words: two or more clauses in 26 of 392.

So the "640 of 640" in `prisma-punctuation-note.md` counts any punctuation mark, end-of-sentence full stops included. It does not count clause breaks, so that note overstates how often the change check could run. Figure-turn text is almost always one clause.

**What changed**
- *Change check* (`samajh/extract`). The check now also runs on a one-clause reply that holds a take-back word, not only on replies of two or more clauses. On a one-clause reply, a `withdrawn`, `corrected` or failed check makes the answer unusable (`incomplete`). A code rule needs no model: a one-clause reply ending in a "who knows / forgot / or something else" tail is unusable whatever the check said. It is exempt when an exactness word comes just before the tail ("ठीक से याद नहीं"). It is also exempt on non-amount questions when the reply names another detail ("बीमा है पता नहीं कितने का"). The carried premium follows the same rules. No prompt text changed. New sha256 tests pin the prompts and wire schemas, so an edit fails a test. The `ChangeReply` docstring still says "two or more clauses"; it is stale but pinned, and a code comment says so.
- *Amounts* (`samajh/amounts`, `samajh/rules/normalise.py`):
  - "sorry/सॉरी" refuses a figure only when a number follows it.
  - A bound ("X तक", "के अंदर", "up to X") is read as X and marked `bound`. The rules accept a bound figure for cover and the bot's read-back lines. They refuse it for the premium and never carry it.
  - A small count before a noun ("do kisht mein 41300", "do policy") is refused. "ek baar X" reads X, as in Devanagari.
  - Romanised Hindi number words 0–99 and the units are read ("bavan hazaar" → 52,000). A gate keeps everyday words (do, saath, das, tera, bara) from becoming numbers.

**Verified (verifier's counts)**
- Round 1: 23 of 23 withdrawals with a marker word were not `clear`. 19 of 19 informed replies where नहीं/nahi/no is the answer were `clear`. In 10 corrections away from the record, the taken-back value was never stated.
- Recheck:
  - A confirmed cover read-back on the bot's real line: 3 of 3 `clear`.
  - Bounded premiums: 7 of 7 not `clear`.
  - Romanised replies using saath/do/tera/bara/das as everyday words: the amount was read in 8 of 8.
  - Punctuated "…, कौन जाने।" withdrawals: 5 of 5 not `clear`.
  - Prompt pin: a one-character docstring edit failed 2 of 5 pin tests.

**Built, not verified (the last round answered the recheck's four items)**
- Before that round, 2 of 13 withdrawals ending in "या फिर कुछ और" were `clear`, and 9 of 13 informed one-clause replies were falsely made `incomplete`. The builder reran the verifier's own probes from the cache after the fix and reports 0 and 0. Those inputs were known to the builder, so this is not evidence.
- Romanised small counts before a noun are now refused; builder tests only.

**Frozen text-path set** (144 calls, cache only, final code). Every headline and triage number is identical to before this package. Hindi + Hinglish problem customers: 2 of 38 missed, 30 `refer`. Informed: 18 of 18 `clear`. All 144 rows are identical on tier, flags, gaps and fields. An earlier run in this package moved 3 Hindi cover fields ("तीन लाख तक का कवर है" refused). That regression showed up there and in the dialogue tests, and the bound/cover split fixed it. The fix was made on what the words mean, not tuned on the set, but the set did reveal the regression. Reports: `eval/text_path/runs/frozen__openai-gpt-6-luna__before-iter3.md`, `__iter3-first.md`, `__iter3-final.md`.

**Cost per call.** The change check ran 1,107 times before and 1,164 after (+57, every one said `none`). Cost with nothing cached went from $0.00210 to **$0.00214** per transcript ($0.30308 → $0.30774 for 144). LLM spend for the whole package was about $0.06, with no Gnani calls.

**Tests.** `uv run pytest tests/core tests/extract -q`: 2,631 passed. Whole suite: 4 failed, 7,281 passed, all in other lanes:
- 3 dialogue tests use "bavan hazaar" as an example the parser refuses; it is now read on purpose.
- 1 P5 test: new dialogue line keys are not mapped.

**Not done / still open**
- One-clause corrections, even toward the record, are now `incomplete`: 5 of 5 on the verifier's probe. This is the accepted cost.
- A withdrawal phrased with a word on no list still rests on one model reading.
- The tail rule covers one-clause replies only.
- "X और कुछ नहीं" after a recall figure is refused, as it was at HEAD.
- "do 50,000 ki FD" reads 50,000.
- No speech, no real callers, no Tamil or Kannada.
- The held-out amounts result stays scored at commit 59c12d9. It was not rescored.

## P3c: what a referral rests on (2026-11-10)

Status: built (Opus medium), then one narrow check by an Opus-high subagent that wrote none of it; its six defects were fixed in one pass and the fixes were confirmed by the coordinating worker only (tests, frozen comparison, demo), not by a second independent check. Synthetic text only, no speech.

A tag, not a tier. Every tier, verdict, flag and gap is unchanged: the raw results of all 144 frozen rows are byte-identical before and after (cache only, 4,498 of 4,498 LLM calls from the cache, 0 extractor errors), and `samajh.scenarios verify` passes.

**Class of every flag** (`FLAG_BASIS` beside `FLAG_TIER` in `samajh/types.py`; an import-time check and a test cover every `FlagReason`):

| rests on | flag reasons |
|---|---|
| the record alone (`record_only`) | `consent_no_record`, `funded_no_consent`, `bundled_not_mitigant`, `bundled_no_choice_on_record` |
| a customer statement (`customer_statement`) | all 34 others, including `answers_conflict` and `cancel_not_on_record` |

One exception: the two bundling reasons rest on a customer statement when the record does not mark the product as required and only the customer said it was. `checks.bundling` then sets `Flag.rests_on`; a result stored before the field existed is corrected on load from its `heard` text (`TOLD_REQUIRED_HEARD`).

**New names.** `Basis`, `FLAG_BASIS`, `Flag.rests_on` (stored, left out of dumps when unset), `Flag.basis`, `referral_basis(flags)`, and the derived properties `ProductResult.referral_basis` and `CaseResult.referral_basis` (`customer_statement` when at least one refer-tier flag rests on a customer statement, `record_only` when it is `refer` and none does, else None). Summary: `IssueLine.basis`, `CaseSummary.referral_basis`, `CaseSummary.first_line`. Ops: `Triage.referral_basis` and `first_line`; `ReferralSplit` beside every referral count in the views and the report (batch header, queue rows, case view, tiles, tier row, rule rows, decision rows, decided and supported, open, other, breakdowns), each validated to sum to its count. Contract: `P3a-contract.md` sections 1, 2 and 6.

**New strings.**
- Summary first line, record-only referrals only: "Referred on the lender's record alone; nothing the customer said is the reason for the referral."
- Labels: "On what the customer said", "On the record alone"; "Referred on what the customer said", "Referred on the record alone". Beside each count: "a on what the customer said · b on the record alone".
- Queue filter: "All referrals (n)", "On what the customer said (a)", "On the record alone (b)".
- Report note: "A referral on the record alone rests on the lender's own record (for example no consent on record) and on nothing the customer said. It is counted apart, so that the referrals on what the customer said describe the calls and not the lender's records. Either kind is a request for a person to look, and nothing more."
- Rules table note: "In this table the two counts are by rule: whether the lines under that rule rest on the record alone or on what the customer said. A call counted on the record alone under one rule may be referred on what the customer said under another."
- Case page notice for a record-only referral: "This call was referred so that a person can look at the lender's record for this loan. Nothing on this page is a conclusion about the sale. The decision is the reviewer's."
- Phone case card: "Refer to a reviewer, on the record alone. Call outcome: ..." (or "..., on what the customer said. ..."), with the first line above the issue lines.
- Demo and `run` output: "referred on what the customer said: A of N", "referred on the record alone: B of N".

**Counts.**
- Demo batch (scripted): 64 analysed, 7 referred: 7 on what the customer said, 0 on the record alone. The book produces no record-only referral, so the demo does not exercise that side.
- Frozen text set, Hindi and Hinglish (`eval/text_path/runs/frozen__openai-gpt-6-luna.md`, two new columns; no earlier number changed):

| kind of customer | calls (base cases) | referred | on what the customer said | on the record alone |
|---|---|---|---|---|
| problem | 38 (19) | 30 | 30 (15 base cases) | 0 |
| informed, record fault or boundary | 16 (8) | 8 | 6 (3 base cases: G03, V02, V03) | 2 (1 base case: W01) |
| informed, compliant record | 18 (9) | 0 | 0 | 0 |

Tamil and Kannada (experimental, not human-reviewed) split the same way: problem 14 and 15 of 19, all on what the customer said; informed with a fault 4 of 8 each, 3 and 1.

**This corrects the premise of the change.** The 8 of 16 informed customers referred are not all referred on the record: only W01 (no consent on record) is. G03 (the customer names another way of agreeing than the record's) and V02 and V03 (the customer says nobody told them of another provider) rest on what the customer said, so the split moves 2 of the 8, not 8.

**Tests.** `uv run pytest tests/core tests/extract tests/ops tests/server -q`: 3,084 passed, 1 deselected (core 2,027, extract 352, ops 312, server 393). Before P3c: 3,037 (1,993, 352, 306, 386).

**The check** recounted both sets from raw results with its own classification and no project classes, and agreed on every number and every split. It found: the first line could be false (it said the customer said nothing that conflicts, also when a differing premium ended as a gap); stored results lacked the bundling exception; the rules table split was unexplained; one decided/supported count had no split; the case page notice clashed with a record-only first line. All five were fixed. It also found a crash that predates P3c: `summarise` raised `KeyError` on a confirmed differing cover figure (`cover_differs_confirmed`, refer tier since the coordinator's decision), which failed the case file and ops triage for such a call. Fixed in `summary.py` with a test that every refer-tier reason has a summary line.

**Left.** The fixes after the check were not independently re-checked. No page was rendered after the fix pass (JavaScript syntax check only; the builder rendered the four pages once before it). `data/loanbook/README.md` is unchanged (it is generated by `samajh/ops/book.py`). `references/pilots/p3b-artifacts/` is stale. A `recall_not_named` flag can carry no quote and is still classed as a customer statement; it is never refer tier, so no count depends on it.

May say: referrals are given as two counts side by side; on the frozen text set 2 of 16 informed calls with a record fault (1 base case) were referred on the record alone and all 30 problem referrals rest on what the customer said. Must not say: that a record-only referral means the customer understood; any record-only rate as a fact about a lender.

## Fix round 3 (2026-11-10)

Status: built; independent verification: **sound with conditions** (`references/reviews/iter2/verify-P3a-r3.md`, an Opus-high verifier that wrote none of the code, on its own fresh inputs, 79 replies through the real extraction model). The r2 findings 1 to 3 are fixed on fresh inputs. The verifier found two new false-clear paths. One (the carried premium) was fixed afterwards; the other (a reply of one clause has no retraction protection) is open.

This round answers the findings of `references/reviews/iter2/verify-P3a-r2.md`. The r3 verifier's "May say" and "May not say" lists (below) replace the r2 lists for the items they cover and win over any builder wording here. All results are on typed synthetic text, not speech, and say nothing about real callers. The contract (`P3a-contract.md` §1, §3 to §6) describes the code as it now is.

| r2 finding or addition | state | r3 verifier, on fresh inputs |
|---|---|---|
| 1. Informed customers falsely referred by the retraction rule | fixed (phrase list removed; a second model reading, the change check, with code grounding) | kind, payment and required questions: 17 of 17 informed replies with emphasis, filler, an apology or a restatement ended `clear`. Premium: 1 of 3; the 2 holding "sorry"/"सॉरी" ended `incomplete` (the amounts lexicon reads "sorry" as doubt across the whole reply). Open |
| 1, other direction: a taken-back value must not be stated | holds for replies of two or more clauses; **fails for a reply of one clause** | corrections away from the record value: taken-back value stated in 0 of 19. Punctuated withdrawals: 0 of 6 ended `clear`. Unpunctuated withdrawals (one clause, no check): **4 of 10 ended `clear` with the withdrawn value stated**. Open |
| D. Correction inside one reply (option A) | built as decided | toward the record value, non-amount questions: 12 of 12 `clear`, earlier words kept in 9 of the 10 punctuated cases. A premium corrected inside one reply ends `incomplete` (two amounts in the reply) |
| 2. Cover read-back tier | fixed | 21 read-back orders and 12 comparisons: asking a read-back never lowered the tier. Premium orders: 10 of 10 |
| 3. Denial order | fixed | 8 of 8 (scripted). By the contract, the kind question answered as the kind on record still retracts a denial; a same-reply "took it, no, took nothing" ends `incomplete`, not `refer` |
| 4. Amounts holes | the listed holes are fixed; new ones found | 65 fresh sentences: 4 confident wrong figures ("पचास हज़ार तक।", "up to 40,000 rupees.", "do baar 20 hazaar kate.", and the arguable "पचास हज़ार हर महीने, बारह महीने।"); plain amounts 20 of 23 parsed. Open |
| 5. Surviving mutations | covered, `widen()` removed | 11 of 11 of the verifier's own mutations caught, each by exactly one test |
| A. Carried premium | built; the fault the verifier found was fixed after its run | before the fix: **4 of 4 recall replies that gave the figure and took it back ended `clear`**. After the fix: see "Recheck" below |
| B. "Maine 50,000 rupees…" | fixed (a regression from ff960f7) | digit figures inside Hindi and Hinglish sentences: 5 of 5 parsed |
| C. Summary wording | built | 5 cases and 6 labels: strings as specified, tier unchanged in all 5 |

Tests: `uv run pytest tests/core tests/extract -q` gives 2,345 passed (core 1,993, extract 352). At the r2 verification it was 1,959 (core 1,708, extract 251). These are the builders' tests, so they are not evidence that a fix holds.

Frozen set, before and after (`eval/text_path/runs/frozen__openai-gpt-6-luna.md`). It was run three times this round, never to choose anything: at 20:55 IST after the fixes; at 21:13 after the carried-premium fix; at 21:14 on the restored prompt (next paragraph). The first and third runs agree on every row, and every row is the same as before the round; only the run time and the cost section differ.

One thing the second run showed. A builder had corrected the docstring of `ChangeReply` (`samajh/extract/_wire.py`). That docstring is sent to the model as the schema's description, so the edit changed the change check's prompt and all 1,107 checks were asked again. One answered `withdrawn` where it had said `none`: G05-hi-en, the consent reply "Loan और insurance, दोनों के लिए हाँ बोली थी। कैसे... वो अब याद नहीं।". Fields went from 2,166 to 2,165 of 2,180; no verdict or tier moved. The docstring was restored to the exact text the verifier's 79 replies were measured on (the third run is 4,498 of 4,498 cache hits), and a code comment now says it is part of the prompt. What this measures: the change check's reading is sensitive to prompt wording, on 1 of 1,107 frozen replies for one rewording. The table is the first and third runs.

| measure (Hindi and Hinglish unless said) | before round 3 | after round 3 |
|---|---|---|
| call verdicts, all four languages | 143 of 144 (B03-ta wrong) | 143 of 144 (B03-ta wrong) |
| problem customers, misses | 2 of 38 calls (U07-hi, U07-hi-en) | 2 of 38 calls (the same two) |
| problem customers, tiers | refer 30, incomplete 6, understanding_gap 2 | the same |
| informed, compliant record: referred | 0 of 18 calls (18 clear) | 0 of 18 calls (18 clear) |
| informed, fault on the record: referred | 8 of 16 calls (incomplete 2, understanding_gap 6) | the same |
| extractor errors | 0 | 0 |
| LLM requests | 3,391 | 4,498 (1,107 change checks added) |
| cost with nothing cached | 0.211 USD (0.0015 per call) | 0.303 USD (0.0021 per call) |

The change check answered `none` on 1,095 of the 1,107 frozen-set replies it was asked about and was not used on 12 (a recall reply that named nothing). The frozen set holds no reply the check read as corrected or withdrawn, so the set says nothing about how well corrections are read: its unchanged numbers show only that the check did not disturb replies with no correction in them. The first rerun spent 0.031 USD and the second 0.031 USD (the re-asked checks); the rest came from the cache. The carried-premium fix moved nothing on either set.

Development set, before and after (in-sample for the prompt; 20 calls, 5 per language; `eval/text_path/runs/dev__openai-gpt-6-luna.md`). Before is the committed report, which was run at 11:07 IST, before fix rounds 1 and 2.

| measure | before (committed report) | after round 3 |
|---|---|---|
| call verdicts | 20 of 20 | 20 of 20 |
| false clear / false alarm | 0 of 13 / 0 of 7 | 0 of 13 / 0 of 7 |
| fields | 304 of 304 | 303 of 304 |
| LLM requests | 403 | 513 (110 change checks added) |

The change check said `corrected` on 5 development replies, `none` on 102, and was not used on 3. The calls with a correction that ended on the record's answer (hi-04 "डिपॉज़िट... अरे नहीं, बीमा है, बीमा।", kn-04) end `clear` with the earlier words kept. The one field that moved is Tamil (experimental): on ta-03 the term reply "ஒரு வருஷம்னு நினைக்கிறேன், சரியா தெரியலை." is now read as 12 months where the gold says unclear; the call's tier is unchanged (`refer`). This round's rules did not move it: the same model output through the committed normaliser gives the same reading, and the answer prompt is unchanged in this round. Which earlier change moved it was not established.

Verifier's wording (from `verify-P3a-r3.md`; it wins over anything else in this report).

May say:
- "On 17 typed informed replies with emphasis, filler, an apology or a restatement to the kind, payment and required questions, 17 ended `clear`."
- "On 19 typed corrections away from the record value, the taken-back value was never the stated belief."
- "On 6 punctuated withdrawals, none ended `clear`."
- "Across 21 cover read-back orders, asking a read-back never lowered the tier."
- "11 of 11 targeted mutations were caught."

May not say:
- "A retraction never yields a stated value." It is not true of the code: one-clause replies are unprotected (and the carried premium was, until the fix after the verifier's run). It is not true of the model either: 4 of 10 unpunctuated withdrawals ended `clear`.
- "An apology never makes an informed customer incomplete." It does in amount answers.
- "A correction to the record figure passes" for amounts.
- "Bounds ('up to', 'तक') and counts are refused."
- Any claim about speech, real callers, or a pooled rate.

Where the guarantee lives: in two model readings plus code grounding, for replies of two or more clauses, measured on one model and typed text. Code alone guarantees only that every quote is a whole clause of the reply and that the check can take an answer away but never supply one. For a reply of one clause there is no second reading.

Open, in the verifier's order (none fixed in this round except the first):
1. Fixed after the verifier's run: the carried premium now respects the recall reply's change check.
2. A reply of one clause has no retraction protection. Speech-to-text output often has no punctuation; how often Prisma's lacks it was not measured.
3. "सॉरी" and "sorry" count as doubt words across the whole reply, so an informed premium or cover answer with an apology about the line ends `incomplete`.
4. "तक" and "up to" bounds, and a romanised count before an amount ("do baar"), read as the plain figure.
5. Each guard is held by one test.

Recheck of the carried-premium fix by the same verifier, on fresh inputs, on the restored prompt (the addendum in `verify-P3a-r3.md`). Verdict unchanged, sound with conditions; finding 1 is fixed on fresh inputs.
- 13 of 13 recall replies that gave a premium and then took it back or replaced it (9 new, 4 seen by the builder) ended `incomplete`, with nothing carried.
- 8 of 8 informed recall replies with emphasis, filler or an apology still carried the premium and ended `clear`.
- The note line appeared exactly when there was a self-correction, with the tier unchanged (2 cases).
- A reply that corrects only the product and keeps the amount ("बीमा लिया था, नहीं, एफ़डी, इकतालीस हज़ार तीन सौ की।") ends `refer` with the premium not carried: safe, and a little information is lost.
- Two one-clause recall withdrawals ended `incomplete`, but through the amount parser's refusal, not the check: finding 2 stands.
- Under the briefly reworded docstring, "बीमा लिया था, इकतालीस हज़ार तीन सौ, अरे नहीं, वो तो लोन की किस्त थी।" got the check answer `none` and ended `clear` with the withdrawn premium; on the restored prompt it gets `withdrawn` and ends `incomplete`. One wording change flipped 1 of the verifier's 24 cases to a false clear.

The verifier adds to "May say": "On 13 typed recall replies that gave a premium and then took it back or replaced it, the premium was not carried and the case was not `clear` (13 of 13, gpt-6-luna, restored prompt)." and "On 8 typed informed recall replies with emphasis, filler or an apology, the premium was carried and the case ended `clear` (8 of 8)." It adds to "May not say": "the carried premium can never carry a withdrawn figure". Its new condition: the carried premium's protection rests on a single change-check reading, so any edit to the change-check prompt, the `ChangeReply` docstring included, must be followed by a rerun of the retraction probes (`references/reviews/iter2/probes/p3a_r3_llm*.py`, `p3a_r3_carry.py --llm`, `p3a_r3_carry2.py`).

**Retractions (r2 fix 1).** The phrase list (`retraction()`, `_RETRACTION` and `kept()` in `samajh/rules/normalise.py`) is removed. The extractor now makes a third request, the change check (`ChangeReply`, `Change` = none / corrected / withdrawn in `samajh/extract/_wire.py`), on every reply of two or more clauses to a checked question, open recall included. It sees the question and the reply, not the answer call's reading, and returns clause numbers only. Code grounds them as whole clauses and decides (`_Assembly.check`; open recall in `_Assembly._recall_check`, which drops the items said in the clauses taken back and lists the reply as unscreened). The protection therefore rests on two model readings plus code grounding, not on code alone. A reply of one clause gets no check, and a `RawExtraction` built by anything other than the extractor gets no retraction protection in `samajh.rules`. Tests: `tests/extract/test_extract_change.py`.

**Correction inside one reply (coordinator decision, option A).** The final answer stands when both model readings agree which clause holds it; the earlier words go into `Stated.also` and into the new additive field `ProductResult.self_corrections` (`samajh/types.py`, built by `samajh.rules.engine.self_corrections`), a note for the reviewer that is not part of the tier. No conflict flag is added. Disagreement on the clause, or a withdrawal with nothing in its place, makes the answer unusable (`incomplete`). Conflicts across two askings stay `refer`. On the scripted check outputs in the tests, 'बीमा... अरे नहीं, एफ़डी है' on an insurance record ends `refer` and 'डिपॉज़िट... अरे नहीं, बीमा है, बीमा' ends `clear`. The summary adds a note line per self-correction on every case, clear ones included; the line has tier `clear` and `note=True` and is never part of the case tier (`samajh/rules/summary.py`, `summarise`). Tests: `tests/extract/test_extract_change.py`, `tests/core/test_rules_summary.py`.

**Cover read-back (r2 fix 2).** In `samajh/rules/checks.py` `cover` and `samajh/rules/normalise.py` `_confirm`: a plain differing cover whose read-back is rejected without a correction, or mismatched, is now `incomplete`, so asking a read-back does not lower the tier against not asking it. A confirmed read-back followed by the same figure restated stays `refer`; hedged or unknown stays `understanding_gap`. A figure given as a correction at the read-back has had no read-back of its own and is judged as if none was asked, because the bot read back the customer's earlier figure, not the record's (stated in the `cover` docstring). The premium now gives a `readback_rejected` or `readback_mismatch` gap for a rejected or mismatched read-back, whatever the figure. Tests: `tests/core/test_core_normalise.py` (for example `test_a_plain_wrong_cover_is_never_lowered_by_its_read_back`, `test_a_cover_corrected_at_the_read_back_is_judged_as_a_figure_never_read_back`) and `test_the_cover_read_back_table` in `tests/core/test_rules_triage.py`.

**Denial order (r2 fix 3).** `recall` in `samajh/rules/checks.py`: a denial is retracted only by naming this product as the kind on record in a turn after the denial. A naming before it or in the same turn, a misdescription, an item with no kind, "don't know" or nothing asked leaves it standing (`refer`). The extractor keeps the last denial. A recall reply that names something and takes it back is handled by `_recall_check`. Tests: `test_a_denial_is_retracted_only_by_naming_the_kind_on_record_after_it` in `tests/core/test_rules_triage.py`; `tests/extract/test_extract_change.py` for the recall check.

**Amounts.** `samajh/amounts/_parse.py` and `_lexicon.py` now refuse by structure, not by a verb list: a comparison or bound anywhere in the amount's clause ("कम से कम", "at least", "minimum"); a number beside the amount that no duration, percent, clock, filler or count-of-the-next-word reading accounts for, including one touching the amount across a clause break; a misheard unit word ("तीन लक") anywhere in the text; and a small number after a thousand-or-larger unit word unless a currency word, a postposition (numbers other than one) or the end of the clause follows. After a hundreds word the number stays part of the amount ("तीन सौ एक दिए" is 301). Tests: `tests/core/test_amounts_structure.py`. Known cost, from rerunning the old probe `references/reviews/iter2/probes/p3a_r2_amounts.py` today: "one" 43 of 45 as the old verifier's gold accepts (two now refused that the gold read as 50,000: 'पचास हज़ार एक पॉलिसी के', 'पचास हज़ार एक बार'), fractions 51 of 51, ranges 29 of 30 ('डेढ़ से दो लाख' refused), 0 confident wrong figures. The builder saw those inputs, so this is a regression check, not evidence. The held-out amounts result (`data/amounts_v2`) stays scored at commit 59c12d9 and was not rescored.

**Why `parse_amount` rejected "Maine 50,000 rupees…" (addition B).** It was a regression, from commit ff960f7 (the structural fraction refusal), not from f79463e. Run against a copy of each commit: the sentence reads 50,000 at ff960f7~1 and is refused (`malformed`) at ff960f7 and at every commit after it. The cause: ff960f7 refuses a number when the word before it is within a small edit distance of a fraction word, and "maine" is that close to "paune" (पौने; the lexicon's own comment names this pair). The fix requires the two words to share their consonant frame as well (a misspelling changes vowels, not consonants), and adds a list of everyday words that are never refused. `test_an_ordinary_word_before_a_number_does_not_block_it` in `tests/core/test_amounts_structure.py` covers 42 such words before three amounts. A word that may be a fraction misspelt ("sare 3 lakh", "pone 2 lakh") stays refused. Separate and unchanged: an amount written in romanised Hindi number words ("maine pachaas hazaar diye") is refused, as it was before ff960f7; digits, Devanagari number words and English number words are read.

**`widen()` and the other surviving mutations (r2 fix 4).** `widen()` is removed from `normalise.py` as redundant: the whole reply must read to the same amount as the span, and the whole reply already holds every word next to the span (comment in `_read_amount`). Of the other four mutations that survived in r2: "सॉरी" and "sorry" removed from the retraction list target code that is gone (there is no phrase list). "A denial is dropped when any recall item exists" is covered by `test_a_denial_is_retracted_only_by_naming_the_kind_on_record_after_it` (`tests/core/test_rules_triage.py`; cases with an item before the denial, a misdescribed item and an item with no kind expect `recall_denied`). "Approximate tolerance ignored in the conflict rule" is covered by `test_two_premium_answers_conflict_only_beyond_their_tolerance` (`tests/extract/test_extract_carry.py`). The r3 verifier ran 11 mutations of its own and all 11 were caught, among them the approximate tolerance, the denial order and the kind-on-record filter; each was caught by exactly one test. The sub-orchestrator also ran six in a scratch copy (the denial dropped when any recall item exists, the tolerance, the order test, the kind filter, "both readings agree" dropped, the cover correction branch): all six failed a test. That second run is not independent.

**Carried premium (addition A).** `carried_premiums` in `normalise.py` and `_Assembly.carry` in the extractor (rule 3a of the `normalise` docstring): when the bot reads back a premium for a product it never asked the premium of, the open-recall reply whose whole text reads to the figure read back is accepted as the premium's quote, and nothing else is. With no such reply the premium is `Unclear(readback_mismatch)` with the read-back reply as evidence, not "not asked". The premium is carried only from a recall reply whose change check said `none`, or a one-clause reply, which gets no check; after a correction, a withdrawal, a failed check or a failed answer call on that reply nothing is carried and the premium is a gap. The independent verifier found this fault (4 of 4 real-model replies that gave the figure and then took it back ended `clear`); the fix (`_carries` in `_extract.py`) was then re-verified by the same verifier on fresh inputs: 13 of 13 such replies ended `incomplete` and 8 of 8 informed replies still carried (see "Recheck" above). The protection rests on one change-check reading. Tests: `tests/extract/test_extract_carry.py`.

**Summary wording** (`samajh/rules/summary.py`; no tier change). Questions never put: "the call did not get to: …", rendered "The call did not get to: …". A flag line with no customer quote: "(from the lender's record; no customer statement)". New `call_ended_label` with its table `CALL_ENDED`, one label per dialogue outcome; a call with no outcome or `in_progress` gives "Stopped before the call finished: the recording ends there (a hang-up or a dropped line)". Tests: `tests/core/test_rules_summary.py`.

**Old probes.** `references/reviews/iter2/probes/p3a_r2_chain.py`, `p3a_r2_llm.py` and `p3a_r2_mutate.py` no longer run as written: their scripted models do not answer the new `ChangeReply` request, and the mutation targets (the phrase list, `widen`) are gone. They were not edited.

Not verified:
- Anything on speech: every input, the verifier's included, is typed text. No real callers. Tamil and Kannada, and any model other than gpt-6-luna, were not checked.
- How often Prisma output lacks punctuation, which decides how much of a real call has no change check.
- Whether the P2 dialogue reads a premium back after a recall reply that withdrew it.
- The `refer` tier for a required-for-loan correction when the provider-choice question is also asked (the verifier's harness did not ask it).
- The self-correction note on clear cases and the restored `ChangeReply` docstring were changed after the verifier's main run; see the recheck above for what it covered.
- How often the change check reads a real correction or withdrawal right beyond the verifier's counts: no rate exists, and its reading moved on 1 of 1,107 frozen replies when the schema description was reworded.
- No native speaker judged the verifier's gold.
- Whether the two model readings disagree often on typed or spoken replies, which would turn usable answers `incomplete`.
- The amount refusals on speech-to-text output, and their cost on held-out text (the probe rerun above uses inputs the builder saw).
- Any behaviour on speech or with real callers.

## 1. What changed in this pass

| Path | Change |
|---|---|
| `samajh/amounts/_approx.py` (new), `__init__.py` | `Approximate`, `parse_approx_amount`, `has_doubt_word`, `is_loan_tenure`, as in `P3a-contract.md` §4. A hedge ("करीब", "शायद", "के आसपास", "I think") or a narrow range ("पचास बावन हज़ार", "50-52 hazaar", "50,000 से 52,000", "एक से डेढ़ लाख") reads as (low, high). Stays refused: corrections, a negator or comparison in the same clause, "और"/"and", three ends, high more than twice low, mixed forms, restarts, romanised number words, misspelt fraction or unit words. Hindi, Hinglish and English doubt words only |
| `samajh/rules/normalise.py` | `to_beliefs` now passes on payment frequency, conflicts, the recall denial and unscreened replies, each only where its quote is in the call (otherwise an evidence gap). Amounts go through `parse_approx_amount` and carry `hedged`, `approximate` and `low`. A read-back confirms a range only when the bot line has the same two ends. "जब तक लोन चलेगा" is the record's `tenure_months`, or a `not_comparable` gap when the record has none |
| `samajh/rules/checks.py` | A premium with no read-back now quotes the customer's amount in its gap |
| `tests/extract/extractkit.py`, tests | Recorded outputs that predate `took_nothing` replay it as false. Tests from before the change that assumed the old behaviour (trimming, one failure fails the whole call, "दो तीन लाख" refused, timing in `run_text` equality) were rewritten to the new contract |

From the earlier workers and kept unchanged: the `Tier` type and `tier_of`, `FLAG_TIER`, the conflict flags, `summarise`, the misspelt-fraction refusal in `parse_amount`, the extractor (parallel requests, field-level `extraction_failed`, kept conflicts, the payment-frequency question `Question.payment_frequency`, `took_nothing`, no trimming), and the text-path triage scorer.

## 2. Evidence

```
$ uv run pytest tests/core tests/extract tests/scenarios -q
1954 passed in 12.99s          # core 1662, extract 242, scenarios 50
$ uv run ruff check samajh/types.py samajh/rules samajh/amounts samajh/extract samajh/pipeline.py tests/core tests/extract eval/text_path
All checks passed!
```

Verifier probes (run from `references/reviews/iter1/probes/`; the extractor probe from a copy that adds `"took_nothing": false` to its scripted recall outputs, because the field is now required):
- `extractor_attacks.py` case 10 (FD, then "बीमा" after a re-ask): was `clear`, now `flag_for_review` with a kind flag. Case 11 (cash, then "from the loan"): now flagged. Case 12 ("सारे तीन लाख"): was `clear`, now `value_not_parsed` gap. The probe's printed commentary is static and still describes the old behaviour.
- `amounts_fresh.py`: ordinary shapes 174 of 176 right, 2 refused (unchanged); shapes left by the builders 8 wrong (was 9: the romanised fraction is now refused), 45 refused.
- `engine_adversarial.py`: 104 cases, 5 differ from the verifier's reading, 4 of them the false clears of verifier findings 1 and 10 (not in this package; see §4).

## 3. Numbers

**Frozen set, one rerun** (version 3, 144 scripted calls, `openai/gpt-6-luna`; never tuned on). 3,391 requests, 2,733 from the cache, 0.053 USD. Groups come from the set's customer labels; a miss is a customer with a problem ending `clear` or `understanding_gap`. Wilson 95% intervals.

| Hindi + Hinglish (72 calls, 36 base cases) | calls | base cases |
|---|---|---|
| Customers with a problem: misses | 4 of 38 (11 per 100; 4 to 24) | 2 of 19 (3 to 31) |
| ... their tiers | refer 30, incomplete 4, understanding_gap 4 | |
| Informed, compliant record: referrals | 0 of 18 (0 to 18); all 18 `clear` | 0 of 9 |
| Informed, a fault on the record: referrals | 8 of 16 (refer 8, incomplete 2, understanding_gap 6) | 4 of 8 |

- The 2 missed base cases are U06 (told cover ₹10 lakh, record ₹3 lakh) and U07 (told 15 days to cancel, record 30). Both are wrong beliefs about cover and the cancellation window, which the contract's tier table puts in `understanding_gap`. The rule engine on the set's own extraction misses the same 4 calls, so the cause is the tier table, not the extractor. Whether a wrong figure (not "I don't know") for cover or the window should be `refer` is a coordinator decision. It must not be changed because of this run.
- Tamil (experimental): misses 3 of 19 (B03 false clear, U06, U07). Kannada (experimental): 2 of 19. Referrals of informed customers on a compliant record: 0 of 9 each.
- Strict verdicts: 143 of 144 from the cache (B03-ta, the iteration-1 false clear: needs the payment-frequency question in the dialogue). Fields 2,163 of 2,180. The live pass gave 142 of 144: U04-ta's cover request was sent twice at the same time, the two live answers differed, and the cache kept the second. The live pass is in `eval/text_path/runs/p3a__frozen-live-pass.md`, the cached rerun in `frozen__openai-gpt-6-luna.md`. Hindi and Hinglish rows are identical in both. The iteration-1 report is in `runs/iter1/`.
- A regression from dropping trimming: U07-hi's cover span came back "तीन लाख तक" and is now refused (`value_not_parsed`). Before, `tighten` cut it to "तीन लाख". It changes no tier.

**The judge's three typed transcripts** (`references/reviews/iter1/judge-probes/`, compliant record), run with `eval/text_path/run_transcript.py`:

| Transcript | Tier | Before (iteration 1) |
|---|---|---|
| misled Hinglish | `refer`: 6 flags and 6 gaps, merged into 4 summary lines (FD; guaranteed return and withdrawal; premium, consent, payment and bundling undecided; term, cover and window) | 11 flags |
| informed Hindi (b) | `clear` | clear |
| ordinary informed Hindi | `incomplete`: premium range read (₹50,000 to ₹52,000) but never read back, because the iteration-1 dialogue made no read-back; the window "don't know", cover with no figure and term `not_comparable` are `understanding_gap` | `flag_for_review`, 1 flag and 4 gaps |

The ordinary customer is no longer a referral. With a read-back of the range added and `tenure_months: 24` on the record (my variant, in the scratchpad), the call is `understanding_gap`. The misled customer's "bavan hazaar" is romanised and still refused: romanised Hindi amounts are out of scope.

Spend: OpenRouter 0.053 USD in this pass (ledger 0.5763 to 0.6297 USD, all chat rows). No Gnani calls.

## 4. Left open

- Verifier findings 10 (three silent passes in the engine) and 8 (50,002, 1,00,020): not in this package.
- `extractor_attacks.py` case 6 ("…, ऐसा तो नहीं था" negating in the next clause) still ends `clear` when the model says stated. (Superseded by fix round 3: a reply of two or more clauses now gets the change check; not rerun.)
- Finding 1 needs the dialogue to tag a bot turn `asks=payment_frequency`. The extraction field and the rule exist.
- Trimming: an allow-list of harmless words to the right of a number ("तक", "का", "कटे") would recover U07-hi. Design it on the development set and measure it on a fresh set, not on this one.
- Concurrent identical requests in one run can get two different live answers (U04-ta). The fix belongs in the LLM client (single-flight per cache key), which is outside these paths.
- The probe scripts need `"took_nothing": false` in their scripted `RecallReply` outputs.
- No independent review yet.

## 5. Document lines made stale

- `ORCHESTRATION.md:77` "1,223 core tests pass": now 1,662. `:81` "176 tests pass (`tests/extract/`)": now 242.
- `README.md:12` "1,223 core tests pass": now 1,662. `README.md:16` "176 extractor tests": now 242.
- `CLAUDE.md:71` "Tests: `tests/extract/` (176 …)": now 242. The `samajh/extract/` entry should add that one failed model call makes only its own fields `Unclear(extraction_failed)` and that spans are never trimmed.
- `DESIGN.md:222` "Any product with a flag → `flag_for_review`": verdicts stay for gold, and triage now reads `Tier` (`refer`, `incomplete`, `understanding_gap`, `clear`; table in `references/pilots/P3a-contract.md` §1).
- `DESIGN.md:405` "Hedged amounts and two amounts in one reply are not taken": the parser now reads hedged amounts and narrow ranges (`parse_approx_amount`). The dialogue side belongs to P2.
- `DESIGN.md:461` (open item 23): decided. One bad output makes only that field `unclear`.
- `references/pilots/W5-extractor-report.md:442` "One invalid output fails the whole call": superseded.

## 6. Second pass: the iteration-2 verifier's faults (2026-11-10)

| # | Fix | Evidence (probes under `references/reviews/iter2/probes/`) |
|---|---|---|
| 1 | A failed model call on any asking of a question makes its fields `Unclear(extraction_failed)` | `p3a_extractor.py` cases 2 and 3: were `clear`, now `incomplete` |
| 2 | A conflict is two stated, incompatible answers. "I don't know" before or after an answer, a restatement, an approximate figure and an exact one inside it, and amounts within tolerance (1%, or 10% when either is hedged or a range) are not. The other replies are kept in the new `Stated.also` | tests in `tests/extract/test_extract_answers.py` |
| 3 | Every open-recall reply counts and a denial in any of them stays; `recall_denied` is refer whatever follows (superseded by the third pass and fix round 3: retracted by a later naming as the kind on record) | cases 11 and 12: were `understanding_gap`, now `refer` |
| 4 | Fraction and multiplier words: an edit distance on a reduced form of the word (`samajh/amounts/_lexicon.py`), not a list of spellings, with a short list of everyday words (`ORDINARY`). Normalisation reads the span with one more word on each side within its clause (`samajh.rules.normalise.widen`). Span, widened span and whole reply must all read the same. (Superseded by fix round 3: `widen` is removed; span and whole reply must read the same) | sweep `p3a_fraction_sweep.py`: Devanagari 54 wrong, 24 refused, 30 right → 0 wrong, 78 refused, 30 right; Latin 1,095 wrong, 327 refused → 0 wrong, 1,422 refused. Distinct spellings dropped: Devanagari 0 of 36, Latin 0 of 474 |
| 5 | "तीन लाख तक", "चौबीस हज़ार रुपये लगे" read again | B02-hi, R01-hi, U07-hi: no gap |
| 6 | One bound on range width (`samajh.amounts.MAX_RANGE_RATIO = 2`): the parser refuses wider ranges and the rules never pass one (`not_comparable` gap) | tests in `tests/core/test_rules_triage.py` |
| 7 | Summary: one line per rule for incomplete and understanding-gap lines; "did not know", "gave a different figure" and "left undecided" are separate titles | judge's misled call: 2 refer lines, 4 incomplete, 3 understanding |
| 8 | `LlmClient` holds a per-cache-key file lock: one request per key at a time across threads and processes; waiters read the cache | `tests/clients/test_llm_single_flight.py` (8 callers, 2 clients, a transport that answers each request differently: 1 request) |
| 9 | Cover read-back (coordinator decision), `cover_differs_confirmed` / `cover_differs_unconfirmed` | `p3a_tier_attacks.py`: 48 cases, the 1 outside the verifier's reading is this decision |

Frozen set, Hindi + Hinglish, from the cache (0 USD, 3,391 requests, all cache hits):
- Customers with a problem: misses 4 of 38 calls (2 of 19 base cases) → 2 of 38 (1 of 19: U07, wrong cancellation window, still `understanding_gap` by design). U06 (wrong cover, not read back) is now `incomplete`.
- Informed, compliant record: referrals 0 of 18 → 0 of 18.
- Informed, fault on the record: referrals 8 of 16 → 10 of 16. The two new ones are R01 (an informed customer who says "only the loan" in recall, then names the insurance): the denial rule of item 3.
- Strict verdicts 143 of 144; fields 2,166 of 2,180 (was 2,163: U07-hi's cover reads again).

## 7. Third pass (2026-11-10)

- **Retraction in a later clause** (superseded by fix round 3: the phrase list and `retraction` are removed; the extractor's change check decides, see above) (`samajh.rules.normalise.retraction`, Hindi, Hinglish, English): the stated value from the earlier clause is dropped (`no_usable_answer` gap); a different answer after the retraction adds an `answers_conflict`. Probe cases 9 and 10 were `clear`, now `incomplete`. A "नहीं" that opens the reply, or that is part of the answer, is not a retraction.
- **Denial retracted by naming** (fix round 3 adds order: only a naming in a turn after the denial counts, and a misdescribed item no longer does): `recall_denied` (refer) only while the denial stands; naming the product as the kind on record later makes it `recall_not_named` with both quotes. Probe cases 11 and 12 now end `understanding_gap`: in both the customer names insurance at the kind question, which is the record's kind. A later FD, "don't know" or no question keeps it `refer` (tests in `tests/core/test_rules_triage.py`).
- Frozen set, Hindi + Hinglish, from the cache: problem misses 2 of 38 calls (1 of 19 base cases); informed on a compliant record 0 of 18 referred; informed with a record fault 8 of 16 referred (R01 is back to `understanding_gap`). Verdicts 143 of 144, fields 2,166 of 2,180: the retraction rule changed no frozen call.

- **"तीन सौ एक दिए"** (dialogue verifier): a "one" after a hundreds word is part of the number (301); after a thousand-or-larger unit and before a verb ("पचास हज़ार एक दिए", "50 thousand one paid") the parse is ambiguous, never the smaller figure; before a noun it is still a determiner ("पचास हज़ार एक FD" = 50,000). The frozen numbers do not change. (Partly superseded by fix round 3: after a thousand-or-larger unit, "one" before a noun is now refused too; `parse_amount("पचास हज़ार एक FD")` gives `Ambiguous(malformed)`.)
