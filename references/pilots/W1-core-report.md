# W1b report: Samajh core (types, amounts, rules)

Date: 2026-11-10. Worker: W1b, finishing W1 after the usage-limit stall.

Goal as I understood it: W4 (scenarios) and W5 (extractor) need stable types and a rule engine that match DESIGN.md v2 and the claims corrections, and that never return `clear` for a customer who was misled or not asked.

## 1. What changed (paths)

- `samajh/types.py`: v2 types (lender type, bundling fields, open consent and cancel answers, evidence pack, v2 call steps, neutral rule ids).
- `samajh/rules/clauses.py`: paragraph map keyed by lender type.
- `samajh/rules/checks.py`: bundling, consent and cancel rules rewritten. `belief_mismatch` renamed. Each check now receives its rule id and paragraph from the engine.
- `samajh/rules/engine.py`: looks up the paragraph by `record.lender_type` and builds the evidence pack.
- `samajh/rules/normalise.py`: new answer fields, the product-less consent question, clause-aligned quotes, read-back corrections.
- `samajh/amounts/`: `parse_duration_days` (new), and the parser fixes from the review.
- `tests/core/`: 899 tests when I started, 1100 now.

## 2. Evidence

```
$ uv run pytest tests/core -q
........................................................................ [ 98%]
....................                                                     [100%]
1100 passed in 8.08s
exit: 0

$ uv run ruff check samajh/types.py samajh/amounts samajh/rules tests/core
All checks passed!
exit: 0
```

The reviewer's own reproduction script was rerun after the fixes. Every finding I fixed now returns `unclear_needs_human`, a refusal to parse, or the corrected value. Its output is summarised in section 5.

No live Gnani calls. No OpenRouter calls. No credits spent.

## 3. Public surface (code against this)

### Functions

```python
samajh.rules.to_beliefs(raw: RawExtraction, record: LoanRecord, transcript: Transcript) -> Beliefs
samajh.rules.evaluate(record: LoanRecord, beliefs: Beliefs) -> CaseResult
samajh.rules.verdict_of(outcomes: Iterable[Passed | Flag | Gap]) -> Verdict
samajh.rules.RULES: tuple[RuleSpec, ...]          # RuleSpec(id, title, check); RuleSpec.clause(lender_type) -> str
samajh.rules.CLAUSES: dict[LenderType, dict[RuleId, str]]

samajh.amounts.parse_amount(text: str, *, exact: bool = False) -> Parsed | Ambiguous | NoAmount
samajh.amounts.parse_duration_months(text: str, *, exact: bool = False) -> int | None
samajh.amounts.parse_duration_days(text: str, *, exact: bool = False) -> int | None     # new
samajh.amounts.spoken_amount(rupees: int, language: Language) -> str
samajh.amounts.format_inr(rupees: int) -> str
samajh.amounts.NOT_HUMAN_REVIEWED: frozenset[Language]   # {ta, kn}
```

`to_beliefs` raises `ValueError` when the three inputs are not the same call or the extraction names a product that is not on the record. `evaluate` raises `ValueError` for beliefs about another loan or an unknown product.

**Note, 2026-11-10 (after the amounts parser fix; the signatures above are otherwise unchanged).** `samajh.amounts` also exports, as of this note (checked in `samajh/amounts/__init__.py`; `uv run pytest tests/core -q` gives 1223 passed):

```python
samajh.amounts.cross_check(first: AmountResult, second: AmountResult) -> Agreed | ReadBackNeeded
samajh.amounts.Agreed          # status "agreed", rupees: int
samajh.amounts.ReadBackNeeded  # status "read_back_needed", readings: tuple[int | None, int | None]
```

`cross_check` compares two already-parsed readings of one turn (the Prisma v2.5 and v3.0 transcripts, each through `parse_amount`). The same `Parsed` amount twice gives `Agreed`; a difference, or either reading not being a single `Parsed` amount, gives `ReadBackNeeded` (DESIGN.md §15 item 16). Agreement is a stand-in for a confidence score, not a proof: both readings can share an error. The 240-sentence evidence for it is TTS audio only, and the after-fix numbers are tuned on that set (`eval/amounts/REPORT.md`, note at the top). The test count in this report (1100) is now 1223.

### Enums (values)

| Enum | Values |
|---|---|
| `Language` | hi, hi-en, ta, kn |
| `LenderType` (new) | bank, nbfc |
| `ProductKind` | credit_life |
| `LoanKind` | personal, gold |
| `KindClaim` | insurance, deposit, investment, fee, other |
| `PaymentSource` | from_loan, separately |
| `FeatureClaim` | is_deposit, refundable_anytime, guaranteed_return, one_time_payment, withdrawable_after_period |
| `SaleConcern` | coached_answers, learned_after_sale, signed_without_explanation |
| `ConsentMethod` | signed_form, otp, digital_click, recorded_call, verbal (new) |
| `Speaker` | bot, customer |
| `CallStep` (changed) | right_party_check, disclosure, second_check, context, open_recall, teach_back, consent_check, read_back, close |
| `Question` | kind, premium, payment_source, required_for_loan, provider_choice (new), cover, term, cancel_window, features, consent |
| `GapReason` | not_asked, no_usable_answer, value_not_parsed, readback_rejected, readback_mismatch, quote_not_grounded |
| `Severity` | high, medium, low |
| `Verdict` | clear, flag_for_review, unclear_needs_human |
| `RuleId` (values changed) | kind, premium, cover, term, cancel_window, recall, recall_unmatched, consent, loan_funded, bundling, belief_mismatch, sale_conduct, evidence |

### Models (all frozen, unknown fields rejected)

```python
Consent(method: ConsentMethod, at: date)
Product(id, kind: ProductKind, provider: str, premium_inr: int>0, cover_inr: int>0, term_months: int>0,
        paid_from_loan: bool, required_for_loan: bool,
        risk_mitigant: bool,                  # new, required
        provider_choice_offered: bool,        # new, required
        cancel_window_days: int>0 | None,     # None = no window on record
        features: frozenset[FeatureClaim],    # now required, no default
        consent: Consent | None)
Borrower(name, dob: date, language: Language)
LoanRecord(loan_id, lender_type: LenderType,  # new, required
           borrower, loan_kind: LoanKind, sanctioned_inr, disbursed_inr, disbursed_on: date,
           products: tuple[Product, ...])

Turn(id: TurnId, speaker, step: CallStep, text, asks: Question | None, product_id: ProductId | None,
     start_s: float | None, end_s: float | None)
Transcript(call_id, loan_id, language, turns)          # turn ids strictly increasing

Evidence(quote: str, turn_id: TurnId)
Answer[T] = NotAsked | Unclear(reason, evidence?) | DontKnow(evidence) | Stated[T](value, evidence)

# Layer 1: what the LLM emits
RawRecallItem(evidence, kind: KindClaim | None, amount_text: str | None, product_id: ProductId | None)
RawOpenRecall(asked: bool, answer: Evidence | None, items)
RawProductAnswers(product_id,
    kind: Answer[KindClaim], premium: Answer[str], premium_readback: Answer[bool],
    payment_source: Answer[PaymentSource], required_for_loan: Answer[bool],
    provider_choice_offered: Answer[bool],          # new
    cover: Answer[str], term: Answer[str],
    cancel_allowed: Answer[bool],                   # replaces cancel_window_known
    cancel_window: Answer[str],                     # new: the "by when" in the customer's words
    consent_given: Answer[bool],                    # replaces consent_confirmed
    consent_method: Answer[ConsentMethod],          # new
    feature_probe: Answer[tuple[FeatureClaim, ...]], volunteered_claims: tuple[ClaimEvidence, ...])
RawExtraction(call_id, recall: RawOpenRecall, products, sale_concerns: tuple[ConcernEvidence, ...])

# Layer 2: what the rules consume
ProductBeliefs(... same shared fields ..., premium_inr / cover_inr / term_months / cancel_window_days: Answer[int],
               ungrounded: tuple[Evidence, ...])
Beliefs(call_id, loan_id, language, recall: OpenRecall, products, sale_concerns, ungrounded)
        .for_product(product_id) -> ProductBeliefs

# Results
Passed(rule_id, product_id)
Flag(rule_id, clause, product_id, severity, expected, heard, quote?, turn_id?)
Gap(rule_id, clause, product_id, reason, quote?, turn_id?)
EvidencePack(loan_id, call_id, lender_type, product: Product, flags)     # new
        .quotes() -> tuple[Evidence, ...]    .clauses() -> tuple[str, ...]
ProductResult(product_id, verdict, flags, gaps, passed: tuple[RuleId, ...], evidence_pack: EvidencePack | None)
CaseResult(loan_id, call_id, language, verdict, products, case_flags, case_gaps, unmatched_recall)
        .all_flags() .all_gaps() .evidence_packs() .flag_keys() .gap_keys()

EVIDENCE_PACK_RULES = {kind, premium, consent, bundling, loan_funded}
```

### Contract for W5 (extractor)

1. **Quote whole clauses.** The quote of every answer (`Stated` or `DontKnow`) must be one or more whole clauses of the customer turn it cites. A clause ends at `। , . ; ! ?` or a newline. Quoting the whole reply always qualifies. A partial clause becomes `Unclear(quote_not_grounded)`. Recall items, volunteered claims and concerns may quote any run of whole words.
2. **The turn must reply to the right question.** An answer counts only when its turn replies to the bot turn tagged with that `asks` and `product_id`. The premium may also cite a correction made in reply to a premium read-back.
3. **Amounts and durations stay in words.** `premium`, `cover`, `term`, `cancel_window` carry the customer's span. The parser reads the whole reply and the span must parse to the same number.
4. **`premium_readback` is the reply to the last read-back.** It confirms only when that read-back came after the premium answer and read back the same amount.
5. **One cancel question fills two fields.** `cancel_allowed` (were you told you can cancel) and `cancel_window` (by when). Use `DontKnow` on `cancel_window` only when the customer says they do not know by when.
6. **One consent question fills two fields.** `consent_given` (does their account of what they agreed to buy include this product) and `consent_method` (how they say they agreed).

### Contract for W4 (scenarios) and the script builder

1. Every bot question about a product carries `asks` and `product_id`. The consent question is the exception: tag it `asks=consent` with no `product_id` and it counts for every product on the record.
2. A read-back is a bot turn with `step=read_back`, `asks=premium`. Its text must contain the amount. `"{spoken_amount}, यानी {format_inr}, सही है?"` parses back in all four languages for amounts of 100 and above (tested on a 1,000+ amount sample per language).
3. Every record must state `lender_type`, `risk_mitigant`, `provider_choice_offered`, `cancel_window_days` (or `None`) and `features`.
4. For a product to come out `clear` the call must ask: open recall, kind, premium plus read-back, payment source, required for the loan, cover, term, cancel, the money-back probe (`asks=features`), and consent. Choice of provider is needed only when the product was required (per record or customer).

## 4. How each correction was applied

| Correction | Where | What the code does |
|---|---|---|
| Item 1, bundling (85V / 101V) | `checks.bundling` | Flag only when required (record or `required_for_loan=Stated(True)`) AND one of: record `risk_mitigant=False`; the customer describes it as a deposit (kind `deposit` in the kind answer or open recall, or the `is_deposit` claim); record `provider_choice_offered=False`; customer `provider_choice_offered=Stated(False)`. Each reason is its own flag, severity high. Required, mitigant, choice on record and the customer confirms the choice: pass. Not required per record and customer: pass. Not knowing is a gap. |
| Item 1, belief | `_ProductAnswers.provider_choice_offered`, `Question.provider_choice` | Carries the answer to "were you told you could buy this cover from another company?" |
| Item 7, evidence pack | `EvidencePack`, `ProductResult.evidence_pack`, `engine.evaluate` | A product gets a pack exactly when it has a flag under kind, premium, consent, bundling or loan_funded. The pack holds the product record, loan id, call id, lender type and those flags (customer's words, turn id, paragraph). A validator rejects a result whose pack does not match its flags. |
| Item 7 and 8, wording | `tests/core/test_rules_engine.py` | The wording test bans "refund" (the belief name "refundable" is allowed) along with the older bans. It scans the source of types, rules and amounts, and the JSON of results that raise every rule. |
| Item 8, neutral ids | `RuleId` | Values equal the names in DESIGN.md section 6. `feature_belief` is now `belief_mismatch`. |
| Item 8, clause by lender type | `rules/clauses.py`, `LoanRecord.lender_type` | `CLAUSES[bank]`: 85Y, 85G, 85W, 85V, 4(20A)(ii). `CLAUSES[nbfc]`: 101Y, 101G, 101W, 101V, 6(9A)(ii). `sale_conduct` and `evidence` map to `internal`. |
| Item 11, cancel is an open question | `checks.cancel_window`, `parse_duration_days` | The customer's "by when" is parsed to days and compared with `cancel_window_days` (tolerance 1 day; a month reads as 30 days). No window on record and the customer was told they can cancel: low flag. The code never states a right. |
| Item 12, consent | `checks.consent` | No record: flag (high) from the record alone. Record on file: pass only when `consent_given=Stated(True)` and `consent_method=Stated(<method on record>)`. `consent_given=Stated(False)`: flag high. A different method: flag medium. Anything unanswered or unusable: gap. A record never clears the check by itself. |
| Call steps | `CallStep` | The nine v2 steps, in order. |

Our own reading, not in the corrections: comparing the customer's way of agreeing with `Consent.method`. Item 12 says the bot "compares the answer with the consent record" and the question asks "how did you agree", so the method is the comparable part.

## 5. Independent review (one Fable high-effort subagent that wrote none of the code)

The reviewer saw 1045 passing tests, then attacked. Findings and what I did:

| # | Finding (proven by a script) | Result |
|---|---|---|
| F1 | A quote cut short of a "नहीं" in the same clause grounded a wrong enum or boolean ("यह बीमा" from "यह बीमा नहीं है, एफ़डी है"). A one-letter quote also grounded. | **Fixed.** Answer quotes must be whole clauses on word boundaries. All three cases are now `unclear_needs_human`. |
| F1 (rest) | A wrong value on a complete, real clause still passes. So does one consent reply reused for two products with the wrong polarity for one. | **Documented.** Deterministic code cannot check meaning. This is the extractor's false-clear rate and W5 must measure it. |
| F2 | Record says OTP, customer said "form par sign kiya", extraction omitted the method: `clear`. | **Fixed.** A missing, unusable or "do not know" method is a gap. |
| F3 | A flag raised from the record alone carried an ungrounded quote into the evidence pack. | **Fixed.** Flags quote only `Stated` or `DontKnow` answers. |
| F4 | Negator, comparative or correction not next to the number was ignored ("बावन हज़ार तो नहीं था" gave 52,000). | **Fixed.** A negator or comparative in the same clause refuses the parse. "शायद", "सॉरी", "maybe", "sorry" refuse the text. |
| F5 | Romanised fraction and number words were dropped ("saadhe 5 hazaar" gave 5,000). "½ lakh", ".5 lakh", "₹52.000" parsed wrongly. Misspelt "सादे", "पवने" were dropped. | **Fixed.** A list of romanised Hindi number and fraction words is refused. The three digit forms are refused. "सादे", "साडे", "पवने" are read as the fraction words. |
| F5 (rest) | "एक लाख बीस" parses as 1,00,020 though speech often means 1,20,000. | **Documented**, with a test that pins it. Changing it breaks the read-back round trip. The premium has the read-back as a check; cover has none. |
| F6 | Punctuation-separated ranges read as the last number ("15 – 30 दिन" gave 30). "हफ़्ता दस दिन" gave 10. Kannada "ದಿನಾಂಕ" (date) read as days. | **Fixed.** All return `None`. |
| F7 | A premium corrected at read-back could never clear, and a faithful extraction got a flag for the amount the customer had rejected. | **Fixed.** The premium may cite the correction turn. A "yes" counts only for a later read-back of the same amount. A mismatch makes the premium a gap, not a flag. |
| F8a | Record says paid separately, customer does not know how it was paid: an 85W flag with a pack. | **Fixed.** Now a gap. |
| F8b | `Product.features` defaulted to empty, so a true "single premium" claim flagged. | **Fixed.** `features` is required. |
| F8c | A call that follows DESIGN.md section 5 exactly has no money-back probe, so `belief_mismatch` is a gap and the call is never `clear`. | **Kept, needs a decision.** See section 7. |
| F8d | A compliant customer who does not name the product in open recall gets a low `recall` flag. Section 6 lists no recall rule. | **Kept.** The original W1 spec asks for the unprompted-recall signal. See section 7. |
| F8e | "Free of cost: no flag" cannot be represented (`premium_inr` must be above 0). | **Documented.** v1 has one paid product family. |
| F9 | `required_for_loan` unanswered when the record says required: `clear`. "Do not know" about cancelling when the record has no window: `clear`. A kind named correctly in open recall stands in for a kind question never asked. `RecallItem.amount_inr` is used by no rule. The pack holds the product, not the whole loan record. | **Documented as intended**, except the recall amount: an `amount_text` the customer did not say is now dropped. The recall amount is informational and is not compared with the record. |

Attacks that held: an 800-combination truth table for bundling, both clause maps, the pack rule, banned wording, wrong turn ids, quotes from bot turns or other turns, a "yes" reused across questions, dropped or untagged questions, a skipped product, amount ranges and double amounts, adjacent negation, the Tamil and Kannada fraction forms, the spoken-amount round trip, and 60,000 fuzz inputs with no exception.

## 6. Claims

Verified, with source:
- Paragraph numbers for both lender types: `references/claims/claims-ledger.md` rows A5 and A19 (RBI/2026-27/115 and RBI/2026-27/123, checked by W3 on 2026-11-10). The `[unverified]` note in `clauses.py` is removed.
- Every row of `references/pilots/results.json` is a regression test: 80 rows, 78 with status 200, 76 parse to the gold amount, 2 are the documented miss (item hi08 on phone audio, both v3.0 configs, "पौने" dropped by the recogniser), and 2 are gateway error pages. The miss is asserted as wrong and exposed by the read-back.

Not verified:
- Tamil and Kannada lexicon entries, day and week words, spoken forms and read-back joining words. All `not human-reviewed`.
- The parser was written against the pilot and has no held-out audio test. The numbers above are in-sample, TTS-only, one voice.
- Whether Prisma ends clauses with punctuation on real phone audio. If it does not, each turn is one clause and the extractor must quote the whole turn.

## 7. Failures, known gaps, deviations

**Deviations from the process.**
- I wrote the changes myself and spawned no builder subagents. The delta was small and tightly coupled, and the account was hitting usage limits. One planner pass was done inline, not through the architect arena.
- One review pass ran, as instructed. The fixes made after it (clause-aligned quotes, read-back corrections, parser hedges) have tests and pass the reviewer's reproduction script, but **no independent reviewer has seen them**.

**Decisions the coordinator should confirm.**
1. **The money-back probe.** The engine requires the question tagged `asks=features` ("if you wanted this money back, what would happen?"). DESIGN.md section 5 step 6 does not list it. Without it no call is `clear`. I kept it required because silence must not pass and because it is the question that surfaces the "withdrawable after a year" belief in award BNG-L-041-1617-0797. To make it optional, change the last call in `checks.belief_mismatch`.
2. **The recall flag.** A product the customer does not name in open recall is a low flag, so the product is `flag_for_review` even if every prompted answer is right. This affects the false-flag rate in E2. W4 gold must follow it or the rule must change.
3. **Consent method.** A customer who agrees they bought the product but cannot say how is `unclear_needs_human`. A customer who names a different method than the record is a medium flag.

**Known gaps.**
- A wrong extracted value on a complete clause passes grounding. Measure it in W5.
- Romanised Hindi numbers are refused, not read. The refuse list is not complete: "ek", "do" and "saath" are left out because they are everyday words.
- "एक लाख बीस" reads as 1,00,020.
- Cover, term and cancel window have no read-back.
- A negator in the same clause after an amount refuses the parse even when it negates something else. Without punctuation in the transcript that reaches the whole turn. This errs towards `unclear`.
- A free product cannot be represented.
- `Borrower.dob` is a full date; the v2 call only uses the year of birth.

## 8. Documents this work makes stale

- `DESIGN.md` line 84 (section 5 step 6): the question list lacks the money-back probe that the engine requires. Decision 1 above.
- `DESIGN.md` lines 126 to 131 (type sketch): `Product` lacks `features`; `LoanRecord` lacks `loan_kind` and `disbursed_on`.
- `DESIGN.md` line 132: `Answer = {field, value, quote, turn_id}`. The code has four states (`NotAsked`, `Unclear`, `DontKnow`, `Stated`) and two layers (`RawExtraction`, `Beliefs`).
- `DESIGN.md` lines 133 to 135: the `Flag` rule list lacks `recall`, `recall_unmatched`, `sale_conduct`, `evidence`; the field is `turn_id`, not `ts`.
- `DESIGN.md` lines 148 to 155 (rules): no recall rules; `consent` does not mention the method comparison; `cancel_window` does not say a missing "by when" is a gap; `bundling` says "free of cost: no flag", which is not modelled; line 149 does not say the premium passes only after a confirmed read-back.
- `references/claims/design-corrections.md` lines 18 to 20: the three W1 rows are applied.
- `ORCHESTRATION.md`, iteration 1 table, W1 row: status.

## 9. Spend

Gnani credits: 0. OpenRouter: 0. Subagents: one reviewer.

## 10. Next iteration, in this area

1. A second independent review of the post-review fixes, focused on clause-aligned grounding and the read-back correction path.
2. Check on real Prisma output whether clause punctuation is present, and decide whether whole-turn quoting should be the stated rule for the extractor.
3. A held-out amounts test from fresh audio, with Tamil and Kannada reviewed by a fluent speaker.
4. Decide the three open points in section 7 before W4 freezes gold.
