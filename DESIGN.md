# Samajh — design v3

> A post-sale understanding callback for Indian lenders: a teach-back-style comprehension check. The customer explains in their own words, in their own language, what they bought with their loan. Plain code compares that against the bank's records, and every mismatch becomes evidence a human can review.

Status: **v3 design, 2026-11-10.** v3 applies the iteration 1 judge's review (`references/reviews/iter1/judge.md`) to design v2, which had applied the claims check in `references/claims/` (`design-corrections.md` for the edits, `claims-ledger.md` for the sources; ledger row ids such as A16 appear in brackets). What changed: two product languages (§4); a call built for real people (§5); a four-tier outcome in place of "any flag means review", plus a reviewer queue and a half-yearly report (§6); E1 retired as a headline and a held-out amounts result (§9); the risks the iteration 2 verifiers found (§13); the decisions (§15). The code wins where this text differs; what is built and what is verified is in `ORCHESTRATION.md` ("Coordinator handoff"). Evidence: the amounts result `eval/amounts_v2/` with `references/reviews/iter2/verify-P6.md`; the development amounts set `eval/amounts/REPORT.md`; the extractor and decision chain `references/pilots/W5-extractor-report.md` and `P3a-report.md`; the call `P2-report.md`; the phone `P1-report.md`. How we chose this idea: `IDEAS-HILLCLIMB.md`. Where the text says "our reading" or "our choice", the conclusion is ours and no regulator or court has ruled on it.

**Caveats that apply to every result in this document, stated once.** Every result is on synthetic data. Speech results use Timbre-voiced customers (TTS) unless §9 says otherwise; no person has used the phone. Customers in the scenario and text-path sets are scripted by the team. Nobody fluent has read the bot's lines, and Tamil and Kannada are not human-reviewed. A builder's own probe counts are not evidence of a fix; independent verification on fresh inputs is.

---

## 1. The problem

A gold-loan borrower complained that ₹52,000 had been deducted from his loan amount, and that the bank had described it as a "fixed deposit for loan security". It was a life-insurance policy. The Insurance Ombudsman found he had asked for cancellation within two months and ordered the insurer to cancel the policy and refund the premium (Bhopal, BHP-L-021-1617-0529).

Insurers already make verification calls, and in some awards the recorded call did not save the insurer:
- BNG-L-041-1617-0797: the insurer submitted the recording of the customer confirming the policy. The customer said the bank had assured him the money could be withdrawn after a year. The Ombudsman held the insurer responsible for its agent and ordered the policy converted.
- PUN-L-036-1617-0228: "The PIVC recording is clear about the terms and conditions of the policy but the maturity benefit is not explained." Refund ordered.
- PUN-L-017-1617-0684: the recording showed the caller's "main focus ... was on processing the application". Refund ordered.

In four awards the complainant said they had been told how to answer the call. One was told "there would be a verification call and in reply she had to answer everything in positive" (AHD-L-001-1617-0203). In another the Ombudsman accepted that the customer "responded as was guided" (CHD-L-019-1718-1436).

A recorded "yes" is weak evidence of understanding. It is not worthless. Insurers have won where the recording showed the caller stating the disputed point and the customer agreeing (PUN-L-013-1617-0583), and where the Ombudsman heard the recording and the customer had confirmed the proposal details (NOI-L-036-1819-0337). Both of those complaints were also made late.

## 2. The rule that makes this timely

On 15 June 2026 RBI issued ten entity-specific Amendment Directions on "Advertising, Marketing and Sale of Financial Products and Services by Regulated Entities". They take effect on **1 January 2027**. Commercial banks: Reserve Bank of India (Commercial Banks - Responsible Business Conduct) Second Amendment Directions, 2026, RBI/2026-27/115, para 85Y. NBFCs: RBI/2026-27/123, para 101Y. Small finance banks, payments banks, local area banks, regional rural banks, urban and rural co-operative banks and All India Financial Institutions have the same paragraph under their own numbers. Housing finance companies follow NBFC paragraphs 101A to 101ZA through para 157A of the HFC Directions (RBI/2026-27/124). RBI's consolidated Directions pages did not yet show paragraphs 85A to 85ZA on 10 November 2026, so we cite the amendment.

> "85Y. A bank shall establish a mechanism to seek feedback from customers, within a period of 30 days from the sale of any financial product / service to ensure that customers have understood the features of the financial product / service and also the risks associated with such financial product / service. The mechanism may include selection of the customers on a random basis for such feedback through modes such as call-backs or surveys carried out by a department / vertical of the bank not associated with sale of products / services. A half-yearly report on the findings of the feedback shall be prepared and utilised for review of existing policies and features of financial products / services."

Samajh is a tool a bank's non-sales unit can use to run that mechanism.

85Y requires four things: a feedback mechanism, feedback sought within 30 days of the sale, the purpose of ensuring customers understood features and risks, and a half-yearly report used to review policies and products. Random selection, call-backs, surveys and the independent unit sit in a sentence that begins "may include". 85Y does not say who receives the report and requires no filing with RBI.

We add checks against the related paragraphs of the same chapter to the 85Y callback. 85Y doesn't require these checks, but the bank must meet those paragraphs anyway, and the evidence falls out of the same call:

| Para (commercial banks) | What it says | What we check |
|---|---|---|
| 85G | Explicit consent for each product (for example a signed declaration, OTP, digitally recorded confirmation, or a demarcated clause), kept until one year after the contract ends | Is there a consent record for each product, and does the customer recognise it? |
| 85V | No compulsory bundling of a third-party product with the bank's own. A product required as a risk mitigant is allowed if the customer may buy it from any provider | Was the product required for the loan? If so, is it a risk mitigant, and was the customer offered a choice of provider? |
| 85W | No paying for a product out of the loan without explicit consent | Was the premium deducted from the loan, and did the customer know? |
| 4(20A)(ii) | Mis-selling includes incorrect, incomplete or misleading information | Does what the customer believes contradict the product's features? A wrong belief is evidence that incorrect information may have been given, not proof |
| 85Z | Where mis-selling is established, the bank refunds the full amount paid and compensates loss under its own policy. A customer may also complain within a set window | We prepare an evidence pack for the bank's reviewer |

For NBFCs the sub-paragraph letters are the same and the prefix changes: 101G, 101V, 101W, 101Y, 101Z. The mis-selling definition is para 6(9A) for NBFCs, not 4(20A) (A5, A19).

RBI does not define "risk mitigant". Treating credit-life cover on a loan as one is our reading. A savings policy described as a "security deposit" or an "FD" is not a risk mitigant on any reading (A16).

## 3. Users

- **Primary:** the department of a bank or NBFC that doesn't sell products and runs the 85Y feedback mechanism (customer experience, compliance or audit).
- **Secondary:** the compliance head who owns the half-yearly report; voice-agent vendors (Gnani included) who sell to these lenders.

Insurance sold with a loan is a "third-party product or service" that the bank sells under an agency or referral arrangement with the provider, so the bank owns the duties of this chapter for that sale (A24).

## 4. Scope

**In scope**
- One product family: a loan (personal or gold) sold with credit-life / loan-protection insurance.
- Languages: **Hindi and Hinglish are the product languages.** Tamil and Kannada stay in the code as experimental: they appear only in an appendix, get no new effort, and are not in the demo or any headline. A language counts as **supported** only with a fluent reviewer for its scripts and scenarios and ≥10 improvised real-voice calls. Today no human recording exists, so Hindi and Hinglish are "TTS-only, not human-tested". Regional languages are our choice: 85R covers documents for the bank's own products and defers to the product regulator for third-party products, so it does not ground the language choice for insurance (A25).
- One outbound call flow, from a simulated phone in the browser.
- Checks: 85Y understanding, 85G, 85V, 85W, and belief mismatch (which may engage 4(20A)(ii)).
- Outputs: a case file per call with a triage tier and a short summary; a reviewer queue; a half-yearly report page built from a batch of calls, with the reach funnel. All over a synthetic loan book.

**Not in scope**
- Real telephony and real bank integrations (all records and calls are synthetic). The number series and telecom declarations in §5 describe a real deployment; the demo does not exercise them.
- Other products and a second product family (the lender's own terms are the natural next one: a slide, not a build).
- Analysing the original sales call.
- Deciding whether something *is* mis-selling: we only produce evidence for human review.
- Testing whether the product was suitable for the customer (4(20A)(i)).
- Re-teaching: Samajh assesses understanding and does not explain the product.
- Live streaming STT: REST per turn with a browser end-of-speech detector (decision 12 in §15, closed by measurement).
- A Key Facts Statement check, an SMS arm, a dark-pattern slide (dropped, §15).

## 5. The call

This section describes the call as P2 built it (`references/pilots/P2-contract.md` section 5 is as built; the code wins). **A fix round is in progress.** An independent verifier (Opus, 2026-11-10) found the built call not ready for a live line; the numbers are in §13. The fix makes the turn classifier the primary judge at the opening, adds safe defaults and new outcomes. Wording below that the fix round changes will be updated when it lands and is verified.

```
right-party check → short opening and go-ahead → second check → context → open recall
  → questions per product (or the "took nothing" branch) → consent check → close
  (read-backs follow the premium and a stated cover)
```

1. **Right-party check.** "Am I speaking with <first name>?" Only an unambiguous first-person yes continues ("हाँ जी, बोल रहा हूँ", "मैं ही हूँ"). Anything else gets one re-ask ("are you Ramesh yourself?"). A speaker who says or implies they are someone else ("रमेश की वाइफ़", "Ramesh's brother") ends the call as `wrong_party` with a line that gives only the first name and "customer care". The loan is never named at this step.
2. **Opening.** After the yes, four short lines: who is calling (an automated assistant from the lender's customer care), that this is feedback and not sales, that the call is recorded with a pointer to the lender's written notice, and "may we talk for two or three minutes?" That is 48 words before the customer's second turn, 19.2 s at an assumed 2.5 words a second (a word count; nothing was timed). A no ends the call as `declined`; a request for a later call as `call_back_later`. "How to check that the call is genuine" (hang up and call the number printed on the papers from the lender) is said on request and at every completed close.
3. **Second check, no secret.** One low-sensitivity fact, the year of birth (synthetic in the demo), asked with the line "we will never ask for an OTP, PIN, password or account number". The bot never asks for account digits. The customer gets two tries, and a mismatch and an unclear reply get the same re-ask line, so the bot never confirms a wrong guess as wrong. A two-digit year passes only when the last two digits of the year on record are 10 or more. A speaker who says they are someone else fails the check even with the right year. Failure ends the call with no mention of the loan (`second_check_failed`, or `wrong_party`).
4. **Context.** Only now does the bot mention the loan, and "you can stop, or ask for a person, at any time" comes with the first mention.
5. **Open recall (the key question).** The bot asks whether anything was taken with the loan and, if so, what and for how much. It names no product, so it does not lead the answer, and it does not presuppose that anything was taken. A customer who says they took nothing ("कुछ नहीं लिया, बस लोन लिया था") gets one neutral follow-up, then the consent question and the close; no product question is asked. The denial is recorded and the rules decide what it means (§6).
6. **Questions for each product on record.** The bot never names the product's kind, so no spoken line holds the words insurance, policy, premium, cover, FD or deposit (the lint in `samajh/dialogue/lint.py` rejects them). With one product it says "the thing taken with the loan"; with several, "the first / second thing". Per product, in this order: what the customer thinks it is, in their own words; what they paid (then the read-back, step 8); where and how the money was paid; one payment or recurring; whether it was needed for the loan or their choice; what they were told about where to take it from (**asked only when the customer does not say it was their own choice**; the branch depends on the customer's answer, not on the record, so it leaks nothing); what it gives and up to what amount (a stated figure is read back); how long it runs; whether it can be cancelled and until when; and the open money-back question ("if you wanted this money back, what would happen?"), which is how a belief such as "the money can be withdrawn after a year" (BNG-L-041-1617-0797) comes out. "I don't know" is an answer and is never re-asked; a bare yes or no to an either/or question is asked again once. The bot compares the cancel answer with `cancel_window_days` on the record and never states a right itself.
7. **Consent check.** "When you took the loan, what did you say yes to, and how did you say yes?" (the lint bans "buy" and any suggested method such as "sign" or "form"). The bot compares the answer with the consent record. The call never *captures* consent.
8. **Read-back.** The premium the customer stated is read back at once, in their language, with the figure the customer said and never the record's, and with what it is for ("तो आपने उसके लिए बावन हज़ार रुपये दिए, यानी 52,000। सही है?"). A cover figure the customer states is read back the same way. A hedged or ranged premium ("पचास बावन हज़ार के आसपास") is read back as said, with both ends (a range is not read back for cover). A reply that names another figure gets "so what is the right amount?"; "I don't know" is recorded as unresolved and not pressed. At most three read-backs per product. Why: Prisma v3.0 writes some amounts confidently wrong (§9, E3).
9. **Close.** Thanks, the pointer to check the call is genuine, and "our team may call again" only when the live call left something unresolved. Flags are computed after the call, so the bot has no flag to announce and promises nothing. The close mentions no other product.

**Two readings on figure turns.** Where the dialogue expects a figure, the server also fetches the second Prisma reading (v2.5 `transcribe`, bounded at 2.5 s; a late or failed reading counts as missing) and passes both to `step(..., second_reading=...)`. If both give the same figure, it is read back at once. If they differ or one holds no figure, the bot asks the customer to say the amount once more (once per product), then reads back. At a read-back, one yes and one no repeat the read-back. `Turn.text` holds the reading the call acted on and the other is kept with an `agreed` flag for the evidence. **The order matters and a report and the code disagree:** P2's contract asks for v2.5 first (iteration 1 verifier H4: on the 240 real Prisma pairs of the development amounts set, the held figure was wrong 2 times with v2.5 first against 16 with v3.0 first), and `readings()` in `samajh/server/samajh_dialogue.py` passes v3.0 first. Open (§15 item 34).

**Unclear, refusals and ends.** An unclear answer is asked once more in simpler words, then recorded as unresolved (one re-ask also avoids the "nagging" pattern in RBI's dark-pattern annex, A20). The bot never argues with the customer and never explains the product during the call: that would contaminate the test. Eleven outcomes: `completed`, `wrong_party`, `not_confirmed`, `no_go_ahead`, `second_check_failed`, `declined`, `human_requested`, `turn_limit`, `call_back_later`, `language_switch` (the call ends and records the language asked for; there is no live switch), `no_response` (two silent turns in a row). A refusal, a request for a person or a request for a later call ends the call (without a stated time the bot asks "when should we call?" once). "Who is this?" and "is this a fraud call?" get the verification lines and the question again, twice at most. "Be quick" continues the call. A third-person or habitual narration ("वो लोग हमेशा बोलते हैं") makes refusal words an answer, because those are the sentences the product exists to hear. Limits so a call always ends: one re-ask per question, at most 60 bot utterances, 3 read-backs per product, 2 stop questions, 2 silences. An LLM turn classifier (Mistral small, 2.5 s wall-clock limit) works beside the word lists; on a failure the turn keeps the word lists' reading and is marked degraded.

**The call keeps no tested value.** `start` keeps a plan (loan id, first name, birth year, product ids) and nothing else from the record. No line can depend on the kind, premium, payment source, cover, term, cancel window, consent or provider choice, and the only figures the bot says are ones the customer said first. Test: two records that differ in every tested value got word-for-word identical bot lines (random customers in four languages, and random-interpreter calls; the test is extended to the new branches). The bot's words do show that a product is on record and how many.

**Call length.** An informed one-product call is 147.6 s by word count (bot plus customer, assumed 2.5 words a second; `call_seconds`), under the 150 s target by 2.4 s. A misled customer who talks more ran 184.8 s. Nothing has been timed on audio.

**What grounds the opening.**
- The call is made from the lender's 1600-series number. Required for service and transactional calls: TRAI direction of 19 November 2025 para 8(iii); RBI/2024-25/105. No TRAI text classifies a feedback call. We treat it as a service call, and it carries no promotional content (promotional content needs the 140 series and consent under the TCCCPR).
- The lender tells its telecom provider in advance that it uses automated calls: TCCCPR regulation 4 as substituted in February 2025. The Third Amendment of 18 September 2026 widens this to a declaration of all application-to-person calls, from 60 days after gazette publication.
- The AI line and the offer of a human: recommended by RBI's FREE-AI committee report (para 4.4.54, read in a mirror copy). We found no law that requires them.
- The recording line: our choice. The only RBI recording duty we found is for recovery calls.
- The purpose, the right to decline, and the pointer to a written notice: required by the DPDP Act sections 5 and 6 from 13 May 2027 where the lender relies on consent.
- Calls are placed between 10:00 and 19:00: our choice (85N(4) sets 09:00 to 19:00 for sales staff and the card rules 10:00 to 19:00).
- Why the opening changed from design v1: v1 asked for loan-account digits and a date of birth and named the loan before confirming who had answered. RBI's public advice says never to share account details, PIN or OTP with anyone; an unknown caller asking for them looks like the pattern it describes (E5.2, E5.3), and naming the loan first would disclose it to whoever answers. We found no RBI text that prescribes how to authenticate a customer on an outbound call (E5.1). A first-name "yes" alone is a weak check, which is why step 3 exists.

## 6. How it works

```
LOAN RECORD (synthetic) ─► DIALOGUE (samajh/dialogue + data/prompts/: line templates, no value under
                           test is kept) ─► bot lines (Timbre v3.0, 8 kHz; fixed lines pre-made,
                           read-backs made on the turn because they carry the customer's figure)
customer audio, each turn ─► PRISMA REST (v3.0 transcribe; on figure turns v2.5 transcribe as well)
                           ─► AMOUNT NORMALISER (fraction-aware; the two readings compared)
        after the call ──────────────────────────────────────────────────────────────────────
whole call ─► PRISMA BATCH (segment times, speakers) ─► aligned to the customer's turns
transcript ─► EXTRACTOR (LLM, strict schema, a quoted span per field; requests in parallel)
           ─► RULE ENGINE (pure functions: answer vs record ─► flags and gaps) ─► TIER ─► CASE SUMMARY
case file (tier, summary, every quote with turn id and audio offset, both readings of each figure,
models and parameters, audio hash) ─► REVIEWER QUEUE (`refer` cases) · HALF-YEARLY REPORT (all tiers + reach funnel)
```

**Core types (sketch; `samajh/types.py` wins)**
```python
# The lender's record (all frozen; unknown fields rejected)
Product    = {id, kind: "credit_life", provider, premium_inr, cover_inr, term_months,
              paid_from_loan, required_for_loan, risk_mitigant, provider_choice_offered,
              cancel_window_days | None,
              features: set of is_deposit|refundable_anytime|guaranteed_return|
                               one_time_payment|withdrawable_after_period,   # claims true of it
              consent: {method: signed_form|otp|digital_click|recorded_call|verbal, at: date} | None}
LoanRecord = {loan_id, lender_type: "bank"|"nbfc", borrower (synthetic), loan_kind, sanctioned_inr,
              disbursed_inr, disbursed_on, tenure_months | None, products: [Product]}

# What the customer said: every answer is exactly one of four states
Answer[T]  = NotAsked | Unclear(reason) | DontKnow(quote, turn_id) | Stated(value, quote, turn_id,
                                          hedged, approximate, low, also)
# Two layers: the LLM only fills the first; deterministic code builds the second
RawExtraction -> Beliefs     # rupees, months, days parsed; every quote found in the right customer turn

Flag = {rule_id, reason: FlagReason, clause, product_id, severity, expected, heard, quote, turn_id, also}
Gap  = {rule_id, reason: GapReason, clause, product_id, quote, turn_id}
Tier = refer | incomplete | understanding_gap | clear           # derived by tier_of(flags, gaps), nothing else
```
The paragraph a rule may engage is looked up by lender type (A5, A19): `kind`, `premium`, `cover`, `term`, `cancel_window`, `recall`, `recall_unmatched` engage 85Y (101Y for NBFCs); `consent` 85G (101G); `bundling` 85V (101V); `loan_funded` 85W (101W); `belief_mismatch` 4(20A)(ii) (6(9A)(ii)); `sale_conduct` and `evidence` are `internal`, engaging no paragraph. `Verdict` (`clear | flag_for_review | unclear_needs_human`) stays because the frozen gold is written in it; new code reads `tier`.

**Rules.** Deterministic; the LLM is never called. The paragraph in brackets is the commercial-bank one:
- `kind` (85Y): the stated kind ≠ the record ("FD" vs credit-life) → flag. "I don't know what it is" → flag. No usable answer → gap.
- `premium` (85Y): beyond 1% of the record → flag; "I don't know" → flag (medium). The premium **passes only after the customer confirms a read-back of the same figure** (for a range, a read-back with the same two ends). Within the approximate tolerance (10%, range-aware) and confirmed → `premium_approximate` (low). Further off and confirmed → `premium_differs_confirmed`; unconfirmed → `premium_differs` (it may be a mis-hearing). A confirmed range wider than twice its low end never passes (`not_comparable` gap).
- `cover` (85Y): within 1% and unhedged passes. A plain figure beyond tolerance is `cover_differs_confirmed` once the customer confirmed a read-back of that figure and `cover_differs_unconfirmed` until then; hedged or approximate, or "I don't know", is a low flag.
- `term`, `cancel_window` (85Y): unaware or different → low flag; "I don't know" → low flag; the cancel "by when" is compared in days with 1 day of tolerance; the code never states a right. "As long as the loan runs" is compared with `tenure_months` on the record, else a `not_comparable` gap.
- `recall` (85Y): asked what they took, the customer names no product on the record → low flag (`recall_not_named`). A customer who says they took nothing → `recall_denied` (high) while the denial stands; if the customer later names the product kind on the record, it becomes `recall_not_named` with both quotes.
- `recall_unmatched` (85Y, case-level): an insurance, deposit or investment named that is not on the record → flag (medium).
- `consent` (85G): no consent on record → flag. A record on file passes only when the customer's own account includes this product **and** names the same method of agreeing. A product not recognised → flag (high); "I don't know what I agreed to" → flag; a different method → flag (medium); agrees but cannot say how → gap.
- `loan_funded` (85W): `paid_from_loan` and (no consent, or the customer says it was paid separately or did not know) → flag. The record says paid separately and the customer says deducted → flag. Record says separately and the customer does not know → gap (§15 item 19).
- `bundling` (85V): the product was required (per the record or the customer) **and** at least one of: the record says it is not a risk mitigant; the customer describes it as a deposit (not a risk mitigant on any reading, A16); the record shows no choice of provider; the customer says they were not told they could buy it elsewhere. Each reason is its own flag (high).
- `belief_mismatch` (may engage 4(20A)(ii)): a belief contradicts the product's `features` (refundable, guaranteed return, FD, or a single payment when the record does not list `one_time_payment`; the payment-frequency question must have been asked for that last one) → flag. The money-back question must be asked: without a usable answer the product is at best a gap, and "I don't know" is a low flag. The paragraph is shown as the paragraph the flag may engage, never as a verdict.
- `sale_conduct` (internal, case-level): the customer voices a concern about how the sale or the confirmation was handled (told what to answer, learned of the product only after the sale) → flag (high).
- `evidence` (internal): a quote that is not in the call transcript supports no verdict → gap.

**Answers the rules read with care** (`P3a-contract.md`): a hedge ("करीब", "शायद", "I think") or a narrow range ("पचास बावन हज़ार") is read as (low, high), marked, never a pass by itself; a correction, a negator in the same clause, "and", three ends, or a range wider than twice its low end stays refused. A question asked twice keeps every answer; **two stated, incompatible answers** (beyond 1% for amounts, or 10% when hedged or ranged) become an `answers_conflict` flag, while "I don't know" before or after an answer, a restatement, or an approximate and an exact figure inside it are not conflicts. A stated answer that a later clause of the same reply takes back ("…, ऐसा तो नहीं था", "नहीं नहीं", "galat bola", "actually no") is never a stated value: a gap, and a conflict if a different answer follows. A failed model call on a reply makes only its own fields `Unclear(extraction_failed)`; a failed screening call becomes a case-level gap. Silence is never a pass: a question never asked or not usably answered is a gap.

**Tiers** (the one table is `FLAG_TIER` in `samajh/types.py`; the code wins):

| Tier | Meaning | Flags | Gaps under rule |
|---|---|---|---|
| `refer` | a human must look; goes in the reviewer queue | `kind_*`, `premium_differs_confirmed`, `cover_differs_confirmed`, `recall_denied`, `recall_off_record`, `consent_*`, `funded_*`, `unfunded_says_deducted`, `bundled_*`, `feature_contradicted`, `sale_concern`, `answers_conflict` on these rules | none |
| `incomplete` | the call did not yield enough to decide | `premium_differs`, `cover_differs_unconfirmed` | `kind`, `premium`, `consent`, `loan_funded`, `bundling`, `belief_mismatch`, `recall_unmatched`, `sale_conduct`, `evidence` |
| `understanding_gap` | reported in aggregate in the half-yearly report, not queued | `premium_dont_know`, `premium_approximate`, `cover_differs`, `cover_dont_know`, `term_*`, `cancel_*`, `recall_not_named`, `feature_dont_know`, `frequency_*`, `answers_conflict` on cover, term or window | `cover`, `term`, `cancel_window`, `recall` |
| `clear` | every rule passed | none | none |

A product's tier is the worst of its flags and gaps; a case's tier is the worst of its products and the case-level ones. Term and the cancellation window stay `understanding_gap` even when the customer states a wrong figure (coordinator decision, §15 item 28). A flag is evidence for review, never a finding: no line says "mis-selling" or "refund", and the 85Z refund duty arises only where mis-selling is established (A18), which a flag is not.

**The case summary and the evidence.** `samajh.rules.summarise(record, result)` returns what a reviewer reads: one line per distinct `refer` issue and one line per rule for the rest, each with the record's value, the customer's best quote, its turn id and the paragraphs it may engage. On the judge's typed misled call the 11 iteration 1 flags became 2 `refer` lines, 4 `incomplete` and 3 `understanding_gap` lines (P3a report §6); the judge's ordinary informed customer, a referral in iteration 1, is no longer one (it ends `incomplete` because the iteration 1 dialogue made no read-back of the range; with the read-back and `tenure_months` on the record it is `understanding_gap`, P3a report §3). The case file adds both readings of each figure, the models and parameters, the audio hash and per-turn latencies. A flag on `kind`, `premium`, `consent`, `bundling` or `loan_funded` is the evidence pack for the bank's 85Z review: the record, the customer's words with turn ids and audio offsets, and the paragraph engaged.

**The reviewer queue and the half-yearly report** (`samajh/ops`, `web/review`, over a synthetic 200-loan book, `data/loanbook/README.md`). The sampler draws a share of the sales made since the previous draw that are still within 30 days of the sale (draws do not overlap, every eligible sale has about the same chance, no attempt after day 30); the attempt log keeps every attempt; the queue holds the `refer` cases, one page each (the loan, the refer lines with their quotes, the other lines, the questions left undecided, the transcript, and the decisions recorded so far; a decision is one of a list of neutral choices with a note and the reviewer's name, and carries no interval); the report is the artifact para 85Y names: the reach funnel (sampled, attempted, answered, right person confirmed, completed within 30 days) is its denominator, the tiers of completed calls and each rule's finding are grouped as features, risks and how the product was sold, each with an interval for sampling among eligible sales only. Real phone sessions enter the queue and the report (`samajh.ops ingest`); the batch's other calls are simulated from the builders' assumed customer mix, so no share in it says anything about a real lender. The report's own risk note says risk coverage is thin: one question bears on risk (can the money be got back), and nothing asks about exclusions, claim conditions or what happens to the cover if the loan closes early (§15 item 35).

**Amounts.** We use `format=transcribe`, then a fraction-aware parser (sawa / saadhe / paune / dedh / dhai; Tamil and Kannada 1.5 and 2.5). The measured weakness of Prisma v3.0 is in §9 (E3). *Design consequence, adopted (§15 item 16):* each figure turn is transcribed by both v3.0 and v2.5 and `samajh.amounts.cross_check` compares the parsed readings (`Agreed(rupees)` or `ReadBackNeeded(readings)`); a disagreement or a missing reading makes the bot ask again and then read back, and the read-back stays for every critical amount whatever the readings say. v3.0 alone is not enough: its wrong amounts come with no warning. Shapes the parser deliberately refuses (it returns no amount, which leads to a re-ask and a read-back): a number word directly before digits, clock times beside amounts, romanised Hindi amounts ("bavan hazaar"), Kannada ondu kaalu and ondu mukkaalu before a unit (needs a fluent Kannada reader), "3/4 lakh" in Tamil, and a word the lexicon does not know that stands before a number and looks like a fraction or unit word. A "one" after a hundreds word is part of the number ("तीन सौ एक दिए" = 301); after a thousand-or-larger unit and before a verb it is ambiguous, never the smaller figure; before a noun it is a determiner. The development set's after-fix numbers are in-sample and are not reported here (`eval/amounts/REPORT.md`, `references/pilots/W1-core-report.md` §3).

## 7. Gnani models used

| Model | Use |
|---|---|
| **Prisma STT v3.0** (`/stt/v3`, `format=transcribe`, language set per call) | Each customer turn (REST, ≤30 s); the first reading on figure turns |
| **Prisma STT v2.5** (`/stt/v3`, `format=transcribe`, language set per call) | The second reading on figure turns (bounded at 2.5 s; a late or failed reading counts as missing), compared with v3.0 (§6, Amounts). It is also the other arm of the v2.5 vs v3.0 comparison in results |
| **Prisma Batch** | Full-call transcript with segment timestamps and speaker labels (v3.0, two speakers), aligned to each customer turn for the audio offsets in the case file. In the P1 runs (4 calls) the speaker with the most overlap was the customer's for every customer turn and segment edges fell within 0.09 s of the logged turn edges |
| **Timbre TTS v3.0** (8 kHz, `hi-IN` / `hi-en` / `ta-IN` / `kn-IN`) | Bot lines (the fixed lines pre-generated; a read-back carries the customer's own figure and is synthesised on the turn) and synthetic customer voices for testing. The voice is Shivani for every language and has not been compared with others by ear. The 101 fixed lines made for P1 predate P2's rewrite and are rebuilt when the lines are final; nobody has listened to them |
| Voice cloning | **Not used.** Nothing here needs it, cloning a bank officer's voice would be misleading, and voice patterns used for authentication are biometric data under the SPDI Rules 2011 (read in a mirror copy). No voiceprints either |
| LLM: `openai/gpt-6-luna`, reached through OpenRouter | Extraction only: strict schema, quoted spans, no arithmetic, no verdicts. Runs after the call, not per turn (below) |
| LLM: `mistralai/mistral-small-3.2-24b-instruct`, reached through OpenRouter | The dialogue's turn classifier, beside the word lists, with a 2.5 s wall-clock limit (§5). It returns a label, never a number or a year. It is the one place an LLM runs during a call; its role at the opening is being changed in the P2 fix round |

**Extraction model: `openai/gpt-6-luna` through OpenRouter.** This is W5b's recommendation (`references/pilots/W5-extractor-report.md` §2.4). It replaces the earlier default, the cheap `mistralai/mistral-small-3.2-24b-instruct`, which `references/pilots/W2-clients-report.md` chose on a 16-utterance probe. The model returns enums, clause numbers and spans, never turn ids, product ids, rupee figures or verdicts. Code resolves them against the customer's reply, so every quote kept is a slice of the reply (frozen-set run: 0 of 802 spans not in the reply, 0 of 1,195 clause numbers out of range). The model rejects the `temperature` parameter (OpenRouter answers 404), so it is not pinned to 0 and a second uncached run could differ; the extractor also now runs its requests in parallel. `samajh.pipeline.default_llm()` leaves the parameter out. It is a reasoning model and needs room: at 800 output tokens one hard reply came back cut off and empty, so the limit is 4,000.

- **Cost.** $0.00171 per transcript on the frozen set (144 transcripts, 3,391 LLM requests, $0.24589 with nothing cached, $0.00007 per LLM request) and $0.00153 per transcript on the development set (n = 20 transcripts). That is about twice Mistral ($0.00081 on the development set) and a third of `anthropic/claude-haiku-5.5` ($0.00502).
- **Latency.** Per LLM request, when first made: median 1.88 s, p90 3.38 s (frozen-set run; wall time of the client call, retries included). A transcript takes 20 to 24 requests; in iteration 1 they ran one after another (about 40 s at the median, inferred from the per-request median) and P3a now runs them in parallel, so the end-to-end time of a case file is not measured. **Consequence: extraction runs after the call, on the whole transcript, and not per turn.** It is fine after a call and too slow inside one. Anything the bot must decide during the call (the one re-ask of an unclear answer, §5; the read-back) cannot wait for the extractor. The dialogue decides these turns with word lists and the turn classifier (§5).
- **Why the earlier default was rejected.** On the development set (20 hand-written calls, 5 per language, 7 of them gold-clear), Mistral raised false alarms on 3 of the 7 gold-clear calls (`google/gemini-2.5-flash-lite`: 7 of 7; `openai/gpt-6-luna` and `anthropic/claude-haiku-5.5`: 0 of 7). Call verdicts right: gpt-6-luna 20 of 20, Haiku 20, Mistral 17, Gemini 13. Fields right (n = 304): gpt-6-luna 304, Haiku 303, Mistral 298, Gemini 285. The weaker models read a plain "I signed" or "I gave the OTP" as a sale concern. They also misread negations. On a probe of 24 Hindi and Hinglish replies written so that the first clause, read alone, gives the opposite answer, gpt-6-luna and Haiku read 24 of 24 correctly, Mistral 20 and Gemini 18. Two of Mistral's four misses were in the false-clear direction: a reply that begins "I agreed" and then denies it was read as consent given. The probe shows a failure pattern and is not a rate, and it has no Tamil or Kannada. A difference of one or two on these sets is noise (Mistral gave 18 of 20 verdicts in one run and 17 in another with the same prompts); the gap between the two groups of models is not. The development set is in-sample for the prompt, which was iterated on it, and the model was not selected on the frozen set (it is kept for one final measurement).
- **Alternative.** `anthropic/claude-haiku-5.5` matches gpt-6-luna on the probe, is one field behind on the development set, costs 3.3 times as much per transcript and is faster per request (median 1.04 s).
- **Not checked.** Any other caller that sends `temperature` to this model would get a 404. The dialogue's LLM fallback does not use this model by default (it names `mistralai/mistral-small-3.2-24b-instruct` in code, chosen on the dialogue's turn set, and sends 512 output tokens after a 30-token limit left a reasoning model's reply empty); the `--llm-model` option can name another.
- Caveats: text only and scripted customers, as in §9 E2.

## 8. Engineering constraints

- **Concurrency is 1 per account, not per key.** A second simultaneous REST request gets an instant 429 "Only 1 active request is allowed at a time", and with two keys from the same account the second still got it (6 of 6 trials, order shuffled, 2026-11-10). One queue for all requests, exponential backoff, no parallel REST calls; STT and TTS share the slot. In the probe a WebSocket streaming session did not occupy it, but streaming is not shipped (§15 item 12). A live turn waits 5 s for the key lock and then fails with `gnani_busy`, so nothing else may use the account during a call (§13). Fixed bot lines are cache hits; a read-back carries the customer's figure and is synthesised on the turn (about 1.4 s in the P1 runs, n = 2).
- **Caching:** key = sha256(model, params, audio/text). Noise and 8 kHz variants are made offline and only STT is re-run per condition.
- **Cost:** client estimates, not dashboard readings: 0.010 credits per STT audio second and 0.002 per TTS character. About 295 of the 1,000-credit project cap are used by the end of iteration 2's build wave; the 101 fixed bot lines cost about 13, the held-out amounts run 136.5 (`uv run python -m samajh.clients.gnani ledger` reads the local ledger). The dashboard has not been read.
- **Latency** (P1, `P1-report.md` §2; Timbre customer voices, key lightly used; n = 31 uncached turns of replayed calls, plus 4 turns by microphone in headless Chrome): STT for both readings median 364 ms (p90 569, max 1,632); the dialogue on word lists alone median 1 ms; with the LLM classifier consulted median 1,398 ms (p90 1,753; 15 of 31 turns); fixed lines from cache 3 ms; a read-back made on the turn about 1.4 s (n = 2); in Chrome, from the end of speech to the bot's audio, a median 1,145 ms (n = 4, yes/no turns only). The phone does not answer before the grace window passes (yes/no 1,000 ms to open 1,800 ms). No open or amount question has been answered by microphone.
- **End of speech** (`web/phone.js`, `samajh/server/settings.toml`): the cut and the grace come from the kind of reply the last bot line calls for (yes/no 700/1,000 ms, short 800/1,200, amount 1,000/1,600, open 1,100/1,800). At the cut the take is sent; if the customer resumes inside the grace window the phone sends the whole answer as part 2, which supersedes part 1. In headless Chrome a 1,300 ms pause on the yes/no question lost the second half (only "हाँ जी।" was heard). None of these values was set on human audio; pause statistics are logged per turn so they can be.
- **Backend proxy** (FastAPI, `samajh/server/`): browsers can't set `X-API-Key-ID`. The Gnani and OpenRouter keys live in environment variables only. The server resamples uploads to the line rate with ffmpeg, binds 127.0.0.1, refuses other Host and Origin values and has no login. A call's log and dialogue state are one atomic file, so a call resumes after a restart. After the call a background job builds the case file; a failed step is named and the case is `failed`, never given a tier.
- **LLM hosting:** v1 sends only synthetic transcripts to OpenRouter. A real lender must check where transcripts may go first: for digital lenders, the Digital Lending Directions require storage in India and deletion within 24 hours of processing abroad (E2.9).
- **Synthetic data only:** obviously fake names, loan IDs, years of birth and numbers. Ombudsman cases are re-created with invented parties, never quoted with real names.

## 9. Evaluation

| # | Question | State |
|---|---|---|
| E1 | Does a teach-back-style question catch what a yes/no call misses? | **Retired as a headline** (§15 item 9). It is true by construction: coached and acquiescent customers say yes to the closed script because the script says so, and the "never asked" stratum counts questions the closed script was written without. The iteration 1 stratum table stays in `eval/text_path/runs/iter1/` and `W5-extractor-report.md` §2.2, not here. Replaced by E6 |
| E2 | Are the flags and tiers right? | Text path on the frozen scenario set, below. Scripted text, not speech |
| E3 | Are amounts heard correctly? | Held-out TTS set, development set and public recordings, below |
| E4 | Does it hold on real voices? | **Nothing recorded.** Target: ≥10 improvised calls per supported language (the user and consenting friends, from a brief card, not a script; package P4) |
| E5 | Does it survive phone audio? | Amounts: yes, on TTS audio with synthetic noise (`eval/amounts/REPORT.md` §2.3). The call path: no |
| E6 | Customers the builders did not script (package P5) | **Not run.** A different model plays each customer from a persona card, voiced through several Timbre voices and the phone channel, through the real dialogue and extractor; disposition is a parameter applied to both the open call and a matched best-practice closed call, so the result is a curve (catch rate against the probability of agreeing). Reports referrals per 100 informed customers and misses per 100 misled ones, text against voice |

**E2, text path** (`eval/text_path/runs/frozen__openai-gpt-6-luna.md`; frozen set version 3, hash prefix 14e49b58, 144 scripted calls = 36 base cases × 4 languages; the extractor `openai/gpt-6-luna`, §7). The set was run once in iteration 1 and rerun after P3a's changes (one live pass, then cache-only reruns); it was never tuned on. **Results on text, the upper bound for the voice path.** Hindi and Hinglish (72 calls from the 36 base cases: 19 with a customer problem, 9 informed customers on a compliant record, 8 informed customers with a fault on the lender's record):
- Customers with a problem: **2 of 38 calls ended `clear` or `understanding_gap`** (1 of 19 base cases: U07, a wrong cancellation window, `understanding_gap` by design). Tiers of the 38: `refer` 30, `incomplete` 6, `understanding_gap` 2.
- Informed customers on a compliant record: **0 of 18 referred** (all `clear`; 0 of 9 base cases). Informed customers with a fault on the lender's record (no consent on record, no choice of provider): 8 of 16 referred.
- The rule engine on the set's own perfect extraction misses the same 2 calls, so these misses are the tier table's, not the extractor's. Verdicts 143 of 144 over all four languages and fields 2,166 of 2,180; the one wrong verdict is B03 in Tamil (experimental), a missed "paid only once" claim, caught in the other three languages.
- Intervals are wide: 36 independent base cases, 9 of them gold-clear; cluster by base case. Gold agrees with the rule engine on 144 of 144 partly by a coordinator decision on 8 scenarios (§15 item 17), so that agreement is not independent confirmation. 70 of the 1,604 frozen replies also appear in the development set the prompt was tuned on. No speech, no STT output; Tamil and Kannada not human-reviewed (13 of the 17 wrong fields in the iteration 1 run were in those two languages).
- The tier decisions of the coordinator (cover, denial, retraction, §15 items 28 to 30) were made on verifier probes and development transcripts, not on the frozen set.

**E3, amounts.** *Held-out TTS set* (`data/amounts_v2/amounts-v2.jsonl`, manifest sha256 `1beea924…`; `eval/amounts_v2/tables-tts.md`; independently verified, every number reproduced, `references/reviews/iter2/verify-P6.md`). 280 Hindi and Hinglish sentences from Timbre voices, built to stress amounts that skip a place-value group; 68 skipped-group amounts, each with a matched control (same carrier, voice and leading group), frozen before any audio; scored with the amounts parser as of commit 59c12d9; exact match on the rupee amount; simulated 8 kHz phone audio unless stated.

| Phone audio, parser's reading | skipped group (n = 68): different amount | matched control (n = 68): different amount |
|---|---|---|
| Prisma v3.0 `transcribe` | **40 (59%, 95% CI 47-70)** | 0 |
| Prisma v3.0 `verbatim` (same audio) | 1 | 0 |
| Prisma v2.5 `transcribe` | 0 (refused 2) | 0 (refused 2) |

- Exact McNemar on the 68 pairs: 40 discordant one way, 0 the other, p = 1.8e-12. The **verbatim output of the same audio had the right number words in all 40**, so Prisma heard the words; the digits are wrong. "Formatting, not recognition" is an inference (the transcribe output is not always a pure formatting of the verbatim one); the measured fact is the verbatim words.
- **Reported apart:** 14 of the 40 are an "X lakh Y" phrase with Y under 100, written as X lakh Y thousand ("तीन लाख चालीस" as 3,40,000). Colloquial Hindi may mean 3.4 lakh by it, so a native speaker has to say whether they count (open, §15 item 36). The other 26 are wrong under any reading: the lakh dropped ("one lakh three hundred" as 1,300), the crore dropped ("पाँच करोड़ छब्बीस हज़ार" as 5,26,000), the final group dropped, or hundreds turned into thousands ("four lakh nine hundred" as 4,09,000). On clean 16 kHz audio the numbers are 39, 14 and 25.
- Not a function of shape alone (23 of the 68 were right on phone audio). Not a rate for the field: the skipped stratum is 24% of the set by design, and in a pool of 1,358 public Hindi utterances 6 skip a group (0.4%). The pooled "14% of amounts" and a retail-band rate are not to be quoted.
- **Agreement as a confidence signal.** Accepting an amount only when v3.0 and v2.5 `transcribe` agree accepted **224 of 280 clips (80%, 75-84) with no wrong amount accepted** (the Wilson 95% upper bound for 0 wrong of 224 is about 1.7%); on the skipped stratum it accepted 22 of 68, all right, and sends the rest to a re-ask and a read-back. A variant comparing v3.0 with v2.5's `output.literal` accepted 234 of 280 with none wrong, but it was chosen on these same sets: not validated.

*Public recordings, a separate result* (`data/amounts_v2/realvoice-v1.jsonl`; `eval/amounts_v2/tables-realvoice.md`; evaluation only, the audio and text stay on the user's machine). 124 scored clips of Hindi speech (IndicVoices 88, Kathbath 36; read and extempore, phone copy). v3.0 `transcribe` alone gave a different amount on 3 of 124 and v2.5 on 4 of 124; the agreement rule accepted 113 of 124 (91%, 85-95) with **no wrong amount accepted**. Caveats: 107 of the 124 are from the datasets' train splits, which Gnani may have trained on, so this may be optimistic; most clips are solo phone-app recordings, many of them command prompts, 103 of the 124 golds are multiples of 100 and only 15 are ≥ 1,000 and not a multiple of 1,000; **4 clips skip a group and v3.0 was wrong on 1**, too few for a rate.

*Development set* (`data/amounts/amounts-v1.jsonl`, 240 sentences in four languages, `eval/amounts/REPORT.md`; in-sample for the parser after its fixes). First saw the skipped-group fault (v3.0 read 6 of 16 such amounts against 161 of 164 other non-fraction amounts; v2.5 read 15 of 16) and the agreement signal (the two models agreed on 200 of 240 and 199 of those were right). The held-out set replicates the fault; the numbers above replace these as the headline.

**Gold standard and circularity.** 11 of the 36 base cases are templated on public awards: five of the customer-relief awards in §1, BNG-L-033-1617-0600 (a policy bought "as a requirement of a security deposit for the overdraft facility"), BHP-L-013-1617-0436 (an "Fixed Deposit to get the housing loan"), Baramulla consumer commission CC 33/2025 v J&K Bank (₹2,00,000 debited for a policy without consent; our copy of that order is a scan hosted by a news site), and three awards named nowhere else here: BHP-L-021-1617-0456, PUN-L-041-1617-0649 and PUN-L-009-1617-0009. Compliant scenarios are written from the rules; awards the insurer won are not used as compliant gold. Gold verdicts are written first and **frozen with a hash before any audio is made**. Each templated case records the remedy in its award: 5 refund, 4 conversion, 1 partial refund, 1 other; of the 22 relief awards we read, about two-thirds ordered a refund and one-third a conversion. The set is built to exercise each rule, not to mirror how often a problem occurs, so no rate on it says anything about prevalence. Speech is templated, one to three variants per answer. The frozen set is for final measurement only: never tune on it. Datasheet and history: `data/scenarios/README.md`, `CHANGELOG.md`.

**What teach-back is, and what we don't claim for it.** Teach-back means asking a person to explain in their own words what they were told. It is well studied in healthcare; the newest systematic review (2026) found no clear pattern of effect on knowledge. We found no study of teach-back for loan or insurance sales, or by an automated voice. Most of this rests on abstracts, not full papers (C3).

## 10. Demo (60 s)

The plan below is the judge's (`references/reviews/iter1/judge.md` §4), not yet recorded. Nothing on screen may be a real phone number, account number or person.

1. 0 to 5 s. One line of 85Y and the date 1 January 2027.
2. 5 to 15 s. The usual confirmation call: "Kya aapne policy li hai?" "Haan." Confirmed. Caption: this customer was told it is an FD, and says yes to the closed question (an illustration of scenario U02, not a measured rate).
3. 15 to 40 s. The Samajh call on the browser phone in Hinglish, in the user's own voice: "Loan ke saath aapne kya-kya liya?" "Ek FD, security ke liye, bavan hazaar." Split screen: the loan record on one side, the customer's quote lighting up against it; on the amount turn, the two Prisma readings side by side ("v3.0 52,000, v2.5 52,000, agree"), then the read-back. The record: a ₹5,00,000 gold loan, ₹52,000 deducted, credit-life on record, no consent record (figures ours, not from any award).
4. 40 to 50 s. The reviewer's case page (the referral, the quote, the paragraphs it may engage, never "mis-selling"), then the half-yearly report page built from a batch of calls, labelled simulated.
5. 50 to 60 s. Two numbers with n and source (the held-out amounts result and the agreement rule, §9 E3) and "Prisma v2.5 and v3.0, Timbre v3.0, Prisma Batch".

Close on the Ombudsman's own words if time allows: "The PIVC recording is clear about the terms and conditions of the policy but the maturity benefit is not explained." No voice figure about the product itself exists yet; show none until E6 or E4 has run.

**Award target:** Real Deal, with the cut also usable for Demo Day Drop. Jugaad Genius is the best alternative (two Prisma versions checked against each other as the confidence score Prisma does not return). Frame the user as the borrower who was sold an "FD", and the bank as the payer.

## 11. What we can and can't claim

**We can say:**
- The 85Y quote, verbatim, cited as "para 85Y, inserted by RBI/2026-27/115 (15 June 2026)" for commercial banks, and 101Y for NBFCs.
- "From 1 January 2027 it applies to commercial banks, small finance banks, payments banks, local area banks, regional rural banks, urban and rural co-operative banks, All India Financial Institutions, NBFCs and housing finance companies, each under its own direction." The NBFC direction excludes Core Investment Companies, Account Aggregators, Non-Operative Financial Holding Companies and NBFCs with no customer interface.
- "On 10 November 2026 we found no vendor page that cites para 85Y or 101Y, or that sells a product built for RBI's 30-day post-sale feedback mechanism. We did find adjacent products: AI welcome calls that ask whether the borrower understood (SquadStack, Edesy), post-sale verification for insurers that compares the customer's understanding with the policy (Ringg), and a sales-call audit against policy documents (NuSummit)."
- "In some Insurance Ombudsman awards the insurer relied on a recorded verification call and the customer still got relief (BNG-L-041-1617-0797, PUN-L-036-1617-0228, PUN-L-017-1617-0684). In other awards a recorded call won the case for the insurer (PUN-L-013-1617-0583, NOI-L-036-1819-0337)."
- The consent, bundling and loan-funding checks are added to the 85Y callback. The bank must meet those paragraphs anyway.
- Under 85V, a third-party product that a lender requires "as a risk mitigant" is not compulsory bundling if the customer may buy it from any provider. RBI does not define "risk mitigant". Treating credit-life as one is our reading.
- "IRDAI recorded 26,667 unfair-business-practice grievances against life insurers in 2024-25, up from 23,335. The category includes mis-selling. The National Housing Bank wrote to housing finance companies on 10 December 2024 after inspections found insurance bundled with housing loans. No official source we found says how many borrowers are sold insurance with a loan."
- RBI's illustrative list of dark patterns names "loan protection insurance by default during the loan application process". It illustrates a user-interface pattern under 85X. Our hero case is a misdescription at a branch, so we present it as a related pattern, not the same thing.
- The grounding of each line of the opening, as labelled in §5: required, recommended, or our choice.
- For policies sold by distance marketing, IRDAI's 2011 guidelines required sampled verification calls "to ascertain whether the client has understood the benefits, features and disclosures". Whether they are still in force is unconfirmed.
- The UK regulator's March 2026 review lists post-sale comprehension calls and customer call-backs as good practice.
- Only measured numbers, each with n and audio source.
- "Flags for human review."

**We can't say:**
- "RBI requires voice calls" (85Y names call-backs or surveys and sets no channel).
- "It applies to every RBI-regulated lender."
- "85Y requires consent/bundling checks."
- "Captures consent" or "prevents mis-selling".
- "This is mis-selling", or a mis-selling paragraph printed as a verdict.
- "A flag triggers a refund under 85Z."
- Any mis-selling prevalence rate. Complaint counts are quoted as complaint counts.
- "PIVC is mandatory."
- Indian SMS-vs-voice response rates (we found no controlled Indian comparison for a lender's customers; the closest peer-reviewed study is from Nigeria, on cold calls to the general population).
- "RBI requires recording of the feedback call" or "RBI requires AI disclosure".
- "TRAI classifies a feedback call as a service call." We treat it as one.
- "No consent is needed because RBI directs the call." The DPDP Act has no general legal-obligation ground.
- "Teach-back is proven for financial products" or "for voice AI".
- "The customer asked for ₹5 lakh and received ₹4.48 lakh" as a fact of award BHP-L-021-1617-0529. The award states only the ₹52,000.
- TTS accuracy presented as real-world accuracy. Every speech number is TTS-only except the public-recording result in §9 E3, which has its own caveats.
- A text-path result (§9 E2) presented as a result on speech or on real callers, or as "no misses": the Hindi and Hinglish frozen-set run ended 2 of 38 problem calls as `clear` or `understanding_gap`.
- A dialogue result (the tests, the synthetic replies, any builder's probe counts) presented as a result on speech, on real callers or on a reviewed script, or the call as ready for a live line: it is not (§13).
- "Supported" for any language before it meets the bar in §4.
- "Production-ready."
- "Nobody does this."

**Wording for the Prisma number-formatting finding** (from `references/reviews/iter2/verify-P6.md`). **Allowed:** the matched comparison of §9 E3 with its n, interval and set description; "its `verbatim` output of the same audio had the right number words in all 40, and v2.5 wrote none wrong"; the examples "one lakh three hundred" as 1,300 and "five crore twenty-six thousand" as 5,26,000; the agreement result with its n on synthetic clips and, separately, on public recordings; "in public recordings the pattern appeared in 1 of 4 skipped-group amounts: too few for a rate". **Not allowed:** "v3.0 gets 14% (or 1 in 7) of amounts wrong"; "11% of retail premiums"; any per-call or field rate; "100% accurate", "zero errors" or "guarantees" for any scheme without its n and set; "proven formatting bug" or "a separate formatter stage"; "fails whenever an amount skips a group" or "depends only on shape"; "tested on real calls, callers or borrowers"; "validated" for the `output.literal` variant (say "chosen on these two sets, not yet tested on fresh data"); "three lakh forty → 3,40,000" as an unqualified headline error.

## 12. Why we think this is not yet common (our read)

1. **The rule is new.** It was issued on 15 June 2026 and takes effect on 1 January 2027.
2. **A low-cost survey is not excluded.** 85Y names surveys as an example and sets no channel, so a low-cost survey is not excluded by the text. A low-cost survey is the likely default. That is our inference. We found no bank or industry statement on how banks will comply.
3. **Most voice-AI vendors lead with support, sales and collections.** Of 11 vendor sites checked on 10 November 2026, 10 list support, 9 sales and 8 collections. Seven also sell audit or compliance products, and some market adjacent post-sale checks (§11). None of those pages cites 85Y.
4. **It's harder than it looks (our view).** It needs product records, deterministic comparison, and correct Indian amounts. In our 20-sentence TTS pilot (one voice), Prisma's digit output ignored the fraction word in 8 transcripts across 5 sentences. In the 240-sentence set (TTS audio, phone) the naive digit reading was right on 9 of 60 fraction sentences on v2.5 and 54 of 60 on v3.0.

What Samajh adds to the adjacent products: an open question before any product is named, a deterministic comparison with the lender's record, an evidence log, and a measured evaluation.

Unknowns: banks may build it in-house or adapt survey bots, and we found no public statement from any bank on how it will run 85Y feedback. No regulator or survey we found reports how many loans carry bundled insurance. The numbers that exist count complaints.

## 13. Risks

| Risk | State and mitigation |
|---|---|
| **A third party hears the loan named, or a refusal gets the next question (P2).** Independent verification (Opus, 2026-11-10) on its own fresh inputs: the loan was named to **16 of 64 third parties**, and **25 of 45 refusals got the next question with the word lists alone (16 of 45 with the LLM fallback)**. The builder's counts on the verifier's earlier probes (0 of 34 third parties, 0 of 42 refusals) and on its own fresh sets (0 of 20, 0 of 18) were taken on sets it had iterated against. Probe counts of written text, not rates on callers | **Open; a structural fix round is in progress** (the turn classifier becomes the primary judge at the opening, safe defaults, new outcomes). The call is not to be put on a live line, and no person is to be called, before an independent verifier has run it on inputs the builder never saw. A third party who gives a false first-person yes and then the right year of birth passes both checks; the design accepts that (§5 step 3), and P2's own report lists it among the gaps |
| No human voice recording and no fluent Tamil or Kannada reviewer | Every speech number is TTS-only except the public recordings in E3. Hindi and Hinglish are "TTS-only, not human-tested"; Tamil and Kannada text is "not human-reviewed" and out of the product. P4 (20 improvised calls) is the evidence that answers both |
| Circularity: we write the records and the customers' answers; E1 was true by construction | E1 retired. Scenarios templated on awards; gold frozen with a hash. P5 replaces the scripted customers with ones played by a different model from persona cards, with a matched closed arm. P4 adds people |
| Prisma v3.0 writes some amounts confidently wrong (skipped-group amounts: 40 of 68 against 0 of 68 controls, §9 E3) | Two readings on figure turns, a re-ask on disagreement and a read-back on every critical amount. The agreement rule accepted no wrong amount on 224 synthetic clips and 113 public recordings, but the rule was chosen with the evidence in view and the public recordings are mostly train-split. The order of the readings differs between P2's contract and the server (§5, §15 item 34) |
| The dual reading doubles STT calls on figure turns, and v2.5 returned 504 on 15 of 1,184 calls (1.3%; 14 of the 15 Tamil or Kannada) in the iteration 1 amounts run, each succeeding on a second attempt after about 30 s (inferred from ledger times); v3.0 once in 1,456 | A 2.5 s bound on the second reading; a missing reading counts as a disagreement, so the turn falls back to a re-ask and a read-back instead of waiting out the retry. The bound has not been measured on a live call |
| A live call shares the one Gnani account with any evaluation: 3 of 12 live phone turns failed with `gnani_busy` while the iteration 1 amounts evaluation ran. A second key does not help (§8) | Never run an evaluation, probe or other Gnani job during a call or a rehearsal. Giving live calls priority in the lock is a possible fix, not built |
| No human has used the phone: every turn so far is Timbre audio or a WAV fed to headless Chrome. Real microphones, echo, noisy rooms, Safari, Firefox and mobile browsers are untested, and the cut and grace values were not set on human audio (a 1,300 ms pause lost the second half of an answer in headless Chrome) | Before any claim about the phone, record human turns and set the thresholds on them. Until then say "tested with synthetic voices in headless Chrome" |
| The extractor can miss a claim it does not return. One false clear in the frozen text run (B03 in Tamil, a "paid only once" claim; Tamil is experimental). Validation checks what the model returns against the reply; it cannot catch a claim the model leaves out | Measured, not prevented. Every reply is read twice (the answer, then a screen for claims said in passing), quotes are grounded in the reply by code, and the rules are deterministic. The Hindi and Hinglish text run misses 2 of 38 problem calls, both by the tier table (§9 E2). A human spot check of a sample of `clear` calls before any real use is our proposal, not built |
| The call asks almost nothing about risk, while 85Y speaks of features and risks. The report's own risk note says coverage is thin | Open for the next judge (§15 item 35) |
| The bot's words have not been read by anyone fluent, and the banned-wording lint is a word list (in iteration 1, 5 of 52 probe lines of bad wording still passed it). Nothing has been listened to: whether Timbre reads mixed-script Hinglish, "ए-आई" and "ओ-टी-पी" well is unchecked | `load_prompts` refuses a file that fails the lint. A person must read any change to `data/prompts/`; the user's wording review waits for the P2 fix round, then a listening pass. Tamil and Kannada lines were read for structure only |
| The reviewer pages and half-yearly report run over a simulated book, with the builders' assumed customer mix and reach probabilities; the phone cannot yet call a loan from the book | Every page says so. No share in the report is evidence about real sales |
| Judges know the adjacent vendors (SquadStack, Edesy, Ringg, NuSummit) | Name them ourselves and say what Samajh adds (§12) |
| Regulatory wording drifts | Recheck RBI's notifications for amendments dated after 6 August 2026 before submission; quote text, not summaries |
| Four documents were read in copies the issuer does not host (FREE-AI report, SPDI Rules 2011, IRDAI circular 274/11/2020, Baramulla order) | Check each against the official copy before quoting it to judges |

## 14. Where the build stands

- **Iteration 1 (done, reviewed):** records, the Gnani and OpenRouter clients, the amount normaliser, the rule engine, 144 scenarios frozen at version 3, the LLM extractor, the text-path evaluation, the transport and browser phone, the audio harness and the amounts evaluation, and a dialogue that was never connected to the phone. The judge scored it 69 of 100 (the idea 84): the parts were never joined.
- **Iteration 2 (build wave done; verification and fixes in progress):** P3a the decision chain, P3b the loan book, queue and report, P6 the held-out amounts result, P1 the call on the phone to a case file, P2 call v2. Package states: `ORCHESTRATION.md`. Remaining: the P2 fix round and its verification, re-voicing and verifying P1, re-verifying the P3a and P3b fixes, joining the phone to the loan book, the full suite, then an iteration 2 verifier and judge.
- **Iteration 3 (planned):** P5 evaluation on customers the builders did not script, P4 twenty human calls (needs the user), P7 the 60-second demo, a two-page brief, the written submission and a last claims recheck.

## 15. Decisions

Numbers are kept stable for the references in other documents. Closed or adopted items are one line each; the evidence is in the file named.

1. **Reviewers per language.** Adopted as a gate (judge): Hindi and Hinglish aim for "supported" (a fluent reviewer and ≥10 real-voice calls); Tamil and Kannada leave the call. Today there are no human recordings.
2. ~~LLM for extraction.~~ Closed: OpenRouter, `openai/gpt-6-luna` (item 21).
3. **Final name.** Decided by the user, 2026-11-10: **Samajh** ("understanding", the word 85Y's purpose turns on). Used as is in the video and the written title.
4. **Second product family.** Dropped for now. One slide: 85Y covers any financial product, and the lender's own terms are the natural next family.
5. **Key Facts Statement check.** Dropped (uncertain reach for bullet gold loans, no demo value).
6. **Call timing.** Adopted: one field in the sampler; the day since sale is logged and no attempt follows day 30.
7. **A fuller evidence log.** Adopted: the case file keeps the audio hash, every model and parameter, the bot's lines, both readings of each figure and the audio offset of each quote.
8. ~~A "told how to answer" scenario group.~~ Adopted in the scenario set (C01 to C03).
9. **A text-confirmation arm in E1.** Replaced: P5 builds a matched closed arm instead, and E1 is no longer a headline.
10. **The dark-pattern quote on a slide.** Dropped: a related pattern that dilutes the hero case.
11. **A retention setting.** Deferred: one sentence in the write-up. RBI fixes one year after contract end for consent records and nothing for feedback audio; the DPDP Rules set a one-year floor for logs from 13 May 2027.
12. ~~Live streaming STT.~~ **Closed by measurement, 2026-11-10: REST per turn with a browser end-of-speech detector is the only shipped path.** TTS clips only. (a) Streaming was not faster at the same silence threshold: median 0.78 s from the end of speech to the transcript at its default 500 ms (n = 20) against about 0.71 s for the detector at 500 ms plus a REST call (a sum of two medians, n = 20 each). (b) At that default it cut all 4 clips with a spliced 600 or 900 ms pause into two segments. (c) Billing unknown, no cache, and it rejects a comma-separated `language_code` on v3.0 (13 of 13 attempts). Reopen only if human callers pause past the thresholds often enough that turns are cut, or barge-in is needed. Details: `voice-loop-iter1.md` §3.
13. **The money-back probe is part of the flow** and the rule engine requires it, so no call comes out `clear` without it.
14. **A product on record that the customer does not name unprompted** is a low `recall_not_named` flag, now in the report-only tier, not a referral.
15. **A customer who agrees they bought the product but cannot say how they agreed** is a gap; a different method than the record's is a medium flag.
16. **Amount turns get two Prisma readings** (v3.0 and v2.5); disagreement or a missing reading leads to a re-ask and a read-back; every critical amount is read back whatever the readings say. Now in the product: the server fetches the second reading (§5). Open: the order (item 34).
17. **A customer who says they do not know the premium** is a flag (medium, `premium_dont_know`), in the report-only tier. It resolved the one disagreement between gold and the rule engine, in the engine's favour: gold was changed by hand for 8 scenarios (U09 and U10 in four languages) before any audio or LLM extraction, and the set was refrozen as version 3 (§9).
18. **A customer who says they do not know what the product is** is a flag on `kind`. In the code it is still `refer` (`kind_dont_know`); the judge asked for the report-only tier for "don't know" answers. Not changed; open.
19. **`loan_funded`:** the record says the premium was paid separately and the customer does not know how it was paid → gap.
20. **`belief_mismatch` includes a single-payment claim** when the record does not list `one_time_payment` (scenario B03); the payment-frequency question is now asked in the call.
21. **The extraction model is `openai/gpt-6-luna`** (W5b); the choice was not rerun on the frozen set. The dialogue's turn classifier uses a different model (§7).
22. **Extraction runs after the call, on the whole transcript.** Built with parallel requests (P3a); the end-to-end time of a case file has not been measured.
23. ~~Should one invalid model output fail the whole call?~~ Closed: it makes only that reply's fields `Unclear(extraction_failed)`.
24. **The one false clear in the frozen text run** (B03 in Tamil, experimental). Look at Tamil "only once" phrasings on new development replies, never on the frozen set.
25. ~~Changes from the §5 flow that the dialogue worker made.~~ Superseded by P2 (§5).
26. **Does a live call use the LLM classifier?** Yes, since P2 (it was consulted on 15 of 31 turns in the P1 runs, adding about 1.4 s on those turns; §8). Its role at the opening is being changed in the P2 fix round. Open: a lender name on `LoanRecord`, or keep it as call configuration.

From iteration 2 (coordinator and user, 2026-11-10):

27. **Four-tier triage** (`refer`, `incomplete`, `understanding_gap`, `clear`) replaces "any flag means review". `Verdict` stays for the frozen gold.
28. **Cover and the other figures.** A confidently stated wrong cover figure is `refer` only after a confirmed read-back of that figure, `incomplete` if unconfirmed, `understanding_gap` if hedged or unknown. Term and the cancellation window stay `understanding_gap`.
29. **A "took nothing" denial** is `refer` only if it stands; if the customer later names the product kind on the record it becomes `recall_not_named`.
30. **A retraction in a later clause** never yields a stated value.
31. **The loan-book sampler:** draws do not overlap, no attempt after day 30. Reviewer decision labels are neutral and carry no intervals.
32. **Models and process:** Fable only orchestrates, Opus medium builds, a separate Opus high verifies on fresh inputs, Sonnet researches and documents.
33. **Human-call material** lives in `.samajh-human/` (gitignored) and never enters the repo or the demo.
34. **Open: the order of the two readings** on figure turns (v2.5 first per P2's contract and the iteration 1 verifier's H4; v3.0 first in the server). Decide when P1 is re-verified.
35. **Open for the next judge: a risk question.** 85Y speaks of features and risks; the call's only risk-related question is the money-back one.
36. **Open for the user: does "teen lakh chalis" mean 3,40,000 or 3,00,040?** It decides whether 14 of the 40 held-out failures count (§9 E3).
