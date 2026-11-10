# Negation probe

24 reviewer-written Hindi and Hinglish replies, max_tokens 4000. Each reply is built so that its first clause, read alone, gives the opposite answer. Not a sample of real speech: it shows a failure pattern, not a rate.

## `mistralai/mistral-small-3.2-24b-instruct`: 20 of 24 read correctly

- [consent] "बीमा के लिए हामी भरी थी, ऐसा मुझे याद नहीं, मैंने तो सिर्फ़ लोन के कागज़ पर दस्तखत किए।"
  - correct: not given=true
  - model: `{"given_status": "stated", "given": true, "given_clauses": [1], "method_status": "stated", "method": "signed_form", "method_clauses": [3]}`
- [consent] "Policy के लिए agree किया, ये गलत है, मैंने सिर्फ loan के लिए OTP दिया था."
  - correct: not given=true
  - model: `{"given_status": "stated", "given": true, "given_clauses": [1], "method_status": "stated", "method": "otp", "method_clauses": [3]}`
- [features] "जब चाहूँ निकाल सकता हूँ, ऐसा नहीं है, यह बीमा है।"
  - correct: no refundable_anytime
  - model: `{"status": "stated", "claims": ["refundable_anytime"], "clauses": [1]}`
- [features] "Interest के साथ वापस मिलेगा, ऐसा पहले लगा था, पर अब पता है कि नहीं मिलता."
  - correct: no guaranteed_return
  - model: `{"status": "stated", "claims": ["guaranteed_return"], "clauses": [1]}`

## `google/gemini-2.5-flash-lite`: 18 of 24 read correctly

- [required_for_loan] "ज़रूरी था, ऐसा तो किसी ने नहीं कहा।"
  - correct: not yes=true
  - model: `{"status": "stated", "yes": true, "clauses": [1]}`
- [cancel_window] "Cancel कर सकते हैं, ये नहीं बताया था, बस sign करवा लिया."
  - correct: not allowed=true
  - model: `{"allowed_status": "stated", "allowed": true, "allowed_clauses": [1], "window_status": "unclear", "window_span": null, "window_clauses": []}`
- [consent] "बीमा के लिए हामी भरी थी, ऐसा मुझे याद नहीं, मैंने तो सिर्फ़ लोन के कागज़ पर दस्तखत किए।"
  - correct: not given=true
  - model: `{"given_status": "stated", "given": true, "given_clauses": [1], "method_status": "stated", "method": "signed_form", "method_clauses": [3]}`
- [consent] "Policy के लिए agree किया, ये गलत है, मैंने सिर्फ loan के लिए OTP दिया था."
  - correct: not given=true
  - model: `{"given_status": "stated", "given": true, "given_clauses": [1], "method_status": "stated", "method": "otp", "method_clauses": [3]}`
- [features] "जब चाहूँ निकाल सकता हूँ, ऐसा नहीं है, यह बीमा है।"
  - correct: no refundable_anytime
  - model: `{"status": "stated", "claims": ["refundable_anytime"], "clauses": [1, 3]}`
- [screen] "किसी ने नहीं कहा कि हर बात पर हाँ कहना, मैं अपनी समझ से बता रहा हूँ।"
  - correct: no coached_answers
  - model: `{"claims": [], "concerns": [{"concern": "coached_answers", "span": "किसी ने नहीं कहा कि हर बात पर हाँ कहना"}]}`

## `openai/gpt-6-luna`: 24 of 24 read correctly


## `anthropic/claude-haiku-5.5`: 24 of 24 read correctly

