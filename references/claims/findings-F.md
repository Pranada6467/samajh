# Findings F: identity on an outbound call (package P8)

Research date: 2026-11-10. Four researchers, one per part; each section below is that researcher's report, unchanged
except for the heading levels. Sources are under `sources/F/` (prefixes `reg-`, `prac-`, `vend-`, `intl-`, `kba-`);
quotes marked E or C come from files already saved under `sources/E/` or `sources/C/`. The short version, the menu
and the allowed and banned wording are in `references/pilots/identity-check-research.md` and Part 1 of the ledger.
A vendor's or an institution's page is first-hand evidence of what it publishes, never of what happens on a call.

## F1: what Indian regulators say (RBI, TRAI/DoT, DPDP, IRDAI)

### F1.1 RBI: no direction says how to establish the right party on an outbound call
- Claim as worded: "Identity check. Synthetic: last 4 digits of the loan account, plus the date of birth." (DESIGN.md line 66; same claim as E5.1)
- Status: unverifiable (a negative finding that confirms and extends E5.1)
- Corrected wording: "No RBI direction I could find prescribes how a regulated entity or its agent must confirm it is speaking to the customer on an outbound call (service, feedback, recovery or telemarketing)." Do not cite RBI for any identity-check method.
- Source: searched `sources/E/rbi-commercial-banks-rbc-directions-2025-notif13140.txt`, `rbi-nbfc-rbc-directions-2025-notif12942.txt`, `rbi-commercial-banks-credit-debit-cards-directions-2025-notif13155.txt`, `rbi-md-credit-debit-card-2022-updated-2024-03-07-notif12300.txt`, `rbi-2026-27-223-commercial-banks-rbc-fourth-amendment-recovery.txt` and `rbi-2026-27-230-nbfc-rbc-third-amendment-recovery.txt` for: identity card, authorisation letter, telemarketer, telephone banking, IVR, call back, tele-caller, "identify themselves". Also two web searches (phone-banking authentication; BE(A)WARE) | retrieved 2026-11-10
- Quote: "The card-issuer’s representatives shall contact the customers only between 10:00 hrs and 19:00 hrs." (E; Credit Cards and Debit Cards Directions 2025, card-issuer item (9), the only telemarketing rule in them)
- Quote: "not engage telemarketers (DSAs / DMAs) who do not have any valid registration certificate from DoT, Government of India, as telemarketers" (E; NBFC RBC Directions 2025, para 101(1))
- Notes: The card and NBFC telemarketing rules cover registration, TRAI compliance and calling hours. They say nothing about who is on the line, what the caller must say, or what the customer may be asked. I did not fetch the stand-alone Commercial Banks Managing Risks in Outsourcing Directions 2025. I only read the recovery paragraphs that cross-refer to them (see F1.2). A web search found no RBI call-centre authentication circular. It surfaced a rule on OTPs for customer-initiated phone-banking transactions (RBI file CKUI0209013E). I could not fetch that file (see section c), so it is unverified. It would concern inbound customer transactions, not outbound calls.

### F1.2 RBI recovery directions: how the lender's agent is made identifiable
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: "RBI makes a lender identify its recovery agent to the borrower in advance (notice, authorisation letter, agent's identity card) and, for visits, makes the agent show the identity card. It prescribes no phone-call self-identification script, and no identity check on the borrower."
- Source: `sources/E/rbi-commercial-banks-rbc-directions-2025-notif13140.txt` (para 414); `rbi-nbfc-rbc-directions-2025-notif12942.txt` (para 95); `rbi-2026-27-223-commercial-banks-rbc-fourth-amendment-recovery.txt` (paras 454L, 454P, 454X) | URLs in `sources/E/INDEX.md` | retrieved 2026-11-10
- Quote: "To ensure due notice and appropriate authorisation, an NBFC shall provide the details of recovery agents to the borrower while initiating the process of recovery. The agent shall also carry a copy of the notice and the authorisation letter from the NBFC along with the identity card issued to her / him by the NBFC or the agency." (E; NBFC RBC Directions 2025, para 95; commercial banks para 414 is the same)
- Quote: "shall identify themselves by displaying their identity card issued by the bank and recovery agency, respectively." (E; RBI/2026-27/223, para 454X; the sentence begins "while visiting the borrower / guarantor")
- Quote: "The authorisation letter and the notice shall, among other details, include the telephone number of the recovery agency and the grievance redressal officer appointed by the bank" (E; para 454X)
- Quote: "the bank shall intimate the details of the recovery agency to the borrower / guarantor at least one day prior to the first visit." (E; para 454L, for in-person visits)
- Quote: "the bank shall take reasonable precautions such as intimating the borrower / guarantor that the conversation is being recorded" (E; para 454P)
- Notes: Para 454X is written for visits, and 454L for in-person recovery. Para 414 / 95 is general: the borrower gets the agent's details when recovery starts. E5.4 already covers 454Y(1). The 2026 amendments take effect 1 Jan 2027 (per the `sources/E` INDEX). For Samajh (a service call, not recovery): the closest regulator-backed practice is that the customer can match the caller to a notice or letter the lender sent earlier, plus a recording notice. There is no rule for the bot to state its own identity beyond this.

### F1.3 RBI BE(A)WARE: what impostors do on calls, and what a genuine entity never asks
- Claim as worded: not in DESIGN.md (follows E5.2 and E5.3, which could not read the booklet).
- Status: verified
- Corrected wording: "RBI's BE(A)WARE booklet (Mar 2022) says genuine banks, financial institutions and RBI never ask customers to share username, password, card details, CVV or OTP. It also says impostors on calls share the customer's name or date of birth to gain confidence." Do not say RBI lists date of birth as something a bank never asks for. Do say a caller knowing the customer's name and date of birth is described as an impostor tactic.
- Source: `sources/F/reg-rbi-beaware-booklet.txt` (Part A, item 2 "Vishing calls", booklet p.4; Glossary) | https://web.archive.org/web/20220307100628id_/https://rbidocs.rbi.org.in/rdocs/content/pdfs/BEAWARE07032022.pdf (archived capture of https://rbidocs.rbi.org.in/rdocs/content/pdfs/BEAWARE07032022.pdf) | retrieved 2026-11-10
- Quote: "To gain confidence, imposters share a few customer details such as the customer’s name or date of birth." (Part A item 2, Modus Operandi)
- Quote: "Bank officials / financial institutions / RBI / any genuine entity never ask customers to share confidential information such as username / password / card details / CVV / OTP." (Part A item 2, Precautions)
- Quote: "imposters pressurize / trick customers into sharing confidential details such as passwords / OTP / PIN / Card Verification Value ( CVV) etc., by citing an urgency / emergency" (same; the text layer has the stray space inside "( CVV)")
- Quote: "Vishing: It refers to phone calls pretending to be from bank / non-bank e-wallet providers / telecom service providers luring customers into sharing confidential details in the pretext of KYC-updation, unblocking of account / SIM-card, crediting debited amount, etc." (Glossary)
- Notes: The PDF came from a Wayback capture of RBI's own host (2022-03-07 10:06 UTC); the live host serves a captcha. An earlier copy hosted on taxguru (`reg-secondary-taxguru-beaware-booklet.txt`, secondary) words the same entry slightly differently. It says impostors "seek confirmation of the secure credentials by sharing few details such as name or date of birth to gain confidence" (a different version of the booklet; not quoted in this finding). This extends E5.3: date of birth is named, but as a thing impostors share, not in the "never ask" list.

### F1.4 RBI BE(A)WARE: how the customer should check a caller or number
- Claim as worded: not in DESIGN.md (extends E5.5).
- Status: verified
- Corrected wording: "RBI tells customers to take customer-care numbers from the bank's or company's official website, not from a search engine, and notes that customer-care numbers are never mobile numbers. For loan offers by phone it says to cross-check through other sources. The booklet does not say 'hang up and call back'."
- Source: `sources/F/reg-rbi-beaware-booklet.txt` (Part A item 8 "search engines", p.5 of the booklet; Part B items 2 and 3) | same URL as F1.3 | retrieved 2026-11-10
- Quote: "Always obtain the customer care contact details from the official websites of banks / companies." (Part A item 8)
- Quote: "Do not call the numbers directly displayed on the search engine results page as these are often camouflaged by fraudsters." (Part A item 8)
- Quote: "Please also note that customer care numbers are never in the form of mobile numbers." (Part A item 8)
- Quote: "Never believe loan offers made by people on their own through telephones / emails, etc." (Part B item 2)
- Quote: "Never make any payment against such offers or share any personal / financial credentials against such offers without cross-checking that it is genuine through other sources." (Part B item 2)
- Notes: The 'not a mobile number' line fits the 1600xx rule (E1.8, E1.10): a customer following RBI advice should distrust any 10-digit mobile caller who says they are the lender. Searched the text for "call back" and "hang up": no hit.

### F1.5 Does any RBI awareness list name date of birth, year of birth, PIN code, address or mother's maiden name?
- Claim as worded: not in DESIGN.md (extends E5.3).
- Status: verified (negative, limited to the texts searched)
- Corrected wording: "No saved RBI awareness text names date of birth, year of birth, PIN code/postal code, address or mother's maiden name in a list of things never to share or never asked on a call." In RBI's lists the named items are credentials (username, password, card details, CVV, OTP, PIN, UPI-PIN) and, in E5.2, account number and login ID. Date of birth appears in the booklet only as an impostor's trust-building detail and as a poor password.
- Source: grep of `sources/F/reg-rbi-beaware-booklet.txt`, `sources/E/rbi-press-release-53185-consumer-awareness-fraud.txt`, `rbi-press-release-never-asks-2440.txt`, `rbi-press-release-53372-beaware-booklet.txt`, `rbi-notification-12770-voice-calls-sms.txt` for "mother", "maiden", "pin code", "pincode", "postal code" (0 hits in all five) and "birth" (booklet only: 2 hits) | retrieved 2026-11-10
- Quote: "Avoid having you date of birth, spouse name, car number etc. as passwords." (booklet, Part C, "For password security")
- Notes: The "Raju and the forty thieves" booklet could not be read (F1.12), so this negative covers the BE(A)WARE booklet and the saved press releases only. Year of birth alone appears nowhere. DESIGN.md's year-of-birth second check is neither endorsed nor banned by any RBI text found. The risk is by analogy with F1.3.

### F1.6 TRAI / DoT: calling-name display (CNAP) is a recommendation, not live
- Claim as worded: not in DESIGN.md.
- Status: verified (the content of the recommendations); whether CNAP is operating on 2026-11-10: unverifiable
- Corrected wording: "India's phone networks display only the calling number. TRAI recommended in Feb 2024 that a verified calling name be shown; DoT's view (Sep 2025) is that it should be on by default with an opt-out; TRAI replied on 28 Oct 2025. I found no DoT order setting a start date. Do not tell customers the caller's name will appear on their phone."
- Source: `sources/F/reg-trai-cnap-response-2025-10-28.txt`; `sources/F/reg-trai-cnap-recommendations-2024-02-23.txt` | https://www.trai.gov.in/sites/default/files/2025-10/Response_CNAP_28102025.pdf ; https://www.trai.gov.in/sites/default/files/2024-11/Recommendation_23022024_0.pdf | retrieved 2026-11-10
- Quote: "Presently, in Indian Telecom Networks, only the mobile/ landline numbers are being displayed as Calling Line Identification (CLI) during incoming calls." (DoT reference of 21.03.2022, quoted in TRAI's 28 Oct 2025 response, para 1.2)
- Quote: "CNAP is the supplementary service which enables the called party to receive the calling name information of the calling party." (same, para 1.2)
- Quote: "CNAP service shall be available by default to called party and if any subscriber (called party) does not require it then he/she may request to disable it as per procedure." (DoT's view on Recommendation 3.1, quoted in the response, para 2.2)
- Quote: "The calling name (CNAM) of each telephone subscriber should be provided by the originating access service providers." (TRAI recommendation 2.27(c), 23 Feb 2024)
- Quote: "in case of telephone calls originating from 140 level numbers allocated to registered telemarketers, and any other number series allocated for making transactional or service related calls, the name information of the subscriber entity should, invariably, be presented to the called party." (TRAI recommendation 2.109, 23 Feb 2024)
- Notes: The 28 Oct 2025 response covers only recommendations 3.1, 3.3, 3.4, 3.5 and 3.9, and 2.109 is not among them. I did not establish what DoT decided on 2.109. The name source is the subscriber's CAF (KYC record); businesses may use a registered trade or trademark name as a 'preferred name' (recommendation 2.118). Web search summaries (not saved) say the TRAI status page lists CNAP as under government consideration and describe operator pilots; I could not confirm either from a primary source. Status on the research date therefore rests on the absence of a DoT order in my search.

### F1.7 DoT Sanchar Saathi: Trusted Contact Details (check a number) and Chakshu (report a caller)
- Claim as worded: not in DESIGN.md (extends E5.5).
- Status: verified
- Corrected wording: "DoT's Sanchar Saathi portal has a 'Trusted Contact Details' module in which a citizen can check whether a number they are calling, or receiving a call from, is an authentic contact of a bank or financial institution. Its 'Chakshu' module lets them report a suspected fraud call, SMS or WhatsApp message; it is not for reporting a loss (that goes to 1930 / cybercrime.gov.in)." Do not say every lender's number is listed. The module shows information 'as provided by the stakeholders'.
- Source: `sources/F/reg-sancharsaathi-home.txt` (home page and FAQ); `sources/F/reg-pib-chakshu-2026-02-05.txt` | https://sancharsaathi.gov.in/ ; https://www.pib.gov.in/PressReleasePage.aspx?PRID=2223779&reg=3&lang=1 | retrieved 2026-11-10
- Quote: "Trusted Contact Details helps citizens verify official contact information such as customer care numbers, toll-free numbers, email IDs, and genuine website links of important stakeholders, like banks and financial institutions." (Sanchar Saathi home page)
- Quote: "The module enables citizens to check whether a contact number they are calling -or receiving a call from- belongs to an authentic source." (same)
- Quote: "The module provides verified information, as provided by the stakeholders, such as their official contact numbers, toll-free numbers, customer care numbers, email IDs, and genuine website details of important stakeholders like banks and financial institutions." (FAQ)
- Quote: "Chakshu facilitates citizens to report the suspected fraud communications with the intention of defrauding telecom service users for cyber-crime, financial frauds, non-bonafide purpose like impersonation or any other misuse through Call, SMS or WhatsApp." (home page)
- Quote: "It may be noted that 'Chakshu' is not a facility for reporting about financial fraud or cyber-crime cases." (home page)
- Quote: "Provide the verified details of their customer care numbers to DIP for enabling DoT to publish them on the “Sanchar Saathi” portal" (E; RBI/2024-25/105, para 2, already E1.8 and E5.5)
- Notes: RBI/2024-25/105 tells regulated entities to supply their customer-care numbers for publication on the portal. That is the regulator-backed route for a customer to check a number, tied to the lender's own numbers. The PIB release of 5 Feb 2026 (Rajya Sabha reply) is the primary statement that Sanchar Saathi has a web portal and app, and describes the Digital Intelligence Platform, "a secure online platform, for bi-directional information sharing among stakeholders". Whether a particular lender's 1600xx numbers are listed was not checked.

### F1.8 DPDP Act 2023 and Rules 2025: telling a non-borrower that a loan exists
- Claim as worded: not in DESIGN.md.
- Status: verified (the texts); not in force on 2026-11-10 (the operative duties start 13 May 2027)
- Corrected wording: "Under the DPDP Act, a personal data breach includes 'accidental disclosure' of personal data that compromises its confidentiality; a lender must take reasonable security safeguards against it (s.8(5)) and process personal data only for a lawful purpose (s.4(1)). Telling someone who is not the borrower that a loan exists would, on my reading, be such a disclosure. No regulator or Board decision applies the Act to a third party answering a call. These duties start on 13 May 2027, so on 2026-11-10 they are not in force. Until then the IT Act s.43A and SPDI Rules apply (E2.9). RBI's own right-party rule applies now (F1.2, E5.4)."
- Source: `sources/E/dpdp-act-2023-egazette-248045.txt` (ss.2(u), 4(1), 8(5), 8(6)); `sources/E/dpdp-rules-2025-egazette-267650.txt` (rules 1, 7); `sources/E/dpdp-act-commencement-gsr843e-2025-11-13-egazette-267647.txt` | URLs as in E2.1 | retrieved 2026-11-10
- Quote: "“personal data breach” means any unauthorised processing of personal data or accidental disclosure, acquisition, sharing, use, alteration, destruction or loss of access to personal data, that compromises the confidentiality, integrity or availability of personal data;" (E; Act s.2(u))
- Quote: "A Data Fiduciary shall protect personal data in its possession or under its control, including in respect of any processing undertaken by it or on its behalf by a Data Processor, by taking reasonable security safeguards to prevent personal data breach." (E; s.8(5))
- Quote: "A person may process the personal data of a Data Principal only in accordance with the provisions of this Act and for a lawful purpose" (E; s.4(1))
- Quote: "In the event of a personal data breach, the Data Fiduciary shall give the Board and each affected Data Principal, intimation of such breach in such form and manner as may be prescribed." (E; s.8(6))
- Quote: "On becoming aware of any personal data breach, the Data Fiduciary shall, to the best of its knowledge, intimate to each affected Data Principal, in a concise, clear and plain manner and without delay" (E; Rules, rule 7(1))
- Quote: "(c) eighteen months from the date of publication of this gazette, on which the provision of sections 3 to 5, sub-sections (1) to (8) and (10) of section 6,sections 7 to 10, sections 11 to 17" (E; G.S.R. 843(E), 13 Nov 2025; the quote is cut short, and the clause goes on to name further sections)
- Quote: "(4) Rules 3, 5 to 16, 22 and 23 shall come into force eighteen months after the date of publication of this Gazette." (E; Rules, rule 1(4); this includes rule 7)
- Quote: "(a) the date of publication of this notification in the Official Gazette as the date on which the provisions of sub-section (2) of section 1, section 2, sections 18 to 26" (E; G.S.R. 843(E); s.2, the definitions, is in force)
- Notes: Gazette date 13 Nov 2025 gives 13 May 2027 for ss.3-5, 6(1)-(8), 7-10 and Rules 3, 5-16 (E2.2). s.2(u) is in force as a definition but bites only through operative sections. Rule 7 breach notice and the Board's 72-hour report apply from 13 May 2027. "Reasonable security safeguards" are not defined for a misdirected call; applying the definition to a third-party answer is my interpretation.

### F1.9 IRDAI PIVC circular: no identity data points, and now superseded
- Claim as worded: not in DESIGN.md (follows C1.x on PIVC; the question is whether it prescribes identity checks).
- Status: verified (negative on identity data points)
- Corrected wording: "IRDAI's PIVC circular of 12 May 2020 only encourages life insurers to run pre-issuance verification calls; it specifies no identity data points or number of checks. It is listed among the circulars superseded by IRDAI's Master Circular on Protection of Policyholders' Interests of 5 Sep 2024. Neither the 2024 master circular nor the 2024 operations regulations nor the 2024 life-products master circular, as saved, contains a PIVC or identity-check procedure."
- Source: `sources/C/irdai-circular-pivc-116-05-2020.txt`; `sources/C/irdai-annexure-1-to-circular-274-11-2020.txt`; `sources/C/irdai-master-circular-ppi-2024-bilingual.txt` (Ch. IX, item 27); grep of `irdai-ppi-operations-regulations-2024.txt` and `irdai-master-circular-life-insurance-products-2024-en.txt` for "welcome call", "verification call", "pre-issuance", "PIVC", "distance marketing" | URLs in `sources/C/INDEX.md` | retrieved 2026-11-10
- Quote: "all Life Insurers are encouraged to conduct Pre-Issuance Verification Call (PIVC) to the extent possible and certainly in important cases." (C; circular para 2)
- Quote: "31.1. This Master Circular supersedes the following Guidelines/Circulars:" (C; Master Circular 2024, Ch. IX)
- Quote: "27. IRDAI/Life/Misc/CIR/116/05/2020 Circular on Pre-Issuance Verification Call (PIVC)" (C; same list)
- Quote: "Statement of Grievances in respect of policies sold with OTP Authentication in lieu of wet signature on physical Proposal form, BI, Suitability Assessment" (C; Annexure 1 to circular 274/11/2020; a monthly grievance-reporting template, not an identity check)
- Notes: This repeats C's finding that the PIVC is only "encouraged" and superseded. The new point is that I found no data points, no count and no method in any saved IRDAI text. Nothing supports "IRDAI requires date of birth plus N other items". The annexure to 274/11/2020 concerns OTP-based consent and its grievance reporting, not caller identity.

### F1.10 IRDAI 2011 distance-marketing guidelines: what the telephone caller must disclose, and verification calls
- Claim as worded: not in DESIGN.md.
- Status: verified (text); whether still in force unverified
- Corrected wording: "IRDAI's 2011 distance-marketing guidelines require a telephone solicitor to state the insurer's name and the purpose, give the caller's name, indicate the language options, and tell the client the call is recorded. They also require insurers to make verification calls to at least 3% of distance-marketing buyers each month, to check that the client understood the product, using a standardised script. They set no identity check on the person who answers."
- Source: `sources/C/irdai-guidelines-distance-marketing-2011.txt` (paras 9.2, 9.3, and the verification-call clause); `sources/C/irdai-ppi-regulations-2017.txt` | https://policyholder.gov.in/en/distance-marketing | retrieved 2026-11-10
- Quote: "The communication shall clearly highlight the name of the insurer." (C; para 9.2(i))
- Quote: "In case of telephonic solicitation the name of the caller shall be disclosed and the language options available must be indicated." (C; para 9.3(iii))
- Quote: "Tele callers shall inform clients that the call is being recorded and that the client is entitled to a voice copy" (C; para 9.3(iv))
- Quote: "Insurers shall make verification calls, to monitor the quality of sales, to a minimum of 3% of the policyholders who purchase insurance over distance marketing mode, every month." (C; verification-call clause)
- Quote: "The purpose of verification calls is to ascertain whether the client has understood the benefits, features and disclosures of the product purchased correctly. Verification calls shall also bear a standardized script" (C; same clause)
- Quote: "Care should be exercised to ensure that the prospect contacted has clarity as to the identity of the insurer, the distribution channel, the product, benefits and conditions of offer etc." (C; 2017 PPI Regulations, repealed by the 2024 Regulations; kept for history)
- Notes: The text layer has stray spaces inside words (OCR); quotes are given with normal spacing and match once whitespace is ignored. The 2011 guidelines are not in the 2024 Master Circular's repeal list (see findings-C), but the intermediary regulations were amended after 2015/2017 and I did not check each amendment, so do not call these provisions current without a check. For an insurance-linked Samajh variant: a post-sale verification call that tests understanding with a fixed script is something IRDAI's text describes (as a quality check), and the caller must name itself and say the call is recorded. This is the only saved regulator text that asks for the purpose Samajh's call serves, for distance-marketing sales.

### F1.11 IRDAI on spurious calls: what the regulator and insurers never do, and how to verify a caller
- Claim as worded: not in DESIGN.md.
- Status: verified
- Corrected wording: "IRDAI's public notice of 9 Sep 2019 says IRDAI does not sell insurance or announce bonuses; that anyone using an IRDAI ID to propose a sale is fraudulent; and that before any financial transaction based on a phone conversation the caller's identity should be verified at the insurer's authorised offices or call centres, whose numbers are in the policy documents and on the insurer's official website. The 2024 master circular repeats the caution. IRDAI's notice does not list data items an insurer never asks for."
- Source: `sources/F/reg-irdai-public-notice-spurious-calls-2019-09-09.txt` | https://irdai.gov.in/documents/37343/1358307/Spurious+Phone+Calls+and+Fictitious+_+Fraudulent+Offers_PUBLIC+NOTICE.pdf/88457f78-650d-010c-4f7c-43557ec4daac?version=2.1&t=1662752931535 ; `sources/C/irdai-master-circular-ppi-2024-bilingual.txt` (Ch. VII item 1, p.111-112) | retrieved 2026-11-10
- Quote: "IRDAI advises that before making a financial transaction based on the telephonic conversations it is necessary to verify the identity of the caller. The facts can be verified at authorized offices / call centers of insurance companies. The telephone numbers of the authorized call centers can be verified in the policy documents/official websites of insurer." (2019 notice, para 4)
- Quote: "IRDAI/IGMS does not involve directly or through any representative in sale of any kind of insurance or financial products." (2019 notice, para 3)
- Quote: "If any person approaches with an ID of IRDAI/IGMS and proposes sale of insurance products or provides any inducement by way of money or in kind, that person is a fraudulent person" (2019 notice, para 3)
- Quote: "Policyholders or the prospects should be aware of spurious phone calls and fictitious / fraudulent offers through messages or any other means of communication." (C; Master Circular 2024, Ch. VII.1(i))
- Quote: "IRDAI or its officials do not involve in any activities of insurance business like selling insurance policies, announcing bonus or investment of premiums, refund of amounts." (C; same, VII.1(ii))
- Quote: "CAD/01/10-11 DATED 21.01.2011 Verification of the Authenticity of calls" (C; Master Circular 2024, repeal list item 6)
- Notes: The 2019 notice is the one IRDAI text that tells the customer how to verify a caller (the insurer's call-centre number from policy documents or website). The 21 Jan 2011 circular "Verification of the Authenticity of calls" was superseded in 2024 and I could not read it (see section c); news summaries say it concerned impostors claiming to be IRDA staff, not insurers' own outbound calls. I ran one search for a newer IRDAI notice and found none.

### F1.12 "RBI Kehta Hai" site and the "Raju and the forty thieves" booklet
- Claim as worded: not in DESIGN.md.
- Status: unverifiable
- Corrected wording: "I could not read any RBI Kehta Hai page or the pictorial 'Raju and the forty thieves' booklet, so nothing from them is cited. The BE(A)WARE booklet (F1.3 to F1.5) is the text read."
- Source: URLs in section (c) | retrieved 2026-11-10
- Quote: none
- Notes: RBI's foreword to the Raju booklet (seen in a bank-hosted copy) calls it a pictorial companion to BE(A)WARE, with forty stories and do's and don'ts. Its "2. VISHING CALLS" page is an image with no text layer, so there is nothing to quote. A reader should view the PDF by eye if the point matters.

## F2: what Indian lenders and insurers publish

### F2.1 Data points checked on an outbound call: not published
- Claim as worded: not in DESIGN.md. The assumption tested: Indian lenders and insurers publish which data points (name, DOB, year of birth, PIN code, last digits, mother's maiden name, nominee) they check on an outbound service, welcome, feedback or verification call, and how many and how many attempts.
- Status: unverifiable
- Corrected wording: "None of the institutions' own pages we retrieved states which identity data points the institution asks on an outbound call, how many it needs, or how many attempts it allows. The nearest published material is the content of an insurer's pre-issuance verification call, which is product facts (see F2.2), and a self-service web tracker (see F2.10)."
- Source: searched and fetched 25 files, all under `prac-*` (list in part b) | HDFC Bank, ICICI Bank, Axis, Kotak, SBI, SBI Card, Bank of Baroda, PNB, Bajaj Finance, Tata Capital, HDFC Life, ICICI Prudential Life, SBI Life, LIC, IRDAI, Bajaj Life | retrieved 2026-11-10
- Quote: "Insurers must ensure that PIVC contains important proposal data such as the sum assured, the premium amount due, the policy term, the premium payment term, and obtain customer confirmation." (`prac-bajajlife-pivc-7-steps.txt`, "Be available for video pre-issuance verification call (PIVC)")
- Notes: A page's silence is not proof of practice. Operating scripts are internal. Not found for Max Life or Axis Max Life, Star Health, SBI Life, HDFC Life or ICICI Pru welcome calls (see "Could not retrieve"). Do not write "banks verify with DOB plus X" as a published fact. At most it can be said that this is a common industry practice, and no source here shows that.

### F2.2 Insurer pre-issuance verification call (PIVC): regulator text and insurer description
- Claim as worded: not in DESIGN.md. The assumption tested: the regulator or insurers define what an insurer confirms on a PIVC.
- Status: verified (for what these two pages say)
- Corrected wording: "IRDAI circular IRDAI/LIFE/CIR/MISC/116/05/2020 of 12/05/2020 encourages all life insurers to conduct a PIVC 'to the extent possible and certainly in important cases'. It lists no content and no identity data points. Bajaj Life Insurance's customer guide, paraphrasing the circular, says a PIVC covers sum assured, premium due, policy term and premium payment term plus customer confirmation, as a video call by a link sent to the registered contact number."
- Source: `prac-irdai-pivc-document-detail.txt`; `prac-bajajlife-pivc-7-steps.txt` | https://irdai.gov.in/document-detail?documentId=394397 ; https://www.bajajlifeinsurance.com/life-insurance-guide/life/7-steps-to-quicker-policy-issuance.html | retrieved 2026-11-10
- Quote: "all Life Insurers are encouraged to conduct Pre-Issuance Verification Call (PIVC) to the extent possible and certainly in important cases." (IRDAI circular, para 2)
- Quote: "some of the life Insurers have adopted the practice of PIVC (Pre-Issuance Verification Call) to prevent mis-selling and unfair business practices" (IRDAI circular, para 1)
- Quote: "be available to complete a video pre-issuance verification call through a link you will get on your registered contact number" (Bajaj Life, PIVC section)
- Notes: The circular PDF attachment ("Pre-Issuance Verification Call (PIVC).pdf") was not downloaded. Only the IRDAI page text was saved, and it carries the full body of the circular. This is an insurer's description of what the call must contain, not a script. Product facts are confirmed, and the registered mobile is the channel that identifies the customer.

### F2.3 Public RFPs/tenders: no verification data points found
- Claim as worded: not in DESIGN.md. The assumption tested: a public bank or insurer RFP for outbound calling states the verification data points or rule (for example "any two of five").
- Status: unverifiable
- Corrected wording: "Of the public tenders found, only SBI's 2022 RFP for an outbound contact-centre technology stack was retrievable (270 pages). It specifies outbound-IVR features and has no customer identity-verification data points, no script and no authentication rule. A search of its text for birth, authenticate/verify customer, customer identification and script found nothing relevant. Three other bank call-centre RFPs could not be retrieved. No insurer welcome-call tender was found."
- Source: `prac-rfp-sbi-outbound-cc-tech-stack-2022.txt` | https://sbi.co.in/webfiles/uploads/files_2122/01022022_RFP%20for%20procurement%20of%20outbound%20cc%20tech%20stack.pdf | retrieved 2026-11-10
- Quote: "TS OB IVR 09 - Record Customer Name on Outbound IVR Call" (RFP technical specification, outbound IVR table)
- Quote: "TS OB IVR 13 On successful Customer Voice detection patch customer and play defined recorded Outbound Message" (same table)
- Notes: This is a technology RFP, so the absence is expected and is not evidence about practice. A search for a tender with an authentication rule found only US and Bangladesh material. Not tried for budget reasons: UCO Bank, J&K Bank and SIDBI tenders.

### F2.4 "We will never ask" lists name OTP, PIN, CVV, password, card number
- Claim as worded: not in DESIGN.md. The assumption tested: institutions tell customers they will never ask for OTP, PIN, CVV or password on a call.
- Status: verified
- Corrected wording: "HDFC Bank, ICICI Bank, Axis Bank, SBI, SBI Card, Kotak, Bank of Baroda, PNB and Bajaj Finance each publish a line that the institution does not ask for OTP, PIN, CVV, password or card details on a call. This is what the institution tells customers. It is not a measurement of what any call does."
- Source: `prac-hdfcbank-official-number-series.txt`; `prac-hdfcbank-security.txt`; `prac-icicibank-customer-care.txt`; `prac-icicibank-fraud-prevention.txt`; `prac-axisbank-identify-genuine.txt`; `prac-sbi-onlinesbi-home.txt`; `prac-sbicard-fraud-prevention-blog.txt`; `prac-kotak-safe-banking.txt`; `prac-bob-secure-banking.txt`; `prac-pnb-faq-atm-card-never-ask.txt`; `prac-bajajfinance-customer-care.txt` | URLs in INDEX rows below | retrieved 2026-11-10
- Quote: "It is important to remember that HDFC Bank never asks for confidential banking details over a phone call." (HDFC Bank blog dated May 12, 2026)
- Quote: "ICICI Bank will never ask for your confidential or sensitive information like Card number, CVV, OTP, etc over the call or SMS or email." (ICICI Bank customer care page, transaction confirmation numbers)
- Quote: "SBI never asks for confidential information such as PIN and OTP from customers. Any such call can be made only by a fraudster. Please do not share personal info." (SBI banner, onlinesbi.sbi home page)
- Quote: "The bank never asks for OTP, PIN, CVV, or passwords on calls." (Axis Bank, "How to identify genuine Axis Bank communication")
- Quote: "Bajaj Finance will never ask for your OTP, PIN, or full card details over a call, SMS, or email" (Bajaj Finance customer care page)
- Notes: Further wording: Kotak, "We will never ask for card details, CVV, expiry date or any such sensitive information over a call". PNB, "Please note that our Bank officials will never ask for card details or PIN over telephone / email. So, do not respond to any calls/phishing mails from people indicating that they represent our Bank." The SBI line comes from a homepage banner, so it can change. The PNB line is in an ATM-card FAQ, so it sits in a card context. None of these lists says "but we may ask X to verify you".

### F2.5 Several lists name date of birth as something not to give on a call
- Claim as worded: not in DESIGN.md. The assumption tested: some institutions' never-ask or do-not-share lists include date of birth.
- Status: verified
- Corrected wording: "Axis Bank says it never seeks dates of birth through any form of communication. SBI Life tells customers not to share date of birth on a phone call even from a trusted source such as the insurer. Kotak says its executives will never ask for such details because they already have them, and names date of birth and mother's maiden name in its identity-theft section. LIC tells customers not to part with DOB to unverified callers. A voice product that asks a customer for date of birth, or year of birth, on an outbound call sits against this published customer education."
- Source: `prac-axisbank-vishing-never-seeks.txt`; `prac-sbilife-beware-fraudulent-calls.txt`; `prac-kotak-fraud-tips.txt`; `prac-lic-policy-protection-interests-policyholders-2024.txt` | https://www.axis.bank.in/fraud-awareness/types-of-scams/vishing-scam-preteding-to-be-axis-bank-employees ; https://www.sbilife.co.in/beware-of-fraudulent-websites-calls-and-emails ; https://www.kotak.bank.in/en/safe-banking/types-of-fraud-tips.html ; https://licindia.in/documents/20121/134266/Policy+for+Protection+of+Interest+of+Policyholders+2024.pdf/1d2eecdc-1e5c-c60e-f8fc-9613b13a1a73?t=1737625659110 | retrieved 2026-11-10
- Quote: "Axis Bank never seeks any personal or financial credential details such as email ID, phone number, Credit Card details (CVV, expiry date, number) OTP, UPI PIN, bank account numbers, dates of birth, PAN or Aadhaar card details, etc. through any form of communication." (Axis Bank vishing page)
- Quote: "Do not share your confidential information like password, customer-id, date of birth, credit card number, etc on e-mail or on a phone call, even if it is from a trusted source like your insurer, IRDAI, Income Tax Department, Bank, Credit Card Company, etc." (SBI Life, "Dos and Don'ts")
- Quote: "Kotak Mahindra Bank’s executives will never ask you for such details as they already have it." (Kotak, vishing and phishing tips)
- Quote: "Kotak Mahindra already has the aforementioned information in its database and would never ask you for it." (Kotak, identity-theft tip, in an "emails" context)
- Quote: "their policy number or personal data such as DOB, PAN number, address, Aadhaar" (LIC Policy for Protection of Interests of Policyholders 2024, spurious calls procedure; the sentence begins "Not to entertain calls from unverified sources and part with any information about")
- Notes: Axis and SBI Life list date of birth in general terms. The Kotak "would never ask" sentence is attached to emails. The Kotak page elsewhere describes a scam script in which callers "are asked for personal details such as name, User Id, password, date of birth, and more." The LIC advice is for unverified callers, not a general rule. These are scam-awareness lines, and none of them states what the institution's own verified outbound call asks. They still show the customer is told not to give DOB on a phone call, and a genuine caller asking for it matches the scam pattern the customer was warned about. This is the main design risk for a "second identity check by year of birth". Compare Bank of Baroda in F2.8 for the one stated exception. Not allowed to infer from these pages that "banks never ask DOB". Axis and Kotak are the only two that say it directly.

### F2.6 No institution says "we may ask for DOB or other details to verify you"
- Claim as worded: not in DESIGN.md. The assumption tested: any institution's page says it may ask date of birth or other details on a call to verify the customer.
- Status: unverifiable
- Corrected wording: "No saved page from any of the 16 institutions says the institution may ask date of birth, year of birth, PIN code, address or similar details to verify the customer on an outbound call. The only qualified line found is Bank of Baroda's 'unless the communication is a response to your query or complaint made previously'."
- Source: all `prac-*` files; searched for "birth", "verify" and "never ask" in each | retrieved 2026-11-10
- Quote: "Never reveal or key-in your confidential details to anyone who calls or e-mails, unless the" (Bank of Baroda, "How to remain safe")
- Quote: "communication is a response to your query or complaint made previously." (the same sentence, continued on the next line)
- Notes: Bank of Baroda's exception covers calls returning a customer's own query. It is not a list of data points. A welcome, feedback or collections call is not a response to a query, so that exception would not cover it.

### F2.7 How to check an outbound call is genuine: number series
- Claim as worded: not in DESIGN.md. The assumption tested: institutions tell customers that genuine calls come from specific numbers (the 1600 series).
- Status: verified
- Corrected wording: "HDFC Bank (blog dated 12 May 2026) says it contacts customers only from 1600-series numbers (service and account-specific) and 140-series numbers (promotional), and a call from any other number is to be treated as suspicious. Axis Bank says its Relationship Manager will call only from 1600 numbers and promotion calls start with 140, 'as per RBI guidelines'. ICICI Bank publishes a list of 1600-series numbers for IVR transaction-confirmation and dispute-update calls and says a call from these is from ICICI Bank."
- Source: `prac-hdfcbank-official-number-series.txt`; `prac-axisbank-identify-genuine.txt`; `prac-icicibank-customer-care.txt` | https://www.hdfc.bank.in/blogs/banking-services/how-to-verify-hdfc-bank-official-number-series ; https://application.axis.bank.in/WebForms/axis-support/Blogs/identify_genuine.aspx ; https://www.icici.bank.in/customer-care.html | retrieved 2026-11-10
- Quote: "HDFC Bank connects with customers only via 1600 and 140 series numbers." (HDFC Bank blog, Synopsis)
- Quote: "If a call does not originate from a number starting with 1600 or 140, it should be treated as suspicious." (HDFC Bank blog)
- Quote: "your Axis Bank Relationship Manager will contact you only through phone numbers starting with 1600 and all promotion calls will start with 140." (Axis Bank, identify genuine communication)
- Quote: "If you receive any call from the below mentioned numbers, know that the call is from ICICI Bank." (ICICI Bank customer care page)
- Notes: Applies to banks only. The insurers and NBFCs checked name no such series. The HDFC Bank security page also names seven 1600-prefixed transaction-monitoring numbers ("Always attend calls from these numbers"). This is a check done by the customer on the caller ID. It says nothing about the call itself.

### F2.8 How to check an outbound call is genuine: call back, app, portal
- Claim as worded: not in DESIGN.md. The assumption tested: institutions tell customers to verify by calling back an official number or signing in to the app or portal.
- Status: verified
- Corrected wording: "Bajaj Finance tells customers to sign in to its portal or app to check requests directly, and to call the number on its official website, not a number in the suspicious message. Axis Bank tells customers to confirm by calling its phone-banking numbers. Bank of Baroda tells customers never to call back a number given by a caller and to give confidential details only in reply to their own earlier query. None of the pages checked mentions a prior SMS announcing the call, or an in-app approval of an outbound call."
- Source: `prac-bajajfinance-beware-of-scams.txt`; `prac-axisbank-vishing-never-seeks.txt`; `prac-bob-secure-banking.txt` | URLs in INDEX rows | retrieved 2026-11-10
- Quote: "Sign in to your Bajaj Finance customer portal or app directly to check for any genuine offers, requests, or updates on your account." (Bajaj Finance, "How to verify if a communication is genuinely from Bajaj Finance")
- Quote: "If in doubt, contact Bajaj Finance customer care directly using the number listed on their official website, rather than a number provided in the suspicious message." (same section)
- Quote: "please confirm by calling us on the Axis Bank Phone Banking Numbers - 18604195555 / 18605005555" (Axis Bank vishing page)
- Quote: "Never call back a phone number sent to you in an email or provided through a phone call and" (Bank of Baroda, "How to remain safe"; sentence continues "provide confidential bank account information.")
- Notes: A caller-controlled call-back is discouraged by Bank of Baroda, so a bot cannot rely on "call us back on this number". The pattern is customer-initiated verification through a channel the customer already has (portal, app, printed number).

### F2.9 LIC says it uses no telecaller services
- Claim as worded: not in DESIGN.md. The assumption tested: insurers run outbound calls to policyholders.
- Status: verified (as LIC's own statement of policy)
- Corrected wording: "LIC's Policy for Protection of Interests of Policyholders 2024 states that the Corporation does not engage any telecaller services to call its policyholders, and advises policyholders not to give policy number or personal data such as DOB to unverified callers. This is LIC's stated policy and says nothing about what it does on welcome or PIVC calls."
- Source: `prac-lic-policy-protection-interests-policyholders-2024.txt` | https://licindia.in/documents/20121/134266/Policy+for+Protection+of+Interest+of+Policyholders+2024.pdf/1d2eecdc-1e5c-c60e-f8fc-9613b13a1a73?t=1737625659110 | retrieved 2026-11-10
- Quote: "The Corporation does not engage any telecaller services to call our policyholders." (procedure for registering complaints relating to spurious calls)
- Notes: LIC's own spurious-calls notice PDF returned 503 and was not retrieved. A public-sector insurer saying it does not call is a market fact worth knowing for the interview. The lenders and private insurers did not say so.

### F2.10 Date of birth as a self-service factor (not an outbound call)
- Claim as worded: not in DESIGN.md. The assumption tested: date of birth is used as a knowledge factor in insurer self-service.
- Status: verified (inbound web only)
- Corrected wording: "HDFC Life's service guidebook describes a web 'track now' option for service requests that asks for policy number, date of birth and a captcha code. It is a web form, not an outbound call, and it shows DOB used as a factor by an insurer in self-service."
- Source: `prac-hdfclife-my-service-guidebook.txt` | https://myaccount.hdfclife.com/static-cp-cms/pdffiles/My%20Service%20Guidebook%20_%20Final_with%20comment_V3.pdf | retrieved 2026-11-10
- Quote: "providing policy no, your date of birth and typing the captcha code." (guidebook, "Track Your Service Requests")
- Notes: The guidebook's Call Centre and IVR section lists no authentication data points. Do not cite this as outbound practice.

### F2.11 Institutions with no first-hand outbound-verification page found
- Claim as worded: not in DESIGN.md. The assumption tested: a first-hand page exists for each named institution.
- Status: unverifiable
- Corrected wording: "No first-hand welcome-call, PIVC or outbound-verification page was found for Axis Max Life or Max Life, Star Health, SBI Life, HDFC Life, ICICI Prudential Life, or Tata Capital. For Tata Capital the saved page is a one-page fraud advisory with no never-ask list and no data points. The ICICI Prudential Life fraud-tips page lists 'never' items about documents and website credentials, not about phone calls."
- Source: `prac-tatacapital-fraud-advisory.txt`; `prac-iciciprulife-fraud-prevention-tips.txt` (web.archive.org copy; live URL 403) | https://www.tatacapital.com/content/dam/tata-capital/pdf/footer/Fraud%20Advisory.pdf ; https://web.archive.org/web/2026/https://www.iciciprulife.com/insurance-library/fraud-prevention-tips.html | retrieved 2026-11-10
- Quote: "customercare@tatacapital.com or call us on our toll-free number 1860 267 6060." (Tata Capital advisory, Loan Fraud Advisory)
- Quote: "Never share your website user ID, password, etc. with anyone (including ICICI Prudential Life Insurance officials)." (ICICI Prudential Life fraud tips, "Remember to never do any of these things")
- Notes: The Tata Capital advisory's text extraction has a split word ("authe nticity"), which is a PDF artefact. The Tata Capital OTP wording seen in search snippets was not fetched, so it is not claimed here. Search snippets are not evidence.


## F3: vendors' published flows, and the right-party norm abroad (comparison only)

### F3.1 Exotel's "RBI-compliant" collections flow checks name plus last four digits or date of birth
- Claim as worded: not in DESIGN.md (research question: what do Indian vendors' outbound flows check before disclosing?)
- Status: verified as to what the page says (vendor guidance, not RBI text)
- Corrected wording: Exotel's April 2026 guide tells lenders to put a mandatory gate before any account disclosure. It says the gate typically combines "name confirmation and last-four digits or date of birth". The page does not say last four digits of what, how many attempts are allowed, or what happens when verification fails.
- Source: vend-exotel-rbi-compliant-ai-collections.txt | https://exotel.com/blog/rbi-compliant-ai-collections/ (page shows April 14, 2026) | retrieved 2026-11-10
- Quote: "No account information should be disclosed before the AI has confirmed it is speaking to the authorised borrower." (section 5, "Right-Party Verification Before Disclosure")
- Quote: "The verification logic, typically a combination of name confirmation and last-four digits or date of birth, must be configured as a mandatory gate in the call flow, not an optional step." (same section)
- Quote: "Call open: Mandatory identification statement (organisation name, caller purpose). Non-skippable, locked in script." (step list)
- Quote: "Right-party verification: Borrower confirmed before any account information is disclosed." (step list)
- Notes:
  - The step list puts the identification statement (organisation and purpose) before right-party verification. That is the same sequencing tension seen in F3.2.
  - The only third-party line is a bullet: "Ensuring no data is shared with unauthorised third parties during the collections workflow".
  - A second saved Exotel page (vend-exotel-ai-voice-agents-india-debt-collection) only mentions "Voice biometrics for identity verification" as a future direction.

### F3.2 Mobicule and Smallest.ai: DOB or OTP, or account number, DOB or SSN; Mobicule's sample opener already says "outstanding balance"
- Claim as worded: not in DESIGN.md
- Status: verified as to what the pages say
- Corrected wording:
  - Mobicule's Indian-collections blog says the bot does right-party verification "via DOB or OTP" before discussing debt.
  - Its own sample opener names the purpose ("regarding your outstanding balance") in the non-skippable disclosure that starts the conversation.
  - The page does not say whether that disclosure comes before or after the check, so its sequencing is unclear.
  - Smallest.ai's banking page lists "account number, DOB, or SSN". SSN is a US identifier, so that example is not India-specific.
  - Neither page gives an attempt limit or a failure path.
- Source: vend-mobicule-ai-voicebots-debt-collection-india.txt | https://mobicule.com/how-ai-chatbots-and-voicebots-are-redefining-debt-collection-in-india/ (several dates on the page, Nov 2025 and Nov 2026; publication date unclear) | retrieved 2026-11-10; vend-smallest-ai-voice-agents-debt-collection-banking.txt | https://smallest.ai/blog/ai-voice-agents-debt-collection-banking (October 5, 2026) | retrieved 2026-11-10
- Quote: "The voicebot ensures Right Party Contact verification (via DOB or OTP) before discussing any debt details." (Mobicule, FPC compliance table, privacy row)
- Quote: "The conversation flow starts with a dynamic, non-skippable disclosure: “Hello, I am [Bot Name], an automated assistant calling from [Lending Institution] regarding your outstanding balance…”" (Mobicule, same table, disclosure row)
- Quote: "Identity Verification & Right‑Party Contact (RPC): The agent confirms that it’s speaking to the correct borrower, using verification steps such as account number, DOB, or SSN check to ensure compliance." (Smallest.ai, "How do AI Voice Agents work")
- Notes: Caller.Digital (already saved in sources/C) also says an Indian recovery bot "must disclose name, the lender's name, and the purpose of the call" within 30 seconds. So the vendor norm is to disclose purpose early and also to verify, and none of the pages resolves the order.

### F3.3 Edesy's sample collections prompt confirms the name only
- Claim as worded: not in DESIGN.md
- Status: verified as to what the pages say
- Corrected wording:
  - Edesy's docs publish a full collections system prompt whose identity step is a single name question: "Am I speaking with {{customerName}}?"
  - If the answer is no, the bot asks for the customer and says only "an important account matter".
  - The prompt forbids discussing account details with anyone else.
  - The disclosure line ("This is an attempt to collect a debt") is US FDCPA wording.
  - Edesy's India pages say "secure borrower identification before discussing any loan or payment details" and that the Hindi EMI template "confirms it's speaking to the right borrower" first. Neither names a data point.
  - The only attempt numbers anywhere in the sample are call-frequency settings (maxAttemptsPerDay 3, maxAttemptsPerWeek 7), not verification retries.
- Source: vend-edesy-docs-use-case-debt-collection.txt | https://edesy.in/docs/voice-agent/use-cases/debt-collection (undated) | retrieved 2026-11-10; vend-edesy-debt-collection-india.txt | https://edesy.in/ai-voice-agent/solutions/debt-collection-india | retrieved 2026-11-10; vend-edesy-emi-collection-voice-agent-template-hindi-2026.txt | https://edesy.in/blog/emi-collection-voice-agent-template-hindi-2026 (June 13, 2026) | retrieved 2026-11-10
- Quote: "Am I speaking with {{customerName}}?" (docs, Step 1: Identity Verification)
- Quote: "Is {{customerName}} available? I need to speak with them regarding an important account matter." (docs, same step)
- Quote: "Do NOT discuss account details with anyone other than the account holder." (docs, same step)
- Quote: "\"maxAttemptsPerDay\": 3," (docs, compliance config block)
- Quote: "Secure borrower identification before discussing any loan or payment details" (India solutions page)
- Quote: "Greeting & identity verification — confirms it's speaking to the right borrower before discussing anything sensitive." (Hindi EMI template page, call flow)
- Notes: Edesy's welcome-call blog is already in findings-C as C2.3; these are different pages. The sample asks "Am I speaking with…?" and nothing more. A yes/no on a name is the weakest possible confirmation, and a third party can answer yes for the borrower.

### F3.4 Retell's collections template and script blog: verify first, and a third party gets no reason for the call
- Claim as worded: not in DESIGN.md
- Status: verified as to what the pages say (global platform; US FDCPA framing)
- Corrected wording:
  - The template page says the agent verifies the right person, makes the debt-collector disclosure "after identity confirmation", and "never reveals balance or creditor details to third parties or unverified callers".
  - The blog's outbound script asks "may I speak with [consumer name]?" and, if anyone else answers, says nothing about the reason, asks only when the consumer can be reached, then ends.
  - The blog's inbound script asks for "full name and [second identifier]".
  - The blog's account of 12 CFR 1006.10 (identify yourself, say you are confirming or correcting location information, no mention of debt, contact the third party once) matches the eCFR text in F3.9. It gives no attempt count for failed verification.
- Source: vend-retell-template-payment-collection.txt | https://www.retellai.com/templates/payment-collection (Last Update August 5, 2026) | retrieved 2026-11-10; vend-retell-blog-collection-call-script.txt | https://www.retellai.com/blog/collection-call-script (published Oct 22, 2026) | retrieved 2026-11-10
- Quote: "never reveals balance or creditor details to third parties or unverified callers" (template description)
- Quote: "\"Hello, may I speak with [consumer name]?\"" (blog, Script 1)
- Quote: "If anyone else answers: do not state the reason for the call. Ask only when the consumer can be reached, then end." (blog, Script 1)
- Quote: "Verification comes first because the disclosure itself reveals the existence of a debt." (blog, notes under Script 1)
- Quote: "\"Before we discuss the account, can you confirm your full name and [second identifier]?\"" (blog, Script 3, inbound)
- Notes: On outbound, the verification step is effectively "is this [name]?" with a hold on content for anyone else. A real data-point check (second identifier) is shown only for inbound calls. That fits the difficulty InsideARM describes in F3.8.

### F3.5 Oration AI cookbook, Dapta and Bland: date of birth, ZIP, "any other verification question"
- Claim as worded: not in DESIGN.md
- Status: verified as to what the pages say (generic or US-framed templates)
- Corrected wording:
  - The Oration AI outbound-recovery cookbook (hosted at projectsingularity.visionwaves.com) tells the agent to ask "date of birth or any other verification question". It also says not to discuss account details on voicemail or with a third party.
  - Dapta's script template asks for "[date of birth or ZIP]".
  - Bland's debt-collection page lists "Right-party contact verification" and says "Identity verification before any account discussion". It names no data points and no attempt count.
- Source: vend-visionwaves-cookbook-outbound-recovery-agents.txt | https://projectsingularity.visionwaves.com/cookbook/setting-outbound-recovery-agents-for-collections (undated) | retrieved 2026-11-10; vend-dapta-ai-debt-collection-call-scripts.txt | https://dapta.ai/blog-posts/ai-debt-collection-call-scripts/ (undated) | retrieved 2026-11-10; vend-bland-industries-debt-collection.txt | https://www.bland.ai/industries/debt-collection (undated) | retrieved 2026-11-10
- Quote: "Confirm you're speaking to the right person before sharing any account details. Ask for date of birth or any other verification question." (Oration cookbook, conversation flow)
- Quote: "Do not discuss account details if you reach a voicemail or speak to a third party" (Oration cookbook, Important rules)
- Quote: "“Hello, this is [company]. Before we continue, can you confirm your [date of birth or ZIP] so I know I’m speaking with the right person?”" (Dapta, script template)
- Quote: "Right-party contact verification ... Identity verification before any account discussion." (Bland, use-case list; two adjacent lines)
- Notes: Oration's sample opener asks "Is this [Customer Name]?" first and then verifies, so it is a two-step flow. No page states a retry count.

### F3.6 Skit.ai and Haptik define "right party" differently
- Claim as worded: not in DESIGN.md
- Status: verified as to what the pages say
- Corrected wording:
  - Skit.ai's blog (Nov 14, 2023) is aimed at US collection agencies. It says its voice AI authenticates the consumer "through SSN, DOB, or zip code".
  - It defines the right party as the debtor "or a relative who has been given permission to handle the debt".
  - Haptik's May 2026 collections post defines right-party contact as "the borrower, not a relative or a voicemail".
  - Skit.ai's India homepage (already saved in sources/C) lists "Right-party verification" among its collections capabilities and gives no flow.
  - No published India flow from either vendor shows its data points.
- Source: vend-skit-ai-arm-boost-right-party-contact-voice-ai.txt | https://skit.ai/resource/blog/how-arm-companies-can-boost-right-party-contact-with-voice-ai/ | retrieved 2026-11-10; vend-haptik-voice-ai-for-debt-collection.txt | https://www.haptik.ai/blog/voice-ai-for-debt-collection (May 19, 2026) | retrieved 2026-11-10; ../C/vendors/skit-ai-in-homepage.txt
- Quote: "the voice AI solution confirms right-party contact and authenticates the consumer through SSN, DOB, or zip code" (Skit.ai blog)
- Quote: "which could be either the debtor or a relative who has been given permission to handle the debt" (Skit.ai blog)
- Quote: "Right Party Contact (RPC) ensures the AI is talking to the borrower, not a relative or a voicemail." (Haptik)
- Quote: "Right-party verification" (Skit.ai India homepage, sources/C)
- Notes: Whether an authorised third party counts as the right party is a policy choice vendors disagree on. The design's third-party handling should name its own rule.

### F3.7 Most other named vendors publish no outbound identity flow I could retrieve
- Claim as worded: not in DESIGN.md
- Status: unverifiable for the vendors listed under "searched only" below. This is a documented search, not proof of absence.
- Corrected wording:
  - Pages I fetched and read (Gnani solutions, Oriserve, Revrag, SquadStack debt-collection voicebot) describe no right-party data point or failure path. Haptik's banking page (in sources/C) describes only inbound authentication.
  - Gnani's solutions page lists "identity verification" as a supported interaction type and nothing more.
  - Revrag says the agent "states its identity and the lending entity's name at the start of every call" and says nothing about borrower verification.
  - Oriserve's EMI-collections page has no identity or right-party step.
  - Caller.Digital's comparison (a secondary source, in sources/C) says Gnani's "voice biometric stack (Inya Shield)" is used for authentication on personal-loan and card collections.
  - Searched only (a web search returned no flow page; I did not fetch their sites): Ozonetel, Knowlarity, Yellow.ai, Uniphore, Credgenics, DPDzero, Spocto/Yubi, CreditMate, Bolna, Vodex, Sarvam, Twilio, Genesys, Five9, Vapi, ElevenLabs.
  - No retrieved vendor page gives a retry count for a failed identity check.
- Source: vend-gnani-solutions.txt | https://www.gnani.ai/solutions | retrieved 2026-11-10; vend-revrag-ai-debt-recovery-compliance-india.txt | https://www.revrag.ai/resources/blog/ai-debt-recovery-compliance-india | retrieved 2026-11-10; vend-oriserve-voice-ai-emi-loan-collections.txt | https://oriserve.com/blog/voice-ai-for-emi-loan-collections | retrieved 2026-11-10; vend-squadstack-ai-voicebot-debt-collection.txt | https://www.squadstack.ai/voicebot/ai-voicebot-for-debt-collection | retrieved 2026-11-10; ../C/vendors/callerdigital-best-voice-ai-nbfc-india-2026.txt
- Quote: "The agent states its identity and the lending entity's name at the start of every call" (Revrag)
- Quote: "the voice biometric stack (Inya Shield) is genuinely useful for high-value authentication on personal loan and credit card collections" (Caller.Digital on Gnani; secondary)
- Quote: "identity verification" (Gnani solutions page, list of interactions)
- Notes: SquadStack's page says AI can "verify customer details, confirm their current payment intentions, and record their location information before escalating", which is generic. SquadStack, Edesy and Ringg welcome-call coverage stays in C2.2, C2.3 and C2.7.

### F3.8 InsideARM (trade press): outbound identity questions are harder, and a third party may only be asked for location information
- Claim as worded: not in DESIGN.md
- Status: secondary-only (collections trade publication reporting a peer-group discussion, 18 Feb 2026)
- Corrected wording: Outbound calls reach third parties more often, and asking date-of-birth or SSN-digits questions before saying who is calling makes most people hang up. A collector faces a circular problem: it cannot say who it is or why it is calling until the right party is verified. The article's suggested workaround is to give a small piece of known information to build trust.
- Source: vend-insidearm-ai-agents-calling-third-parties.txt | https://www.insidearm.com/news/00095016-ai-agents-calling-third-parties/ (Published February 18, 2026) | retrieved 2026-11-10
- Quote: "Outbound calls are very different. If you ask these same questions without first identifying who you are and why you are calling (which you cannot identify who you are unless they ask, or why you are calling until they verify RPC), most will hang up."
- Quote: "Right Party Contact (RPC) is harder to establish, as the called party is often less cooperative."
- Quote: "Under the FDCPA, collectors can only request “location information” from third parties."
- Notes: This is the same known difficulty as the Australian passage you described, which I did not find in the guideline text (see F3.11). Do not cite this article as a rule.

### F3.9 US: FDCPA 805(b) and Reg F 1006.6(d) bar debt communication with anyone but the consumer; 1006.10 limits third-party calls to location information
- Claim as worded: not in DESIGN.md
- Status: verified
- Corrected wording:
  - A debt collector must not communicate "in connection with the collection of any debt" with anyone other than the consumer, the consumer's attorney, a consumer reporting agency, the creditor and the attorneys of the creditor or collector.
  - The exceptions are location information under 1006.10, prior consent given directly to the collector, a court's permission, and postjudgment remedies.
  - 1006.6(a) widens "consumer" to include the spouse (and a minor's parent, a legal guardian, an estate's executor, and a confirmed successor in interest).
  - When talking to a non-consumer to find the consumer, the collector must name himself or herself individually, say they are "confirming or correcting the consumer's location information", name the employer only if expressly asked, and not state that the consumer owes any debt.
  - The collector may generally contact that person only once, unless that person asks or the collector reasonably believes the earlier answer was erroneous or incomplete.
  - Neither 1006.6 nor 1006.10 says what counts as confirming that the person on the line is the consumer, or how many identity-check attempts are allowed. The sections I retrieved contain no such rule.
  - The official commentary (Supplement I) has headings for 6(d)(2) to 6(d)(5) but no comment to 6(d)(1). I searched it for "identity" and "confirm" and found no passage on confirming the consumer's identity.
  - The Federal Register preamble (85 FR 76734) was not retrieved, so any discussion there is unchecked.
- Source: intl-us-ecfr-12cfr1006.6.txt, intl-us-ecfr-12cfr1006.10.txt, intl-us-ecfr-12cfr1006-supp-I.txt | eCFR (current to 2026-11-06) via https://www.ecfr.gov/api/versioner/v1/full/2026-11-06/title-12.xml?part=1006&section=1006.6 (also section=1006.10, and appendix=Supplement%20I%20to%20Part%201006); intl-us-15usc1692c-cornell.txt | https://www.law.cornell.edu/uscode/text/15/1692c | retrieved 2026-11-10
- Quote: "a debt collector may not communicate, in connection with the collection of any debt, with any person other than the consumer, his attorney, a consumer reporting agency if otherwise permitted by law, the creditor, the attorney of the creditor, or the attorney of the debt collector." (15 U.S.C. 1692c(b))
- Quote: "(d) Communications with third parties—(1) Prohibitions. Except as provided in paragraph (d)(2) of this section, a debt collector must not communicate, in connection with the collection of any debt, with any person other than:" (12 CFR 1006.6(d)(1))
- Quote: "(i) For the purpose of acquiring location information, as provided in § 1006.10;" (12 CFR 1006.6(d)(2)(i))
- Quote: "For purposes of this section, the term consumer includes:" followed by "(1) The consumer's spouse;" (12 CFR 1006.6(a))
- Quote: "Identify himself or herself individually by name, state that he or she is confirming or correcting the consumer's location information, and, only if expressly requested, identify his or her employer;" (12 CFR 1006.10(b)(1))
- Quote: "Not state that the consumer owes any debt;" (12 CFR 1006.10(b)(2))
- Quote: "must not communicate more than once with such person unless requested to do so by such person, or unless the debt collector reasonably believes that the earlier response of such person is erroneous or incomplete" (12 CFR 1006.10(c))
- Notes: eCFR is the Office of the Federal Register's editorial compilation, not the legal edition. The Cornell page is a mirror of the U.S. Code. Section 1692b (location information) is also saved (intl-us-15usc1692b-cornell) but I did not quote it.

### F3.10 US: a limited-content message may carry only four things, and a voicemail left for a third party is not one
- Claim as worded: not in DESIGN.md
- Status: verified
- Corrected wording:
  - 12 CFR 1006.2(j) lets a collector leave a voicemail without it counting as a communication, but only if it contains a business name that does not indicate debt collection, a request to reply, the name of one or more natural persons, and a number to call. It may add a salutation, date and time, suggested reply times, and a line that any representative can help.
  - Commentary 2(j) comment 1 says a message that also says it is from a debt collector and asks for a named consumer is not a limited-content message, because it includes more than the permitted content.
  - Comment 2 says a message knowingly left for a third party is not a limited-content message at all.
- Source: intl-us-ecfr-12cfr1006.2.txt and intl-us-ecfr-12cfr1006-supp-I.txt | eCFR as above | retrieved 2026-11-10
- Quote: "(i) A business name for the debt collector that does not indicate that the debt collector is in the debt collection business;" (12 CFR 1006.2(j)(1)(i))
- Quote: "a voicemail message that includes a statement that the message is from a debt collector and a request to speak to a particular consumer is not a limited-content message because it includes more than the required or permitted content." (Supp. I, 2(j) comment 1)
- Quote: "A message knowingly left for a third party is not a limited-content message because it is not for a consumer." (Supp. I, 2(j) comment 2)
- Quote: "“This is Robin Smith calling from ABC Inc. Please contact me or Jim Johnson at 1-800-555-1212.”" (Supp. I, 2(j)(1) comment 1, official example)
- Notes: The model message names a person and a company and never the debt or the creditor's purpose. A bot that left a message naming the product would fall outside this safe harbour.

### F3.11 Australia: the guideline says establish that the person is the debtor before divulging anything, on every contact
- Claim as worded: not in DESIGN.md
- Status: verified (the guideline is advisory: "This guideline does not have legal force")
- Corrected wording:
  - Part 2, section 1(a) says the collector's first task is to ensure the person is the debtor, every time, before divulging "any information about the debt, the process for its recovery or … any other confidential information".
  - Section 1(b) allows revealing that the caller is a debt collector before being sure only if that "would not have the effect of divulging that the debtor has a debt". It gives two examples: a bank's name is unlikely to reveal a debt, while a descriptive name such as 'Collections R Us' would.
  - Section 1(c) applies the same limits to the spouse, partner and family.
  - Section 1(d): once identity is established, say who you are, who you work for and the purpose.
  - Section 8(f): voicemail must avoid letting a third party infer the nature of your interest.
  - Section 18(h): if a third party says they do not want to help, stop contacting them.
  - The guideline recommends contacting a third party for location information no more than once every six months.
  - It does not say how to establish identity, which data points to ask for, or how many attempts are allowed. I did not find the passage you described, that asking for identifying details before the collector identifies itself is a known difficulty. I searched for "difficult", "dilemma" and "chicken" and found nothing. Section 1(b) is the closest.
- Source: intl-au-accc-asic-debt-collection-guideline-2021-04.txt | https://www.accc.gov.au/system/files/Debt%20collection%20guideline%20for%20collectors%20and%20creditors%20-%20April%202021.pdf (April 2021 edition; ASIC publishes it as RG 96) | retrieved 2026-11-10
- Quote: "your first task must always be to ensure the person you are dealing with is the debtor. This must be done every time you make contact before you divulge any information about the debt, the process for its recovery or before providing any other confidential information." (Part 2, s 1(a), printed p. 6)
- Quote: "If you consider it necessary to divulge your identity as a debt collector before being sure that you are dealing with the debtor (for example, if requested by the person you are dealing with), then you may do so if that would not have the effect of divulging that the debtor has a debt." (s 1(b), p. 6)
- Quote: "The limits on disclosing information to third parties apply to the debtor’s spouse, partner and/or family as much as they apply to other third parties." (s 1(c), p. 7)
- Quote: "Having established the debtor’s identity, you should then identify who you are, who you work for and explain the purpose of the contact." (s 1(d), p. 7)
- Quote: "Voicemail messages should be phrased so as to avoid a third party inferring the nature of your interest in contacting the debtor" (s 8(f))
- Quote: "If a third party indicates they do not want to help you—however unreasonable that refusal may seem to you—stop contacting the third party." (s 18(h), p. 32)
- Quote: "We recommend that you do not contact a third party to obtain location information more often than once every six months." (frequency section)
- Quote: "This guideline does not have legal force." (introduction)
- Notes: Australia is the most explicit that the caller may name its organisation to an unverified person only if the name reveals no debt. Only the bank-name example is close to a lender call.

### F3.12 UK: CONC 7.9.10R requires establishing, "by suitably appropriate means", who the individual is before disclosing any debt detail. The 159 and "hang up and call back" guidance covers the customer's side.
- Claim as worded: not in DESIGN.md
- Status: verified for the CONC text as printed in FCA instrument 2014/11. I did not confirm the current Handbook wording because the Handbook site is JavaScript-only (see section (c)). Verified for the 159 and Which? statements as what those bodies publish.
- Corrected wording:
  - CONC 7.9.10R: a firm must not disclose details of a debt to an individual without first establishing, "by suitably appropriate means", that the individual is (or acts on behalf of) the borrower or hirer.
  - The rule names no data points and no attempt limit.
  - CONC 7.9.11G says a payment demand sent to everyone with the same name and date of birth or address as the customer is likely to contravene 7.9.10R.
  - CONC 7.9.1R requires the caller to say who they work for, their role and the purpose of the contact.
  - CONC 7.9.6R and 7.9.7R: no unfair disclosure of the debt to a third party, and reasonable steps so third parties do not become aware the customer is being pursued.
  - On the customer's side: Stop Scams UK's 159 is a number the customer dials to reach their bank's fraud team, and it never calls out. Which? advises hanging up on an unexpected call and calling back on an official number, or the number on the back of the card, or 159, using a different phone or waiting 10 to 15 minutes in case the line is held open.
  - I found no FCA or UK Finance primary text on letting customers verify an unexpected call, and no in-app call-verification page.
- Source: intl-uk-fca-instrument-2014-11-conc.txt | https://www.Handbook.fca.org.uk/instrument/2014/FCA_2014_11.pdf (CONC 7.9, PDF pp. 125-127 of 204) | retrieved 2026-11-10; intl-uk-stopscamsuk-159-get-help-now.txt | https://stopscamsuk.org.uk/campaign/get-help-now/ | retrieved 2026-11-10; intl-uk-which-phone-scams.txt | https://www.which.co.uk/consumer-rights/advice/phone-scams-aL1Yy5L9Utl4 | retrieved 2026-11-10
- Quote: "A firm must not disclose details of a debt to an individual without first establishing, by suitably appropriate means, that the individual is (or acts on behalf of) the borrower or hirer under the relevant agreement)." (CONC 7.9.10R)
- Quote: "sends a payment demand to all persons sharing the same name and date of birth or address as the customer;" (CONC 7.9.11G(2))
- Quote: "A firm must ensure that a person contacting a customer on its behalf explains to the customer the following matters:" (CONC 7.9.1R)
- Quote: "A firm must not unfairly disclose or threaten to disclose information relating to the customer’s debt to a third party." (CONC 7.9.6R)
- Quote: "a firm must take reasonable steps to ensure that third parties do not become aware that the customer is being pursued in respect of a debt" (CONC 7.9.7R(2))
- Quote: "If you get a call that seems off, stop, hang up, and dial 159. It’s a safe and direct way to connect with your bank when you’re most at risk of being scammed. It’s simple, easy to remember, and can’t be faked so 159 will never call you." (Stop Scams UK)
- Quote: "You can contact your bank by using the number found on the back of your card, or by dialling 159 to be connected to its fraud team." (Which?, secondary)
- Quote: "Be aware that scammers may be able to keep your phone line open even after you’ve hung up, so if you hang up on a dodgy call, use a different phone to call the company back on a trusted number or wait for at least 10 to 15 minutes." (Which?, secondary)
- Notes: The CONC text is the April 2014 instrument, and I could not check later amendments. 7.9.10R is a debt-disclosure rule for collections, so it does not by itself cover a bank's non-debt call. 159 is the customer-initiated route that follows from the "hang up and call back" advice.

## F4: how weak knowledge questions are, and the stronger measures

### F4.1 NIST SP 800-63A (rev 3 and rev 4): knowledge-based verification
- Claim as worded: not in DESIGN.md
- Status: verified
- Corrected wording: SP 800-63A-4 says knowledge-based verification or authentication must not be used for identity verification. It allows it only as part of a fraud-management program. Rev 3 allowed it at IAL2 with four conditions: the information must not be freely available or purchasable, the answers must change over time, a minimum of four questions, and no more than three attempts. The scope is digital identity proofing, not a bank's outbound call. The principle that public or purchasable data cannot prove identity still carries over.
- Source: sources/F/kba-nist-sp800-63a-4.txt (and .html) | https://pages.nist.gov/800-63-4/sp800-63a.html | retrieved 2026-11-10. Rev 3: sources/F/kba-nist-sp800-63a-3.txt | https://pages.nist.gov/800-63-3/sp800-63a.html | retrieved 2026-11-10
- Quote: "Knowledge-based verification (KBV) or knowledge-based authentication SHALL NOT be used for identity verification." (63A-4, identity verification methods)
- Quote: "CSPs MAY employ KBV as part of its fraud management program." (63A-4, fraud management)
- Quote: "Information accessible freely, for a fee in the public domain, or via the black market SHALL NOT be used." (63A-3 §5.3.2)
- Quote: "The CSP SHALL NOT use KBV questions for which the answers do not change (e.g., "What was your first car?")." (63A-3 §5.3.2)
- Quote: "A process of validating the knowledge of personal or private information associated with an individual for the purpose of verifying the claimed identity of an applicant." (63A-4 glossary)
- Notes: Date of birth, year of birth and PIN code are answers that "do not change" and are "accessible ... for a fee" or leaked (F4.7). Under rev 3's own test they fail. The rev 4 text bans the technique outright.

### F4.2 NIST SP 800-63B (rev 3 and rev 4): hints and prompts
- Claim as worded: not in DESIGN.md
- Status: verified
- Corrected wording: SP 800-63B bans stored hints that an unauthenticated person can see. It also bans prompting people to use "first pet" style knowledge answers as a password. The text concerns choosing passwords. It is not a direct ruling on a phone call, but it shows NIST treats such answers as unfit as a secret.
- Source: sources/F/kba-nist-sp800-63b-4.txt | https://pages.nist.gov/800-63-4/sp800-63b.html (page header "Tue, 26 Aug 2025") | retrieved 2026-11-10. Rev 3: sources/F/kba-nist-sp800-63b-3.txt | https://pages.nist.gov/800-63-3/sp800-63b.html
- Quote: "Verifiers and CSPs SHALL NOT prompt subscribers to use knowledge-based authentication (KBA) (e.g., "What was the name of your first pet?") or security questions when choosing passwords." (63B-4, password requirements)
- Quote: "Verifiers and CSPs SHALL NOT permit the subscriber to store a hint (e.g., a reminder of how the password was created) that is accessible to an unauthenticated claimant." (63B-4)
- Quote: "Memorized secret verifiers SHALL NOT permit the subscriber to store a "hint" that is accessible to an unauthenticated claimant." (63B-3)
- Notes: Rev 3 said "specific types of information (e.g. first pet)". Rev 4 names KBA and security questions.

### F4.3 FFIEC 2021 authentication guidance (US bank regulators)
- Claim as worded: not in DESIGN.md
- Status: verified
- Corrected wording: The FFIEC guidance (August 2021, replacing the 2005 and 2011 guidance) says reliable identity verification generally does not rest on knowledge questions alone. For call-centre credential resets it lists stronger methods, including an OTP sent to a pre-established device and a call-back to a pre-established number.
- Source: sources/F/kba-ffiec-2021-authentication-guidance.txt (web.archive.org copy of the ffiec.gov PDF; the direct URL returned 403) | https://web.archive.org/web/2024/https://www.ffiec.gov/guidance/Authentication-and-Access-to-Financial-Institution-Services-and-Systems.pdf | retrieved 2026-11-10
- Quote: "Reliable verification methods generally do not depend solely on knowledge-based questions to verify identity." (identity verification section)
- Quote: "sending an OTP to a pre-established communication device" (Section 8, Customer Call Centers controls)
- Quote: "call-backs to a pre-established phone number" (Section 8)
- Quote: "Threat actors frequently have used social engineering and other techniques to deceive customer call center and IT help desk representatives" (Section 8)
- Notes: The word is "solely". The FFIEC does not ban knowledge questions. It asks for other methods beside them. The call-centre controls concern a customer calling in, not an outbound call. The call-back to a pre-established number is the only item that also covers outbound.

### F4.4 RBI Authentication Mechanisms for Digital Payment Transactions Directions, 2025
- Claim as worded: not in DESIGN.md
- Status: verified for what it says. unverifiable that it bears on spoken knowledge questions.
- Corrected wording: These directions govern authenticating digital payment transactions. They count "something the user knows" as a factor. They require one dynamic factor per non-card-present transaction, and independence of factors. They say nothing about identity checks on a phone call. No RBI, CERT-In or UIDAI text on spoken knowledge questions was found.
- Source: sources/F/kba-rbi-authentication-directions-2025-notif12898.txt | https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12898 | retrieved 2026-11-10
- Quote: "The factors of authentication can be from "something the user has", "something the user knows" or "something the user is"" (para 5(f))
- Quote: "at least one of the factors of authentication is dynamically created or proven, i.e., the proof of possession of the factor, being sent as part of the transaction, is unique to that transaction." (para 6(b))
- Quote: "The factor of authentication shall be such that compromise of one factor does not affect reliability of the other." (para 6)
- Notes: Do not cite this as RBI saying knowledge questions are weak. It is the closest Indian standard, and it concerns transactions. A static answer such as year of birth is not a "dynamic" factor and could not be the only factor.

### F4.5 Measured guessing of answers by acquaintances and strangers
- Claim as worded: not in DESIGN.md
- Status: verified
- Corrected wording: In a 2009 lab study (webmail secret questions of AOL, Google, Microsoft and Yahoo, up to 5 guesses), partners who the participant would not trust with their password guessed 17% of answers. Partners who were trusted guessed 28%. Strangers using the most popular answers got 13% within 5 tries, partly an artefact of a homogeneous sample. Participants forgot 20% of their own answers within six months. Google's 2015 paper found 40% of its English-speaking US users could not recall their answers. It also found that 37% of users who gave fake answers did so to make them harder to guess, and this made them more predictable. The questions in these studies were not date of birth, year of birth or PIN code. A relative's chance of knowing a birth year is not measured here.
- Source: sources/F/kba-schechter-2009-its-no-secret.txt (Microsoft Research-hosted PDF of the IEEE S&P 2009 paper, 16 pages) | https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/oakland09.pdf | retrieved 2026-11-10. sources/F/kba-bonneau-2015-secrets-lies-google.txt (Google-hosted PDF of the WWW 2015 paper) | https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/43783.pdf | retrieved 2026-11-10
- Quote: "Acquaintances with whom participants reported being unwilling to share their webmail passwords were able to guess 17% of their answers." (Schechter abstract)
- Quote: "Participants forgot 20% of their own answers within six months." (Schechter abstract)
- Quote: "13% of answers could be guessed within five attempts by guessing the most popular answers of other" (Schechter abstract; the sentence goes on, after the word participants, "though this weakness is partially attributable to the geographic homogeneity")
- Quote: "those who were trusted by their partners were able to guess their partners' answers 28% of the time." (Schechter §5.5)
- Quote: "Both groups were able to guess the answers to roughly 17% of their partners' questions." (Schechter §5.5; "both groups" = partners not trusted, or trusted only under some circumstances)
- Quote: "acquaintances could guess 17% of answers correctly in five tries or fewer" (Bonneau §2, citing Schechter)
- Quote: "(e.g 40% of our English-speaking US users) were unable to recall their" (Bonneau abstract; the sentence ends "answers when needed")
- Notes: Schechter's table shows 130 participants. The Table 4 total row reads 628 of 2,870 answers guessed by the partner (22%). That is my reading of the columns, not a quoted sentence. Google's questions did best: "Nobody guessed the answer to their partner's ID card answers and the overall guess rate was just 4%." The studies show that knowledge held by someone close is not secret from them. For spoken year of birth against a family member, expect much higher than 17%. This is my inference, not measured.

### F4.6 Answers that sit in public data
- Claim as worded: not in DESIGN.md
- Status: verified
- Corrected wording: Rabkin (SOUPS 2008) found that date of birth and ZIP code questions can be read from structured social-network profiles. About 12% of his question sample was "automatically attackable" this way. Griffith and Jakobsson (2005) derived mother's maiden names from Texas public records. They cut entropy from about 13 bits to below 6.9 bits for over a quarter of the people targeted, and deduced the name for about 4.1 million Texans. They conclude it should be abandoned as an authenticator. Bonneau cites at least 30% of Texas mothers' maiden names as deducible. Rabkin also found four of the institutions he studied required date of birth, and three required ZIP code, as the authenticating answer.
- Source: sources/F/kba-rabkin-2008-soups.txt (CMU CUPS-hosted proceedings PDF) | https://cups.cs.cmu.edu/soups/2008/proceedings/p13Rabkin.pdf | retrieved 2026-11-10. sources/F/kba-griffith-jakobsson-2005-messin-with-texas.txt (Springer PDF, freely downloadable) | https://rd.springer.com/content/pdf/10.1007/11496137_7.pdf | retrieved 2026-11-10. Abstract listing only: sources/F/kba-griffith-jakobsson-2005-passwordresearch-abstract.txt | https://www.passwordresearch.com/papers/paper334.html (secondary)
- Quote: "Date of birth and ZIP code, which are often mandatory questions, fall into this category." (Rabkin §4.3)
- Quote: "Roughly 12% of our question sample was automatically attackable, meaning that answers to those questions could be found on a social networking site." (Rabkin §4.3)
- Quote: "four require users to specify their date of birth to authenticate, three require a ZIP code, and one requires the user's mother's maiden name." (Rabkin §4.1)
- Quote: "reduce the entropy of a mother's maiden name from an average of close to 13 bits down to below 6.9 bits for more than a quarter of the people targeted" (Griffith abstract)
- Quote: "This emphasizes the need to move away from mothers maiden names as an authenticator." (Griffith abstract)
- Quote: "we were able to deduce the mother's maiden name for approximately 4,105,111 Texans." (Griffith abstract)
- Quote: "at least 30% of Texas residents' mothers' maiden names can be deduced from birth and marriage records" (Bonneau §2)
- Quote: "had answers routinely listed publicly in online social-networking profiles" (Bonneau §2, citing Rabkin: 16% of questions)
- Notes: US and Texas data. Texas birth records hide parents' names for 50 years, per the paper's own discussion. The maiden-name result is not transferable to India. In India many women change surnames on marriage, but surname conventions vary, and no Indian measurement was found. Do not cite a mother's-maiden-name guess rate for India.

### F4.7 India exposure of date or year of birth and PIN code, plus how many birth years are plausible
- Claim as worded: not in DESIGN.md
- Status: verified for the leak fields (a vendor's first-hand report). unverifiable from a saved primary source for the printed documents (Aadhaar, PAN) and the electoral roll.
- Corrected wording: Resecurity reported in October 2023 that a seller on BreachForums offered "815 million" Indian records. The seller's field list included name, father's name, phone numbers, Aadhaar number, age, gender, address, district and pincode. Resecurity verified only a leaked part: 400,000 records, with sampled Aadhaar IDs checked against UIDAI's "Verify Aadhaar" feature and victims contacted. The 815 million figure is the seller's claim and is not independently confirmed. The seller did not say where the data came from. The field list has age, not date of birth, but age gives the birth year within two values. One leaked record would hold the phone number, the age and the PIN code together. So a person holding such a record can answer a year-of-birth or PIN-code question without knowing the customer.
- Source: sources/F/kba-resecurity-india-pii-aadhaar-2023.txt | https://www.resecurity.com/blog/article/pii-belonging-to-indian-citizens-including-their-aadhaar-ids-offered-for-sale-on-the-dark-web | retrieved 2026-11-10. Secondary press coverage: sources/F/kba-medianama-815m-breach-2023.txt | https://www.medianama.com/2023/10/223-aadhaar-815-million-indian-data-breach/
- Quote: "- fathersName" (Resecurity field list; the same list contains "- age", "- address", "- pincode")
- Quote: "In total the actor leaked 400,000 records containing AADHAAR details." (Resecurity)
- Quote: "Resecurity acquired all 400,000 records and contacted multiple victims to validate the information" (Resecurity)
- Quote: "Pwn0001 declined to specify how they obtained the data." (Resecurity)
- Notes (arithmetic, labelled as ours, no population data used):
  - An adult borrower aged 18 to 70 on 2026-11-10 was born between 1956 and 2008, so there are 53 plausible years of birth.
  - Ages 21 to 65 give 45 values. If most borrowers are aged 25 to 45, that is 21 values.
  - A blind guess among 53 equally likely years has a 1.9% chance. Among 21 values it has 4.8%. Real ages bunch in working years, so the true blind-guess rate is likely higher than 1.9%.
  - A relative, a colleague or anyone holding a leaked record knows the answer.
  - The PIN-code space was not counted. No source for the number of Indian PIN codes was found.
  - Not retrieved, so unverified here: that Aadhaar and PAN cards print date of birth (an Aadhaar can show only the year), and that electoral rolls publish age and address (see list c).

### F4.8 Should an institution ask the customer for personal data on an outbound call? Both views
- Claim as worded: not in DESIGN.md
- Status: unverifiable for the exact proposition (that outbound identity questions train customers to answer vishing calls). The adjacent statements are verified.
- Corrected wording: No source found says plainly that an outbound caller should not ask for personal data to prove identity because it trains customers to answer vishing calls. Statements that point that way, all from first-hand pages:
  - The FTC tells customers never to share personal or account information with a caller, "no matter who says they're calling". It also warns that a caller can know a customer's name, address or accounts and still be a scammer.
  - RBI, ICICI and HDFC say not to share OTP, PIN and card details even with someone who claims to be the bank.
  - Monzo takes the opposite practice. It does ask security questions on calls it makes, but only after arranging the call in the app and showing call status in the app. In the same pages it says it never asks for "any personal information", and never asks the customer to accept a notification on the phone.
  - Starling says that when it calls, it never asks for a PIN, password or a payment to a new account.
- Source: sources/F/kba-ftc-unexpected-calls-2026-archive.txt (web.archive.org copy of consumer.ftc.gov; the live URL returned 404 to my fetch) | https://web.archive.org/web/2026/https://consumer.ftc.gov/consumer-alerts/2026/01/how-handle-unexpected-calls-claim-your-money-risk | retrieved 2026-11-10. sources/F/kba-monzo-blog-call-status-2023.txt | https://monzo.com/blog/2023/09/06/making-it-clear-when-were-on-a-call-with-you/ . sources/F/kba-monzo-is-monzo-calling-me.txt | https://monzo.com/learn/money-safety/is-monzo-calling-me . sources/F/kba-starling-159.txt | https://starlingbank.com/blog/fight-fraud-call-159-if-you-suspect-a-scam . sources/E/rbi-press-release-53185-consumer-awareness-fraud.txt . sources/F/kba-icicibank-fraud-prevention.txt | https://icicibank.com/Personal-Banking/debt-service/fraud-prevention.page . sources/F/kba-hdfcbank-security.txt | https://hdfcbank.com/personal/useful-links/security . All retrieved 2026-11-10.
- Quote: "The caller might know things about you—like your full name or address—or your accounts. But that doesn't mean they're trustworthy. Scammers buy or steal this information to make their lies seem believable." (FTC)
- Quote: "And no matter who says they're calling, never share your personal or account information, don't grant anyone remote access to your phone or computer, and keep account verification codes to yourself." (FTC)
- Quote: "And if we do call you we'll always make sure we go through some security questions before discussing anything to do with your account." (Monzo blog)
- Quote: "We'll always go through security questions with you before discussing your account, to confirm we're really speaking to you." (Monzo learn page)
- Quote: "give us your PIN or any personal information" (Monzo, from its "we'll also never ask you to" list)
- Quote: "Remember that if Starling does call you (for example if you've requested a callback), we will never ask you to share your PIN, password or ask you to authorise a payment from your account to a new 'safe account'." (Starling)
- Quote: "Never share your account details such as account number, login ID, password, PIN, UPI-PIN, OTP, ATM / Debit card / credit card details with anyone, not even with bank officials, however genuine they might sound." (RBI press release 2021-2022/1630, in sources/E)
- Quote: "Never share your Card Number, CVV, PIN, expiry date, OTP, Net Banking User ID, Password or URN with anyone, even if the caller claims to be a Bank employee." (ICICI)
- Quote: "Do not share your customer ID, login password, OTP, or any card details over calls, messages, emails or with anyone. The bank will never ask for these details." (HDFC)
- Notes: Monzo is the one first-hand case where a bank asks questions on its own outbound call. It pairs the questions with prior arrangement and in-app call verification. Monzo also says it never asks for "any personal information". The two statements sit side by side in its pages and are not reconciled there. The RBI press release also describes the attack: "Vishing - phone calls pretending to be from bank / non-bank e-wallet providers / telecom service providers in order to lure customers into sharing confidential details".

### F4.9 Recognisable or verifiable calling number
- Claim as worded: not in DESIGN.md
- Status: verified
- Corrected wording:
  - India: TRAI mandates 1600xx for service and transaction calls by RBI, SEBI, IRDAI and PFRDA-regulated entities. TRAI's stated aim is to make these calls trustworthy to the customer, and it bars tagging, blocking or filtering of calls from that series. RBI's circular tells regulated entities to use 1600xx for transactional and service calls "when operationalized". HDFC Bank publishes that it calls only from 1600 and 140 numbers.
  - US: STIR/SHAKEN lets authenticated caller ID travel with the call. It combats spoofed numbers. It does not prove who is calling.
  - UK: 159 is a number the customer dials in, to reach their bank. Stop Scams UK says it cannot be spoofed. Starling says a call from 159 is never real.
- Source: sources sources/E/trai-pr-91-2026-clarifications-1600-140-series.txt and sources/E/rbi-notification-12770-voice-calls-sms.txt (both already saved); sources/F/prac-hdfcbank-official-number-series.txt (saved by another worker, quote verified); sources/F/kba-fcc-stir-shaken-fact-sheet-2024.txt | https://docs.fcc.gov/public/attachments/DOC-407144A1.pdf ; sources/F/kba-stopscamsuk-159.txt | https://stopscamsuk.org.uk/159 ; sources/F/kba-starling-159.txt | all retrieved 2026-11-10
- Quote: "A key objective of assigning designated series for these important communications is to make such calls trustworthy for the customers/ citizen." (TRAI PR 91/2026 para (i))
- Quote: "Undertake transactional / service calls only using '1600xx' numbering series, when operationalized" (RBI notification 12770)
- Quote: "HDFC Bank connects with customers only via 1600 and 140 series numbers." (HDFC Bank number-series page)
- Quote: "The STIR/SHAKEN caller ID authentication framework combats unlawfully spoofed robocalls by allowing authenticated caller ID information to securely travel with the call itself throughout the entire call path." (FCC fact sheet, 31 Oct 2024, Background)
- Quote: "Unlike many long-form numbers, 159 cannot be spoofed" (Stop Scams UK; the sentence continues past this)
- Quote: "No, you will never receive a call from 159." (Starling)
- Notes: A recognisable number is a possession-side signal that the customer can use without answering anything. It is the strongest measure that fits an outbound call from an Indian lender. 1600 is mandatory for BFSI service and transaction calls. A possible gap for the design: TRAI's rule covers calls to existing customers, so check that the call type is service or transactional. The FCC's own caveat that a checkmark is not a guarantee came only from a search summary and is not saved.

### F4.10 Hang up and call back the official number
- Claim as worded: not in DESIGN.md
- Status: verified (FTC, RBI, Starling, FFIEC). Take Five and the FCC page could not be retrieved.
- Corrected wording: The FTC's January 2026 alert says to get basic details, hang up, then contact the company or bank yourself, using the app or website, or the number on a recent statement or the back of the card, and not search results. RBI says to use the official website or contact the branch. Starling says to hang up and dial 159. The FFIEC lists call-backs to a pre-established number as a call-centre control.
- Source: sources/F/kba-ftc-unexpected-calls-2026-archive.txt (as in F4.8); sources/E/rbi-press-release-53185-consumer-awareness-fraud.txt; sources/F/kba-starling-159.txt; sources/F/kba-ffiec-2021-authentication-guidance.txt | retrieved 2026-11-10
- Quote: "Get some basic details, then hang up." (FTC)
- Quote: "Verify the story by contacting the company or bank yourself." (FTC)
- Quote: "Do call the phone number on a recent statement or the back of your card" (FTC)
- Quote: "Always access the official website of your bank / NBFC / e-wallet provider or contact the branch." (RBI press release 2021-2022/1630)
- Quote: "If you're contacted by someone claiming to be from your bank, stop, hang up and dial 159" (Starling)
- Notes: This advice puts the work on the customer, and it is the reverse of answering questions on the call. A lender whose call may be hung up on should be ready for a call-back to a number printed on the loan paperwork. UK Finance's Take Five advice pages were not retrieved (list c). Search summaries repeated "hang up and call back" for Take Five, but none is saved.

### F4.11 Prior notice and in-app call verification
- Claim as worded: not in DESIGN.md
- Status: verified for Monzo. Barclays, Revolut and Indian banks were not found.
- Corrected wording: Monzo says it never calls without arranging it first through in-app chat. When the customer is on a call and opens the app, a banner says whether Monzo staff are on the phone with them. If it does not say so, hang up. Monzo tells customers to ignore claims of a technical fault. If the phone is offline, wait until it is online and check the status.
- Source: sources/F/kba-monzo-blog-call-status-2023.txt | https://monzo.com/blog/2023/09/06/making-it-clear-when-were-on-a-call-with-you/ | retrieved 2026-11-10. sources/F/kba-monzo-is-monzo-calling-me.txt | https://monzo.com/learn/money-safety/is-monzo-calling-me | retrieved 2026-11-10
- Quote: "Remember, we will never call you without arranging it with you first through in-app chat." (Monzo blog)
- Quote: "If you're on a call and open the Monzo app, you should see a banner at the top of the home tab. It'll tell you whether you're on the phone with us or not." (Monzo blog)
- Quote: "If the 'Monzo call status' is showing that a member of the Monzo team isn't talking to you, hang up right away and report it to us." (Monzo blog)
- Quote: "Even if the person you're talking to tries to tell you there's a technical issue or that they're from a specialist team that wouldn't show on the call status, don't believe them." (Monzo blog)
- Notes: This is the verified-channel approach. The customer checks the caller in the bank's own app, with no spoken question. It needs an app, and many Indian borrowers may not use the lender's app. An SMS or in-app message before the call (sent to the number the lender already holds) is the weaker variant. No source was found for it beyond Monzo's "arranging it first" statement.

### F4.12 OTP or push approval to the customer's own device, versus "never read out an OTP"
- Claim as worded: not in DESIGN.md
- Status: verified
- Corrected wording: Two rules sit side by side. (1) Regulators and banks say never read an OTP to a caller, even a "bank official". (2) The FFIEC lists an OTP sent to a pre-established device as a good control for call-centre credential resets. These do not conflict when the OTP is typed by the customer into the bank's own channel, never spoken to the caller. NIST warns that approve-on-your-phone requests can be approved without checking, and Monzo says it never asks a caller on the phone to accept a notification.
- Source: sources/F/kba-nist-sp800-63b-4.txt (Sec. 3.1.3.1 note); sources/F/kba-ffiec-2021-authentication-guidance.txt; sources/F/kba-monzo-is-monzo-calling-me.txt; sources/E/rbi-press-release-53185-consumer-awareness-fraud.txt | retrieved 2026-11-10
- Quote: "This method is no longer considered acceptable because it increases the likelihood that the subscriber would approve an authentication request without actually comparing the secrets as required." (NIST 63B-4, out-of-band note)
- Quote: "accept a notification on your phone" (Monzo, the "on a call, we'll never" list)
- Quote: "sending an OTP to a pre-established communication device" (FFIEC Section 8)
- Notes: A push approval during a call is vulnerable to a caller telling the customer to "approve it". This is a design caution. NIST's note concerns approving a request without comparing codes. The NIST text does not itself ban push approval on a call.

## Could not retrieve

**F1: what Indian regulators say (RBI, TRAI/DoT, DPDP, IRDAI)**

- RBI Kehta Hai home, https://rbikehtahai.rbi.org.in/: captcha page ("What code is in the image?"), no content.
- https://website.rbi.org.in/documents/87730/39710918/PR1817f4a7b3662bec4ad7ac6a2d85eaf937ed.pdf: HTTP 200 but an HTML shell (152 KB), not the PDF.
- https://rbidocs.rbi.org.in/rdocs/content/pdfs/BEAWARE07032022.pdf, and the same URL under `web.archive.org/web/2026/` and `/web/2023/`: HTTP 200, but HTML (captcha or Wayback wrapper). https://www.rbi.org.in/commonman/Upload/English/Content/PDFs/BEAWARE07032022.pdf: a 6 KB HTML error page. What worked: the Wayback CDX index for the rbidocs URL, then the `id_` capture of 2022-03-07.
- https://website.rbi.org.in/en/web/rbi/rbi-kehta-hai/raju-and-forty-thieves and https://website.rbi.org.in/web/rbi/rbi-kehta-hai: JavaScript shells (153 KB), no booklet text; removed. https://website.rbi.org.in/documents/87730/108977001/AlertFamilyEnglish.pdf/d1e84547-186e-c34c-23dc-31e8f593191b: HTML shell.
- "Raju and the forty thieves" PDF via https://scc.bank.in/resources/assets/upload/bank_document/46_20250922173513.pdf (a bank-hosted copy, 17 MB, 86 pages): downloaded but the pages are pictures, with headings only in the text layer; not saved.
- RBI phone-banking OTP file CKUI0209013E.pdf: https://website.rbi.org.in/documents/87730/39710850/CKUI0209013E.pdf gave an HTML shell; Wayback captures of the rbidocs URL (2013-09-08 and 2021-10-24) returned HTTP 429 on 5 tries (with waits); the BankBazaar summary page returned HTTP 500 ("database connection"). Its content and title are unverified.
- Commercial Banks Managing Risks in Outsourcing Directions 2025 and the NBFC outsourcing equivalent: not fetched (budget); I only used what the saved RBC directions say about recovery agents (F1.2). Whether they say anything about agents identifying themselves on calls is unchecked.
- IRDA circular CAD/1/10-11 of 21 Jan 2011 ("Verification of the Authenticity of calls"): one web search found only news summaries (TaxGuru, Deccan Herald); no primary text.
- A DoT order or licence amendment bringing CNAP into force, and the TRAI recommendation-status page showing "under consideration" (seen only in a search summary): not found or not saved.
- No DPDP Board decision or guidance on a third party answering a call exists in what I found (the Board's provisions are in force, but I found no orders).

**F2: what Indian lenders and insurers publish**

- https://www.sbi.co.in/web/personal-banking/information-security: HTTP 404 (a URL I guessed, nothing saved). Only the `onlinesbi.sbi` banner is available for SBI.
- https://iciciprulife.com/insurance-library/fraud-prevention-tips.html: HTTP 403. Retrieved through web.archive.org instead (row above).
- https://beta.pnbindia.in/security-alerts.html: curl status 000 (no connection). A search snippet attributed a "call centre" never-ask line to it, but it was not saved and is not used.
- https://licindia.in/documents/20121/129511/Spurious-calls_161017.pdf/...: HTTP 503, empty file.
- https://indianbank.in/wp-content/uploads/2020/05/Indian-Bank-RFP-for-Call-Centre-Operations.pdf: returned an HTML bot-challenge page, not a PDF. Not retried through the archive.
- https://www.southindianbank.com/UserFiles/file/Call%20Center%20Solution%20RFP%20Approved%20for%20publication%20231116.pdf: HTTP 403.
- https://bankofmaharashtra.in/writereaddata/documentlibrary/a883d883-cf14-4c50-92a5-bce67a14d842.pdf: curl status 000.
- Searched, no first-hand page found: welcome call or PIVC pages for Axis Max Life or Max Life, Star Health, SBI Life, HDFC Life, ICICI Prudential Life; a public RFP or tender with identity-verification data points or a "minimum 2 of 5" rule (three searches); any institution page stating the number of attempts allowed.
- Not fetched, search snippets only: Tata Capital's OTP wording and customer-care pages, HDFC Life's and Star Health's customer-service pages.
- Not tried for budget: UCO Bank, J&K Bank and SIDBI tender documents; the IRDAI PIVC circular PDF attachment; Bank of Baroda, PNB and Kotak welcome-call pages; Bajaj Finance outbound-call scripts.


**F3: vendors' published flows, and the right-party norm abroad (comparison only)**

- https://www.consumerfinance.gov/rules-policy/regulations/1006/6/ and .../1006/interp-6/: HTTP 403, so I used eCFR instead.
- eCFR with date 2026-11-09: HTTP 404, because the latest issue date is 2026-11-06; I used 2026-11-06.
- The Reg F final-rule preamble (85 FR 76734, 30 Nov 2020), so any discussion there of confirming the consumer's identity is unchecked:
  - https://www.govinfo.gov/content/pkg/FR-2020-11-30/pdf/2020-26323.pdf was a different document (a five-page FCC notice). I deleted it.
  - https://www.govinfo.gov/content/pkg/FR-2020-11-30/pdf/2020-22314.pdf returned HTML, not a PDF. I deleted it.
- The current FCA Handbook text of CONC 7 (https://www.handbook.fca.org.uk/handbook/CONC/7.pdf, /7/5.pdf, /7/7.pdf, /7/5.html, /api/handbook/CONC/7, and a web.archive.org snapshot): all returned HTTP 200 but only a JavaScript shell or stub. I used the original 2014 instrument instead, so the current wording of CONC 7.9.10R is unverified. fshandbook.info gave a connection failure.
- https://www.ukfinance.org.uk/policy-and-guidance/guidance/fraud-the-facts-take-five and https://takefive-stopfraud.org.uk/advice/: HTTP 403. No FCA or UK Finance primary text on letting customers verify an unexpected call was retrieved, and I found no in-app call-verification page.
- https://justcall.io/blog/voice-ai-right-party-contact.html: HTTP 410 (deleted).
- The Australian guideline passage that asking for identifying details before the collector identifies itself is a known difficulty is not in the April 2021 text. I searched it for "difficult", "dilemma" and "chicken". Earlier ASIC drafts and the 2014 edition were not read.
- No published outbound identity flow was found, or no page was fetched, for Ozonetel, Knowlarity, Yellow.ai, Uniphore, Credgenics, DPDzero, Spocto/Yubi, CreditMate, Bolna, Vodex, Sarvam (only the STT docs already in sources/C), Twilio, Genesys, Five9, Vapi and ElevenLabs. Searches returned no flow page for them. This is unverifiable, not verified absent.
- No Gnani.ai page was found that describes its own outbound right-party flow.

**F4: how weak knowledge questions are, and the stronger measures**

- `https://www.ffiec.gov/guidance/Authentication-and-Access-to-Financial-Institution-Services-and-Systems.pdf`: 403. The web.archive.org copy worked and is used.
- `https://consumer.ftc.gov/consumer-alerts/2026/01/how-handle-unexpected-calls-claim-your-money-risk`: 404 to my fetch. The web.archive.org copy worked and is used.
- `https://www.fcc.gov/consumers/scam-alert/bank-impersonation-scams`: 403 direct, 404 via archive. `https://www.fcc.gov/call-authentication`: 403. Only the FCC fact sheet PDF was saved.
- `https://www.takefive-stopfraud.org.uk/advice/`: 403 direct. The archive copy held navigation only (script-rendered), so it was deleted. UK Finance Take Five wording, including "hang up and call back", is therefore not saved.
- `https://mndc.uidai.gov.in/images/LR_Aadhaar_Handbook_2026.pdf`: 503. That the Aadhaar prints date of birth (or year only), as a search summary of UIDAI forms suggested, is unverified here. UIDAI's May 2022 advisory on photocopies was reported in the press as issued and then withdrawn within two days. The press reports are not saved and the advisory itself was not retrieved.
- `https://voters.eci.gov.in/download-eroll`: 200, but a 1.5 kB script shell with no content. That electoral rolls publish age and address is unverified from a saved primary source.
- `https://www.incometaxindia.gov.in/documents/d/guest/faqs-on-permanent-account-number`: 403. That the PAN card prints date of birth is unverified.
- `https://www.resecurity.com/blog/article/pii-belonging-to-815-million-indians-offered-for-sale-on-the-dark-web`: 404 (a slug I guessed). The correct URL, found by search, is used.
- `https://monzo.com/help/monzo-fraud-category/monzo-call-status`: 404. The two Monzo pages that loaded are used.
- Axis Bank `https://axisbank.com/escape-the-fraud`: saved, then deleted. The two phrases a search summary attributed to it (a claim that the bank never contacts customers from its toll-free numbers, and a "will not ask for" CVV/OTP/PIN line) were not found in my saved text.
- Not searched at all, for lack of budget: UK NCSC, PCI DSS, ENISA, CERT-In, UIDAI advisories on sharing Aadhaar details. Barclays and Revolut call verification pages. The number of Indian PIN codes. An Indian bank's in-app call verification (one search on Indian bank sites returned only generic "never ask for OTP" pages).
- A search for Griffith and Jakobsson was refused by the search tool on the first attempt. A rephrased search found the paper.

## Researchers' summaries

**F1: what Indian regulators say (RBI, TRAI/DoT, DPDP, IRDAI)**

1. RBI prescribes nothing on how to confirm the customer's identity on an outbound call. It only requires that a recovery agent be made identifiable in advance (notice, authorisation letter, agent ID card, shown at visits), that recovery calls be recorded with notice, and that loan matters be discussed only with the borrower. That is firm for what it says and a firm negative for the rest (searched six direction texts).
2. RBI's BE(A)WARE booklet says genuine entities never ask for username, password, card details, CVV or OTP, and says impostors on calls "share a few customer details such as the customer's name or date of birth" to gain confidence. No RBI list I read names date of birth, PIN code, address or mother's maiden name as something never asked. The advice to the customer is to get numbers from the official website and to cross-check loan offers, not to hang up and call back.
3. The customer-side checks that exist are DoT's: the 1600xx series (cited from E), Sanchar Saathi's Trusted Contact Details (check a number you are calling or receiving a call from), and Chakshu (report a suspect call). Calling-name display (CNAP) is only a TRAI recommendation, with DoT favouring default-on, and I found no order putting it into effect.
4. The DPDP Act's definition of a personal data breach ("accidental disclosure ... that compromises the confidentiality"), s.8(5) safeguards and s.4(1) lawful purpose bear on telling a non-borrower a loan exists, but they start on 13 May 2027, so on 2026-11-10 they are not in force; applying them to a misdirected call is my reading, not a ruling.
5. IRDAI specifies no identity data points for any verification call (the PIVC circular only encourages the call and is superseded). The 2011 distance-marketing guidelines require the caller to name itself, say the call is recorded and run a standardised understanding check on at least 3% of buyers (current status unchecked), and IRDAI's 2019 notice tells customers to verify a caller through the insurer's call-centre number in the policy documents.

**F2: what Indian lenders and insurers publish**

| Institution | Call type | Data points checked | How many / attempts | Source file |
|---|---|---|---|---|
| HDFC Bank | outbound service (1600) and promotional (140) | none stated; "never asks for confidential banking details over a phone call" | not stated | prac-hdfcbank-official-number-series |
| ICICI Bank | outbound IVR transaction confirmation; dispute update (1600 numbers) | none stated | not stated | prac-icicibank-customer-care |
| Axis Bank | Relationship Manager call (1600), promotion (140) | none stated; says it never seeks dates of birth | not stated | prac-axisbank-identify-genuine, prac-axisbank-vishing-never-seeks |
| Kotak | outbound by executives | none stated; "will never ask you for such details as they already have it" | not stated | prac-kotak-fraud-tips |
| SBI, SBI Card, Bank of Baroda, PNB | outbound by officials | none stated | not stated | prac-sbi-onlinesbi-home, prac-sbicard-fraud-prevention-blog, prac-bob-secure-banking, prac-pnb-faq-atm-card-never-ask |
| Bajaj Finance, Tata Capital | outbound | none stated | not stated | prac-bajajfinance-*, prac-tatacapital-fraud-advisory |
| SBI Life, HDFC Life, ICICI Prudential Life | welcome or service call | none stated; SBI Life says do not give DOB on a call | not stated | prac-sbilife-beware-fraudulent-calls, prac-hdfclife-my-service-guidebook, prac-iciciprulife-fraud-prevention-tips |
| LIC | outbound telecaller | says it uses none | not applicable | prac-lic-policy-protection-interests-policyholders-2024 |
| Life insurers generally (IRDAI circular; Bajaj Life) | PIVC | product facts confirmed (sum assured, premium, policy term, premium payment term); identity data points not stated; channel is a video link to the registered contact number | not stated | prac-irdai-pivc-document-detail, prac-bajajlife-pivc-7-steps |

Five plain lines:
1. Is there a common practice in the published material? Yes, but it is a practice of telling the customer what not to share, not of telling the customer what will be asked.
2. What is it? A never-ask list (OTP, PIN, CVV, password, card number) at nine of the ten banks and lenders checked, plus a way for the customer to check the caller: a number series (HDFC Bank, Axis, ICICI) or a call to a number the customer already has (Bajaj Finance, Axis, Bank of Baroda).
3. What about date of birth? Four institutions (Axis, SBI Life, Kotak, LIC) tell customers not to give it on a call. None says it may ask for it.
4. How firm is the evidence? Firm that these pages say these things (quotes verified in the saved files). Not firm on anything about real calls: no script, data-point count or attempt limit was found, and the one retrievable RFP is a technology tender.
5. What it does not show: how many data points any institution actually checks on an outbound call, whether a 2026 outbound bot call asking year of birth is tolerated, or practice at Max Life, Star Health, SBI Life, HDFC Life or ICICI Prudential Life welcome calls. Treat those as unverified.

**F3: vendors' published flows, and the right-party norm abroad (comparison only)**

1. Vendors' published outbound flows mostly check a confirmed name first (Edesy and Retell samples), then one more data point when they name one: date of birth, last four digits (of what, unspecified), an OTP, or ZIP. Several named data points are US ones (SSN, ZIP).
2. No vendor page states a retry limit for a failed identity check, and the only attempt numbers are call-frequency settings. Third-party handling is a one-line "do not discuss" in most pages, and Retell's script is the only one that says what to say instead.
3. The norm that is visible is "verify before disclosing", and the pages disagree on whether an authorised relative counts as the right party (Skit.ai yes, Haptik no). Mobicule's and Exotel's own flows also put the call purpose before verification, and none of the pages resolves that tension.
4. US rules (FDCPA 805(b), Reg F 1006.6(d), 1006.10): before the consumer is confirmed, the caller may talk to a third party only to get location information, must name himself or herself, and must say only that they are confirming or correcting location information. It must not say there is a debt, and may contact that person only once. "Consumer" includes the spouse, a limited-content voicemail may carry only four items, and the rule text and commentary I retrieved say nothing about what counts as confirming identity.
5. The Australian guideline says to establish the person is the debtor on every contact before divulging anything about the debt. Before that, the caller may name its organisation only if the name would not reveal a debt (a bank name is probably fine; a collections-style name is not), and the same limits apply to the spouse and family. It does not say what counts as confirmation, and a third party who refuses should be left alone.
6. The UK's CONC 7.9.10R requires establishing, "by suitably appropriate means", that the person is or acts for the borrower before disclosing debt details, and 7.9.7R requires reasonable steps so third parties do not learn the customer is being pursued. Customer-side guidance is to hang up and call the number on the card or 159, which never calls out, from a different phone or after 10 to 15 minutes. None of the three regimes defines what counts as confirmation.

**F4: how weak knowledge questions are, and the stronger measures**

1. Spoken year of birth, date of birth and PIN code are weak against anyone close to the customer: a relative or colleague knows them, and acquaintances guessed 17% to 28% of other secret-question answers in the best-known study (US webmail questions, not birth data).
2. Against a stranger holding a leaked record they are close to worthless: the listed Indian leak fields include name, phone, age, address and pincode together, and a year of birth falls out of the age within two values.
3. Against a random person guessing blind, a year of birth is one of about 53 adult values (our arithmetic), roughly 2%, and likely higher because ages bunch.
4. NIST (rev 3 and rev 4) says knowledge-based verification must not be used for identity verification, rev 3 allowing it only with non-public, changing answers. The FFIEC says reliable verification does not rest solely on knowledge questions. RBI's 2025 directions govern payments and say nothing on spoken questions.
5. Non-question measures: a recognisable calling number (TRAI's 1600 series, with RBI telling lenders to use it for service calls; the 159 inbound number in the UK), prior arrangement plus an in-app call-status banner (Monzo), and the customer hanging up and calling back a number they already hold (FTC, RBI, Starling, and the FFIEC as a call-centre control).
6. No source found says an outbound caller must never ask identity questions. Monzo does ask, but only on a pre-arranged, app-verified call. The FTC and Indian banks say customers should share nothing with a caller, and an OTP is never read aloud (RBI, ICICI, HDFC).
