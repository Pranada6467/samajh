# Corrections to DESIGN.md

This file lists the edits `DESIGN.md` needs after the claims check of 2026-11-10, most important first, and then the product changes the verified rules suggest. Each item names the ledger rows that support it (`claims-ledger.md`). Line numbers refer to `DESIGN.md` as it stood on 2026-11-10. An independent reviewer tried to refute the first version of this file, and the changes it proved are applied here.

Where an item says "our reading", the source text is quoted and the conclusion is ours. No regulator or court has ruled on it.

## What held up

- The 85Y quote in section 2 matches RBI's text character for character (A9).
- The circular numbers, paragraph numbers and dates are right: RBI/2026-27/115 para 85Y for commercial banks, RBI/2026-27/123 para 101Y for NBFCs, HFCs through para 157A, issued 15 June 2026, in effect from 1 January 2027 (A2 to A5, A7). The two **[verify]** tags in sections 2 and 13 can go. The live RBI pages matched the saved copies on 2026-11-10.
- The six cited Ombudsman case numbers exist in the Council for Insurance Ombudsmen compendium, and the Baramulla order was retrieved. What the design says about several of them is wrong (items 2 and 6).
- The ban on "PIVC is mandatory" is correct (C1.9).

## Work in progress that these corrections affect

| Work package | Change | Item | Status |
|---|---|---|---|
| W1 rule engine | The 85V rule must not flag "required for the loan" on its own. Add `provider_choice_offered` and `risk_mitigant` to `Product`. | 1 | **Applied** (W1b, 2026-11-10): both fields are required on `Product`; `checks.bundling` flags only when the product is required and is not a risk mitigant, is described as a deposit, or had no choice of provider (`references/pilots/W1-core-report.md` §4) |
| W1 rule engine | A flag produces an evidence pack, not a refund case, and only for kind, premium, 85G, 85V and 85W flags. | 7 | **Applied** (W1b, 2026-11-10): `EvidencePack` is built exactly for flags under `EVIDENCE_PACK_RULES` (kind, premium, consent, bundling, loan_funded) |
| W1 rule engine | A consent record on file must not clear 85G by itself. | 12 | **Applied** (W1b, 2026-11-10): `checks.consent` passes only when the customer's own account includes the product and names the method on record (comparing the method is W1b's own reading of item 12) |
| W4 scenarios | Drop AHD-L-021-1617-0367 as a mis-selling template. Treat AHD-L-001-1617-0203 as a complainant's account of coaching, not a "recorded yes" case. Do not use insurer-won awards as compliant gold. Gold verdicts state the real remedy. | 2, 6, 16 | |
| Iteration 2 call flow | Replace the identity check. Do not name the loan before the right person is confirmed. Ground each disclosure line. | 4, 5 | |

## Edits, most important first

### 1. The 85V check is wrong (section 2 table, section 6 rules and types)

Old (line 31): `| 85V | No compulsory bundling of third-party products | Did the customer believe the product was required for the loan? |`

New: `| 85V | No compulsory bundling of a third-party product with the bank's own. A product required as a risk mitigant is allowed if the customer may buy it from any provider | Was the product required for the loan? If so, is it a risk mitigant, and was the customer offered a choice of provider? |`

Old (line 114): "`85V`: the customer says it was required for the loan, or the record has `required_for_loan` → flag for review (a voluntary or free bundle is allowed under 85V)."

New: "`85V`: the product was required for the loan (per the record or the customer) **and** either it is not a risk mitigant, or the customer was not offered a choice of provider → flag for review. Required as a risk mitigant with a choice of provider, voluntary, or free of cost → no flag."

Old (line 99): `paid_from_loan: bool, required_for_loan: bool, cancel_window_days,`

New: `paid_from_loan: bool, required_for_loan: bool, risk_mitigant: bool, provider_choice_offered: bool, cancel_window_days: int | None,`

Add a question in section 5 step 4: "Were you told you could buy this cover from another company?"

Why: 85V says "if the sale of the bank's own product / service is contingent on purchase of a TPPS as a risk mitigant, the customer shall be provided the option to purchase the same from any TPPS Provider". The current rule would flag sales that this sentence allows. RBI does not define "risk mitigant". Treating credit-life cover on a loan as one is our reading. A savings policy described as a "security deposit" or an "FD" is not a risk mitigant on any reading, so requiring it stays a flag whatever choice of provider was offered. That keeps the section 9 templates as violations. (A16)

### 2. Section 1 misdescribes three of the four cited awards

Old (lines 11 to 18): the paragraph beginning "A borrower asks for a ₹5 lakh loan, receives ₹4.48 lakh" through "A "yes" doesn't show that the customer understood."

New:

> A gold-loan borrower complained that ₹52,000 had been deducted from his loan amount, and that the bank had described it as a "fixed deposit for loan security". It was a life-insurance policy. The Insurance Ombudsman found he had asked for cancellation within two months and ordered the insurer to cancel the policy and refund the premium (Bhopal, BHP-L-021-1617-0529).
>
> Insurers already make verification calls, and in some awards the recorded call did not save the insurer:
> - BNG-L-041-1617-0797: the insurer submitted the recording of the customer confirming the policy. The customer said the bank had assured him the money could be withdrawn after a year. The Ombudsman held the insurer responsible for its agent and ordered the policy converted.
> - PUN-L-036-1617-0228: "The PIVC recording is clear about the terms and conditions of the policy but the maturity benefit is not explained." Refund ordered.
> - PUN-L-017-1617-0684: the recording showed the caller's "main focus ... was on processing the application". Refund ordered.
>
> In four awards the complainant said they had been told how to answer the call. One was told "there would be a verification call and in reply she had to answer everything in positive" (AHD-L-001-1617-0203). In another the Ombudsman accepted that the customer "responded as was guided" (CHD-L-019-1718-1436).
>
> A recorded "yes" is weak evidence of understanding. It is not worthless. Insurers have won where the recording showed the caller stating the disputed point and the customer agreeing (PUN-L-013-1617-0583), and where the Ombudsman heard the recording and the customer had confirmed the proposal details (NOI-L-036-1819-0337). Both of those complaints were also made late.

Why:
- "asks for a ₹5 lakh loan, receives ₹4.48 lakh" is not in the award. The only amount is ₹52,000 (B1b). Keep ₹5,00,000 as the synthetic scenario figure in section 10 and do not attribute it to the award.
- The "fixed deposit" description is the complainant's account under "Brief Facts of the Case". The Forum's own finding is the two-month cancellation request (B1).
- "there are many like it" is an unquantified prevalence claim, which section 11 bans.
- "the insurer played the customer's recorded 'yes' and still lost" fails for two of the three cases listed. AHD-L-001-1617-0203 mentions no verification-call recording. It says the insurer "had not produced a voice copy of the tele conversation between the Complainant & Intermediary", which is the sales call (B4). In BNG-L-014-1617-0598 the award records only the insurer's statement about the call, and the customer was refused a refund (B3).
- NOI-L-036-1819-0337 is a case where a plain recorded confirmation won. It cuts against the thesis and belongs in the text.
- "Lenders already make confirmation calls, but they ask yes/no questions" has no source for lenders. The awards concern insurers' calls (D4.4).

### 3. Section 12 and the vendor claim break the ban on "nobody does this"

Old (line 168): "## 12. Why nobody has built this (our honest read)"

New: "## 12. Why we think this is not yet common (our read)"

Old (line 164): "we found no vendor marketing an 85Y understanding callback (searched Nov 2026)"

New: "on 10 November 2026 we found no vendor page that cites para 85Y or 101Y, or that sells a product built for RBI's 30-day post-sale feedback mechanism. We did find adjacent products: AI welcome calls that ask whether the borrower understood (SquadStack, Edesy), post-sale verification for insurers that compares the customer's understanding with the policy (Ringg), and a sales-call audit against policy documents (NuSummit)."

Old (lines 171 to 172): reasons 2 and 3.

New: see ledger rows S23 to S26. Delete "This product surfaces refunds, so nobody is pushing it."

Why: the judges come from this industry and know these vendors.
- SquadStack (21 October 2026) describes an AI call after gold-loan disbursal that "doubles as the RBI-required welcome and mis-sell check: the agent asks whether the borrower understands what they agreed to". That is the demo's product category. The same flow goes on to cross-sell, and it asks the borrower to self-report understanding.
- Edesy (10 September 2026): "The welcome call is also the best moment to catch mis-selling", with the fixed-deposit example.
- Ringg's insurance page says it can "compare the customer's understanding and declarations with the policy information, flag mismatches".
- Gnani's own site lists activation welcome calls and survey automation.

None of these pages cites 85Y. Position Samajh on what it adds: an open question before any product is named, a deterministic comparison with the lender's record, an evidence log, and a measured evaluation. (C2.1 to C2.4, D2.2)

### 4. Ground each disclosure element (section 5, new sub-section)

Add after the call steps:

> **What grounds the opening.**
> - The call is made from the lender's 1600-series number. Required for service and transactional calls: TRAI direction of 19 November 2025 para 8(iii); RBI/2024-25/105. No TRAI text classifies a feedback call. We treat it as a service call.
> - The call carries no promotional content. Under the TCCCPR, promotional content makes it a promotional call, which needs the 140 series and consent.
> - The lender tells its telecom provider in advance that it uses automated calls. Required now: TCCCPR regulation 4 as substituted in February 2025. The Third Amendment of 18 September 2026 widens this to a declaration of all application-to-person calls, and treats undeclared calls as unsolicited commercial communication, from 60 days after gazette publication.
> - The AI line and the offer of a human. Recommended by RBI's FREE-AI committee report (para 4.4.54). We found no law that requires them.
> - The recording line. Our choice. The only RBI recording duty we found is for recovery calls.
> - The purpose, the right to decline, and a pointer to a written notice. Required by the DPDP Act sections 5 and 6 from 13 May 2027 where the lender relies on consent.
> - Calls are placed between 10:00 and 19:00. Our choice. We found no RBI or TRAI hour limit that applies in terms to a feedback call. 85N(4) sets 09:00 to 19:00 for sales staff and the card rules set 10:00 to 19:00.

Why: the design had no grounding for the disclosure step, and number series and automated-call declaration are day-one knowledge for a voice-AI vendor. (E1.2, E1.5, E1.8 to E1.12, E2.2 to E2.5, E3.2 to E3.5, E4.3, E4.8)

### 5. The identity check resembles the vishing pattern RBI warns about (section 5 steps 1 and 2)

Old (lines 64 to 65): "1. **Disclosure.** An automated call from the bank's customer-care team (not sales), recorded, about the loan taken on a given date. The bot says it is an AI, and the customer can ask for a human at any time. 2. **Identity check.** Synthetic: last 4 digits of the loan account, plus the date of birth."

New:

> 1. **Right-party check.** "Am I speaking with <first name>?" If not, the bot ends the call and says nothing about a loan.
> 2. **Disclosure.** The bank's name and "customer-care team". This is not a sales call and nothing will be offered. The caller is an automated AI assistant. The call is recorded to keep an accurate record of the feedback. The customer can decline, stop at any time, or ask for a human. The customer can hang up and call the customer-care number on the loan papers to check the call is genuine. The bot will never ask for an OTP, PIN, password or account number.
> 3. **Second check, no secret.** One low-sensitivity fact, for example the year of birth. The bot never asks for account digits.
> 4. **Context.** Only now does the bot mention the loan.

Why:
- RBI's public advice says: "Never share your account details such as account number, login ID, password, PIN, UPI-PIN, OTP, ATM / Debit card / credit card details with anyone, not even with bank officials, however genuine they might sound." This is public-awareness text, not a direction to lenders, and it does not name loan-account digits or a date of birth. An unknown caller asking for them still looks like the pattern it describes, and a customer who refuses is behaving sensibly. (E5.2, E5.3)
- We found no RBI text that prescribes how to authenticate a customer on an outbound call. (E5.1)
- Naming the loan before the right person is confirmed discloses it to whoever answers. 85N(6) and the 2026 recovery amendment protect the customer's privacy on other kinds of call, so this is good practice by analogy. (A21, E5.4)
- A first-name "yes" alone is a weak check. If v1 keeps only that, say so in the limits.

### 6. Section 9 lists two wrong scenario templates

Old (line 150): "(§1, plus BNG-L-033-1617-0600 for bundling, AHD-L-021-1617-0367 for an undisclosed health declaration, and the Baramulla consumer commission v J&K Bank 2026 case)"

New: "(§1, plus BNG-L-033-1617-0600 where the customer paid for a policy 'as a requirement of a security deposit for the overdraft facility', BHP-L-013-1617-0436 where the complainant said he was asked to deposit ₹1 lakh 'as an Fixed Deposit to get the housing loan', and Baramulla consumer commission CC 33/2025 v J&K Bank where ₹2,00,000 was debited for a policy without consent). Compliant scenarios are written synthetically."

Why:
- AHD-L-021-1617-0367 is a death-claim dispute that the insurer won. The Ombudsman found the health questions had been answered in the negative despite earlier illness. It is not a mis-selling win. (B6)
- The Baramulla order says the money was debited "from the account of the complainant". It does not say the premium came out of the loan. The bank was proceeded against ex parte, and the order discusses no call. Our copy is a scan hosted by a news site. (B7)
- Awards the insurer won are not compliant sales. In PUN-L-013-1617-0583, NOI-L-036-1819-0337 and JPR-L-041-1920-0004 the complaint failed on the evidence or on delay, and each complainant alleged a false promise or no knowledge of the policy. A teach-back call to those customers should flag. Using them as "must not flag" gold would corrupt the false-flag rate in E2. (B-N14 to B-N16)
- Eighteen more awards are verified and available as templates. (B-N1 to B-N18)

### 7. 85Z does not make a flag a refund case (sections 2, 4, 6, 10)

Old (line 34): `| 85Z | Mis-selling → full refund + compensation | We prepare the refund case for human review |`

New: `| 85Z | Where mis-selling is established, the bank refunds the full amount paid and compensates loss under its own policy. A customer may also complain within a set window | We prepare an evidence pack for the bank's reviewer |`

Old (line 116): "Any product with a flag → `flag_for_review` plus a draft refund case."

New: "Any product with a flag → `flag_for_review`. A flag on kind, premium, 85G, 85V or 85W also produces an evidence pack: the record, the customer's words with timestamps, and the paragraph engaged."

Old (lines 48, 93, 156): "a draft refund case", "REFUND CASE DRAFT (85Z)", "a refund case is drafted"

New: "an evidence pack for review", "EVIDENCE PACK (for the bank's 85Z review)", "an evidence pack is prepared for the reviewer"

Why: the refund duty arises "in cases where mis-selling of a financial product / service is established". The text does not say who establishes it, and it does not say whether a complaint is needed. It sets no refund deadline and leaves compensation to the bank's "approved policy". A flag is not established mis-selling, and a draft refund for a customer who misremembered the cover term presumes a loss. The same paragraph lets a customer complain within the product regulator's timeline or, failing one, "within 30 days of receiving the signed copy of the terms and conditions". (A18)

### 8. The demo verdict and closing line read as findings (sections 6, 10, 11)

Old (line 156): "→ red: thinks it's an FD (4(20A)(ii)), paid from the loan without consent (85W), no consent record (85G)."

New: "→ FLAG FOR REVIEW: the customer describes the product as an FD and the record says credit-life (possible incorrect information, 4(20A)(ii)); the premium was funded from the loan and the record holds no consent (85W, 85G)."

Old (line 158): "5. Close on the Ombudsman awards where the recorded "yes" still lost."

New: "5. Close on the Ombudsman's own words: 'The PIVC recording is clear about the terms and conditions of the policy but the maturity benefit is not explained.'"

Old (line 164): "Ombudsman awards show yes/no calls failed misled customers"

New: see ledger row S4.

Rename the rule id `4(20A)(ii)` in section 6 to `belief_mismatch`, with 4(20A)(ii) as the paragraph it may engage.

Why: 4(20A) is the definition of mis-selling. Printing it as the verdict breaks the section 11 ban on "this is mis-selling". A wrong belief is evidence that incorrect information may have been given, not proof. (A19, B-N2, D6.13)

### 9. Title, coverage and citation form (section 2 and section 11)

Old (line 22): "RBI's Responsible Business Conduct (Second Amendment) Directions 2026 take effect on **1 Jan 2027**. Commercial banks: RBI/2026-27/115, para 85Y. NBFCs: RBI/2026-27/123, para 101Y. Every other RBI-regulated lender gets an equivalent paragraph, and HFCs inherit it via para 157A **[verify circular numbers against PDFs]**."

New: "On 15 June 2026 RBI issued ten entity-specific Amendment Directions on 'Advertising, Marketing and Sale of Financial Products and Services by Regulated Entities'. They take effect on **1 January 2027**. Commercial banks: Reserve Bank of India (Commercial Banks - Responsible Business Conduct) Second Amendment Directions, 2026, RBI/2026-27/115, para 85Y. NBFCs: RBI/2026-27/123, para 101Y. Small finance banks, payments banks, local area banks, regional rural banks, urban and rural co-operative banks and All India Financial Institutions have the same paragraph under their own numbers. Housing finance companies follow NBFC paragraphs 101A to 101ZA through para 157A of the HFC Directions (RBI/2026-27/124)."

Old (line 164): "it applies to every RBI-regulated lender from 1 Jan 2027"

New: see ledger row S2.

Old (line 166): "(an SMS survey is allowed)"

New: "(85Y names call-backs or surveys and sets no channel)"

Also: for NBFCs the mis-selling definition is para 6(9A), not 4(20A). RBI's consolidated Directions pages did not yet show paragraphs 85A to 85ZA on 10 November 2026, so cite the amendment.

Why: no instrument has the title the design uses. Payments banks got "Amendment Directions", and the HFC title has no "Responsible Business Conduct". The NBFC direction excludes four NBFC types. No RBI text says an SMS survey meets the purpose of 85Y. (A1, A5 to A8, A10, A13)

### 10. "Samajh is that mechanism" overclaims (sections 2 and 3)

Old (line 26): "Samajh is that mechanism."

New: "Samajh is a tool a bank's non-sales unit can use to run that mechanism."

Add: "85Y requires four things: a feedback mechanism, feedback sought within 30 days of the sale, the purpose of ensuring customers understood features and risks, and a half-yearly report used to review policies and products. Random selection, call-backs, surveys and the independent unit sit in a sentence that begins 'may include'. 85Y does not say who receives the report and requires no filing with RBI."

Old (line 39): "the compliance head who signs the half-yearly report"

New: "the compliance head who owns the half-yearly report"

Why: 85Y puts the duty on the bank and names no signatory. (A11, A29, D6.12)

### 11. The cancel question may state a right the borrower does not have (section 5 step 4)

Old (line 67): "Do you know you can cancel it within N days?"

New: "Were you told whether you can cancel this cover, and by when?" The bot compares the answer with `cancel_window_days` on the record and never states a right itself.

Why: IRDAI's 2024 Regulations give "every policyholder of life and new individual health insurance policies, except for those policies with tenure of less than a year" a free-look period of 30 days from receipt of the policy document. Credit-life with a loan is usually group cover with the lender as master policyholder, and cover on a short gold loan may run under a year. We found no text that gives a group member a free-look right, though one saved award applies a free-look period under a group master policy's own terms (JPR-L-041-1920-0004). RBI's chapter has no free-look or cooling-off rule. The digital-lending cooling-off period is a separate right of at least one day. A closed question that asserts a 30-day right could be false for the hero product. (C1.4, A26, D4.2)

### 12. The consent check is a yes/no question (section 5 step 5, section 6 rule 85G)

Old (line 68): "5. **Consent check.** "Our records show you agreed on <date> — is that right?" This only checks existing consent; the call never *captures* it."

New: "5. **Consent check.** "When you took the loan, what did you agree to buy, and how did you agree?" The bot compares the answer with the consent record. The call never *captures* consent."

Add to the 85G rule: "A consent record that the customer does not recognise → flag for review. A record on file does not clear 85G by itself."

Why: the design's own thesis is that a "yes" is weak evidence, and step 5 asks for one. RBI defines explicit consent as "a specific, informed and unambiguous indication of an individual's choice". A record can exist for a consent that was not informed. (A15)

### 13. Pilot numbers break the "n and audio source" rule (sections 5, 6, 8, 12)

| Line | Old | New |
|---|---|---|
| 69 | "on the phone line, Prisma dropped "paune" from "paune do lakh"" | "in one pilot sentence (n = 1, TTS voice, simulated 8 kHz phone audio), Prisma v3.0 returned 2,00,000 for "paune do lakh"" |
| 83, 118 | "pilot-proven"; "In the pilot it fixed every case where Prisma's digit conversion (ITN) went wrong." | "tested in-sample"; "On the 20-sentence pilot (one TTS voice) it corrected all 8 transcripts where Prisma's digits ignored the fraction word. It was written after seeing those results and has no held-out test yet." |
| 135 | "~0.02 credits per STT call, ~0.06 per TTS call ... ≈ **240 credits (<5% of 5,000)**" | "about 0.02 credits per 3-second STT call (n = 78) and 0.06 per short TTS sentence (n = 20), from one dashboard reading with no saved screenshot. The four-language plan is about 230 to 265 credits, which is about a quarter of the 1,000-credit project cap." |
| 136 | "STT median 0.3 s, TTS 0.8 s" | "STT about 0.2 to 0.3 s and TTS about 0.6 to 0.8 s on short clips (pilot and client probe)" |

Also reconcile `IDEAS-HILLCLIMB.md` line 127 (180 credits) with `DESIGN.md` (240 credits). Both are right for their plans. The plans differ by a third.

Why: D5.1 to D5.10. The credit split and the latency cannot be rechecked, because the pilot ledger is gitignored and no dashboard screenshot was saved. The reviewer did not recompute these numbers.

### 14. Risk 1 claims an answer the experiment does not give (section 13)

Old (line 181): "| "SMS is enough, why voice?" | E1 answers it with our own data; the Ombudsman awards show yes/no calls failing |"

New: "| "SMS is enough, why voice?" | E1 compares teach-back with a yes/no confirmation. A yes/no SMS is the same question in text, so E1 bears on it, but E1 has no SMS arm and does not measure response rates |"

Why: E1 runs both arms by voice. Either add a text-confirmation arm or keep the narrower claim. (D contradiction 7)

Also fix the mismatch between "≥10 improvised calls per supported language" (sections 4 and 9) and "≥20 improvised human calls" (section 13).

### 15. Teach-back wording (sections 4, 9, 10)

Add to section 9 under E1: "Teach-back means asking a person to explain in their own words what they were told. It is well studied in healthcare. Reviews report benefits, but the newest systematic review (2026) found no clear pattern of effect on knowledge. We found no study of teach-back for loan or insurance sales, and none by an automated voice. E1 is our own test of it."

Call the product "a teach-back-style comprehension check". Samajh assesses and does not re-teach.

Why: C3.1 to C3.10. The one telephone trial we found (a nurse helpline) had a null primary outcome. Most of these rows rest on abstracts, not full papers.

### 16. Scenario gold verdicts must match what the awards ordered (section 9)

Add after the gold-standard paragraph: "Each scenario records the remedy in its source award. Relief varied: of the 22 awards we read that gave the customer relief, about two-thirds ordered a refund and about one-third a conversion to a single-premium policy."

Why: conversions include BNG-L-041-1617-0797, BNG-L-033-1617-0600 and BHP-L-013-1617-0436. Refunds include BHP-L-021-1617-0529, PUN-L-036-1617-0228, PUN-L-017-1617-0684, CHD-L-019-1718-1436 and the Baramulla order. (B product implication 5)

### 17. Replace the Nigeria remark and add quotable complaint data (section 11)

Old (line 166): "Indian SMS-vs-voice response rates (the only data is from Nigeria)"

New: "Indian SMS-vs-voice response rates (we found no controlled Indian comparison for a lender's customers; the closest peer-reviewed study is from Nigeria, on cold calls to the general population)"

Add to "We can say": "IRDAI recorded 26,667 unfair-business-practice grievances against life insurers in 2024-25, up from 23,335. The category includes mis-selling. The National Housing Bank wrote to housing finance companies on 10 December 2024 after inspections found insurance bundled with housing loans. No official source we found says how many borrowers are sold insurance with a loan."

Why: D1.1, D1.2, C4.2, C4.6, C4.8.

### 18. Smaller edits

| Where | Old | New | Why |
|---|---|---|---|
| Line 30 | "Explicit consent for each product, recorded" | "Explicit consent for each product (for example a signed declaration, OTP, digitally recorded confirmation, or a demarcated clause), kept until one year after the contract ends" | "recorded" does not mean audio, and 85G's list is open-ended (A15) |
| Line 32 | "No paying for a product out of the loan without explicit consent" | Keep. | 85W matches (A17) |
| Line 70 | "Someone from our team will call you within N days." | Keep, with N set by the bank. | A promise the bank must keep |
| Line 128 | "cloning a bank officer's voice would be misleading" | Add: "and voice patterns used for authentication are biometric data under the SPDI Rules 2011" | E2.9, read in a mirror copy |
| Line 185 | "Regulatory wording drifts or the citation numbers are wrong" | "Regulatory wording drifts: recheck RBI's notifications for amendments dated after 6 August 2026 before submission" | A33 |
| `IDEAS-HILLCLIMB.md` line 79 | "IRDAI/LIFE/CIR/MISC/116/05/2020" | "IRDAI/Life/Misc/CIR/116/05/2020 (12 May 2020), superseded by the Master Circular of 5 September 2024, para 31.1 item 27" | C1.1, C1.2 |
| `IDEAS-HILLCLIMB.md` lines 95, 97, 109, 113 | The old title; "No vendor offers 85Y callbacks"; "recorded 'yes' and still lost"; "₹2 lakh premium deducted from a CC loan"; the AHD-L-021 template | Add a note at the top that `references/claims/` supersedes these lines. | Items 2, 3, 6, 9 |

## Product implications

### Add

1. **A choice-of-provider field, a risk-mitigant field and a question.** See item 1. Without them the bundling check is wrong.
2. **A Key Facts Statement check.** Para 348 of the Commercial Banks - Responsible Business Conduct Directions, 2025 (para 29 for NBFCs) applies to "all new retail and MSME term loans sanctioned on or after October 1, 2024". It says "Charges recovered from the borrowers by the bank on behalf of third-party service providers on actual basis, such as insurance charges, legal charges etc., shall also form part of the APR and shall be disclosed separately", and that fees "not mentioned in the KFS, cannot be charged by the bank to the borrower at any stage during the term of the loan, without explicit consent of the borrower". Add `in_kfs: bool` to `Product` and flag a premium that is absent from the KFS. This rule is in force today, so the product does not rest only on 1 January 2027. Two limits: cite para 348 and not the old circular RBI/2024-25/18, which the 2025 Directions very likely repealed, and check that the scenario loan is a term loan, since a bullet-repayment gold loan may not be one. The same paragraph requires an acknowledgement that the borrower has "understood" the KFS, so expect the question "why is that acknowledgement not enough?" (D4.1)
3. **Early calls.** Place the call in the first one to two weeks after the sale, not near day 30. The 85Z fallback complaint window is 30 days from receipt of the signed terms, and the free-look period for an individual policy runs 30 days from receipt of the policy. A customer flagged on day 28 has almost no time to act. Record the day of the call relative to the sale in the evidence log. (A18, C1.4)
4. **A complete evidence log.** In about a third of the customer-relief awards we read, the Forum relied on the insurer not producing the sales-stage recording. Log the number called, the caller number, the time, the full audio with a hash, and every bot prompt. (B product implication 1)
5. **Synthetic compliant scenarios.** Write them from the rules: a required risk mitigant with a choice of provider, a voluntary add-on with a consent the customer recognises, a premium paid separately. Do not template them on awards. (Item 6)
6. **A "told how to answer" scenario group.** Four awards record complainants saying they were told how to answer the verification call. An open question in the customer's own words is the countermeasure the design proposes. (B4, B-N5, B-N6, B-N17)
7. **The basket-sneaking quote on a slide.** RBI's illustrative list of dark patterns (Annex IIA) includes "adding protection against online fraud / loan protection insurance by default during the loan application process". It illustrates a user-interface pattern under 85X. The hero case is a misdescription at a branch, so present it as a related pattern that RBI names. (A20)
8. **A headroom slide on the lender's own products.** 85Y covers "the sale of any financial product / service", and 85A covers the bank's "own as well as third-party" products. The same engine can check understanding of the loan itself: rate, EMI, tenure, charges. This is our reading of the chapter. (A12)
9. **A retention setting.** RBI fixes one year after contract end for consent records and nothing for feedback audio. The DPDP Rules set a one-year floor for logs from 13 May 2027. Make retention a configured value with those two anchors. (A29, E2.8)

### Remove or change

1. **The account-digits and date-of-birth check.** See item 5.
2. **A refund draft on every flag.** See item 7.
3. **The mis-selling paragraph as a verdict label.** See item 8.
4. **Any bot line that states a cancellation right.** See item 11.
5. **The yes/no consent question.** See item 12.
6. **Any sales content in the call,** including a mention of other products in the closing line. Promotional content moves the call to the promotional category. (E1.2, E1.7)

### Keep, and say why

1. **No explaining during the call.** 85J also bars a bank from presenting a third-party product as its own, so the bot names the insurer from the record and adds nothing. (A24)
2. **One simpler re-ask, then hand to a human.** This avoids the "nagging" pattern in RBI's dark-pattern annex, whose definition covers interactions "on any platform". (A20)
3. **No voice cloning and no voiceprints.** (E2.9)
4. **Regional languages.** This is our choice. 85R requires documents for the bank's own products "in the language of the region or in a language understood by the customer". For third-party products it defers to the product regulator, so 85R does not ground the language choice for insurance. (A25)

### Questions an interviewer may ask, with the grounded answer

| Question | Answer | Basis |
|---|---|---|
| Is a feedback call a commercial communication under TRAI's rules? | No TRAI text names it. We treat it as a service call: 1600 series, no promotional content, automated calling notified to the telecom provider. | E1.5, E1.10, E1.11 |
| Does the customer have to consent to this call? | Not under telecom rules for a service call. Under the DPDP Act, from 13 May 2027, the lender needs either consent or the ground that the customer gave the data for this purpose. The Act has no general legal-obligation ground. The lender should name feedback calls in its loan-time notice. | E1.3, E2.5 |
| Does RBI require a voice call? | No. 85Y names call-backs or surveys and sets no channel. | A11, A13 |
| Does a flag mean the customer gets a refund? | No. The duty arises where mis-selling is established. A flag is evidence for the bank's reviewer. | A18 |
| Is requiring insurance with a loan illegal? | 85V allows a third-party product required as a risk mitigant if the customer can choose the provider. RBI does not define "risk mitigant". | A16 |
| Who else does this? | SquadStack, Edesy and Ringg market adjacent calls. None cites 85Y. Say what Samajh adds. | C2.1 to C2.4 |
| Where does a foreign-hosted LLM fit? | For digital lenders, the Digital Lending Directions require storage in India and deletion within 24 hours of processing abroad. Check before sending transcripts abroad. | E2.9 |
| Doesn't IRDAI already require this for insurance? | The 2024 rules require a customer-feedback mechanism against mis-selling but no call. For distance-marketing sales, the 2011 guidelines required sampled verification calls "to ascertain whether the client has understood". We could not confirm they are still in force. | C1.3, C1.6 |

## Not settled

1. Whether the 85Y text changed between the February draft and the June final. RBI's statement on feedback received (Annex I) sits behind a CAPTCHA and has no archive copy. (A32)
2. Whether the 30-day feedback duty reaches sales made before 1 January 2027. The directions have no transitional clause. (A4)
3. Whether establishing mis-selling under 85Z needs a customer complaint, and who establishes it. (A18)
4. Whether a member of a group credit-life policy has a free-look right. (C1.4)
5. Whether RBI/2024-25/18 (the KFS circular) and RBI/2024-25/105 (the 1600-series circular) are still the operative instruments after the November 2025 consolidation. The KFS text is carried in para 348. The saved consolidated Directions do not mention the 1600 series. (D4.1, E1.8)
6. The gazette dates of the TCCCPR Third and Fourth Amendments. (E1.12)
7. How any bank plans to run 85Y feedback. No public statement was found. (D3.3)
8. RBI Ombudsman 2024-25 category figures. The report PDF could not be retrieved, so only press coverage supports them. (C4.4)
9. Whether RBI has amended the directions after 6 August 2026. (A33)
10. Four documents were read in copies the issuing body does not host: the FREE-AI report, the SPDI Rules 2011, IRDAI circular 274/11/2020 and the Baramulla order. Check each against the official copy before quoting it to judges.
