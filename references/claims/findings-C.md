# Findings C: supporting practice and evidence (PIVC, vendors, teach-back, prevalence data)

Research date: 2026-11-10. Saved sources are under `sources/C/`; `sources/C/INDEX.md` lists every file with URL, hash and issuer. Page numbers are PDF page numbers in the saved extraction (`===== page N =====`), unless a quote says "report p." (the page printed on the document).

Method notes:
- IRDAI documents came from `irdai.gov.in` (its site search at `irdai.gov.in/search?q=` returns document-detail pages that link the PDFs).
- The RBI Ombudsman 2024-25 report PDF sits behind a CAPTCHA and the Wayback copy returned HTTP 429. I did not get around either block, so numbers from that report are `secondary-only`.
- The web-search tool is US-only, returns summaries, and cannot see LinkedIn, webinar sign-ups, bank tender portals or login pages. A negative result from it is weak evidence.
- No real person is named. Case documents are referred to by forum, insurer and amount.

---

## C1. IRDAI pre-issuance verification call (PIVC)

### C1.1 The 2020 circular says "encouraged"
- Claim as worded: "PIVC is only 'encouraged' (IRDAI/LIFE/CIR/MISC/116/05/2020)" (`IDEAS-HILLCLIMB.md` line 79; the ban on "PIVC is mandatory" is `DESIGN.md` line 166)
- Status: verified
- Corrected wording: Cite **IRDAI/Life/Misc/CIR/116/05/2020, 12 May 2020, to All Life Insurers**. It says life insurers are "encouraged to conduct" PIVC "to the extent possible and certainly in important cases". It names no product or channel.
- Source: `sources/C/irdai-circular-pivc-116-05-2020.pdf` | https://irdai.gov.in/document-detail?documentId=394397 | retrieved 2026-11-10
- Quote: "all Life Insurers are encouraged to conduct Pre-Issuance Verification Call (PIVC) to the extent possible and certainly in important cases. Board approved guidelines may be put in place to this effect." (para 2, p1). "some of the life Insurers have adopted the practice of PIVC (Pre-Issuance Verification Call) to prevent mis-selling and unfair business practices" (para 1, p1)
- Notes: The PDF is a scan whose OCR layer misreads the number; I rendered the page and read "116" and "12/05/2020" by eye (`rendered-irdai-circular-pivc-116-05-2020-page1.png`). Para 1 rests on Reg 5(1)(iv) of the 2017 PPI Regulations, now repealed (C1.2).

### C1.2 The 2024 Master Circular supersedes it
- Claim as worded: "that circular appears repealed by the 2024 Master Circular" (`IDEAS-HILLCLIMB.md` line 105)
- Status: verified
- Corrected wording: "IRDAI's Master Circular on Protection of Policyholders' Interests (IRDAI/PP&GR/CIR/MISC/117/9/2024, 5 Sep 2024) supersedes the 2020 PIVC circular (para 31.1, item 27)." Drop "appears".
- Source: `sources/C/irdai-master-circular-ppi-2024-bilingual.pdf` | https://irdai.gov.in/web/guest/document-detail?documentId=5625747 | retrieved 2026-11-10
- Quote: "31.1. This Master Circular supersedes the following Guidelines/Circulars:" ... "27. IRDAI/Life/Misc/CIR/116/05/2020 Circular on Pre-Issuance Verification Call (PIVC)" (Chapter IX, pp150-151)
- Notes: The English title line in the PDF says "2025" while the reference and date say 2024; IRDAI's listing and the Canara order say "2024". The 2024 Regulations repeal the 2017 Regulations that the circular relied on: "The Insurance Regulatory and Development Authority of India (Protection of Policyholders' Interests) Regulations, 2017" (Reg 58(1)(g), p32 of `irdai-ppi-operations-regulations-2024.pdf`; Gazette 20 Mar 2024; in force "from the date of the publication in the Official Gazette or 1st April, 2024, whichever is later", Reg 1(3), p18).

### C1.3 No PIVC or welcome-call rule in the 2024 instruments; a customer-feedback mechanism is required
- Claim as worded: requested (what the 2024 documents say about verification and welcome calls)
- Status: verified (absence in the saved text, plus the positive provisions)
- Corrected wording: "The 2024 Regulations, the Master Circular on Protection of Policyholders' Interests and the Master Circular on Life Insurance Products contain no pre-issuance verification call or welcome call requirement. They do require insurers to have a mechanism against mis-selling that includes customer feedback."
- Source: `irdai-ppi-operations-regulations-2024.txt`, `irdai-master-circular-ppi-2024-bilingual.txt`, `irdai-master-circular-life-insurance-products-2024-en.txt` (searched for "pre-issuance", "PIVC", "verification call", "welcome call", "call back"; the only hit is the repeal list) | retrieved 2026-11-10
- Quote: "7.4 Lay down a mechanism of obtaining customer feedback." (Master Circular Section 2 Chapter II para 7 "Mis-selling", p141). "establish a mechanism to obtain feedback for continuous improvements" (Reg 21(2), p24). "Before the prospect is directed to fill up the proposal form, explicit confirmation for Benefit Illustration from the prospect shall be obtained about their understanding the benefits illustrated." (para 4.3, online sales, p139)
- Notes: Anyone running a PIVC today does it as an own control. Para 7.4 and Reg 21(2) are the insurance-side counterparts of RBI para 85Y, but they set no 30-day window and no call-back. Do not say "IRDAI requires a feedback call".

### C1.4 Free-look is 30 days from receipt of the policy document
- Claim as worded: the call asks "Do you know you can cancel it within N days?" (`DESIGN.md` line 67)
- Status: verified for individual life policies; unverifiable for group credit-life members
- Corrected wording: "30 days from the date of receipt of the policy document, whether received electronically or otherwise, for life policies (except tenure under one year)." The 2017 rule was 15 days (30 for electronic or distance-mode policies) and is repealed.
- Source: `irdai-ppi-operations-regulations-2024.pdf` Reg 20 (p24) | `irdai-master-circular-ppi-2024-bilingual.pdf` Part A para 2 (p105) | `irdai-master-circular-life-insurance-products-2024-en.pdf` para 5 | `irdai-ppi-regulations-2017.pdf` (p20) | retrieved 2026-11-10
- Quote: "Every policyholder of life and new individual health insurance policies, except for those policies with tenure of less than a year, shall be provided a free look period of 30 days beginning from the date of receipt of policy document, whether received electronically or otherwise, to review the terms and conditions of such policy." (Reg 20(1)). Old rule: "he has a free look period of 15 days from the date of receipt of the policy document and period of 30 days in case of electronic policies and policies obtained through distance mode" (2017 Regs, Reg 10(1)(i), p20)
- Notes: Credit-life sold with loans is usually a group policy with the lender as master policyholder. Reg 14(2)(iii)(b): "the individual group member would be treated as the insured beneficiary and the master policyholder will only be the holder of the policy". Reg 20 gives free-look to "every policyholder". I found no text giving a borrower-member a free-look right. The Master Circular does say the Customer Information Sheet must "be provided to every policyholder in case of both Individual Insurance policy holder as well as a Member of a Group Insurance Policy" (Part A, p104). Compliance should confirm before the script states a number; use the 30-day line only for individual policies in scenarios.

### C1.5 IRDAI rules on insurance sold with loans
- Claim as worded: requested
- Status: verified (existing rule is consumer information; the bundling ban is only proposed)
- Corrected wording: "IRDAI's Master Circular tells borrowers buying insurance through the lender is not compulsory. A ban on compulsory bundling by banks and NBFCs acting as insurance distributors is proposed in IRDAI's 23 Sep 2026 consultation paper; it is not yet a rule."
- Source: `irdai-master-circular-ppi-2024-bilingual.pdf` (p100) | `irdai-consultation-paper-distribution-reforms-part1-2026-09.pdf` (pp58-59) | `irdai-master-circular-life-insurance-products-2024-en.pdf` (pp10-11) | retrieved 2026-11-10
- Quote: "In case of availing insurance cover for loans like housing or any other kind of loans, the prospect may note as under: a. it is not compulsory to purchase insurance policy through the financial institution giving loan. He / She is free to buy insurance policy from any insurer or through any distribution channel through any mode." (Master Circular Part A para 2(iv), p100). "131. It is proposed to prohibit compulsory bundling of insurance products by banks and NBFCs, registered with the authority as IDEs, along with their products and services." (consultation paper p58). Footnote 17: "Agreeing to provide a loan (such as home loan, motor loan, working capital, loan for plant & machinery, export credit, etc.) conditional upon the borrower necessarily buying an insurance product (that may or may not be related to the asset being financed by the loan) is compulsory bundling." Credit-life: "The coverage term at inception shall not be more than the outstanding loan tenure." and "Sum Assured shall also be consistent with the original loan amount sanctioned" (Life Products Master Circular 7.16.1-7.16.2)
- Notes: The paper's "acceptable package" for a loan with a rate discount requires "Premium for the insurance product is paid separately and directly by the customer from his account/debit card/credit card and not out of the loan amount." Comments were extended to 31 Oct 2026: "the last date for submission of comments has been extended till 31st October 2026" (`irdai-extension-feedback-distribution-reforms-consultation-2026.pdf`). Present as a proposal.

### C1.6 Other IRDAI rules that make a verification call mandatory
- Claim as worded: requested (distance marketing, seniors, bank corporate agents)
- Status: verified that the texts exist; current force unverifiable
- Corrected wording: "No 2024 rule requires a verification call. Older IRDAI instruments required sampled post-sale verification calls to check understanding for policies sold by distance marketing: at least 3% of such policyholders a month. They are the nearest insurance precedent for 85Y-style calls. I could not confirm they are still in force."
- Source: `irdai-guidelines-distance-marketing-2011.pdf` | `excerpt-irdai-corporate-agents-regs-2015-schedule-VII-pages-75-77.pdf` | `excerpt-irdai-web-aggregators-regs-2017-pages-51-52.pdf` | `irdai-circular-208-08-2020-dispensing-physical-signature.pdf` | `secondary-taxguru-irdai-circular-274-11-2020-dispensing-physical-signature.html` | retrieved 2026-11-10
- Quote: "Insurers shall make verification calls, to monitor the quality of sales, to a minimum of 3% of the policyholders who purchase insurance over distance marketing mode, every month. The purpose of verification calls is to ascertain whether the client has understood the benefits, features and disclosures of the product purchased correctly. Verification calls shall also bear a standardized script" (IRDA/ADMN/GDL/MISC/059/04/2011, 5 Apr 2011, s.13(iii), p10). Same for corporate agents: "Corporate agent shall make verification calls, to monitor the quality of sales, to a minimum of 3% of the policyholders who purchase insurance over distance marketing mode, every month." (2015 Regs, Schedule VII para 11(iii), p76) and web aggregators (2017 Regs, Schedule VI para 15(c), p52). "Carrying out pre-issuance verification calls in respect of all such proposals." (IRDAI/Life/Cir/Misc/208/08/2020, 5 Aug 2020, para 2(d), p2)
- Notes:
  - The 2020 e-consent circulars were a time-limited concession (no wet signature), not a standing rule. 208/08/2020 ran "on an experimental basis with immediate effect till" 31 Dec 2020 for pure-risk products. The 12 Nov 2020 circular 274/11/2020 widened it and added: "The Insurer shall verify at least 3% of sales to ascertain compliance with these provisions. The records of verification calls shall be preserved for a period of not less than 3 years." (TaxGuru copy, `secondary-only`; the IRDAI-hosted main text was not found, but IRDAI's Annexure 1 and the later extensions are saved). The last extension on irdai.gov.in runs "up to 30/09/2022" (circular 059/03/2022). I found none after, so the concession appears to have lapsed; not proven.
  - Not in the 2024 Master Circular's repeal list: the 2011 guidelines and the e-consent circulars. (Item 6 there, "Verification of the Authenticity of calls", CAD/01/10-11, is a different document.) The 2011 guidelines are still on the IRDAI consumer site under "Already in Place". The intermediary regulations were amended after 2015/2017 and I did not check each amendment.
  - Seniors: I found no IRDAI rule mandating a verification call for senior citizens. Banks as corporate agents: only the distance-marketing sampling rule above.

### C1.7 The Canara HSBC Life order (10 Sep 2026)
- Claim as worded: "IRDAI's Canara HSBC order (10 Sep 2026, Rs 1 cr) calls the pre-issuance call 'a critical regulatory safeguard'" (`IDEAS-HILLCLIMB.md` line 47)
- Status: verified
- Corrected wording: none for the quote. Add: "The order lists no PIVC-specific rule among the provisions violated."
- Source: `irdai-order-canara-hsbc-life-2026-09.pdf` | https://irdai.gov.in/web/guest/document-detail?documentId=9825939 | retrieved 2026-11-10
- Quote: "A pre-issuance verification call is a critical regulatory safeguard and a formal touchpoint for ensuring informed consent. Any misrepresentation of the fundamental benefit structure of the product during such a call directly undermines the integrity of the entire disclosure framework." (para 5.10, p11). "the Authority hereby imposes a penalty of Rs. One Crore (Rs. 1,00,00,000/-) on the insurer" (para 6.1, p14). "Date: 10th September 2026" (p17). "Ref: IRDAI/PP&GR/ORD/MISC/118/9/2026" (p1)
- Notes: "the caller misrepresented that the policyholder would receive the annuity, whereas in fact, it was the daughter of the policyholder (annuitant) who would be the recipient" (para 3.2.3, p3). The insurer's remedy included "introduction of pre-issuance video-based validation calls" (para 4.7, p7). Provisions penalised: Regs 6(b), 7(2)(i), 21(7) of the 2024 Regulations, Master Circular clauses on fair treatment, suitability and the proposal stage, and Reg 5(2) of the Corporate Governance Regulations (paras 6.1.1-6.1.2); none is a PIVC rule. The order also requires a three-year audit of policies sold to people above 75 through the bank corporate agent (para 6.2.1). It names the policyholder; do not repeat the name.

### C1.8 The IRDAI consultation paper with 12 mis-selling illustrations (Box 5, pp61-62)
- Claim as worded: "a draft IRDAI paper lists 12 mis-selling practices (Box 5, pp. 61-62)" (`IDEAS-HILLCLIMB.md` lines 47, 97)
- Status: verified
- Corrected wording: "IRDAI's consultation paper 'Recalibrating Economics of Insurance Distribution' (Part 1, 23 Sep 2026) proposes 12 'illustrations of mis-selling of insurance products' in Box 5. They are proposals, not rules."
- Source: `irdai-consultation-paper-distribution-reforms-part1-2026-09.pdf` (hosted by IIB for IRDAI, https://iib.gov.in/dr); press release `irdai-press-release-distribution-reforms-consultation-2026-09-23.pdf` | retrieved 2026-11-10
- Quote: "Proposed guidance by the Authority: The following are illustrations of mis-selling of insurance products and would attract disincentive or regulatory action." (Box 5, p61); item "1. Selling a regular premium product as a single premium product;" (p61) to "12. Selling life insurance products for inheritance planning." (p62)
- Notes: All 12 concern life products (premium type, ULIPs, deposit-like sales, assured returns, switching, single-premium products). None is "insurance bundled with a loan"; that is Section 10 (pp58-59). Box 5 also quotes RBI's definition including "(iv) Compulsory bundling of another product / service with sale of the requested product / service" (p61). "About 8 detectable in a call" in the earlier note is a judgement, not in the paper.

### C1.9 One-sentence legal status of PIVC today
- Claim as worded: the design bans "PIVC is mandatory" (`DESIGN.md` line 166)
- Status: verified (the ban stands)
- Corrected wording: **"A pre-issuance verification call is not a stand-alone legal requirement under IRDAI's current (2024) framework: the only circular that addressed it (12 May 2020) merely encouraged life insurers to run one and has been superseded, though IRDAI's September 2026 Canara HSBC Life order treats a PIVC, where an insurer runs one, as 'a critical regulatory safeguard', and older IRDAI instruments required sampled verification calls for distance-marketing sales."**
- Source: C1.1 to C1.8
- Notes: Safe: "IRDAI encouraged pre-issuance verification calls in 2020, and in September 2026 called one 'a critical regulatory safeguard' when it fined an insurer Rs 1 crore over a defective call." Unsafe: "IRDAI requires a PIVC", "PIVC is mandatory", "PIVC is only encouraged" (it was).

---

## C2. Is there an existing vendor product for an 85Y-style understanding callback?

Search record (2026-11-10): about 30 queries combining "85Y", "post-sale feedback", "feedback mechanism within 30 days", "customer understanding", "mis-selling", "mis-sell check" with "voice bot", "AI agent", "call-back", "welcome call", "RBI responsible business conduct 2026", "tender", "RFP", "webinar", "LinkedIn"; domain-restricted searches per named vendor and the four consultancies; fetches of the closest pages (saved in `sources/C/vendors/`).

### C2.1 "We found no vendor marketing an 85Y understanding callback"
- Claim as worded: "we found no vendor marketing an 85Y understanding callback (searched Nov 2026)" (`DESIGN.md` line 164; `IDEAS-HILLCLIMB.md` line 97: "No vendor offers 85Y callbacks or per-product consent checks")
- Status: wrong as worded (a negative can never be `verified`, and two vendor pages came close)
- Corrected wording: "On 10 Nov 2026 we found no vendor page that cites para 85Y/101Y or sells a product built for the RBI 30-day post-sale feedback mechanism with independent-team calls and a half-yearly findings report. We did find vendor blogs (Sept to Oct 2026) describing AI welcome or post-disbursal calls that ask whether the borrower understood (SquadStack, Edesy), and a vendor case study comparing sales-call content with policy documents (NuSummit). What we add: rule-grounded comparison against the lender's records, teach-back rather than yes/no, an evidence log." Do not write "nobody does this" or "no vendor offers 85Y callbacks".
- Source: C2.2 to C2.9
- Notes: Verdict: "none found" is not supportable as worded; supportable only in the narrow form above, as "a documented search, not proof". The search could not see LinkedIn, private demos, decks or bank procurement portals. A generic "feedback call" product could be pointed at 85Y without ever saying so publicly.

### C2.2 SquadStack (closest hit; blog dated 21 Oct 2026)
- Status: verified as to what the page says; "RBI-required" is the vendor's unsupported claim
- Source: `vendors/squadstack-gold-loan-disbursement-follow-up.html` | https://www.squadstack.ai/blog/gold-loan-disbursement-follow-up-ai-voice-for-nbfcs | "October 21, 2026" | retrieved 2026-11-10
- Quote: "This call doubles as the RBI-required welcome and mis-sell check: the agent asks whether the borrower understands what they agreed to, creating an auditable contact record." (Stage 3). "RBI's April 2026 gold loan framework introduced tiered LTV caps and stricter auction norms, making compliant, documented contact attempts a regulatory necessity" (TL;DR)
- Notes: Offers an AI voice agent (9 Indian languages) for NBFC gold-loan disbursement follow-up. Close in intent, far in method: no 85Y/101Y citation, no 30-day timing, no independence from sales (Stage 4 of the same flow is cross-sell), no per-product check against records, no half-yearly report. It asks the borrower to self-report understanding, the pattern Samajh criticises.

### C2.3 Edesy (blog, 10 Sep 2026)
- Status: verified as to what the page says
- Source: `vendors/edesy-customer-onboarding-welcome-calls-ai-voice-2026.html` | https://edesy.in/blog/customer-onboarding-welcome-calls-ai-voice-2026 | "Edesy Team · September 10, 2026" | retrieved 2026-11-10
- Quote: "The rule across all of them: confirm what the customer understood , not just what the system says." and "The welcome call is also the best moment to catch mis-selling. If the customer says "I was told this is a fixed deposit" or "I thought the premium was one-time", the agent records it and routes the case to a person immediately."
- Notes: Self-serve AI welcome calls for lenders and insurers. The sample script is closed questions ("Kya aapko Key Fact Statement mil gaya? Aur kya aap jaante hain ki aap cooling-off period mein bina penalty ke loan band kar sakte hain?"). Cites RBI Digital Lending Directions 2025 (cooling-off) and IRDAI free-look, not 85Y.

### C2.4 NuSummit (case study; undated)
- Status: verified as to what the page says; numbers self-reported
- Source: `vendors/nusummit-preventing-policy-mis-selling-ai-document-call-verification.html` | https://www.nusummit.com/preventing-policy-mis-selling-ai-led-document-call-verification/ | retrieved 2026-11-10
- Quote: "The system then summarized the conversation so reviewers could quickly understand what was discussed, what was promised, and where there might be a mismatch." and "helped to reduce the mis-selling percentage from ~3% to ~1.8% in first 6-7 months of implementation."
- Notes: Insurance client; transcribes the agent-customer call and compares it with proposal and policy data. It audits what the **seller said**; Samajh asks the **customer** afterwards. Not RBI-related. Do not quote the 3% to 1.8% figure (no defined baseline, no audit).

### C2.5 Saakshi (hackathon entry, 5 Sep 2026; not a vendor)
- Status: verified as to what the page says
- Source: `vendors/lablab-saakshi-consent-you-can-prove.html` | https://lablab.ai/submissions/yq8ij2120upfm8wq4mztpj2x | "Created by team MONSTER on September 05, 2026" | retrieved 2026-11-10
- Quote: "Then she asks three to five teach-back questions from what was said, hears the Hinglish answers and records a verdict each." and "No customers yet; every number on /metrics carries its command."
- Notes: Sits in the sale between advisor and customer (AssemblyAI streaming STT, English and Hindi), checks each turn against a disclosure rulebook (IRDAI ULIP, RBI KFS loan). Not post-sale, not 85Y. It shows teach-back with Indian-language voice was demoed this same month, so "first to use teach-back" is not a claim to make.

### C2.6 PIVC vendors (pre-sale)
- Status: verified as to what the pages say
- Source: `vendors/authbridge-pre-issuance-verification-pivc.html`, `perfios-pre-issuance-verification-call-product.html`, `skit-ai-voice-ai-for-insurance-persistency-renewals.html` (blog 2 May 2022) | retrieved 2026-11-10
- Quote: AuthBridge: "Prevent misselling of policies by getting the customer's consent. Show clear & concise policy details and documents to the customer on the call and capture their audio and visual consent there and then." Perfios: "Complete your policy consent in less than 3 minutes with our user-friendly DIY journey." Skit.ai: "PIVC (Pre-Insurance Verification call) where a call is triggered by the insurance company to share the important insurance details and confirm it with the policyholder."
- Notes: Identity and consent confirmation before issue, usually video, face match and a listening customer. None mentions 85Y, loans or understanding in the customer's own words.

### C2.7 Call-audit and generic feedback-call vendors
- Status: verified as to what the pages say
- Source: `vendors/callerdigital-mis-selling-controls-voice-sales-calls.html` (Sep 8, 2026), `convin-call-verification-banking.html`, `haptik-voice-ai-for-banking.html`, `gnani-banking-customer-experience-voice-ai-feedback.html`, `ringg-voice-ai-compliance-india.html` (20 Oct 2026), `sarvam-docs-bfsi-voice-bots-stt.html`, `skit-ai-in-homepage.html`
- Quote: Caller.Digital: "Regulators across RBI, IRDAI and SEBI have moved steadily toward asking whether the customer actually understood and whether the product was suitable, which is a question a signed form cannot answer and a call recording can."
- Notes: Caller.Digital sells 100% audit of recorded sales calls (what the seller said). Gnani, Haptik, Convin, Ringg, Sarvam and Skit pages describe feedback, welcome, verification or audit calls in general terms; none cites 85Y or a 30-day understanding check. Ringg's compliance guide covers TRAI, DPDP, RBI recovery and IRDAI distance-marketing recording rules but not mis-selling.

### C2.8 How lawyers, advisers and analysts say lenders will comply
- Status: verified as to what the pages say
- Source: `vendors/vinodkothari-from-consent-to-compensation-rbi-directions-sales-practices.html`, `corporateprofessionals-when-a-signature-is-not-consent.html`, `khaitan-new-business-conduct-directions-dpdpa.html`, `forrester-consent-deficit-rbi-rbc-directions.html`, `outlookbusiness-rbi-new-mis-selling-rules-explained-2027.html`; `prevalence/loksabha-188-AU1257.pdf`
- Quote: Corporate Professionals (NBFCs): "Stand up an independent feedback and grievance function for 30-day post-sale verification and half-yearly reporting." Vinod Kothari (Feb 2026, draft): "Feedback mechanism from customers to obtain feedback within 30 days from sale of any product/ service" ... "to ensure that customers have understood features of the product/ service and associated risks". Outlook Business: "Another key change is the introduction of post-sale verification. Within 30 days of a sale, banks will be required to seek customer feedback through call-backs or surveys conducted by teams that were not involved in the original sale process." Lok Sabha Unstarred Q.1257 (27 Jul 2026, p2): "banks are required to establish a mechanism to seek feedback from customers within a specified timeline to ensure that customers have understood the features of the financial product / service and also the risks"
- Notes: These explain 85Y/101Y and advise an independent function; none recommends a vendor. Forrester (16 Mar 2026) calls mis-selling "a proof problem" but does not discuss the feedback call. Vinod Kothari's DSA/DMA code-of-conduct list includes "No Post-Sale Solicitation: Avoid calls regarding sold products; redirect customers to RE customer service." It is a rule for sales agents; group E should confirm it does not touch the bank's own feedback calls. No Deloitte, PwC, EY or KPMG India note on complying with 85Y was found.

### C2.9 Named-vendor coverage
- Status: unverifiable (documented search, not proof of absence)
- Notes: No page citing 85Y/101Y or marketing an RBI post-sale understanding callback was found for any named vendor.
  - Fetched and read: Gnani.ai, Sarvam, Skit.ai, Haptik, Ringg, Convin, NuSummit, AuthBridge, Perfios, Caller.Digital, Edesy, SquadStack.
  - Domain-restricted searches only, no relevant hit: Yellow.ai, Uniphore, Exotel, Ozonetel, Knowlarity, CoRover, Reverie (one page unfetchable), Mihup, Observe.AI, Krisp, GreyLabs, Signzy (recovery and KYC blogs only), HyperVerge and IDfy (KYC and V-CIP only), Artivatic, Lentra, VideoCX, Credgenics, Vernacular.ai (now Skit.ai).
  - The 113 catalogued challenge entries in `references/challenge-entries-github.json` include no 85Y or post-sale understanding project.
  - Bank tenders: aggregator search found nothing; GeM and bank portals are not searchable with this tool.

---

## C3. Teach-back as an evidence-based method

### C3.1 AHRQ Health Literacy Universal Precautions Toolkit, Tool 5
- Claim as worded: "A 'yes' doesn't show that the customer understood." (`DESIGN.md` line 17); E1 headline (`DESIGN.md` line 144)
- Status: verified (practice guidance, not a trial)
- Source: `teachback/ahrq-health-literacy-universal-precautions-toolkit-tool5-teach-back.html` | https://www.ahrq.gov/health-literacy/improve/precautions/tool5.html (reviewed April 2024) | retrieved 2026-11-10
- Quote: "The teach-back method is a way of checking understanding by asking patients to state in their own words what they need to know or do about their health." "Do not ask questions that can be answered with a "yes" or "no." "Do you understand?" and "Does that make sense?" are NOT teach-back questions. Patients are likely to answer "yes" whether they understand or not." "If they parrot your words back to you, they may not have understood."
- Notes: Best primary support for the yes/no vs open-question contrast. Two design points: (1) AHRQ's teach-back includes re-teaching ("Clarify and check again"); Samajh deliberately does not explain, so it is a teach-back-style **comprehension check** (assessment only), not the full intervention. (2) The per-product questions in `DESIGN.md` step 4 ("Is this insurance, FD or something else?", "Was it required for the loan?") are closed-set probes. Only step 3 (open recall) is teach-back in AHRQ's sense. E1 should be able to separate them.

### C3.2 Schillinger et al., Arch Intern Med 2003
- Status: verified
- Corrected wording: an observational study showing an association, not a trial.
- Source: `teachback/pubmed-schillinger-2003-closing-the-loop.txt` | https://pubmed.ncbi.nlm.nih.gov/12523921/ | doi 10.1001/archinte.163.1.83
- Quote: "Physicians assessed recall and comprehension of any new concept in 12 (20%) of 61 visits and for 15 (12%) of 124 new concepts." "Patients whose physicians assessed recall or comprehension were more likely to have hemoglobin A(1c) levels below the mean (< or = 8.6%) vs patients whose physicians did not (odds ratio, 8.96; 95% confidence interval, 1.1-74.9)" "physicians' application of the interactive communication strategy (odds ratio, 15.15; 95% confidence interval, 2.07-110.78)" (abstract)
- Notes: Audiotapes of 74 English-speaking diabetes patients with low literacy, 38 physicians; the behaviour occurred in 12 visits; intervals are very wide; the outcome is glycaemic control. It shows clinicians rarely check comprehension (the gap), not that teach-back works.

### C3.3 Ha Dinh et al., JBI Database Syst Rev Implement Rep 2016
- Status: verified
- Source: `teachback/pubmed-ha-dinh-2016-teach-back-systematic-review.txt` | https://pubmed.ncbi.nlm.nih.gov/26878928/
- Quote: "Of the 21 articles retrieved in full, 12 on the use of the teach-back method met the inclusion criteria and were selected for analysis." "Overall, the teach-back method showed positive effects in a wide range of health care outcomes although these were not always statistically significant." "There was limited evidence on improvement in quality of life or disease related knowledge retention."
- Notes: 12 heterogeneous studies, no meta-analysis, chronic-disease education.

### C3.4 Talevski et al., PLoS ONE 2020
- Status: verified
- Source: `teachback/pubmed-talevski-2020-teach-back-systematic-review.txt`; full text `pmc-talevski-2020-teach-back-plos-one-fulltext.txt` (PMC7156054) | https://pubmed.ncbi.nlm.nih.gov/32287296/
- Quote: "Use of teach-back proved effective in 19 of the 20 studies, ranging from learning-related outcomes (e.g. knowledge recall and retention) to objective health-related outcomes (e.g. hospital re-admissions, quality of life)." Limits: "most learning-related outcomes were measured immediately post-intervention; therefore, research demonstrating that teach-back has long-term effects on patient knowledge and recall is warranted." "Searches were limited to published studies, subjecting this review to the possibility of publication bias." "Additionally, given the heterogeneity of outcome measures, it was not possible to conduct a meta-analysis."
- Notes: 20 studies (4 high, 9 moderate, 7 weak quality), all clinical. A 95% positive rate suggests publication bias; read with C3.6.

### C3.5 Yen and Leasure, Fed Pract 2019
- Status: verified (the abstract is one sentence; full-text page saved)
- Source: `teachback/pubmed-yen-leasure-2019-teach-back.txt`; `pmc-yen-leasure-2019-teach-back-fed-pract-page.html` | https://pubmed.ncbi.nlm.nih.gov/31258322/ (PMC6590951)
- Quote: "A review of the literature on the teach-back method of education suggests that the technique may be beneficial in reinforcing patient education." "Most participants in the reviewed studies improved their disease knowledge with teach-back, though the evidence regarding improved health care knowledge retention was limited."
- Notes: Small narrative review. Prefer Talevski and Vick.

### C3.6 Vick et al., J Gen Intern Med, Sept 2026 (newest; most cautious)
- Status: verified
- Source: `teachback/pubmed-vick-2026-teach-back-meta-analysis.txt` | https://pubmed.ncbi.nlm.nih.gov/42693371/ | doi 10.1007/s11606-026-10678-y
- Quote: "Our systematic review included 18 randomized controlled trials (RCTs) involving 1985 participants. Across 9 RCTs assessing knowledge acquisition, conceptual inconsistencies precluded meta-analysis. Overall, there was no clear pattern of the effect of teach-back on knowledge (very low COE)." "we did not identify a clear benefit of teach-back on knowledge acquisition but did find evidence that teach-back improves self-efficacy and self-reported, short-term adherence to health behaviors."
- Notes: Self-efficacy SMD 2.40 (95% CI 0.37-4.44, very low certainty); adherence SMD 1.04 (0.45-1.64, low certainty). A sceptical judge will cite this. Samajh's claim is an assessment claim ("an open question exposes misunderstanding a yes/no question misses"), not "teach-back improves knowledge"; E1 measures it directly.

### C3.7 Teach-back by telephone
- Status: verified (studies exist); evidence that it works by phone: weak
- Corrected wording: "Teach-back has been tested in a national telephone helpline (one stepped-wedge RCT, human nurses, health information) that found no independent effect on its primary outcome. Telehealth reviews are small and of moderate quality. There is no study of teach-back by an automated voice."
- Source: `teachback/pubmed-morony-2018-teach-back-telephone-helpline-stepped-wedge-rct.txt` (https://pubmed.ncbi.nlm.nih.gov/30379942/); `pubmed-morony-2017-experiences-teach-back-telephone-health-service.txt` (31294263); `pubmed-albertson-2026-teach-back-telehealth-review.txt` (41455447); `pubmed-zangouei-2025-teach-back-telephone-followup-rct.txt` (40457369)
- Quote: Morony 2018: "Ratings on the primary outcome increased over time (OR 1.17, CI 1.01 to 1.32, p = 0.03) but no independent Teach-Back effect was observed." "Teach-Back appears to benefit telephone health service users with inadequate health literacy, but the extent of this is unclear due to smaller numbers of lower literacy participants." Morony 2017 (qualitative): "Teach-Back is a simple communication technique that can be used in a consumer telehealth service to confirm caller understanding and actions to take" Albertson 2026: "Overall evidence quality was moderate, with common limitations including small sample sizes and brief follow-up periods."
- Notes: Morony 2018: 637 callers to an Australian helpline, 15 nurses, caller self-reported "sufficient information"; trends for inadequate literacy at p = 0.06. Zangouei 2025 is in-person teach-back with phone follow-up, not teach-back by phone. Nothing tests an automated agent, Indian languages or 8 kHz lines.

### C3.8 Teach-back in informed consent
- Status: verified
- Source: `teachback/pubmed-fink-2010-repeat-back-surgical-informed-consent-rct.txt` (https://pubmed.ncbi.nlm.nih.gov/20562609/); `pubmed-glaser-2020-informed-consent-interventions-review.txt` (31948345); `pubmed-tamariz-2013-low-literacy-consent-review.txt` (22782275)
- Quote: Fink 2010 RCT (575 patients): "The mean comprehension score was significantly higher in the RB group (71.4%) versus the no RB group (68.2%, P = 0.03)"; "providers spent 2.6 minutes longer". Glaser 2020: "100% (3/3) of verbal discussion with test/feedback or teach-back interventions". Tamariz 2013: "The evidence supporting interventions to improve the informed consent process in low literacy populations is extremely limited."
- Notes: Nearest health analogue to "did the customer understand what they agreed to". Effects are modest (3.2 points) and Glaser's 3 of 3 rests on three interventions. All medical settings.

### C3.9 Teach-back or comprehension checks in finance
- Status: verified (documents exist); no teach-back study in finance found (unverifiable negative)
- Corrected wording: "We found no published trial of teach-back for loan, insurance or microfinance sales. The nearest evidence is regulator-published practice examples of post-sale comprehension calls, surveys showing borrowers know instalments but not interest, and an RCT showing low recall of insurance details after a loan-linked sale."
- Source: `teachback/fca-consumer-understanding-good-practice-areas-for-improvement-2026-03.html` (https://www.fca.org.uk/publications/good-and-poor-practice/consumer-understanding-good-practice-areas-improvement, "Published: 13/03/2026"); `asic-rep-632-disclosure-why-it-shouldnt-be-the-default-2019.pdf`; `tiwari-2008-how-do-microfinance-clients-understand-their-loans.pdf`; `cgap-responsible-bundling-of-microfinance-services-page.html` / `cgap-2016-...-working-paper.pdf`
- Quote: FCA (UK): "A smaller firm carried out post-sale comprehension calls using a short questionnaire to confirm that customers understood key aspects of the product, including monthly payments, term length, and what to do if they fell behind." "Testing was mostly phone-based and involved staff asking customers to read back key elements of their product with policy documents in hand." "Good practice includes testing communications in a proportionate way, using methods such as short surveys, comprehension checks, A/B testing or customer callbacks." ASIC/AFM REP 632 (2019, p13, consumer credit insurance sold with loans, Australia): "Yet, despite disclosure, many consumers who have CCI have only a shallow knowledge of the policy, and others are not even aware they have it." "Some consumers were led to believe it was mandatory" IFMR CMF (Tiwari et al., Oct 2008, India): "small borrowers are able to identify the size and duration of the loan and their weekly instalment on their loan. However, they know very little about the interest rate and total interest expense on the loan." CGAP (Zimmerman et al., Mar 2016, Colombia RCT): "most clients understood at the time of the offer the product features they needed to make an informed purchase decision, later survey data reveal low recall of product information"
- Notes: The FCA examples are anecdotes: no sample sizes or error rates. One firm used "internal target of at least 80% correct recall of key points", a precedent for a measured threshold. The FCA review is a regulator accepting callbacks and comprehension checks as evidence of understanding, which supports the idea behind 85Y but is UK evidence. Tiwari data are 2008 microfinance.

### C3.10 Wording the team can honestly use
- Status: recommendation
- Use: (1) "Teach-back means asking a person to explain, in their own words, what they were told. Health-literacy guidance (AHRQ) says yes/no questions such as 'Do you understand?' are not teach-back, because people answer yes whether they understand or not." (2) "Teach-back is well studied in healthcare; reviews report benefits for knowledge, self-efficacy and adherence, though the latest systematic review (2026) found no clear pattern of effect on knowledge and rated that evidence as very low certainty." (3) "We found no study of teach-back for loan or insurance products, and none of teach-back by an automated voice. Samajh tests it directly: E1 compares what a teach-back call and a yes/no call catch on the same scenarios." (4) "The UK regulator's 2026 review lists post-sale comprehension calls and customer call-backs as good practice for checking understanding."
- Do not say: "proven to improve understanding of financial products", "clinically validated", "evidence-based for phone or voice AI", "improves comprehension" (Vick 2026 finds no clear knowledge effect), "Samajh is a teach-back intervention" (it assesses, it does not re-teach).

---

## C4. Data on loan-bundled insurance prevalence or complaints in India

### C4.1 "We found no data on how common loan-bundled insurance is"
- Claim as worded: "we found no data on how common loan-bundled insurance is" (`DESIGN.md` line 175); "any mis-selling prevalence rate" is on the can't-say list (`DESIGN.md` line 166)
- Status: unverifiable (negative); the ban stands
- Corrected wording: "No regulator or survey we found reports how many loans carry bundled or forced insurance. The numbers that exist count complaints, not borrowers or loans, and none separates loan-linked insurance from other mis-selling."
- Notes: Parliament was asked directly. Lok Sabha Unstarred Q.1257 (27 Jul 2026) asked whether the Government "has reviewed the practice of banks and housing finance companies requiring borrowers to purchase investment products or maintain deposits while sanctioning home loans"; the answer describes RBI rules and gives no figure (`prevalence/loksabha-188-AU1257.pdf`, pp1-2).

### C4.2 IRDAI: unfair-business-practice (UFBP) grievances against life insurers
- Claim as worded: "unfair-practice complaints rose from 23,335 to 26,667 (FY24 to FY25)" (`IDEAS-HILLCLIMB.md` line 47)
- Status: verified
- Corrected wording: "IRDAI's Annual Report 2024-25 (Table II.16) records UFBP grievances against life insurers rising from 23,335 (2023-24) to 26,667 (2024-25), 22.14% of life-insurer grievances (19.33% the year before). UFBP includes mis-selling but is not the same thing." (A hackathon page calls the 26,667 "mis-selling grievances"; the report's heading is UFBP.)
- Source: `prevalence/irdai-annual-report-2024-25.pdf` | https://irdai.gov.in/document-detail?documentId=8375620
- Quote: "Total no. of UFBP grievances reported 23,335 26,667" and "Share of UFBP grievances to total grievances 19.33% 22.14%" (Table II.16, PDF p314, report p.82). "the total number of grievances registered under UFBP (Unfair Business Practices) have increased from 23,335 in 2023-24 to 26,667 in 2024-25." (para II.6.5). "Total no. of Grievances reported against Life insurers 1,20,726 1,20,429". Parliament: "the total number of grievances related to Unfair Business Practices (UFBP), including mis-selling, reported during the FY 2024-25 was 26,667." (Lok Sabha Unstarred Q.1203, 27 Jul 2026, p2)
- Notes: Outcomes of the 26,495 resolved: 9,613 in favour, 1,797 partly in favour, 15,085 against (about 36% fully in favour). FY2025-26 life grievances were 1,19,027 (Q.1203, p1); no FY26 UFBP figure was given. 26,667 against 270.22 lakh new individual policies in 2024-25 (para I.2.2.6) is about 0.10 per 100 (the FY2019-20 report computed 0.15 on the same basis), but the numerator can relate to older policies; do not call it a mis-selling rate. IRDAI's consultation paper: "Unfair business practices have been a leading category of customer complaints." (para 135, p60)

### C4.3 IRDAI: complaints by channel; credit-life volumes
- Claim as worded: requested
- Status: verified for the old channel data; unverifiable for current channel complaints and credit-life volume
- Corrected wording: "The latest IRDAI annual report gives no complaint breakdown by channel and no credit-life volume. The last channel breakdown of mis-selling complaints I found (private life insurers, 2017-18 to 2019-20) shows banks as the largest channel."
- Source: `prevalence/irdai-annual-report-2019-20-english.pdf` (https://irdai.gov.in/document-detail?documentId=979747), Chart I.18 (PDF p73, report p.46; read from `rendered-irdai-annual-report-2019-20-pdf-p73-charts-I16-I17-I18.png`); `irdai-annual-report-2024-25.pdf` Table II.10; `secondary-businessstandard-2021-02-banks-brokers-most-complaints-mis-selling.html`
- Quote: "The analysis of mis-selling complaints data of private life insurers shows that number of mis-selling complaints have reduced from 47,503 in 2017-18 to 35,178 in 2019-20." (para I.5.1.18). Chart I.18, Banks: 15,140 (2017-18), 12,334 (2018-19), 9,631 (2019-20); Brokers: 12,084, 10,988, 9,911 (read from the chart). "Complaints categorised under unfair trade practices include misrepresentation of terms, conditions and benefits available under the life insurance products, false advertising or representation of a product, bundled with other products free prize or gift offers, deceptive pricing etc." (para I.5.1.14). "In 2018-19, banks received more than 12,000 mis-selling complaints" (Business Standard 2021, secondary)
- Notes: Banks were about 27% of the 35,178 complaints in 2019-20 (9,631), about 29% in 2018-19 and 32% in 2017-18. That is a share of complaints, not of sales, across all bank-sold policies. FY2024-25 channel data are premium shares: "2 Corporate Agents- Banks 49.66 4.13 32.59 21.28 0.10 6.23" (Table II.10, p304), i.e. banks sold 32.59% of industry individual new-business premium and 6.23% of group. Searches of the 2024-25 report for credit life, group credit and loan-linked found only a product-name listing. Press reports (Financial Express, The Ken; paywalled, not retrieved) say group credit-life lives covered fell by roughly 47 to 50 million in FY25; unverified.

### C4.4 RBI Ombudsman annual reports
- Claim as worded: requested
- Status: verified for 2018-19; secondary-only for 2024-25 (PDF not retrieved)
- Corrected wording: "RBI's 2018-19 report is the latest I could read in primary form that counts mis-selling separately: 1,115 mis-selling complaints of 1,95,901 (about 0.57%). RBI's 2024-25 report (posted 1 Dec 2025) shows loans and advances as the largest category (29.25%) per press coverage; I could not read its category table."
- Source: `prevalence/rbi-press-release-annual-report-banking-ombudsman-2018-19-prid48899.html` (https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=48899, Press Release 2019-2020/1444, 17 Dec 2019); `rbi-press-release-annual-report-ombudsman-scheme-2024-25-prid61721.html` (one line, no figures); `secondary-businessstandard-rbi-ombudsman-complaints-fy25.html`; `secondary-tribune-rbi-ombudsman-13-34-lakh-complaints-fy25.html`
- Quote: "The number of complaints pertaining to 'mis-selling' have gone up from 579 complaints in 2017-18 to 1,115 in 2018-19, an increase of 92.57 per cent;" "The complaints received at OBOs rose by 32,311 taking the total to 1,95,901 complaints in 2018-19" (RBI). "those related to loans and advances were the highest at 29.25 per cent in FY25." (Business Standard, secondary). "13.34 Lakh complaints in FY25" (Tribune, secondary)
- Notes: The 2018-19 "mis-selling" ground covers banks selling insurance, mutual funds and other third-party products; it is not limited to loans. No mis-selling, para-banking or levy-of-charges counts for 2024-25 were readable. Secondary claims that para-banking complaints fell 24.16% are unverified. The 2025-26 report is not out.

### C4.5 Insurance Ombudsman (Council for Insurance Ombudsmen) statistics, 2024-25
- Claim as worded: requested
- Status: verified
- Corrected wording: "Insurance Ombudsman offices received 53,102 complaints in 2024-25 and disposed of 48,898. About 15,400 were life complaints, and under Rule 13(1)(d) ('Misrepresentation of policy terms and conditions') 7,491 of the 12,631 entertainable life complaints (59%) fell in the category nearest to mis-selling."
- Source: `prevalence/cio-annual-report-2024-25.pdf` (image-only; OCR in `cio-annual-report-2024-25.ocr.txt`; tables read by eye from `rendered-cio-annual-report-2024-25-pdf-p66/p68/p78-*.png`) | https://cioins.co.in/annualreports/AnnualReport2024-2025.pdf
- Quote: "During the year 2024-25 the Offices of Insurance Ombudsman received a total of 53102 complaints out of which 48898 were disposed of." (Preface, PDF p7, OCR). Statement L8, Life Insurance (PDF p68, report p.59): Total (A+B) 15,342; entertainable total 12,631; Rule 13(1)(d) "Misrepresentation of policy terms and conditions at any time in the policy document or policy contract" 7,491 (column sums check); Rule 13(1)(b) (claim repudiation) 1,986. Chart p78 (report p.69): Life 15,431 received in 2024-25 (16,252 in 2023-24; 19,786 in 2022-23); Health 32,655; General 5,016 (sum 53,102).
- Notes: The CIO label is a rule number, not "mis-selling"; do not call 7,491 a mis-selling count. Internal totals differ slightly (life 15,342 in L8 vs 15,431 in the chart; all-stream 52,766 in L7 vs 53,102). Cafemutual and AngelOne reported "17,237 life insurance complaints" for FY25; I did not retrieve those pieces and the number does not match the report, so quote the report.

### C4.6 Government and regulator statements on forced or bundled insurance with loans
- Claim as worded: requested
- Status: verified for the primary documents; secondary-only for the news items
- Corrected wording: "The Government, supervisors and IRDAI have said, in documents and press interviews, that insurance is being pushed with loans; none has published a count."
- Source: `prevalence/nhb-advisory-mis-selling-insurance-housing-loans-2024-12-10.pdf` (primary); `loksabha-188-AU1203.pdf`, `loksabha-188-AU1257.pdf` (primary); `irdai-consultation-paper-distribution-reforms-part1-2026-09.pdf`; `secondary-businessstandard-2024-03-17-dfs-secy-banks-asked-to-check-mis-selling.html`; `secondary-cafemutual-fm-irdai-chief-concerns-mis-selling-by-banks.html`
- Quote: NHB advisory to HFCs, 10 Dec 2024: "During the Supervisory Inspections of HFCs, Bank had observed that there are cases of mis-selling of insurance loans along with the Individual housing loans, complaints on multiple kinds of policies bundled with housing loan/s and borrowers not being aware of the terms and conditions of the policies & the tenure of the insurance in some cases is also less than that of the tenure of the loan." "It was observed that consent of customer while availing insurance was also not taken in some cases. Even if the consent of the customer was taken it was observed that the premium amount/term was not mentioned in the consent form." (paras 1, 5). Business Standard/PTI, 17 Mar 2024 (secondary): the DFS "regularly gets complaints that fraudulent and unethical practices are being adopted by banks and life insurance companies for procuring policies from the bank customers" (Financial Services Secretary to PTI); in the report's own words "Insurance products are pushed when customers go to seek any kind of loan or buy a term deposit." Cafemutual, 20 Nov 2024 (secondary, SBI Banking & Economics Conclave): the Finance Minister and the IRDAI Chairperson "expressed concerns over mis-selling of insurance policies by banks"; the IRDAI Chairperson said banks "should not mis-sell or force-sell insurance policies". IRDAI consultation paper (Sept 2026, p65): "NBFCs and banks financing motor vehicle purchase and insisting on compulsory bundling of loan and insurance still get 16% commission while the borrowers remaining unaware." (assertion on motor loans; no data). Lok Sabha Q.1257: "Banks are also directed to not resort to compulsory bundling of any product, including, inter alia, investment products, insurance products and deposits, with any of its own product/service, including, inter alia, home loans."
- Notes: The NHB advisory is the strongest primary statement: from supervisory inspections, with patterns ("majority of the HFCs" with life cover shorter than the loan; consent not taken "in some cases") but no counts. It matches the scenarios Samajh tests (cover shorter than the loan; premium or term absent from the consent). I did not find the DFS advisory text itself, nor any Parliament answer with a bundling-complaint count.

### C4.7 Surveys (secondary data)
- Claim as worded: requested (LocalCircles, Dvara, others)
- Status: unverifiable (negative)
- Corrected wording: "I found no survey that puts a number on borrowers made to buy insurance with a loan."
- Notes: Three targeted searches found none. Press pieces (Mint, Nov 2025; Business Standard) describe the practice without a rate; not saved. Cite no survey figure.

### C4.8 What can honestly be said about prevalence
- Status: recommendation
- Use: (1) "IRDAI recorded 26,667 unfair-business-practice grievances against life insurers in 2024-25, up from 23,335 and 22% of all life-insurer grievances; the category includes mis-selling." (2) "In 2018-19, RBI's banking ombudsmen received 1,115 mis-selling complaints, about 0.6% of all complaints." (3) "The National Housing Bank wrote to housing finance companies in December 2024 after inspections found insurance bundled with housing loans, cover shorter than the loan, and consent forms without the premium or term." (4) "No official source we found says how many borrowers are sold insurance with their loan, or how many are mis-sold."
- Do not say: any percentage of loans with bundled insurance; "X% of borrowers are mis-sold"; "26,667 loan-insurance complaints"; that complaints measure prevalence.

---

## Could not retrieve
| URL | What was tried | Result |
|---|---|---|
| `https://rbidocs.rbi.org.in/rdocs/Publications/PDFs/OMBUDSMANSCHEME0112256FF61F650D4945CFAD6C822B3EF3481F.PDF` (RBI Ombudsman Annual Report 2024-25) | curl; WebFetch | HTTP 200 but a CAPTCHA page. Not bypassed. |
| Wayback copy of the same PDF (`web.archive.org/web/20260711091259id_/...`) | curl, twice | HTTP 429 "suspected abusive bot traffic". Not retried. |
| IRDAI-hosted main text of circular 274/11/2020 (12 Nov 2020) | site search by reference and title; probed neighbouring IDs; fetched extensions and Annexure 1 | Only the Annexure and later circulars are on irdai.gov.in. Quote is from a TaxGuru copy (`secondary-only`). `compfie.aparajitha.com/.../16112020_FCC_03.pdf` returned HTTP 504. |
| Full PDFs of the Corporate Agents Regulations 2015 and Web Aggregators Regulations 2017 | fetched | Retrieved but only page excerpts and full extracted text are stored (30 and 38 MB); full-file hashes are in `INDEX.md`. |
| FTC "Improving Consumer Mortgage Disclosures" (2007) | ftc.gov and UNT archive paths | HTTP 404 / HTML. A search summary attributed "three-quarters did not recognise an optional credit-insurance charge" to this kind of study; unverified, not used. |
| `valueresearchonline.com/stories/200278/how-banks-mis-sell-insurance/` | curl | HTTP 403 |
| BusinessLine via pressreader (RBI and IRDAI lens on SFBs forcing insurance) | curl | Empty page |
| `reverieinc.com/?p=1286311` | curl | Connection failed (000) |
| Financial Express "MFI stress erases life cover for 50 mn"; The Ken "47 million lost life insurance" | search result only | Paywalled |
| `eparlib.nic.in` Lok Sabha PDFs; `rsdebate.nic.in` PQ 259 (14 Mar 2023) | curl | Connection failed / HTML. Replaced by sansad.in answers. |
| LocalCircles survey on bundled loan insurance | three searches | None found |
| Lok Sabha answer of 2 Feb 2026 on insurance mis-selling | not located on sansad.in | Not retrieved |
| Bank tender portals (GeM, bank e-procurement) | aggregator search only | Not searchable with this tool |
| `references/claims/findings-C.md` | Write tool | Refused by the harness for subagents; content supplied in this message instead |

## Product implications (most important first)
1. **Drop "we found no vendor marketing an 85Y understanding callback."** SquadStack (21 Oct 2026) calls an AI post-disbursal call an "RBI-required welcome and mis-sell check"; Edesy (10 Sep 2026) markets welcome calls that "confirm what the customer understood". Use the C2.1 wording and state the difference: teach-back not yes/no, comparison with the lender's records, flags with evidence, a measured evaluation. BFSI voice-industry judges will know these vendors.
2. **Fix the PIVC sentence.** Cite IRDAI/Life/Misc/CIR/116/05/2020 (12 May 2020), "encouraged", superseded in 2024. Add that IRDAI's 10 Sep 2026 order against Canara HSBC Life (Rs 1 crore) calls a PIVC "a critical regulatory safeguard". Keep the ban on "PIVC is mandatory". The failure in that order (a caller telling the customer he would receive an annuity that goes to his daughter) is exactly the mismatch Samajh's records comparison catches.
3. **Use the older IRDAI verification-call rules as precedent**: sampled post-sale calls "to ascertain whether the client has understood the benefits, features and disclosures" (3% of distance-marketing policyholders a month, standard script, records kept 3 years). Say current force is unconfirmed and they cover distance-marketing sales only.
4. **Free-look in the script.** 30 days from receipt of the policy document (Reg 20, 2024). Credit-life with loans is usually group cover and the borrower is a member, not the policyholder; I found no text giving members a free-look right. Check with compliance before the script says "cancel within 30 days" for loan-linked cover; use it only for individual policies in scenarios.
5. **Teach-back wording.** Use C3.10. Newest systematic review: no clear pattern of effect on knowledge (the knowledge trials could not be pooled); one telephone RCT: null primary outcome; nothing in finance or with an automated voice. The design's per-product questions are closed probes and Samajh does not re-teach, so call it a "teach-back-style comprehension check".
6. **Prevalence stays off the table, but quotable facts exist.** IRDAI's 26,667 UFBP grievances (22.14% of life-insurer grievances in 2024-25), RBI's 1,115 mis-selling complaints in 2018-19, the Insurance Ombudsman's 7,491 Rule 13(1)(d) complaints (59% of entertainable life complaints, 2024-25), and the NHB's December 2024 advisory are primary and measure complaints or inspection findings, not prevalence. Banks were about 27% of private-insurer mis-selling complaints in 2019-20, across all bank-sold life policies.
7. **Cite IRDAI's feedback clause carefully.** Master Circular para 7.4 and Reg 21(2) are the insurance counterparts of 85Y but set no 30-day window and no call-back. Do not say IRDAI requires a feedback call.
8. **Mark every Sept to Nov 2026 IRDAI consultation item as a proposal**: the distribution-reforms paper (bundling ban, Box 5) closed on 31 Oct 2026 after an extension. The Canara item is an order, not a rule.
9. **Group E check:** Vinod Kothari's summary of the DSA/DMA code of conduct lists "No Post-Sale Solicitation: Avoid calls regarding sold products; redirect customers to RE customer service." Confirm it covers sales agents, not the bank's own independent feedback calls.
