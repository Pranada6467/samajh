# Text path on the `dev` set, model `openai/gpt-6-luna`

Run at 2026-11-13T02:45:39+00:00. Development set: 20 hand-written calls (5 each hi, hi-en, ta, kn), typed text, one author for replies, gold and prompt. Tamil and Kannada not human-reviewed. Gold verdicts and flags are the rule engine run on the hand-labelled extraction. Used for prompt iteration, so these numbers are in-sample.

## Headline

| group | calls | false clear | false alarm | call verdict | product verdict | fields |
|---|---|---|---|---|---|---|
| all | 20 | 0.0% (0/13) | 0.0% (0/7) | 100.0% (20/20) | 100.0% (20/20) | 99.7% (303/304) |
| hi | 5 | 0.0% (0/3) | 0.0% (0/2) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (77/77) |
| hi-en | 5 | 0.0% (0/4) | 0.0% (0/1) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (76/76) |
| ta | 5 | 0.0% (0/3) | 0.0% (0/2) | 100.0% (5/5) | 100.0% (5/5) | 98.7% (74/75) |
| kn | 5 | 0.0% (0/3) | 0.0% (0/2) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (76/76) |
| gold extraction, no LLM | 20 | 0.0% (0/13) | 0.0% (0/7) | 100.0% (20/20) | 100.0% (20/20) | - |

False clear: gold is flag_for_review or unclear_needs_human and the pipeline says clear (n = calls whose gold is not clear). False alarm: gold is clear and the pipeline does not say clear (n = calls whose gold is clear). Extractor errors: 0. Last row: the rule engine on the set's gold extraction, so any miss there is not the extractor's.

## Triage: where each kind of customer ended up

| group | languages | calls (base cases) | tiers | misses, calls | misses, base cases | referrals, calls | referrals, base cases | referred on what the customer said, calls | referred on the record alone, calls | misses on the set's own extraction, calls |
|---|---|---|---|---|---|---|---|---|---|---|
| gold_not_clear | hi + hi-en | 7 (0) | refer 6, understanding_gap 1 | 14 per 100 (1/7; 95% 3 to 51) | n/a (no base cases) | 86 per 100 (6/7; 95% 49 to 97) | n/a (no base cases) | 6/7 | 0/7 | 14 per 100 (1/7; 95% 3 to 51) |
| gold_not_clear | hi | 3 (0) | refer 3 | 0 per 100 (0/3; 95% 0 to 56) | n/a (no base cases) | 100 per 100 (3/3; 95% 44 to 100) | n/a (no base cases) | 3/3 | 0/3 | 0 per 100 (0/3; 95% 0 to 56) |
| gold_not_clear | hi-en | 4 (0) | refer 3, understanding_gap 1 | 25 per 100 (1/4; 95% 5 to 70) | n/a (no base cases) | 75 per 100 (3/4; 95% 30 to 95) | n/a (no base cases) | 3/4 | 0/4 | 25 per 100 (1/4; 95% 5 to 70) |
| gold_not_clear | ta (experimental) | 3 (0) | refer 3 | 0 per 100 (0/3; 95% 0 to 56) | n/a (no base cases) | 100 per 100 (3/3; 95% 44 to 100) | n/a (no base cases) | 3/3 | 0/3 | 0 per 100 (0/3; 95% 0 to 56) |
| gold_not_clear | kn (experimental) | 3 (0) | refer 3 | 0 per 100 (0/3; 95% 0 to 56) | n/a (no base cases) | 100 per 100 (3/3; 95% 44 to 100) | n/a (no base cases) | 3/3 | 0/3 | 0 per 100 (0/3; 95% 0 to 56) |
| gold_clear | hi + hi-en | 3 (0) | clear 3 | 100 per 100 (3/3; 95% 44 to 100) | n/a (no base cases) | 0 per 100 (0/3; 95% 0 to 56) | n/a (no base cases) | 0/3 | 0/3 | 100 per 100 (3/3; 95% 44 to 100) |
| gold_clear | hi | 2 (0) | clear 2 | 100 per 100 (2/2; 95% 34 to 100) | n/a (no base cases) | 0 per 100 (0/2; 95% 0 to 66) | n/a (no base cases) | 0/2 | 0/2 | 100 per 100 (2/2; 95% 34 to 100) |
| gold_clear | hi-en | 1 (0) | clear 1 | 100 per 100 (1/1; 95% 21 to 100) | n/a (no base cases) | 0 per 100 (0/1; 95% 0 to 79) | n/a (no base cases) | 0/1 | 0/1 | 100 per 100 (1/1; 95% 21 to 100) |
| gold_clear | ta (experimental) | 2 (0) | clear 2 | 100 per 100 (2/2; 95% 34 to 100) | n/a (no base cases) | 0 per 100 (0/2; 95% 0 to 66) | n/a (no base cases) | 0/2 | 0/2 | 100 per 100 (2/2; 95% 34 to 100) |
| gold_clear | kn (experimental) | 2 (0) | clear 2 | 100 per 100 (2/2; 95% 34 to 100) | n/a (no base cases) | 0 per 100 (0/2; 95% 0 to 66) | n/a (no base cases) | 0/2 | 0/2 | 100 per 100 (2/2; 95% 34 to 100) |

Misses (a customer with a problem ends `clear` or `understanding_gap`): 0.

False referrals (an informed customer on a compliant record ends `refer`): 0.

A miss is counted only for customers the set labels misled, unaware or did not agree. `incomplete` is not a miss and not a referral: the call did not yield enough to decide. The last column runs the rule engine on the set's own extraction, so a miss there is the rules', not the extractor's. Base cases, not calls, are the independent unit. A referral on the record alone rests only on the lender's record (for example no consent on record) and on nothing the customer said; a referral on what the customer said has at least one refer-tier flag that rests on the customer's words (counts of the group's calls, base cases in brackets).

## Verdicts, gold against pipeline (all calls)

| gold | pipeline | calls |
|---|---|---|
| clear | clear | 7 |
| flag_for_review | flag_for_review | 12 |
| unclear_needs_human | unclear_needs_human | 1 |

## Tiers by gold verdict (all calls)

| gold verdict | pipeline tier | calls |
|---|---|---|
| clear | clear | 7 |
| flag_for_review | refer | 12 |
| unclear_needs_human | understanding_gap | 1 |

## Extraction accuracy per field

| field | all | hi | hi-en | ta | kn |
|---|---|---|---|---|---|
| kind | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| premium_inr | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| premium_readback | 100.0% (17/17) | 100.0% (4/4) | 100.0% (5/5) | 100.0% (4/4) | 100.0% (4/4) |
| payment_source | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| required_for_loan | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| provider_choice_offered | 100.0% (7/7) | 100.0% (3/3) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (2/2) |
| cover_inr | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| term_months | 95.0% (19/20) | 100.0% (5/5) | 100.0% (5/5) | 80.0% (4/5) | 100.0% (5/5) |
| cancel_allowed | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| cancel_window_days | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| feature_probe | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| consent_given | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| consent_method | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| recall_items | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| volunteered_claims | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| sale_concerns | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |

## Flags per rule: precision and recall

| rule | all P | hi P | hi-en P | ta P | kn P | all R | hi R | hi-en R | ta R | kn R |
|---|---|---|---|---|---|---|---|---|---|---|
| kind | 100.0% (6/6) | 100.0% (2/2) | n/a (n=0) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (6/6) | 100.0% (2/2) | n/a (n=0) | 100.0% (2/2) | 100.0% (2/2) |
| premium | 100.0% (4/4) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (4/4) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) |
| cover | 100.0% (6/6) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (3/3) | 100.0% (1/1) | 100.0% (6/6) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (3/3) | 100.0% (1/1) |
| term | 100.0% (2/2) | n/a (n=0) | n/a (n=0) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (2/2) | n/a (n=0) | n/a (n=0) | 100.0% (1/1) | 100.0% (1/1) |
| cancel_window | 100.0% (10/10) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (10/10) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (3/3) | 100.0% (3/3) |
| recall | 100.0% (4/4) | 100.0% (2/2) | n/a (n=0) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (4/4) | 100.0% (2/2) | n/a (n=0) | 100.0% (1/1) | 100.0% (1/1) |
| recall_unmatched | 100.0% (1/1) | n/a (n=0) | 100.0% (1/1) | n/a (n=0) | n/a (n=0) | 100.0% (1/1) | n/a (n=0) | 100.0% (1/1) | n/a (n=0) | n/a (n=0) |
| consent | 100.0% (6/6) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (6/6) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (2/2) | 100.0% (2/2) |
| loan_funded | 100.0% (4/4) | 100.0% (1/1) | n/a (n=0) | 100.0% (1/1) | 100.0% (2/2) | 100.0% (4/4) | 100.0% (1/1) | n/a (n=0) | 100.0% (1/1) | 100.0% (2/2) |
| bundling | 100.0% (4/4) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (4/4) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) |
| belief_mismatch | 100.0% (9/9) | 100.0% (3/3) | 100.0% (1/1) | 100.0% (2/2) | 100.0% (3/3) | 100.0% (9/9) | 100.0% (3/3) | 100.0% (1/1) | 100.0% (2/2) | 100.0% (3/3) |
| sale_conduct | 100.0% (4/4) | 100.0% (2/2) | 100.0% (1/1) | 100.0% (1/1) | n/a (n=0) | 100.0% (4/4) | 100.0% (2/2) | 100.0% (1/1) | 100.0% (1/1) | n/a (n=0) |
| all rules | 100.0% (60/60) | 100.0% (16/16) | 100.0% (9/9) | 100.0% (18/18) | 100.0% (17/17) | 100.0% (60/60) | 100.0% (16/16) | 100.0% (9/9) | 100.0% (18/18) | 100.0% (17/17) |

## Spans and grounding

- Spans the model copied (amounts, durations, recall items, claims, concerns) that were not in the reply: 0 of 108 (0.00%). By field: none.
- Answers whose clause numbers were missing or out of range: 0 of 179 (0.00%). By field: none.
- Both kinds are dropped to `unclear` (answers) or left for the rule engine to record as an evidence gap (recall items, claims, concerns). None is kept as an answer.
- Answers marked stated with no value or no span, kept as unclear: 0. By field: none.
- Gaps the rule engine raised with reason `quote_not_grounded`: 0 (with the gold extraction: 0).
- Gaps with reason `value_not_parsed`: 2 (with the gold extraction: 0).
- Record values found in bot turns shown to the model: premium in a `readback` question: 16. A lexical check of the premium, cover, sanctioned and disbursed amounts (digits and spoken form) and the provider name. A read-back repeats the amount the customer said, so it shows the record's premium whenever the customer's amount equals it. The two identity checks are never sent.

## Cost and latency

- LLM calls: 519 for 20 calls (519 served from the cache in this run).

| request | LLM calls | cost with nothing cached |
|---|---|---|
| answer | 229 | $0.01747 |
| screen | 174 | $0.00765 |
| check | 116 | $0.01122 |

- The change check (a second look at a reply of two or more clauses, or of one clause with a marker word such as नहीं or ruko: did the customer change their answer?) said: {'none': 108, 'not used': 3, 'corrected': 5}. `not used`: a recall reply that named nothing, or a reply whose answer call failed.
- Spent in this run: $0.00000.
- Cost of these calls with nothing cached: $0.03633 ($0.00182 per transcript, $0.00007 per LLM call).
- Latency per LLM call when first made: median 2.04 s, p90 3.83 s (wall time of the client call, retries included, one network).

## Failures

### ta-03 (ta): gold `flag_for_review`, pipeline `flag_for_review`, tier `refer`
Scenario: does not know; silence; says they agreed only to the loan
- field `term_months`: gold `('unclear', None)`, pipeline `('stated', 12)`
  - turn 21 [term] bot: "இது எவ்வளவு காலத்துக்கு?" customer: "ஒரு வருஷம்னு நினைக்கிறேன், சரியா தெரியலை."
  - pipeline kept: "ஒரு வருஷம்னு நினைக்கிறேன், சரியா தெரியலை." (turn 21)
