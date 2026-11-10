# Findings E: rules for an automated, recorded, AI-voiced outbound call by a lender

Research date: 2026-11-10. Sources are in `sources/E/` (index: `sources/E/INDEX.md`). File names below are relative to `sources/E/`.

- Quotes are copied from the saved `.txt` extractions. `[...]` joins two spans of one passage.
- The TRAI Third Amendment (18 Sep 2026) is a scan with OCR text; only clean spans are quoted from it.
- Two files are third-party mirrors of primary documents (FREE-AI report, SPDI Rules); the status line says so.
- "Interpretation" in a Notes line is my reading of the text, not a ruling by any regulator or court. This is not legal advice.

In force on 2026-11-10?

| Rule | In force? |
|---|---|
| TCCCPR 2018 as amended 12 Feb 2025 | Yes |
| TRAI Direction 19 Nov 2025 (1600-series, dates 1 Jan / 1 Feb / 1 Mar 2026) | Yes; all dates passed |
| TCCCPR Third Amendment (18 Sep 2026), general part | Yes if gazetted 18 Sep (about 18 Oct 2026) |
| Third Amendment regulation 4 (A2P declaration) | About 17 Nov 2026 if gazetted 18 Sep. Not yet |
| Third Amendment regulation 35A (A2P termination charge) | No; Fourth Amendment defers it to a notified date |
| DPDP Act s.3-17 (notice, consent, legitimate uses, rights, security) and Rules 3, 5-16 | No; 13 May 2027 |
| DPDP Act s.6(9) and Rule 4 (Consent Managers) | 13 Nov 2026 |
| RBI Responsible Business Conduct (Second Amendment) Directions 2026, incl. 85Y | No; 1 Jan 2027 |
| RBI recovery amendments of 6 Aug 2026 (call recording, 08:00-19:00) | No; 1 Jan 2027 |
| IT Rules amendment on synthetically generated information | Yes since 20 Feb 2026 (addressed to intermediaries) |

---

## E1. TRAI: call category, number series, auto-dialler rules, hours, AI voice

### E1.1 What counts as a "commercial communication"
- Claim as worded: not in DESIGN.md. Question: which TRAI category is a post-sale feedback call (DESIGN.md line 64: "An automated call from the bank's customer-care team (not sales)").
- Status: verified
- Corrected wording: none needed
- Source: `trai-tcccpr-2018-original-RegulationUcc19072018.txt` | https://trai.gov.in/sites/default/files/2024-09/RegulationUcc19072018.pdf | retrieved 2026-11-10
- Quote: "“Commercial Communication” means any voice call or message using telecommunication services, where the primary purpose is to inform about or advertise or solicit business for" (regulation 2, definitions, p.2)
- Notes: The TCCCPR regulates "commercial communication", defined by primary purpose. The Second and Third Amendments do not amend this clause. "Sender" is defined only "in relation to a commercial communication". Whether a feedback call has that purpose is E1.5.

### E1.2 The categories: promotional, service, transactional, government
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `trai-tcccpr-second-amendment-2025-reg12022025.txt` (pp.1-3); `trai-tcccpr-3rd-amendment-2026-09-18-Regulation_18092026.txt` (p.2) | https://trai.gov.in/sites/default/files/2025-02/Regulation_12022025.pdf ; https://www.trai.gov.in/sites/default/files/2026-09/Regulation_18092026.pdf | retrieved 2026-11-10
- Quote: "“Promotional Voice Call” means commercial communication any voice Commercial Communication containing promotional material or advertisement of a product or service" (Second Amendment, clause (av), p.2)
- Quote: "Provided that if promotional content is mixed with any type of commercial Voice Call, such voice call shall be treated as a Promotional Voice Call." (p.2)
- Quote: "its Customer or Subscriber to provide information pertaining to any product or service, its warranty, product recall, software upgrade alerts, safety or security of the product used or purchased by the Customer, periodic balance alerts, information regarding delivery of goods or services, and such Messages are not promotional in nature and do not require Explicit Consent" (Second Amendment, clause (bh)(i), p.2)
- Quote: "Provided also that a transactional Message or transactional Voice Call containing information pertaining to service shall be treated as a Service Message or Service Voice Call" (Third Amendment, regulation 2(h), p.2)
- Quote: "“Transactional Message or Transactional Voice Call” means a Message sent or Voice Call made by a Sender to its Customer or Subscriber in response to Customer initiated transaction within thirty minutes of the transaction relating to any product or service" (Second Amendment, clause (bt), p.2)
- Quote: "“ Government Message or Government Voice Call ” means any message sent or voice call made on the directions of –" (Second Amendment, clause (za), p.1)
- Notes: The Third Amendment re-wrote the service-call definition but kept the limb "not promotional in nature and do not require Explicit Consent" for calls to the sender's own customers. A call that mixes in promotional content becomes a promotional call. For Samajh this is the main legal limit on the script: no upsell, no offer.

### E1.3 Consent: explicit versus inferred
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `trai-tcccpr-2018-original-RegulationUcc19072018.txt`; `trai-tcccpr-3rd-amendment-2026-09-18-Regulation_18092026.txt` (p.1); `trai-pr-119-2026-third-amendment-tcccpr.txt` | URLs as in INDEX | retrieved 2026-11-10
- Quote: "“Inferred Consent” means any permission that can be reasonably inferred from the customer’s conduct or the Relationship between the Recipient and the Sender;" (2018 text, definitions)
- Quote: "“Explicit consent” means such consent as has been verified directly from the Recipient in a robust and verifiable manner and recorded by Consent Registrar as defined under these regulations;" (2018 text, definitions)
- Quote: "means any voluntary permission, either explicit or inferred, given by the customer to Sender to receive Commercial Communication related to" (Third Amendment, clause (k) as substituted, p.1)
- Quote: "The definition of consent has been expanded to include legacy consents already available with the entities." (TRAI PR 119/2026, para 4(vi))
- Notes: A service call to the sender's own customer needs no explicit consent (E1.2). TRAI consent is consent to receive commercial communication; DPDP consent to process data is separate (E2).

### E1.4 Opt-out rules and what DND blocks
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `trai-tcccpr-second-amendment-2025-reg12022025.txt` (p.2); `trai-tcccpr-3rd-amendment-2026-09-18-Regulation_18092026.txt` (p.14) | URLs as in INDEX | retrieved 2026-11-10
- Quote: "Provided that the Sender shall give an opt-out mechanism to the Recipient in the same Message, as may be specified by the Authority" (Second Amendment, promotional message definition, p.2)
- Quote: "Note-3: BLOCK PROMO option shall block only promotional types of Commercial Communications for all categories of content, mode, time band and day types but shall not block transaction and service type of Commercial Communications and Government Communications;" (Third Amendment, Schedule II item 1, p.14)
- Notes: The TCCCPR opt-out duty is for promotional messages. DND "BLOCK PROMO" does not block service or transactional calls. No TCCCPR text requires an opt-out line in a service call; an "I do not want these calls" path is good practice. RBI requires an easy unsubscribe from promotional communication (RBI/2026-27/115 para 85M).

### E1.5 Where a post-sale feedback call from a lender falls
- Claim as worded: "An automated call from the bank's customer-care team (not sales), recorded, about the loan taken on a given date." (DESIGN.md line 64)
- Status: unverifiable
- Corrected wording: Say "we treat it as a service call and make it from a 1600xx number". Do not say "TRAI classifies it as a service call".
- Source: `trai-tcccpr-2018-original-RegulationUcc19072018.txt` (para 4.3.13); searched all saved TRAI texts for "feedback", "survey", "post-sale" | https://trai.gov.in/sites/default/files/2024-09/RegulationUcc19072018.pdf | retrieved 2026-11-10
- Quote: "Communications from Political Parties related to political campaign and from entities sending communications to survey the market may not be directly falling under the definition of commercial communications." (2018 explanatory memorandum, para 4.3.13)
- Notes: No TRAI text names a post-sale understanding or feedback call. The nearest statements point two ways: (a) the 2018 memorandum says market-survey calls "may not" be commercial communication (explanatory, about market surveys, not operative); (b) the service-call definition covers information about a product the customer bought, which a post-sale call resembles, though a feedback call mostly asks rather than informs (interpretation). If outside "commercial communication", the TCCCPR number and consent rules may not bite on its content; if a service call, it needs a 1600xx number (E1.10) and no promotional content (E1.2). Take the second, cautious reading. The A2P rules apply either way (E1.11).

### E1.6 DoT allocation of the 1600 series
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `trai-direction-2025-11-19-1600-series-rbi-sebi-pfrda.txt` (para 4); `dot-letter-2025-02-11-1600-series-allotment.txt` | https://www.trai.gov.in/sites/default/files/2025-11/Direction_19112025_0.pdf | retrieved 2026-11-10
- Quote: "the Department of Telecommunications (DoT), vide its letter dated the 23rd December 2024, conveyed its decision to allocate a separate numbering series for Service and Transactional Voice Calls, i.e., “1600”, exclusively for Government (Central/State) entities and BFSI (Banking, Financial Services, and Insurance) sector entities" (TRAI Direction 19 Nov 2025, para 4)
- Quote: "Allocation of telecommunication identifiers in numbering series '1600' exclusively for service and transactional voice calls" (DoT letter No.16-02/2024-AS-III/N17, 11.02.2025, subject line)
- Notes: The DoT instruction of 23 Dec 2024 was not found; the DoT letter of 11 Feb 2025 cites it.

### E1.7 The 140 series for promotional calls; what a service call may not contain
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `rbi-notification-12770-voice-calls-sms.txt` (Annexure (A)(b)); `trai-pr-91-2026-clarifications-1600-140-series.txt` | https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12770&Mode=0 | retrieved 2026-11-10
- Quote: "shall use only ‘140’ numbering series for making promotional voice calls to their customers or prospective customers" (RBI/2024-25/105 Annexure (A)(b))
- Quote: "There shall be no mixing of promotional/upsell/cross-sell/offer-related communication on such transactional or service calls." (same)
- Quote: "Senders shall not use any other 10-digit fixed line/ mobile number for making promotional/Service/transactional voice calls to their customers, either directly or through their employees or channel partners, DSAs, BPO partner, in-house or outsources Call Center etc." (same)
- Quote: "TRAI has mandated use of 140xx series numbers for making promotional calls by entities of any sector." (TRAI PR 91/2026, 10 Jul 2026, para (ii))
- Notes: The RBI annexure calls the service series "160" (pre-launch name); TRAI's later texts say "1600xx". A vendor's or BPO's ordinary 10-digit number is expressly barred.

### E1.8 The RBI instruction to use 1600xx
- Claim as worded: not in DESIGN.md. (Prompt: "believed to be the RBI circular of January 2025".)
- Status: verified
- Corrected wording: The promotional series is "140xx", not "1400xx". The saved circular text has no compliance date; secondary summaries giving "31 March 2025" are not supported by it.
- Source: `rbi-notification-12770-voice-calls-sms.txt` | https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12770&Mode=0 | retrieved 2026-11-10
- Quote: "Undertake transactional / service calls only using ‘1600xx’ numbering series, when operationalized; undertake promotional voice calls only through phone numbers using ‘140xx’ numbering series;" (RBI/2024-25/105, 17 Jan 2025, para 2, third item)
- Quote: "Provide the verified details of their customer care numbers to DIP for enabling DoT to publish them on the “Sanchar Saathi” portal" (para 2, second item)
- Quote: "All REs are advised to ensure compliance with the above instructions expeditiously." (para 3)
- Notes: Addressed to commercial banks, co-operative banks, NBFCs (incl. HFCs) and others. The second item supports a "call back on the published number" line (E5.5).

### E1.9 Deadlines for RBI-regulated lenders to move to 1600
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `trai-direction-2025-11-19-1600-series-rbi-sebi-pfrda.txt`; `trai-pr-135-2025-1600-series-direction.txt`; `trai-pr-151-2025-1600-series-irdai-entities.txt` | https://trai.gov.in/sites/default/files/2025-11/PR_No.135of2025.pdf | retrieved 2026-11-10
- Quote: "Commercial Banks (including Public Sector Banks, Private Sector Banks, and Foreign Banks) shall onboard by 1st January, 2026." (TRAI PR 135/2025, B.i)
- Quote: "Large NBFCs (Asset size above 5000 crore), Payments Banks, and Small Finance Banks shall onboard by 1st February, 2026." (B.ii)
- Quote: "Remaining NBFCs, Co-operative Banks, Regional Rural Banks, and smaller entities shall onboard by 1st March, 2026." (B.iii)
- Quote: "should adopt ‘1600’ series numbers by the last date of 15th February, 2026" (TRAI PR 151/2025, IRDAI-regulated entities, direction of 16 Dec 2025)
- Notes: All dates have passed. I found no extension; absence of one is not proven. The 16 Dec 2025 IRDAI direction itself was not downloaded. The direction's Annexure-I (OCR) agrees with the press release.

### E1.10 What happens if a regulated lender uses another number
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `trai-direction-2025-11-19-1600-series-rbi-sebi-pfrda.txt` (para 8) | https://www.trai.gov.in/sites/default/files/2025-11/Direction_19112025_0.pdf | retrieved 2026-11-10
- Quote: "the entities referred to in paragraph 8(i) shall not be permitted to initiate any service or transactional voice calls, even with the explicit or inferred consent of customers, from numbers other than those allocated under the 1600-series, after the specified dates for mandatory adoption of 1600-series" (para 8(iii))
- Quote: "the action shall be taken as per regulatory provisions applicable to unregistered telemarketer" (para 8(ii))
- Notes: Consent does not excuse a non-1600 number. Complaints against such a caller are handled as against an unregistered telemarketer.

### E1.11 Auto-dialler, robo and A2P calls: declaration, not consent
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `trai-tcccpr-2018-original-RegulationUcc19072018.txt`; `trai-tcccpr-second-amendment-2025-reg12022025.txt` (reg. 4); `trai-tcccpr-3rd-amendment-2026-09-18-Regulation_18092026.txt` (pp.1-3 and explanatory part); `trai-pr-119-2026-third-amendment-tcccpr.txt` | URLs as in INDEX | retrieved 2026-11-10
- Quote: "“Robo Calls” means any call made to any customer using an artificial or prerecorded voice to interactively deliver a voice message without the involvement of human being on calling side for participating in the dialogue;" (2018 definition (bc))
- Quote: "Every Sender shall notify the Originating Access Provider, in advance, about the use of Auto Dialer or Robo-Calls as well as the intended objective of such calls in writing." (Second Amendment, regulation 4 as substituted, p.3)
- Quote: "refers to a voice call that is initiated by an application, software system, or automated platform without direct human dialling and delivered to an individual telecom subscriber" (Third Amendment, new clause (ea), p.1)
- Quote: "Every Sender shall declare to the Originating Access Provider (OAP), in advance, about the use of Application-to-Person (A2P) calls" (Third Amendment, regulation 4 as substituted, p.3)
- Quote: "A2P calls made without the required prior declaration will be treated as UCC." (TRAI PR 119/2026, para 4(ii)(b))
- Quote: "the Authority notes that as A2P calling is used for making bulk communication, the regulations apply to all A2P calls." (Third Amendment, explanatory part)
- Quote: "between voice of an actual human interacting on call and a pre-recorded or artificially generated human voice. Therefore, the bulk callers must pre-declare to the OAP, the use of A2P calling" (same)
- Notes: A service or transactional robo call needs no prior consent of the called person. It needs: a registered sender; an advance declaration to the telecom provider with CLI ranges (once regulation 4 is in force, E1.12); a 1600xx number (E1.10). The definition covers "artificial voice technologies", so an AI voice agent is an A2P call, and fits "Robo Calls" in the 2018 text. Tension: "Sender" is defined only for commercial communication, but the TRAI memorandum says the A2P rules apply to all A2P calls. Plan for the declaration either way. The original 2018 regulation 4 also barred auto-dialling that causes silent or abandoned calls; the Second Amendment replaced regulation 4, so that text is no longer there.

### E1.12 When the A2P declaration duty starts
- Claim as worded: not in DESIGN.md.
- Status: unverifiable
- Corrected wording: Say "the A2P declaration rule starts 60 days after gazette publication of the Third Amendment (about 17 Nov 2026 if published 18 Sep 2026)". Do not state a fixed date as fact.
- Source: `trai-tcccpr-3rd-amendment-2026-09-18-Regulation_18092026.txt` (p.1); `trai-tcccpr-4th-amendment-2026-11-04-Regulation_TCCCPR_04112026.txt`; `trai-amendments-page-7617.txt` | URLs as in INDEX | retrieved 2026-11-10
- Quote: "(3) These regulations shall come into force after thirty days from the date of their publication in the Official Gazette except" (Third Amendment, regulation 1(3))
- Quote: "(a) regulation 4, regulation 6, regulation 8(a) and regulation 18, which shall come into force after sixty days" (regulation 1(3)(a))
- Quote: "New Delhi, the 18th September, 2026" (Third Amendment header; the copy says "TO BE PUBLISHED IN THE GAZETTE")
- Quote: "shall come into force from such date as the Authority may, by notification in the Official Gazette, appoint." (Fourth Amendment, 4 Nov 2026, regulation 2; defers regulation 35A, the A2P termination charge)
- Notes: Amending regulation 4 is the A2P declaration; amending regulation 18 inserts regulation 35A. The gazette publication date was not retrieved, so dates are computed: general part about 18 Oct 2026; A2P declaration about 17 Nov 2026; annexure items about 17 Dec 2026.

### E1.13 Service and transactional robo calls: TRAI says unrestricted, but series and preferences apply
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `trai-tcccpr-second-amendment-2025-reg12022025.txt` (explanatory memorandum paras 18, 52); `trai-tcccpr-3rd-amendment-2026-09-18-Regulation_18092026.txt` (p.15) | URLs as in INDEX | retrieved 2026-11-10
- Quote: "Therefore, service or transactional robocalls should not be subject to any restrictions." (Second Amendment memorandum, para 18)
- Quote: "Service and Transactional Voice Calls through Auto-dialer/Robo calls should be permitted through 1600 or any other series allotted for the purpose." (para 18)
- Quote: "the Sender should pre-declare the use of Auto-dialers or Robo-calls along with intended objectives of such calls, to the concerned Access Providers" (para 52)
- Quote: "for the words “except transactional type commercial communications”, the words “except transactional type and service type of Commercial Communications” shall be substituted" (Third Amendment, Schedule II item 2 Note 3)
- Notes: The memorandum is TRAI's reasoning, not an operative rule. The declaration is meant to "enable the blocking of such calls based on the preference of the customer" (para 18), so a customer's mode preference may still stop a call connecting. The text does not say whether the specific robo-call block reaches service calls. Handle a failed connect without hammering retries.

### E1.14 Calling hours under the TCCCPR
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `trai-tcccpr-2018-original-RegulationUcc19072018.txt` (Schedule II item 3); `trai-tcccpr-3rd-amendment-2026-09-18-Regulation_18092026.txt` (p.15) | URLs as in INDEX | retrieved 2026-11-10
- Quote: "Time Bands (i), (ii), (iii) and (ix) shall be default OFF for all customers irrespective of the status of registration of customer" (2018 Schedule II item 3 Note-1)
- Quote: "transactional type and service type of Commercial Communications shall not be blocked during any time band" (Third Amendment, Schedule II item 3 Note-4)
- Notes: The schedule's bands are 00:00-06:00 (i), 06:00-08:00 (ii), 08:00-10:00 (iii) and 21:00-24:00 (ix). By default they are off for commercial communication, so promotional calls reach a customer only 10:00-21:00 unless she opts in (reading of the schedule). I found no TCCCPR clause setting hours for service or transactional calls, and the Third Amendment says a customer's block cannot stop them in any time band. RBI hour rules are in E3.

### E1.15 TRAI or DoT rule on AI-generated voices
- Claim as worded: "The bot says it is an AI, and the customer can ask for a human at any time." (DESIGN.md line 64)
- Status: verified
- Corrected wording: TRAI treats "artificial voice" as a reason to declare A2P use to the telecom provider. We found no TRAI duty to tell the called person the voice is an AI. The Third Amendment is OCR text that garbles "artificial" and "AI", so the search was re-run with tolerant patterns by the reviewer and found only AI spam-flagging of numbers.
- Source: `trai-pr-119-2026-third-amendment-tcccpr.txt`; searched the 2018 text, the Second, Third and Fourth Amendments and the 1600/1601 directions for "synthetic", "artificial", "AI-generated", "announce", "identify itself" | retrieved 2026-11-10
- Quote: "defined A2P calls as voice calls initiated by an application, software system or automated platform without direct human dialing, including using autodialing, robo-calls and pre-recorded/artificial voice technologies" (TRAI PR 119/2026, para 4(ii)(b))
- Notes: Vendor blogs claim a TRAI draft requiring AI disclosure at call start. I found no such text in any TRAI document; those claims are unverified. I found no DoT instruction on AI voices.

### E1.16 The 1601 series is not for lenders
- Claim as worded: not in DESIGN.md. (Needed because the FREE-AI report names "1601 series" for AI voice; see E4.3.)
- Status: verified
- Corrected wording: none needed
- Source: `trai-direction-2026-08-10-1601-series-non-bfsi.txt`; `trai-pr-91-2026-clarifications-1600-140-series.txt` | https://www.trai.gov.in/sites/default/files/2026-08/Direction_10082026.pdf | retrieved 2026-11-10
- Quote: "has allocated the 1601 numbering series exclusively for Service and Transactional Voice Calls by entities in sectors other than BFSI, and Government sector" (TRAI direction 10 Aug 2026, para 1)
- Quote: "TRAI has mandated the use of 1600xx series numbers for service and transaction calls by regulated entities of BFSI sector i.e. entities regulated by RBI, SEBI, IRDAI and PFRDA to their existing customers" (TRAI PR 91/2026, para (i))
- Notes: A lender uses 1600xx.

---

## E2. DPDP Act 2023 and Rules 2025: notice and consent

### E2.1 Act and Rules saved; commencement clauses
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `dpdp-act-2023-egazette-248045.txt`; `dpdp-act-commencement-gsr843e-2025-11-13-egazette-267647.txt`; `dpdp-rules-2025-egazette-267650.txt` | https://egazette.gov.in/WriteReadData/2023/248045.pdf ; https://egazette.gov.in/WriteReadData/2025/267647.pdf ; https://egazette.gov.in/WriteReadData/2025/267650.pdf | retrieved 2026-11-10
- Quote: "(c) eighteen months from the date of publication of this gazette, on which the provision of sections 3 to 5, sub-sections (1) to (8) and (10) of section 6,sections 7 to 10, sections 11 to 17, section 27 except clause (d) of sub -section (1) of the said section, sections 28 to 34, 36, 37 and sub -section (2) of section 44 of the said Act shall come into force." (G.S.R. 843(E), 13 Nov 2025)
- Quote: "(3) Rule 4 shall come into force one year after the date of publication of this Gazette. (4) Rules 3, 5 to 16, 22 and 23 shall come into force eighteen months after the date of publication of this Gazette." (DPDP Rules, rule 1)
- Quote: "NEW DELHI, THURSDAY, NOVEMBER 13, 2025" (gazette date line of G.S.R. 843(E))
- Notes: 13 Nov 2025 gives 13 Nov 2026 (one year) and 13 May 2027 (eighteen months). Some secondary sources say 14 Nov; the gazette file ID carries 14112025 (upload date), while the gazette header says 13 Nov.

### E2.2 What is in force today and what is not
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `dpdp-act-commencement-gsr843e-2025-11-13-egazette-267647.txt`; `dpdp-rules-2025-egazette-267650.txt` | URLs as in E2.1 | retrieved 2026-11-10
- Quote: "(a) the date of publication of this notification in the Official Gazette as the date on which the provisions of sub-section (2) of section 1, section 2, sections 18 to 26 sections 35, 38, 39, 40, 41, 42, 43, and sub -sections (1) and (3) of section 44 of the said Act shall come into force;" (G.S.R. 843(E))
- Quote: "(2) Rules 1, 2 and 17 to 21 shall come into force on the date of their publication in the Official Gazette." (DPDP Rules, rule 1)
- Notes: In force now: definitions, Data Protection Board provisions and general provisions (Act s.1(2), 2, 18-26, 35, 38-43, 44(1),(3); Rules 1, 2, 17-21). From 13 Nov 2026: s.6(9), s.27(1)(d), Rule 4. From 13 May 2027: s.3-5, s.6(1)-(8),(10), s.7-17, penalties, Rules 3 and 5-16. RBI 85Y starts 1 Jan 2027, so a lender runs 85Y calls for about four and a half months before the DPDP duties bind. Until s.44(2) commences, IT Act s.43A and the SPDI Rules 2011 apply (E2.9).

### E2.3 Notice: section 5 and Rule 3
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `dpdp-act-2023-egazette-248045.txt` (s.5); `dpdp-rules-2025-egazette-267650.txt` (rule 3) | URLs as in E2.1 | retrieved 2026-11-10
- Quote: "Every request made to a Data Principal under section 6 for consent shall be accompanied or preceded by a notice given by the Data Fiduciary to the Data Principal, informing her,—" (Act s.5(1))
- Quote: "give, in clear and plain language, a fair account of the details necessary to enable the Data Principal to give specific and informed consent for the processing of her personal data, which shall include, at the minimum, — (i) an itemised description of such personal data; and (ii) the specified purpose or purposes of, and specific description of the goods or services to be provided or uses to be enabled by, such processing" (Rules, rule 3(b))
- Quote: "give, the particular communication link for accessing the website or app, or both, of such Data Fiduciary, and a description of other means, if any, using which such Data Principal may—" (Rules, rule 3(c))
- Notes: The notice must list the data, the purpose, how to withdraw consent, how to exercise rights and how to complain to the Board. A short spoken opening cannot carry all of that. Workable pattern: say the purpose and the recording in the opening, and point to the full notice delivered in writing (SMS or link) in the customer's language. Applies from 13 May 2027 where consent is the legal basis (E2.5).

### E2.4 Consent: section 6
- Claim as worded: "Consent check. 'Our records show you agreed on <date> — is that right?' This only checks existing consent; the call never captures it." (DESIGN.md line 69). That is product consent under RBI 85G. This claim is about data-protection consent for the call itself.
- Status: verified
- Corrected wording: none needed for line 69; add a separate notice-and-consent step for the call's own processing.
- Source: `dpdp-act-2023-egazette-248045.txt` (s.6) | https://egazette.gov.in/WriteReadData/2023/248045.pdf | retrieved 2026-11-10
- Quote: "The consent given by the Data Principal shall be free, specific, informed, unconditional and unambiguous with a clear affirmative action, and shall signify an agreement to the processing of her personal data for the specified purpose and be limited to such personal data as is necessary for such specified purpose." (s.6(1))
- Quote: "such Data Principal shall have the right to withdraw her consent at any time, with the ease of doing so being comparable to the ease with which such consent was given." (s.6(4))
- Quote: "the Data Fiduciary shall be obliged to prove that a notice was given by her to the Data Principal and consent was given by such Data Principal to the Data Fiduciary" (s.6(10))
- Notes: "Clear affirmative action" makes silence or "stayed on the line" a weak consent (interpretation). A spoken "yes" or key press stored in the evidence log gives the lender something to prove under s.6(10). Withdrawal must be as easy as giving: provide a "say stop" path.

### E2.5 "Certain legitimate uses": does an RBI direction remove the need for consent?
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: Do not say "the call needs no consent because RBI requires it".
- Source: `dpdp-act-2023-egazette-248045.txt` (s.2(za), s.7, s.8(7)) | https://egazette.gov.in/WriteReadData/2023/248045.pdf | retrieved 2026-11-10
- Quote: "(a) for the specified purpose for which the Data Principal has voluntarily provided her personal data to the Data Fiduciary, and in respect of which she has not indicated to the Data Fiduciary that she does not consent to the use of her personal data." (s.7(a))
- Quote: "(d) for fulfilling any obligation under any law for the time being in force in India on any person to disclose any information to the State or any of its instrumentalities, subject to such processing being in accordance with the provisions regarding disclosure of such information in any other law for the time being in force;" (s.7(d))
- Quote: "“specified purpose” means the purpose mentioned in the notice given by the Data Fiduciary to the Data Principal in accordance with the provisions of this Act and the rules made thereunder" (s.2(za))
- Notes: Interpretation, not a ruling. The Act has no general "compliance with any legal obligation" ground. Section 7(d) covers duties to disclose information to the State; 85Y requires a feedback mechanism and a half-yearly internal report, which is not a disclosure to the State on its face. Section 7(a) is the likelier fit: the borrower gave her phone number and loan data for servicing the loan; whether a recorded understanding call is within that "specified purpose" depends on what the origination notice said. For certainty a lender should list "post-sale feedback calls under RBI directions, recorded" as a purpose in the loan-time notice, and give a short notice and ask for a clear "yes" at the start of the call.

### E2.6 Language of the notice and consent request
- Claim as worded: not in DESIGN.md. (DESIGN.md section 4 lists Hindi, Hinglish, Tamil, Kannada.)
- Status: verified
- Corrected wording: none needed
- Source: `dpdp-act-2023-egazette-248045.txt` (s.5(3), s.6(3)) | https://egazette.gov.in/WriteReadData/2023/248045.pdf | retrieved 2026-11-10
- Quote: "The Data Fiduciary shall give the Data Principal the option to access the contents of the notice referred to in sub-sections (1) and (2) in English or any language specified in the Eighth Schedule to the Constitution." (s.5(3))
- Quote: "providing the contact details of a Data Protection Officer, where applicable, or of any other person authorised by the Data Fiduciary to respond to any communication from the Data Principal for the purpose of exercise of her rights under the provisions of this Act." (s.6(3))
- Notes: The duty is an option to read the notice in English or an Eighth Schedule language. Hindi, Tamil and Kannada qualify; "Hinglish" does not, so the written notice should be Hindi or English. The consent request must also give a DPO or authorised contact (feeds the callback-number element).

### E2.7 Rights of the data principal
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `dpdp-act-2023-egazette-248045.txt` (ss.11-14); `dpdp-rules-2025-egazette-267650.txt` (rule 14) | URLs as in E2.1 | retrieved 2026-11-10
- Quote: "A Data Principal shall have the right to correction, completion, updating and erasure of her personal data for the processing of which she has previously given consent, including consent as referred to in clause (a) of section 7" (s.12(1))
- Quote: "A Data Principal shall have the right to have readily available means of grievance redressal provided by a Data Fiduciary or Consent Manager" (s.13(1))
- Quote: "within a reasonable period not exceeding ninety days" (Rules, rule 14(3))
- Notes: Rights: a summary of data and who it was shared with (s.11), correction and erasure (s.12), grievance redress (s.13), nomination (s.14), withdrawal of consent (s.6(4)). Erasure can be refused where retention is "necessary for the specified purpose or for compliance with any law" (s.12(3)). The evidence log should be able to produce, correct and delete one customer's call data.

### E2.8 Recording and retaining a call: purpose, retention, security
- Claim as worded: not in DESIGN.md. (DESIGN.md section 6 keeps quotes with timestamps in an evidence log.)
- Status: verified
- Corrected wording: none needed
- Source: `dpdp-act-2023-egazette-248045.txt` (s.2(t), s.8); `dpdp-rules-2025-egazette-267650.txt` (rules 6, 8(3)) | URLs as in E2.1 | retrieved 2026-11-10
- Quote: "“personal data” means any data about an individual who is identifiable by or in relation to such data;" (s.2(t))
- Quote: "A Data Fiduciary shall protect personal data in its possession or under its control, including in respect of any processing undertaken by it or on its behalf by a Data Processor, by taking reasonable security safeguards to prevent personal data breach." (s.8(5))
- Quote: "(a) erase personal data, upon the Data Principal withdrawing her consent or as [...] soon as it is reasonable to assume that the specified purpose is no longer being served, whichever is earlier; and" (s.8(7)(a), pp.7-8; the lead-in reads "unless retention is necessary for compliance with any law for the time being in force")
- Quote: "appropriate data security measures, such as securing of personal data through encryption, obfuscation, masking or the use of virtual tokens mapped to that personal data" (Rules, rule 6(1)(a))
- Quote: "retain such logs and personal data for a period of one year, unless compliance with any law for the time being in force requires otherwise" (Rules, rule 6(1)(e))
- Quote: "such personal data, associated traffic data and other logs of the processing for a minimum period of one year from the date of such processing" (Rules, rule 8(3))
- Notes: A recording of an identified borrower is personal data. Purpose limitation (s.4, s.6(1)), security (s.8(5), Rule 6), erasure when the purpose ends (s.8(7)) and breach reporting (Rule 7: to the Board without delay and in detail within 72 hours) apply from 13 May 2027. Rules 6(1)(e) and 8(3) set a one-year floor for logs and processing data. The Third Schedule erasure timers (Rule 8(1)) cover only large e-commerce, online gaming and social media firms, not lenders. The Act and Rules do not name call recordings or set a maximum retention. The lender must choose and document a period; RBI 85G fixes only consent records (one year after the contract ends). Processors (voice-AI vendor, LLM provider) need a contract (s.8(2)); the lender stays responsible (s.8(1)).

### E2.9 Is voice a special category?
- Claim as worded: not in DESIGN.md.
- Status: verified (the SPDI Rules file is a mirror of the gazette notification, hosted by PRS India)
- Corrected wording: none needed
- Source: `dpdp-act-2023-egazette-248045.txt` (no hits for "sensitive", "biometric", "voice"); `spdi-rules-2011-gsr313e-prs-mirror.txt`; `rbi-digital-lending-directions-2025-notif12848.txt` | https://PRSINDIA.org/files/bills_acts/bills_parliament/2011/IT_Rules_2011.pdf | retrieved 2026-11-10
- Quote: "(2) The Information Technology Act, 2000 shall be amended in the following manner, namely:— (a) section 43A shall be omitted;" (DPDP Act s.44(2)(a))
- Quote: "“Biometrics” means the technologies that measure and analyse human body characteristics, such as ‘fingerprints’, ‘eye retinas and irises’, ‘voice patterns’, “facial patterns’, ‘hand measurements’ and ‘DNA’ for authentication purposes;" (SPDI Rules 2011, rule 2(1)(b))
- Quote: "(vi) Biometric information;" (SPDI Rules 2011, rule 3)
- Quote: "RE shall ensure that no biometric data is stored/ collected by the RE and LSP, unless allowed under extant statutory guidelines." (RBI Digital Lending Directions 2025, para 13(iii))
- Notes: The DPDP Act has no sensitive-data category (confirmed). Until s.44(2) commences on 13 May 2027, IT Act s.43A and the SPDI Rules apply, and they treat "voice patterns" as biometrics when used "for authentication purposes". A plain recording for a feedback call is not a voiceprint. Samajh should not build speaker verification or voiceprints; DESIGN.md already excludes cloning. For a digital lender, Digital Lending Directions 13(iii) bars storing biometric data and 13(iv) requires storage on servers in India, with processing abroad deleted within 24 hours; check before sending transcripts to a foreign-hosted LLM (unverified for any specific deployment).

---

## E3. RBI: recording, calling hours, conduct

### E3.1 The 85Y text and the circular numbers
- Claim as worded: "Commercial banks: RBI/2026-27/115, para 85Y. NBFCs: RBI/2026-27/123, para 101Y. Every other RBI-regulated lender gets an equivalent paragraph, and HFCs inherit it via para 157A [verify circular numbers against PDFs]." (DESIGN.md line 22)
- Status: verified
- Corrected wording: none needed. Also: AIFIs are RBI/2026-27/122; HFCs are RBI/2026-27/124.
- Source: `rbi-2026-27-115-commercial-banks-rbc-second-amendment.txt`; `rbi-2026-27-123-nbfc-rbc-second-amendment.txt`; `rbi-2026-27-122-aifi-rbc-second-amendment.txt`; `rbi-2026-27-124-hfc-second-amendment.txt` | https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Id=13485 (also Id=13493, 13492, 13494) | retrieved 2026-11-10
- Quote: "These Directions shall come into effect from January 1, 2027." (RBI/2026-27/115, DOR.MCS.REC.No.94/01-01-032/2026-27, 15 Jun 2026, para 3(2))
- Quote: "85Y. A bank shall establish a mechanism to seek feedback from customers, within a period of 30 days from the sale of any financial product / service to ensure that customers have understood the features of the financial product / service and also the risks associated with such financial product / service. The mechanism may include selection of the customers on a random basis for such feedback through modes such as call-backs or surveys carried out by a department / vertical of the bank not associated with sale of products / services." (para 85Y)
- Quote: "101Y. An NBFC shall establish a mechanism to seek feedback from customers, within a period of 30 days from the sale of any financial product / service" (RBI/2026-27/123, para 101Y)
- Quote: "157A. An HFC shall ensure compliance with the provisions of paragraphs 101A to 101ZA under Chapter IIIA of Reserve Bank of India (Non-Banking Financial Companies – Responsible Business Conduct) Directions, 2025." (RBI/2026-27/124, para 157A)
- Notes: The numbers in DESIGN.md are right. Neither 85Y nor 101Y mentions recording, hours, consent or AI.

### E3.2 What RBI says about recording calls
- Claim as worded: "recorded" (DESIGN.md line 64).
- Status: verified
- Corrected wording: Do not say "RBI requires the 85Y call to be recorded". The only RBI recording duty we found in the saved texts, and the duty to tell the customer, are written for recovery calls.
- Source: `rbi-commercial-banks-rbc-directions-2025-notif13140.txt` (para 442(4)); `rbi-2026-27-223-commercial-banks-rbc-fourth-amendment-recovery.txt` (paras 454A, 454P); `rbi-2026-27-230-nbfc-rbc-third-amendment-recovery.txt` (para 100P); `rbi-commercial-banks-credit-debit-cards-directions-2025-notif13155.txt`; `rbi-2026-27-115-commercial-banks-rbc-second-amendment.txt` (paras 85G, 4(13A)) | https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=13140&Mode=0 ; https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Id=13665 | retrieved 2026-11-10
- Quote: "The bank shall ensure that there is a tape recording of the content / text of the calls made by recovery agents to the customers, and vice-versa. The bank shall take reasonable precaution such as intimating the customer that the conversation is being recorded, etc." (Commercial Banks RBC Directions 2025, para 442(4), in force now)
- Quote: "the bank shall ensure that there is a recording of the content / text of the calls made by the employee / recovery agent to the borrower / guarantor and the calls made by the borrower / guarantor to the telephone / mobile number conveyed by the bank. The record shall be preserved for a period of six months from the date the call was made, or in cases which are sub judice, till they are disposed of." (RBI/2026-27/223, para 454P, from 1 Jan 2027)
- Quote: "Further, the bank shall take reasonable precautions such as intimating the borrower / guarantor that the conversation is being recorded, etc." (para 454P)
- Quote: "The provisions under this Section shall apply to recovery of loan dues by a bank from borrowers in default, including taking possession of a security." (para 454A)
- Quote: "The bank shall store or preserve consent and related records of a product / service sold by it till one year from the date of cessation of the contractual agreement with respect to the product / service." (RBI/2026-27/115, para 85G)
- Quote: "Explicit consent means a specific, informed and unambiguous indication of an individual’s choice, given through a duly recorded / documented statement or clear affirmative action" (RBI/2026-27/115, para 4(13A))
- Quote: "Customer-initiated process indicating intent to use a credit card such as PIN generation, modification of transaction control, Interactive Voice Response, recorded call to the customer care centre and SMS may be considered as activation of Credit Card." (Credit Cards and Debit Cards Directions 2025, explanation to para 11(6))
- Notes: From 1 Jan 2027 the Fourth Amendment (RBI/2026-27/223) deletes paras 408-416 and 442-454 of the Commercial Banks RBC Directions 2025 and replaces them with Section L (paras 454A-454AB), so 442(4) is replaced by 454P. NBFC equivalent: para 100P (RBI/2026-27/230), same wording. 454A extends a provision to non-defaulters only "wherever explicitly specified", and 454P is not so specified. The NBFC RBC Directions 2025 contain no call-recording text. No RBI paragraph I found requires an 85Y feedback call to be recorded or sets how long to keep it. Recording and telling the customer follows RBI's own pattern and is needed under DPDP from May 2027 (E2.3, E2.8).

### E3.3 RBI calling-hour rules for recovery calls
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `rbi-commercial-banks-rbc-directions-2025-notif13140.txt` (paras 445, 410); `rbi-nbfc-rbc-directions-2025-notif12942.txt` (para 100); `rbi-2026-27-223-commercial-banks-rbc-fourth-amendment-recovery.txt` (para 454Y) | URLs as in E3.2 | retrieved 2026-11-10
- Quote: "persistently calling the borrower and / or calling the borrower before 8:00 a.m. and after 7:00 p.m. for recovery of overdue loans" (Commercial Banks RBC Directions 2025, para 445, in force now)
- Quote: "persistently calling the borrower and/ or calling the borrower before 8:00 a.m. and after 7:00 p.m. for recovery of overdue loans" (NBFC RBC Directions 2025, para 100)
- Quote: "An employee / recovery agent shall contact / visit the borrower / guarantor only between 08:00 hours and 19:00 hours. Calls / visits earlier or later than the prescribed time period shall be done only when the borrower / guarantor has expressly given a request or authorisation to do so." (RBI/2026-27/223, para 454Y(4), from 1 Jan 2027)
- Quote: "Persistently calling the borrower and / or calling the borrower before 9:00 a.m. and after 6:00 p.m." (Commercial Banks RBC Directions 2025, para 410(2), microfinance loans)
- Notes: These apply to calls to recover overdue loans (para 410: microfinance recovery). The common "8 a.m. to 7 p.m." figure comes from paras 445 and 100. From 1 Jan 2027 paras 408-416 and 442-454 are deleted and replaced by Section L, whose para 454Y(4) sets 08:00-19:00.

### E3.4 RBI calling-hour rules for sales, marketing and card telemarketing
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `rbi-2026-27-115-commercial-banks-rbc-second-amendment.txt` (para 85N); `rbi-2026-27-123-nbfc-rbc-second-amendment.txt` (para 101N); `rbi-commercial-banks-credit-debit-cards-directions-2025-notif13155.txt` (para 11(9)) | URLs as in INDEX | retrieved 2026-11-10
- Quote: "A bank shall ensure that its employees, DSAs / DMAs and their sub-agents as well as representatives of any TPPS Provider deployed for sale or marketing activities in the bank’s premises:" (RBI/2026-27/115, para 85N, lead-in)
- Quote: "make telephonic contacts and / or visits to customers normally between 09:00 hours and 19:00 hours. Calls / visits earlier or later than the prescribed time period shall be done only when the customer has expressly given a request or authorisation to do so;" (para 85N(4), from 1 Jan 2027)
- Quote: "The card-issuer’s representatives shall contact the customers only between 10:00 hrs and 19:00 hrs." (Commercial Banks Credit Cards and Debit Cards Directions 2025, para 11(9), in force now)
- Notes: Para 85N(4) applies to staff and agents "deployed for sale or marketing". NBFC equivalent: para 101N(4), same wording. The card rule sits in the customer-acquisition paragraph for credit cards; it replaced the 2022 Master Direction for commercial banks (para 93, "stand repealed"), which carried the same sentence (`rbi-md-credit-debit-card-2022-updated-2024-03-07-notif12300.txt`).

### E3.5 Does any RBI hour limit apply in terms to a feedback call? What window is cautious?
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `rbi-2026-27-115-commercial-banks-rbc-second-amendment.txt` (para 85Y); all RBI texts saved in `sources/E/` searched for "hours", "a.m.", "p.m.", "hrs", "telephonic" | retrieved 2026-11-10
- Quote: "A bank shall establish a mechanism to seek feedback from customers, within a period of 30 days from the sale of any financial product / service" (para 85Y: no hours stated)
- Notes: No RBI paragraph I found sets a calling-hour limit for a feedback call in terms. The limits in E3.3 and E3.4 attach to recovery, sales/marketing and card telemarketing. A feedback call must not be mistaken for any of them (85Y says the department doing it must be "not associated with sale"), so a cautious window is the intersection of all limits: 10:00 to 19:00 in the customer's local time, calling outside it only if the customer asks. It also sits inside the TCCCPR default 10:00-21:00 window (E1.14). This is good practice, not a quoted rule.

### E3.6 The Second Amendment Directions 2026: contact and consent paragraphs
- Claim as worded: "RBI's Responsible Business Conduct (Second Amendment) Directions 2026 take effect on 1 Jan 2027." (DESIGN.md section 2)
- Status: verified
- Corrected wording: none needed
- Source: `rbi-2026-27-115-commercial-banks-rbc-second-amendment.txt` | https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Id=13485 | retrieved 2026-11-10
- Quote: "A bank shall send promotional communication / alerts about promotional offers in respect of its own or third-party financial products / services to a customer only if he / she has given explicit consent to receive such communication / alerts." (para 85L)
- Quote: "respect the customer’s privacy and discuss the matters of her / his interest with any other individual only if the customer has given an explicit request or consent for sharing of such information;" (para 85N(6))
- Quote: "provide the details of the customers, who have expressed their desire to be flagged as “Do Not Disturb” for promotional communication, to the bank;" (para 85N(7))
- Notes: Saved in full; no paragraph mentions recording of calls or AI. Contact paragraphs: 85L (promotional communication needs explicit consent), 85M (easy unsubscribe), 85N (staff conduct, hours, privacy, DND). Another researcher covers the rest.

### E3.7 RBI tells lenders to follow TCCCPR
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `rbi-2026-27-115-commercial-banks-rbc-second-amendment.txt` (para 85ZA); `rbi-2026-27-123-nbfc-rbc-second-amendment.txt` (para 101ZA); `rbi-2026-27-223-commercial-banks-rbc-fourth-amendment-recovery.txt` (para 454AB) | URLs as in E3.1 | retrieved 2026-11-10
- Quote: "guidelines issued by the relevant authorities from time to time, including the guidelines issued by Department of Telecommunications (DoT), Government of India and Telecom Regulatory Authority of India (TRAI) on aspects related to commercial communication such as the Telecom Commercial Communications Customer Preference Regulations (TCCCPR), 2018, as amended from time to time;" (para 85ZA(1))
- Notes: The E1 duties bind a lender under TRAI's regulations and, from 1 Jan 2027, as an RBI condition.

---

## E4. AI disclosure

### E4.1 IT Rules amendment on synthetically generated information: definition and labelling duty
- Claim as worded: not in DESIGN.md. (Earlier notes cite G.S.R. 120(E), 2026.)
- Status: verified
- Corrected wording: none needed
- Source: `it-rules-amendment-2026-gsr120e-egazette-269993.txt` | https://egazette.gov.in/WriteReadData/2026/269993.pdf | retrieved 2026-11-10
- Quote: "(wa) ‘synthetically generated information’ means audio, visual or audio -visual information which is artificially or algorithmically created, generated, modified or altered using a computer resource, in a manner that such information appears to be real, authentic or true and depicts or portrays any individual or event in a manner that is, or is likely to be perceived as indistinguishable from a natural person or real -world event;" (rule 2(1)(wa), as inserted)
- Quote: "(3) Due diligence in relation to synthetically generated information: (a) Where an intermediary offers a computer resource which may enable, permit, or facilitate the creation, generation, modification, alteration, publication, transmission, sharing, or dissemination of information as synthetically generated information, it shall ensure that,—" (rule 3(3), as inserted)
- Quote: "or, in the case of audio content, through a prominently prefixed audio disclosure, that can be used to immediately identify that such information is synthetically generated information" (rule 3(3)(a)(ii))
- Quote: "G.S.R. 120(E).–– In exercise of the powers conferred by sub -section (1), clauses (z) and (zg) of sub -section (2) of section 87 of the Information Technology Act, 2000" (notification of 10 Feb 2026; in force 20 Feb 2026 per rule 1(2))
- Notes: For audio, the label is "a prominently prefixed audio disclosure". A voice that sounds like a person falls within "indistinguishable from a natural person" (interpretation).

### E4.2 Does that duty reach a lender's own outbound call?
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `it-rules-amendment-2026-gsr120e-egazette-269993.txt`; `it-act-2000-indiacode-updated.txt` (s.2(1)(w)) | https://www.indiacode.nic.in/bitstream/123456789/13116/1/it_act_2000_updated.pdf | retrieved 2026-11-10
- Quote: intermediary, "with respect to any particular electronic records, means any person who on behalf of another person receives, stores or transmits that record or provides any service with respect to that record" (IT Act s.2(1)(w))
- Notes: Interpretation, not a ruling. The duty in rule 3(3) is addressed to "an intermediary" that "offers a computer resource" enabling creation or sharing of synthetic content, and rule 4(1A) to significant social media intermediaries. A bank or NBFC phoning its own customer with its own bot is not receiving, storing or transmitting records on behalf of another, so on its face it is not an intermediary. The rule could reach a platform offering synthetic-voice generation to others; whether a given vendor is an "intermediary" is not settled by the text. No call-opening duty is placed on the lender.

### E4.3 RBI FREE-AI committee report (Aug 2025): telling customers
- Claim as worded: "The bot says it is an AI, and the customer can ask for a human at any time." (DESIGN.md line 64)
- Status: verified (the report PDF is a mirror hosted by Medianama; RBI's own host is blocked by a captcha)
- Corrected wording: The AI line is recommended by RBI's FREE-AI committee, not required by an RBI direction.
- Source: `rbi-free-ai-committee-report-2025-08-13-medianama-mirror.txt` (para 4.4.54, printed p.58; Annexure IV); `rbi-press-release-61018-free-ai-report.txt` | https://www.medianama.com/wp-content/uploads/2025/08/Framework-for-Responsible-and-Ethical-Enablement-of-Artificial-Intelligence-FREE-AI-RBI-Report.pdf ; https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=61018 | retrieved 2026-11-10
- Quote: "Consumers must be explicitly informed whenever they are interacting with AI systems and should always have the option to switch to human representatives when they want. Firms should not be allowed to deceive customers by falsely claiming to be using AI. REs should ensure that AI-driven systems operate only through secure and verifiable channels such as verified 1601 series phone numbers for voice interactions" (para 4.4.54, printed p.58)
- Quote: "(i) May include awareness to customer when interacting with AI systems under para 8 “Guidance to customers and Disclosure of Information” of the master circular." (Annexure IV, item 4, proposed enhancement to the Master Circular on Customer Service in Banks)
- Quote: "the Committee has recommended a forward-looking approach, containing 26 actionable recommendations under six strategic pillars" (RBI press release 2025-2026/902, 13 Aug 2025, para 3)
- Notes: The strongest source on AI disclosure. It is a committee report with recommendations, not an RBI direction. The sentence is in the body text (para 4.4.54), not in the numbered Recommendation 18. Its "1601 series" for AI voice does not match the later allocation: TRAI's 10 Aug 2026 direction gives 1601 to non-BFSI sectors and 1600xx stays with lenders (E1.16). Use 1600xx. "Option to switch to human representatives" supports the ask-for-a-human element.

### E4.4 Has RBI issued anything binding on AI disclosure to customers since?
- Claim as worded: not in DESIGN.md.
- Status: unverifiable
- Corrected wording: Say "I found no RBI direction requiring it".
- Source: `rbi-free-ai-committee-report-2025-08-13-medianama-mirror.txt` (Recommendation 25); searched the saved RBI texts (Commercial Banks and NBFC RBC Directions 2025; Second, Third and Fourth Amendment Directions 2026; Credit Cards Directions 2025; Digital Lending Directions 2025; RBI/2024-25/105) for "artificial intelligence", "chatbot", "automated call", "robo", "AI", "interacting with" | retrieved 2026-11-10
- Quote: "Recommendation 25 – Disclosures by REs: REs should include AI -related disclosures in their annual reports and websites." (FREE-AI report, Recommendation 25)
- Notes: No hits in any saved RBI direction. Web search found only a draft model-risk guidance (consultation to 24 Jul 2026) and commentary that FREE-AI is advisory until RBI issues directions. I could not crawl every 2026 RBI circular, so one may exist that I did not see.

### E4.5 IndiaAI governance guidelines (MeitY, Nov 2025)
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `india-ai-governance-guidelines-2025-11-pib-doc2025115685601.txt` | https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc2025115685601.pdf | retrieved 2026-11-10
- Quote: "Provide disclosures and explanations that can be understood by the intended user and regulators." (principle "Understandable by Design")
- Quote: "India has developed a pragmatic approach to AI governance that is emphasised by a techno-legal framework supported by voluntary measures and Digital Public Infrastructure (DPI)." (summary)
- Notes: Principles and voluntary measures. No rule on announcing that a call is AI.

### E4.6 SEBI and IRDAI AI guidance
- Claim as worded: not in DESIGN.md.
- Status: secondary-only
- Corrected wording: none needed
- Source: web search only; not saved: https://www.business-standard.com/markets/news/sebi-proposes-ai-ml-guidelines-for-market-participants-125062001137_1.html ; https://startupfortune.com/sebi-is-preparing-to-make-ai-part-of-market-regulation/ | retrieved 2026-11-10
- Quote: none (the SEBI and IRDAI items come from news reports that were not saved)
- Notes: News reports describe a SEBI consultation paper (June 2025), a SEBI chair statement (June 2026) that guidelines are being prepared, and a June 2026 IRDAI working group on AI. None is a final rule on telling customers they are talking to an AI, and none governs an RBI-regulated lender. I did not look for the primary SEBI or IRDAI texts.

### E4.7 TRAI on AI disclosure to the person called
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `trai-tcccpr-3rd-amendment-2026-09-18-Regulation_18092026.txt`; `trai-pr-119-2026-third-amendment-tcccpr.txt` | URLs as in INDEX | retrieved 2026-11-10
- Quote: "A2P calls made without the required prior declaration will be treated as UCC." (TRAI PR 119/2026, para 4(ii)(b))
- Notes: The A2P regime requires the lender to tell its telecom provider it uses automated or artificial-voice calls. It does not require the bot to announce itself to the called person (searched, no such text).

### E4.8 Is AI disclosure on such a call a legal requirement?
- Claim as worded: "The bot says it is an AI, and the customer can ask for a human at any time." (DESIGN.md line 64)
- Status: unverifiable
- Corrected wording: "Disclosing that the call is AI is recommended by RBI's FREE-AI committee (a non-binding report) and is good practice. We found no Indian law or RBI direction that requires it for a lender's own outbound call."
- Source: `rbi-free-ai-committee-report-2025-08-13-medianama-mirror.txt` (para 4.4.54); see also E4.1-E4.7 and E1.15 | retrieved 2026-11-10
- Quote: "Consumers must be explicitly informed whenever they are interacting with AI systems and should always have the option to switch to human representatives when they want." (RBI FREE-AI Committee report, para 4.4.54)
- Notes: By source. Legal requirement: none found. Regulator-committee recommendation: FREE-AI para 4.4.54. Voluntary principle: IndiaAI guidelines. Telecom rule: declaration to the telecom provider only (E1.11, E1.15). IT Rules label duty: addressed to intermediaries (E4.2). Keep the AI line: it matches the one clear regulator statement, costs nothing, and the same paragraph warns against "falsely claiming to be using AI".

---

## E5. Identity check

### E5.1 Is there RBI guidance on authenticating a customer on an outbound call?
- Claim as worded: "Identity check. Synthetic: last 4 digits of the loan account, plus the date of birth." (DESIGN.md line 66)
- Status: unverifiable
- Corrected wording: Say "no RBI text prescribes how to authenticate a customer on an outbound call". Do not cite RBI for the choice of last four account digits plus date of birth.
- Source: searched `rbi-commercial-banks-rbc-directions-2025-notif13140.txt`, `rbi-nbfc-rbc-directions-2025-notif12942.txt`, `rbi-digital-lending-directions-2025-notif12848.txt`, `rbi-notification-12770-voice-calls-sms.txt` and the 2026 amendment directions for "authenticat", "date of birth", "telephone banking", "verify ... identity" | retrieved 2026-11-10
- Quote: none (negative finding; nothing to quote)
- Notes: The only hits are two-factor authentication for digital channels, KYC document checks and the senior-citizen date-of-birth conversion (para 116), none about an outbound call. Web search found no RBI text either.

### E5.2 RBI's public advice on sharing details with callers
- Claim as worded: "Identity check. Synthetic: last 4 digits of the loan account, plus the date of birth." (DESIGN.md line 66)
- Status: verified
- Corrected wording: Do not ask the customer to say account digits or other secrets on an outbound call.
- Source: `rbi-press-release-53185-consumer-awareness-fraud.txt` (press release 2021-2022/1630, 28 Jan 2022); `rbi-press-release-never-asks-2440.txt` | https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=53185 | retrieved 2026-11-10
- Quote: "Never share your account details such as account number, login ID, password, PIN, UPI-PIN, OTP, ATM / Debit card / credit card details with anyone, not even with bank officials, however genuine they might sound." (RBI press release 28 Jan 2022, "Safe digital banking practices")
- Quote: "Vishing - phone calls pretending to be from bank / non-bank e-wallet providers / telecom service providers in order to lure customers into sharing confidential details in the pretext of KYC-updation, unblocking of account / SIM-card, crediting debited amount, etc." (same)
- Quote: "Fraudsters attempt to get confidential details like user id, login / transaction password, OTP (one time password), debit / credit card details such as PIN, CVV, expiry date and other personal information." (same)
- Quote: "The Reserve Bank of India has today reiterated that it never contacts the public via unsolicited phone calls or emails asking for money or any other type of personal information." (older RBI press release)
- Notes: Account numbers are named in RBI's "never share" list. A bot that opens by asking for account digits and a date of birth looks like the vishing pattern RBI warns about, so customers following that advice should refuse, and a refusal is the right behaviour (interpretation). This is public awareness messaging, not a direction to lenders.

### E5.3 Is asking for a date of birth on an outbound call named as bad practice?
- Claim as worded: "Identity check. Synthetic: last 4 digits of the loan account, plus the date of birth." (DESIGN.md line 66)
- Status: unverifiable
- Corrected wording: Say "RBI's lists name account details, passwords, PINs, OTPs and card details; date of birth is not named, but falls under 'other personal information' in the vishing description". Do not say RBI bans asking for a date of birth.
- Source: `rbi-press-release-53185-consumer-awareness-fraud.txt`; `rbi-press-release-53372-beaware-booklet.txt` | retrieved 2026-11-10
- Quote: "The booklet emphasises the need for keeping one's personal information confidential at all times, being mindful of unknown calls / emails / messages, etc." (RBI press release on the BE(A)WARE booklet)
- Notes: The BE(A)WARE booklet PDF could not be fetched (RBI's PDF host is captcha-protected), so its own list was not checked for "date of birth". No saved primary text names date of birth.

### E5.4 Right-party and privacy rules in RBI conduct directions
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `rbi-2026-27-223-commercial-banks-rbc-fourth-amendment-recovery.txt` (para 454Y(1)); `rbi-2026-27-115-commercial-banks-rbc-second-amendment.txt` (para 85N(6)) | URLs as in E3.2 | retrieved 2026-11-10
- Quote: "An employee / recovery agent shall discuss the matters related to the loan dues and collection / recovery thereof only with the borrower / guarantor, as applicable." (RBI/2026-27/223, para 454Y(1))
- Quote: "respect the customer’s privacy and discuss the matters of her / his interest with any other individual only if the customer has given an explicit request or consent for sharing of such information;" (RBI/2026-27/115, para 85N(6))
- Notes: Both are written for recovery and sales staff, not a feedback call. They show RBI's expectation that loan matters are not discussed with anyone but the customer. For Samajh: say nothing account-specific until the right person is on the line, and end the call without disclosing the loan if someone else answers.

### E5.5 A verifiable way for the customer to check the caller
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: none needed
- Source: `rbi-notification-12770-voice-calls-sms.txt`; `trai-pr-91-2026-clarifications-1600-140-series.txt`; `rbi-press-release-53185-consumer-awareness-fraud.txt` | URLs as in INDEX | retrieved 2026-11-10
- Quote: "Provide the verified details of their customer care numbers to DIP for enabling DoT to publish them on the “Sanchar Saathi” portal" (RBI/2024-25/105, para 2)
- Quote: "A key objective of assigning designated series for these important communications is to make such calls trustworthy for the customers/ citizen." (TRAI PR 91/2026, para (i))
- Quote: "Fake numbers of banks / e-wallet providers on webpages / social media and displayed by search engines, etc." (RBI press release 28 Jan 2022, list of fraud methods)
- Notes: Calling from a registered 1600xx number, and telling the customer she can hang up and call the customer-care number printed on her loan papers, is the regulator-backed way to let her check the caller. The RBI warning about fake numbers on web pages argues for a number printed on the agreement or SMS, not one found by search.

### E5.6 Data minimisation for the identity check
- Claim as worded: "Identity check. Synthetic: last 4 digits of the loan account, plus the date of birth." (DESIGN.md line 66)
- Status: verified
- Corrected wording: none needed
- Source: `dpdp-act-2023-egazette-248045.txt` (s.6(1)) | https://egazette.gov.in/WriteReadData/2023/248045.pdf | retrieved 2026-11-10
- Quote: "be limited to such personal data as is necessary for such specified purpose" (s.6(1))
- Notes: From 13 May 2027, consent covers only personal data "necessary" for the purpose. If the open-recall answer (what she says she bought, and for how much) already shows she is the borrower, collecting a date of birth too is harder to justify. The demo uses synthetic data, so this concerns the product's real-world design.

---

## Grounded disclosure script

Elements the opening of the call must or should contain, in English. Tags: **LAW** = required by law (clause given); **REG** = recommended by a regulator (source given); **GOOD** = good practice only. "From 13 May 2027" means the DPDP duty is not yet in force. "Consent basis" means the lender relies on consent, not on s.7(a) (E2.5).

| # | Element | Tag | Basis |
|---|---|---|---|
| 1 | The call comes from the lender's registered 1600xx number | LAW | TRAI Direction 19 Nov 2025 para 8(iii); RBI/2024-25/105 para 2 (E1.8, E1.10). Not spoken; it is how the customer sees who is calling |
| 2 | Who is calling: lender name, "customer-care team", the loan by month | GOOD | No clause fixes the wording. Matches RBI's fraud advice that the bank states facts (E5.2, E5.5) |
| 3 | Why: a feedback call about a product bought in the last 30 days, "as RBI asks lenders to do" | LAW from 13 May 2027 (consent basis); GOOD now | DPDP s.5(1)(i) and Rules r.3(b)(ii) need the purpose in the notice (E2.3). RBI 85Y / 101Y is the reason for the call, not a script rule (E3.1) |
| 4 | Not a sales call; nothing will be offered or sold | LAW (absence of sales content); GOOD (saying it) | TCCCPR clause (av) proviso: promotional content mixed in makes the call promotional; RBI/2024-25/105 Annexure: "no mixing" (E1.2, E1.7). RBI 85L needs explicit consent for promotional communication (E3.6) |
| 5 | It is an automated / AI voice | REG (committee); not LAW | RBI FREE-AI report para 4.4.54 (E4.3). No Indian law found requires it (E4.8). The telecom duty is to declare A2P use to the telecom provider, not to the customer (E1.11) |
| 6 | The call is recorded, and why ("to keep an accurate record of your feedback and review our products") | REG by analogy; LAW from 13 May 2027 (consent basis) | RBI recovery paras 442(4) / 454P: "intimating ... that the conversation is being recorded", which apply in terms to recovery calls only (E3.2). DPDP notice must state the purpose of processing (E2.3, E2.8) |
| 7 | She can say "stop" or decline at any time | LAW from 13 May 2027 (consent basis); GOOD now | DPDP s.6(4): withdraw consent at any time, as easily as it was given (E2.4) |
| 8 | She can ask for a human at any time | REG (committee) | FREE-AI para 4.4.54: "option to switch to human representatives" (E4.3) |
| 9 | Language choice: the call in the language she picks; the written notice in English or an Eighth Schedule language | LAW from 13 May 2027 (notice); GOOD (call language) | DPDP s.5(3), s.6(3) (E2.6). Hinglish is not an Eighth Schedule language |
| 10 | A pointer to the full written notice (SMS or link): data used, purpose, how to withdraw, how to complain | LAW from 13 May 2027 (consent basis) | DPDP s.5(1) and Rules r.3(c) (E2.3) |
| 11 | A callback number: "you may hang up and call the customer-care number on your loan papers" | LAW from 13 May 2027 (contact of DPO or authorised person); REG; GOOD | DPDP s.6(3) (E2.6); RBI/2024-25/105 para 2 puts verified customer-care numbers on Sanchar Saathi (E5.5) |
| 12 | Calling window 10:00-19:00 customer-local | GOOD only | No RBI or TRAI hour limit applies in terms to a feedback call; this is the intersection of the recovery, sales and card rules (E3.5, E1.14) |
| 13 | What the bot will not ask for: OTP, PIN, CVV, password, account number | REG | RBI press release 28 Jan 2022: "Never share your account details ... not even with bank officials" (E5.2) |
| 14 | Nothing about the loan is said until she confirms she is the right person; if someone else answers, end the call without disclosing the loan | REG by analogy; GOOD | RBI/2026-27/223 para 454Y(1); RBI/2026-27/115 para 85N(6) (E5.4) |

## Could not retrieve

| What | URLs tried | Result |
|---|---|---|
| RBI FREE-AI report from RBI's host | `https://rbidocs.rbi.org.in/rdocs/PublicationReport/PDFs/FREEAIR130820250A24FF2D4578453F824C72ED9F5D5851.PDF` ; `https://rbidocs.rbi.org.in/rdocs/content/pdfs/FREEAIR13082025_ANVI.pdf` ; web.archive.org copies | rbidocs returns an HTML captcha page; web.archive.org returned HTTP 429, then "Temporarily Offline". Used the Medianama-hosted copy (mirror). |
| RBI circulars and directions as PDF | `https://rbidocs.rbi.org.in/rdocs/Notification/PDFs/...` (RBI/2026-27/115, RBI/2024-25/105); `https://website.rbi.org.in/documents/...` | HTML captcha page or empty HTML shell. Used the full-text HTML pages on `www.rbi.org.in`. |
| RBI BE(A)WARE booklet PDF | `https://website.rbi.org.in/documents/87730/39016390/BEAWARE07032022.pdf` | HTML shell, no PDF. Only the RBI press release about it was saved. |
| DPDP Act PDF on India Code | `https://www.indiacode.nic.in/bitstream/123456789/22037/2/a2023-22.pdf` ; `.../22037/1/a2023-22.pdf` | HTTP 504 twice. Used the egazette copy. |
| DPDP Act PDF on MeitY | `https://www.meity.gov.in/writereaddata/files/Digital%20Personal%20Data%20Protection%20Act%202023.pdf` | HTTP 404. |
| RBI circular mirror | `https://www.pdicai.org/Docs/RBI-2024-25-105_1812025145839888.pdf` | Connection failed (curl code 000). |
| TCCCPR 2018 at first URL | `https://trai.gov.in/sites/default/files/RegulationUcc19072018.pdf` | HTTP 404. Found at `.../2024-09/RegulationUcc19072018.pdf`. |
| SPDI Rules 2011 on MeitY | `https://www.meity.gov.in/writereaddata/files/GSR313E_10511%281%29_0.pdf` | HTTP 404. Used the PRS India copy (mirror). |
| DoT instruction of 23 Dec 2024 (1600 allocation) | web search of dot.gov.in, trai.gov.in, pib.gov.in | Not found. The TRAI direction (para 4) and a DoT letter of 11 Feb 2025 cite it. |
| Gazette publication date of the TRAI Third Amendment | egazette.gov.in (no search possible by curl) | Not found. The TRAI copy says "TO BE PUBLISHED IN THE GAZETTE". Dates are computed (E1.12). |
| TRAI direction of 16 Dec 2025 for IRDAI-regulated entities | `https://trai.gov.in/sites/default/files/2025-12/Direction_16122025.pdf` (seen in search, not downloaded) | Only press release PR 151/2025 saved. |
| TRAI "draft" on AI-voice disclosure (vendor blogs) | search only | No TRAI document found. Unverified. |
| SEBI and IRDAI AI guidance, primary texts | news search only | Not looked for in primary form (E4.6). |
| Any RBI circular after Oct 2026 on AI disclosure | search only | None found; RBI's site cannot be crawled fully (E4.4). |

## Product implications (most important first)

1. **The call must come from a 1600xx number, with no promotional content.** All three RBI phase dates have passed. TRAI bars a regulated lender from service or transactional calls from any other number "even with the explicit or inferred consent of customers" (E1.10). A promotional element turns the call into a promotional call, which needs 140xx and consent (E1.2). The demo uses a simulated phone, but the design and pitch should say "1600xx" and show a script with no sell-in.
2. **Tell the telecom provider the call is automated.** The TRAI Third Amendment makes A2P use (autodialling, robo, pre-recorded or artificial voice) declarable in advance with CLI ranges; undeclared calls are "treated as UCC". It starts about 17 Nov 2026 if gazetted 18 Sep (E1.11, E1.12). The memorandum says it applies to all A2P calls, so do not rely on "feedback is not commercial".
3. **DPDP notice and consent arrive on 13 May 2027, after RBI 85Y starts on 1 Jan 2027.** Build the opening to the future standard: purpose, recording, a pointer to a full written notice in the customer's language, and a clear way to say no or ask for a human. An RBI direction does not automatically replace consent (E2.5). Until May 2027, IT Act s.43A and the SPDI Rules apply.
4. **Replace "last four digits plus date of birth" with a right-party check and facts the bank states.** RBI's public advice says never share account details "not even with bank officials", and its vishing description matches an unknown caller asking for personal details (E5.2). No RBI text prescribes outbound authentication (E5.1). Alternative: call from the registered 1600xx number; open with lender name, loan month and purpose, all stated by the bank; ask only "am I speaking with <first name>?"; say nothing account-specific until she confirms; tell her she can hang up and call the number on her loan papers (E5.5). The open-recall answer then supports identity without a secret (interpretation).
5. **Do not say "RBI requires the AI line" or "RBI requires recording the feedback call".** AI disclosure is a FREE-AI recommendation (para 4.4.54), not a rule (E4.3, E4.8). RBI's recording-and-intimation duty is in the recovery paragraphs (E3.2). Keep both as good practice and say why the call is recorded (to keep a record of the feedback and review products, as RBI requires).
6. **Use a conservative calling window: 10:00-19:00 customer-local.** No RBI hour limit applies in terms to a feedback call; the intersection of the recovery (08:00-19:00), sales (09:00-19:00) and card (10:00-19:00) rules is 10:00-19:00 (E3.5, E1.14).
7. **Decide retention and processor contracts in writing.** DPDP Rules set a one-year floor for logs and processing data (Rules 6(1)(e), 8(3)); the Act requires erasure when the purpose ends (s.8(7)). RBI sets six months for recovery-call recordings and one year after contract end for consent records, and nothing for 85Y audio (E2.8). Gnani and any LLM provider are processors needing a contract.
8. **No voiceprints, no cloning.** Under the SPDI Rules "voice patterns ... for authentication purposes" are biometric (sensitive) data, and RBI's Digital Lending Directions bar storing biometric data (E2.9).
9. **Where transcripts go may matter.** For digital lenders, Digital Lending Directions 13(iv) requires storage in India and deletion within 24 hours of processing abroad. Check before sending transcripts to a foreign-hosted LLM (E2.9).
10. **Wording changes for DESIGN.md section 11.** Add to "We can say": "post-sale feedback calls fall in no TRAI category by name; we treat them as service calls from 1600xx"; "AI disclosure is a FREE-AI recommendation". Add to "We can't say": "TRAI requires AI voice disclosure", "RBI requires recording of 85Y calls", "consent is not needed because RBI directs the call".
