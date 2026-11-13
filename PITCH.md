# Samajh: a post-sale understanding callback for Indian lenders

**Team:** Pranav Pandian and Sambhav Jain · Great Indian AI Internship Challenge · built on Gnani's Speech APIs

## The problem
Borrowers are sometimes sold an add-on with a loan without understanding it. In one Insurance Ombudsman award (Bhopal, BHP-L-021-1617-0529), a gold-loan borrower had ₹52,000 deducted from the loan amount, described as a "fixed deposit for loan security" (his account). It was a life-insurance policy; the Ombudsman ordered it cancelled and ₹52,000 refunded. From 1 January 2027, RBI's para 85Y requires a bank to set up a mechanism to seek feedback within 30 days of a sale on whether customers understood the product's features and risks, and to prepare a half-yearly report.

## The solution
Samajh is a Hindi and Hinglish voice callback. Before it mentions the loan it runs a right-party check (the name, then "are you <name> yourself?"), not identity verification: a person who says yes twice is treated as the borrower. It asks an open question that names no product: "Did you take anything else with the loan? If so, what, and for how much?" After the call a language model turns the answers into fixed fields, each quote checked against what was said, and plain code (not the model) compares the fields with the lender's record. A conflict goes to a human reviewer with the customer's own words, linked to that moment in the recording; gaps in understanding are counted in the half-yearly report. A flag is evidence for review, never a finding.

## Who it is for
The department of a bank or NBFC that runs the feedback mechanism, the compliance team that prepares the report, and voice-agent vendors serving these lenders.

## How it uses Gnani
- **Prisma STT v3.0** (`POST /stt/v3`, `transcribe`) reads every customer turn.
- **Prisma STT v2.5** gives a second reading where the call expects a figure, such as the premium. Prisma returns no confidence score, so Samajh compares the two readings: if they differ, it asks for the amount again, and every amount is read back.
- **Prisma Batch** gives segment times, so each quote links to its point in the recording.
- **Timbre TTS v3.0** is the bot's voice.

## What we measured
On a held-out synthetic set (TTS audio, simulated 8 kHz phone line), Prisma v3.0 `transcribe` wrote a different amount for 40 of 68 amounts that skip a place-value group and for 0 of 68 matched controls; "one lakh three hundred" became 1,300. 26 of the 40 are wrong under any reading. Its `verbatim` output had the right number words in all 40, and v2.5 wrote none wrong. Accepting an amount only when both models agree accepted 224 of 280 synthetic clips and 113 of 124 public Hindi recordings, with no wrong amount accepted (107 of the 124 are from train splits, so this may be optimistic). On the synthetic set v2.5 alone was wrong on 0 of 280, so agreement only added re-asks there; the case for the rule rests on 6 public clips (v2.5 alone wrong on 4 of 119 accepted, agreement on 0 of 113). An independent verifier reproduced every number. None is a rate on real callers.

## Status
A call runs on a browser phone to a case file; a reviewer queue and report run on a simulated 200-loan book. The call's latest independent check (typed text, not speech): ready for consenting testers playing customers, with the classifier on and degraded sessions voided; not ready for anyone else. The only human audio is two unscored practice calls. All data is synthetic. Details: `README.md`.
