# Text path on the `dev` set, model `anthropic/claude-haiku-5.5`

Run at 2026-11-10T04:05:56+00:00. Development set: 20 hand-written calls (5 each hi, hi-en, ta, kn), typed text, one author for replies, gold and prompt. Tamil and Kannada not human-reviewed. Used for prompt iteration, so these numbers are in-sample.

## Headline

| group | calls | false clear | false alarm | call verdict | product verdict | fields |
|---|---|---|---|---|---|---|
| all | 20 | 0.0% (0/13) | 0.0% (0/7) | 100.0% (20/20) | 100.0% (20/20) | 99.7% (303/304) |
| hi | 5 | 0.0% (0/3) | 0.0% (0/2) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (77/77) |
| hi-en | 5 | 0.0% (0/4) | 0.0% (0/1) | 100.0% (5/5) | 100.0% (5/5) | 98.7% (75/76) |
| ta | 5 | 0.0% (0/3) | 0.0% (0/2) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (75/75) |
| kn | 5 | 0.0% (0/3) | 0.0% (0/2) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (76/76) |

False clear: gold is flag_for_review or unclear_needs_human and the pipeline says clear (n = calls whose gold is not clear). False alarm: gold is clear and the pipeline does not say clear (n = calls whose gold is clear). Extractor errors: 0.

## Verdicts, gold against pipeline (all calls)

| gold | pipeline | calls |
|---|---|---|
| clear | clear | 7 |
| flag_for_review | flag_for_review | 12 |
| unclear_needs_human | unclear_needs_human | 1 |

## Extraction accuracy per field

| field | all | hi | hi-en | ta | kn |
|---|---|---|---|---|---|
| kind | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| premium_inr | 95.0% (19/20) | 100.0% (5/5) | 80.0% (4/5) | 100.0% (5/5) | 100.0% (5/5) |
| premium_readback | 100.0% (17/17) | 100.0% (4/4) | 100.0% (5/5) | 100.0% (4/4) | 100.0% (4/4) |
| payment_source | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| required_for_loan | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| provider_choice_offered | 100.0% (7/7) | 100.0% (3/3) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (2/2) |
| cover_inr | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| term_months | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
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
| premium | 100.0% (3/3) | 100.0% (1/1) | n/a (n=0) | 100.0% (1/1) | 100.0% (1/1) | 75.0% (3/4) | 100.0% (1/1) | 0.0% (0/1) | 100.0% (1/1) | 100.0% (1/1) |
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
| all rules | 100.0% (59/59) | 100.0% (16/16) | 100.0% (8/8) | 100.0% (18/18) | 100.0% (17/17) | 98.3% (59/60) | 100.0% (16/16) | 88.9% (8/9) | 100.0% (18/18) | 100.0% (17/17) |

## Spans and grounding

- Spans the model copied (amounts, durations, recall items, claims, concerns) that were not in the reply: 0 of 104 (0.00%). By field: none.
- Answers whose clause numbers were missing or out of range: 0 of 169 (0.00%). By field: none.
- Both kinds are dropped to `unclear` (answers) or left for the rule engine to record as an evidence gap (recall items, claims, concerns). None is kept as an answer.
- Answers marked stated with no value or no span, kept as unclear: 0. By field: none.
- Gaps the rule engine raised with reason `quote_not_grounded`: 0 (with the gold extraction: 0).
- Gaps with reason `value_not_parsed`: 0 (with the gold extraction: 0).

## Cost and latency

- LLM calls: 417 for 20 calls (16 served from the cache in this run).
- Spent in this run: $0.10002.
- Cost of these calls with nothing cached: $0.10410 ($0.00520 per transcript, $0.00025 per LLM call).
- Latency per LLM call when first made: median 1.06 s, p90 1.97 s (wall time of the client call, retries included, one network).

## Failures

### en-02 (hi-en): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: premium differs from the record and is confirmed; consent method differs
- field `premium_inr`: gold `('stated', 20000)`, pipeline `('unclear', None)`
  - turn 13 [premium] bot: "उसका cost कितना था?" customer: "20,000 के आसपास था."
  - turn 15 [readback] bot: "twenty thousand, यानी 20,000, सही है?" customer: "हाँ, 20,000."
  - pipeline kept: "20,000 के आसपास था." (turn 13)
- missed flag: `premium` on P1
