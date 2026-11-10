# Findings D: DESIGN.md section 11 and section 12

Research date 2026-11-10. Sources in `sources/D/` (index: `sources/D/INDEX.md`). Statuses: for D1 to D4 `verified` needs a saved primary document containing the quote; vendor pages, consultancy notes, news and portal summaries are secondary. For D5 `verified` means I recomputed it from `references/pilots/` files; a figure that rests on an unsaved dashboard reading is `unverifiable`. A negative search is never `verified`.

## D1. "Indian SMS-vs-voice response rates (the only data is from Nigeria)"

### D1.1 The Nigerian study
- Claim as worded: "Indian SMS-vs-voice response rates (the only data is from Nigeria)" (DESIGN.md line 166); this entry identifies the study.
- Status: verified
- Corrected wording: cite Lau, Cronberg, Marks, Amaya (2019), "In Search of the Optimal Mode for Mobile Phone Surveys in Developing Countries. A Comparison of IVR, SMS, and CATI in Nigeria", Survey Research Methods 13(3), 305-318.
- Source: `sources/D/D1-lau-2019-nigeria-ivr-sms-cati-srm.pdf` (+ `.txt`) | https://ojs.ub.uni-konstanz.de/srm/article/download/7375/6821 | 2026-11-10
- Quote: "We find that FTF had the highest response rate (99%), followed by CATI (15%), IVR (3%) and SMS (0.2%)." (abstract p. 305). "Among mobile phone modes, CATI has the highest response rate (14.55%), followed by IVR (2.89%) and then by SMS (0.23%)." (Section 4.1). "Number of sample members contacted 36,992 97,092 1,842,017 40,320" (Table 1, CATI/IVR/SMS/FTF).
- Notes: it samples the general population, not a lender's customers: "dialing (RDD) sample of the four main mobile phone networks in Nigeria". It is not a same-time experiment: "We assigned each sampled phone number to either SMS or IVR." IVR ran June–August 2017, SMS September–October 2017, and IVR offered four languages vs two for SMS. The authors write: "It is difficult to compare SMS and IVR response rates because these studies differ in country, length, topic, population, and sample frame." Its literature range for sub-Saharan SMS and IVR: "ranging from 0.7% - 4.8%", with "One outlier is an SMS survey in Kenya" (about 12%). So even in Africa Nigeria is not the only datum. The 0.2% and 3% are cold-contact levels and must not be applied to a callback to a known customer.

### D1.2 "The only data is from Nigeria"
- Claim as worded: "(the only data is from Nigeria)" (DESIGN.md line 166)
- Status: wrong
- Corrected wording: "We can't quote an SMS-versus-voice response rate for India. We found no controlled Indian comparison for a lender's own customers. The closest peer-reviewed mode comparison is Nigeria, general population, cold contact (CATI 15%, IVR 3%, SMS 0.2%), which is a different setting." Do not write "the only data is from Nigeria".
- Source: table below | 2026-11-10
- Quote (examples): "If calls were initiated by users, 50%-60% of the calls were answered as compared with calls that were pushed by the system (20%-25%)." (BMJ Open 2022, Mobile Vaani, Bihar). "After all callbacks, 116 calls were answered, giving a total pickup rate of 41.1 per cent." (IDinsight). "WhatsApp surveys had the highest response rates compared to SMS and IVR, as well as the highest start rate and survey completion rate." (IPA, Colombia).
- Notes: other data that exist (all saved in `sources/D/`):

| Study | Place | Modes | Result | Primary? |
|---|---|---|---|---|
| Lau 2019 | Nigeria | CATI/IVR/SMS/FTF | 15% / 3% / 0.2% / 99% | primary |
| Pariyo 2019, PLoS ONE, Table 2 | Bangladesh, Tanzania | CATI vs IVR | first-contact response: IVR 558/61,129 (0.9%) vs CATI 429/7,059 (6.1%) in Bangladesh; IVR 557/51,759 (1.1%) vs CATI 384/4,391 (8.7%) in Tanzania | primary |
| IPA, Colombia (randomised; opted-in migrants; incentive) | Colombia | WhatsApp, SMS, IVR | "The response rate for the WhatsApp surveys was 55 percent, 12 percentage points higher than the response rate for IVR and 27 percentage points higher than the response rate for SMS." So IVR 43%, SMS 28% (my subtraction) | secondary summary |
| Chakraborty 2013, ACM DEV | India | IVR vs live operator | "to 31 low-income job seekers in India"; 20 completed both; IVR 4.0% error, 2.5x longer; no SMS arm | primary |
| BMJ Open 2022, Mobile Vaani | India (Bihar) | outbound IVR vs user-initiated | 20-25% vs 50-60% answered; health messaging, not a survey | primary |
| IDinsight pilots | India | 3 IVR variants + SMS-only, 508 farmers, randomised | pickup 41.1% after callbacks; "Only 8 out of 87 farmers made any keypress responses"; SMS-arm result is in an image table, not in the text | secondary |
| Anderson 2024, J. Dev. Econ. | India (Bihar) | phone vs in-person | no SMS/IVR arm | primary |
| Artha CRI note 2023 | India | IVR surveys | "Break-offs rates are high in IVR-based surveys as the respondent may not be engaged." | secondary |

- Conflicting vendor claims for India, none with a method: Gnani, "SMS and email surveys are below 4% response rates." (`D2-vendor-gnani-solutions.txt`); caller.digital, "SMS survey link response rate: 6-12%" on one page and "SMS Survey (link)8-14%" on another; Ksolves, "Omni-channel surveys triggered at loan milestones achieved a 12.8% response rate within 6 months" (one unnamed Indian lender, SMS and email).
- Also: the Artha note says "The length of the survey should be less than four questions." Samajh asks six or more per product; call completion and break-off are a risk that E1 does not measure.

### D1.3 "We found no controlled Indian comparison of SMS vs voice response rates for a lender's customers"
- Claim as worded: the replacement wording in D1.2
- Status: unverifiable (negative result)
- Corrected wording: "searched 2026-11-10; none found"
- Source: search results only.
- Quote: none
- Notes: 12 general web queries on 2026-11-10 (Nigeria mode experiment; India SMS vs IVR vs voice; Gram Vaani / Mobile Vaani; CGAP; India randomized IVR vs SMS; NCAER; Indian vendor blogs; Indian bank SMS survey response; World Bank / J-PAL / CGAP India mode effects; WhatsApp vs IVR vs CATI India; India IVR survey cooperation rate trials; Dimagi / Digital Green / ARMMAN / PAD). I did not search PubMed, J-PAL, Dvara, CGAP or World Bank sites directly, so absence there is not shown. NCAER RFP not retrieved (the URL serves the NCAER home page).

## D2. "Voice AI in India is built for revenue (sales, collections). This product surfaces refunds, so nobody is pushing it."

Method: I saved the home and BFSI or use-case pages of 11 vendors, plus Gnani's banking page and blogs, plus Edesy. A cell is marked when the use case is named as a product, use case, industry flow or FAQ on a saved page. One reader coded it; it counts marketing statements, not deployments or revenue.

| Vendor | Support | Sales/lead | Collections | Renewal/retention | KYC/onboard | Audit/compliance product | Welcome call / post-sale verify | Feedback/NPS/survey |
|---|---|---|---|---|---|---|---|---|
| Gnani | Y | Y | Y | - | Y | Y | Y | Y |
| Sarvam | Y | Y | Y | - | - | - | - | - |
| Skit.ai | - | - | Y (only product) | - | - | Y (inside collections) | - | - |
| Yellow.ai (BFSI) | Y | - | - | - | - | - | - | - |
| Haptik | Y | Y | ~ (reminders) | Y | Y | - | - | Y (one list item) |
| Uniphore | Y | Y | - | - | Y | Y | - | - |
| Ozonetel | Y | Y | Y | Y | Y | Y | - | Y |
| Exotel | Y | Y | Y | - | Y | Y | - | - |
| Ringg | Y | Y | Y | Y | Y | - | Y (insurance) | Y |
| Convin | Y | Y | Y | Y | Y | Y | Y | Y |
| Mihup | Y | Y | Y | Y | - | Y | - | - |
| Count of 11 | 10 | 9 | 8 | 5 | 7 | 7 | 3 | 5 |

### D2.1 "Voice AI in India is built for revenue (sales, collections)."
- Claim as worded: "**Voice AI in India is built for revenue** (sales, collections)." (DESIGN.md line 172)
- Status: secondary-only
- Corrected wording: "Most voice-AI vendors lead with support, sales and collections (of 11 checked on 2026-11-10: 10 list support, 9 sales or lead qualification, 8 collections), but 7 also sell audit or compliance products, 5 list feedback or survey calls and 3 list welcome calls or post-sale verification."
- Source: `sources/D/D2-vendor-*.txt`, `D2-gnani-agentic-ai-for-banking.txt` | 2026-11-10
- Quote: "Marketing & Sales Customer Engagement Customer Support Collections Analytics" (Gnani banking page); "Ten Billion Reasons to Believe" and "Agentic AI has already put an extra $10B on our clients' books, yours could be next." (same page); "Skit.ai runs on a team of AI agents for debt collection, each an expert in one part of collections."; "Conversations That Drive Revenue" (Ozonetel); "Sales, collections, support, bookings. Pick one and have the conversation yourself." (Sarvam).
- Notes: Gnani's own solutions page lists six use cases, "Customer Support Lead Qualification Collections & Recovery Appointment Booking Onboarding & KYC Survey Automation"; Survey Automation lists "Key deployments Telecom · Public Sector · Retail · Entertainment" (not BFSI), and Onboarding & KYC lists "Activation welcome calls." The judges include Gnani people.

### D2.2 "This product surfaces refunds, so nobody is pushing it."
- Claim as worded: "This product surfaces refunds, so nobody is pushing it." (DESIGN.md line 172)
- Status: wrong. Caveat: the README defines `wrong` as a primary source contradicting; vendor pages are secondary under your note. I used `wrong` because the vendors' own pages are first-hand evidence of what they market. Downgrade to `secondary-only` if you read the README strictly.
- Corrected wording: delete the sentence. If a replacement is wanted: "We found no vendor page that cites RBI 85Y. Two vendors (Ringg, Edesy) market post-sale verification or welcome calls that flag possible mis-selling. We found no evidence on whether lenders avoid features that surface refunds."
- Source: `D2-vendor-ringg-insurance.txt`, `D2-vendor-ringg-industries.txt`, `D2-vendor-edesy-welcome-calls.txt`, `D2-vendor-gnani-solutions.txt`, `D2-vendor-convin-bfsi2.txt` | 2026-11-10
- Quote: Ringg FAQ: "Ringg can run a structured verification conversation after a sale, compare the customer's understanding and declarations with the policy information, flag mismatches, and route correction, endorsement, or review requests to the appropriate team." and "Ringg can consistently check what a customer understood against approved policy details and flag potential discrepancies for investigation. Final compliance decisions and sensitive corrections remain with the insurer's authorised team." Ringg hero: "After a sale, it verifies customer understanding and declarations, flags potential discrepancies or mis-selling, and routes corrections or sensitive cases to human review." Edesy (10 Sep 2026): "The welcome call is also the best moment to catch mis-selling." and "If the customer says "I was told this is a fixed deposit" or "I thought the premium was one-time", the agent records it and routes the case to a person immediately." Convin: "Guide customers through welcome calls and first-payment setup." Gnani: "Activation welcome calls." and "Post-transaction feedback via CRM triggers."
- Notes: marketing claims, no 85Y mentioned, no deployment evidence. Ringg's function is close to Samajh but for insurers.

## D3. "The cheap way is legal. An SMS survey satisfies 85Y, so the default is a checkbox."

The legal half belongs to group A.

### D3.1 What a secondary note says
- Claim as worded: n/a (context)
- Status: secondary-only
- Corrected wording: none
- Source: `sources/D/D3-vinodkothari-from-consent-to-compensation.pdf` (+ `.txt`) | https://vinodkothari.com/wp-content/uploads/2026/06/From-Consent-to-Compensation_-RBIs-Draft-Directions-for-REs-on-Sales-Practices.pdf | consultancy
- Quote: "to obtain feedback within 30 days from sale of any product/ service"; "may include random selection of customers, and obtain feedback through call-backs/ surveys"; "to be carried out by a department/ vertical not associated with the sale of products/ services"; "Para 85Y and 85Z of the Commercial Bank Directions and para 101 Y and 101 Z of the NBFC Directions".
- Notes: it restates the rule and says nothing on bank implementation or on SMS. Useful to group A as a secondary confirmation of paragraph numbers.

### D3.2 "so the default is a checkbox"
- Claim as worded: "The cheap way is legal. An SMS survey satisfies 85Y, so the default is a checkbox." (DESIGN.md line 171)
- Status: unverifiable
- Corrected wording: "The rule says 'call-backs or surveys' and names no channel, so a low-cost survey is the likely default (our inference; we found no bank or industry statement on how banks will comply)."
- Source: none.
- Quote: none
- Notes: 2026-11-10 queries, all returning only rule restatements or fee-income commentary: Second Amendment Directions plus law-firm note; "85Y" plus implementation challenge (extended); IBA or FIDC representation; "banks seek clarity ... industry body"; bank tender or RFP for customer feedback or welcome calls (including a GeM variant); "85Y" plus voice AI; compliance-head interview, webinar or conference; brokerage and analyst notes on bancassurance fee income. No tender, IBA, FIDC, conference or webinar item found for June–November 2026. One explainer says banks may need "an independent compliance vertical" for call-backs; that is interpretation.

### D3.3 Evidence of how banks plan to comply with 85Y
- Claim as worded: n/a (question put to me)
- Status: unverifiable
- Corrected wording: "we found no public statement from a bank, NBFC or industry body on how it will run 85Y feedback (searched 2026-11-10)"
- Source: none.
- Quote: none
- Notes: see D3.2.

## D4. "Banks may build it in-house or adapt survey bots"

### D4.1 RBI Key Facts Statement
- Claim as worded: n/a (interviewer question). Related: section 5 step 4.
- Status: verified (the text; the circular number is no longer the operative citation)
- Corrected wording: cite para 348 of the Commercial Banks - Responsible Business Conduct Directions, 2025 (para 29 for NBFCs), which carry the text of RBI/2024-25/18. Para 464 of the 2025 Directions says the earlier instructions "stand repealed". The repeal list itself is not saved, so the repeal of RBI/2024-25/18 is very likely but not confirmed. Keep the limiting words: "retail and MSME term loans" and "charges recovered ... on behalf of third-party service providers on actual basis".
- Source: `sources/D/D4-rbi-kfs-circular-2024-04-15-notification-page.html` (+ `.txt`) | https://rbi.org.in/Scripts/NotificationUser.aspx?Id=12663&Mode=0 | RBI/2024-25/18, 15 Apr 2024 (primary). Carried into `sources/D/D4-rbi-nbfc-rbc-directions-2025-master-direction-page.html` (+ `.txt`) | https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12942 | RBI/DOR/2025-26/362, 28 Nov 2025, "Updated as on July 1, 2026", para 29.
- Quote: para 2: "The harmonised instructions shall be applicable in cases of all retail and MSME term loan products extended by all regulated entities (REs)." Para 4: "Contents of KFS shall be explained to the borrower and an acknowledgement shall be obtained that he/she has understood the same." Para 5: "the KFS shall be provided with a unique proposal number and shall have a validity period of at least three working days for loans having tenor of seven days or more, and a validity period of one working day for loans having tenor of less than seven days." Para 7: "Charges recovered from the borrowers by the REs on behalf of third-party service providers on actual basis, such as insurance charges, legal charges etc., shall also form part of the APR and shall be disclosed separately." Para 8: "Any fees, charges, etc. which are not mentioned in the KFS, cannot be charged by the REs to the borrower at any stage during the term of the loan, without explicit consent of the borrower." Para 10: "Credit card receivables are exempted from the provisions contained under this circular." Para 11: "all new retail and MSME term loans sanctioned on or after October 1, 2024, including fresh loans to existing customers, shall comply with the above guidelines in letter and spirit without any exception." NBFC RBC Directions para 29(1): "Contents of KFS shall be explained to the borrower and an acknowledgement shall be obtained that they have understood the same."
- Notes: para 4 is a pre-contract acknowledgement of understanding. Paras 7 and 8 mean a lender-routed insurance premium belongs in the KFS and APR, so the hero case is a KFS failure or a post-KFS change; the demo must not imply no KFS was given. The RBI relies on an acknowledgement for the KFS, which an interviewer may use against "a yes does not show understanding"; the answer is the Ombudsman awards (group B). Credit cards are exempt, so the card add-on headroom idea is outside the KFS rules. The consolidated NBFC page (updated 1 Jul 2026) has no "feedback" paragraph, so it does not include 101Y; do not cite it for 101Y. I did not retrieve the commercial-bank RBC Directions page.

### D4.2 Cooling-off and look-up provisions
- Claim as worded: n/a (interviewer question)
- Status: verified
- Corrected wording: "Under the RBI Digital Lending Directions 2025 para 10, a borrower can exit a digital loan without penalty during a cooling-off period of at least one day, set by the lender's board." Do not say every borrower gets N days.
- Source: `sources/D/D4-rbi-digital-lending-directions-2025-notification-page.html` (+ `.txt`) | https://rbi.org.in/scripts/NotificationUser.aspx?Id=12848&Mode=0 | RBI/2025-26/36, 8 May 2025 (primary)
- Quote: para 10(i): "The borrower shall be given an explicit option to exit a digital loan by paying the principal and the proportionate APR without any penalty during an initial “cooling-off period”. The cooling off period shall be determined by the Board of the RE as laid down in their loan policy, subject to the period so determined not being less than one day." Para 10(ii): "RE may retain a reasonable one-time processing fee, if the customer exits the loan during the cooling-off period. This, if applicable, shall be disclosed to the customer upfront in KFS."
- Notes: scope is "digital loan". I found no cooling-off paragraph in the consolidated NBFC RBC page; the NBFC Credit Facilities Directions were not retrieved. Three windows exist: KFS validity (3 working days or 1), digital-loan cooling-off (at least 1 day), insurance free-look (D4.5). The script's "N days" must say which.

### D4.3 "Banks may build it in-house or adapt survey bots"
- Claim as worded: "Unknowns: banks may build it in-house or adapt survey bots" (DESIGN.md line 175)
- Status: secondary-only
- Corrected wording: keep as an unknown: "We found no public statement from any bank on how it will run 85Y feedback." Optional: Bank of Baroda built bob SAMVAD in house (a branch assistant, not a feedback tool); an unnamed Indian lender used Salesforce Feedback Management for SMS/email surveys.
- Source: `D4-news-bob-samvad-in-house.txt` (news, 10 Apr 2026); `D4-vendor-ksolves-indian-fi-feedback-case.txt` (vendor case study)
- Quote: "Developed in house"; "The institution had no survey or feedback mechanism at any stage of the loan or credit card lifecycle"
- Notes: both show the options exist, not that any bank plans either for 85Y.

### D4.4 Banks running post-sale feedback or welcome calls today
- Claim as worded: section 1: "Lenders already make confirmation calls, but they ask yes/no questions" (no source in the design)
- Status: secondary-only
- Corrected wording: "In the Ombudsman awards we reviewed, the insurer's evidence was a recorded yes/no confirmation" (group B). Delete the sentence about lenders unless sourced.
- Source: `D2-vendor-gnani-home.txt`, `D2-vendor-edesy-welcome-calls.txt`, `D4-vendor-ksolves-indian-fi-feedback-case.txt`
- Quote: Gnani testimonial (unnamed bank, salary card): "we chose Gnani's Voice AI to engage customers post-transaction" and "achieving a connect rate of over 85%". Edesy's sample loan welcome call (vendor script): "Kya aapko Key Fact Statement mil gaya? Aur kya aap jaante hain ki aap cooling-off period mein bina penalty ke loan band kar sakte hain?"
- Notes: no primary source (bank, regulator, tender) shows what a named lender does on a welcome or feedback call. Searches returned vendor blogs, a Scribd script and a consumer-news item. Claims that insurer welcome calls are "mandatory" were not backed by an IRDAI document.

### D4.5 IRDAI free-look (the script's "cancel within N days")
- Claim as worded: section 5 step 4, "Do you know you can cancel it within N days?"
- Status: secondary-only
- Corrected wording: keep N as a record field; cite "free look at least 15 days (30 for electronic or distance-mode policies) per the IRDAI portal; confirm against the regulation".
- Source: `sources/D/D4-irdai-policyholder-portal-free-look.txt` | https://policyholder.gov.in/protecting-you (regulator-run summary, not the regulation)
- Quote: "The insured will be allowed a period of at least 15 days (30 days in case of electronic policies and policies sourced through distance mode) from the date of receipt of the policy to review the terms and conditions of the policy and to return the same if not acceptable."
- Notes: Edesy says "IRDAI provides 30 days from receipt of the policy document for health insurance policies and for life insurance policies with a term of one year or more" and cites the same portal; the portal text I fetched says 15 (30 for electronic or distance). They disagree; the IRDAI regulation was not retrieved. Outside groups A to E; flag for the manager.

### D4.6 Credit-life demand context
- Claim as worded: n/a
- Status: secondary-only
- Corrected wording: none; background only.
- Source: search snippets (Business Standard 12 Feb 2026, 403 on fetch; Financial Express). Not saved.
- Quote: none saved
- Notes: reports the draft rules may hit insurers' credit-life business. Not relied on.

## D5. Measured-number claims (local files only; no API call)

Files: `references/pilots/amounts-pilot-2026-11-10.md` (line numbers are its lines), `results.json` (80 rows), `pilot.py`, `score.py` (re-run with `python3 -I score.py`). `ledger.jsonl`, `cache/` and `audio/` are gitignored and absent; `results.json` has no latency, credit or header fields. For corroboration I also read `.samajh/probe/log.jsonl` (gitignored, written by work package W2 on 2026-11-10, 170 rows, another worker's output); a 429 excerpt is saved as `sources/D/D5-probe-log-429-excerpt.jsonl`.

### D5.1 "~0.02 credits per STT call"
- Claim as worded: "Measured cost (pilot): ~0.02 credits per STT call, ~0.06 per TTS call." (DESIGN.md line 135)
- Status: unverifiable
- Corrected wording: "About 0.02 credits per short (about 3 s) Prisma REST call, from one dashboard reading on 2026-11-10 (n = 78 billed STT calls); the STT/TTS split was read off a chart and no screenshot is saved." Save a screenshot.
- Source: pilot write-up lines 30-31
- Quote: "2.96 credits (₹2.96) for 98 billed requests (78 STT + 20 TTS; the two 504s were not billed) = ~₹0.03 per request. The chart split is roughly STT ≈ 1.7 and TTS ≈ 1.2"
- Notes: n = 78 STT (rows with status 200: 20 + 20 + 18 + 20; the two 504s are kn01, kn03, v2.5 phone, confirmed). 1.7/78 = 0.0218. Clip length is about 3 s; real turns reach 30 s; whether billing is per call or per second is unknown. Write-up line 25 still says "Credit cost not measured", superseded by line 31; delete it.

### D5.2 "~0.06 per TTS call"
- Claim as worded: as D5.1
- Status: unverifiable
- Corrected wording: "About 0.06 credits per short Timbre sentence (n = 20)", same fix.
- Source: same
- Quote: same
- Notes: 1.2/20 = 0.060. The 20 inputs are 6 to 9-word sentences; real prompts are longer and cost may scale with text.

### D5.3a Credit arithmetic
- Claim as worded: "The full plan with 4 languages (~1,350 TTS + ~7,400 STT) ≈ **240 credits (<5% of 5,000)**." (DESIGN.md line 135)
- Status: verified (arithmetic only)
- Corrected wording: "about 230 to 265 credits, 4.6% to 5.3% of 5,000, depending on the STT/TTS split".
- Source: recomputed
- Quote: n/a
- Notes: stated rates 1,350 x 0.06 + 7,400 x 0.02 = 229 (4.6%); unrounded split (0.0218 and 0.060) = 242 (4.8%), the source of "about 240"; flat 2.96/98 = 0.0302 per request x 8,750 = 264 (5.3%). So "<5%" fails under the flat reading. `ORCHESTRATION.md` sets "Total cap 1,000 across the project", so 240 is 24% of the operative cap.

### D5.3b The plan counts (~1,350 TTS + ~7,400 STT)
- Claim as worded: as D5.3a
- Status: unverifiable
- Corrected wording: show the derivation (scenarios x turns x conditions x models) or say "planned".
- Source: none; not derived in DESIGN.md, IDEAS-HILLCLIMB.md or the write-up.
- Quote: none
- Notes: 96 scenarios x about 9.6 customer turns x 4 conditions x 2 models gives about 7,400; I could not confirm that reconstruction.

### D5.4 "STT median 0.3 s, TTS 0.8 s"
- Claim as worded: "Latency (pilot): STT median 0.3 s, TTS 0.8 s." (DESIGN.md line 136)
- Status: unverifiable
- Corrected wording: "STT about 0.2 to 0.3 s and TTS about 0.6 to 0.8 s on short clips and sentences."
- Source: write-up line 5; `results.json` has no timing; `pilot.py` logs `secs` only to the absent ledger.
- Quote: "Median latency: TTS 0.8 s, STT 0.3 s."
- Notes: W2 probe log corroborates: `stt` n = 17 median 0.338 s; `lat-stt` n = 40 median 0.222 s; `tts` n = 9 median 0.831 s; `lat-tts` n = 40 median 0.581 s. Clips were short; 10 to 30 s turns will be slower.

### D5.5 429 "Only 1 active request"
- Claim as worded: "**Concurrency 1** (429 "Only 1 active request")" (DESIGN.md line 133)
- Status: verified
- Corrected wording: say the message was seen in a burst test on 2026-11-10, not in the pilot (the pilot recorded no 429).
- Source: `sources/D/D5-probe-log-429-excerpt.jsonl`
- Quote: "Only 1 active request is allowed at a time. Wait for your current request to finish before sending another." (error_code `RATE_LIMITED`, three rows 03:40:05 to 03:40:11). A fourth row (`batch-start`, 03:47:08) returned a different body, "Rate limit exceeded".
- Notes: write-up line 5 says "0 × 429", unrecheckable. `RESEARCH.md` line 67 says the docs "show "1 active request" as an example limit". A second throttle exists; W2 owns it.

### D5.6 "Prisma dropped 'paune' from 'paune do lakh'"
- Claim as worded: "The pilot showed why: on the phone line, Prisma dropped "paune" from "paune do lakh"." (DESIGN.md line 69)
- Status: verified
- Corrected wording: "In one sentence with 'paune do lakh' (n = 1, one synthetic voice), Prisma v3.0 on simulated 8 kHz phone audio returned 'unhone 2,00,000'; v2.5 kept it."
- Source: `results.json`, id `hi08`, config `v3.0_transcribe`, cond `phone8k`; config `v3.0_auto`
- Quote: v3.0 phone `"उन्होंने 2,00,000 रुपये जमा किए।"`; indic-auto `"उन्होंने दो लाख रुपये जमा किए।"`; v2.5 phone `"पौने ₹2,00,000 जमा किए"`; gold `"पौने दो लाख रुपये जमा किए।"` (`pilot.py`).
- Notes: n = 1; only one of 20 sentences contains "paune". It is a substitution, not a deletion; v3.0 clean kept the word. The design's wording generalises one observation.

### D5.7 "the fraction-aware parser fixed every case where ITN went wrong"
- Claim as worded: "In the pilot it fixed every case where Prisma's digit conversion (ITN) went wrong." (DESIGN.md line 118)
- Status: verified (in-sample)
- Corrected wording: "On the 20-sentence pilot (one TTS voice) the fraction parser corrected all 8 transcripts (5 distinct sentences, Hindi and Tamil) where Prisma's digits ignored the fraction word. It was written after seeing those results and has no held-out test."
- Source: `score.py` run on `results.json`; write-up lines 11-13, 18-19
- Quote: score.py rows: v2.5 phone n=20, digits 16, naive 11, fixed 16, words 2, err 2; v3.0 clean 20 digits, naive 18, fixed 20; v3.0 phone 19 digits, naive 17, fixed 18, words 1. Fixed cases: hi03 (v2.5 phone); hi04 (v3.0 clean, v2.5 phone, v3.0 phone); hi08 (v3.0 clean, v2.5 phone); ta02, ta04 (v2.5 phone). hi08 v3.0 phone stays wrong (recognition miss).
- Notes: "16/16" and "18/19" divide by transcripts containing digits. Counting all 20: v2.5 phone 16/20 (word-only hi02 and hi05; two timeouts), v3.0 phone 18/20 (word-only hi06; one miss), v3.0 clean 20/20. `FRACTIONS` in `score.py` holds exactly the test items' words. Kannada fraction words never failed (kn02 and kn04 came back as correct digits), so the Kannada rule ran 0 times. Write-up finding 1's "5 cases vs 2 on v3.0" counts v3.0 clean only (v3.0 phone has a third, hi04), and v2.5 was run only on phone audio. Call the normaliser "in-sample", not "pilot-proven".

### D5.8 The documents disagree on the full-plan cost
- Claim as worded: `DESIGN.md` line 135 "≈ **240 credits**" vs `IDEAS-HILLCLIMB.md` line 127 "the full plan ≈ 180 credits (~4% of the budget)"; write-up line 31 "(~1,010 TTS + ~5,560 STT) costs about 180 credits".
- Status: wrong (the documents are inconsistent)
- Corrected wording: carry one plan and state its counts; 240 (four languages, later document) is the one to carry.
- Source: arithmetic
- Quote: n/a
- Notes: 1,010 x 0.06 + 5,560 x 0.02 = 172 (182 unrounded); 1,350 x 0.06 + 7,400 x 0.02 = 229 (242 unrounded). Both are right for their plans; the plans differ by 33% (1,350/1,010 = 1.34; 7,400/5,560 = 1.33).

### D5.9 Other write-up checks
- Claim as worded: write-up lines 5 and 11-14
- Status: verified
- Corrected wording: none beyond the above
- Source: `results.json`, `pilot.py`, `score.py`
- Quote: n/a
- Notes: 20 sentences = 8 Hindi + 4 Hinglish + 4 Tamil + 4 Kannada; voice Shivani, `timbre-v3.0`, 16 kHz; phone = ffmpeg 8 kHz μ-law; Hinglish sent as `hi-IN`; 80 STT rows with the only non-200 rows two 504s (kn01, kn03, v2.5 phone). indic-auto: 0 of 20 contain digits; I compared the 20 transcripts to the source text and only hi08 is wrong, so "19/20" holds. v2.5 returned digits for ta02, ta04, kn02, kn04 ("docs understate v2.5" holds). The pilot's v2.5 requests carry no `model` field; the W2 log shows such a request returns `"model":"prisma-v2.5"`. "0 × 429" not checkable.

### D5.10 "only measured numbers, each with n and audio source", applied to the design
- Claim as worded: section 11 rule (DESIGN.md line 164)
- Status: verified (the design breaks its own rule)
- Corrected wording: add n and audio source to each pilot number in sections 5, 6, 8, 12.
- Source: `DESIGN.md` lines 69, 118, 135-136, 173
- Quote: "Measured cost (pilot): ~0.02 credits per STT call, ~0.06 per TTS call."; "Latency (pilot): STT median 0.3 s, TTS 0.8 s."; "Off-the-shelf speech recognition mangles fractions (pilot)."
- Notes: all come from 20 TTS sentences in one voice.

## Contradictions inside DESIGN.md sections 1 to 13 against section 11

1. Section 12 heading "Why nobody has built this" and reason 3 "so nobody is pushing it" against the ban on "nobody does this". D2.2 contradicts the substance. Suggested heading: "Why we think this is not yet common (our read)".
2. Section 1 "there are many like it" is an unquantified prevalence hint; use "several Insurance Ombudsman awards (group B)". "Lenders already make confirmation calls, but they ask yes/no questions" is unsourced (D4.4) and conflicts with vendor pages describing understanding-based welcome calls.
3. Section 2 "Samajh is that mechanism." 85Y puts the duty on the bank (selection method, non-sales unit, 30 days, half-yearly report). Suggested: "Samajh is a tool a bank's non-sales unit can use to run that mechanism." As written it reads as "complies with 85Y".
4. Section 2 marks HFC coverage via 157A "[verify]" while section 11 lists universal coverage as something we can say. Group A to verify or reword.
5. The demo and rule 4(20A)(ii): the rule is named after the mis-selling definition, demo step 3 shows "red: thinks it's an FD (4(20A)(ii))" and "a refund case is drafted", while section 4 puts "Deciding whether something is mis-selling" out of scope and section 11 bans "this is mis-selling". Relabel the verdict "FLAG FOR REVIEW", the clause "possible issue under 4(20A)(ii)", the refund output "refund-case input for the reviewer, not a finding". The Kothari note lists the refund under "Consequences of mis-selling", so a flag is not the trigger.
6. Section 6: "Any product with a flag → flag_for_review plus a draft refund case" also covers lower-severity flags (`85Y.cover/term/cancel`) and `unclear`. A draft refund for a misremembered cover term presumes a loss. Limit the draft to kind, premium, 85V and 85W flags.
7. Section 13 risk 1 ("SMS is enough, why voice?" — "E1 answers it with our own data"): E1 compares teach-back with yes/no, both by voice, with no SMS or text arm. Add a text-confirmation baseline or reword.
8. Sections 5, 6, 8, 12: measured numbers without n or audio source (D5.10).
9. Sections 4 and 9 (E4) say ≥10 improvised calls per supported language; section 13 says ≥20 improvised human calls. Pick one.

## Could not retrieve

| URL / item | Tried | Result |
|---|---|---|
| https://ncaer.org/?p=13345 (NCAER RFP) | curl, WebFetch | HTTP 200, but the page is the NCAER home page; deleted; not relied on |
| https://ifmrlead.org/?p=6697, https://www.ifmrlead.org/wp-content/uploads/2024/09/IFMR_Report_NDIC.pdf | curl | HTTP 404 |
| https://ndic.ncaer.org/wp-content/uploads/2021/12/8b31715f-a712-4583-8419-ef3543cf2684.pdf | curl, pypdf | retrieved; NDIC report 02 on CATI social discrimination; no SMS/IVR; deleted |
| medium.com IDinsight article | WebFetch | 403; idinsight.org copy used |
| Business Standard credit-life article (Feb 2026) | WebFetch | 403; snippet only |
| website.rbi.org.in NBFC RBC PDF and KFS circular PDF | curl with browser User-Agent | HTTP 200 but the body is the RBI home page, not a PDF; `rbi.org.in` notification pages used |
| gnani.ai/agents, gnani.ai/analytics | curl | 404 |
| Commercial-bank RBC Directions 2025; NBFC Credit Facilities Directions 2025; IRDAI PPI Regulations | not searched or retrieved | open |
| Pilot `ledger.jsonl`, cache, audio; dashboard screenshot | gitignored or never saved | latency, 0 × 429 and credit split cannot be rechecked |
| PubMed, J-PAL, Dvara, CGAP, World Bank site searches | not run | absence there not shown |

## Product implications (most important first)

1. Drop "nobody has built this" and "nobody is pushing it". Position as "a measured, deterministic version for 85Y that we found", not "the first". Ringg, Edesy, Gnani and Convin market adjacent products.
2. E1 does not answer "why not SMS". Add a text-confirmation arm or stop saying it does.
3. Replace "the only data is from Nigeria" with the D1.2 wording. Do not quote any Indian SMS or voice response rate, including Gnani's own "below 4%".
4. Fix pilot numbers before judges hear them: n and audio source on each; save the dashboard screenshot; reconcile 180 vs 240 and mention the 1,000-credit cap; say "about 4% to 5%"; call the parser "in-sample"; say the paune miss was one sentence on one model.
5. Prepare the KFS and cooling-off answer (D4.1, D4.2). The KFS already requires an understanding acknowledgement; the hero case implies a KFS failure or a post-KFS change.
6. Relabel the demo verdict and refund draft (contradictions 5 and 6).
7. "Samajh is that mechanism" becomes "a tool for that mechanism".
8. Report completion and break-off for long calls in E4.

## D6. Consistency table for DESIGN.md sections 11 and 12

Owner key: A = RBI directions; B = Ombudsman cases; C = PIVC, vendors, teach-back, prevalence; E = outbound rules; D = me. Status is blank where another group owns it. For policy bans I use "n/a (policy)" plus whether the design obeys. "Note from D" is a pointer, not a status.

| # | Exact wording (DESIGN.md) | Owner | Status | Corrected wording / note from D |
|---|---|---|---|---|
| D6.1 | "quote 85Y verbatim" (line 164) | A | | |
| D6.2 | "it applies to every RBI-regulated lender from 1 Jan 2027" (line 164) | A | | Note: section 2 says HFCs inherit via 157A "[verify]"; the Kothari note names 85Y/85Z (banks) and 101Y/101Z (NBFCs). |
| D6.3 | "we found no vendor marketing an 85Y understanding callback (searched Nov 2026)" (line 164) | C | | Note: no vendor page cites 85Y, but Ringg and Edesy market post-sale understanding checks that flag possible mis-selling; Gnani and Convin list welcome calls (D2.2). Suggested: "we found no vendor page that cites RBI 85Y; two vendors market post-sale verification that flags possible mis-selling (Ringg, Edesy)." |
| D6.4 | "Ombudsman awards show yes/no calls failed misled customers" (line 164) | B | | |
| D6.5 | "the consent and bundling checks are our added layer" (line 164) | A | | |
| D6.6 | "only measured numbers, each with n and audio source" (line 164) | D | n/a (policy); design breaks it | Add n and audio source at lines 69, 118, 135, 136, 173 (D5.10). |
| D6.7 | "flags for human review" (line 164) | D | n/a (policy); design partly breaks it | Keep. Relabel the red verdict and refund draft (contradictions 5, 6). |
| D6.8 | "'RBI requires voice calls'" (line 166) | A | | |
| D6.9 | "(an SMS survey is allowed)" (line 166) | A | | Note: the 85Y text in section 2 says "modes such as call-backs or surveys" and "may include"; no bank-practice source (D3.2). |
| D6.10 | "'85Y requires consent/bundling checks'" (line 166) | A | | |
| D6.11 | "'captures consent'" (line 166) | A | | Note: section 5 step 5 and rule 85G already say the call never captures consent; consistent. |
| D6.12 | "'prevents mis-selling'" (line 166) | D | n/a (policy); no literal occurrence | "Samajh is that mechanism" (section 2) comes close (contradiction 3). |
| D6.13 | "'this is mis-selling'" (line 166) | D | n/a (policy); design comes close | Rule 4(20A)(ii) and the red demo verdict read as a finding; relabel (contradiction 5). Attribute the section 1 case to the Ombudsman award (group B). |
| D6.14 | "any mis-selling prevalence rate" (line 166) | C | | Note: section 1 "many like it" (contradiction 2). |
| D6.15 | "'PIVC is mandatory'" (line 166) | C | | |
| D6.16 | "Indian SMS-vs-voice response rates" (line 166) | D | wrong as a reason; ban stands | Reword per D1.2. |
| D6.17 | "(the only data is from Nigeria)" (line 166) | D | wrong | Data exist from Nigeria, Bangladesh, Tanzania, Colombia, and Indian IVR data; vendor figures conflict (D1.2). |
| D6.18 | "TTS accuracy presented as real-world accuracy" (line 166) | D | n/a (policy); design breaks it | Say "TTS, one voice, 20 sentences" with every pilot number (D5.10). |
| D6.19 | "'production-ready'" (line 166) | D | n/a (policy); design obeys | No occurrence in sections 1 to 13. |
| D6.20 | "'nobody does this'" (line 166) | D | n/a (policy); design breaks it | Section 12 heading and reason 3 (contradiction 1). |
| D6.21 | "Why nobody has built this (our honest read)" (line 168) | D | wrong | "Why we think this is not yet common (our read)". |
| D6.22 | "**The rule is new.** It was issued in June 2026 and takes effect in January 2027." (line 170) | A (dates); D (causal step) | | Note: the causal "so nobody built it" is inference; Kothari note (secondary) says the Amendment Directions were issued 15 June 2026. |
| D6.23 | "**The cheap way is legal.** An SMS survey satisfies 85Y" (line 171) | A | | Note: D3.1. |
| D6.24 | "so the default is a checkbox." (line 171) | D | unverifiable | "so a low-cost survey is the likely default (our inference; no bank statement found)" (D3.2). |
| D6.25 | "**Voice AI in India is built for revenue** (sales, collections)." (line 172) | D | secondary-only | "Most vendors lead with support, sales and collections; 7 of 11 also sell audit or compliance products" (D2.1). |
| D6.26 | "This product surfaces refunds, so nobody is pushing it." (line 172) | D | wrong | Delete (D2.2). |
| D6.27 | "**It's harder than it looks.** It needs product records, deterministic comparison, and correct Indian amounts." (line 173) | D | secondary-only | A design view, not a fact; Ringg claims a similar comparison for insurers. Keep, labelled as our view. |
| D6.28 | "Off-the-shelf speech recognition mangles fractions (pilot)." (line 173) | D | verified (in-sample, n = 20) | "In our 20-sentence TTS pilot, 5 of the 10 sentences with a fractional amount had digits that ignored the fraction word on at least one config (8 cases overall)" (D5.7). |
| D6.29 | "Unknowns: banks may build it in-house or adapt survey bots" (line 175) | D | secondary-only | Keep as an unknown (D4.3). |
| D6.30 | "we found no data on how common loan-bundled insurance is." (line 175) | C | | |
