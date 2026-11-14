# Samajh: a post-sale understanding callback for Indian lenders

**Team:** Pranav Pandian and Sambhav Jain · Great Indian AI Internship Challenge · built on Gnani's Speech APIs

## The problem
Borrowers are sometimes sold an add-on with a loan without understanding it. In one Insurance Ombudsman award (Bhopal, BHP-L-021-1617-0529), a gold-loan borrower had ₹52,000 deducted from the loan amount, described as a "fixed deposit for loan security" (his account). It was a life-insurance policy; the Ombudsman ordered it cancelled and ₹52,000 refunded. From 1 January 2027, RBI's para 85Y requires a bank to set up a mechanism to seek feedback within 30 days of a sale on whether customers understood the product's features and risks, and to prepare a half-yearly report.

## The solution
Samajh is a Hindi and Hinglish voice callback. Before it mentions the loan it runs a right-party check (the name, then "are you <name> yourself?"), not identity verification: a person who says yes twice is treated as the borrower. It asks an open question that names no product: "Did you take anything else with the loan? If so, what, and for how much?" After the call a language model turns the answers into fixed fields, each quote checked against what was said, and plain code (not the model) compares the fields with the lender's record. A conflict goes to a human reviewer with the customer's own words, linked to that moment in the recording, in an evidence bundle that is tamper-evident: it detects a change made after the fact unless the chain heads and seals are rebuilt too. Gaps in understanding are counted in the half-yearly report. A flag is evidence for review, never a finding.

## Who it is for
The department of a bank or NBFC that runs the feedback mechanism, the compliance team that prepares the report, and voice-agent vendors serving these lenders.

## How it uses Gnani
- **Prisma STT v3.0** (`POST /stt/v3`, `transcribe`) reads every customer turn.
- **Prisma STT v2.5** gives a second reading where the call expects a figure, such as the premium. Prisma returns no confidence score, so Samajh compares the two readings: if they differ, it asks for the amount again, and every amount is read back.
- **Prisma Batch** gives segment times, so each quote links to its point in the recording.
- **Timbre TTS v3.0** is the bot's voice; every fixed line is made before the first call.

## What we measured
On a held-out synthetic set (TTS audio, simulated 8 kHz phone line), Prisma v3.0 `transcribe` wrote a different amount for 40 of 68 amounts that skip a place-value group and for 0 of 68 matched controls; "one lakh three hundred" became 1,300. 26 of the 40 are wrong under any reading. Its `verbatim` output had the right number words in all 40, and v2.5 wrote none wrong. Accepting an amount only when both models agree accepted 224 of 280 synthetic clips and 113 of 124 public Hindi recordings, with no wrong amount accepted (107 of the 124 are from train splits, so this may be optimistic). On the synthetic set v2.5 alone was wrong on 0 of 280, so agreement only added re-asks there; the case for the rule rests on 6 public clips (v2.5 alone wrong on 4 of 119 accepted, agreement on 0 of 113). An independent verifier reproduced every number. None is a rate on real callers.

Three more, from iteration 4, each on synthetic text or TTS audio. On the same 68 skipped-group clips (scored by our frozen parser, which cannot read transliterated English number words) Whisper large-v3 wrote 33 wrong amounts, IndicWhisper 15 and Gemini 3 Flash 8; no open model matched v2.5 `transcribe`. On synthetic Hindi and Hinglish text (160 customers, replies written by two outside models from beliefs alone), when customers answer for themselves the open call referred 80 of 80 problem customers on a gold ground and turned 45 of 48 customers' own "don't know" into an understanding gap on the right field; we make no claim that it finds more than a yes/no call, because under matched giving way it found fewer. An independent checker tried 47 kinds of tampering on the evidence bundle; ten were missed, fixed and rerun.

## Status
A call runs on a browser phone to a case file; a reviewer queue and report run on a simulated 200-loan book. The call's latest full independent check (typed text, not speech): ready for consenting testers playing customers, with the classifier on and degraded sessions voided; not ready for anyone else. Iteration 4's changes (name matching, a live language switch, follow-up questions, pre-made lines) were each checked once on typed text or replayed TTS audio. The only human audio is two unscored practice calls; the team's human calls start on 2026-11-15. All data is synthetic. Details: `README.md`.
