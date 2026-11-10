# W3 claims verification: final report

Date: 2026-11-10. Goal: trace every regulatory and factual claim Samajh will show to BFSI judges to a saved primary source, or strike it. Research only. No product code was written.

## 1. What was built

All paths are under `references/claims/`.

| Path | Content |
|---|---|
| `claims-ledger.md` | Part 1: a verdict for each statement in `DESIGN.md` sections 11 and 12 (S1 to S30), plus new allowed and banned statements. Part 2: one row per claim for groups A to E, 165 rows, generated from the findings files. |
| `design-corrections.md` | 18 edits to `DESIGN.md` (old text to new text), ordered by importance, then product implications, interview questions and open points. |
| `findings-A.md` to `findings-E.md` | The research notes behind the ledger, with full quotes. |
| `sources/A` to `sources/E` | 457 saved files (about 180 MB), each group with an `INDEX.md` giving URL, retrieval date and SHA-256. |
| `check_quotes.py`, `build_ledger.py` | Two small scripts so the check can be rerun offline. |
| `README.md` | Protocol, status definitions, and what to decide before the repository goes public. |

## 2. Evidence

```
$ python3 -I references/claims/check_quotes.py
group A: 61 quoted spans checked, 0 not found in saved sources
group B: 109 quoted spans checked, 0 not found in saved sources
group C: 96 quoted spans checked, 0 not found in saved sources
group D: 46 quoted spans checked, 0 not found in saved sources
group E: 128 quoted spans checked, 0 not found in saved sources

$ python3 -I references/claims/build_ledger.py      # run twice, same output
| | **All groups** | secondary-only 7 | unverifiable 20 | verified 130 | wrong 8 | Total 165 |

$ uv run ruff check references/claims/*.py
All checks passed!
```

Other checks, run inline:
- 34 source phrases quoted in `design-corrections.md` were searched in the saved sources. All 34 were found.
- 22 "Old (line N)" quotes in `design-corrections.md` were compared with `DESIGN.md`. All match their stated lines.
- The feedback paragraph number was read from each of the seven other entity pages: 85Y, 42Y, 17Y, 136Y, 65Y, 79Y, 32Y.
- The reviewer re-fetched five URLs. The three RBI direction bodies were identical to the saved copies, and the TRAI direction and the Ombudsman compendium matched by SHA-256.
- The reviewer searched the findings, ledger and corrections files for 110 name tokens taken from the award texts. No complainant name was found.

Limit of `check_quotes.py`: it checks that a quote exists in the group's saved text. It does not check that the quote supports the claim. That was the reviewer's job.

## 3. Claims verified, and claims not verified

**Verified against saved primary text**
- The 85Y quote in `DESIGN.md` is identical to RBI's text (702 characters).
- RBI/2026-27/115 para 85Y (commercial banks) and RBI/2026-27/123 para 101Y (NBFCs). Issued 15 June 2026. In effect from 1 January 2027. HFCs follow NBFC paragraphs 101A to 101ZA through para 157A (RBI/2026-27/124).
- The verbatim text of 85G, 85V, 85W, 85X, 85Y, 85Z, 85N and 4(20A), and the NBFC equivalents.
- All six cited Ombudsman case numbers, the Baramulla order, and 18 further awards.
- IRDAI's PIVC circular (12 May 2020, "encouraged") and its supersession in 2024. The Canara HSBC Life order of 10 September 2026.
- TRAI's 1600-series direction of 19 November 2025, the TCCCPR amendments of 2025 and 2026, and the DPDP commencement dates (13 November 2026 and 13 May 2027).

**Wrong in the design (8)**
- The title of the RBI instrument (A1).
- "every RBI-regulated lender" (A6).
- The 85V check, which would flag a required risk mitigant even where the customer had a choice of provider (A16).
- AHD-L-021-1617-0367 as a mis-selling template. It is a death-claim dispute the insurer won (B6).
- "no vendor marketing an 85Y understanding callback" as worded (C2.1), and "nobody is pushing it" (D2.2).
- "the only data is from Nigeria" (D1.2).
- The 180 versus 240 credit figures in the two design documents (D5.8).

**Unverifiable (20)**, including:
- The "asked for ₹5 lakh, received ₹4.48 lakh" figures. They are not in the award (B1b).
- That a recorded "yes" existed in AHD-L-001-1617-0203 (B4).
- That an SMS survey satisfies 85Y (A13).
- Where TRAI places a feedback call (E1.5).
- Whether any law requires AI disclosure on a lender's call (E4.8).
- The pilot's cost and latency figures, which rest on an unsaved dashboard reading (D5.1, D5.2, D5.4).

**Secondary-only (7)**: vendor-market statements and survey-mode context in group D, and SEBI and IRDAI AI guidance (E4.6).

## 4. The reviewer's refutation attempt

One Fable reviewer at high effort, which did none of the research, tried to refute each `verified` mark offline against the saved sources.

**What survived.** The RBI citations (A2 to A5, A7, A9, A10), which it confirmed are the final directions and not the February draft. The quotes for 85V, 85Z and the other paragraphs. The facts of B1 to B8, with the Baramulla order read from the page images. The PIVC, TRAI, DPDP, FREE-AI and KFS quotes.

**What it refuted.** Twelve points, almost all in the first version of `design-corrections.md` and not in the quotes. All are now fixed.

| # | Error | Fix |
|---|---|---|
| R1 | The KFS check cited circular RBI/2024-25/18, which the 2025 consolidated Directions very likely repealed. | Cite para 348 of the Commercial Banks Directions (para 29 for NBFCs). |
| R2 | "85Z needs a customer complaint" was an inference. The refund sentence stands alone. | Say the duty arises where mis-selling "is established", and that the text names no decider. |
| R3 | The two insurer-won awards were misdescribed. In one, a plain recorded confirmation won. | Described as the awards read. |
| R4 | Insurer-won awards were proposed as "compliant" gold scenarios. They are dismissals on evidence or delay. | Compliant scenarios are to be written synthetically. |
| R5 | "Most ended in conversion" and "most wins turned on missing recordings" were false. The tally is 14 refunds, 7 conversions, and 7 of 22 on missing recordings. | Replaced with the tally. |
| R6 | The corrected 85V rule dropped the "not a risk mitigant" branch, and called credit-life "the standard risk mitigant" with no source. | Both branches restored. Marked as our reading. |
| R7 | Complainants' allegations were written as facts. B4 was over-read as "no recording at all". | Attributed. B4 is now `unverifiable`. |
| R8 | The automated-call notice already exists (2025). "No law requires" overstated a negative search. | Reworded. |
| R9 | The identity-check heading overstated RBI's advice, and the replacement left no second check. | Softened. A non-secret second check added. |
| R10 | Two quotes had lost limiting words (free-look "except ... less than a year"; 85R covers own products only). | Restored. |
| R11 | HFCs do not expressly import definition 6(9A). | Reworded. |
| R12 | Smaller wording errors and two wrong page numbers. | Fixed. |

**What I did not adopt, and why.** The reviewer said rows that quote a vendor's own page (C2.2 to C2.8, D2.2) and rows that rest on a mirror copy should be `secondary-only` under the strict definition. I kept the vendor rows as `verified (as to what the page says)`, because a vendor's page is first-hand evidence of what it markets. I kept the mirror rows as `verified` with the mirror named in the status. The ledger's convention 4 states that a strict reading makes these four rows `secondary-only`.

**What the reviewer did not check.** Ledger Part 2 as generated. The context of about 60 lower-stakes rows (listed in its report as quote-in-file only). The pilot arithmetic in D5. Whether RBI amended anything after 6 August 2026.

**The fixes were not re-reviewed.** The second version of `design-corrections.md` was checked by script only (quotes and old-text lines), not by a fresh reviewer.

## 5. Failures, gaps, and changes from the spec

- **RBI PDFs.** `rbidocs.rbi.org.in` serves a human-verification page to automated clients. Only the commercial-banks PDF was obtained, from web.archive.org. The other nine directions are saved as the full-text HTML pages RBI publishes on `rbi.org.in`. The verification page was not bypassed.
- **Not retrieved.** RBI's statement on feedback received (Annex I). The RBI Ombudsman 2024-25 report. The gazette dates of the TCCCPR Third and Fourth Amendments. e-Jagriti and confonet (no connection). Ombudsman award PDFs from 2018 onward, except April 2019.
- **Copies not hosted by the issuer.** The FREE-AI report (Medianama), the SPDI Rules 2011 (PRS India), IRDAI circular 274/11/2020 (TaxGuru) and the Baramulla order (LiveLaw).
- **New-case list is a sample.** The 18 extra awards came from keyword scans of the 2016-18 compendiums, not a full read.
- **Findings files.** The harness refused report-file writes from four of the five researchers. They returned the text, and I saved it after reading it.
- **Another worker's file.** The group D researcher read `.samajh/probe/log.jsonl` (W2's output) and saved a four-row 429 excerpt. I checked that the excerpt holds no key.
- **Scripts.** I added two small scripts under `references/claims/`. They are check tools, not product code.
- **Size and names.** `sources/` is about 180 MB. `sources/B/` contains award texts that name real complainants. The findings, ledger and corrections files name none. Decide before the repository goes public (see `README.md`).
- **Gnani API claims.** `ORCHESTRATION.md` describes W3 as covering Gnani-API claims too. My task listed groups A to E only, so those were not checked here.

## 6. Credits and spend

Gnani credits: 0. OpenRouter: 0. Six subagents used about 2.7 million tokens in total (five Sonnet researchers, one Fable reviewer).

## 7. What the next iteration should do

1. Apply `design-corrections.md` items 1, 7 and 12 to the rule engine now (W1): the 85V rule with `risk_mitigant` and `provider_choice_offered`, an evidence pack in place of a refund draft, and a consent record that does not clear 85G by itself.
2. Apply items 2, 6 and 16 before W4 freezes the gold set: drop AHD-L-021-1617-0367, stop using insurer-won awards as compliant gold, and record each award's real remedy.
3. Decide the identity check (item 5) before the call state machine is built.
4. Have a person read the four mirror-copy documents against the official copies, and get RBI's Annex I and the RBI Ombudsman 2024-25 report through a browser.
5. Recheck RBI's notifications for amendments before submission.
6. Verify the Gnani API claims in `DESIGN.md` sections 7 and 8 against `docs.gnani.ai`, which this package did not cover.
