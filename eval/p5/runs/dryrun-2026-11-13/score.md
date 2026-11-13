# P5 text path: dryrun-2026-11-13

Synthetic customers, scripted replies, text only (no audio). Counts per 100 with n and a Wilson 95% interval on customers, by kind; no pooled rate. A referral is evidence for human review, never a finding. Above level 0 each arm stands on its own: no open-minus-closed difference is computed (contract section 8).

**Closed, lenient** (a sensitivity reading, reported apart; the primary closed outcome is the interpreter's yes/no/other as built). A statement counts as a yes when the interpreter said yes, or when all of these hold: (a) the reply's first word is one of haan, han, ji, sahi, yes, जी, ठीक, सही, हाँ, हाँजी, हां, हांजी; (b) neither of its first two words is a negation word (galat, na, nahi, nahin, never, no, not, wrong, गलत, ग़लत, न, नही, नहीं, ना, मत); (c) the reply holds no negation word anywhere, unless the statement's own claim (the sentence before the final "is that correct?") holds one, in which case a repeated negation is the claim agreed with. Words are split on spaces and the marks , . ! ? । - and compared in lower case. Fixed before any counting run; not tuned on outcomes.

## 1. Misses per 100 customers with a problem

Open miss: tier clear or understanding_gap. Closed miss: confirmed. `incomplete` and `ended early` are neither; the denominator n is every customer with a result.

| arm | level | kind | n | caught | miss | incomplete | ended early | no result | misses per 100 [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| closed | 0 | misled | 1 | 1 | 0 | 0 | 0 | 0 | 0 [0-79] |
| open | 0 | misled | 1 | 1 | 0 | 0 | 0 | 0 | 0 [0-79] |

## 2. Referrals per 100 customers without a problem

| arm | level | gold class | kind | n | referred | clear | gap | incomplete | confirmed | ended early | no result | referrals per 100 [95% CI] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| closed | 0 | no_problem | well_informed | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 100 [21-100] |
| open | 0 | no_problem | well_informed | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 [0-79] |

## 3. What open referrals rest on

| arm | level | gold class | customer statement | record only |
|---|---|---|---|---|
| open | 0 | problem | 1 | 0 |

## 4. Opening kinds (open arm only)

Third parties: loan named = any bot line `context.loan` or `verify.after_loan`, or of a later step. Refusals: a further question = any bot utterance after the first turn read as a refusal (decline, maybe_decline, no, do_not_call).

| level | kind | n | expected outcome reached | per 100 [95% CI] | outcomes | loan named | refusal: asked further / about the loan / refusal not read | no result |
|---|---|---|---|---|---|---|---|---|
| 0 | refusal | 1 | 1 | 100 [21-100] | declined: 1 |  | 0 / 0 / 0 | 0 |
| 0 | third_party | 1 | 1 | 100 [21-100] | wrong_party: 1 | 0 |  | 0 |

## 5. Open against closed, paired by customer, level 0 only

`caught` = referred (open tier refer; closed not confirmed). Exact McNemar on the discordant pairs.

| gold class | kind | pairs | both | open only | closed only | neither | no-result pairs | McNemar p |
|---|---|---|---|---|---|---|---|---|
| no_problem_or_gap | all kinds | 1 | 0 | 0 | 1 | 0 | 0 | 1.0 |
| no_problem_or_gap | well_informed | 1 | 0 | 0 | 1 | 0 | 0 | 1.0 |
| problem | all kinds | 1 | 1 | 0 | 0 | 0 | 0 | 1.0 |
| problem | misled | 1 | 1 | 0 | 0 | 0 | 0 | 1.0 |

## 6. By writer model

| arm | level | writer model | gold class | n | counts | count | no result | per 100 [95% CI] |
|---|---|---|---|---|---|---|---|---|
| closed | 0 | google/gemini-3.7-flash | no_problem | 1 | referred | 1 | 0 | 100 [21-100] |
| closed | 0 | google/gemini-3.7-flash | problem | 1 | miss | 0 | 0 | 0 [0-79] |
| open | 0 | google/gemini-3.7-flash | no_problem | 1 | referred | 0 | 0 | 0 [0-79] |
| open | 0 | google/gemini-3.7-flash | problem | 1 | miss | 0 | 0 | 0 [0-79] |

## 7. Degraded turns and unmapped lines

| arm | level | calls | customer turns | degraded turns | unmapped lines | unmapped keys | no result |
|---|---|---|---|---|---|---|---|
| closed | 0 | 2 | 26 | 0 | 0 | none | 0 |
| open | 0 | 4 | 33 | 0 | 0 | none | 0 |

## 8. No-result calls

None.

## 9. Closed arm under both readings (lenient: a sensitivity, see the rule at the top)

| level | gold class | kind | n | confirmed (primary) | confirmed (lenient) | ended early | no result |
|---|---|---|---|---|---|---|---|
| 0 | no_problem | well_informed | 1 | 0 | 1 | 0 | 0 |
| 0 | problem | misled | 1 | 0 | 0 | 0 | 0 |

Paired open against closed at level 0, closed read leniently:

| gold class | kind | pairs | both | open only | closed only | neither | no-result pairs | McNemar p |
|---|---|---|---|---|---|---|---|---|
| no_problem_or_gap | all kinds | 1 | 0 | 0 | 0 | 1 | 0 | 1.0 |
| no_problem_or_gap | well_informed | 1 | 0 | 0 | 0 | 1 | 0 | 1.0 |
| problem | all kinds | 1 | 1 | 0 | 0 | 0 | 0 | 1.0 |
| problem | misled | 1 | 1 | 0 | 0 | 0 | 0 | 1.0 |

## 10. Closed statements read as no or other, customers without a problem (verbatim)

| customer | kind | gold class | level | statement | reply | reading | lenient yes |
|---|---|---|---|---|---|---|---|
| P5-C029 | well_informed | no_problem | 0 | c_not_savings | हाँ, मैं जानती हूँ कि यह बचत नहीं है और पैसे वापस नहीं मिलेंगे। | no | True |
