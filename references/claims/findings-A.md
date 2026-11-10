# Findings A: RBI directions cited in DESIGN.md section 2

Research date 2026-11-10. Sources in `sources/A/`, checksums in `sources/A/INDEX.md`.

**How sources were obtained.** RBI publishes each direction on a `rbi.org.in` notification page (`NotificationUser.aspx?Id=<n>&Mode=0`) that carries the full text as HTML, plus a PDF link on `rbidocs.rbi.org.in`. The `rbidocs` PDFs return a human-verification page. I treated the `rbi.org.in` page text as primary (RBI's own publication under the circular number). For commercial banks I also hold the PDF (web.archive.org snapshot 2026-08-28, 15 pages). A whitespace-insensitive comparison showed 85G, 85V, 85W, 85X, 85Y, 85Z, 85N, 85P, 85U and 4(20A) read the same in PDF and HTML. The only difference is a page-break marker inside 85Z. Quotes marked `>` were extracted by script. A leading `“` or trailing `”` (the amendment's own quotation marks) is dropped.

File short names: **CB** = `rbi-page-rbi-2026-27-115-commercial-banks-rbc-second-amendment.txt`; **NBFC** = `...-123-nbfc-rbc-second-amendment.txt`; **HFC** = `...-124-hfc-second-amendment.txt`; **PR-0615** = `rbi-press-release-62938.txt`.

### A1 Title of the instrument
- Claim as worded: "RBI's Responsible Business Conduct (Second Amendment) Directions 2026" (DESIGN.md line 22); "RBI RBC Second Amendment Directions 2026" (IDEAS-HILLCLIMB.md line 95)
- Status: wrong
- Corrected wording: There is no single instrument with that name. On 15 Jun 2026 RBI issued ten entity-specific Amendment Directions, announced in one press release titled "RBI Issues Amendment Directions on ‘Advertising, Marketing and Sale of Financial Products and Services by Regulated Entities’". Commercial banks: "Reserve Bank of India (Commercial Banks - Responsible Business Conduct) Second Amendment Directions, 2026". NBFCs: "Reserve Bank of India (Non-Banking Financial Companies – Responsible Business Conduct) Second Amendment Directions, 2026". Payments banks are "Amendment Directions" (no "Second"). HFCs are "Reserve Bank of India (Housing Finance Companies) Second Amendment Directions, 2026" (no "Responsible Business Conduct"). Safe short form: "RBI's June 2026 Amendment Directions on Advertising, Marketing and Sale of Financial Products and Services".
- Source: sources/A/rbi-press-release-62938.txt; CB; NBFC; HFC | https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=62938 | retrieved 2026-11-10
- Quote: "RBI Issues Amendment Directions on ‘Advertising, Marketing and Sale of Financial Products and Services by Regulated Entities’" (press release title). Title lines: "Reserve Bank of India (Commercial Banks - Responsible Business Conduct) Second Amendment Directions, 2026" (CB); "Reserve Bank of India (Non-Banking Financial Companies – Responsible Business Conduct) Second Amendment Directions, 2026" (NBFC); "Reserve Bank of India (Housing Finance Companies) Second Amendment Directions, 2026" (HFC).
- Notes: the amended principal Directions are "Reserve Bank of India (Commercial Banks - Responsible Business Conduct) Directions, 2025" (RBI/2025-26/170, DOR.MCS.REC.No.89/01-01-032/2025-26, 28 Nov 2025) and the NBFC equivalent (RBI/DOR/2025-26/362, DOR.MCS.REC.No.281/01-01-039/2025-26, 28 Nov 2025). The background in the brief is right.

### A2 Circular numbers and DOR references
- Claim as worded: "Commercial banks: RBI/2026-27/115, para 85Y. NBFCs: RBI/2026-27/123, para 101Y." (DESIGN.md line 22)
- Status: verified
- Corrected wording: none needed. Add the DOR reference. Banks: RBI/2026-27/115, DOR.MCS.REC.No.94/01-01-032/2026-27. NBFCs: RBI/2026-27/123, DOR.MCS.REC.No.102/01-01-039/2026-27. HFCs: RBI/2026-27/124, DOR.MCS.REC.No.103/01-01-039/2026-27.
- Source: CB; NBFC | https://rbi.org.in/Scripts/NotificationUser.aspx?Id=13485&Mode=0 and Id=13493 | retrieved 2026-11-10
- Quote: "RBI/2026-27/115 DOR.MCS.REC.No.94/01-01-032/2026-27 June 15, 2026" (CB header); "RBI/2026-27/123 DOR.MCS.REC.No.102/01-01-039/2026-27 June 15, 2026" (NBFC header)
- Notes: the companion Undertaking of Financial Services Third Amendment for banks has a different number style (RBI/DoR/2026-27/125).

### A3 Issue date
- Claim as worded: "issued June 2026 (hill-climb notes say 15 Jun 2026)"; "RBI/2026-27/115 (15 Jun 2026)" (IDEAS-HILLCLIMB.md line 97); "It was issued in June 2026" (DESIGN.md line 170)
- Status: verified
- Corrected wording: none needed. Issued 15 June 2026; press release 2026-2027/460 of the same date.
- Source: sources/A/rbi-press-release-62938.txt | retrieved 2026-11-10
- Quote: "Date : Jun 15, 2026"; "Accordingly, the Reserve Bank has today issued the following Amendment Directions, which shall come into effect from January 1, 2027." (PR-0615 para 2)
- Notes: none.

### A4 Effective date
- Claim as worded: "take effect on **1 Jan 2027**" (DESIGN.md line 22)
- Status: verified
- Corrected wording: none needed. The directions contain no transitional clause, so they do not say whether the 30-day feedback applies to sales made before 1 Jan 2027. Do not claim either way.
- Source: CB; NBFC; HFC | retrieved 2026-11-10
- Quote: CB para 3(2): "(2) These Directions shall come into effect from January 1, 2027." NBFC para 3(2): the same sentence. HFC para 3(2): "(2) These Directions shall come into effect on January 1, 2027."
- Notes: the same sentence is in all ten directions. The principal CB Directions say (para 2) "These Directions shall come into effect immediately upon issuance, unless indicated otherwise", so 2027 is an override for this amendment.

### A5 Which document covers which entity, and the feedback paragraph in each
- Claim as worded: "Equivalents claimed: SFB 85Y, payments banks 42Y, local area banks 17Y, UCB 65Y, rural co-op 79Y, RRB 136Y, AIFI 32Y." (task brief; DESIGN.md line 22; IDEAS-HILLCLIMB.md line 107)
- Status: verified
- Corrected wording: none needed. Sub-paragraph letters are identical across entities (G consent, V bundling, W funding, X dark patterns, Y feedback, Z refund). Only the numeric prefix changes. The mis-selling definition is 4(20A) for banks and 6(9A) for NBFCs.

| Entity | Circular | DOR ref | Exact title | Page Id | Feedback para |
|---|---|---|---|---|---|
| Commercial banks (not SFB/PB/RRB/LAB) | RBI/2026-27/115 | DOR.MCS.REC.No.94/01-01-032/2026-27 | Reserve Bank of India (Commercial Banks - Responsible Business Conduct) Second Amendment Directions, 2026 | 13485 | 85Y |
| Small finance banks | RBI/2026-27/116 | DOR.MCS.REC.No.95/01-01-033/2026-27 | Reserve Bank of India (Small Finance Banks - Responsible Business Conduct) Second Amendment Directions, 2026 | 13486 | 85Y |
| Payments banks | RBI/2026-27/117 | DOR.MCS.REC.No.96/01-01-034/2026-27 | Reserve Bank of India (Payments Banks - Responsible Business Conduct) Amendment Directions, 2026 | 13487 | 42Y |
| Local area banks | RBI/2026-27/118 | DOR.MCS.REC.No.97/01-01-035/2026-27 | Reserve Bank of India (Local Area Banks - Responsible Business Conduct) Second Amendment Directions, 2026 | 13488 | 17Y |
| Regional rural banks | RBI/2026-27/119 | DOR.MCS.REC.No.98/01-01-036/2026-27 | Reserve Bank of India (Regional Rural Banks - Responsible Business Conduct) Second Amendment Directions, 2026 | 13489 | 136Y |
| Urban co-operative banks | RBI/2026-27/120 | DOR.MCS.REC.No.99/01-01-037/2026-27 | Reserve Bank of India (Urban Co-operative Banks - Responsible Business Conduct) Second Amendment Directions, 2026 | 13490 | 65Y |
| Rural co-operative banks | RBI/2026-27/121 | DOR.MCS.REC.No.100/01-01-038/2026-27 | Reserve Bank of India (Rural Co-operative Banks - Responsible Business Conduct) Second Amendment Directions, 2026 | 13491 | 79Y |
| All India financial institutions | RBI/2026-27/122 | DOR.MCS.REC.No.101/01-01-040/2026-27 | Reserve Bank of India (All India Financial Institutions - Responsible Business Conduct) Second Amendment Directions, 2026 | 13492 | 32Y |
| NBFCs (exclusions in A6) | RBI/2026-27/123 | DOR.MCS.REC.No.102/01-01-039/2026-27 | Reserve Bank of India (Non-Banking Financial Companies – Responsible Business Conduct) Second Amendment Directions, 2026 | 13493 | 101Y (Chapter IIIA, 101A to 101ZA) |
| Housing finance companies | RBI/2026-27/124 | DOR.MCS.REC.No.103/01-01-039/2026-27 | Reserve Bank of India (Housing Finance Companies) Second Amendment Directions, 2026 | 13494 | 157A, pointing to NBFC 101A to 101ZA |

- Source: sources/A/rbi-page-rbi-2026-27-116-...-122-...txt, NBFC, HFC | https://rbi.org.in/Scripts/NotificationUser.aspx?Id=13486&Mode=0 (Ids 13486 to 13494) | retrieved 2026-11-10
- Quote: each entity's feedback paragraph follows one template. Small finance banks, for example: "85Y. An SFB shall establish a mechanism to seek feedback from customers, within a period of 30 days from the sale of any financial product / service" (the other six read the same with "A PB", "An LAB", "An RRB", "A UCB", "An RCB" or "An AIFI" and the paragraph numbers in the table).
- Notes: the chapter is one template reproduced per entity. Annex lettering differs (bank Annex IIA, NBFC Annex III, LAB Annex AI, AIFI Annex I).

### A6 "It applies to every RBI-regulated lender from 1 Jan 2027"
- Claim as worded: "it applies to every RBI-regulated lender from 1 Jan 2027" (DESIGN.md line 164)
- Status: wrong (right in substance, wrong in the universal quantifier)
- Corrected wording: "It applies to commercial banks, small finance banks, payments banks, local area banks, regional rural banks, urban and rural co-operative banks, All India Financial Institutions, NBFCs and HFCs, each under its own direction, from 1 January 2027. NBFC coverage excludes Core Investment Companies, NBFC-Account Aggregators, Non-Operative Financial Holding Companies and NBFCs not having any customer interface." Never say "every".
- Source: NBFC | https://rbi.org.in/Scripts/NotificationUser.aspx?Id=13493&Mode=0 | retrieved 2026-11-10
- Quote: NBFC para 1: "...issue comprehensive instructions on advertising, marketing and sale of financial products / services to all NBFCs, excluding Core Investment Companies, NBFC-Account Aggregators, Non-Operative Financial Holding Companies, and NBFCs not having any customer interface, (hereinafter referred to collectively as “NBFCs” and individually as an “NBFC”)..." Para 4(1): "4A. The provisions contained in Chapter IIIA shall be additionally applicable to: (1) NBFC-P2P registered with the RBI under the provisions of the RBI Act, 1934; (2) Mortgage Guarantee Company ...; (3) Standalone Primary Dealer ...". CB para 1: "...to all Commercial Banks (other than Small Finance Banks, Payments Banks, Regional Rural Banks and Local Area Banks)..."
- Notes: payments banks are covered but do not lend. I found no RBI statement that these ten cover every regulated lender. Entities outside the ten (for example credit information companies, asset reconstruction companies) are not researched.

### A7 HFCs "inherit it via para 157A"
- Claim as worded: "HFCs inherit it via para 157A" (DESIGN.md line 22)
- Status: verified
- Corrected wording: "HFCs are covered by para 157A of the HFC Directions, 2025 (Chapter X, Fair Practices Code), inserted by RBI/2026-27/124. It requires an HFC to comply with paragraphs 101A to 101ZA of Chapter IIIA of the NBFC Responsible Business Conduct Directions, 2025. The HFC feedback duty is therefore NBFC para 101Y. An HFC has no 85Y or 101Y text of its own." The amendment also deletes old HFC paragraphs 150 to 157 (A.10 Advertising, Marketing and Sales; A.11 Code of Conduct for DSAs/DMAs).
- Source: HFC | https://rbi.org.in/Scripts/NotificationUser.aspx?Id=13494&Mode=0 | retrieved 2026-11-10
- Quote (para 4(1)): "(1) In Chapter-X on ‘Fair Practices Code’, the sub-sections A.10 Advertising, Marketing and Sales (paragraphs 150 to 154) and A.11 Code of Conduct for DSAs/DMAs (paragraphs 155 to 157) shall be deleted and substituted with a new sub-section as under: “A.11A Advertising, Marketing and Sale of Financial Products / Services by HFCs 157A. An HFC shall ensure compliance with the provisions of paragraphs 101A to 101ZA under Chapter IIIA of Reserve Bank of India (Non-Banking Financial Companies – Responsible Business Conduct) Directions, 2025.”" Scope (para 1): "...to all Non-Banking Financial Companies (NBFCs), including HFCs but excluding Core Investment Companies, NBFC-Account Aggregators, Non-Operative Financial Holding Companies, and NBFCs not having any customer interface..."
- Notes: made under Section 30A of the National Housing Bank Act, 1987. HFC principal: RBI/DoR/2025-26/365, DoR.FIN.REC.284/03-10-119/2025-26, 28 Nov 2025.

### A8 Consolidated principal Directions "as amended"
- Claim as worded: not in DESIGN.md (the brief asks whether RBI publishes consolidated text)
- Status: verified (finding: no consolidated text contains 85A to 85ZA yet)
- Corrected wording: cite "RBI/2026-27/115, para 85Y, inserted into the Commercial Banks - Responsible Business Conduct Directions, 2025 (Chapter IV, after para 85)", not "para 85Y of the Directions". RBI publishes dated consolidated versions, but the current ones predate this amendment and contain none of the new paragraphs.
- Source: sources/A/rbi-page-principal-cb-rbc-directions-2025-updated-2026-10-01.txt; ...-nbfc-...-updated-2026-07-01.txt; ...-hfc-...-updated-2026-10-01.txt | https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=13140&Mode=0 (CB), Id=12942 (NBFC), Id=12939 (HFC) | retrieved 2026-11-10
- Quote: titles "Reserve Bank of India (Commercial Banks - Responsible Business Conduct) Directions, 2025 (Updated as on October 1, 2026)"; "...(Non-Banking Financial Companies – Responsible Business Conduct) Directions, 2025 (Updated as on July 1, 2026)"; "Reserve Bank of India (Housing Finance Companies) Directions, 2025 (Updated as on October 01, 2026)". Insertion point (CB para 4(7)): "In Chapter IV on ‘Customer Guidance and Protection’, the following section and paragraphs shall be inserted after paragraph 85, namely:". Principal para 85 today: "85. A bank shall leverage the technology available with it and the telecom service provider(s) to ensure that charges levied by it for sending SMS alerts to customers are levied on actual usage basis."
- Notes: searches of all three principal texts for "85Y", "101Y", "157A" and "Compulsory bundling" found nothing. "Mis-selling" occurs once in the principal bank text, in an unrelated paragraph on commodity derivatives (para 462). "Financial product / service" is not defined in any of the three. Recheck after 1 Jan 2027.

### A9 The 85Y quote in DESIGN.md
- Claim as worded: the full 85Y quote (DESIGN.md line 24)
- Status: verified (identical)
- Corrected wording: none needed. A script compared DESIGN.md line 24 (702 characters including "85Y. ") with the 85Y line in CB (702 characters): IDENTICAL, zero differences. It also matches the archived PDF text apart from whitespace.
- Source: CB; sources/A/rbi-2026-27-115-commercial-banks-rbc-second-amendment.pdf | https://rbi.org.in/Scripts/NotificationUser.aspx?Id=13485&Mode=0 | retrieved 2026-11-10
- Quote (para 85Y, commercial banks): "85Y. A bank shall establish a mechanism to seek feedback from customers, within a period of 30 days from the sale of any financial product / service to ensure that customers have understood the features of the financial product / service and also the risks associated with such financial product / service. The mechanism may include selection of the customers on a random basis for such feedback through modes such as call-backs or surveys carried out by a department / vertical of the bank not associated with sale of products / services. A half-yearly report on the findings of the feedback shall be prepared and utilised for review of existing policies and features of financial products / services."
- Notes: correct for commercial banks only. For NBFCs cite 101Y. It sits under heading "F.6 Feedback and Compensation to Customers" with 85Z.

### A10 85Y in the NBFC direction and the other entity directions
- Claim as worded: "NBFCs: RBI/2026-27/123, para 101Y" (DESIGN.md line 22)
- Status: verified
- Corrected wording: none needed. Differences from the bank wording are one comma and the entity noun.
- Source: NBFC | https://rbi.org.in/Scripts/NotificationUser.aspx?Id=13493&Mode=0 | retrieved 2026-11-10
- Quote (para 101Y): "101Y. An NBFC shall establish a mechanism to seek feedback from customers, within a period of 30 days from the sale of any financial product / service to ensure that customers have understood the features of the financial product / service and also the risks associated with such financial product / service. The mechanism may include selection of the customers on a random basis for such feedback through modes such as call-backs or surveys carried out by a department / vertical of the NBFC, not associated with sale of products / services. A half-yearly report on the findings of the feedback shall be prepared and utilised for review of existing policies and features of financial products / services."
- Notes: differences found by script after replacing "NBFC" with "bank":
  - 101Y has a comma after "vertical of the NBFC,". 85Y has none. The AIFI and RCB texts also carry that comma. The RRB text says "utilized". No change in meaning.
  - 101G, 101H, 101I, 101N, 101P, 101Q, 101R, 101S, 101T, 101V, 101W, 101X, 101Z and 6(9A) are word-for-word the bank text with "bank" → "NBFC".
  - Immaterial differences: 101U reads "marketing / sale of TPPS" (85U "sale / marketing of TPPS"); 101ZA(1) says "amended from time to time" (85ZA(1) "as amended from time to time"); the bank DSA definition mentions Business Correspondent (BC), the NBFC one does not; a few annex illustrations differ.
  - Only substantive wording difference found in any entity: payments banks 42W reads "shall not indirectly fund" (A17).
  - NBFC definitions are renumbered: Compulsory bundling 6(1A) (bank 4(6A)), Dark pattern 6(2A) (4(10.1A)), DSA/DMA 6(2B) (4(10B)), Explicit consent 6(4A) (4(13A)), Mis-selling 6(9A) (4(20A)), TPPS 6(13) (4(26A)).

### A11 85Y: what is mandatory and what is optional
- Claim as worded: "call-backs or surveys by a non-sales unit, random sampling, plus a half-yearly report" (IDEAS-HILLCLIMB.md line 107)
- Status: verified
- Corrected wording: "85Y requires a mechanism that seeks feedback within 30 days of the sale, to ensure customers have understood the features and risks, and a half-yearly report on the findings that is used to review policies and product features. It says the mechanism *may* include random selection of customers, and gives call-backs and surveys as example modes carried out by a department or vertical not associated with sales." Do not write that random sampling, call-backs or an independent unit are required.
- Source: CB | retrieved 2026-11-10
- Quote: "The mechanism may include selection of the customers on a random basis for such feedback through modes such as call-backs or surveys carried out by a department / vertical of the bank not associated with sale of products / services." (85Y)
- Notes:
  - Mandatory ("shall"): the mechanism; feedback sought within 30 days of the sale; the purpose (customers understand features and risks); the half-yearly report, "utilised for review of existing policies and features".
  - Optional ("may include", "such as"): random selection, call-backs, surveys. The independence wording sits inside the same optional sentence. Treat sales-independence as the expectation but say "as 85Y describes it", not "requires".
  - Not specified: sample size, channel, language, a pass mark for "understood", who receives the report (board, committee, regulator), any individual remediation (that is only in 85Z), what happens if the customer does not answer ("seek").
  - Outsourcing: the text says "by a department / vertical of the bank". A vendor running the calls acts on that department's behalf; 85ZA(3) points to RBI's outsourcing instructions (not researched).
  - "Sale" is not defined, so the "30 days from the sale" start point is undefined.

### A12 Does "sale of any financial product / service" cover the lender's own loan?
- Claim as worded: "Covers own and third-party products." (IDEAS-HILLCLIMB.md line 107)
- Status: verified (the text is quoted; the conclusion is our reading of 85Y with 85A, 85Q and 4(20A), because 85Y itself does not say "own" or "third-party")
- Corrected wording: "85Y applies to the sale of any financial product or service, which on the wording of the same chapter includes the bank's own products such as loans, as well as third-party products such as insurance." Present it as our reading, not an RBI statement.
- Source: CB | retrieved 2026-11-10
- Quote: 85A: "A bank shall put in place a comprehensive policy for advertising, marketing and sale of its own as well as third-party financial products / services, which shall, amongst others, cover aspects related to criteria for determination of suitability and appropriateness of products / services offered to customers, feedback mechanism, customer compensation in cases of mis-selling, etc." 85Q (part): "prominently indicate the nature (e.g., loan, deposit, insurance, mutual fund, pension fund, hybrid product (insurance + investment), etc.)". 4(20A): "Mis-selling means sale of a financial product / service, whether own or third party, in the following cases:"
- Notes: if a loan is a "financial product", a feedback mechanism is due within 30 days of every product sold, including every new loan. Insurance-with-loan is a narrow slice. That enlarges the market but also means banks can meet 85Y with a generic survey (A13).

### A13 "An SMS survey satisfies 85Y"
- Claim as worded: "An SMS survey satisfies 85Y, so the default is a checkbox." (DESIGN.md line 171); "(an SMS survey is allowed)" (DESIGN.md line 166)
- Status: unverifiable
- Corrected wording: "85Y names surveys as an example mode and prescribes no channel, so a survey by SMS is not excluded by the text. I found no RBI statement that an SMS survey meets the stated purpose, which is to ensure that customers have understood the features and risks." Replace "satisfies" with "is not excluded by the text".
- Source: CB (85Y contains no "SMS", "text message" or "electronic") | retrieved 2026-11-10
- Quote: "...through modes such as call-backs or surveys carried out by a department / vertical of the bank not associated with sale of products / services." (85Y)
- Notes: whether a survey design satisfies 85Y is RBI's supervisory judgment. "Voice teach-back is a stronger test and 85Y does not forbid it" is safe. "SMS does not satisfy 85Y" is also unsupportable. The Third Amendment replaced principal para 85 with an SMS-charges rule, which is unrelated.

### A14 "RBI requires voice calls" is not claimable
- Claim as worded: "We can't say: "RBI requires voice calls"" (DESIGN.md line 166)
- Status: verified
- Corrected wording: none needed. Change the parenthetical to "(85Y names call-backs or surveys and sets no channel)".
- Source: CB | retrieved 2026-11-10
- Quote: see A11.
- Notes: "call-backs" is the closest the text comes to voice, and does not say human or automated.

### A15 85G: explicit consent
- Claim as worded: "85G | Explicit consent for each product, recorded | Is there a consent record for each product?" (DESIGN.md line 30)
- Status: verified (summary right; "recorded" needs care)
- Corrected wording: "85G: products or services, own or third-party, may be sold only with the customer's explicit consent, which may be a signed declaration (physical or electronic), OTP-based approval, a digitally recorded confirmation, or consent embedded in a clearly demarcated section of the agreement. Where one form covers several products each is enumerated and the customer may choose only those wanted. Consent and related records are kept until one year after the contract ends."
- Source: CB | retrieved 2026-11-10
- Quote (85G): "85G. A bank shall ensure that products / services, whether own or third-party, are offered / sold to a customer only with her / his explicit consent, which may be obtained either through a signed declaration (either physically or electronically), OTP based approval, digitally recorded confirmation, consent embedded in a clearly demarcated section of the agreement for the product / service, etc. Further, while obtaining consent from a customer for more than one product / service on a single form, each product / service shall be clearly enumerated and the customer shall have the option to choose only the desired product(s) / service(s). The bank shall store or preserve consent and related records of a product / service sold by it till one year from the date of cessation of the contractual agreement with respect to the product / service."
  4(13A): "4(13A) Explicit consent means a specific, informed and unambiguous indication of an individual’s choice, given through a duly recorded / documented statement or clear affirmative action, which indicates agreement to a specific action by or arrangement with a bank."
- Notes: NBFC 101G is identical with "NBFC". "Recorded" does not mean audio. A consent that exists but was not informed is arguably not "explicit consent". So "consent is None → flag" is sound, "consent exists → pass" is not. The record's `method` should allow "agreement clause". Related: 85H, 85I (default must be ‘No’ / ‘I do not agree’), 85Q (each product needs its own section and consent in a digital form).

### A16 85V: compulsory bundling
- Claim as worded: "85V | No compulsory bundling of third-party products | Did the customer believe the product was required for the loan?" (DESIGN.md line 31); "`85V`: the customer says it was required for the loan, or the record has `required_for_loan` → flag for review" (DESIGN.md line 114)
- Status: wrong (the summary is nearly right; the check built on it is not)
- Corrected wording: "85V: a bank shall not compulsorily bundle any third-party product or service (TPPS) with any of its own products or services. If the sale of the bank's own product is contingent on purchase of a TPPS as a risk mitigant, the customer must be given the option to buy it from any TPPS Provider. A package offered on the customer's voluntary consent, or complimentary (no additional direct or indirect cost), is not compulsory bundling." Replace the check with "required for the loan **and** no choice of provider offered, or required when it is not a risk mitigant."
- Source: CB | retrieved 2026-11-10
- Quote (85V): "85V. A bank shall not resort to compulsory bundling of any TPPS with any of its own product / service. However, if the sale of the bank’s own product / service is contingent on purchase of a TPPS as a risk mitigant, the customer shall be provided the option to purchase the same from any TPPS Provider. Further, offering of multiple products / services as a package based on voluntary consent from the customer and / or on complimentary basis (i.e., without any additional direct or indirect cost to the customer) shall not be construed as compulsory bundling."
  4(6A): "4(6A) Compulsory bundling means the practice by a bank of making availment of one product / service by a customer conditional upon availment of another product / service, whether own or third-party, offered by the bank."
- Notes:
  - Does 85V ban all bundling? No: compulsory bundling only, with two carve-outs.
  - Does it cover the lender's own products? Operative 85V covers a TPPS bundled with the bank's own product. Own-with-own bundling is not in 85V, but is in the mis-selling definition: 4(6A) covers "own or third-party", and 4(20A)(iv) lists "Compulsory bundling of another product / service with sale of the requested product / service" (A19), which carries the 85Z remedy.
  - RBI's text does not define "risk mitigant". Our reading is that credit-life or property insurance a lender requires on a loan is a risk mitigant, so requiring it is not itself a breach and the breach is no choice of provider. A product that is not a risk mitigant (a savings policy sold as a "security deposit", an "FD") falls outside the carve-out, so requiring it is compulsory bundling whatever choice of provider is offered. The record needs a field like `provider_choice_offered`. The customer saying "the bank said I had to" is evidence for review, not proof.
  - NBFC 101V is identical with "NBFC".

### A17 85W: paying for a product out of the loan
- Claim as worded: "85W | No paying for a product out of the loan without explicit consent | Was the premium deducted from the loan, and did the customer know?" (DESIGN.md line 32)
- Status: verified
- Corrected wording: none needed. 85W is not premium-specific. It covers the purchase of any product or service, own or third-party, funded out of any loan facility sanctioned to the customer. Use "premium" only for the insurance example.
- Source: CB | retrieved 2026-11-10
- Quote (85W): "85W. A bank shall not fund the purchase of a product / service by a customer, whether of its own or of a third-party, out of any loan facility sanctioned to the customer without her / his explicit consent." Payments banks 42W: "42W. A PB shall not indirectly fund the purchase of a product / service by a customer, whether of its own or of a third-party, out of any loan facility sanctioned to the customer without her / his explicit consent."
- Notes: "explicit consent" has the 4(13A) meaning (informed). "Did the customer know" is a fair proxy. NBFC 101W is identical. 85W fits the hero scenario best.

### A18 85Z: refund and compensation
- Claim as worded: "85Z | Mis-selling → full refund + compensation | We prepare the refund case for human review" (DESIGN.md line 34)
- Status: verified (direction right, conditions missing)
- Corrected wording: "85Z lets a customer complain about mis-selling to the bank within the timeline set by the product's regulator, or, if none, within 30 days of receiving the signed terms and conditions or agreement. Where mis-selling is established, the bank must refund the entire amount paid for the product or service, tell the customer the sale is cancelled where applicable, and compensate any loss arising from the mis-selling as per its approved policy." Do not write that a flagged call triggers a refund.
- Source: CB | retrieved 2026-11-10
- Quote (85Z): "85Z. A customer can lodge complaint regarding mis-selling of a financial product / service with the bank within the timeline specified by the respective financial sector regulators. In cases where no such timeline has been specified, customers can lodge complaint within 30 days of receiving the signed copy of the terms and conditions / agreement. In cases where mis-selling of a financial product / service is established, the bank shall refund the entire amount paid by the customer for purchase of the financial product / service and also intimate the customer about cancellation of the sale, wherever applicable. Further, the bank shall also compensate the customer, for any loss arising due to mis-selling, as per its approved policy."
- Notes:
  - Who decides it is mis-selling: the text does not say ("is established"; no body, process or standard).
  - Trigger: the refund duty arises "in cases where mis-selling ... is established". That sentence stands alone. The text does not say a complaint is required, and it does not say a complaint is not required. A Samajh flag is not established mis-selling. 85Y findings go into a report for policy review and are not linked to individual refunds.
  - Refund scope: "the entire amount paid by the customer for purchase of the financial product / service", the price (for example the premium), not other losses.
  - Compensation basis: the bank's own approved policy; no formula, cap or minimum.
  - Timeline: none for refund or compensation. The only day-count is the complaint window. A callback near day 30 leaves little time to complain.
  - Which regulator timeline applies to insurance is outside group A (IRDAI; not verified).
  - NBFC 101Z is identical with "NBFC". Frame the refund case as input to the bank's complaint process, not an entitlement under 85Z.

### A19 4(20A): mis-selling definition, all sub-clauses
- Claim as worded: "4(20A)(ii) | Mis-selling includes incorrect, incomplete or misleading information" (DESIGN.md line 33)
- Status: verified
- Corrected wording: "4(20A)(ii): sale of a product / service without providing correct or complete information or by giving misleading information." The paraphrase is fair. The definition concerns what was provided at sale. For NBFCs the number is 6(9A)(ii). HFCs follow paragraphs 101A to 101ZA, which use the term; para 157A does not expressly import the definitions in NBFC para 6.
- Source: CB; NBFC | retrieved 2026-11-10
- Quote: 
  > 4(20A) Mis-selling means sale of a financial product / service, whether own or third party, in the following cases:
  > (i) Sale of a product / service, which is neither suitable nor appropriate in view of the customer’s profile evaluated at the time of sale, notwithstanding her / his explicit consent; or
  > (ii) Sale of a product / service without providing correct or complete information or by giving misleading information; or
  > (iii) Sale of a product / service without customer’s explicit consent; or
  > (iv) Compulsory bundling of another product / service with sale of the requested product / service; or
  > (v) Sale of a product / service involving any other element defined by the financial sector regulator concerned as mis-selling.
- Notes: NBFC 6(9A)(i) to (v) are word-for-word the same. Mapping: (ii) is the "belief contradicts features" check; (iii) is 85G; (iv) is 85V and the wider 4(6A); (i) is untested by Samajh (A25); (v) brings in other regulators' definitions via 85ZA(2). A customer's wrong belief is evidence that (ii) may have occurred, not proof. Sub-clause (i), "notwithstanding her / his explicit consent", is the text's own answer to "a recorded yes is enough".

### A20 85X dark patterns, "UI-only"
- Claim as worded: "leaves out 85X (UI-only)" (IDEAS-HILLCLIMB.md line 95)
- Status: verified (85X is about user interfaces; it does not regulate the sale conversation), with a caution for our own bot
- Corrected wording: "85X requires the bank and its DSAs/DMAs to ensure their user interfaces do not deploy any dark pattern, to subject those interfaces to user testing and periodic internal audit, and to follow the CCPA's Guidelines for Prevention and Regulation of Dark Patterns, 2023." Cautions: (1) the definition covers "user interface or user experience interactions on any platform", so a bank-run voice bot is arguably a user interface, and Samajh's script falls under the same discipline; (2) Annex IIA names "loan protection insurance by default during the loan application process" as a dark pattern, which is the hero-scenario mechanism.
- Source: CB | retrieved 2026-11-10
- Quote (85X): "85X. A bank and its DSA / DMA shall ensure that their user interfaces do not deploy any dark pattern. User interfaces deployed by the bank and the DSA / DMA shall be subject to user testing and periodic internal audit for identification of any unfair features, including dark patterns. An illustrative list of dark patterns, which may be relevant to banks, is given in Annex IIA. Further, the bank and the DSA / DMA shall ensure adherence to the ‘Guidelines for Prevention and Regulation of Dark Patterns, 2023’ issued by the Central Consumer Protection Authority (CCPA), as amended from time to time."
  4(10.1A): "4(10.1A) Dark pattern means any practice or deceptive design pattern using user interface or user experience interactions on any platform that is designed to mislead or trick users to do something they originally did not intend or want to do, by subverting or impairing the consumer autonomy, decision making or choice, amounting to misleading advertisement or unfair trade practice or violation of consumer rights."
  Annex IIA(2) Basket Sneaking, illustration: "Illustration: Selecting additional products / services by default, on behalf of the customer, e.g., adding protection against online fraud / loan protection insurance by default during the loan application process."
- Notes: for the script, the relevant patterns are Trick Wording (double negatives), Nagging, False Urgency, Confirm Shaming (Annex IIA(11), (10), (1), (3)). The design's "ask once more in simpler words" is bounded, which is fine. The NBFC annex is Annex III with the same basket-sneaking illustration (checked).

### A21 Call timing and contact conduct (85N)
- Claim as worded: not in DESIGN.md (the brief asks about timing)
- Status: verified
- Corrected wording: add to DESIGN.md section 5: "Calls are placed between 09:00 and 19:00 unless the customer has asked otherwise, following the conduct norm in 85N(4)." Say "following", not "required by", because 85N is addressed to employees, DSAs/DMAs, sub-agents and TPPS representatives "deployed for sale or marketing activities". A feedback call from a non-sales unit is not literally covered.
- Source: CB | retrieved 2026-11-10
- Quote (85N): "85N. A bank shall ensure that its employees, DSAs / DMAs and their sub-agents as well as representatives of any TPPS Provider deployed for sale or marketing activities in the bank’s premises: ... (4) make telephonic contacts and / or visits to customers normally between 09:00 hours and 19:00 hours. Calls / visits earlier or later than the prescribed time period shall be done only when the customer has expressly given a request or authorisation to do so; (5) provide the contact details of the customer care and the grievance redressal official, if requested by the customer; (6) respect the customer’s privacy and discuss the matters of her / his interest with any other individual only if the customer has given an explicit request or consent for sharing of such information; ... (9) do not mislead or coerce the customer in purchase of any product / service offered by the bank; and (10) do not make any false / unauthorised commitment on behalf of the bank."
- Notes: DESIGN.md step 1 says the bot states it is a bank call "about the loan taken on a given date" before the identity check in step 2. If someone else answers, that discloses the loan. Rephrase to disclose only the bank name and "a customer-care call", and mention the loan after identity is confirmed. The closing line "Someone from our team will call you within N days" is a commitment, so N must be one the bank will keep. 85ZA(1) points to the DoT and TRAI rules on commercial communication (TCCCPR 2018); whether a feedback call is "commercial communication" is for group E.

### A22 Call recording
- Claim as worded: "An automated call from the bank's customer-care team (not sales), recorded" (DESIGN.md line 64)
- Status: verified (absence finding: the new chapter has no recording rule for feedback calls)
- Corrected wording: describe recording as our design and evidence choice, not an RBI requirement for the feedback call. RBI mandates recording today for calls by recovery agents.
- Source: CB (searched "record", "recording": only 85G and 4(13A)); sources/A/rbi-page-principal-cb-rbc-directions-2025-updated-2026-10-01.txt; sources/A/rbi-page-rbi-2026-27-223-cb-rbc-fourth-amendment-recovery.txt | retrieved 2026-11-10
- Quote: principal text: "The bank shall ensure that there is a tape recording of the content / text of the calls made by recovery agents to the customers, and vice-versa. The bank shall take reasonable precaution such as intimating the customer that the conversation is being recorded, etc." Fourth Amendment 454P (effective 1 Jan 2027): "Further, the bank shall take reasonable precautions such as intimating the borrower / guarantor that the conversation is being recorded, etc." (same paragraph also sets a six-month retention for recovery calls).
- Notes: these are recovery rules, not obligations for Samajh. They show RBI's habit of tying recording to telling the customer, which matches our disclosure line. No retention period is stated for feedback calls (A29).

### A23 Consent form and withdrawal
- Claim as worded: not in DESIGN.md
- Status: verified (withdrawal: absence finding)
- Corrected wording: none needed. The chapter regulates how consent is obtained and kept. It has no clause on withdrawal or revocation. Exit-related text is limited to disclosure of "exit terms including penalties" at consent (85H) and dark-pattern examples on cancellation (Annex IIA(5)).
- Source: CB | retrieved 2026-11-10
- Quote (85I): "85I. The process flow for obtaining consent through any user interface shall be designed in such a way that consent cannot be granted by the user without going through the applicable terms and conditions, if any. Further, the default choice for the customer to give consent shall be ‘No’ / ‘I do not agree’." 85H (part): "...shall prominently disclose the key features of the product / service, e.g., fees / charges / interest rate, etc., risks involved, financial commitment for the customer, lock in conditions, exit terms including penalties, etc. in a manner to draw the attention of the customer to such important information."
- Notes: a customer who says "I want to cancel" goes to a human. The bot must not state any cancel right or window (product-regulator matter, A26).

### A24 Third-party products, DSAs/DMAs, corporate agency
- Claim as worded: not in DESIGN.md
- Status: verified
- Corrected wording: add to DESIGN.md section 3 that insurance sold with a loan is a "third-party product or service" (TPPS) sold under the bank's agency business arrangement, and the bank owns the 85-series obligations for that sale.
- Source: CB; sources/A/rbi-page-rbi-uofs-third-amendment-commercial-banks.txt | https://rbi.org.in/Scripts/NotificationUser.aspx?Id=13485&Mode=0 ; Id=13495 | retrieved 2026-11-10
- Quote: 4(26A): "4(26A) Third-party Product or Service (TPPS) means a product or service offered by a bank to its customers on behalf of a third-party product / service provider (TPPS Provider) after entering into an agency business or referral services arrangement with the TPPS Provider as permitted under Reserve Bank of India (Commercial Banks – Undertaking of Financial Services) Directions, 2025." 85J: "A bank shall not advertise / market any TPPS as its own. While giving the details of any TPPS Provider to a customer, the bank shall clarify its role in providing such financial product / service." 85F (part): "...put in place a Code of Conduct for sale and marketing of financial products / services, which shall be applicable to the bank’s own employees, DSAs / DMAs and their sub-agents as well as representatives of any TPPS Provider deployed for the purpose in the bank’s premises." UoFS Third Amendment para 58(2) (effective 1 Jan 2027): "Banks shall ensure that it is in full compliance with the instructions on Reserve Bank of India (Commercial Banks - Responsible Business Conduct) Directions, 2025."
- Notes: 85J matters for the script: the bot must not call the insurer's product the bank's own. DSA/DMA rules are 85B to 85F, 85O. 85C requires an up-to-date website list updated "within seven calendar days". IRDAI rules apply to the product itself (85ZA(2)); not researched here.

### A25 Suitability and appropriateness
- Claim as worded: not in DESIGN.md
- Status: verified
- Corrected wording: none needed. Samajh does not test suitability (4(20A)(i)); state it as a limit.
- Source: CB | retrieved 2026-11-10
- Quote (85P): "85P. Before a financial product / service, other than those determined as suitable for all customers as per the bank’s policy, is sold to an individual customer, its suitability and appropriateness for the customer shall be determined by the bank based on an analysis of the features, risk-return attributes, time horizon, complexity, fee structure, etc. vis-à-vis the customer’s age, income, level of financial literacy, risk tolerance, etc. Wherever the financial sector regulator has prescribed any specific suitability assessment analysis for determining the suitability and appropriateness of the product / service regulated by it, a bank shall ensure adherence to the same."
- Notes: "level of financial literacy" is the term closest to the idea behind teach-back. 85R: "all documents related to sale of its own products / services, including the terms and conditions, are also available in the language of the region or in a language understood by the customer", which supports the multi-language scope.

### A26 Free-look, cancellation, refund and compensation timelines
- Claim as worded: "Do you know you can cancel it within N days?" (DESIGN.md line 67)
- Status: verified (absence finding)
- Corrected wording: N comes from the product regulator, not from this chapter. The chapter has no free-look period and no deadline for refund or compensation. Its only day-counts are 30 days in 85Y, 30 days in 85Z (complaint fallback) and seven calendar days in 85C.
- Source: CB (searched "free look", "free-look", "cooling": no hits; "cancel" only in 85Z and Annex IIA(5)) | retrieved 2026-11-10
- Quote (85T): "85T. On completion of a sale, copy of the terms and conditions / agreement signed by the customer and the employee of the bank or the TPPS Provider, as applicable, shall be provided to the customer, either physically or digitally." 85S requires an acknowledgement of the application with a telephone number.
- Notes: 85T's copy of the agreement starts the 85Z fallback complaint clock. Insurance free-look belongs to IRDAI (85ZA(2)); not verified here.

### A27 Incentives for sales staff
- Claim as worded: not in DESIGN.md
- Status: verified
- Corrected wording: none needed. A reason the feedback unit should be independent of sales.
- Source: CB | retrieved 2026-11-10
- Quote (85U): "85U. A bank shall ensure that its policies and practices do not create incentives for mis-selling of products / services, whether its own or offered on behalf of a third-party. Further, it shall be ensured that no incentive is directly or indirectly received by the bank’s employees from the TPPS Provider for sale / marketing of TPPS."
- Notes: the Fourth Amendment has a parallel for recovery incentives (454Q), not relevant here.

### A28 Board-approved policy
- Claim as worded: not in DESIGN.md
- Status: verified
- Corrected wording: say "a comprehensive policy (85A) and a compensation approach 'as per its approved policy' (85Z)". The new chapter does not say the policy is Board-approved. The principal Directions require policies in general to be approved by the Board or a delegated committee, but the new 85A policy is not in that paragraph's list (which predates it).
- Source: CB; sources/A/rbi-page-principal-cb-rbc-directions-2025-updated-2026-10-01.txt; ...-nbfc-...-updated-2026-07-01.txt | retrieved 2026-11-10
- Quote: 85A (quoted in A12). Principal CB para 5: "A bank shall put in place approved policies and periodic review mechanisms to ensure sound business conduct and enhanced customer service. An illustrative list of such policies to be approved by the Board or a Committee(s) to which powers have been delegated is provided below." Principal NBFC para 7: "An NBFC shall have Board approved policies and review mechanisms in place to ensure responsible business conduct."
- Notes: 85A requires the policy to cover the "feedback mechanism", so Samajh must fit inside it. Principal CB paras 6(1) and 15 require a six-monthly Board review of customer-service aspects, a natural home for the 85Y report, but no paragraph says so. Do not claim the link.

### A29 Reporting to RBI and record retention
- Claim as worded: "HALF-YEARLY VIEW (85Y)" (DESIGN.md line 93)
- Status: verified (absence finding)
- Corrected wording: none needed for the view. State that 85Y does not say who receives the report and requires no filing with RBI. The chapter's only retention period is for consent, until one year after the contract ends (85G). It sets none for feedback responses, recordings or the half-yearly report.
- Source: CB | retrieved 2026-11-10
- Quote: 85Y: "A half-yearly report on the findings of the feedback shall be prepared and utilised for review of existing policies and features of financial products / services." 85G: "The bank shall store or preserve consent and related records of a product / service sold by it till one year from the date of cessation of the contractual agreement with respect to the product / service."
- Notes: aligning evidence retention to 85G is our conservative choice; say so.

### A30 Automated, AI or voice-bot calls
- Claim as worded: "An automated call from the bank's customer-care team ... The bot says it is an AI" (DESIGN.md line 64)
- Status: verified (absence finding)
- Corrected wording: none needed. Do not write "RBI permits" or "RBI requires" AI disclosure for these calls. Case-insensitive searches of the CB and NBFC texts for "automat", "artificial", "chatbot", "bot", "IVR", "robo", "voice", "AI", "machine" found no relevant hit. The AI disclosure is our design choice.
- Source: CB; NBFC | retrieved 2026-11-10
- Quote (85ZA): "85ZA. In addition to the Directions mentioned herein, a bank shall also ensure compliance with: (1) guidelines issued by the relevant authorities from time to time, including the guidelines issued by Department of Telecommunications (DoT), Government of India and Telecom Regulatory Authority of India (TRAI) on aspects related to commercial communication such as the Telecom Commercial Communications Customer Preference Regulations (TCCCPR), 2018, as amended from time to time; (2) guidelines issued by the respective financial sector regulators, viz., Securities and Exchange Board of India (SEBI), Insurance Regulatory and Development Authority of India (IRDAI), and Pension Fund Regulatory and Development Authority (PFRDA) regarding products / services falling under their respective domains; and (3) any relevant guidelines issued by the Reserve Bank on related matters, as applicable to the banks, such as undertaking agency business by banks, outsourcing of financial services, mobilisation of deposits through agents, etc."
- Notes: running the callback through a vendor's voice agent is outsourcing, so 85ZA(3) and RBI's outsourcing instructions are relevant (group E; not researched). 4(10.1A) says "on any platform" (A20).

### A31 Timeline: policy statement, draft, final
- Claim as worded: not in DESIGN.md (the brief asks for the policy statement and press releases)
- Status: verified
- Corrected wording: none needed. 6 Feb 2026: Statement on Developmental and Regulatory Policies announces the measure. 11 Feb 2026: draft Amendment Directions issued; comments due by 4 Mar 2026. 15 Jun 2026: final directions issued with "consequent modifications".
- Source: sources/A/rbi-press-release-62171.txt; -62207.txt; -62938.txt | https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=62171, 62207, 62938 | retrieved 2026-11-10
- Quote: policy statement item 1: "There is a felt need to ensure that third party products and services that are being sold at the bank counters are suitable to customer needs and are commensurate with the risk appetite of individual clients." Draft press release: "The comments / feedback on the draft Amendment Directions may be submitted by the regulated entities and members of public / other stakeholders on or before March 4, 2026". Final: "Feedback received on the above draft Directions has been examined and the consequent modifications have been suitably incorporated in the final Amendment Directions."
- Notes: RBI's own motive, in its own words, is usable in the demo opening. The draft press release says existing suitability instructions covered "the context of insurance agency business" for scheduled commercial banks (excluding RRBs) and HFCs; the 2026 directions widen this to all banks and NBFCs.

### A32 RBI's statement on feedback received (Annex I) and FAQs
- Claim as worded: not in DESIGN.md (the brief asks for FAQs and the feedback statement)
- Status: unverifiable
- Corrected wording: none. I could not read Annex I, so I cannot say whether 85Y changed between the draft and the final.
- Source: none retrieved. See "Could not retrieve".
- Quote: none.
- Notes: the press release names Annex I (`PR45915062026_A1.pdf`) for the banks and NBFC directions and Annex II (`_A2.pdf`) for the Undertaking of Financial Services amendments. I found no RBI FAQ in two web searches.

### A33 Later amendments do not change the 85-series
- Claim as worded: not in DESIGN.md (checks that numbering is stable)
- Status: verified
- Corrected wording: none needed. Two later RBC amendments exist and do not touch 85A to 85ZA or the definitions used here. Third Amendment (24 Jun 2026, RBI/2026-27/167, customer liability in digital transactions): replaces principal para 85 with an SMS-charges rule and inserts other definitions. Fourth Amendment (6 Aug 2026, RBI/2026-27/223, recovery of dues and recovery agents): inserts 4(24A), 4(24B) and section L from 454A. Both take effect from 1 Jan 2027, and the numbering of 85Y and 4(20A) is stable as of 2026-11-10.
- Source: sources/A/rbi-page-rbi-2026-27-167-cb-rbc-third-amendment-customer-liability.txt; ...-223-cb-rbc-fourth-amendment-recovery.txt; rbi-press-release-63011.txt; -63305.txt | https://rbi.org.in/Scripts/NotificationUser.aspx?Id=13543&Mode=0 ; Id=13665 | retrieved 2026-11-10
- Quote: Third Amendment para 4(9): "In Chapter IV on ‘Customer Guidance and Protection’, paragraph 85 shall be substituted by the following, namely: “A bank shall not levy any charges on its customers for SMS sent in compliance to extant regulations or those sent for promotional / marketing / customer awareness purposes. In case of SMS sent for other purposes, the bank may levy or waive charges as per its internal policy.”"
- Notes: neither text refers to paragraphs 85A to 85ZA or Annex IIA. Recheck for amendments dated after 6 Aug 2026 before submission.

## Could not retrieve

| What | URL tried | Result |
|---|---|---|
| All ten Second Amendment PDFs plus the two Undertaking of Financial Services PDFs on RBI's document host | `https://rbidocs.rbi.org.in/rdocs/notification/PDFs/1NOTI1159FE64C67CBFC4483828513EE93480433.PDF` (and the other eleven) | curl and WebFetch: HTTP 200 but an F5 human-verification page, not a PDF. Not bypassed. The text is on the `rbi.org.in` notification pages instead. |
| Commercial-banks PDF | Same URL via `https://web.archive.org/web/2026/...` | Success: 302 to snapshot 20260828135256, a 316,217-byte 15-page PDF. |
| NBFC and HFC PDFs via the Wayback Machine | `https://web.archive.org/web/20260713183517id_/...9NOTI1231C5DA...PDF` (NBFC), `...20260713183829id_/...10NOTI124463DA...PDF` (HFC) | CDX lists one snapshot each, 2026-07-13, mimetype text/html (the verification page). The SFB, PB, LAB, RRB, UCB, RCB, AIFI and UoFS PDFs hit HTTP 429 rate limits and were not confirmed. |
| Annex I and II feedback statements | `https://rbidocs.rbi.org.in/rdocs/content/pdfs/PR45915062026_A1.pdf`, `..._A2.pdf` | WebFetch: verification page. Wayback availability API: no snapshot. |
| Press-release PDF | `https://rbidocs.rbi.org.in/rdocs/PressRelease/PDFs/PR4598097BCF6E7F74690A4E8EDC19B219027.PDF` | Wayback: no snapshot. The HTML press release page was saved instead. |
| RBI FAQ on the measure | two web searches | None found. |
| Draft CB Directions on `website.rbi.org.in/documents/d/rbi/commercial-banks-responsible-business-conduct-2` | direct fetch | HTTP 200 but the generic site home page, not the document. Not used. |
| Mirror `hellobanker.in/.../NT46BB3AE9CC38644D9A960F2017BA96D485.pdf` | direct fetch | A genuine PDF but an unrelated RBI circular (RBI/2026-27/46, 29 Apr 2026, banking services after a calamity). Discarded. |

Secondary leads seen in search results and not relied on: Khaitan & Co ERGO note on the draft (5 Mar 2026); Vinod Kothari "From Consent to Compensation" (June 2026); Taxmann, King Stubb & Kasiva and Mondaq summaries.

## Product implications (most important first)

1. **85V check.** Flag "required for the loan" only together with "no choice of TPPS provider" or "not a risk mitigant". Add a `provider_choice_offered` field to the product record. On our reading, credit-life required on a loan is not compulsory bundling if the customer may buy from any provider. RBI does not define "risk mitigant".
2. **85Z framing.** A Samajh flag is evidence for the bank's review, not a trigger for a refund. Refund and compensation arise where mis-selling is "established". The text does not say who establishes it or whether a complaint is needed. Compensation follows the bank's own approved policy. Remove any wording that a flag leads to a refund.
3. **Citations.** Cite the entity-specific direction by title, circular and DOR number. Use 101Y for NBFCs and 157A (pointing to 101A to 101ZA) for HFCs. Use 6(9A) for NBFC mis-selling. Drop "every RBI-regulated lender" and "an SMS survey satisfies 85Y".
4. **Optional parts of 85Y.** Random selection, call-backs and an independent unit are all inside "may include". The hard requirements are the mechanism, 30 days, the stated purpose and the half-yearly report. There is no stated channel, sample size, language or recipient of the report.
5. **Scope of 85Y.** On the chapter's wording it covers the sale of the lender's own loans too. The insurance-with-loan case is a subset.
6. **Our bot is itself a user interface under 85X.** Avoid trick wording, nagging, false urgency and confirm shaming. The Annex IIA basket-sneaking illustration ("loan protection insurance by default") is the hero case, a strong anchor for the demo.
7. **No RBI rule on AI or automated calls, or on recording feedback calls.** AI disclosure and recording are our choices. Do not cite RBI for them. 85ZA points to TRAI/DoT commercial-communication rules (group E) and RBI outsourcing rules (not researched).
8. **Call design.** Adopt the 09:00 to 19:00 norm, and do not mention the loan before identity is confirmed (85N(6) privacy). Keep the closing promise to something the bank can keep (85N(10)). Route "I want to cancel" to a human. N in "cancel within N days" comes from the product regulator, not this chapter.
9. **No transitional rule.** The directions do not say how the 30-day feedback treats sales made before 1 Jan 2027. Do not claim either way.
10. **Evidence retention.** Align to 85G (one year after the contract ends) as our conservative default. The chapter sets no retention period for feedback evidence.
11. **Re-verify before submission.** RBI's consolidated Directions pages did not yet contain 85A to 85ZA on 2026-11-10. Annex I (RBI's response to comments) was not read and may explain wording changes from the draft.