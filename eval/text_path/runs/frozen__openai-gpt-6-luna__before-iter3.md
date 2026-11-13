# Text path on the `frozen` set, model `openai/gpt-6-luna`

Run at 2026-11-10T16:48:39+00:00. Frozen set version 3 of 2026-11-10: 144 scripted calls (sha256 gold.jsonl 14e49b58929c, calls.jsonl b10111dfc64e). Synthetic, templated text, no speech-to-text, Tamil and Kannada not human-reviewed. Verdicts and flags are scored against the hand-written gold; fields against the set's perfect extraction. Not used for prompt or model selection.

## Headline

| group | calls | false clear | false alarm | call verdict | product verdict | fields |
|---|---|---|---|---|---|---|
| all | 144 | 0.9% (1/108) | 0.0% (0/36) | 99.3% (143/144) | 99.3% (143/144) | 99.4% (2166/2180) |
| hi | 36 | 0.0% (0/27) | 0.0% (0/9) | 100.0% (36/36) | 100.0% (36/36) | 99.6% (543/545) |
| hi-en | 36 | 0.0% (0/27) | 0.0% (0/9) | 100.0% (36/36) | 100.0% (36/36) | 99.6% (543/545) |
| ta | 36 | 3.7% (1/27) | 0.0% (0/9) | 97.2% (35/36) | 97.2% (35/36) | 98.9% (539/545) |
| kn | 36 | 0.0% (0/27) | 0.0% (0/9) | 100.0% (36/36) | 100.0% (36/36) | 99.3% (541/545) |
| gold extraction, no LLM | 144 | 0.0% (0/108) | 0.0% (0/36) | 100.0% (144/144) | 100.0% (144/144) | - |

False clear: gold is flag_for_review or unclear_needs_human and the pipeline says clear (n = calls whose gold is not clear). False alarm: gold is clear and the pipeline does not say clear (n = calls whose gold is clear). Extractor errors: 0. Last row: the rule engine on the set's gold extraction, so any miss there is not the extractor's.

## Triage: where each kind of customer ended up

| group | languages | calls (base cases) | tiers | misses, calls | misses, base cases | referrals, calls | referrals, base cases | referred on what the customer said, calls | referred on the record alone, calls | misses on the set's own extraction, calls |
|---|---|---|---|---|---|---|---|---|---|---|
| problem | hi + hi-en | 38 (19) | refer 30, incomplete 6, understanding_gap 2 | 5 per 100 (2/38; 95% 1 to 17) | 5 per 100 (1/19; 95% 1 to 25) | 79 per 100 (30/38; 95% 64 to 89) | 79 per 100 (15/19; 95% 57 to 91) | 30/38 (15/19) | 0/38 (0/19) | 5 per 100 (2/38; 95% 1 to 17) |
| problem | hi | 19 (19) | refer 15, incomplete 3, understanding_gap 1 | 5 per 100 (1/19; 95% 1 to 25) | 5 per 100 (1/19; 95% 1 to 25) | 79 per 100 (15/19; 95% 57 to 91) | 79 per 100 (15/19; 95% 57 to 91) | 15/19 (15/19) | 0/19 (0/19) | 5 per 100 (1/19; 95% 1 to 25) |
| problem | hi-en | 19 (19) | refer 15, incomplete 3, understanding_gap 1 | 5 per 100 (1/19; 95% 1 to 25) | 5 per 100 (1/19; 95% 1 to 25) | 79 per 100 (15/19; 95% 57 to 91) | 79 per 100 (15/19; 95% 57 to 91) | 15/19 (15/19) | 0/19 (0/19) | 5 per 100 (1/19; 95% 1 to 25) |
| problem | ta (experimental) | 19 (19) | refer 14, incomplete 3, understanding_gap 1, clear 1 | 11 per 100 (2/19; 95% 3 to 31) | 11 per 100 (2/19; 95% 3 to 31) | 74 per 100 (14/19; 95% 51 to 88) | 74 per 100 (14/19; 95% 51 to 88) | 14/19 (14/19) | 0/19 (0/19) | 5 per 100 (1/19; 95% 1 to 25) |
| problem | kn (experimental) | 19 (19) | refer 15, incomplete 3, understanding_gap 1 | 5 per 100 (1/19; 95% 1 to 25) | 5 per 100 (1/19; 95% 1 to 25) | 79 per 100 (15/19; 95% 57 to 91) | 79 per 100 (15/19; 95% 57 to 91) | 15/19 (15/19) | 0/19 (0/19) | 5 per 100 (1/19; 95% 1 to 25) |
| informed_clear | hi + hi-en | 18 (9) | clear 18 | 100 per 100 (18/18; 95% 82 to 100) | 100 per 100 (9/9; 95% 70 to 100) | 0 per 100 (0/18; 95% 0 to 18) | 0 per 100 (0/9; 95% 0 to 30) | 0/18 (0/9) | 0/18 (0/9) | 100 per 100 (18/18; 95% 82 to 100) |
| informed_clear | hi | 9 (9) | clear 9 | 100 per 100 (9/9; 95% 70 to 100) | 100 per 100 (9/9; 95% 70 to 100) | 0 per 100 (0/9; 95% 0 to 30) | 0 per 100 (0/9; 95% 0 to 30) | 0/9 (0/9) | 0/9 (0/9) | 100 per 100 (9/9; 95% 70 to 100) |
| informed_clear | hi-en | 9 (9) | clear 9 | 100 per 100 (9/9; 95% 70 to 100) | 100 per 100 (9/9; 95% 70 to 100) | 0 per 100 (0/9; 95% 0 to 30) | 0 per 100 (0/9; 95% 0 to 30) | 0/9 (0/9) | 0/9 (0/9) | 100 per 100 (9/9; 95% 70 to 100) |
| informed_clear | ta (experimental) | 9 (9) | clear 9 | 100 per 100 (9/9; 95% 70 to 100) | 100 per 100 (9/9; 95% 70 to 100) | 0 per 100 (0/9; 95% 0 to 30) | 0 per 100 (0/9; 95% 0 to 30) | 0/9 (0/9) | 0/9 (0/9) | 100 per 100 (9/9; 95% 70 to 100) |
| informed_clear | kn (experimental) | 9 (9) | clear 9 | 100 per 100 (9/9; 95% 70 to 100) | 100 per 100 (9/9; 95% 70 to 100) | 0 per 100 (0/9; 95% 0 to 30) | 0 per 100 (0/9; 95% 0 to 30) | 0/9 (0/9) | 0/9 (0/9) | 100 per 100 (9/9; 95% 70 to 100) |
| informed_flagged | hi + hi-en | 16 (8) | refer 8, incomplete 2, understanding_gap 6 | 38 per 100 (6/16; 95% 18 to 61) | 38 per 100 (3/8; 95% 14 to 69) | 50 per 100 (8/16; 95% 28 to 72) | 50 per 100 (4/8; 95% 22 to 78) | 6/16 (3/8) | 2/16 (1/8) | 38 per 100 (6/16; 95% 18 to 61) |
| informed_flagged | hi | 8 (8) | refer 4, incomplete 1, understanding_gap 3 | 38 per 100 (3/8; 95% 14 to 69) | 38 per 100 (3/8; 95% 14 to 69) | 50 per 100 (4/8; 95% 22 to 78) | 50 per 100 (4/8; 95% 22 to 78) | 3/8 (3/8) | 1/8 (1/8) | 38 per 100 (3/8; 95% 14 to 69) |
| informed_flagged | hi-en | 8 (8) | refer 4, incomplete 1, understanding_gap 3 | 38 per 100 (3/8; 95% 14 to 69) | 38 per 100 (3/8; 95% 14 to 69) | 50 per 100 (4/8; 95% 22 to 78) | 50 per 100 (4/8; 95% 22 to 78) | 3/8 (3/8) | 1/8 (1/8) | 38 per 100 (3/8; 95% 14 to 69) |
| informed_flagged | ta (experimental) | 8 (8) | refer 4, incomplete 1, understanding_gap 3 | 38 per 100 (3/8; 95% 14 to 69) | 38 per 100 (3/8; 95% 14 to 69) | 50 per 100 (4/8; 95% 22 to 78) | 50 per 100 (4/8; 95% 22 to 78) | 3/8 (3/8) | 1/8 (1/8) | 38 per 100 (3/8; 95% 14 to 69) |
| informed_flagged | kn (experimental) | 8 (8) | refer 4, incomplete 1, understanding_gap 3 | 38 per 100 (3/8; 95% 14 to 69) | 38 per 100 (3/8; 95% 14 to 69) | 50 per 100 (4/8; 95% 22 to 78) | 50 per 100 (4/8; 95% 22 to 78) | 3/8 (3/8) | 1/8 (1/8) | 38 per 100 (3/8; 95% 14 to 69) |

Misses (a customer with a problem ends `clear` or `understanding_gap`): 5.
- U07-hi: tier `understanding_gap`
  - understanding_gap: Customer gave a different figure for the cancellation window (customer said it can be cancelled within 15 days). | record: cancellation window 30 days | quote: "बताया था, पंद्रह दिन का टाइम होता है कैंसल करने का।"
- U07-hi-en: tier `understanding_gap`
  - understanding_gap: Customer gave a different figure for the cancellation window (customer said it can be cancelled within 15 days). | record: cancellation window 30 days | quote: "हाँ, बोला था fifteen days के अंदर cancel कर सकते हैं।"
- U07-ta: tier `understanding_gap`
  - understanding_gap: Customer gave a different figure for the cancellation window (customer said it can be cancelled within 15 days). | record: cancellation window 30 days | quote: "ஆமா, பதினைந்து நாள் டைம் இருக்கு, அதுக்குள்ள கேன்சல் பண்ணலாம்னு சொன்னாங்க."
- U07-kn: tier `understanding_gap`
  - understanding_gap: Customer gave a different figure for the cancellation window (customer said it can be cancelled within 15 days). | record: cancellation window 30 days | quote: "ಹೌದು, ಹದಿನೈದು ದಿನ ಟೈಮ್ ಇದೆ, ಅಷ್ಟರೊಳಗೆ ಕ್ಯಾನ್ಸಲ್ ಮಾಡಬಹುದು ಅಂತ ಹೇಳಿದ್ರು."
- B03-ta: tier `clear`

False referrals (an informed customer on a compliant record ends `refer`): 0.

A miss is counted only for customers the set labels misled, unaware or did not agree. `incomplete` is not a miss and not a referral: the call did not yield enough to decide. The last column runs the rule engine on the set's own extraction, so a miss there is the rules', not the extractor's. Base cases, not calls, are the independent unit. A referral on the record alone rests only on the lender's record (for example no consent on record) and on nothing the customer said; a referral on what the customer said has at least one refer-tier flag that rests on the customer's words (counts of the group's calls, base cases in brackets).

## Verdicts, gold against pipeline (all calls)

| gold | pipeline | calls |
|---|---|---|
| clear | clear | 36 |
| flag_for_review | clear | 1 |
| flag_for_review | flag_for_review | 99 |
| unclear_needs_human | unclear_needs_human | 8 |

## Tiers by gold verdict (all calls)

| gold verdict | pipeline tier | calls |
|---|---|---|
| clear | clear | 36 |
| flag_for_review | clear | 1 |
| flag_for_review | incomplete | 8 |
| flag_for_review | refer | 75 |
| flag_for_review | understanding_gap | 16 |
| unclear_needs_human | incomplete | 8 |

## Extraction accuracy per field

| field | all | hi | hi-en | ta | kn |
|---|---|---|---|---|---|
| kind | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |
| premium_inr | 99.3% (143/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 97.2% (35/36) |
| premium_readback | 100.0% (132/132) | 100.0% (33/33) | 100.0% (33/33) | 100.0% (33/33) | 100.0% (33/33) |
| payment_source | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |
| required_for_loan | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |
| provider_choice_offered | 100.0% (32/32) | 100.0% (8/8) | 100.0% (8/8) | 100.0% (8/8) | 100.0% (8/8) |
| cover_inr | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |
| term_months | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |
| cancel_allowed | 99.3% (143/144) | 100.0% (36/36) | 100.0% (36/36) | 97.2% (35/36) | 100.0% (36/36) |
| cancel_window_days | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |
| feature_probe | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |
| consent_given | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |
| consent_method | 93.8% (135/144) | 94.4% (34/36) | 94.4% (34/36) | 91.7% (33/36) | 94.4% (34/36) |
| recall_items | 98.6% (142/144) | 100.0% (36/36) | 100.0% (36/36) | 97.2% (35/36) | 97.2% (35/36) |
| volunteered_claims | 99.3% (143/144) | 100.0% (36/36) | 100.0% (36/36) | 97.2% (35/36) | 100.0% (36/36) |
| sale_concerns | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |

## Flags per rule: precision and recall

| rule | all P | hi P | hi-en P | ta P | kn P | all R | hi R | hi-en R | ta R | kn R |
|---|---|---|---|---|---|---|---|---|---|---|
| kind | 100.0% (28/28) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (28/28) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) |
| premium | 100.0% (16/16) | 100.0% (4/4) | 100.0% (4/4) | 100.0% (4/4) | 100.0% (4/4) | 100.0% (16/16) | 100.0% (4/4) | 100.0% (4/4) | 100.0% (4/4) | 100.0% (4/4) |
| cover | 100.0% (36/36) | 100.0% (9/9) | 100.0% (9/9) | 100.0% (9/9) | 100.0% (9/9) | 100.0% (36/36) | 100.0% (9/9) | 100.0% (9/9) | 100.0% (9/9) | 100.0% (9/9) |
| term | 100.0% (24/24) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (24/24) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) |
| cancel_window | 100.0% (31/31) | 100.0% (8/8) | 100.0% (8/8) | 100.0% (7/7) | 100.0% (8/8) | 96.9% (31/32) | 100.0% (8/8) | 100.0% (8/8) | 87.5% (7/8) | 100.0% (8/8) |
| recall | 85.7% (12/14) | 100.0% (3/3) | 100.0% (3/3) | 75.0% (3/4) | 75.0% (3/4) | 100.0% (12/12) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (3/3) |
| consent | 100.0% (28/28) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (28/28) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) |
| loan_funded | 100.0% (24/24) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (24/24) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) |
| bundling | 100.0% (28/28) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (28/28) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) |
| belief_mismatch | 100.0% (43/43) | 100.0% (11/11) | 100.0% (11/11) | 100.0% (10/10) | 100.0% (11/11) | 97.7% (43/44) | 100.0% (11/11) | 100.0% (11/11) | 90.9% (10/11) | 100.0% (11/11) |
| sale_conduct | 100.0% (12/12) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (12/12) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (3/3) |
| all rules | 99.3% (282/284) | 100.0% (71/71) | 100.0% (71/71) | 98.6% (69/70) | 98.6% (71/72) | 99.3% (282/284) | 100.0% (71/71) | 100.0% (71/71) | 97.2% (69/71) | 100.0% (71/71) |

## Spans and grounding

- Spans the model copied (amounts, durations, recall items, claims, concerns) that were not in the reply: 0 of 802 (0.00%). By field: none.
- Answers whose clause numbers were missing or out of range: 0 of 1196 (0.00%). By field: none.
- Both kinds are dropped to `unclear` (answers) or left for the rule engine to record as an evidence gap (recall items, claims, concerns). None is kept as an answer.
- Answers marked stated with no value or no span, kept as unclear: 0. By field: none.
- Gaps the rule engine raised with reason `quote_not_grounded`: 0 (with the gold extraction: 0).
- Gaps with reason `value_not_parsed`: 0 (with the gold extraction: 0).
- Record values found in bot turns shown to the model: premium in a `readback` question: 120. A lexical check of the premium, cover, sanctioned and disbursed amounts (digits and spoken form) and the provider name. A read-back repeats the amount the customer said, so it shows the record's premium whenever the customer's amount equals it. The two identity checks are never sent.

## Cost and latency

- LLM calls: 4498 for 144 calls (4498 served from the cache in this run).

| request | LLM calls | cost with nothing cached |
|---|---|---|
| answer | 1604 | $0.13418 |
| screen | 1787 | $0.07719 |
| check | 1107 | $0.09171 |

- The change check (a second look at a reply of two or more clauses: did the customer change their answer?) said: {'none': 1095, 'not used': 12}. `not used`: a recall reply that named nothing, or a reply whose answer call failed.
- Spent in this run: $0.00000.
- Cost of these calls with nothing cached: $0.30308 ($0.00210 per transcript, $0.00007 per LLM call).
- Latency per LLM call when first made: median 2.34 s, p90 4.21 s (wall time of the client call, retries included, one network).

## By base case

- False clears: 1 calls in 1 of 36 base cases (B03).
- False alarms: 0 calls in 0 of 36 base cases; gold-clear base cases: 9.
- Any wrong call verdict: 1 calls in 1 of 36 base cases (B03).
- Any wrong field: 13 calls in 5 of 36 base cases (B03, G01, G02, U08, U10).
- `consent_given` where the customer agreed to a misdescribed product (C02, U08, V04, V06; the set expects true and calls false a defensible reading): 16/16 match the set. All other calls: 128/128.
- Replies to a checked question that are word for word a reply of the development set: 70 of 1604 (4.36%); 28 of them longer than three words. The prompt was iterated on the development set, so the model's reading of these replies is in-sample.

## E1: teach-back call against the yes/no call, by stratum

| stratum | gold | calls (base cases) | yes/no call caught | teach-back caught | teach-back flagged the target rule | teach-back caught, gold extraction |
|---|---|---|---|---|---|---|
| coached | flag or unclear | 12 (3) | 0/12 calls (0/3 base cases in every language) | 12/12 calls (3/3 base cases in every language) | 12/12 calls (3/3 base cases in every language) | 12/12 calls (3/3 base cases in every language) |
| acquiescent | flag or unclear | 4 (1) | 0/4 calls (0/1 base cases in every language) | 4/4 calls (1/1 base cases in every language) | 4/4 calls (1/1 base cases in every language) | 4/4 calls (1/1 base cases in every language) |
| never_asked | flag or unclear | 20 (5) | 0/20 calls (0/5 base cases in every language) | 19/20 calls (4/5 base cases in every language) | 19/20 calls (4/5 base cases in every language) | 20/20 calls (5/5 base cases in every language) |
| asked | flag or unclear | 40 (10) | 40/40 calls (10/10 base cases in every language) | 40/40 calls (10/10 base cases in every language) | 36/40 calls (9/10 base cases in every language) | 40/40 calls (10/10 base cases in every language) |
| informed | flag or unclear | 32 (8) | 4/32 calls (1/8 base cases in every language) | 32/32 calls (8/8 base cases in every language) | 28/32 calls (7/8 base cases in every language) | 32/32 calls (8/8 base cases in every language) |
| informed | clear | 36 (9) | 0/36 calls (0/9 base cases in every language) | 0/36 calls (0/9 base cases in every language) | 0/36 calls (0/9 base cases in every language) | 0/36 calls (0/9 base cases in every language) |

Caught: the call did not end as a pass (yes/no: not confirmed; teach-back: verdict not clear, which includes unclear and an extractor error). The yes/no arm is the set's scripted outcome with no LLM; coached and acquiescent customers say yes to it by assumption, and never_asked is the coverage of a five-question script. The strata are the set author's mix, so no pooled rate is given. For a clear-gold row, caught is a false alarm.

## Failures

### U08-ta (ta): gold `flag_for_review`, pipeline `flag_for_review`, tier `refer`
Scenario: Customer believes the cover is an investment plan that grows [violating, target rule kind]
- field `recall_items`: gold `((('P1', <KindClaim.investment: 'investment'>), 1),)`, pipeline `(((None, None), 1),)`
  - turn 10 [recall] bot: "லோனுடன் நீங்கள் என்னென்ன எடுத்தீர்கள், எவ்வளவுக்கு?" customer: "லோனோட ஒரு பிளான்ல பணம் போட்டேன், இருபத்தையாயிரம் ரூபாய்."
  - pipeline kept: None:"லோனோட ஒரு பிளான்ல பணம் போட்டேன்"->None
- flag not in gold: `recall` on P1: customer did not name this product unprompted | quote: "லோனோட ஒரு பிளான்ல பணம் போட்டேன், இருபத்தையாயிரம் ரூபாய்."

### U08-kn (kn): gold `flag_for_review`, pipeline `flag_for_review`, tier `refer`
Scenario: Customer believes the cover is an investment plan that grows [violating, target rule kind]
- field `recall_items`: gold `((('P1', <KindClaim.investment: 'investment'>), 1),)`, pipeline `(((None, None), 1),)`
  - turn 10 [recall] bot: "ಲೋನ್ ಜೊತೆ ನೀವು ಏನೇನು ತೆಗೆದುಕೊಂಡಿರಿ, ಎಷ್ಟಕ್ಕೆ?" customer: "ಲೋನ್ ಜೊತೆ ಒಂದು ಪ್ಲಾನಲ್ಲಿ ದುಡ್ಡು ಹಾಕಿದೆ, ಇಪ್ಪತ್ತೈದು ಸಾವಿರ ರೂಪಾಯಿ."
  - pipeline kept: None:"ಲೋನ್ ಜೊತೆ ಒಂದು ಪ್ಲಾನಲ್ಲಿ ದುಡ್ಡು ಹಾಕಿದೆ"->None
- flag not in gold: `recall` on P1: customer did not name this product unprompted | quote: "ಲೋನ್ ಜೊತೆ ಒಂದು ಪ್ಲಾನಲ್ಲಿ ದುಡ್ಡು ಹಾಕಿದೆ, ಇಪ್ಪತ್ತೈದು ಸಾವಿರ ರೂಪಾಯಿ."

### U10-hi (hi): gold `flag_for_review`, pipeline `flag_for_review`, tier `refer`
Scenario: Customer who answers 'I don't know' to almost everything [violating, target rule cover]
- field `consent_method`: gold `('dont_know', None)`, pipeline `('unclear', None)`
  - turn 28 [consent] bot: "लोन लेते समय आपने क्या-क्या लेने के लिए हामी भरी थी, और हामी कैसे दी थी?" customer: "ये मुझे नहीं पता कि किस-किस चीज़ के लिए हाँ हुई थी।"
  - pipeline kept: "ये मुझे नहीं पता कि किस-किस चीज़ के लिए हाँ हुई थी।" (turn 28)

### U10-hi-en (hi-en): gold `flag_for_review`, pipeline `flag_for_review`, tier `refer`
Scenario: Customer who answers 'I don't know' to almost everything [violating, target rule cover]
- field `consent_method`: gold `('dont_know', None)`, pipeline `('unclear', None)`
  - turn 28 [consent] bot: "Loan लेते समय आपने क्या-क्या लेने के लिए हाँ की थी, और हाँ कैसे की थी?" customer: "ये मुझे नहीं पता कि किस-किस चीज़ के लिए agree किया था।"
  - pipeline kept: "ये मुझे नहीं पता कि किस-किस चीज़ के लिए agree किया था।" (turn 28)

### U10-ta (ta): gold `flag_for_review`, pipeline `flag_for_review`, tier `refer`
Scenario: Customer who answers 'I don't know' to almost everything [violating, target rule cover]
- field `cancel_allowed`: gold `('dont_know', None)`, pipeline `('unclear', None)`
  - turn 24 [cancel_window] bot: "அதை ரத்து செய்ய முடியுமா முடியாதா, எத்தனை நாளுக்குள் என்று உங்களிடம் சொன்னார்களா?" customer: "கேன்சல் பண்ண முடியுமா முடியாதான்னு தெரியல."
  - pipeline kept: "கேன்சல் பண்ண முடியுமா முடியாதான்னு தெரியல." (turn 24)
- field `consent_method`: gold `('dont_know', None)`, pipeline `('unclear', None)`
  - turn 28 [consent] bot: "லோன் வாங்கும்போது நீங்கள் என்னென்ன எடுக்க ஒப்புக்கொண்டீர்கள், எப்படி ஒப்புதல் கொடுத்தீர்கள்?" customer: "எது எதுக்கு ஒத்துக்கிட்டேன்னு எனக்கு தெரியலங்க."
  - pipeline kept: "எது எதுக்கு ஒத்துக்கிட்டேன்னு எனக்கு தெரியலங்க." (turn 28)
- missed flag: `cancel_window` on P1

### U10-kn (kn): gold `flag_for_review`, pipeline `flag_for_review`, tier `refer`
Scenario: Customer who answers 'I don't know' to almost everything [violating, target rule cover]
- field `consent_method`: gold `('dont_know', None)`, pipeline `('unclear', None)`
  - turn 28 [consent] bot: "ಲೋನ್ ತೆಗೆದುಕೊಳ್ಳುವಾಗ ನೀವು ಏನೇನು ತೆಗೆದುಕೊಳ್ಳಲು ಒಪ್ಪಿದ್ದಿರಿ, ಒಪ್ಪಿಗೆ ಹೇಗೆ ಕೊಟ್ಟಿರಿ?" customer: "ಯಾವುದಕ್ಕೆಲ್ಲ ಒಪ್ಪಿದ್ದೆ ಅಂತ ನನಗೆ ಗೊತ್ತಿಲ್ಲ."
  - pipeline kept: "ಯಾವುದಕ್ಕೆಲ್ಲ ಒಪ್ಪಿದ್ದೆ ಅಂತ ನನಗೆ ಗೊತ್ತಿಲ್ಲ." (turn 28)

### G01-ta (ta): gold `flag_for_review`, pipeline `flag_for_review`, tier `refer`
Scenario: Two lakh debited from the borrower's account for a policy, no consent on record [violating, target rule consent]
- field `consent_method`: gold `('unclear', None)`, pipeline `('stated', <ConsentMethod.verbal: 'verbal'>)`
  - turn 28 [consent] bot: "லோன் வாங்கும்போது நீங்கள் என்னென்ன எடுக்க ஒப்புக்கொண்டீர்கள், எப்படி ஒப்புதல் கொடுத்தீர்கள்?" customer: "நான் லோனுக்கு மட்டும்தான் சரின்னு சொன்னேன். இன்ஷூரன்ஸ் பத்தி என்கிட்ட யாரும் கேக்கல. எனக்கு அப்புறம்தான் தெரிஞ்சுது, அக்கவுண்ட்ல இருந்து பணம் போனப்ப."
  - pipeline kept: "நான் லோனுக்கு மட்டும்தான் சரின்னு சொன்னேன். இன்ஷூரன்ஸ் பத்தி என்கிட்ட யாரும் கேக்கல. எனக்கு அப்புறம்தான் தெரிஞ்சுது, அக்கவுண்ட்ல இருந்து பணம் போனப்ப." (turn 28)

### G01-kn (kn): gold `flag_for_review`, pipeline `flag_for_review`, tier `refer`
Scenario: Two lakh debited from the borrower's account for a policy, no consent on record [violating, target rule consent]
- field `premium_inr`: gold `('stated', 200000)`, pipeline `('unclear', None)`
  - turn 14 [premium] bot: "ಅದಕ್ಕೆ ನೀವು ಎಷ್ಟು ರೂಪಾಯಿ ಕೊಟ್ಟಿರಿ?" customer: "ಎರಡು ಲಕ್ಷ ರೂಪಾಯಿ ತಗೊಂಡಿದ್ದಾರೆ."
  - turn 30 [readback] bot: "ಎರಡು ಲಕ್ಷ, ಅಂದರೆ 2,00,000 ರೂಪಾಯಿ, ಸರಿಯೇ?" customer: "ಹೌದು, ಸರಿ."
  - pipeline kept: "ಎರಡು ಲಕ್ಷ ರೂಪಾಯಿ ತಗೊಂಡಿದ್ದಾರೆ." (turn 14)

### G02-hi (hi): gold `flag_for_review`, pipeline `flag_for_review`, tier `refer`
Scenario: Signed consent on file; the customer says they agreed only to the loan [violating, target rule consent]
- field `consent_method`: gold `('unclear', None)`, pipeline `('stated', <ConsentMethod.signed_form: 'signed_form'>)`
  - turn 28 [consent] bot: "लोन लेते समय आपने क्या-क्या लेने के लिए हामी भरी थी, और हामी कैसे दी थी?" customer: "मैंने तो बस लोन के लिए हाँ बोली थी। बीमे के लिए मुझसे किसी ने नहीं पूछा। बहुत सारे काग़ज़ों पर साइन करवाए थे, किसी ने बताया नहीं कौन सा किस चीज़ का है।"
  - pipeline kept: "मैंने तो बस लोन के लिए हाँ बोली थी। बीमे के लिए मुझसे किसी ने नहीं पूछा। बहुत सारे काग़ज़ों पर साइन करवाए थे, किसी ने बताया नहीं कौन सा किस चीज़ का है।" (turn 28)

### G02-hi-en (hi-en): gold `flag_for_review`, pipeline `flag_for_review`, tier `refer`
Scenario: Signed consent on file; the customer says they agreed only to the loan [violating, target rule consent]
- field `consent_method`: gold `('unclear', None)`, pipeline `('stated', <ConsentMethod.signed_form: 'signed_form'>)`
  - turn 28 [consent] bot: "Loan लेते समय आपने क्या-क्या लेने के लिए हाँ की थी, और हाँ कैसे की थी?" customer: "सिर्फ़ loan। Insurance लेने की हामी मैंने कभी नहीं भरी। बहुत सारे papers पर sign करवाए थे, किसी ने बताया नहीं कौन सा किस चीज़ का है।"
  - pipeline kept: "सिर्फ़ loan। Insurance लेने की हामी मैंने कभी नहीं भरी। बहुत सारे papers पर sign करवाए थे, किसी ने बताया नहीं कौन सा किस चीज़ का है।" (turn 28)

### G02-ta (ta): gold `flag_for_review`, pipeline `flag_for_review`, tier `refer`
Scenario: Signed consent on file; the customer says they agreed only to the loan [violating, target rule consent]
- field `consent_method`: gold `('unclear', None)`, pipeline `('stated', <ConsentMethod.signed_form: 'signed_form'>)`
  - turn 28 [consent] bot: "லோன் வாங்கும்போது நீங்கள் என்னென்ன எடுக்க ஒப்புக்கொண்டீர்கள், எப்படி ஒப்புதல் கொடுத்தீர்கள்?" customer: "லோன் மட்டும்தான். இன்ஷூரன்ஸ் எடுக்க நான் ஒருநாளும் ஒத்துக்கல. நிறைய பேப்பர்ல கையெழுத்து வாங்கினாங்க, எது எதுக்குன்னு யாரும் சொல்லல."
  - pipeline kept: "லோன் மட்டும்தான். இன்ஷூரன்ஸ் எடுக்க நான் ஒருநாளும் ஒத்துக்கல. நிறைய பேப்பர்ல கையெழுத்து வாங்கினாங்க, எது எதுக்குன்னு யாரும் சொல்லல." (turn 28)

### G02-kn (kn): gold `flag_for_review`, pipeline `flag_for_review`, tier `refer`
Scenario: Signed consent on file; the customer says they agreed only to the loan [violating, target rule consent]
- field `consent_method`: gold `('unclear', None)`, pipeline `('stated', <ConsentMethod.signed_form: 'signed_form'>)`
  - turn 28 [consent] bot: "ಲೋನ್ ತೆಗೆದುಕೊಳ್ಳುವಾಗ ನೀವು ಏನೇನು ತೆಗೆದುಕೊಳ್ಳಲು ಒಪ್ಪಿದ್ದಿರಿ, ಒಪ್ಪಿಗೆ ಹೇಗೆ ಕೊಟ್ಟಿರಿ?" customer: "ಲೋನ್ ಮಾತ್ರ. ಇನ್ಶೂರೆನ್ಸ್ ತಗೊಳ್ಳೋಕೆ ನಾನು ಯಾವತ್ತೂ ಒಪ್ಪಿಲ್ಲ. ತುಂಬಾ ಪೇಪರಿಗೆ ಸಹಿ ಹಾಕಿಸ್ಕೊಂಡ್ರು, ಯಾವುದು ಯಾವುದಕ್ಕೆ ಅಂತ ಯಾರೂ ಹೇಳಿಲ್ಲ."
  - pipeline kept: "ಲೋನ್ ಮಾತ್ರ. ಇನ್ಶೂರೆನ್ಸ್ ತಗೊಳ್ಳೋಕೆ ನಾನು ಯಾವತ್ತೂ ಒಪ್ಪಿಲ್ಲ. ತುಂಬಾ ಪೇಪರಿಗೆ ಸಹಿ ಹಾಕಿಸ್ಕೊಂಡ್ರು, ಯಾವುದು ಯಾವುದಕ್ಕೆ ಅಂತ ಯಾರೂ ಹೇಳಿಲ್ಲ." (turn 28)

### B03-ta (ta): gold `flag_for_review`, pipeline `clear`, tier `clear` **FALSE CLEAR**
Scenario: Believes the premium is paid only once; the record shows a regular-premium product [violating, target rule belief_mismatch]
- field `volunteered_claims`: gold `(('P1', <FeatureClaim.one_time_payment: 'one_time_payment'>),)`, pipeline `()`
  - pipeline kept: -
  - gold has: one_time_payment:"ஒரே தடவைதான், ஐம்பத்திரண்டாயிரம் ரூபாய்."
- missed flag: `belief_mismatch` on P1
