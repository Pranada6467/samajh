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
- Cover (coordinator decision; `samajh.rules.checks.cover`): a plain, unhedged cover figure
  outside the 1% tolerance is `cover_differs_confirmed` (refer) once the customer confirmed a
  read-back of that figure, and `cover_differs_unconfirmed` (incomplete) until then. A confirmed
  read-back followed by the same figure restated stays confirmed (refer). Asking a read-back does
  not lower the tier against not asking it: a plain differing figure whose read-back was rejected
  without a correction, or mismatched (`Unclear(readback_mismatch)`), is `incomplete`. A figure
  that matches the record is a `readback_rejected` or `readback_mismatch` gap when its read-back
  was rejected or mismatched. A figure the customer gave as a correction at the read-back has had
  no read-back of its own and is judged as if none was asked: the bot read back the customer's
  earlier figure, not the record's. Hedged or approximate stays `cover_differs`
  (understanding_gap); "I don't know" stays `cover_dont_know`. Term and window are unchanged.
- `recall_denied` is refer while the denial stands (coordinator decision, second round;
  `samajh.rules.checks.recall`). The denial is retracted only when the customer names this
  product as the kind on record in a turn AFTER the denial: a later recall item of that kind
  matched to this product, or the kind question answered as that kind. Then the finding is
  `recall_not_named` (understanding_gap), quote = the denial, `also` = the later namings. A naming
  before the denial or in the same turn, a misdescription ("an FD" for insurance), an item with no
  kind, "I don't know" or nothing asked: the denial stands (`refer`). The extractor keeps the last
  denial.
- Retractions and corrections inside one reply are judged by the extractor's change check (§5),
  not by a phrase list in code. Coordinator decision ("option A"): A correction inside one reply
  that ends on an answer: the final answer stands when both model readings agree which clause holds
  it; the earlier words are kept in `Stated.also` and shown whenever the case is opened; no conflict
  flag. The model only names clauses; code grounds every quote as a verbatim whole clause and
  decides. If the readings disagree on the clause, or the answer is withdrawn with nothing in its
  place, it is unusable (`incomplete`). Conflicts across two askings stay `refer`. A correction TO
  a wrong answer refers through the value: 'बीमा... अरे नहीं, एफ़डी है' on an insurance record is
  `refer`; 'डिपॉज़िट... अरे नहीं, बीमा है, बीमा' is `clear`.
  As built: the earlier words are also listed on `ProductResult.self_corrections` (§3) for every
  case; the reviewer summary (§6) adds a note line per self-correction on every case, clear ones
  included; the line has tier `clear` and `note=True` and is never part of the case tier. A read-back "yes" that is
  taken back is unusable.
- This protection rests on two model readings plus code grounding, not on code alone. A reply of
  one clause gets no change check. A `RawExtraction` built by anything other than
  `samajh.extract` gets no retraction protection in `samajh.rules`.
  Measured by the independent verifier on typed text with gpt-6-luna
  (`references/reviews/iter2/verify-P3a-r3.md`): on replies of two or more clauses, the taken-back
  value was the stated belief in 0 of 19 corrections away from the record value, and 0 of 6
  withdrawals ended `clear`; on unpunctuated replies (one clause, so no check) 4 of 10 withdrawals
  ended `clear` with the withdrawn value stated. So "a retraction never yields a stated value" is
  not a claim this contract makes. The `ChangeReply` docstring is sent to the model as the
  schema's description: it is part of the prompt, and rewording it changed 1 of 1,107 frozen-set
  readings (restored; see `P3a-report.md`).
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
the cover, and that corrected figure is judged as if no read-back was asked (§1). A rejected
read-back is kept as `Stated(False)` and a mismatched one becomes `Unclear(readback_mismatch)`;
the customer's figure is kept either way and the rules decide what the read-back changes.

`Stated.also: tuple[Evidence, ...] = ()` (new): the other replies to the same question that the
answer stands over, such as an earlier "I don't know", and, for a correction inside one reply that
stood (§1), the earlier words of that reply (whole clauses, same turn).

```python
ProductResult.self_corrections: tuple[AnswerConflict, ...] = ()   # additive (samajh.types)
```

Built by `samajh.rules.engine.self_corrections` from each stated belief's `also` entries in the
same turn: (the earlier words, the whole reply). A note for the reviewer only: not a flag, not a
gap, and not part of the verdict or tier.

Conflicts are only stated answers that
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
- Refusals by structure (`samajh/amounts/_parse.py`, `_lexicon.py`; tests in
  `tests/core/test_amounts_structure.py`). Each gives `Ambiguous(malformed)` from both parsers:
  - A comparison or bound anywhere in the clause of the amount: "कम से कम पचास हज़ार",
    "पचास हज़ार से कम", "at least 50,000", "minimum 50,000", "ज़्यादा से ज़्यादा दो लाख".
    Not refused (found by the r3 verifier, open): the bounds "तक" and "up to" ("पचास हज़ार तक।"
    and "up to 40,000 rupees." read as the plain figure), and a count written in romanised Hindi
    before the amount ("do baar 20 hazaar kate." reads 20,000).
  - Known cost, open: "सॉरी" and "sorry" count as doubt words anywhere in the reply, so an amount
    answer with an apology about the line ("…इकतालीस हज़ार तीन सौ रुपये, सॉरी, नेटवर्क चला गया था।")
    is refused and the question ends `incomplete`.
  - A number beside the amount that nothing accounts for (not a duration, percent, clock or
    filler run, and not a count of the next word): "पचास हज़ार दो बार कटे", "दो एफडी पचास हज़ार की",
    and a number that touches the amount across a clause break ("पचास हज़ार, दो बार",
    "2, ₹50,000"). A number in another clause that does not touch the amount is ignored
    ("दो लोग थे, पचास हज़ार दिए" is 50,000).
  - A small number after a thousand-or-larger unit word ends the amount only before a currency
    word or the end of the clause ("पचास हज़ार एक" is 50,001); a number other than one also before
    a postposition ("उन्नीस हज़ार अस्सी की है"); before a duration, percent or clock word it is that
    word's number ("पचास हज़ार दो साल"). Before anything else it may be the units digit or a count,
    and "one" may be the article, so the run is refused ("पचास हज़ार एक दिए", "पचास हज़ार एक FD",
    "fifty thousand one policy"). After a hundreds word a number is part of the amount
    ("तीन सौ एक दिए" is 301), except a count before its own noun ("तीन सौ दो बार").
  - A misheard unit word ("तीन लक") anywhere in the text refuses it, in any clause.
  - Fraction and unit words close to a known one are compared on a reduced form with the same
    consonant frame; everyday words close to one (`ORDINARY`) are not refused. Hindi and Latin
    script only.
- `parse_approx_amount` reads what `parse_amount` refuses as hedged: "करीब पचास हज़ार" is
  `Approximate(50000, 50000)`, "पचास बावन हज़ार के आसपास" and "50 से 52 हज़ार" are
  `Approximate(50000, 52000)`. A correction ("बावन नहीं पचपन हज़ार") stays `Ambiguous`.
- The premium rule: within 1% of the record and confirmed at the read-back passes. Within the
  approximate tolerance (10%, range-aware) and confirmed is a `premium_approximate` flag (low,
  `understanding_gap`). Further off and confirmed is `premium_differs_confirmed` (`refer`).
- **Read-back contract for the dialogue.** A premium still passes only after a confirmed read-back of
  the same figure. For an approximate answer the bot line must carry the same figures: the code reads
  the bot's read-back line with `parse_approx_amount` and requires the same `(low, high)`. For a
  single figure nothing changes. A rejected read-back is a `readback_rejected` gap and a
  mismatched one a `readback_mismatch` gap, whatever the figure (`incomplete`).
- **Premium carried from open recall** (`samajh.rules.normalise.carried_premiums`,
  `samajh.extract._Assembly.carry`; tests in `tests/extract/test_extract_carry.py`). When the bot
  reads back a premium for a product it never asked the premium of, the open-recall reply whose
  whole text reads to the figure read back is accepted as the premium's quote, and nothing else
  is. When no such reply exists the premium is `Unclear(readback_mismatch)` with the read-back
  reply as its evidence, not "not asked". The carried premium is put in call order, so a
  correction at the read-back replaces it like any premium. The premium is carried only from a
  recall reply whose change check said `none`, or a one-clause reply, which gets no check; after
  a correction, a withdrawal, a failed check or a failed answer call on that reply nothing is
  carried and the premium is a gap (`readback_mismatch`). The independent verifier found the
  fault (4 of 4 real-model replies that took the figure back ended `clear`); after the fix the same
  verifier found 13 of 13 fresh such replies `incomplete` and 8 of 8 informed replies still
  carried (`verify-P3a-r3.md`, addendum). The protection rests on one change-check reading: an
  edit to the change-check prompt needs the retraction probes rerun.
- The amount span the model gives and the customer's whole reply must read to the same amount;
  the span is not trimmed or widened (the whole reply already holds every word next to the span).

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
- **The change check** (a third request per reply; `ChangeReply` and `Change` in
  `samajh.extract._wire`, applied by `_Assembly.check`). It goes with every answer call on a reply
  of two or more clauses to a checked question, and on open-recall replies of two or more clauses.
  It sees the numbered question and reply the answer call sees, not the answer call's reading, and
  returns `change` (`none`, `corrected`, `withdrawn`) with `first_clauses` and `final_clauses`
  (clause numbers only; it gives no value). Code resolves the clause numbers against the reply and
  decides:
  - `none`: the answer call's reading stands.
  - `withdrawn`, a failed check, a pointer that does not resolve or two runs that overlap: every
    stated answer of the reply becomes `Unclear` (a failed check: `extraction_failed`).
  - `corrected`: a stated answer stands only when the answer call's clauses start after the
    check's `first_clauses` and end inside its `final_clauses`; the `first_clauses` run goes into
    its `also`; no conflict is added. Otherwise it becomes `Unclear`.
  - `DontKnow`, `Unclear` and a rejected read-back are left as they are; a read-back "yes" taken
    back becomes `Unclear`.
  - Open recall (`_recall_check`): items said in the clauses taken back are dropped and the reply
    is listed in `unscreened` (a case-level gap); when the first run does not resolve every item of
    the reply is dropped. A change whose first answer named nothing (a denial, then a thing named)
    leaves the items alone. A failed check keeps the items and lists the reply as unscreened.
  - A reply of one clause gets no check.

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
call_ended_label(outcome: str | None) -> str                         # pure; gives a label for any value
```

- Questions never put are named in one clause of the line, "the call did not get to: …",
  rendered as a sentence: "The call did not get to: the cover."
- A flag line whose outcomes carry no customer quote ends its title with
  "(from the lender's record; no customer statement)" (`RECORD_ONLY_MARK`).
- On every case, clear ones included, a note line (tier `clear`, `note=True`, no clauses) follows
  every issue line for each item of `ProductResult.self_corrections`: 'Customer first said "…"
  about …, then corrected it in the same reply.' A note line is never part of the case tier.
- `call_ended_label` turns the dialogue's outcome into a reviewer's line through the table
  `CALL_ENDED` (one label per dialogue `Outcome`, for example "The call reached its closing lines",
  "Ended early: the customer asked not to be called again"). `None`, an empty value or
  `in_progress` gives "Stopped before the call finished: the recording ends there (a hang-up or a
  dropped line)"; an unknown value gives "Ended: " and the value with spaces for underscores.

A flag is evidence for review and never a finding. No line says "mis-selling" or "refund".
