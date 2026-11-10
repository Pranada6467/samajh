# Samajh: a post-sale understanding callback for Indian lenders

**Team:** Pranav Pandian and Sambhav Jain · Great Indian AI Internship Challenge · built on Gnani's Speech APIs

## The problem
Borrowers are sometimes sold an add-on with a loan without understanding what it is. In one Insurance Ombudsman award (Bhopal, BHP-L-021-1617-0529), a gold-loan borrower had ₹52,000 deducted from his loan, described as a "fixed deposit for loan security". It was a life-insurance policy. A confirmation call that asks yes/no questions records a "yes", which is weak evidence of understanding. From 1 January 2027, RBI's directions (para 85Y for commercial banks) ask lenders to seek feedback within 30 days of a sale and to prepare a half-yearly report.

## The solution
Samajh is a Hindi and Hinglish voice callback. It confirms who is on the line before it mentions the loan, and never asks for an OTP, PIN, password or account number. It asks an open question that names no product: "Did you take anything else with the loan? If so, what, and for how much?" After the call, plain code (not an LLM) compares each answer with the lender's record. Every difference becomes evidence for a human reviewer: the customer's own words, linked to that moment in the recording. A flag is evidence for review, never a finding. The calls roll up into the half-yearly report.

## Who it is for
The unit of a bank or NBFC that runs the feedback mechanism and is not associated with sales, the compliance head who owns the report, and voice-agent vendors who serve these lenders.

## How it uses Gnani
- **Prisma STT v3.0** (`POST /stt/v3`, `transcribe`) reads every customer turn.
- **Prisma STT v2.5** gives a second reading whenever the customer says an amount. Prisma returns no confidence score, so Samajh uses agreement between the two models as one: if they differ, it asks again, and every amount is read back.
- **Prisma Batch** gives segment times, so each quote links to its point in the recording.
- **Timbre TTS v3.0** is the bot's voice.

## What we measured
On a held-out synthetic set (TTS audio, simulated 8 kHz phone line), Prisma v3.0 `transcribe` wrote a different amount for 40 of 68 amounts that skip a place-value group (59%, 95% CI 47-70) and for 0 of 68 matched controls; "one lakh three hundred" was written as 1,300. Its `verbatim` output had the right number words in all 40, and v2.5 wrote none wrong. Accepting an amount only when the two models agree accepted 224 of 280 synthetic clips and 113 of 124 public Hindi recordings, with no wrong amount accepted (107 of the 124 are from train splits, so this may be optimistic). An independent verifier reproduced every number.

## Status
A working call on a browser phone, a reviewer queue and the report page, over a simulated 200-loan book. All records and customers are synthetic; nothing here is a claim about real callers. Details and how to run it: `README.md`.
