# P3a contract: decision chain v2 public types and signatures

Written 2026-11-10 by the P3a execution manager. Other packages may code against this now.
After this point changes are additive only. `samajh/types.py` is the source if the two differ.

Nothing that exists today is removed or renamed. `Verdict`, `ProductResult.verdict` and
`CaseResult.verdict` keep their meaning (any flag gives `flag_for_review`). They stay because the
frozen gold is written in them. New code reads `tier`.

## 1. Triage tier

```python
class Tier(StrEnum):            # samajh.types
    refer = "refer"                         # a human must look
    incomplete = "incomplete"               # the call did not yield enough to decide
    understanding_gap = "understanding_gap" # reported in aggregate, not queued
    clear = "clear"

ProductResult.tier: Tier        # required field, validated against its flags and gaps
CaseResult.tier: Tier           # worst of the products and the case-level flags and gaps
Flag.tier -> Tier               # property
Gap.tier -> Tier                # property
tier_of(flags, gaps) -> Tier    # samajh.types: the one pure function. Order: refer > incomplete > understanding_gap > clear
```

Every flag and gap is still in `flags` and `gaps`. The tier is derived from them and from nothing else.

| Tier | Flags (by `Flag.reason`) | Gaps (by `Gap.rule_id`) |
|---|---|---|
| `refer` | `kind_*`, `premium_differs_confirmed`, `cover_differs_confirmed`, `recall_denied`, `recall_off_record`, `consent_*`, `funded_*`, `unfunded_says_deducted`, `bundled_*`, `feature_contradicted`, `sale_concern`, `answers_conflict` on a refer-tier rule | none |
| `incomplete` | `premium_differs`, `cover_differs_unconfirmed` (a differing plain figure the customer never confirmed at a read-back) | `kind`, `premium`, `consent`, `loan_funded`, `bundling`, `belief_mismatch`, `recall_unmatched`, `sale_conduct`, `evidence` |
| `understanding_gap` | `premium_dont_know`, `premium_approximate`, `cover_differs` (hedged or approximate), `cover_dont_know`, `term_*`, `cancel_*`, `recall_not_named`, `feature_dont_know`, `frequency_recurring_on_single`, `frequency_dont_know`, `answers_conflict` on cover, term or cancel window | `cover`, `term`, `cancel_window`, `recall` |
| `clear` | no flag and no gap | |

Silence is never a pass: a refer-tier question with no usable answer is a gap, so the product is `incomplete`.

Changed 2026-11-10 after the iteration-2 verifier (additive):
- Cover (coordinator decision): a plain, unhedged cover figure outside the 1% tolerance is
  `cover_differs_confirmed` (refer) once the customer confirmed a read-back of that figure, and
  `cover_differs_unconfirmed` (incomplete) until then. Hedged or approximate stays `cover_differs`
  (understanding_gap); "I don't know" stays `cover_dont_know`. Term and window are unchanged.
- `recall_denied` is refer while the denial stands (coordinator decision, second round). If the
  customer then names this product themselves as the kind on record (a later recall reply, or the
  kind question), the denial is retracted: `recall_not_named` (understanding_gap), quote = the
  denial, `also` = the naming. Another kind, "I don't know" or nothing asked: it stands.
- A stated answer whose reply takes it back in a later clause ("…, ऐसा तो नहीं था", "नहीं नहीं",
  "मतलब वो नहीं", "galat bola", "actually no") is `Unclear(no_usable_answer)`; with a different
  answer after the retraction it is also an `answers_conflict` (two clause quotes from the one
  reply). Read by code over the whole reply (`samajh.rules.normalise.retraction`).
- A confirmed range wider than `MAX_RANGE_RATIO` (2) times its low end never passes: a
  `not_comparable` gap on premium or cover.

## 2. Flag and Gap

```python
class FlagReason(StrEnum)       # samajh.types. The old samajh.rules.checks.Why is now an alias of it.
# existing values keep their names; new: answers_conflict, premium_approximate, recall_denied,
# frequency_recurring_on_single, frequency_dont_know

class Flag(Frozen):
    ...                                     # rule_id, clause, product_id, severity, expected, heard, quote, turn_id: unchanged
    reason: FlagReason                      # NEW, required
    claim: FeatureClaim | None = None       # NEW: the belief, on a feature_contradicted flag
    also: tuple[Evidence, ...] = ()         # NEW: further quotes; a conflict flag holds every differing answer here after `quote`

class GapReason(StrEnum):       # NEW values
    extraction_failed = "extraction_failed" # the model gave no valid output for this reply
    not_comparable = "not_comparable"       # a usable answer the record gives nothing to compare with
```

## 3. Answers

```python
class Stated(Frozen, Generic[T]):
    value: T
    evidence: Evidence
    hedged: bool = False            # NEW: said with a word of doubt ("शायद", "I think"). A marker only: it never turns a wrong answer into a pass
    approximate: bool = False       # NEW: an amount said as "about X" or as a range
    low: StrictInt | None = None    # NEW: lower end of a spoken range; `value` is the upper end. Set only with approximate=True

class PaymentFrequency(StrEnum):    # NEW
    one_time = "one_time"
    recurring = "recurring"

Question.payment_frequency = "payment_frequency"        # NEW value. Tag the bot turn with asks=payment_frequency and the product_id

class AnswerConflict(Frozen):       # NEW: one question asked more than once, with differing usable answers
    question: Question
    answers: tuple[Evidence, ...]   # in call order, at least two, each the customer's whole reply

# on RawProductAnswers and ProductBeliefs (both default to "not asked" / empty):
payment_frequency: Answer[PaymentFrequency] = NotAsked()
conflicts: tuple[AnswerConflict, ...] = ()

# open recall (RawOpenRecall and OpenRecall):
denial: Evidence | None = None      # NEW: the customer says they took nothing with the loan

LoanRecord.tenure_months: Count | None = None   # NEW, optional: lets "as long as the loan runs" be compared with the term
RawExtraction.unscreened: tuple[Evidence, ...] = ()  # NEW: replies whose screening call failed
Beliefs.unscreened: tuple[Evidence, ...] = ()
```

**Cover read-back (new, for the dialogue).** No new `Question` value: tag the bot turn exactly like
the premium read-back, with `step=read_back`, `asks=cover` and the `product_id`. Its reply fills
the new field `cover_readback: Answer[StrictBool] = NotAsked()` on `RawProductAnswers` and
`ProductBeliefs` (`SlotKind.cover_readback` in the extractor). The bot line must carry the
customer's figure (or both ends of a range), as for the premium; a correction in reply replaces
the cover.

`Stated.also: tuple[Evidence, ...] = ()` (new): the other replies to the same question that the
answer stands over, such as an earlier "I don't know". Conflicts are only stated answers that
are incompatible (amounts beyond tolerance of each other, different enums or durations); a
failed model call on any asking of a question makes its fields `Unclear(extraction_failed)`.

Payment frequency is checked only when the transcript has a bot turn tagged `asks=payment_frequency`.
"Paid once" on a product without `one_time_payment` in `features` is a `feature_contradicted` flag
under `belief_mismatch` (refer). A transcript that never asks it gets no flag and no gap from it.

## 4. Amounts (`samajh.amounts`)

```python
parse_amount(text, *, exact=False) -> Parsed | Ambiguous | NoAmount       # same types as today
class Approximate(Frozen):          # NEW
    status: Literal["approximate"]
    low: int                        # low == high for "about fifty thousand"
    high: int
    span: Span
parse_approx_amount(text, *, exact=False) -> Parsed | Approximate | Ambiguous | NoAmount   # NEW
has_doubt_word(text) -> bool        # NEW: a word of doubt or approximation is in the text
MAX_RANGE_RATIO = 2; too_wide(low, high) -> bool   # NEW: the one bound on range width, for parser and rules
is_loan_tenure(text) -> bool        # NEW: a duration given relative to the loan ("जब तक लोन चलेगा")
```

- `parse_amount` keeps its return types. One behaviour change: a word the lexicon does not know that
  stands directly before a number and is close to a fraction or unit word ("सारे तीन लाख",
  "pauney 2 lakh") now gives `Ambiguous(malformed)`. Before, the word was dropped.
- `parse_approx_amount` reads what `parse_amount` refuses as hedged: "करीब पचास हज़ार" is
  `Approximate(50000, 50000)`, "पचास बावन हज़ार के आसपास" and "50 से 52 हज़ार" are
  `Approximate(50000, 52000)`. A correction ("बावन नहीं पचपन हज़ार") stays `Ambiguous`.
- The premium rule: within 1% of the record and confirmed at the read-back passes. Within the
  approximate tolerance (10%, range-aware) and confirmed is a `premium_approximate` flag (low,
  `understanding_gap`). Further off and confirmed is `premium_differs_confirmed` (`refer`).
- **Read-back contract for the dialogue.** A premium still passes only after a confirmed read-back of
  the same figure. For an approximate answer the bot line must carry the same figures: the code reads
  the bot's read-back line with `parse_approx_amount` and requires the same `(low, high)`. For a
  single figure nothing changes.

## 5. Extraction and pipeline

```python
extract(transcript, record, llm, *, model=None, max_workers=8) -> RawExtraction
extract_traced(transcript, record, llm, *, model=None, max_workers=8) -> Extraction
run_text(transcript, record, llm, *, model=None, max_workers=8) -> TextRun
run_text_case(transcript, record, llm=None) -> CaseResult
```

- Requests for one transcript run in parallel threads; the result does not depend on `max_workers`.
- A bad or failed model output no longer raises. The fields of that reply become
  `Unclear(reason=extraction_failed)`; a failed screening call is listed in `unscreened` and becomes a
  case-level gap. `CapExceeded`, `AuthError` and `ConfigError` still raise.
- A question asked twice keeps every answer: the field holds the last usable answer and
  `conflicts` holds the differing ones. The rules turn a conflict into an `answers_conflict` flag.

## 6. Case summary for a reviewer (`samajh.rules`)

```python
class IssueLine(Frozen):
    product_id: ProductId | None    # None for a case-level line
    tier: Tier
    title: str                      # one plain sentence: what the issue is
    record_value: str               # what the lender's record shows
    quote: str | None               # the customer's best quote
    turn_id: TurnId | None
    clauses: tuple[str, ...]        # the paragraphs the merged flags may engage
    rule_ids: tuple[RuleId, ...]    # the rules merged into this line

class CaseSummary(Frozen):
    loan_id: str
    call_id: str
    tier: Tier
    lines: tuple[IssueLine, ...]    # refer first, then incomplete, then understanding gaps; one per distinct
                                    # refer issue, and one per rule for incomplete and understanding-gap lines

summarise(record: LoanRecord, result: CaseResult) -> CaseSummary      # pure
```

A flag is evidence for review and never a finding. No line says "mis-selling" or "refund".
