# Samajh — design v1 (working name)

> A post-sale understanding callback for Indian lenders. The customer explains in their own words, in their own language, what they bought with their loan. Plain code compares that against the bank's records, and every mismatch becomes a flag a human can act on.

Status: **v1 design, 2026-11-10.** How we chose this idea: `IDEAS-HILLCLIMB.md` (5 rounds, final score 84/100). Amounts pilot: `references/pilots/amounts-pilot-2026-11-10.md`. Items marked **[verify]** are not yet confirmed against the primary PDF.

---

## 1. The problem

A borrower asks for a ₹5 lakh loan, receives ₹4.48 lakh, and is told the ₹52,000 difference is "an FD for loan security". It is actually a life-insurance premium. Months later they find out, complain, and an Ombudsman orders a refund. That is a real case (Insurance Ombudsman, BHP-L-021-1617-0529), and there are many like it.

Lenders already make confirmation calls, but they ask yes/no questions ("Did you take a policy?" "Haan."). In several Ombudsman awards the insurer played the customer's recorded "yes" and **still lost**, because the customer had been misled:
- BNG-L-041-1617-0797: a banker promised the money could be withdrawn after a year.
- BNG-L-014-1617-0598: the customer was promised a one-time premium and got a 15-year policy with 7 years of payments.
- AHD-L-001-1617-0203: the customer was told to "answer everything in positive".

A "yes" doesn't show that the customer understood.

## 2. The rule that makes this timely

RBI's Responsible Business Conduct (Second Amendment) Directions 2026 take effect on **1 Jan 2027**. Commercial banks: RBI/2026-27/115, para 85Y. NBFCs: RBI/2026-27/123, para 101Y. Every other RBI-regulated lender gets an equivalent paragraph, and HFCs inherit it via para 157A **[verify circular numbers against PDFs]**.

> "85Y. A bank shall establish a mechanism to seek feedback from customers, within a period of 30 days from the sale of any financial product / service to ensure that customers have understood the features of the financial product / service and also the risks associated with such financial product / service. The mechanism may include selection of the customers on a random basis for such feedback through modes such as call-backs or surveys carried out by a department / vertical of the bank not associated with sale of products / services. A half-yearly report on the findings of the feedback shall be prepared and utilised for review of existing policies and features of financial products / services."

Samajh is that mechanism. On top of it we add checks against the related paragraphs of the same directions. 85Y doesn't require these checks, but the evidence falls out of the same call:

| Para | What it says | What we check |
|---|---|---|
| 85G | Explicit consent for each product, recorded | Is there a consent record for each product? |
| 85V | No compulsory bundling of third-party products | Did the customer believe the product was required for the loan? |
| 85W | No paying for a product out of the loan without explicit consent | Was the premium deducted from the loan, and did the customer know? |
| 4(20A)(ii) | Mis-selling includes incorrect, incomplete or misleading information | Does what the customer believes contradict the product's features? |
| 85Z | Mis-selling → full refund + compensation | We prepare the refund case for human review |

## 3. Users

- **Primary:** the department of a bank or NBFC that doesn't sell products and runs the 85Y feedback mechanism (customer experience, compliance or audit).
- **Secondary:** the compliance head who signs the half-yearly report; voice-agent vendors (Gnani included) who sell to these lenders.

## 4. v1 scope

**In v1**
- One product family: a loan (personal or gold) sold with credit-life / loan-protection insurance.
- Languages: Hindi, Hinglish, Tamil and Kannada. A language counts as **supported** only with a fluent reviewer for its scripts and scenarios, plus ≥10 improvised real-voice calls. Any language below that bar is reported as "TTS-only, not human-tested".
- One outbound call flow, made from a simulated phone in the browser.
- Checks: 85Y understanding, 85G, 85V, 85W, 4(20A)(ii).
- Outputs: a flagged case with evidence, a draft refund case, and a half-yearly summary view.
- The headline experiment: teach-back vs yes/no on the same scenarios.

**Not in v1**
- Real telephony and real bank integrations (all records and calls are synthetic).
- Mutual funds, credit-card add-ons and other products (they're headroom, and the same engine).
- Analysing the original sales call.
- Deciding whether something *is* mis-selling: we only flag cases for human review.
- Live streaming STT (we use REST per turn; see §8).

## 5. The call

```
disclosure → identity check → open recall → teach-back per product → consent check → read-back → close
```

1. **Disclosure.** An automated call from the bank's customer-care team (not sales), recorded, about the loan taken on a given date. The bot says it is an AI, and the customer can ask for a human at any time.
2. **Identity check.** Synthetic: last 4 digits of the loan account, plus the date of birth.
3. **Open recall (the key question).** *"Loan ke saath aapne kya-kya liya, aur kitne ka?"* This is asked before we mention any product, so we don't lead the answer.
4. **Teach-back for each product on record.** "Is this insurance, FD or something else?"; "How much did it cost?"; "How was it paid — from the loan amount, or separately?"; "Was it required for the loan?"; "What does it cover, and for how long?"; "Do you know you can cancel it within N days?"
5. **Consent check.** "Our records show you agreed on <date> — is that right?" This only checks existing consent; the call never *captures* it.
6. **Read-back.** Every critical amount is read back ("bavan hazaar, yaani 52,000 — sahi hai?"). The pilot showed why: on the phone line, Prisma dropped "paune" from "paune do lakh".
7. **Close.** "Thank you." If anything was flagged: "Someone from our team will call you within N days."

Unclear answers are asked once more in simpler words, then marked `unclear → human`. The bot never argues with the customer and never explains the product during the call. That would contaminate the test, and explaining belongs to a human follow-up.

## 6. How it works

```
LOAN RECORD (synthetic)  ──►  SCRIPT BUILDER  ──►  bot prompts (Timbre, pre-generated, 8 kHz)
                                                        │
                       customer audio (each turn) ◄─────┘
                                │
                     PRISMA REST (v3.0 transcribe; v2.5 for comparison)
                                │
                     AMOUNT NORMALISER (fraction-aware; pilot-proven)
                                │
                     EXTRACTOR (LLM → strict schema, with a quoted span for each field)
                                │
                     RULE ENGINE (pure functions: answer vs record → flags + clause)
                                │
              ┌─────────────────┴──────────────────┐
        PRISMA BATCH on the full call          CASE + EVIDENCE LOG
        (segment timestamps, speakers)  ───►   (quotes with timestamps, clause, verdict)
                                                     │
                                        REFUND CASE DRAFT (85Z) · HALF-YEARLY VIEW (85Y)
```

**Core types (sketch)**
```python
Product   = {id, kind: "credit_life"|..., provider, premium_inr, cover_inr, term_months,
             paid_from_loan: bool, required_for_loan: bool, cancel_window_days,
             consent: {method, at} | None}
LoanRecord = {loan_id, borrower (synthetic), sanctioned_inr, disbursed_inr, products: [Product]}
Answer     = {field, value, quote, turn_id}          # from the extractor; value=None if not said
Flag       = {product_id, rule: "85Y.kind"|"85Y.premium"|"85G"|"85V"|"85W"|"4(20A)(ii)",
              expected, heard, quote, ts, severity}
Verdict    = "clear" | "flag_for_review" | "unclear_needs_human"   # per product
```

**Rules.** These are deterministic and never call the LLM:
- `85Y.kind`: the customer's stated kind ≠ the record (e.g. "FD" vs credit_life) → flag.
- `85Y.premium`: |heard − record| > 1% (after normalising) → flag; not stated → `unclear`.
- `85Y.cover/term/cancel`: unaware or wrong → flag (lower severity).
- `85G`: `consent is None` → flag (the record alone is enough; the call adds the customer's words).
- `85W`: `paid_from_loan` and (no consent or the customer says it was paid separately / didn't know) → flag.
- `85V`: the customer says it was required for the loan, or the record has `required_for_loan` → flag for review (a voluntary or free bundle is allowed under 85V).
- `4(20A)(ii)`: belief contradicts features (refundable / guaranteed return / FD) → flag.
- Any product with a flag → `flag_for_review` plus a draft refund case. The bot never says "mis-selling".

**Amounts.** We use `format=transcribe`, then a fraction-aware parser (sawa / saadhe / paune / dedh / dhai; Tamil and Kannada 1.5 and 2.5). In the pilot it fixed every case where Prisma's digit conversion (ITN) went wrong. A full word-to-number parser is only needed if we use `indic-auto`. Read-back covers real recognition misses.

## 7. Gnani models used

| Model | Use |
|---|---|
| **Prisma STT v3.0** (`/stt/v3`, `format=transcribe`, language set per call) | Each customer turn (REST, ≤30 s) |
| **Prisma STT v2.5** | The same turns, for the comparison reported in results |
| **Prisma Batch** | Full-call transcript with segment timestamps and speaker labels, used for the evidence log |
| **Timbre TTS v3.0** (8 kHz, `hi-IN` / `hi-en` / `ta-IN` / `kn-IN`) | Bot prompts and read-backs (pre-generated from records) and synthetic customer voices for testing |
| Voice cloning | **Not used.** Nothing here needs it, and cloning a bank officer's voice would be misleading |
| LLM (any; e.g. Claude) | Extraction only: strict schema, quoted spans, no arithmetic, no verdicts |

## 8. Engineering constraints

- **Concurrency 1** (429 "Only 1 active request"): one queue for all requests, exponential backoff, no parallel calls. Bot audio is pre-generated, so a live call only uses STT.
- **Caching:** key = sha256(model, params, audio/text). Noise and 8 kHz variants are made offline, and only STT is re-run per condition.
- **Measured cost** (pilot): ~0.02 credits per STT call, ~0.06 per TTS call. The full plan with 4 languages (~1,350 TTS + ~7,400 STT) ≈ **240 credits (<5% of 5,000)**.
- **Latency** (pilot): STT median 0.3 s, TTS 0.8 s. Pre-generated prompts keep the bot responsive.
- **Backend proxy** (FastAPI): browsers can't set `X-API-Key-ID`. The key lives in an environment variable only.
- **Synthetic data only:** obviously fake names, loan IDs and numbers. Ombudsman cases are re-created with invented parties, never quoted with real names.

## 9. Evaluation

| # | Question | Metric | Data |
|---|---|---|---|
| E1 | **Does teach-back catch what yes/no misses?** (headline) | Misled customers caught: teach-back vs yes/no on the same scenarios; **false-clear rate** (misled customer passes, the dangerous error) | All scenarios, both call styles |
| E2 | Are the flags right? | Per-clause precision / recall; false flags on compliant scenarios | 96 scenarios: 4 clauses × 6 (3 violating, 3 compliant or near-miss) × 4 languages |
| E3 | Are amounts heard correctly? | Exact match, naive vs normaliser vs normaliser + read-back; v2.5 vs v3.0 | Pilot items + every amount in E2 |
| E4 | Does it hold on real voices? | E1–E3 on human speech, per language | ≥10 improvised calls per supported language (teammates or consenting friends, from a brief card, not a script) |
| E5 | Does it survive phone audio? | E2/E3 by condition: clean, 8 kHz μ-law, 8 kHz + noise at 10 / 5 dB | Same audio, transformed offline |

**Gold standard and circularity.** Scenarios are templated on public Ombudsman awards (§1, plus BNG-L-033-1617-0600 for bundling, AHD-L-021-1617-0367 for an undisclosed health declaration, and the Baramulla consumer commission v J&K Bank 2026 case). Gold verdicts are written first and **frozen with a hash before any audio is made**. TTS results and human results are reported separately, and failure cases are published.

## 10. Demo (60 s)

1. The loan record: ₹5,00,000 gold loan, ₹52,000 deducted, no consent record.
2. **Yes/no call:** "Kya aapne policy li hai?" "Haan." → green PASS.
3. **Samajh call:** "Loan ke saath aapne kya-kya liya?" "Bas ek FD, loan security ke liye, bavan hazaar." → red: thinks it's an FD (4(20A)(ii)), paid from the loan without consent (85W), no consent record (85G). The quote is timestamped at 00:41 and a refund case is drafted.
4. Cut to the result: "Teach-back caught X of Y misled customers; yes/no caught Z", plus the amounts finding.
5. Close on the Ombudsman awards where the recorded "yes" still lost.

**Award target:** Real Deal (backup: Demo Day Drop).

## 11. What we can and can't claim

**We can say:** quote 85Y verbatim; it applies to every RBI-regulated lender from 1 Jan 2027; "we found no vendor marketing an 85Y understanding callback (searched Nov 2026)"; Ombudsman awards show yes/no calls failed misled customers; the consent and bundling checks are our added layer; only measured numbers, each with n and audio source; "flags for human review".

**We can't say:** "RBI requires voice calls" (an SMS survey is allowed); "85Y requires consent/bundling checks"; "captures consent" or "prevents mis-selling"; "this is mis-selling"; any mis-selling prevalence rate; "PIVC is mandatory"; Indian SMS-vs-voice response rates (the only data is from Nigeria); TTS accuracy presented as real-world accuracy; "production-ready"; "nobody does this".

## 12. Why nobody has built this (our honest read)

1. **The rule is new.** It was issued in June 2026 and takes effect in January 2027.
2. **The cheap way is legal.** An SMS survey satisfies 85Y, so the default is a checkbox.
3. **Voice AI in India is built for revenue** (sales, collections). This product surfaces refunds, so nobody is pushing it.
4. **It's harder than it looks.** It needs product records, deterministic comparison, and correct Indian amounts. Off-the-shelf speech recognition mangles fractions (pilot).

Unknowns: banks may build it in-house or adapt survey bots; we found no data on how common loan-bundled insurance is.

## 13. Risks

| Risk | Mitigation |
|---|---|
| "SMS is enough, why voice?" | E1 answers it with our own data; the Ombudsman awards show yes/no calls failing |
| Circularity (we write both the records and the answers) | Scenarios templated on awards; gold frozen with a hash; ≥20 improvised human calls; TTS and human results reported separately |
| Tamil/Kannada amounts and phone-line misses | Fraction-aware normaliser, read-back, v2.5 vs v3.0 reported |
| Unclear whether an open streaming session counts as the one active request | v1 uses REST per turn; test streaming separately later |
| Regulatory wording drifts or the citation numbers are wrong | Verify circular numbers against the PDFs before submission; quote text, not summaries |

## 14. Milestones (3 weeks; a 2-week cut drops the SNR-5 condition and reports any language without enough human audio as TTS-only)

- **Week 1, text path:** record generator; 96 scenarios with gold frozen (each language pack reviewed by a fluent speaker); amount normaliser (unit tests from the pilot); rule engine passes 100% of gold on perfect transcripts; Gnani client (queue, backoff, cache, ledger).
- **Week 2, voice path:** call state machine; browser phone with FastAPI proxy; pre-generated prompts; one full Hindi call end to end; voiced eval set; first metrics table.
- **Week 3, results and polish:** Hinglish, Tamil and Kannada calls end to end; evidence log, refund case and half-yearly view; E1–E5 report with failures; 60 s video; written submission.

## 15. Open decisions

1. Who reviews and records for each language (Tamil and Kannada each need a fluent reviewer and ≥10 real-voice calls to count as supported).
2. LLM for extraction.
3. Final name.
4. Whether to add the second product family (MF or card add-on) as a stretch goal or leave it as a headroom slide.
