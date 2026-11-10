# Text path on the `frozen` set, model `openai/gpt-6-luna`

Run at 2026-11-10T05:44:37+00:00. Frozen set version 3 of 2026-11-10: 144 scripted calls (sha256 gold.jsonl 14e49b58929c, calls.jsonl b10111dfc64e). Synthetic, templated text, no speech-to-text, Tamil and Kannada not human-reviewed. Verdicts and flags are scored against the hand-written gold; fields against the set's perfect extraction. Not used for prompt or model selection.

## Headline

| group | calls | false clear | false alarm | call verdict | product verdict | fields |
|---|---|---|---|---|---|---|
| all | 144 | 0.9% (1/108) | 0.0% (0/36) | 99.3% (143/144) | 99.3% (143/144) | 99.2% (2163/2180) |
| hi | 36 | 0.0% (0/27) | 0.0% (0/9) | 100.0% (36/36) | 100.0% (36/36) | 99.6% (543/545) |
| hi-en | 36 | 0.0% (0/27) | 0.0% (0/9) | 100.0% (36/36) | 100.0% (36/36) | 99.6% (543/545) |
| ta | 36 | 3.7% (1/27) | 0.0% (0/9) | 97.2% (35/36) | 97.2% (35/36) | 98.5% (537/545) |
| kn | 36 | 0.0% (0/27) | 0.0% (0/9) | 100.0% (36/36) | 100.0% (36/36) | 99.1% (540/545) |
| gold extraction, no LLM | 144 | 0.0% (0/108) | 0.0% (0/36) | 100.0% (144/144) | 100.0% (144/144) | - |

False clear: gold is flag_for_review or unclear_needs_human and the pipeline says clear (n = calls whose gold is not clear). False alarm: gold is clear and the pipeline does not say clear (n = calls whose gold is clear). Extractor errors: 0. Last row: the rule engine on the set's gold extraction, so any miss there is not the extractor's.

## Verdicts, gold against pipeline (all calls)

| gold | pipeline | calls |
|---|---|---|
| clear | clear | 36 |
| flag_for_review | clear | 1 |
| flag_for_review | flag_for_review | 99 |
| unclear_needs_human | unclear_needs_human | 8 |

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
| feature_probe | 98.6% (142/144) | 100.0% (36/36) | 100.0% (36/36) | 97.2% (35/36) | 97.2% (35/36) |
| consent_given | 99.3% (143/144) | 100.0% (36/36) | 100.0% (36/36) | 97.2% (35/36) | 100.0% (36/36) |
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
- Answers whose clause numbers were missing or out of range: 0 of 1195 (0.00%). By field: none.
- Both kinds are dropped to `unclear` (answers) or left for the rule engine to record as an evidence gap (recall items, claims, concerns). None is kept as an answer.
- Answers marked stated with no value or no span, kept as unclear: 0. By field: none.
- Gaps the rule engine raised with reason `quote_not_grounded`: 0 (with the gold extraction: 0).
- Gaps with reason `value_not_parsed`: 0 (with the gold extraction: 0).
- Record values found in bot turns shown to the model: premium in a `readback` question: 120. A lexical check of the premium, cover, sanctioned and disbursed amounts (digits and spoken form) and the provider name. A read-back repeats the amount the customer said, so it shows the record's premium whenever the customer's amount equals it. The two identity checks are never sent.

## Cost and latency

- LLM calls: 3391 for 144 calls (2149 served from the cache in this run).
- Spent in this run: $0.09482.
- Cost of these calls with nothing cached: $0.24589 ($0.00171 per transcript, $0.00007 per LLM call).
- Latency per LLM call when first made: median 1.88 s, p90 3.38 s (wall time of the client call, retries included, one network).

## By base case

- False clears: 1 calls in 1 of 36 base cases (B03).
- False alarms: 0 calls in 0 of 36 base cases; gold-clear base cases: 9.
- Any wrong call verdict: 1 calls in 1 of 36 base cases (B03).
- Any wrong field: 16 calls in 7 of 36 base cases (B01, B03, G01, G02, G05, U08, U10).
- `consent_given` where the customer agreed to a misdescribed product (C02, U08, V04, V06; the set expects true and calls false a defensible reading): 16/16 match the set. All other calls: 127/128.
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

### U08-ta (ta): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Customer believes the cover is an investment plan that grows [violating, target rule kind]
- field `recall_items`: gold `((('P1', <KindClaim.investment: 'investment'>), 1),)`, pipeline `(((None, None), 1),)`
  - turn 10 [recall] bot: "லோனுடன் நீங்கள் என்னென்ன எடுத்தீர்கள், எவ்வளவுக்கு?" customer: "லோனோட ஒரு பிளான்ல பணம் போட்டேன், இருபத்தையாயிரம் ரூபாய்."
  - pipeline kept: None:"லோனோட ஒரு பிளான்ல பணம் போட்டேன்"->None
- flag not in gold: `recall` on P1: customer did not name this product unprompted | quote: "லோனோட ஒரு பிளான்ல பணம் போட்டேன், இருபத்தையாயிரம் ரூபாய்."

### U08-kn (kn): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Customer believes the cover is an investment plan that grows [violating, target rule kind]
- field `recall_items`: gold `((('P1', <KindClaim.investment: 'investment'>), 1),)`, pipeline `(((None, None), 1),)`
  - turn 10 [recall] bot: "ಲೋನ್ ಜೊತೆ ನೀವು ಏನೇನು ತೆಗೆದುಕೊಂಡಿರಿ, ಎಷ್ಟಕ್ಕೆ?" customer: "ಲೋನ್ ಜೊತೆ ಒಂದು ಪ್ಲಾನಲ್ಲಿ ದುಡ್ಡು ಹಾಕಿದೆ, ಇಪ್ಪತ್ತೈದು ಸಾವಿರ ರೂಪಾಯಿ."
  - pipeline kept: None:"ಲೋನ್ ಜೊತೆ ಒಂದು ಪ್ಲಾನಲ್ಲಿ ದುಡ್ಡು ಹಾಕಿದೆ"->None
- flag not in gold: `recall` on P1: customer did not name this product unprompted | quote: "ಲೋನ್ ಜೊತೆ ಒಂದು ಪ್ಲಾನಲ್ಲಿ ದುಡ್ಡು ಹಾಕಿದೆ, ಇಪ್ಪತ್ತೈದು ಸಾವಿರ ರೂಪಾಯಿ."

### U10-hi (hi): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Customer who answers 'I don't know' to almost everything [violating, target rule cover]
- field `consent_method`: gold `('dont_know', None)`, pipeline `('unclear', None)`
  - turn 28 [consent] bot: "लोन लेते समय आपने क्या-क्या लेने के लिए हामी भरी थी, और हामी कैसे दी थी?" customer: "ये मुझे नहीं पता कि किस-किस चीज़ के लिए हाँ हुई थी।"
  - pipeline kept: "ये मुझे नहीं पता कि किस-किस चीज़ के लिए हाँ हुई थी।" (turn 28)

### U10-hi-en (hi-en): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Customer who answers 'I don't know' to almost everything [violating, target rule cover]
- field `consent_method`: gold `('dont_know', None)`, pipeline `('unclear', None)`
  - turn 28 [consent] bot: "Loan लेते समय आपने क्या-क्या लेने के लिए हाँ की थी, और हाँ कैसे की थी?" customer: "ये मुझे नहीं पता कि किस-किस चीज़ के लिए agree किया था।"
  - pipeline kept: "ये मुझे नहीं पता कि किस-किस चीज़ के लिए agree किया था।" (turn 28)

### U10-ta (ta): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Customer who answers 'I don't know' to almost everything [violating, target rule cover]
- field `cancel_allowed`: gold `('dont_know', None)`, pipeline `('unclear', None)`
  - turn 24 [cancel_window] bot: "அதை ரத்து செய்ய முடியுமா முடியாதா, எத்தனை நாளுக்குள் என்று உங்களிடம் சொன்னார்களா?" customer: "கேன்சல் பண்ண முடியுமா முடியாதான்னு தெரியல."
  - pipeline kept: "கேன்சல் பண்ண முடியுமா முடியாதான்னு தெரியல." (turn 24)
- field `consent_method`: gold `('dont_know', None)`, pipeline `('unclear', None)`
  - turn 28 [consent] bot: "லோன் வாங்கும்போது நீங்கள் என்னென்ன எடுக்க ஒப்புக்கொண்டீர்கள், எப்படி ஒப்புதல் கொடுத்தீர்கள்?" customer: "எது எதுக்கு ஒத்துக்கிட்டேன்னு எனக்கு தெரியலங்க."
  - pipeline kept: "எது எதுக்கு ஒத்துக்கிட்டேன்னு எனக்கு தெரியலங்க." (turn 28)
- missed flag: `cancel_window` on P1

### U10-kn (kn): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Customer who answers 'I don't know' to almost everything [violating, target rule cover]
- field `consent_method`: gold `('dont_know', None)`, pipeline `('unclear', None)`
  - turn 28 [consent] bot: "ಲೋನ್ ತೆಗೆದುಕೊಳ್ಳುವಾಗ ನೀವು ಏನೇನು ತೆಗೆದುಕೊಳ್ಳಲು ಒಪ್ಪಿದ್ದಿರಿ, ಒಪ್ಪಿಗೆ ಹೇಗೆ ಕೊಟ್ಟಿರಿ?" customer: "ಯಾವುದಕ್ಕೆಲ್ಲ ಒಪ್ಪಿದ್ದೆ ಅಂತ ನನಗೆ ಗೊತ್ತಿಲ್ಲ."
  - pipeline kept: "ಯಾವುದಕ್ಕೆಲ್ಲ ಒಪ್ಪಿದ್ದೆ ಅಂತ ನನಗೆ ಗೊತ್ತಿಲ್ಲ." (turn 28)

### G01-ta (ta): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Two lakh debited from the borrower's account for a policy, no consent on record [violating, target rule consent]
- field `consent_method`: gold `('unclear', None)`, pipeline `('stated', <ConsentMethod.verbal: 'verbal'>)`
  - turn 28 [consent] bot: "லோன் வாங்கும்போது நீங்கள் என்னென்ன எடுக்க ஒப்புக்கொண்டீர்கள், எப்படி ஒப்புதல் கொடுத்தீர்கள்?" customer: "நான் லோனுக்கு மட்டும்தான் சரின்னு சொன்னேன். இன்ஷூரன்ஸ் பத்தி என்கிட்ட யாரும் கேக்கல. எனக்கு அப்புறம்தான் தெரிஞ்சுது, அக்கவுண்ட்ல இருந்து பணம் போனப்ப."
  - pipeline kept: "நான் லோனுக்கு மட்டும்தான் சரின்னு சொன்னேன். இன்ஷூரன்ஸ் பத்தி என்கிட்ட யாரும் கேக்கல. எனக்கு அப்புறம்தான் தெரிஞ்சுது, அக்கவுண்ட்ல இருந்து பணம் போனப்ப." (turn 28)

### G01-kn (kn): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Two lakh debited from the borrower's account for a policy, no consent on record [violating, target rule consent]
- field `premium_inr`: gold `('stated', 200000)`, pipeline `('unclear', None)`
  - turn 14 [premium] bot: "ಅದಕ್ಕೆ ನೀವು ಎಷ್ಟು ರೂಪಾಯಿ ಕೊಟ್ಟಿರಿ?" customer: "ಎರಡು ಲಕ್ಷ ರೂಪಾಯಿ ತಗೊಂಡಿದ್ದಾರೆ."
  - turn 30 [readback] bot: "ಎರಡು ಲಕ್ಷ, ಅಂದರೆ 2,00,000 ರೂಪಾಯಿ, ಸರಿಯೇ?" customer: "ಹೌದು, ಸರಿ."
  - pipeline kept: "ಎರಡು ಲಕ್ಷ ರೂಪಾಯಿ ತಗೊಂಡಿದ್ದಾರೆ." (turn 14)

### G02-hi (hi): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Signed consent on file; the customer says they agreed only to the loan [violating, target rule consent]
- field `consent_method`: gold `('unclear', None)`, pipeline `('stated', <ConsentMethod.signed_form: 'signed_form'>)`
  - turn 28 [consent] bot: "लोन लेते समय आपने क्या-क्या लेने के लिए हामी भरी थी, और हामी कैसे दी थी?" customer: "मैंने तो बस लोन के लिए हाँ बोली थी। बीमे के लिए मुझसे किसी ने नहीं पूछा। बहुत सारे काग़ज़ों पर साइन करवाए थे, किसी ने बताया नहीं कौन सा किस चीज़ का है।"
  - pipeline kept: "मैंने तो बस लोन के लिए हाँ बोली थी। बीमे के लिए मुझसे किसी ने नहीं पूछा। बहुत सारे काग़ज़ों पर साइन करवाए थे, किसी ने बताया नहीं कौन सा किस चीज़ का है।" (turn 28)

### G02-hi-en (hi-en): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Signed consent on file; the customer says they agreed only to the loan [violating, target rule consent]
- field `consent_method`: gold `('unclear', None)`, pipeline `('stated', <ConsentMethod.signed_form: 'signed_form'>)`
  - turn 28 [consent] bot: "Loan लेते समय आपने क्या-क्या लेने के लिए हाँ की थी, और हाँ कैसे की थी?" customer: "सिर्फ़ loan। Insurance लेने की हामी मैंने कभी नहीं भरी। बहुत सारे papers पर sign करवाए थे, किसी ने बताया नहीं कौन सा किस चीज़ का है।"
  - pipeline kept: "सिर्फ़ loan। Insurance लेने की हामी मैंने कभी नहीं भरी। बहुत सारे papers पर sign करवाए थे, किसी ने बताया नहीं कौन सा किस चीज़ का है।" (turn 28)

### G02-ta (ta): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Signed consent on file; the customer says they agreed only to the loan [violating, target rule consent]
- field `consent_method`: gold `('unclear', None)`, pipeline `('stated', <ConsentMethod.signed_form: 'signed_form'>)`
  - turn 28 [consent] bot: "லோன் வாங்கும்போது நீங்கள் என்னென்ன எடுக்க ஒப்புக்கொண்டீர்கள், எப்படி ஒப்புதல் கொடுத்தீர்கள்?" customer: "லோன் மட்டும்தான். இன்ஷூரன்ஸ் எடுக்க நான் ஒருநாளும் ஒத்துக்கல. நிறைய பேப்பர்ல கையெழுத்து வாங்கினாங்க, எது எதுக்குன்னு யாரும் சொல்லல."
  - pipeline kept: "லோன் மட்டும்தான். இன்ஷூரன்ஸ் எடுக்க நான் ஒருநாளும் ஒத்துக்கல. நிறைய பேப்பர்ல கையெழுத்து வாங்கினாங்க, எது எதுக்குன்னு யாரும் சொல்லல." (turn 28)

### G02-kn (kn): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Signed consent on file; the customer says they agreed only to the loan [violating, target rule consent]
- field `consent_method`: gold `('unclear', None)`, pipeline `('stated', <ConsentMethod.signed_form: 'signed_form'>)`
  - turn 28 [consent] bot: "ಲೋನ್ ತೆಗೆದುಕೊಳ್ಳುವಾಗ ನೀವು ಏನೇನು ತೆಗೆದುಕೊಳ್ಳಲು ಒಪ್ಪಿದ್ದಿರಿ, ಒಪ್ಪಿಗೆ ಹೇಗೆ ಕೊಟ್ಟಿರಿ?" customer: "ಲೋನ್ ಮಾತ್ರ. ಇನ್ಶೂರೆನ್ಸ್ ತಗೊಳ್ಳೋಕೆ ನಾನು ಯಾವತ್ತೂ ಒಪ್ಪಿಲ್ಲ. ತುಂಬಾ ಪೇಪರಿಗೆ ಸಹಿ ಹಾಕಿಸ್ಕೊಂಡ್ರು, ಯಾವುದು ಯಾವುದಕ್ಕೆ ಅಂತ ಯಾರೂ ಹೇಳಿಲ್ಲ."
  - pipeline kept: "ಲೋನ್ ಮಾತ್ರ. ಇನ್ಶೂರೆನ್ಸ್ ತಗೊಳ್ಳೋಕೆ ನಾನು ಯಾವತ್ತೂ ಒಪ್ಪಿಲ್ಲ. ತುಂಬಾ ಪೇಪರಿಗೆ ಸಹಿ ಹಾಕಿಸ್ಕೊಂಡ್ರು, ಯಾವುದು ಯಾವುದಕ್ಕೆ ಅಂತ ಯಾರೂ ಹೇಳಿಲ್ಲ." (turn 28)

### G05-ta (ta): gold `unclear_needs_human`, pipeline `unclear_needs_human`
Scenario: Customer agreed to the insurance but cannot say how [near_miss, target rule consent]
- field `consent_given`: gold `('stated', True)`, pipeline `('unclear', None)`
  - turn 28 [consent] bot: "லோன் வாங்கும்போது நீங்கள் என்னென்ன எடுக்க ஒப்புக்கொண்டீர்கள், எப்படி ஒப்புதல் கொடுத்தீர்கள்?" customer: "ரெண்டுக்கும் ஒத்துக்கிட்டேன். ஆனா எப்படி ஒத்துக்கிட்டேன்னு ஞாபகம் வரல."
  - pipeline kept: "ரெண்டுக்கும் ஒத்துக்கிட்டேன். ஆனா எப்படி ஒத்துக்கிட்டேன்னு ஞாபகம் வரல." (turn 28)

### B01-ta (ta): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Knows it is a policy; believes the money can be withdrawn after one year [violating, target rule belief_mismatch]
- field `feature_probe`: gold `('stated', (<FeatureClaim.withdrawable_after_period: 'withdrawable_after_period'>,))`, pipeline `('stated', (<FeatureClaim.refundable_anytime: 'refundable_anytime'>, <FeatureClaim.withdrawable_after_period: 'withdrawable_after_period'>))`
  - turn 26 [features] bot: "அந்தப் பணத்தை நீங்கள் திரும்பக் கேட்டால் கிடைக்குமா, எப்போது?" customer: "ஆமா, ஒரு வருஷம் கழிச்சு எப்ப வேணும்னாலும் எடுத்துக்கலாம்னு சொன்னாங்க."
  - pipeline kept: "ஆமா, ஒரு வருஷம் கழிச்சு எப்ப வேணும்னாலும் எடுத்துக்கலாம்னு சொன்னாங்க." (turn 26)

### B01-kn (kn): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Knows it is a policy; believes the money can be withdrawn after one year [violating, target rule belief_mismatch]
- field `feature_probe`: gold `('stated', (<FeatureClaim.withdrawable_after_period: 'withdrawable_after_period'>,))`, pipeline `('stated', (<FeatureClaim.refundable_anytime: 'refundable_anytime'>, <FeatureClaim.withdrawable_after_period: 'withdrawable_after_period'>))`
  - turn 26 [features] bot: "ಆ ಹಣವನ್ನು ನೀವು ವಾಪಸ್ ಕೇಳಿದರೆ ಸಿಗುತ್ತದೆಯೇ, ಯಾವಾಗ?" customer: "ಹೌದು, ಒಂದು ವರ್ಷ ಆದ್ಮೇಲೆ ಯಾವಾಗ ಬೇಕಾದ್ರೂ ತಗೋಬಹುದು ಅಂತ ಹೇಳಿದ್ರು."
  - pipeline kept: "ಹೌದು, ಒಂದು ವರ್ಷ ಆದ್ಮೇಲೆ ಯಾವಾಗ ಬೇಕಾದ್ರೂ ತಗೋಬಹುದು ಅಂತ ಹೇಳಿದ್ರು." (turn 26)

### B03-ta (ta): gold `flag_for_review`, pipeline `clear` **FALSE CLEAR**
Scenario: Believes the premium is paid only once; the record shows a regular-premium product [violating, target rule belief_mismatch]
- field `volunteered_claims`: gold `(('P1', <FeatureClaim.one_time_payment: 'one_time_payment'>),)`, pipeline `()`
  - pipeline kept: -
  - gold has: one_time_payment:"ஒரே தடவைதான், ஐம்பத்திரண்டாயிரம் ரூபாய்."
- missed flag: `belief_mismatch` on P1
