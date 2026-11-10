# Identity on an outbound call: what the norm is (package P8, 2026-11-10)

## Findings

Evidence: `references/claims/findings-F.md`.

| Area | Finding | Ids |
|---|---|---|
| Regulators | No RBI, TRAI or IRDAI text we found says how to confirm who is on an outbound call. They do say: loan matters only with the borrower; service calls from the 1600 series; never-share lists name credentials. RBI's booklet says imposters "share a few customer details such as the customer’s name or date of birth". Take numbers from the official website; Sanchar Saathi checks a number. IRDAI's 2019 notice: verify a caller through the insurer's call centre. DPDP's breach definition includes "accidental disclosure"; its operative sections start 13 May 2027. | F1.1 to F1.5, F1.7, F1.8, F1.11, E5.4, E1.8, E1.10 |
| Lenders and insurers | None publishes its outbound identity data points, count or attempts. Nine publish never-ask lists. Axis, SBI Life, Kotak and LIC advise against giving a date of birth on a call (LIC: to unverified callers). Three banks say genuine calls come from 1600 numbers. | F2.1, F2.3 to F2.7 |
| Vendors | The visible convention is "verify before disclosing": a confirmed name, then at most one more item when one is named, most often date of birth (Exotel, Mobicule, Oration, Dapta, Skit), also last four digits, OTP, ZIP. Exotel: "name confirmation and last-four digits or date of birth". Edesy's and Retell's outbound samples confirm the name only. No page gives a retry limit. | F3.1 to F3.7 |
| Abroad (comparison only) | US rules bar debt talk with anyone but the consumer; UK and Australian texts require establishing who the person is first. None defines how. Australia (advisory) lets the caller name its organisation first only if that "would not have the effect of divulging that the debtor has a debt". | F3.9, F3.11, F3.12 |
| Knowledge questions | NIST SP 800-63A-4 (digital identity proofing, not a call): "SHALL NOT be used for identity verification". FFIEC: not solely. Acquaintances guessed 17% to 28% of secret-question answers (US webmail study, no birth data). A 2023 leak listing held name, phone, age, address and pincode together (seller's count unconfirmed). A blind guess at a birth year is about 2% to 5% (our arithmetic). | F4.1, F4.3, F4.5, F4.7 |
| Stronger measures | Not questions: a recognisable number; prior notice or an in-app call status; the customer hanging up and calling a number they already hold; an OTP typed into the lender's own channel, never spoken. | F4.9 to F4.12, F1.2 |

## What the norm is, and how firm

There is no single norm set by any Indian regulator or published by any Indian lender.

Firm (primary texts): the loan is discussed only with the borrower (E5.4); no credential is ever asked for (F1.3); the customer-side checks are the number series and a call the customer makes (E1.8, F4.10).

A soft convention (vendor marketing pages, mostly collections, several US-framed): confirm the name, then optionally one low-sensitivity item, usually date of birth.

Nothing found supports two items, a PIN-code question in India, or any attempt limit.

## Unverified

- No lender's real script or attempt rule; no RFP with data points (F2.1, F2.3).
- RBI Kehta Hai and the Raju booklet unread (F1.12); outsourcing directions not fetched (F1.1); CNAP status (F1.6).
- Whether Aadhaar and PAN print date of birth (F4.7); current CONC wording (F3.12).
- Nothing measured on phone calls or in India.
- No source says an outbound caller must never ask identity questions (F4.8).

## Recommended menu and default for Samajh

The P8 sub-orchestrator's recommendation, put to the coordinator on 2026-11-10; the decision taken is recorded in `P8-report.md`.

- **Second checks (fixed in code):** `none`, `year_of_birth`. Not built unless asked: `pin_code` (two US ZIP templates and a US study; no Indian source; the household knows it (our reading) and is the likeliest third party; the word collides with the `we never ask for a PIN` line) and any second item (no source shows two).
- **Checks:** 0 or 1. **Attempts per check:** 1 or 2, default 2. No source sets a limit; one attempt ended a genuine borrower on a transcription slip; two blind guesses at a year succeed roughly 4% to 10% of the time (our arithmetic).
- **With `none`:** a bare yes is not enough: the caller must say they are the borrower themselves (the existing `are you yourself <name>?` line). The setting and the case file say a person who says they are the borrower is treated as the borrower.
- **Non-question measures as settings:** the call-back line stays on (the call already says to hang up and call the number on the loan papers, never a number the caller gives, F2.8). A prior-notice message is added (an SMS card in the browser demo; an SMS or the written notice in production). The 1600 series is named in the notice; a browser demo cannot show it.
- **Recommended default:** `none` plus prior notice and the call-back line; `year_of_birth` is the lender's opt-in.
  - For: the year stops only a stranger who falsely claims the name. It does not stop family or anyone holding a leaked record; the verifier's false claimants with the right year passed 3 of 3. Four institutions advise customers against giving a date of birth on a call, and RBI describes a caller who knows your date of birth as an impostor pattern, so the question looks like the scam customers are warned about (F1.3, F2.5). It costs 15 to 20 s and ended one of two human calls.
  - Against: "verify before disclosing" with one extra item is the visible vendor convention (F3.1 to F3.5); RBI 454Y(1) and 85N(6) expect loan matters to stay with the borrower; the brief says to keep `year_of_birth` as the default unless the coordinator decides otherwise.
  - This is a judgement, not a finding.

No statement here is a claim that identity is verified: every option is a right-party check, and the case file records which one was used.
