# Samajh — design v2 (working name)

> A post-sale understanding callback for Indian lenders: a teach-back-style comprehension check. The customer explains in their own words, in their own language, what they bought with their loan. Plain code compares that against the bank's records, and every mismatch becomes a flag a human can act on.

Status: **v2 design, 2026-11-10.** v2 applies the claims check in `references/claims/` (`design-corrections.md` for the edits, `claims-ledger.md` for the sources; ledger row ids such as A16 appear in brackets below). How we chose this idea: `IDEAS-HILLCLIMB.md` (5 rounds, final score 84/100). Amounts pilot: `references/pilots/amounts-pilot-2026-11-10.md`. Where the text says "our reading" or "our choice", the conclusion is ours and no regulator or court has ruled on it.

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

## 4. v1 scope

**In v1**
- One product family: a loan (personal or gold) sold with credit-life / loan-protection insurance.
- Languages: Hindi, Hinglish, Tamil and Kannada. A language counts as **supported** only with a fluent reviewer for its scripts and scenarios, plus ≥10 improvised real-voice calls. That bar is the target. **Today no human voice recordings exist, so every language is "TTS-only, not human-tested", and the Tamil and Kannada text is "not human-reviewed".** Regional languages are our choice: 85R covers documents for the bank's own products and defers to the product regulator for third-party products, so it does not ground the language choice for insurance (A25).
- One outbound call flow, made from a simulated phone in the browser.
- Checks: 85Y understanding, 85G, 85V, 85W, and belief mismatch (which may engage 4(20A)(ii)).
- Outputs: a flagged case with evidence, an evidence pack for review, and a half-yearly summary view.
- The headline experiment: teach-back-style open questions vs yes/no on the same scenarios.

**Not in v1**
- Real telephony and real bank integrations (all records and calls are synthetic). The number series and telecom declarations in §5 describe a real deployment; the demo does not exercise them.
- Mutual funds, credit-card add-ons and other products (they're headroom, and the same engine).
- Analysing the original sales call.
- Deciding whether something *is* mis-selling: we only flag cases for human review.
- Testing whether the product was suitable or appropriate for the customer (4(20A)(i)).
- Re-teaching: Samajh assesses understanding and does not explain the product.
- Live streaming STT (we use REST per turn; see §8).

## 5. The call

```
right-party check → disclosure → second check → context → open recall
  → teach-back-style questions per product → consent check → read-back → close
```

1. **Right-party check.** "Am I speaking with <first name>?" If not, the bot ends the call and says nothing about a loan.
2. **Disclosure.** The bank's name and "customer-care team". This is not a sales call and nothing will be offered. The caller is an automated AI assistant. The call is for feedback, it is recorded to keep an accurate record of that feedback, and the bank's written notice explains how the data is used. The customer can decline, stop at any time, or ask for a human. The customer can hang up and call the customer-care number on the loan papers to check the call is genuine. The bot will never ask for an OTP, PIN, password or account number.
3. **Second check, no secret.** One low-sensitivity fact, for example the year of birth (synthetic in the demo). The bot never asks for account digits.
4. **Context.** Only now does the bot mention the loan.
5. **Open recall (the key question).** *"Loan ke saath aapne kya-kya liya, aur kitne ka?"* This is asked before we mention any product, so we don't lead the answer.
6. **Teach-back-style questions for each product on record.** "Is this insurance, FD or something else?"; "How much did it cost?"; "How was it paid — from the loan amount, or separately?"; "Was it required for the loan?"; "Were you told you could buy this cover from another company?"; "What does it cover, and for how long?"; "Were you told whether you can cancel this cover, and by when?" The bot compares the cancel answer with `cancel_window_days` on the record and never states a right itself.
7. **Consent check.** "When you took the loan, what did you agree to buy, and how did you agree?" The bot compares the answer with the consent record. The call never *captures* consent.
8. **Read-back.** Every critical amount is read back ("bavan hazaar, yaani 52,000 — sahi hai?"). The pilot showed why: in one pilot sentence (n = 1, TTS voice, simulated 8 kHz phone audio), Prisma v3.0 returned 2,00,000 for "paune do lakh".
9. **Close.** "Thank you." If anything was flagged: "Someone from our team will call you within N days", with N set by the bank. It is a promise the bank must keep. The close mentions no other product.

Unclear answers are asked once more in simpler words, then marked `unclear → human`. One re-ask and no more also avoids the "nagging" pattern in RBI's dark-pattern annex (A20). The bot never argues with the customer and never explains the product during the call. That would contaminate the test, and explaining belongs to a human follow-up. Where the bot names the insurer it uses the name on the record and adds nothing, because 85J bars a bank from presenting a third-party product as its own (A24). The call carries no sales content of any kind.

**Why the opening changed from design v1.** Design v1 asked for the last 4 digits of the loan account and the date of birth, and named the loan before confirming who had answered. RBI's public advice says: "Never share your account details such as account number, login ID, password, PIN, UPI-PIN, OTP, ATM / Debit card / credit card details with anyone, not even with bank officials, however genuine they might sound." That is public-awareness text, not a direction to lenders, and it does not name loan-account digits or a date of birth. An unknown caller asking for them still looks like the pattern it describes, and a customer who refuses is behaving sensibly (E5.2, E5.3). Naming the loan first would disclose it to whoever answers. Not doing so is good practice by analogy with the privacy rules RBI sets for other kinds of call (85N(6), the 2026 recovery amendment). We found no RBI text that prescribes how to authenticate a customer on an outbound call (E5.1). A first-name "yes" alone is a weak check, which is why step 3 exists.

**What grounds the opening.**
- The call is made from the lender's 1600-series number. Required for service and transactional calls: TRAI direction of 19 November 2025 para 8(iii); RBI/2024-25/105. No TRAI text classifies a feedback call. We treat it as a service call.
- The call carries no promotional content. Under the TCCCPR, promotional content makes it a promotional call, which needs the 140 series and consent.
- The lender tells its telecom provider in advance that it uses automated calls. Required now: TCCCPR regulation 4 as substituted in February 2025. The Third Amendment of 18 September 2026 widens this to a declaration of all application-to-person calls, and treats undeclared calls as unsolicited commercial communication, from 60 days after gazette publication.
- The AI line and the offer of a human. Recommended by RBI's FREE-AI committee report (para 4.4.54, read in a mirror copy). We found no law that requires them.
- The recording line. Our choice. The only RBI recording duty we found is for recovery calls.
- The purpose, the right to decline, and a pointer to a written notice. Required by the DPDP Act sections 5 and 6 from 13 May 2027 where the lender relies on consent.
- Calls are placed between 10:00 and 19:00. Our choice. We found no RBI or TRAI hour limit that applies in terms to a feedback call. 85N(4) sets 09:00 to 19:00 for sales staff and the card rules set 10:00 to 19:00.

## 6. How it works

```
LOAN RECORD (synthetic)  ──►  SCRIPT BUILDER  ──►  bot prompts (Timbre, pre-generated, 8 kHz)
                                                        │
                       customer audio (each turn) ◄─────┘
                                │
                     PRISMA REST (v3.0 transcribe; v2.5 for comparison)
                                │
                     AMOUNT NORMALISER (fraction-aware; tested in-sample)
                                │
                     EXTRACTOR (LLM via OpenRouter → strict schema, with a quoted span for each field)
                                │
                     RULE ENGINE (pure functions: answer vs record → flags + paragraph)
                                │
              ┌─────────────────┴──────────────────┐
        PRISMA BATCH on the full call          CASE + EVIDENCE LOG
        (segment timestamps, speakers)  ───►   (quotes with timestamps, paragraph, verdict)
                                                     │
                        EVIDENCE PACK (for the bank's 85Z review) · HALF-YEARLY VIEW (85Y)
```

**Core types (sketch)**
```python
Product   = {id, kind: "credit_life"|..., provider, premium_inr, cover_inr, term_months,
             paid_from_loan: bool, required_for_loan: bool, risk_mitigant: bool,
             provider_choice_offered: bool, cancel_window_days: int | None,
             consent: {method, at} | None}
LoanRecord = {loan_id, lender_type: "bank"|"nbfc", borrower (synthetic),
              sanctioned_inr, disbursed_inr, products: [Product]}
Answer     = {field, value, quote, turn_id}          # from the extractor; value=None if not said
Flag       = {product_id, rule: "kind"|"premium"|"cover"|"term"|"cancel_window"|
                                "consent"|"bundling"|"loan_funded"|"belief_mismatch",
              clause, expected, heard, quote, ts, severity}   # clause = CLAUSES[lender_type][rule]
Verdict    = "clear" | "flag_for_review" | "unclear_needs_human"   # per product

CLAUSES = {   # the paragraph a rule may engage, by lender type (A5, A19)
  "bank": {kind|premium|cover|term|cancel_window: "85Y",  consent: "85G",  bundling: "85V",
           loan_funded: "85W",  belief_mismatch: "4(20A)(ii)"},
  "nbfc": {kind|premium|cover|term|cancel_window: "101Y", consent: "101G", bundling: "101V",
           loan_funded: "101W", belief_mismatch: "6(9A)(ii)"},
}
```
Rule ids are neutral and the paragraph is looked up by lender type. Housing finance companies follow the NBFC paragraphs through para 157A. Other lender types change only the numeric prefix and are not mapped in v1.

**Rules.** These are deterministic and never call the LLM. The paragraph in brackets is the commercial-bank one:
- `kind` (85Y): the customer's stated kind ≠ the record (e.g. "FD" vs credit_life) → flag.
- `premium` (85Y): |heard − record| > 1% (after normalising) → flag; not stated → `unclear`.
- `cover` / `term` / `cancel_window` (85Y): unaware or wrong → flag (lower severity). The cancel answer is compared with `cancel_window_days` on the record.
- `consent` (85G): `consent is None` → flag (the record alone is enough; the call adds the customer's words). A consent record that the customer does not recognise → flag for review. A record on file does not clear 85G by itself.
- `loan_funded` (85W): `paid_from_loan` and (no consent or the customer says it was paid separately / didn't know) → flag.
- `bundling` (85V): the product was required for the loan (per the record or the customer) **and** either it is not a risk mitigant, or the customer was not offered a choice of provider (per the record or the customer) → flag for review. Required as a risk mitigant with a choice of provider, voluntary, or free of cost → no flag.
- `belief_mismatch` (may engage 4(20A)(ii)): belief contradicts features (refundable / guaranteed return / FD) → flag. The paragraph is the definition of mis-selling, so it is shown as the paragraph the flag may engage and never as a verdict.
- Any product with a flag → `flag_for_review`. A flag on `kind`, `premium`, `consent`, `bundling` or `loan_funded` also produces an evidence pack: the record, the customer's words with timestamps, and the paragraph engaged. The bot never says "mis-selling".

**Why an evidence pack and not a refund case.** The 85Z refund duty arises "in cases where mis-selling of a financial product / service is established". The text does not say who establishes it or whether a complaint is needed, sets no refund deadline, and leaves compensation to the bank's "approved policy". A flag is not established mis-selling (A18).

**Amounts.** We use `format=transcribe`, then a fraction-aware parser (sawa / saadhe / paune / dedh / dhai; Tamil and Kannada 1.5 and 2.5). On the 20-sentence pilot (one TTS voice) it corrected all 8 transcripts where Prisma's digits ignored the fraction word. It was written after seeing those results and has no held-out test yet. A full word-to-number parser is only needed if we use `indic-auto`. Read-back covers real recognition misses.

## 7. Gnani models used

| Model | Use |
|---|---|
| **Prisma STT v3.0** (`/stt/v3`, `format=transcribe`, language set per call) | Each customer turn (REST, ≤30 s) |
| **Prisma STT v2.5** | The same turns, for the comparison reported in results |
| **Prisma Batch** | Full-call transcript with segment timestamps and speaker labels, used for the evidence log |
| **Timbre TTS v3.0** (8 kHz, `hi-IN` / `hi-en` / `ta-IN` / `kn-IN`) | Bot prompts and read-backs (pre-generated from records) and synthetic customer voices for testing |
| Voice cloning | **Not used.** Nothing here needs it, cloning a bank officer's voice would be misleading, and voice patterns used for authentication are biometric data under the SPDI Rules 2011 (read in a mirror copy). No voiceprints either |
| LLM (reached through OpenRouter; a cheap model by default) | Extraction only: strict schema, quoted spans, no arithmetic, no verdicts |

## 8. Engineering constraints

- **Concurrency 1** (429 "Only 1 active request", seen in a burst test on 2026-11-10): one queue for all requests, exponential backoff, no parallel calls. Bot audio is pre-generated, so a live call only uses STT.
- **Caching:** key = sha256(model, params, audio/text). Noise and 8 kHz variants are made offline, and only STT is re-run per condition.
- **Measured cost** (pilot): about 0.02 credits per 3-second STT call (n = 78) and 0.06 per short TTS sentence (n = 20), from one dashboard reading with no saved screenshot. The four-language plan (~1,350 TTS + ~7,400 STT) is about 230 to 265 credits, which is about a quarter of the 1,000-credit project cap.
- **Latency:** STT about 0.2 to 0.3 s and TTS about 0.6 to 0.8 s on short clips (pilot and client probe). Pre-generated prompts keep the bot responsive.
- **Backend proxy** (FastAPI): browsers can't set `X-API-Key-ID`. The Gnani and OpenRouter keys live in environment variables only.
- **LLM hosting:** v1 sends only synthetic transcripts to OpenRouter. A real lender must check where transcripts may go first: for digital lenders, the Digital Lending Directions require storage in India and deletion within 24 hours of processing abroad (E2.9).
- **Synthetic data only:** obviously fake names, loan IDs, years of birth and numbers. Ombudsman cases are re-created with invented parties, never quoted with real names.

## 9. Evaluation

| # | Question | Metric | Data |
|---|---|---|---|
| E1 | **Does a teach-back-style open question catch what yes/no misses?** (headline) | Misled customers caught: open questions vs yes/no on the same scenarios; **false-clear rate** (misled customer passes, the dangerous error) | All scenarios, both call styles |
| E2 | Are the flags right? | Per-clause precision / recall; false flags on compliant scenarios | 96 scenarios: 4 clauses × 6 (3 violating, 3 compliant or near-miss) × 4 languages |
| E3 | Are amounts heard correctly? | Exact match, naive vs normaliser vs normaliser + read-back; v2.5 vs v3.0 | Pilot items + every amount in E2 |
| E4 | Does it hold on real voices? | E1–E3 on human speech, per language | Target: ≥10 improvised calls per supported language (teammates or consenting friends, from a brief card, not a script). **None recorded yet** |
| E5 | Does it survive phone audio? | E2/E3 by condition: clean, 8 kHz μ-law, 8 kHz + noise at 10 / 5 dB | Same audio, transformed offline |

**What teach-back is, and what we don't claim for it.** Teach-back means asking a person to explain in their own words what they were told. It is well studied in healthcare. Reviews report benefits, but the newest systematic review (2026) found no clear pattern of effect on knowledge. We found no study of teach-back for loan or insurance sales, and none by an automated voice. E1 is our own test of it. Most of this rests on abstracts, not full papers (C3).

**Gold standard and circularity.** Scenarios are templated on public Ombudsman awards (the customer-relief awards in §1, plus BNG-L-033-1617-0600 where the customer paid for a policy "as a requirement of a security deposit for the overdraft facility", BHP-L-013-1617-0436 where the complainant said he was asked to deposit ₹1 lakh "as an Fixed Deposit to get the housing loan", and Baramulla consumer commission CC 33/2025 v J&K Bank where ₹2,00,000 was debited for a policy without consent; our copy of that order is a scan hosted by a news site). Compliant scenarios are written synthetically from the rules: a required risk mitigant with a choice of provider, a voluntary add-on with a consent the customer recognises, a premium paid separately. Awards the insurer won are not used as compliant gold, because the complaint failed on evidence or delay and a teach-back-style call to those customers should still flag. Gold verdicts are written first and **frozen with a hash before any audio is made**. TTS results and human results are reported separately, and failure cases are published. Until human calls exist, every result is labelled TTS-only.

Each scenario records the remedy in its source award. Relief varied: of the 22 awards we read that gave the customer relief, about two-thirds ordered a refund and about one-third a conversion to a single-premium policy.

## 10. Demo (60 s)

1. The loan record (synthetic; the figures are ours, not from any award): ₹5,00,000 gold loan, ₹52,000 deducted, product on record credit-life, no consent record.
2. **Yes/no call:** "Kya aapne policy li hai?" "Haan." → the yes/no script shows PASS.
3. **Samajh call:** the bot confirms the first name, says it is an automated AI assistant from customer care and not sales, takes the year of birth, and only then mentions the loan. Then: "Loan ke saath aapne kya-kya liya?" "Bas ek FD, loan security ke liye, bavan hazaar." → FLAG FOR REVIEW: the customer describes the product as an FD and the record says credit-life (possible incorrect information, 4(20A)(ii)); the premium was funded from the loan and the record holds no consent (85W, 85G). The quote is timestamped at 00:41 and an evidence pack is prepared for the reviewer.
4. Cut to the result: "Open questions flagged X of Y misled-customer scenarios; yes/no flagged Z" with n and "synthetic scenarios, TTS voices" on screen, plus the amounts finding with its n.
5. Close on the Ombudsman's own words: "The PIVC recording is clear about the terms and conditions of the policy but the maturity benefit is not explained."

**Award target:** Real Deal (backup: Demo Day Drop).

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
- TTS accuracy presented as real-world accuracy. Today every number we have is TTS-only.
- "Supported" for any language before it meets the bar in §4.
- "Production-ready."
- "Nobody does this."

## 12. Why we think this is not yet common (our read)

1. **The rule is new.** It was issued on 15 June 2026 and takes effect on 1 January 2027.
2. **A low-cost survey is not excluded.** 85Y names surveys as an example and sets no channel, so a low-cost survey is not excluded by the text. A low-cost survey is the likely default. That is our inference. We found no bank or industry statement on how banks will comply.
3. **Most voice-AI vendors lead with support, sales and collections.** Of 11 vendor sites checked on 10 November 2026, 10 list support, 9 sales and 8 collections. Seven also sell audit or compliance products, and some market adjacent post-sale checks (§11). None of those pages cites 85Y.
4. **It's harder than it looks (our view).** It needs product records, deterministic comparison, and correct Indian amounts. In our 20-sentence TTS pilot (one voice), Prisma's digit output ignored the fraction word in 8 transcripts across 5 sentences.

What Samajh adds to the adjacent products: an open question before any product is named, a deterministic comparison with the lender's record, an evidence log, and a measured evaluation.

Unknowns: banks may build it in-house or adapt survey bots, and we found no public statement from any bank on how it will run 85Y feedback. No regulator or survey we found reports how many loans carry bundled insurance. The numbers that exist count complaints.

## 13. Risks

| Risk | Mitigation |
|---|---|
| "SMS is enough, why voice?" | E1 compares teach-back with a yes/no confirmation. A yes/no SMS is the same question in text, so E1 bears on it, but E1 has no SMS arm and does not measure response rates |
| Circularity (we write both the records and the answers) | Scenarios templated on awards; gold frozen with a hash; ≥10 improvised human calls per supported language (none recorded yet); TTS and human results reported separately |
| No human voice recordings and no fluent Tamil/Kannada reviewer yet | Every language is reported as "TTS-only, not human-tested" and Tamil/Kannada text as "not human-reviewed" until the §4 bar is met |
| Tamil/Kannada amounts and phone-line misses | Fraction-aware normaliser, read-back, v2.5 vs v3.0 reported |
| Unclear whether an open streaming session counts as the one active request | v1 uses REST per turn; test streaming separately later |
| Judges know the adjacent vendors (SquadStack, Edesy, Ringg, NuSummit) | Name them ourselves and say what Samajh adds (§12) |
| Regulatory wording drifts | Recheck RBI's notifications for amendments dated after 6 August 2026 before submission; quote text, not summaries |
| Four documents were read in copies the issuer does not host (FREE-AI report, SPDI Rules 2011, IRDAI circular 274/11/2020, Baramulla order) | Check each against the official copy before quoting it to judges |

## 14. Milestones (3 weeks; a 2-week cut drops the SNR-5 condition and reports any language without enough human audio as TTS-only)

- **Week 1, text path:** record generator; 96 scenarios with gold frozen (target: each language pack reviewed by a fluent speaker; Tamil and Kannada are not human-reviewed today); amount normaliser (unit tests from the pilot); rule engine passes 100% of gold on perfect transcripts; Gnani client (queue, backoff, cache, ledger) and OpenRouter client.
- **Week 2, voice path:** call state machine for the §5 flow; browser phone with FastAPI proxy; pre-generated prompts; one full Hindi call end to end; voiced eval set; first metrics table.
- **Week 3, results and polish:** Hinglish, Tamil and Kannada calls end to end; evidence log, evidence pack and half-yearly view; E1–E5 report with failures; 60 s video; written submission.

## 15. Open decisions

1. Who reviews and records for each language (each language needs a fluent reviewer and ≥10 real-voice calls to count as supported). Today there are no human recordings and no Tamil or Kannada reviewer.
2. ~~LLM for extraction.~~ Closed in design v2: OpenRouter, with a cheap model by default (§7).
3. Final name.
4. Whether to add the second product family (MF or card add-on) as a stretch goal or leave it as a headroom slide. The claims check adds a second headroom candidate: the lender's own products (rate, EMI, tenure, charges), on our reading of 85Y with 85A.

From the claims check. These are judgement calls, so design v2 does not adopt them:

5. **A Key Facts Statement check** (`in_kfs` on `Product`; flag a premium absent from the KFS). The rule is in force today (para 348 for banks, para 29 for NBFCs), but it covers term loans and a bullet-repayment gold loan may not be one.
6. **Call timing.** Place the call in the first one to two weeks after the sale and log the day of the call relative to the sale. The 85Z fallback complaint window runs 30 days from receipt of the signed terms and the individual free-look period 30 days from receipt of the policy, so a day-28 flag leaves the customer little time.
7. **A fuller evidence log** (number called, caller number, time, full audio with a hash, every bot prompt). In about a third of the customer-relief awards we read, the Forum relied on the insurer not producing the sales-stage recording.
8. **A "told how to answer" scenario group.** Four awards record coaching before the verification call; adding the group changes the 96-scenario matrix.
9. **A text-confirmation arm in E1.** Without one we keep the narrower claim in §13 about SMS.
10. **The dark-pattern quote on a slide** (Annex IIA, "loan protection insurance by default"). It is a related pattern, not the hero case.
11. **A retention setting.** RBI fixes one year after contract end for consent records and nothing for feedback audio; the DPDP Rules set a one-year floor for logs from 13 May 2027.
