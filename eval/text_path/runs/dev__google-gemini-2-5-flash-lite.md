# Text path on the `dev` set, model `google/gemini-2.5-flash-lite`

Run at 2026-11-10T05:34:55+00:00. Development set: 20 hand-written calls (5 each hi, hi-en, ta, kn), typed text, one author for replies, gold and prompt. Tamil and Kannada not human-reviewed. Gold verdicts and flags are the rule engine run on the hand-labelled extraction. Used for prompt iteration, so these numbers are in-sample.

## Headline

| group | calls | false clear | false alarm | call verdict | product verdict | fields |
|---|---|---|---|---|---|---|
| all | 20 | 0.0% (0/13) | 100.0% (7/7) | 65.0% (13/20) | 85.0% (17/20) | 93.8% (285/304) |
| hi | 5 | 0.0% (0/3) | 100.0% (2/2) | 60.0% (3/5) | 80.0% (4/5) | 96.1% (74/77) |
| hi-en | 5 | 0.0% (0/4) | 100.0% (1/1) | 80.0% (4/5) | 100.0% (5/5) | 94.7% (72/76) |
| ta | 5 | 0.0% (0/3) | 100.0% (2/2) | 60.0% (3/5) | 80.0% (4/5) | 94.7% (71/75) |
| kn | 5 | 0.0% (0/3) | 100.0% (2/2) | 60.0% (3/5) | 80.0% (4/5) | 89.5% (68/76) |
| gold extraction, no LLM | 20 | 0.0% (0/13) | 0.0% (0/7) | 100.0% (20/20) | 100.0% (20/20) | - |

False clear: gold is flag_for_review or unclear_needs_human and the pipeline says clear (n = calls whose gold is not clear). False alarm: gold is clear and the pipeline does not say clear (n = calls whose gold is clear). Extractor errors: 0. Last row: the rule engine on the set's gold extraction, so any miss there is not the extractor's.

## Verdicts, gold against pipeline (all calls)

| gold | pipeline | calls |
|---|---|---|
| clear | flag_for_review | 7 |
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
| cancel_window_days | 90.0% (18/20) | 100.0% (5/5) | 80.0% (4/5) | 100.0% (5/5) | 80.0% (4/5) |
| feature_probe | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| consent_given | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| consent_method | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| recall_items | 100.0% (20/20) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) |
| volunteered_claims | 65.0% (13/20) | 60.0% (3/5) | 80.0% (4/5) | 60.0% (3/5) | 60.0% (3/5) |
| sale_concerns | 50.0% (10/20) | 80.0% (4/5) | 60.0% (3/5) | 60.0% (3/5) | 0.0% (0/5) |

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
| bundling | 80.0% (4/5) | 50.0% (1/2) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (4/4) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) |
| belief_mismatch | 69.2% (9/13) | 75.0% (3/4) | 50.0% (1/2) | 66.7% (2/3) | 75.0% (3/4) | 100.0% (9/9) | 100.0% (3/3) | 100.0% (1/1) | 100.0% (2/2) | 100.0% (3/3) |
| sale_conduct | 30.8% (4/13) | 66.7% (2/3) | 50.0% (1/2) | 33.3% (1/3) | 0.0% (0/5) | 100.0% (4/4) | 100.0% (2/2) | 100.0% (1/1) | 100.0% (1/1) | n/a (n=0) |
| all rules | 81.1% (60/74) | 84.2% (16/19) | 81.8% (9/11) | 85.7% (18/21) | 73.9% (17/23) | 100.0% (60/60) | 100.0% (16/16) | 100.0% (9/9) | 100.0% (18/18) | 100.0% (17/17) |

## Spans and grounding

- Spans the model copied (amounts, durations, recall items, claims, concerns) that were not in the reply: 0 of 131 (0.00%). By field: none.
- Answers whose clause numbers were missing or out of range: 0 of 171 (0.00%). By field: none.
- Both kinds are dropped to `unclear` (answers) or left for the rule engine to record as an evidence gap (recall items, claims, concerns). None is kept as an answer.
- Answers marked stated with no value or no span, kept as unclear: 0. By field: none.
- Gaps the rule engine raised with reason `quote_not_grounded`: 0 (with the gold extraction: 0).
- Gaps with reason `value_not_parsed`: 1 (with the gold extraction: 0).
- Record values found in bot turns shown to the model: premium in a `readback` question: 16. A lexical check of the premium, cover, sanctioned and disbursed amounts (digits and spoken form) and the provider name. A read-back repeats the amount the customer said, so it shows the record's premium whenever the customer's amount equals it. The two identity checks are never sent.

## Cost and latency

- LLM calls: 403 for 20 calls (10 served from the cache in this run).
- Spent in this run: $0.02648.
- Cost of these calls with nothing cached: $0.02697 ($0.00135 per transcript, $0.00007 per LLM call).
- Latency per LLM call when first made: median 1.01 s, p90 1.22 s (wall time of the client call, retries included, one network).

## Failures

### hi-01 (hi): gold `clear`, pipeline `flag_for_review`
Scenario: compliant customer, every answer matches the record
- field `sale_concerns`: gold `()`, pipeline `(<SaleConcern.learned_after_sale: 'learned_after_sale'>,)`
  - pipeline kept: learned_after_sale:"तीस दिन के अंदर रद्द करवा सकते हैं"
  - gold has: -
- flag not in gold: `sale_conduct` on the call: customer says they learned of the product only after the sale | quote: "तीस दिन के अंदर रद्द करवा सकते हैं"

### hi-02 (hi): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: customer believes the product is an FD; no consent on record
- field `volunteered_claims`: gold `()`, pipeline `(('P1', <FeatureClaim.one_time_payment: 'one_time_payment'>),)`
  - pipeline kept: is_deposit:"बस एक एफ़डी करवाई थी लोन की सिक्योरिटी के लिए"; one_time_payment:"बस एक एफ़डी करवाई थी लोन की सिक्योरिटी के लिए"; is_deposit:"एफ़डी है"
  - gold has: -

### hi-04 (hi): gold `clear`, pipeline `flag_for_review`
Scenario: self-corrections and a premium corrected at read-back
- field `volunteered_claims`: gold `()`, pipeline `(('P1', <FeatureClaim.is_deposit: 'is_deposit'>), ('P1', <FeatureClaim.refundable_anytime: 'refundable_anytime'>))`
  - pipeline kept: is_deposit:"एक एफ़डी"; is_deposit:"बीमा था"; is_deposit:"बीमा लिया था इकतालीस हज़ार का"; is_deposit:"डिपॉज़िट"; is_deposit:"बीमा है, बीमा"; refundable_anytime:"एक महीने के अंदर रद्द कर सकते हैं"
  - gold has: -
- flag not in gold: `belief_mismatch` on P1: customer believes it is a deposit; the product does not have this feature | quote: "एक एफ़डी"; customer believes the money can be taken back at any time; the product does not have this feature | quote: "एक महीने के अंदर रद्द कर सकते हैं"
- flag not in gold: `bundling` on P1: the record marks this product as required for the loan; customer describes it as a deposit, which is not a risk mitigant | quote: "एक एफ़डी"

### en-01 (hi-en): gold `clear`, pipeline `flag_for_review`
Scenario: compliant; paid separately; no cancel window on record
- field `sale_concerns`: gold `()`, pipeline `(<SaleConcern.coached_answers: 'coached_answers'>,)`
  - pipeline kept: coached_answers:"Insurance के लिए phone पे yes बोला था, call record हो रही थी"
  - gold has: -
- flag not in gold: `sale_conduct` on the call: customer says they were told what to answer | quote: "Insurance के लिए phone पे yes बोला था, call record हो रही थी"

### en-02 (hi-en): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: premium differs from the record and is confirmed; consent method differs
- field `volunteered_claims`: gold `()`, pipeline `(('P1', <FeatureClaim.refundable_anytime: 'refundable_anytime'>),)`
  - pipeline kept: refundable_anytime:"30 days के अंदर cancel कर सकते हैं"
  - gold has: -
- flag not in gold: `belief_mismatch` on P1: customer believes the money can be taken back at any time; the product does not have this feature | quote: "30 days के अंदर cancel कर सकते हैं"

### en-03 (hi-en): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: required with no choice of provider; learned of it after the sale
- field `cancel_window_days`: gold `('unclear', None)`, pipeline `('dont_know', None)`
  - turn 27 [cancel_window] bot: "क्या आपको बताया गया था कि इसे cancel कर सकते हैं या नहीं, और कब तक?" customer: "पता नहीं, याद नहीं कि बताया था या नहीं."
  - pipeline kept: "पता नहीं, याद नहीं कि बताया था या नहीं." (turn 27)
- field `sale_concerns`: gold `(<SaleConcern.learned_after_sale: 'learned_after_sale'>,)`, pipeline `(<SaleConcern.learned_after_sale: 'learned_after_sale'>, <SaleConcern.signed_without_explanation: 'signed_without_explanation'>)`
  - pipeline kept: learned_after_sale:"बाद में statement में देखा कि 28,000 का insurance कटा है"; learned_after_sale:"ऐसा statement में लिखा था"; signed_without_explanation:"App पे accept button दबाया था, उसी में insurance भी था"
  - gold has: learned_after_sale:"बाद में statement में देखा कि 28,000 का insurance कटा है"

### ta-01 (ta): gold `clear`, pipeline `flag_for_review`
Scenario: compliant customer
- field `sale_concerns`: gold `()`, pipeline `(<SaleConcern.signed_without_explanation: 'signed_without_explanation'>,)`
  - pipeline kept: signed_without_explanation:"இன்சூரன்ஸ்க்கு ஃபார்ம்ல கையெழுத்து போட்டேன்"
  - gold has: -
- flag not in gold: `sale_conduct` on the call: customer says they signed without an explanation | quote: "இன்சூரன்ஸ்க்கு ஃபார்ம்ல கையெழுத்து போட்டேன்"

### ta-02 (ta): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: customer believes the product is an FD they can take back at any time
- field `volunteered_claims`: gold `()`, pipeline `(('P1', <FeatureClaim.one_time_payment: 'one_time_payment'>),)`
  - pipeline kept: is_deposit:"நகைக்கடனுக்கு பாதுகாப்புன்னு ஒரு எஃப்டி போட்டாங்க"; one_time_payment:"45,000 ரூபாய்"; is_deposit:"எஃப்டி தான்"
  - gold has: -
- field `sale_concerns`: gold `()`, pipeline `(<SaleConcern.signed_without_explanation: 'signed_without_explanation'>,)`
  - pipeline kept: signed_without_explanation:"இது இல்லாம லோன் கிடைக்காதுன்னு சொன்னாங்க"; signed_without_explanation:"எஃப்டிக்குன்னு சொல்லி பேப்பர்ல கையெழுத்து வாங்கினாங்க"
  - gold has: -
- flag not in gold: `sale_conduct` on the call: customer says they signed without an explanation | quote: "இது இல்லாம லோன் கிடைக்காதுன்னு சொன்னாங்க"; customer says they signed without an explanation | quote: "எஃப்டிக்குன்னு சொல்லி பேப்பர்ல கையெழுத்து வாங்கினாங்க"

### ta-04 (ta): gold `clear`, pipeline `flag_for_review`
Scenario: answers a different question once; premium corrected at read-back
- field `volunteered_claims`: gold `()`, pipeline `(('P1', <FeatureClaim.refundable_anytime: 'refundable_anytime'>),)`
  - pipeline kept: refundable_anytime:"30 நாள் டைம் இருக்கு, அதுக்குள்ள கேன்சல் பண்ணலாம்"
  - gold has: -
- flag not in gold: `belief_mismatch` on P1: customer believes the money can be taken back at any time; the product does not have this feature | quote: "30 நாள் டைம் இருக்கு, அதுக்குள்ள கேன்சல் பண்ணலாம்"

### kn-01 (kn): gold `clear`, pipeline `flag_for_review`
Scenario: compliant; required as a risk mitigant with a choice of provider
- field `volunteered_claims`: gold `()`, pipeline `(('P1', <FeatureClaim.refundable_anytime: 'refundable_anytime'>),)`
  - pipeline kept: refundable_anytime:"30 ದಿನ ಒಳಗೆ ಕ್ಯಾನ್ಸಲ್ ಮಾಡಬಹುದು"
  - gold has: -
- field `sale_concerns`: gold `()`, pipeline `(<SaleConcern.learned_after_sale: 'learned_after_sale'>,)`
  - pipeline kept: learned_after_sale:"ಸಾಲಕ್ಕೆ ಇದು ಬೇಕೇ ಬೇಕು ಅಂತ ಹೇಳಿದ್ರು"
  - gold has: -
- flag not in gold: `belief_mismatch` on P1: customer believes the money can be taken back at any time; the product does not have this feature | quote: "30 ದಿನ ಒಳಗೆ ಕ್ಯಾನ್ಸಲ್ ಮಾಡಬಹುದು"
- flag not in gold: `sale_conduct` on the call: customer says they learned of the product only after the sale | quote: "ಸಾಲಕ್ಕೆ ಇದು ಬೇಕೇ ಬೇಕು ಅಂತ ಹೇಳಿದ್ರು"

### kn-02 (kn): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: customer believes the product is a deposit that returns with interest
- field `volunteered_claims`: gold `()`, pipeline `(('P1', <FeatureClaim.one_time_payment: 'one_time_payment'>),)`
  - pipeline kept: is_deposit:"ಚಿನ್ನದ ಸಾಲಕ್ಕೆ ಭದ್ರತೆ ಅಂತ ಒಂದು ಫಿಕ್ಸೆಡ್ ಡೆಪಾಸಿಟ್ ಇಟ್ಟಿದ್ದೀನಿ"; one_time_payment:"ಚಿನ್ನದ ಸಾಲಕ್ಕೆ ಭದ್ರತೆ ಅಂತ ಒಂದು ಫಿಕ್ಸೆಡ್ ಡೆಪಾಸಿಟ್ ಇಟ್ಟಿದ್ದೀನಿ"; is_deposit:"ಡೆಪಾಸಿಟ್ ಅದು"
  - gold has: -
- field `sale_concerns`: gold `()`, pipeline `(<SaleConcern.learned_after_sale: 'learned_after_sale'>, <SaleConcern.signed_without_explanation: 'signed_without_explanation'>)`
  - pipeline kept: learned_after_sale:"ಇದಿಲ್ಲದೆ ಸಾಲ ಕೊಡಲ್ಲ ಅಂದ್ರು"; signed_without_explanation:"ಡೆಪಾಸಿಟ್‌ಗೆ ಅಂತ ಫಾರ್ಮ್‌ಗೆ ಸಹಿ ಹಾಕಿದೆ"
  - gold has: -
- flag not in gold: `sale_conduct` on the call: customer says they learned of the product only after the sale | quote: "ಇದಿಲ್ಲದೆ ಸಾಲ ಕೊಡಲ್ಲ ಅಂದ್ರು"; customer says they signed without an explanation | quote: "ಡೆಪಾಸಿಟ್‌ಗೆ ಅಂತ ಫಾರ್ಮ್‌ಗೆ ಸಹಿ ಹಾಕಿದೆ"

### kn-03 (kn): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: does not know anything about the product; gives the EMI when asked the premium
- field `cancel_window_days`: gold `('unclear', None)`, pipeline `('dont_know', None)`
  - turn 25 [cancel_window] bot: "ಇದನ್ನು ರದ್ದು ಮಾಡಬಹುದು ಎಂದು ಹೇಳಿದ್ದರೇ, ಎಷ್ಟು ದಿನದೊಳಗೆ?" customer: "ಹೇಳಿದ್ರೋ ಇಲ್ವೋ ನೆನಪಿಲ್ಲ."
  - pipeline kept: "ಹೇಳಿದ್ರೋ ಇಲ್ವೋ ನೆನಪಿಲ್ಲ." (turn 25)
- field `sale_concerns`: gold `()`, pipeline `(<SaleConcern.signed_without_explanation: 'signed_without_explanation'>,)`
  - pipeline kept: signed_without_explanation:"ಯಾರೂ ಏನೂ ಹೇಳಿಲ್ಲ"
  - gold has: -
- flag not in gold: `sale_conduct` on the call: customer says they signed without an explanation | quote: "ಯಾರೂ ಏನೂ ಹೇಳಿಲ್ಲ"

### kn-04 (kn): gold `clear`, pipeline `flag_for_review`
Scenario: self-corrections on kind and payment; a fee named in recall
- field `sale_concerns`: gold `()`, pipeline `(<SaleConcern.coached_answers: 'coached_answers'>, <SaleConcern.learned_after_sale: 'learned_after_sale'>)`
  - pipeline kept: learned_after_sale:"ರದ್ದು ಮಾಡಬಹುದು ಅಂತ ಯಾರೂ ತಿಳಿಸಿಲ್ಲ"; coached_answers:"ಇನ್ಶೂರೆನ್ಸ್‌ಗೆ ಫೋನ್‌ನಲ್ಲಿ ಹೌದು ಅಂದೆ, ಆ ಕಾಲ್ ರೆಕಾರ್ಡ್ ಆಗ್ತಿತ್ತು"
  - gold has: -
- flag not in gold: `sale_conduct` on the call: customer says they learned of the product only after the sale | quote: "ರದ್ದು ಮಾಡಬಹುದು ಅಂತ ಯಾರೂ ತಿಳಿಸಿಲ್ಲ"; customer says they were told what to answer | quote: "ಇನ್ಶೂರೆನ್ಸ್‌ಗೆ ಫೋನ್‌ನಲ್ಲಿ ಹೌದು ಅಂದೆ, ಆ ಕಾಲ್ ರೆಕಾರ್ಡ್ ಆಗ್ತಿತ್ತು"

### kn-05 (kn): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: volunteers a one-time-payment belief; says it was deducted though the record says paid separately
- field `sale_concerns`: gold `()`, pipeline `(<SaleConcern.signed_without_explanation: 'signed_without_explanation'>,)`
  - pipeline kept: signed_without_explanation:"ಯಾವ ಸಹಿನೂ ಹಾಕಿಲ್ಲ"
  - gold has: -
- flag not in gold: `sale_conduct` on the call: customer says they signed without an explanation | quote: "ಯಾವ ಸಹಿನೂ ಹಾಕಿಲ್ಲ"
