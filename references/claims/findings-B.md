# Findings B: Ombudsman and consumer-commission cases

Group B of the claims check (README: `references/claims/README.md`). Research date 2026-11-10. Claims B1 to B8 are the eight cases `DESIGN.md` and `IDEAS-HILLCLIMB.md` cite; B-N1 onward are new cases found in the same compendiums. No complainant is named here (README rule 8). Case numbers, forums, insurers, banks and amounts are used instead.

How the sources work. The Council for Insurance Ombudsmen (cioins.co.in) publishes each award as a short synopsis inside a half-yearly compendium PDF. Every Ombudsman case below was found in a compendium saved under `sources/B/`, with the page numbers quoted. Quotes are copied from the saved `.txt` extraction and checked by a script against it, so PDF extraction artefacts (for example "mis -sold", "secu rity", "Rs.5200 0/-") are kept as they are. The extraction collapses line breaks and runs of spaces. Per-case excerpt files (`excerpt-<case>.txt`) hold the full award text with page markers. The page number is the PDF page of the compendium, not a printed page number.

Two points that apply to every cited case:
1. The case number is `<office>-L-<insurer code>-<year pair>-<serial>`. The year pair `1617` means the complaint was registered in FY 2016-17. The insurer is named in each award; the codes seen here are 001 Aegon (Religare) Life, 013 DHFL Pramerica Life, 014 Edelweiss Tokio Life, 021 ICICI Prudential Life, 033 PNB MetLife, 041 SBI Life.
2. These are Ombudsman synopses of 2016-17 awards, written by the Forum. The synopsis is the primary public text. The full award file is not public.

## Status summary

| Id | Case | Status | One line |
|---|---|---|---|
| B1 | BHP-L-021-1617-0529 | verified, with corrections | Real award. ICICI Prudential Life. Rs 52,000 deducted from a gold-loan amount "as fixed deposit for loan security"; full premium refund ordered. |
| B1b | BHP-L-021-1617-0529, "Rs 5 lakh asked, Rs 4.48 lakh received" | unverifiable | The award gives only the Rs 52,000. The Rs 5 lakh and Rs 4.48 lakh are not in it. |
| B2 | BNG-L-041-1617-0797 | verified, with corrections | SBI Life. Insurer submitted the PIVC recording. Outcome: premium converted to a one-time-premium policy, not a refund. |
| B3 | BNG-L-014-1617-0598 | verified, with corrections | Edelweiss Tokio Life. PIVC "yes" is the insurer's submission. Outcome: conversion to single premium, refund refused. |
| B4 | AHD-L-001-1617-0203 | unverifiable | The quote is real, as the complainant's account. The award mentions no verification-call recording; it says the insurer did not produce the recording of the sales call. Aegon Religare Life; Rs 50,000 plus 12% interest. |
| B5 | BNG-L-033-1617-0600 | verified, with corrections | PNB MetLife; Rs 1,00,000; "security deposit for the overdraft facility" at Karnataka Bank. Converted to one-time premium, no refund. |
| B6 | AHD-L-021-1617-0367 | wrong | ICICI Pru Loan Protect. A death-claim repudiation the insurer won. Not a mis-selling win. |
| B7 | Baramulla DCDRC, CC 33/2025 v J&K Bank | verified, with corrections | Rs 2,00,000 debited from the borrower's account for a MetLife policy without consent. Ex parte; refund plus 8%, Rs 50,000 and Rs 10,000. |
| B8 | DHFL Pramerica award = AHD-L-013-1617-0400 to 0403 | verified, with corrections | The recording "stated that the fund transfer had taken place"; the customer had sent a cheque. Forged signatures also found. Refund Rs 1,12,995. |
| B-N1 to B-N18 | New cases | verified | See below. B-N14 to B-N16 are insurer wins kept as counter-examples. |

Tally of the nine cited-case claims: verified 6 (B1, B2, B3, B5, B7, B8, all with corrections), wrong 1 (B6), unverifiable 2 (B1b, B4). The counts section near the end repeats this and adds the new cases.

### B1 BHP-L-021-1617-0529: "FD for loan security" that was an insurance policy
- Claim as worded: "A borrower asks for a ₹5 lakh loan, receives ₹4.48 lakh, and is told the ₹52,000 difference is "an FD for loan security". It is actually a life-insurance premium. Months later they find out, complain, and an Ombudsman orders a refund. That is a real case (Insurance Ombudsman, BHP-L-021-1617-0529)" (DESIGN.md line 11). Also IDEAS-HILLCLIMB.md line 111 ("₹5,00,000 gold loan, ₹52,000 deducted for a policy, no consent record") and DESIGN.md line 154.
- Status: verified (core facts), with the corrections in the next field; the two loan figures are split out as B1b.
- Corrected wording: Insurance Ombudsman, Bhopal, order dated 21 March 2017 (Order No. IO/BHP/A/LI/0179/2016-2017), respondent ICICI Prudential Life Insurance Co. Ltd. The complainant says Rs 52,000 was deducted from his loan amount by the bank, which called it a fixed deposit for loan security, and the Forum records the complainant's submission that the policy was mis-sold on the pretext of security against a gold loan. The Ombudsman held that he asked for cancellation "within 2 months" and ordered the insurer to cancel the policy and refund Rs 52,000 (full premium; no interest is mentioned). The bank is not named. The award does not mention a verification call; it turned on the free-look objection.
- Source: `references/claims/sources/B/excerpt-BHP-L-021-1617-0529.txt` (full award); compendium `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` pp. 139-140; https://www.cioins.co.in/LIC/miscellanious/Miscellaneous%20-%20Life26.pdf | retrieved 2026-11-10
- Quote:
  - (p. 139) "ICICI Prudential Life Insurance Co.Ltd. Order No.IO/BHP/A/LI/0179/2016-2017 Dated: March 21st, 2017"
  - (p. 139) "A policy was sold to the complainant by the respondent company. An amount of Rs.5200 0/- was deducted from his loan amount by bank telling as fixed deposit for loan security."
  - (p. 139) "The policy was mis-sold to him by giving false information in lieu of fixed deposit."
  - (p. 140) "the policy was mis -sold on the pretext of secu rity against gold loan taken by him. I find he applied for cancellation of the same within 2 months."
  - (p. 140) "the Respondent Company is directed to cancel the policy and refund the premium amount Rs. 52,000/- to the complainant. Decision : Allowed."
- Notes: Matches the design on: the Rs 52,000, the words "fixed deposit for loan security", the gold loan (the demo's "gold loan" is correct), and a refund order. Differences: (1) "Rs.5200 0/-" is an extraction split; the Forum's decision gives Rs. 52,000/-. (2) The award never says the policy is a "life-insurance premium" in so many words; it is in the Life compendium and the respondent is a life insurer, so "life insurance" is a safe reading. (3) "Months later": the Forum says within 2 months of the sale; the insurer says the first letter was dated 04.10.2016. (4) No verification call is discussed, so this case cannot be cited as a "recorded yes" case. (5) The deduction was "from his loan amount", which is the closest any cited case comes to the "premium deducted from the loan" pattern (85W). The Rs 52,000 is 10.4% of Rs 5 lakh, but see B1b.

### B1b BHP-L-021-1617-0529: the Rs 5 lakh / Rs 4.48 lakh figures
- Claim as worded: "A borrower asks for a ₹5 lakh loan, receives ₹4.48 lakh" (DESIGN.md line 11); "₹5,00,000 gold loan" (DESIGN.md line 154).
- Status: unverifiable
- Corrected wording: Say "a gold-loan borrower had Rs 52,000 deducted from the loan amount and described as a fixed deposit for loan security". Present Rs 5,00,000 and Rs 4,48,000 as the scenario's synthetic figures, not as facts of the award.
- Source: `references/claims/sources/B/excerpt-BHP-L-021-1617-0529.txt`; searched the award text for "lakh", "lac", "5,00", "500000", "4,48" and "448" (no hits), and the saved Life 25/26/27 and Death 26 text files for "4,48,000", "448000", "4.48 lakh" and "4.48 lac" (no hits) | retrieved 2026-11-10
- Quote:
  - (none: the loan size and the net disbursal do not appear in the award text; the only amount is "Rs. 52,000/-")
- Notes: The award states no principal and no net amount received. Rs 5,00,000 minus Rs 52,000 equals Rs 4,48,000, so the numbers are internally consistent, but they come from the design, not the Ombudsman. If the demo or the video says "this is what happened in the award", it must not quote the Rs 5 lakh.

### B2 BNG-L-041-1617-0797: banker promised withdrawal after a year
- Claim as worded: "BNG-L-041-1617-0797: a banker promised the money could be withdrawn after a year." under "In several Ombudsman awards the insurer played the customer's recorded "yes" and still lost" (DESIGN.md lines 13-14); IDEAS-HILLCLIMB.md line 109.
- Status: verified, with corrections
- Corrected wording: Insurance Ombudsman, Bengaluru, award date 28.02.2017, respondent SBI Life. The complainant's banker, State Bank of India, had assured him the policy could be cancelled and the money withdrawn any time after one year. The insurer submitted the PIVC call recording to show the complainant "had confirmed availing the policy". The Forum still held the insurer responsible, because the bank acts as its agent, and directed it to put the premium into a one-time-premium policy for the minimum period. That is a partial win for the complainant (conversion), not a refund.
- Source: `references/claims/sources/B/excerpt-BNG-L-041-1617-0797.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` p. 70; https://www.cioins.co.in/LIC/miscellanious/Miscellaneous%20-%20Life26.pdf | retrieved 2026-11-10
- Quote:
  - (p. 70) "Complaint no. : BNG-L-041-1617-0797 Award date 28.02.2017 Mis-Sale - Partial Allowed."
  - (p. 70) "State Bank of India who had persuaded him to avail the afore -said policy and had assured him that the policy could be cancelled and the invested amount could be withdrawn any time after a period of 1 year."
  - (p. 70) "The Respondent on their part submitted before the forum the PIVC call recording to establish that the Complainant had confirmed availing the policy and never brought out any complaint regarding terms of the policy or raised any query."
  - (p. 70) "the bank acts as an agent of the Respondent and procures business on their behalf. Therefore, the Respondent would be responsible for all actions of their agent."
  - (p. 70) "So, the Forum would direct the respondent to put the premium paid in to a one time premium policy for the minimum period as was available with the Respondent."
- Notes: The design is right that a recorded confirmation existed and the insurer still lost. Differences: (1) "played" should be "submitted"; the award does not say the recording was played. (2) The loss was partial: no refund, a conversion to a one-time-premium policy. (3) The Forum's stated reason is agency (the bank is the insurer's agent), not that a "yes" does not prove understanding. (4) The award contains a sentence that cuts against its own result: "no person of ordinary prudence would any way tend to believe that officials of the State Bank of India could in fact mislead." Do not quote that sentence as the Ombudsman's endorsement of the customer. (5) The "banker" is SBI, the lender-side channel, which is the Samajh target (bank sells, insurer holds the paper).

### B3 BNG-L-014-1617-0598: promised one-time premium, got a 15-year policy
- Claim as worded: "BNG-L-014-1617-0598: the customer was promised a one-time premium and got a 15-year policy with 7 years of payments." (DESIGN.md line 15), listed among awards where "the insurer played the customer's recorded "yes" and still lost".
- Status: verified, with corrections
- Corrected wording: Insurance Ombudsman, Bengaluru, award date 12.01.2017, respondent Edelweiss Tokio Life. The complainant alleged a 15-year policy with a 7-year premium-paying term instead of the agreed one-time payment. The insurer said that during the PIVC "the Complainant confirmed all the details of the policy". The Forum gave the complainant the benefit of doubt but refused a refund and let the insurer convert the policy to a single-premium policy for the minimum period. The award does not say that the PIVC recording was produced or played; it records the insurer's statement about it.
- Source: `references/claims/sources/B/excerpt-BNG-L-014-1617-0598.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` p. 62; https://www.cioins.co.in/LIC/miscellanious/Miscellaneous%20-%20Life26.pdf | retrieved 2026-11-10
- Quote:
  - (p. 62) "Complaint No. BNG-L-014-1617-0598 Between"
  - (p. 62) "issued a policy for a period of 15 years with PPT of 7yrs instead of onetime payment policy as was assured and agreed."
  - (p. 62) "During the Pre-Issuance Verification Call (PIVC), the Complainant confirmed all the details of the policy."
  - (p. 62) "The Respondent Insurer was not in a position to substantiate its stood as to how the policy was issued for a term of 10 years instead of policy with a Single Premium as was agreed by the insured Complainant."
  - (p. 62) "the Forum was not willing to concede to his request for refund of the amount paid to the Respondent."
  - (p. 62) "the Respondent Insurer was allowed to convert the policy to a single premium policy for the minimum period as available with the Insurer."
- Notes: The 15-year / 7-year detail is the complainant's allegation. The Forum's own findings paragraph says "a term of 10 years", so the award is internally inconsistent on the term; quote the 15/7 figures as "alleged". The word "loss" is too strong: the complainant did not get his refund. Use the case as "a confirmed PIVC did not stop the Forum converting the policy", not as "recorded yes, insurer paid the money back". The Forum's reason was that the insurer could not substantiate the issue of a multi-year policy where a single premium was agreed.

### B4 AHD-L-001-1617-0203: "answer everything in positive"
- Claim as worded: "AHD-L-001-1617-0203: the customer was told to "answer everything in positive"." (DESIGN.md line 16), listed among awards where the insurer "played the customer's recorded "yes" and still lost".
- Status: unverifiable, in the part that says the insurer played a recorded "yes". The award mentions no verification-call recording. The quoted phrase is in the award, as the complainant's account.
- Corrected wording: Insurance Ombudsman, Ahmedabad, award date 27.06.2016, respondent Aegon Religare Life, policy sold through the intermediary "Ahmedabad Net Ambit". A telecaller offered a Rs 10 lakh loan on a Rs 50,000 policy and told the complainant there would be a verification call and she had to answer everything in positive. The Forum found the insurer "had not produced a voice copy of the tele conversation between the Complainant & Intermediary" (the sales call) and had breached the Protection of Policyholders' Interests Regulations 2002 and the IRDAI Distance Marketing guidelines. The complaint was allowed for Rs 50,000 plus 12% interest. The award is silent on whether a verification call took place or was recorded.
- Source: `references/claims/sources/B/excerpt-AHD-L-001-1617-0203.txt` (the compendium prints this award twice, pp. 27 and 34-35); `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf`; https://www.cioins.co.in/LIC/miscellanious/Miscellaneous%20-%20Life26.pdf | retrieved 2026-11-10
- Quote:
  - (p. 34) "Complaint No. AHD-L-001-1617-0203 Date of Award : 27.06.2016"
  - (p. 34) "continuously offering her loan of Rs. 10 lacs on her investment of Rs. 50,000/- in an insurance policy of the Company."
  - (p. 34) "She was told that there would be a verification call and in reply she had to answer everything in positive."
  - (p. 34) "the Forum found that The Respondent had not produced a voice copy of the tele conversation between the Complainant & Intermediary.The Respondent had violated the provisions of the Protection of Policy -holder’s Interests Regulations, 2002, & Guidelines on Distance Marketing of Insurance Products issued by IRDAI."
  - (p. 35) "The complaint is allowed on its merits for an amount of Rs. 50,000 + 12 % interest."
- Notes: The wording "answer everything in positive" is in the award, as the complainant's account of what she was told. The award does not say a recorded "yes" existed: the insurer lost because it could not produce the recording of the sales conversation. The design's sentence has no support in the award. Move this case out of the "recorded yes still lost" list and into a "coached yes" list, together with B-N5 (AHD-L-001-1617-0439), B-N6 (CHD-L-019-1718-1436) and B-N17. It is also a loan-bait case (a promised Rs 10 lakh loan), not a bundled-with-a-loan case. The tip for scenario writers: the telecaller coached the answer before the call; a callback that asks the customer to explain in her own words is the test that would have caught it.

### B5 BNG-L-033-1617-0600: policy sold as a "security deposit" for an overdraft
- Claim as worded: "BNG-L-033-1617-0600 for bundling" (DESIGN.md line 150); "policy as a "security deposit" for an overdraft → 85V" (IDEAS-HILLCLIMB.md line 113).
- Status: verified, with corrections
- Corrected wording: Insurance Ombudsman, Bengaluru, award date 12.01.2017, respondent PNB MetLife India Life. The complainant paid Rs 1,00,000 "as a requirement of a security deposit for the overdraft facility from the Karnataka Bank Ltd" and was told the premium would be paid back after one year. The Forum noted that the process "got started as it was a precondition for the sanction of the OD from the bank" and, giving the complainant the benefit of doubt, converted the policy into a one-time-premium policy for a minimum term. It did not order a refund.
- Source: `references/claims/sources/B/excerpt-BNG-L-033-1617-0600.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` p. 61; https://www.cioins.co.in/LIC/miscellanious/Miscellaneous%20-%20Life26.pdf | retrieved 2026-11-10
- Quote:
  - (p. 61) "Complaint No. BNG-L-033-1617-0600 Between"
  - (p. 61) "The Complainant availed a policy by paying an amount of ₹.1,00,000/- from the Respondent Insurer as a requirement of a security deposit for the overdraft facility from the Karnataka Bank Ltd."
  - (p. 61) "He was told by the Respondent that the premium amount of ₹.1,00,000/- would be paid back to him after one year."
  - (p. 61) "as the very process of insurance got started as it was a precondition for the sanction of the OD from the bank."
  - (p. 61) "the Forum believes that appropriate justice would be rendered by converting the policy into one time premium payment policy fo r a minimum term as available with the Respondent Insurer."
- Notes: This is the best fit for the design's bundling clause (85V) because the award says in terms that the policy was a precondition of the overdraft. The Forum also records "several signatures on multiple blank forms". Correct the outcome: conversion, not refund. The Forum gave the complainant the benefit of doubt because the insurer could not show the policy was voluntary. No verification call is discussed. The amount, the insurer and the bank are all stated, so a scenario can reuse them with synthetic names.

### B6 AHD-L-021-1617-0367: "Loan Protect" bundled into the EMI
- Claim as worded: "AHD-L-021-1617-0367 for an undisclosed health declaration" (DESIGN.md line 150); "AHD-L-021-1617-0367 (Loan Protect bundled into the EMI → health-declaration teach-back)" (IDEAS-HILLCLIMB.md line 113).
- Status: wrong, if the case is used as a mis-selling win. The bundling detail is in the award; the outcome is the opposite of a customer win.
- Corrected wording: Insurance Ombudsman, Ahmedabad, award date 26.08.2016, respondent ICICI Prudential Life. This is a death-claim case, filed by the nominee of a borrower who died about three months after buying an ICICI Pru Loan Protect policy. The insurer repudiated the claim for non-disclosure of the life assured's health in the proposal form. The Forum found the health questions were answered in the negative although the medical papers showed earlier brain-tumour operations, diabetes and high blood pressure, and dismissed the complaint ("fails to succeed"). The insurer's ex gratia refund of the premium, Rs 13,996, was left undisturbed.
- Source: `references/claims/sources/B/excerpt-AHD-L-021-1617-0367.txt` (printed in both compendiums); `references/claims/sources/B/cioins-LIC-deathclaim-Death-Life26.pdf` p. 33 and `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` p. 38; https://www.cioins.co.in/LIC/deathclaim/Death%20-%20Life26.pdf | retrieved 2026-11-10
- Quote:
  - (p. 33) "ICICI Pru Loan Protect policy on 15.05.2015 from ICICI Prudential Life Insurance Company Ltd."
  - (p. 33) "the policy was taken on 15.05.2015 with an annual premium of Rs. 17,861 (EMI + Insurance Premium)."
  - (p. 33) "the Respondent had repudiated the claim on the basis of non-disclosure of the DLA’s health in the proposal form."
  - (p. 33) "questions relating to health position with Serial No. 4,5,6 & 7 in proposal form were answered in negative.The non-disclosure part was relevant."
  - (p. 33) "The Respondent had decided to make an ex -gratia payment of the premium amount of Rs. 13,996/- which needs no intervention."
  - (p. 33) "In view of the foregoing proved facts, the complaint fails to succeed."
- Notes: What matches: the premium was paid with the EMI ("EMI + Insurance Premium") and the policy was "issued to secure loan" with "no medical examination". What does not: (1) the health non-disclosure is by the life assured ("answered in negative"), and the Forum treated it as the borrower's breach; "an undisclosed health declaration" reads as if the lender hid it from the customer, which the award does not say. (2) The insurer won. Use it, if at all, as a scenario about what happens when a borrower does not understand what a health question means. Do not present it as a case the Ombudsman decided for the customer.

### B7 Baramulla consumer commission v J&K Bank (2026): Rs 2 lakh deducted
- Claim as worded: "Baramulla consumer commission v J&K Bank 2026 case" (DESIGN.md line 150); "Baramulla v J&K Bank 2026 (₹2 lakh premium deducted from a CC loan)" (IDEAS-HILLCLIMB.md line 113).
- Status: verified, with corrections (the order is a scanned copy hosted by a news site, not retrieved from e-Jagriti)
- Corrected wording: District Consumer Disputes Redressal Commission, Baramulla/Bandipora, Consumer Complaint No. 33/2025, instituted 22-04-2025, decided 22-04-2026, against J&K Bank, proceeded against ex parte. The heading reads "opposite parties", and the order refers to a plea of the insurance company. The complainant held a Rs 20 lakh cash-credit loan sanctioned in 2015-16 and liquidated in 2020. The Commission records as admitted that Rs 2,00,000 "was debited from the account of the complainant towards MetLife insurance" and found no material that it was done with consent. The bank did not appear and was proceeded against ex parte. Directions: cancel the policy; refund Rs 2,00,000 with 8% interest from the date of deduction; Rs 50,000 compensation and Rs 10,000 litigation charges; comply within 30 days or the whole sum carries 10% a year.
- Source: `references/claims/sources/B/baramulla-dcdrc-cc-33-of-2025-order-2026-04-22.pdf` (scanned two-page order, copy obtained from the LiveLaw article's attached order link, `https://www.livelaw.in/pdf_upload/2026/05/12/<complaint-name>-v-jk-bank-ltd-anr-673359.pdf`; file renamed to omit the complainant's name); page images `references/claims/sources/B/baramulla-order-page1.png`, `references/claims/sources/B/baramulla-order-page2.png`; reader transcription `references/claims/sources/B/baramulla-order-transcription-by-reader.txt` (the PDF has no text layer; the OCR file is unreliable); news report `references/claims/sources/B/livelaw-2026-05-12-baramulla-jkbank-article.html`; https://www.livelaw.in/consumer-cases/baramulla-consumer-commission-holds-jk-bank-liable-for-deducting-insurance-premium-without-consent-533845 | retrieved 2026-11-10
- Quote:
  - (p. 1) "Consumer Complainant No: 33/2025"
  - (p. 1) "he applied for a Cash Credit loan of Rs. 20 lakh from the OP bank for agricultural purposes, and after completing all the requisite formalities, the amount was sanctioned in his favour in the year 2015-2016. However, he liquidated the said loan amount in the year 2020 and the NOC was issued by the OP bank."
  - (p. 1) "The bank deducted an amount of Rs. 2,00,000/- (Rupees Two Lakh only) from his account for MetLife insurance without his knowledge or consent."
  - (p. 2) "despite service of notice, the OP failed to appear or to submit any response with in the stipulated period of time. As such, the OP was proceeded to ex parte."
  - (p. 2) "It is an admitted fact that an amount of Rs. 2,00,000/- (Rupees Two Lakh only) was debited from the account of the complainant towards MetLife insurance,"
  - (p. 2) "Deduction of a substantial amount from the account of the complainant without explicit consent amounts to clear deficiency in service and unfair trade practice."
  - (p. 2) "The OP bank is further directed to refund the amount of Rs. 2,00,000/- (Rupees Two Lakh only) to the complainant along with interest at the rate of 8% from the date of deduction till its realization."
- Notes: Differences from the design: (1) the order says the money was debited "from the account of the complainant"; it does not say the premium came out of the cash-credit loan amount, and the order does not date the deduction (the loan was liquidated in 2020). "Rs 2 lakh premium deducted from a cash-credit loan" overstates what is in the order. Use "Rs 2 lakh debited from a borrower's account for a MetLife policy without consent". (2) The bank did not appear and was proceeded against ex parte. The order does mention "the plea of the insurance company that the policy has lapsed". It shows a consent gap, not a contested understanding dispute. (3) No call or recording is discussed. (4) The order text in the PDF is a scan; the quotes above come from the reader transcription made from the page images, so a reviewer should look at `baramulla-order-page2.png` for the directions. (5) Do not confuse it with a second J&K Bank order of July 2026 from Kupwara (a Rs 16,000 premium on a deceased borrower's loan account); that is a different case and was not checked here. (6) The order was not retrieved from e-Jagriti or confonet (see "Could not retrieve"); the LiveLaw-hosted copy is a scan of the Commission's signed order.

### B8 DHFL Pramerica award: call recording said "fund transfer", customer paid by cheque
- Claim as worded: "DHFL Pramerica (the recording said fund transfer, the customer paid by cheque)" (IDEAS-HILLCLIMB.md line 113). No case number is given there, and the DHFL case is not in DESIGN.md.
- Status: verified, with corrections. The award is AHD-L-013-1617-0400, 401, 402 and 403.
- Corrected wording: Insurance Ombudsman, Ahmedabad, award date 23.09.2016, respondent DHFL Pramerica Life, four policies sourced by a Delhi broker "over mobile phone". The insurer submitted a copy of the verification call. The Forum notes the recording "stated that the fund transfer had taken place, whereas the Complainant had sent a cheque for Rs. 98,000/- in the year 2013 out of which 3 policies were issued". It also noted that the signatures on the proposal forms were forged and that the other insurers had refunded the premium treating the policies as mis-sale. Outcome: the complainant is entitled to a refund of Rs 1,12,995.
- Source: `references/claims/sources/B/excerpt-AHD-L-013-1617-0400-0403.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` pp. 30-31 (the compendium also prints the same award at pp. 39-40); https://www.cioins.co.in/LIC/miscellanious/Miscellaneous%20-%20Life26.pdf | retrieved 2026-11-10
- Quote:
  - (p. 30) "Complaint Ref No. AHD-L-013-1617-0400,401,402 & 403 Date of Award:23.09.2016"
  - (p. 30) "He was lured with one time investment with return of fund after one year, life insurance cover for his whole life and cash back on withdrawal of the fund."
  - (p. 30) "the policies were sourced through M/s Safeway Insurance Brokers Pvt. Ltd, Delhi, over mobile phone."
  - (p. 30) "The Respondent had submitted the copy of the verification call and not the voice copy of the solicitation stage/lead along with the SCN."
  - (p. 31) "PLVC recordings stated that the fund transfer had taken place, whereas the Complainant had sent a cheque for Rs. 98,000/- in the year 2013 out of which 3 policies were issued."
  - (p. 31) "In view of the facts and circumstances, the complainant is entitled for a refund amount of Rs.1,12,995/-."
  - (p. 107; acronym; MUM-L-032-1718-0504, Life 27 compendium) "directive of the Forum to play the Pre Log -In Voice Recordings(PLVC), the representative of the Respondent could not do so"
- Notes: The recording sentence matches the design. Things the design leaves out: the same award found the proposal-form signatures forged ("it was noted that the signatures were forged"), so this is a case of the recording conflicting with the payment record, plus a forgery finding, not a pure comprehension failure. "PLVC" is not expanded in this award; the Mumbai office's 2017 award MUM-L-032-1718-0504 expands it as "Pre Log -In Voice Recordings(PLVC)" and other awards use PIVC and PLVC for the same step. The refund (Rs 1,12,995) is larger than the cheque (Rs 98,000 for 3 policies); the award does not explain the difference. This case is a strong template for a scenario where the call script states a fact (payment mode) that the transaction record contradicts.

## New cases

Patterns: P1 = a recorded verification call (PIVC, PLVC, welcome call) existed and the customer still won; P2 = insurance sold with or out of a loan, or described as an FD, a security deposit, a one-time payment or a loan condition, or premium taken from the loan without clear consent; C = counter-example (insurer won). Every entry is `verified`: the award text is saved and quoted. Amounts are as stated in the award.

### B-N1 BNG-L-001-1617-0496 and 0497: PIVC recordings produced, partial refund
- Case / forum: Insurance Ombudsman, Bengaluru; award date 10.01.2017; respondent Aegon Life Insurance Company Limited.
- Pattern: P1
- Status: verified
- Facts: The complainant bought two policies through M/s SMC Insurance Broker, Bangalore, "on the pretext of securing the accumulated bonus amount on his earlier held policies of LIC of India". The insurer said he confirmed the details in the PIVC call and did not use the free-look option.
- Source: `references/claims/sources/B/excerpt-BNG-L-001-1617-0496-0497.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` pp. 59-60 | retrieved 2026-11-10
- Quote:
  - (p. 59) "He confirmed the details of policy an d proposal in the PVIC call."
  - (p. 60) "However, they failed to produce all call recordings as per the IRDA Guidelines on Distance Marketing except PIVC recordings."
  - (p. 60) "offered to refund the premium of ₹.99,999/- under one policy and requested for continuation of the other policy"
- Outcome: Mis-sale allowed; amicable settlement: Rs 99,999 refunded under one policy, the other (on the life of the complainant's daughter, Rs 25,000 a year) continues.
- Notes: A clean statement that the insurer had the PIVC recordings but not the calls "starting with the lead generation". The sibling award BNG-L-008-1617-0496 to 498 (Bharti Axa, same complainant, 21.01.2017, `excerpt-BNG-L-008-1617-0496-0498.txt`, pp. 66-67) says "During PIVC call, the Complainant had confirmed the terms and conditions of the policy", cites the "IRDA Guidelines on Distance Marketing (of Insurance Products dated 05.04.2011)" and orders a full refund under all three policies.

### B-N2 PUN-L-036-1617-0228: PIVC clear on terms, benefit never explained
- Case / forum: Insurance Ombudsman, Pune; Award no. IO/PUN/A/LI/0113/2016-2017, 27 July 2016; respondent Reliance Nippon Life Insurance Co. Ltd.
- Pattern: P1
- Status: verified
- Facts: The complainant was told she would pay Rs 99,999 a year for five years and get Rs 1,54,160 a year as money back from year 5 to 10; she was later told only Rs 6,25,000 would be payable after 5 years. The insurer said the terms were explained in the pre-verification call and she raised no concern.
- Source: `references/claims/sources/B/excerpt-PUN-L-036-1617-0228.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` pp. 477-478 | retrieved 2026-11-10
- Quote:
  - (p. 477) "During the pre - verification call the terms and conditions of the policy were explained, but she did not raise any concerns."
  - (p. 477) "The PIVC recording is clear about the terms and conditions of the policy but the maturity benefit is not explained."
  - (p. 477) "The Respondent could have called for explanation and gracefully refunded the premium to the complainant."
  - (p. 477) "The Respondent is directed to refund the premium by cancelling the policy"
- Outcome: Allowed: refund of the premium by cancelling the policy (relief sought Rs 99,999; the award does not print the refunded sum).
- Notes: The best single quote for the design's thesis: a recorded call covered the terms but not the one number the customer cared about, and the customer still won. It also shows a call can be "clear" and still miss the benefit.

### B-N3 PUN-L-017-1617-0684: verification call focused on processing; "security deposit" pretext
- Case / forum: Insurance Ombudsman, Pune; Award no. IO/PUN/A/LI/0302/2016-2017, 31 March 2017; respondent Future Generali Life Insurance Co. Ltd.
- Pattern: P1 and P2
- Status: verified
- Facts: Fraudsters posing as IRDAI officials sold a pension scheme, then said a bonus of Rs 12 lakh sat in an RBI account and the complainant should invest 30% of it as a "security deposit". Result: 29 policies from 7 insurers in 3 years.
- Source: `references/claims/sources/B/excerpt-PUN-L-017-1617-0684.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` p. 515 | retrieved 2026-11-10
- Quote:
  - (p. 515) "he was to invest 30% of the bonus in security deposit."
  - (p. 515) "Thus he was sold 29 insurance policies from 7 different insurers within a span of 3 years."
  - (p. 515) "The verification call recording showed the main focus of the tele -caller was on processing the application rather than procuring genuine business and enlightening the complainant about false allurements."
  - (p. 515) "The respondent is directed to refund the premium by cancelling the policies to the complainant"
- Outcome: Allowed: refund by cancelling the policies; the policy of the complainant's wife converted to a single-premium policy.
- Notes: Here the Forum listened to the verification call and criticised its content: the tele-caller ran through the application and never tested what the customer believed. That is the exact gap a teach-back question fills. Premium figures are not given in the award.

### B-N4 PUN-L-036-1617-0630 and 0631: an explicit "no loan" call, partial relief anyway
- Case / forum: Insurance Ombudsman, Pune; Award nos. IO/PUN/A/LI/0270 and 0271/2016-2017, 28 February 2017; respondent Reliance Nippon Life Insurance Co. Ltd.
- Pattern: P1 (partial) and loan-bait
- Status: verified
- Facts: The complainant was lured to buy four policies "with false assurance of loan of ₹ 4 lakhs" and waited six months. The insurer produced the verification call, in which the telecaller told her no loan, gift or bonus came with the policy and she confirmed ECS for renewal premiums.
- Source: `references/claims/sources/B/excerpt-PUN-L-036-1617-0630-0631.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` pp. 505-506 | retrieved 2026-11-10
- Quote:
  - (p. 505) "The complainant was lured to invest in 4 insurance policies with false assurance of loan of ₹ 4 lakhs.The complainant received 4 policy documents and waited for 6 months for the loan."
  - (p. 505-506) "telecaller was very specific in the verification call about no loan, gift, bonus will be payable under the policy and that the complainant should go through the terms and conditions of the policy carefully."
  - (p. 506) "The respondent and the complainant both are not fault free."
  - (p. 506) "The respondent is directed to convert the policies into one single premium policy with immediate effect on receipt of all requirements."
- Outcome: Complaint partly allowed: policies converted into one single-premium policy; the complainant's demand for a refund was refused.
- Notes: Shows the limits of the thesis. A very explicit verification call did not protect the insurer completely, but it did stop the full refund. A good "near-miss" scenario: the call was clear, the customer confirmed, and the outcome was still a compromise.

### B-N5 AHD-L-001-1617-0439: "followed the advice of the broker" in the verification call
- Case / forum: Insurance Ombudsman, Ahmedabad; award date 26.10.2016; respondent Aegon Religare Life Insurance Company Ltd.
- Pattern: P1 (coached yes)
- Status: verified
- Facts: A Mumbai broker promised "high returns with special bonus and profit of the company"; the complainant made a single-time investment and received a policy with an 8-year premium-paying term. He says he accepted the policy in the verification call on the broker's advice.
- Source: `references/claims/sources/B/excerpt-AHD-L-001-1617-0439.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` pp. 4-5 | retrieved 2026-11-10
- Quote:
  - (p. 4) "The Complainant had stated that he had followed the advice of the broker to accept the policy during the verification call (PIVC/PLVC)."
  - (p. 4) "With the non -submission of the broker’s voice copy (on the canvassing of the policy) it became evident that the policy had been mis -sold with false benefits."
  - (p. 5) "The Respondent is hereby directed to cancel the impugned policy"
- Outcome: Allowed: policy cancelled and the premium refunded (amount not printed).
- Notes: Companion to B4. The coaching is the complainant's statement; the Forum accepted it because the broker's call recording was not produced.

### B-N6 CHD-L-019-1718-1436: policy sold "as a security" for a Rs 25 lakh loan; "responded as was guided"
- Case / forum: Insurance Ombudsman, Chandigarh; award dated 16 April 2019; respondent HDFC Standard Life Insurance Co. Ltd. (complaint registered 06.03.2018).
- Pattern: P1 and P2 (loan pretext)
- Status: verified
- Facts: The complainant says the policy was sold "as a security to obtain a loan of Rs. 25 lakhs" that never came. Premium Rs 99,000 for 10 years. The insurer said a verification call was made.
- Source: `references/claims/sources/B/excerpt-CHD-L-019-1718-1436.txt`; `references/claims/sources/B/cioins-AwardsMonthwise-April2019-Mis-Selling_April_2019.pdf` pp. 103-104; https://www.cioins.co.in/AwardsMonthwise/April2019/Mis-Selling_April_2019.pdf (via web.archive.org/web/20240526210336id_/) | retrieved 2026-11-10
- Quote:
  - (p. 104) "he was sold a policy as a security to obtain a loan of Rs. 25 lakhs."
  - (p. 104) "for a premium amount of Rs. 99,000/= to be paid for 10 years."
  - (p. 104) "Although, a verification call was made to the complainant but the compla inant had been getting many calls from representatives of the Insurance Company and it is difficult for him to judge that the particular call was from the Insurance Company and not from any of its representatives, hence he responded as was guided."
  - (p. 104) "refund the premiums collected there-in without any interest or deduction of any charges."
- Outcome: Allowed: policy cancelled from inception and premiums refunded without interest or deduction.
- Notes: The Ombudsman's own reason for discounting the call: the customer could not tell whose call it was and answered as guided. Sourced from the April 2019 mis-selling compendium, not the 2016-17 ones.

### B-N7 KOL-L-013-1718-1552: welcome call raised no issue, full refund on suitability
- Case / forum: Insurance Ombudsman, Kolkata; Award no. IO/KOL/A/LI/0039/2019-2020, dated 7 May 2019; respondent DHFL Pramerica Life Insurance Co. Ltd.
- Pattern: P1 (call not decisive)
- Status: verified
- Facts: Three policies bought on the life of the complainant's daughter, premiums totalling Rs 3,05,000 (the award says Rs 3.05 lakh "per year" in one place and treats Rs 3,05,000 as the total to refund), on assurances of high returns. He alleged the PIVC was done "under Agent’s pressure and tutoring". The insurer pointed to the welcome call.
- Source: `references/claims/sources/B/excerpt-KOL-L-013-1718-1552.txt`; `references/claims/sources/B/cioins-AwardsMonthwise-April2019-Mis-Selling_April_2019.pdf` pp. 282-284; https://www.cioins.co.in/AwardsMonthwise/April2019/Mis-Selling_April_2019.pdf (via web.archive.org/web/20240526210336id_/) | retrieved 2026-11-10
- Quote:
  - (p. 283) "ii) PIVC was done under Agent’s pressure and tutoring resulting in providing false information to the company during verification call."
  - (p. 283) "iii. No issues were raised during the welcome call."
  - (p. 284) "But this income is totally inadequate to support premium payments of Rs 3.05 lakhs per year."
  - (p. 284) "the insurer is directed to cancel all the three polices and refund the entire premium amount of Rs 3,05,000/- to the complainant,"
- Outcome: Allowed: all three policies cancelled and Rs 3,05,000 refunded.
- Notes: The Ombudsman did not rule on the welcome call. The refund rests on financial underwriting and need-based selling. Cite it as "a clean welcome call did not save the insurer", not as "the Ombudsman rejected the call".

### B-N8 PUN-L-008-1617-005: the insurer's "verification call" was a different call
- Case / forum: Insurance Ombudsman, Pune; Award no. IO/PUN/A/LI/0016/2016-2017, 19 May 2016; respondent Bharti Axa Life Insurance Co. Ltd.
- Pattern: P1 (call disproved) and loan-bait
- Status: verified
- Facts: The complainant was told a loan against his policy would come after six months and invested Rs 48,430 in two policies. He said he never got a verification call and the signatures were forged. The insurer said its PLVC recording showed no concerns raised.
- Source: `references/claims/sources/B/excerpt-PUN-L-008-1617-005.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` p. 455 | retrieved 2026-11-10
- Quote:
  - (p. 455) "The complainant was assured loan against his policy after six months of taking the pol icy and invested Rs.48,430/- with the respondent in two policies."
  - (p. 455) "After the hearing the respondent submitted a call recording but it was call by the complainant to the customer care of the respondent."
  - (p. 455) "thus it is proved that the allegation by the complainant about verification call is true."
  - (p. 455) "refund the total premiums with interest @ 9% p.a. from the date of first request for cancellation i.e.30/11/2015 till the date of refund."
- Outcome: Allowed: both policies cancelled; full premiums refunded with 9% interest from 30/11/2015.
- Notes: A case about a verification call that was claimed but not real: the number the insurer called differed from the number on the proposal form. Relevant to the evidence-log design (who was actually on the call).

### B-N9 BHP-L-013-1617-0436: "deposit Rs 1.00 lac as an Fixed Deposit to get the housing loan"
- Case / forum: Insurance Ombudsman, Bhopal; Order No. IO/BHP/A/LI/0159/2016-2017, 21 March 2017; respondent DHFL Pramerica Life Insurance Co. Ltd.
- Pattern: P2 (FD; loan pretext)
- Status: verified
- Facts: The complainant applied for a housing loan from a housing-finance company, paid Rs 1,100 as processing fee, and was told to deposit Rs 1.00 lakh as a fixed deposit to get the loan. A policy was issued instead.
- Source: `references/claims/sources/B/excerpt-BHP-L-013-1617-0436.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` pp. 137-138 | retrieved 2026-11-10
- Quote:
  - (p. 137-138) "had applied for housing loan from Diwan housing Finance in the month of march and deposited Rs 1100/ - as processing fe es, then they ask to deposit Rs 1.00 lac as an Fixed Deposit to get the housing loan but instead of loan issued policy of DHFL Pramerica Life Ins. Co. Ltd."
  - (p. 138) "the Respondent Company was directed to convert the existing policy into a single premium policy from date of application dated 14.03.2016."
- Outcome: Allowed: policy converted to a single-premium policy from 14.03.2016. No refund.
- Notes: Lender-side script that describes insurance as a "fixed deposit" tied to loan sanction. A direct template for an "FD" mismatch scenario, with a different lender type (housing finance).

### B-N10 BHP-L-021-1617-0456: "single premium policy like FD for 5 years"
- Case / forum: Insurance Ombudsman, Bhopal; Order No. IO/BHP/A/LI/175/2016-2017, 21 March 2017; respondent ICICI Prudential Life Insurance Co. Ltd.
- Pattern: P2 (FD; one-time payment)
- Status: verified
- Facts: The complainant took a policy "on pretext of single premium policy like FD for 5 years" and received a regular-premium policy.
- Source: `references/claims/sources/B/excerpt-BHP-L-021-1617-0456.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` p. 147 | retrieved 2026-11-10
- Quote:
  - (p. 147) "on pretext of single premium policy like FD for 5 years."
  - (p. 147) "the Insurance Company issued a regular premium policy on the pretext of single premium policy"
  - (p. 147) "Respondent Company is directed to convert the policy into single premium policy."
- Outcome: Allowed: policy converted to a single-premium policy (the insurer agreed at the hearing).
- Notes: Not loan-linked, but the "FD" wording and the one-time-versus-regular-premium mismatch are the same as the design's hero scenario.

### B-N11 PUN-L-041-1617-0649: group policy with a housing loan, no certificate until the loan was repaid
- Case / forum: Insurance Ombudsman, Pune; Award no. IO/PUN/A/LI/0273/2016-2017, 28 February 2017; respondent SBI Life Insurance Co. Ltd.
- Pattern: P2 (insurance with a loan, no clear consent)
- Status: verified
- Facts: The complainant took a housing loan from SBI; SBI Life issued a group policy for the loan amount. He says it was issued without his consent and he got the policy terms only after repaying the loan, then asked for a refund for the unused period.
- Source: `references/claims/sources/B/excerpt-PUN-L-041-1617-0649.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` pp. 506-507 | retrieved 2026-11-10
- Quote:
  - (p. 507) "The complainant had availed housing loan from SBI and insurance policy for the loan amount was issued by SBI Life as a group policy."
  - (p. 507) "The respondent had not supplied the certificate of insurance to the complainant."
  - (p. 507) "The terms and conditions of the policy and the certificate of insurance were received by the complainant only after he repaid the loan."
  - (p. 507) "The respondent is directed to pay the difference in one time premium for the original term and for the term availed by the complainant to the complainant."
- Outcome: Allowed in part: the insurer must pay the difference between the one-time premium for the original term and for the term actually availed (the amount is not printed).
- Notes: The nearest 2016-17 award to "insurance bundled with a housing loan, with no clear consent". No verification call is discussed.

### B-N12 PUN-L-019-1617-0694: asked about FD rates at the bank, sold a single-premium plan
- Case / forum: Insurance Ombudsman, Pune; Award no. IO/PUN/A/LI/0283/2016-2017, 24 March 2017; respondent HDFC Std Life Insurance Co. Ltd.
- Pattern: P2 (FD enquiry at a bank branch)
- Status: verified
- Facts: The complainant visited HDFC Bank to ask about fixed-deposit rates and was offered a single-premium unit-linked plan with monthly pension after one year. Months later the bank told him he had to pay premiums for four more years.
- Source: `references/claims/sources/B/excerpt-PUN-L-019-1617-0694.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` p. 509 | retrieved 2026-11-10
- Quote:
  - (p. 509) "The complainant visited HDFC bank where he had savings account to enquire about rate of interest on fixed deposit."
  - (p. 509) "He was suggested single premium unit linked insurance plan and informed that he will receive monthly pension on completion of one year of the policy term."
  - (p. 509) "A senior citizen cannot be expected to pay premium of ₹ 4.5 Lakh for 10 years out of his business income."
  - (p. 509) "The respondent is directed to cancel the policy and convert the premium into one sing le premium immediate pension policy ."
- Outcome: Allowed in part: policy cancelled and the premium converted into a single-premium immediate-pension policy.
- Notes: A bank-channel sale that started as a deposit enquiry. Premium Rs 4.5 lakh is in the award. No loan is involved.

### B-N13 PUN-L-036-1617-0515: insurance sold on a "pretext of security deposit"
- Case / forum: Insurance Ombudsman, Pune; Award no. IO/PUN/A/LI/0223/2016-2017, 30 December 2016; respondent Reliance Nippon Life Insurance co ltd.
- Pattern: P2 (security deposit)
- Status: verified
- Facts: The complainant was lured into four policies from two insurers with false assurance of bonus and returns. The Forum says he was canvassed "not for insurance policy but investment o n pretext of security deposit".
- Source: `references/claims/sources/B/excerpt-PUN-L-036-1617-0515.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` p. 497 | retrieved 2026-11-10
- Quote:
  - (p. 497) "The respondent did not submit call recordings."
  - (p. 497) "The complainant was canvassed not for insurance policy but investment o n pretext of security deposit ."
  - (p. 497) "The very essential feature of a valid contract i.e. Consensus ad idem is absent in the contract."
  - (p. 497) "The respondent is directed to refund the premium after due recovery of mortality charges, policy preparation charges, stamp dut y and service tax by cancelling the policies to the complainant immediately on receipt of all requirements."
- Outcome: Allowed: premium refunded after deducting mortality, preparation, stamp duty and service tax charges.
- Notes: The "consensus ad idem is absent" reasoning is a clean legal frame for the design: no meeting of minds on what was bought.

### B-N14 PUN-L-013-1617-0583: counter-example, an explicit "no loan" call protected the insurer
- Case / forum: Insurance Ombudsman, Pune; Award no. IO/PUN/A/LI/0256/2016-2017, 31 January 2017; respondent DHFL Pramerica Life Insurance co ltd.
- Pattern: C (insurer won; P1)
- Status: verified
- Facts: The complainant was "conned to invest in an insurance policy wit h false assurance of loan of ₹ 20 Lakhs".
- Source: `references/claims/sources/B/excerpt-PUN-L-013-1617-0583.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` p. 504 (and pp. 455-456 and 507 for the two other awards quoted) | retrieved 2026-11-10
- Quote:
  - (p. 504) "The respondent submitted verification call recording and the tele -caller very clearly stated that no loan, bonus, gift etc. is attached or offered with this policy to which the complainant had agreed."
  - (p. 504) "The complaint is devoid of merit and is dismissed."
  - (p. 507; PUN-L-019-1617-0641, HDFC Std Life, dismissed) "The respondent submitted call recordings done at the time of issuance of the policy in which the telecaller very clearly stated that no loan, bonus, gift etc. is attached or offered with this policy to which the complainant had agreed."
  - (p. 456; PUN-L-006-1617-015, Bajaj Allianz, dismissed) "In the PIVC recording ,the complainant had asked a specific question ‘ is there any benefit other than the benefits explained by you ?’ and the Tele -caller very clearly told him that no benefit other than the benefits already explained as per the terms and conditions of the policy is available."
- Outcome: Dismissed: the complainant lost.
- Notes: Keep as a counter-example: a recorded call in which the caller states the negatives explicitly and the customer agrees can win for the insurer. The first complaint also came after one year. The dismissal is not a finding that the sale was compliant: the complainant alleged a false promise of a Rs 20 lakh loan, so a teach-back call to this customer should still flag. Two more 2016-17 Pune awards dismissed complaints on the same basis (quoted above with their numbers). The design should not say recorded confirmations always lose.

### B-N15 NOI-L-036-1819-0337: counter-example, PIVC played at the hearing
- Case / forum: Insurance Ombudsman, Noida (Western U.P. and Uttarakhand); dated 24.4.2019; respondent Reliance Nippon Life Insurance Company.
- Pattern: C (insurer won; P1)
- Status: verified
- Facts: A Child Education Plan sold through an agent; the complainant said he was lured on the ground that the amount would be refunded, and complained after 19 months.
- Source: `references/claims/sources/B/excerpt-NOI-L-036-1819-0337.txt`; `references/claims/sources/B/cioins-AwardsMonthwise-April2019-Mis-Selling_April_2019.pdf` pp. 312-313; https://www.cioins.co.in/AwardsMonthwise/April2019/Mis-Selling_April_2019.pdf (via web.archive.org/web/20240526210336id_/) | retrieved 2026-11-10
- Quote:
  - (p. 312) "Award in favour of Insurance Company"
  - (p. 313) "The PIVC recording was also heard at the time of hearing wherein the complainant confirmed the details as filled in proposal form."
  - (p. 313) "On going through the facts and circumstances of the claim, it can not be held a case of mis -selling."
- Outcome: Award in favour of the insurer; no relief.
- Notes: The Ombudsman heard the PIVC and treated it as confirmation. A plain recorded confirmation won here, which cuts against the design's thesis and should be stated honestly. Late complaint (19 months) and the complainant's own statement that he had "never read the terms and conditions" also counted.

### B-N16 JPR-L-041-1920-0004: counter-example, SBI Life Rin Raksha with a housing loan
- Case / forum: Insurance Ombudsman, Jaipur; dated 26.03.2019 (hearing 25.04.2019 shown in the header); respondent SBI Life Insurance Co. Ltd.
- Pattern: C (insurer won; P2)
- Status: verified
- Facts: The complainant took a housing loan from SBBJ (now SBI) in 2013 and was issued a Rin Raksha policy; he said it was issued without informing him and the proposal details were wrong.
- Source: `references/claims/sources/B/excerpt-JPR-L-041-1920-0004.txt`; `references/claims/sources/B/cioins-AwardsMonthwise-April2019-Mis-Selling_April_2019.pdf` pp. 18-19; https://www.cioins.co.in/AwardsMonthwise/April2019/Mis-Selling_April_2019.pdf (via web.archive.org/web/20240526210336id_/) | retrieved 2026-11-10
- Quote:
  - (p. 19) "The subject policy was reported to have issued without informing the complainant."
  - (p. 19) "The Insurance Company submitted that a housing loan was granted to the complainant for Rs 8 Lakhs and to protect the loan , a policy was issued on 10.01.2014 for a premium paying term of 5 years."
  - (p. 19) "Accordingly the complaint is dismissed."
- Outcome: Dismissed: all five premiums had been paid and the complaint came years after the free-look period.
- Notes: Shows the weak point of claims that a policy was issued without telling the borrower: if the borrower paid for the full term, the Ombudsman did not interfere. A callback within 30 days (rule 85Y) would have caught it while a refund was still possible.

### B-N17 PUN-L-009-1617-0009: "instructed to agree to all the terms and conditions during the verification calls"
- Case / forum: Insurance Ombudsman, Pune; Award no. IO/PUN/A/LI/0015/2016-2017, 18 May 2016; respondent Birla Sun Life Insurance Co. Ltd.
- Pattern: P1 (coached yes; partial)
- Status: verified
- Facts: The complainant says he was lured with a plan on which he would have to pay only three premiums, and was instructed to agree to the terms in the verification calls. The insurer said its PLVC recording showed no concerns raised.
- Source: `references/claims/sources/B/excerpt-PUN-L-009-1617-0009.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life26.pdf` pp. 454-455 | retrieved 2026-11-10
- Quote:
  - (p. 454) "He was further instructed to agree to all the terms and conditions during the verification calls."
  - (p. 454) "PLVC recording with the Respondent also showed that the complainant did not raise any concerns."
  - (p. 454) "and refund Rs.29,100/- to the complainant"
- Outcome: Partly allowed: relief only on the third policy (the one sourced through a tied agent of the insurer): cancel and refund Rs 29,100. No intervention on the other two policies.
- Notes: A mixed result inside one award. The Forum accepted the coaching story only for the policy where the insurer's own tied agent was involved.

### B-N18 BHU-L-008-1516-0414: "only PIVC which was recorded after the lead generation, collection of proposal papers and deposit amount"
- Case / forum: Insurance Ombudsman, Bhubaneswar; award dated 11 May 2016; respondent Bharti Axa Life Insurance Co. Ltd. (complaint registered in FY 2015-16, hence 1516).
- Pattern: P1 (the doctrine; the PIVC itself was not produced)
- Status: verified
- Facts: A broker solicited by telephone a one-time investment with "minimum 10% annual tax free return"; the complainant paid Rs 2,00,000 by cheques and received two policy bonds, one on his son, who never signed anything.
- Source: `references/claims/sources/B/excerpt-BHU-L-008-1516-0414.txt`; `references/claims/sources/B/cioins-LIC-miscellanious-Miscellaneous-Life25.pdf` pp. 132-133 (this award is only in the Life 25 compendium) | retrieved 2026-11-10
- Quote:
  - (p. 132) "But in the present case it appears from the SCN that the OP has no such record but only PIVC which was recorded after the lead generation, collection of proposal papers and deposit amount."
  - (p. 132) "Neither PIVC nor any other electronic record has been produced from the side of the insurer."
  - (p. 132) "In the absence of the entire electronic record as per the Distance Marketing guidelines, it cannot be said that the sale of policies is fair and reasonable."
- Outcome: Allowed: Rs 2,00,000 awarded to be paid by the insurer to the complainant; no interest.
- Notes: The clearest statement of the doctrine behind many of these awards. Note that here even the PIVC was not produced at the hearing, so cite it for the rule ("the entire process beginning with lead generation"), not as a "recorded yes" case. Another Bhubaneswar award in the same compendium, BHU-L-017-1516-0419 (Future Generali, p. 122), repeats the reasoning and awards Rs 80,499 / Rs 49,000.

## Counts by status

- Cited cases B1 to B8 plus B1b (9 claims): verified 6 (B1, B2, B3, B5, B7, B8, each with corrections), wrong 1 (B6), unverifiable 2 (B1b, B4), secondary-only 0.
- New cases B-N1 to B-N18 (18 entries): all `verified`. B-N1 to B-N13, B-N17 and B-N18 are customer wins or partial wins (15), B-N14, B-N15 and B-N16 are insurer wins kept as counter-examples (3).

## Could not retrieve

- e-Jagriti (https://e-jagriti.gov.in/) and confonet (https://confonet.nic.in/): connection failed (curl exit 7, HTTP code 000) from this machine on 2026-11-10. The Baramulla order was therefore taken from the copy attached to the LiveLaw article (PDF 200 OK, two scanned pages).
- Full Ombudsman award files: not public. Only the CIO compendium synopses are.
- CIO Annual Report 2016-17 (https://www.cioins.co.in/annualreports/Annual_Report_2016-2017.pdf, 200 OK, 67 pages): a scanned PDF with no text layer; searched only by file-level extraction (empty), not read page by page. It was not searched for the case numbers, since the compendiums gave every cited case.
- CIO awards pages for 2018 onward (`/AwardsMonthwise/<month>/...Mis-selling...pdf`): the live site now returns 404 for them. Via web.archive.org only one file (April 2019) downloaded. The other roughly 50 requests failed (a burst of parallel requests, then single retries that returned HTTP 429, the Wayback rate limit) and were stopped rather than retried further. Later months are not searched, so the new cases from 2018-2023 are limited to April 2019. 
- What was searched, and how far. The Life compendiums for 2016-18 were downloaded from the CIO site (live, 200 OK) and text-extracted: Miscellaneous (Life25, Life26, Life27, Life28), Death Claim (Life25 to Life28), Maturity Claim (Life25 to Life27) and Survival Benefit (Life25 to Life27). All six cited case numbers and the DHFL award were found by exact string search in Life26 (the Life25 file also holds the two Ahmedabad cases). Each file was then scanned by keyword (PIVC, pre-issuance, pre-login, welcome call, verification call, call or voice recording, fixed deposit, FD, security deposit, overdraft, mandatory, one-time, single premium, Loan Protect, Credit Protect, gold, home or housing loan, loan amount, sanction) and I read the blocks that looked relevant. That is a keyword search with selective reading, not a read of every award, so the new-case list is a sample and not a census. Only Life25, Life26, Life27 and Death Claim Life26 are saved under `sources/B/`, because every case used comes from them or from the April 2019 file; the other extractions were used for searching only.
- The CIO "Track complaint" page needs a mobile number and OTP, so it cannot be used for retrieval. The 2016-17 page on the CIO site that maps periods to compendium files is saved as `cioins-awards-archive-page-wayback-20220930.html`; the Wayback CDX listing of the site's PDFs is saved as `wayback-cdx-cioins-co-in-status200.txt`.
- IRDAI and policyholder.gov.in award pages: `https://www.policyholder.gov.in/ombudsman` did not connect (HTTP 000). The site root `https://policyholder.gov.in/` returned 200 but was not searched for award synopses.
- The IRDAI Distance Marketing guidelines dated 05.04.2011, which several awards cite, were not retrieved here (group A or D may cover them).

## Product implications

1. **About a third of the customer-relief awards turn on a missing sales-stage recording, not on the yes.** A tally of the 22 rows with customer relief finds this reasoning in 7 (8 with B-N3). Bengaluru, Bhubaneswar, Pune and Ahmedabad Forums gave the complainant the benefit of doubt because the insurer could not produce the recording "starting with the lead generation" required by IRDAI's Distance Marketing guidelines of 05.04.2011 (B4, B-N1, B-N8, B-N18, and BNG-L-008-1617-0496 to 498 in `excerpt-BNG-L-008-1617-0496-0498.txt`). Samajh's evidence log (who was called, which number, the full transcript, a hash) answers that failure directly. Say so in the pitch; do not say the awards prove a "yes" is meaningless.
2. **The thesis is supported by a few awards, not "several".** Where the recording existed and was examined, the cases are B2 (submitted PIVC; conversion), B8 (verification-call copy; refund, forged signatures), B-N1 (PIVC recordings produced; partial refund), B-N2 (PIVC clear on terms but not the benefit; refund) and B-N3 (verification call criticised for focusing on processing; refund). B3 is the insurer's statement only; B4 is the opposite (no recording produced). Rewrite DESIGN.md section 1 to name B2, B-N2 and B-N3 as the lead examples.
3. **Counter-examples exist and the pitch must admit them.** An explicit "no loan, no bonus" call won for the insurer in B-N14, and a PIVC the Ombudsman heard at the hearing won in B-N15. These are dismissals on the evidence or on delay. They are not findings that the sale was compliant, and in each the complainant alleged a false promise. Do not use them as "must not flag" gold. Write compliant scenarios synthetically.
4. **Fix three factual details before the video.** The Rs 5 lakh and Rs 4.48 lakh are not in BHP-L-021-1617-0529 (B1b). The Baramulla Rs 2 lakh was debited "from the account of the complainant", not stated to be from the cash-credit loan, and the order was ex parte (B7). AHD-L-021-1617-0367 is a death-claim repudiation the insurer won (B6). Suggested replacements for the "other gold templates": B5 (bundling, with the overdraft precondition), B-N9 (FD for a housing loan), B-N10 (FD-like single premium), B-N11 (group policy with a housing loan).
5. **Relief varied.** Of the 22 rows with customer relief, 14 are refunds (full or partial), 7 are conversions into a single-premium policy and 1 is other. Conversions: B2, B3, B5, B-N4, B-N9, B-N10 and B-N12. Refunds include B1, B4, B7, B8, B-N2, B-N3, B-N6, B-N7, B-N8 and B-N13. Scenario gold verdicts should state the real remedy.
6. **Coached answers are a recurring fact pattern.** "answer everything in positive" (B4), "followed the advice of the broker" (B-N5), "responded as was guided" (B-N6), "instructed to agree to all the terms and conditions during the verification calls" (B-N17, partial relief). In three of the four this is the complainant's account; only in B-N6 does the Ombudsman adopt it in the observations. A callback that asks an open question in the customer's own words is the countermeasure the design proposes.
7. **Do not quote the SBI line in B2.** The sentence "no person of ordinary prudence would any way tend to believe that officials of the State Bank of India could in fact mislead" is in an award that went for the complainant. It reads badly out of context.
