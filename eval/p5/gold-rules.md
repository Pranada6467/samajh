# How gold is set for P5 customers and P4 cards

Written by the P5 sub-orchestrator on 2026-11-10 from `DESIGN.md` section 6 (rules and tiers) and section 15 (items 13 to 20 and 27 to 30). It restates them for a person who labels a fact sheet and is meant to add no rule; the last section lists where the independent verifier found it looser than the code. Where this file and `DESIGN.md` differ, `DESIGN.md` wins; where `DESIGN.md` and `samajh/types.py` (`FLAG_TIER`, `REFER_RULES`) differ, the code wins.

Gold is set from the fact sheet and the lender's record only, before any customer words or audio exist. It says what a correct call would find if the customer answered every question for themselves, in line with the fact sheet. It never says a sale was mis-selling: a `refer` is evidence for a human reviewer.

## The four tiers

- `refer`: a human must look.
- `incomplete`: the call did not yield enough to decide. Gold never expects this tier: it arises from how a call went, not from what the customer believes.
- `understanding_gap`: reported in aggregate, not queued.
- `clear`: every rule passed.

A case's tier is the worst of its grounds: any `refer` ground makes it `refer`; else any gap ground makes it `understanding_gap`; else `clear`.

## Grounds, by what the customer believes (from the fact sheet) against the record

| Rule | `refer` ground when | `understanding_gap` ground when |
|---|---|---|
| `recall` | The customer says they took nothing with the loan, and keeps to it (`recall_denied`) | The customer names nothing on the record when first asked but does not deny it (`recall_not_named`) |
| `kind` | The customer says it is something other than insurance (a deposit, FD, investment, a fee) or does not know what it is | never |
| `premium` | The customer states, and would confirm, an amount more than 10% from the record | The customer does not know the amount; or gives an amount or a narrow range within 10% but not within 1% (`premium_approximate`) |
| `cover` | The customer states a plain figure more than 1% from the record and would confirm it | The customer does not know, or gives a hedged or rough figure |
| `term` | never | The customer does not know or says a different length. "As long as the loan runs" passes when it equals `tenure_months` on the record |
| `cancel_window` | never | The customer does not know it can be cancelled, does not know until when, or gives a different window |
| `consent` | The record holds no consent (a ground from the record); or the customer's account of what they agreed to leaves the product out ("I only signed for the loan"), or is "I don't know what I agreed to"; or the customer names a different way of agreeing than the record (signed a form against an OTP on the record) | never. A customer who agreed but cannot say how is undecided, not a ground: write it under `notes` |
| `loan_funded` | The record says paid from the loan and: the record holds no consent (from the record), or the customer says it was paid separately, or does not know how it was paid. Or the record says paid separately and the customer says it was cut from the loan | never |
| `bundling` | The product was required for the loan (the record says so, or the customer was told so) and at least one of: the record says it is not a risk mitigant; the customer describes it as a deposit; the record shows no choice of provider; the customer was not told it could be taken elsewhere | never. A customer who does not know whether it was required is undecided |
| `belief_mismatch` | The customer believes something the record's `features` does not list: it is a deposit, the money can be taken out at any time or after a period, a guaranteed return, or a single payment when `one_time_payment` is not listed | The customer does not know whether the money can be got back |
| `payment_frequency` | (see `belief_mismatch` for a single-payment belief) | The customer says they pay again and again when the record lists `one_time_payment`, or does not know |
| `sale_conduct` | The customer says they were told how to answer a checking call, learned of the product only after the sale, or signed without anything being explained | never |

Readings kept from the scenario set's datasheet, so the two sets are labelled alike: a product recalled under the wrong name is still recalled (`kind` carries it, not `recall`); a customer who agreed under a wrong description ("I signed for the FD") recognises the consent, and `kind` and `belief_mismatch` carry the misdescription.

## The gold row

```
{"id": "...", "kind": "<customer kind>", "language": "hi" | "hi-en", "record_id": "...",
 "class": "problem" | "knowledge_gap_only" | "no_problem" | "procedural",
 "expected_outcome": "completed" | "wrong_party" | "declined" | "call_back_later" | "language_switch",
 "expected_tier": "refer" | "understanding_gap" | "clear" | null,
 "refer_grounds_from_call":   [{"rule": "kind", "because": "<the fact-sheet line it rests on>"}],
 "refer_grounds_from_record": [{"rule": "consent", "because": "<the record field>"}],
 "gap_grounds":               [{"rule": "cancel_window", "because": "..."}],
 "beliefs": {"names_product_unprompted": true | false | "denies",
             "kind": "insurance" | "deposit" | "investment" | "fee" | "other" | "dont_know",
             "premium_inr": 52000 | {"low": 50000, "high": 52000} | "dont_know",
             "payment_source": "from_loan" | "separately" | "dont_know",
             "payment_frequency": "one_time" | "recurring" | "dont_know",
             "required_for_loan": true | false | "dont_know",
             "told_could_take_elsewhere": true | false | "dont_know" | "not_applicable",
             "cover_inr": 500000 | {"low": ..., "high": ...} | "dont_know" | "names_no_amount",
             "term_months": 24 | "as_long_as_loan" | "dont_know",
             "cancel": {"allowed": true | false | "dont_know", "window_days": 30 | "dont_know" | null},
             "money_back": "not_refundable" | "refundable_anytime" | "withdrawable_after_period" | "guaranteed_return" | "is_deposit" | "dont_know",
             "consent_method": "signed_form" | "otp" | "digital_click" | "recorded_call" | "verbal" | "did_not_agree" | "dont_know_how" | "dont_know",
             "sale_concerns": ["coached_answers" | "learned_after_sale" | "signed_without_explanation"]},
 "notes": "<anything undecided, or a reading that is ours>",
 "rationale": "<two or three sentences>"}
```

- `class`: `problem` when gold has at least one `refer` ground from the call; `knowledge_gap_only` when it has gap grounds and no `refer` ground; `no_problem` when it has neither; `procedural` when the call should end before the questions (a third party, a refusal, a later call, another language).
- `expected_outcome` and `expected_tier` assume the customer speaks for themselves. A procedural customer has `expected_tier: null` and `beliefs: null`.
- A customer who asks whether the call is genuine, or says they are in a hurry, and then talks, is labelled by what they believe (`class` and tier as above) with `expected_outcome: completed`.
- For a third party, `expected_outcome` is `wrong_party` and the gold adds `"loan_must_not_be_named": true`.

## Where this file is looser than the code (independent verification, 2026-11-10)

Gold was labelled under the table above and is kept as labelled. The verifier compared the table with `DESIGN.md` section 6 and the code and found these differences:

- **An undecided answer.** This file treats "does not know whether it was required" (and a customer who agreed but cannot say how) as undecided, with no ground. The code raises a gap under `bundling` (or `consent`, `loan_funded`), and a gap under one of those rules makes the tier `incomplete`. So a correct call can end `incomplete` where `expected_tier` says `understanding_gap`: P5-C017 to P5-C020, and any customer whose gold `notes` mention an undecided answer.
- **A hedged cover figure.** This file makes any hedged or rough cover figure a gap. The code passes an approximate figure near the record. It changes one ground (P5-C026, cover) and no tier.
- **`recall_unmatched`** (the customer names an insurance, deposit or investment that is not on the record) is not in the table. No P5 customer or P4 card is written for it.

**Consequence for scoring:** score the tier only as `refer` or not `refer`. `understanding_gap`, `clear` and `incomplete` among customers without a `refer` ground are shown as counts, never scored against `expected_tier`.
