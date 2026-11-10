# Text path on the `dev` set, model `mistralai/mistral-small-3.2-24b-instruct`

Run at 2026-11-10T05:33:51+00:00. Development set: 20 hand-written calls (5 each hi, hi-en, ta, kn), typed text, one author for replies, gold and prompt. Tamil and Kannada not human-reviewed. Gold verdicts and flags are the rule engine run on the hand-labelled extraction. Used for prompt iteration, so these numbers are in-sample.

## Headline

| group | calls | false clear | false alarm | call verdict | product verdict | fields |
|---|---|---|---|---|---|---|
| all | 20 | 0.0% (0/13) | 42.9% (3/7) | 85.0% (17/20) | 100.0% (20/20) | 98.0% (298/304) |
| hi | 5 | 0.0% (0/3) | 0.0% (0/2) | 100.0% (5/5) | 100.0% (5/5) | 98.7% (76/77) |
| hi-en | 5 | 0.0% (0/4) | 0.0% (0/1) | 100.0% (5/5) | 100.0% (5/5) | 98.7% (75/76) |
| ta | 5 | 0.0% (0/3) | 50.0% (1/2) | 80.0% (4/5) | 100.0% (5/5) | 97.3% (73/75) |
| kn | 5 | 0.0% (0/3) | 100.0% (2/2) | 60.0% (3/5) | 100.0% (5/5) | 97.4% (74/76) |
| gold extraction, no LLM | 20 | 0.0% (0/13) | 0.0% (0/7) | 100.0% (20/20) | 100.0% (20/20) | - |

False clear: gold is flag_for_review or unclear_needs_human and the pipeline says clear (n = calls whose gold is not clear). False alarm: gold is clear and the pipeline does not say clear (n = calls whose gold is clear). Extractor errors: 0. Last row: the rule engine on the set's gold extraction, so any miss there is not the extractor's.

## Verdicts, gold against pipeline (all calls)

| gold | pipeline | calls |
|---|---|---|
| clear | clear | 4 |
| clear | flag_for_review | 3 |
| flag_for_review | flag_for_review | 12 |
| unclear_needs_human | unclear_needs_human | 1 |

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
| term_months | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| cancel_allowed | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| cancel_window_days | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| feature_probe | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| consent_given | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| consent_method | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| recall_items | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| volunteered_claims | 95.0% (19/20) | 80.0% (4/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| sale_concerns | 75.0% (15/20) | 100.0% (5/5) | 80.0% (4/5) | 60.0% (3/5) | 60.0% (3/5) |

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
| sale_conduct | 50.0% (4/8) | 100.0% (2/2) | 100.0% (1/1) | 33.3% (1/3) | 0.0% (0/2) | 100.0% (4/4) | 100.0% (2/2) | 100.0% (1/1) | 100.0% (1/1) | n/a (n=0) |
| all rules | 93.8% (60/64) | 100.0% (16/16) | 100.0% (9/9) | 90.0% (18/20) | 89.5% (17/19) | 100.0% (60/60) | 100.0% (16/16) | 100.0% (9/9) | 100.0% (18/18) | 100.0% (17/17) |

## Spans and grounding

- Spans the model copied (amounts, durations, recall items, claims, concerns) that were not in the reply: 0 of 108 (0.00%). By field: none.
- Answers whose clause numbers were missing or out of range: 0 of 169 (0.00%). By field: none.
- Both kinds are dropped to `unclear` (answers) or left for the rule engine to record as an evidence gap (recall items, claims, concerns). None is kept as an answer.
- Answers marked stated with no value or no span, kept as unclear: 0. By field: none.
- Gaps the rule engine raised with reason `quote_not_grounded`: 0 (with the gold extraction: 0).
- Gaps with reason `value_not_parsed`: 1 (with the gold extraction: 0).
- Record values found in bot turns shown to the model: premium in a `readback` question: 16. A lexical check of the premium, cover, sanctioned and disbursed amounts (digits and spoken form) and the provider name. A read-back repeats the amount the customer said, so it shows the record's premium whenever the customer's amount equals it. The two identity checks are never sent.

## Cost and latency

- LLM calls: 403 for 20 calls (9 served from the cache in this run).
- Spent in this run: $0.01590.
- Cost of these calls with nothing cached: $0.01614 ($0.00081 per transcript, $0.00004 per LLM call).
- Latency per LLM call when first made: median 0.82 s, p90 1.25 s (wall time of the client call, retries included, one network).

## Failures

### hi-02 (hi): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: customer believes the product is an FD; no consent on record
- field `volunteered_claims`: gold `()`, pipeline `(('P1', <FeatureClaim.one_time_payment: 'one_time_payment'>),)`
  - pipeline kept: is_deposit:"बस एक एफ़डी करवाई थी लोन की सिक्योरिटी के लिए"; one_time_payment:"बावन हज़ार की"; is_deposit:"बोला था कि एफ़डी के बिना लोन नहीं मिलेगा"
  - gold has: -

### en-03 (hi-en): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: required with no choice of provider; learned of it after the sale
- field `sale_concerns`: gold `(<SaleConcern.learned_after_sale: 'learned_after_sale'>,)`, pipeline `(<SaleConcern.coached_answers: 'coached_answers'>, <SaleConcern.learned_after_sale: 'learned_after_sale'>)`
  - pipeline kept: learned_after_sale:"बाद में statement में देखा कि 28,000 का insurance कटा है"; coached_answers:"Agent ने बोला था compulsory है, इसके बिना loan approve नहीं होगा"
  - gold has: learned_after_sale:"बाद में statement में देखा कि 28,000 का insurance कटा है"

### ta-03 (ta): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: does not know; silence; says they agreed only to the loan
- field `sale_concerns`: gold `()`, pipeline `(<SaleConcern.signed_without_explanation: 'signed_without_explanation'>,)`
  - pipeline kept: signed_without_explanation:"லோனுக்கு மட்டும் தான் ஒத்துக்கிட்டேன்"
  - gold has: -
- flag not in gold: `sale_conduct` on the call: customer says they signed without an explanation | quote: "லோனுக்கு மட்டும் தான் ஒத்துக்கிட்டேன்"

### ta-04 (ta): gold `clear`, pipeline `flag_for_review`
Scenario: answers a different question once; premium corrected at read-back
- field `sale_concerns`: gold `()`, pipeline `(<SaleConcern.signed_without_explanation: 'signed_without_explanation'>,)`
  - pipeline kept: signed_without_explanation:"இன்சூரன்ஸ்க்கு சம்மதிச்சேன்"
  - gold has: -
- flag not in gold: `sale_conduct` on the call: customer says they signed without an explanation | quote: "இன்சூரன்ஸ்க்கு சம்மதிச்சேன்"

### kn-01 (kn): gold `clear`, pipeline `flag_for_review`
Scenario: compliant; required as a risk mitigant with a choice of provider
- field `sale_concerns`: gold `()`, pipeline `(<SaleConcern.signed_without_explanation: 'signed_without_explanation'>,)`
  - pipeline kept: signed_without_explanation:"ಮೊಬೈಲ್‌ಗೆ ಬಂದ OTP ಕೊಟ್ಟೆ"
  - gold has: -
- flag not in gold: `sale_conduct` on the call: customer says they signed without an explanation | quote: "ಮೊಬೈಲ್‌ಗೆ ಬಂದ OTP ಕೊಟ್ಟೆ"

### kn-04 (kn): gold `clear`, pipeline `flag_for_review`
Scenario: self-corrections on kind and payment; a fee named in recall
- field `sale_concerns`: gold `()`, pipeline `(<SaleConcern.signed_without_explanation: 'signed_without_explanation'>,)`
  - pipeline kept: signed_without_explanation:"ರದ್ದು ಮಾಡಬಹುದು ಅಂತ ಯಾರೂ ತಿಳಿಸಿಲ್ಲ"
  - gold has: -
- flag not in gold: `sale_conduct` on the call: customer says they signed without an explanation | quote: "ರದ್ದು ಮಾಡಬಹುದು ಅಂತ ಯಾರೂ ತಿಳಿಸಿಲ್ಲ"
