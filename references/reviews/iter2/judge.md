<!-- Saved by the coordinator on 2026-11-10 from the judge's final message, unchanged. -->
# Judge's review of iteration 2 (2026-11-10, commit 403c48c, read-only)

## 1. Verdict

**Continue, but change the order: post the video before more evidence, and stop hardening.** Score on the iteration 1 rubric: **75 of 100 today (7.5 of 10)**; **about 81 (8.1 of 10)** if the next round goes well. The iteration 1 judge forecast 79 without human calls; the gap is P5 not run and no video. As a submitted entry the score today is zero: nothing is posted and nobody on the project knows the closing date.

| Criterion | Max | Iter 1 | Today | After next round |
|---|---|---|---|---|
| Gnani and market fit | 20 | 18 | 19 | 19 |
| Verified novelty | 20 | 11 | 12 | 12 |
| Evidence of demand | 15 | 10 | 10 | 10 |
| Feasibility | 15 | 11 | 12 | 13 |
| Measurability | 10 | 6 | 7 | 9 |
| Demo strength | 10 | 4 | 6 | 9 |
| Headroom | 10 | 9 | 9 | 9 |

**Product.** The parts are joined. A Hindi or Hinglish call runs on the browser phone, takes two Prisma readings on figures, and ends in a case file, a reviewer page with quotes and audio offsets, and a half-yearly report. I played a misled Hinglish customer in Devanagari offline: 12 questions, a correct read-back, a clean close. Weak points I saw or that the reports show: the first real question comes at about 55 s; there is no acknowledgement between questions; a romanised figure ("bavan hazaar") was not read, so the premium was asked again; "pata nahi, kabhi bhi nikal sakta hoon shayad" got "shall I go on or stop?" (one typed input, word lists only). The call is "ready with conditions" for consenting testers only (`verify-P2-r3.md`).

**Evidence.** The Gnani amounts finding is the one result that is held-out, matched, independently reproduced and partly on real voices (`verify-P6.md`). Everything about the product's own claim (catching a misled customer) is still typed text written by the team: 2 of 38 problem calls missed, 0 of 18 informed customers referred. No voice number exists for the product. The only human audio is one speaker, two practice calls, not independently verified: one died at the birth-year step, and the completed one had a modelled median of 3.4 s from end of speech to reply (`P1b-ownvoice-timing.md`).

**What a judge can see.** One good frame: the phone case page ("Customer described the product as a deposit (FD); the record shows insurance", with "Play the recording from 1:27"). The amount-check clip shows v3.0 writing 2,000 and v2.5 writing 2,012. There is no video, no fixed name, and no human voice in any prepared demo. The report page is about 9,700 px of tables and is not a video frame.

## 2. Iteration 2 against its plan

1. One real call, end to end: **delivered** (P1, P1b verified "sound"; P1c is builder evidence only).
2. Call v2 for real people: **partly**. False declines fixed (0 of 40 genuine borrowers ended), new outcomes built; the user's wording pass is not done; round 4 still open.
3. Triage, queue, report: **delivered**, after five verification rounds.
4. Twenty human calls: **not delivered** (two practice calls by the user).
5. Evaluation on unscripted customers (P5): **not delivered**; prepared and frozen, not run.
6. Harden the Gnani finding: **delivered** and verified; the two reports and the note to Gnani still wait on the user.
7. Demo and submission: **not started**.
8. "Reports of two pages": **not delivered** (`P3a-report.md` is 36 KB, `verify-P2-r2.md` 38 KB).

## 3. The next round, ranked by benefit per hour

Items 1 to 5 and 10 are the user's own hours, about 12 to 14 in all. That is where the entry is won or lost now.

| # | Item | What it changes | Rests on | Who, hours | Risk | Depends on |
|---|---|---|---|---|---|---|
| 1 | Read the challenge page: closing date, engagement cutoff, how to submit, whether you name the category | Sets every other deadline. Internships are filtered on engagement recorded before the cutoff | `USER-GUIDE.md` §5; `RESEARCH.md` §1 | User, 10 min | None | Nothing |
| 2 | Decide tonight: name, category, "teen lakh chalis", yes to the two P6 reports, the year step (4c), the record-fault split (4b) | Unblocks 3, 4, 6, 7, 8 | `USER-GUIDE.md` §2.5, §2.7 | User, 30 min | None | 1 |
| 3 | Wording review of the 69 lines, then the listening pass | Every second of the video and every human call uses lines no fluent person has read or heard | `USER-GUIDE.md` §2.2; `P1c-report.md` §3 | User 2 h; agents 1 h, about 13 credits | A changed line needs the lint and tests | 2 |
| 4 | Record and post a first 60-second video, in the user's voice, before the human calls finish | It is the entry. The numbers it needs (P6) are already verified; the pages exist | `DESIGN.md` §10; `verify-P1b-r2.md` item 7 | User 3 h; agents 2 h | Posting before P4 results; they go in the write-up instead | 1, 3 |
| 5 | Human calls: 5 uncounted shakedown calls by the user, fix thresholds, then the 20 counted | First real-voice result for the product; answers "synthetic voices" and "you scripted it". Speech now finds faults typed probes cannot | `P1b-ownvoice-timing.md`; `verify-P2-r3.md` verdict | User 1 h, then 2 to 3 h with friends; agents 2 h | The one Gnani slot must be free; speaker echo untested | 3; round 4 landed |
| 6 | Send Gnani the reproduction privately; put both P6 reports in the repo, led by the 26 unambiguous cases and framed as v2.5 against v3.0 | The Jugaad case and the best interview story | `verify-P6.md` findings 2 and 4; `direction-review.md` §2 | Agents 1 h; user 15 min | Low | 2 |
| 7 | Count record-only faults apart from `refer` (a tag on the referral, not a new tier, so no re-freeze) | "Referrals per 100" then describes customers, not the lender's database | `product-review.md` §2.1; a 42 s hang-up is `refer` with no quote (I checked the case file) | Agents 2 h, one narrow check | Touches summary and report wording | 2 |
| 8 | Written explanation, two-page brief, judge-first README, last claims check, rotate keys, publish | Required parts of the submission | `RESEARCH.md` §1; `USER-GUIDE.md` §2.4, §2.6 | Agents 3 h; user 1 h | Stale documents (see 6 below) | 1, 2 |
| 9 | P5, smaller: text path on all 60 customers and both arms now; voice on the open arm only, overnight | The only number on the product's claim that needs no people | `P5-contract.md` | Agents 3 to 4 h; my estimate 100 to 150 credits | Holds the Gnani slot; 14 misled customers gives wide intervals | Round 4 landed; never during 4 or 5 |
| 10 | Interview preparation | Internships are decided in individual interviews | `USER-GUIDE.md` §2.6 | User 3 h | None | Nothing |

## 4. Open decisions

- **(a) Award: Jugaad Genius.** Its criterion is the entry's one verified asset: two Prisma versions read against each other as the confidence score Prisma does not return. Real Deal needs users and the entry has none. Mixed Vibes has no measured code-mix result behind it. Write the first lines for Jugaad and the next for Real Deal.
- **(b) Record-only faults: their own count.** A missing consent on the record needs no call. Today it refers a call the customer left after 42 s, and 8 of 16 informed customers on the text path. `refer` should need at least one customer statement.
- **(c) Year of birth: off by default, a lender setting.** It costs 15 to 20 s, a false claimant with the right year passes (3 of 3), it gets one attempt, and one of the two human calls died there. The lender is already named in the opening line, so the step protects only the word "loan". (My reading; a lender may still want it.)
- **(d) Risk question: do not add.** The call has 12 questions and each new one needs lines, rules, gold, a wording review and a check. Name the money-back question as the risk probe and state the limit.
- **(e) Two-model agreement: keep, and say plainly what it rests on.** On the held-out set v2.5 alone was wrong 0 of 280, so agreement only added re-asks there. The case is 6 public clips: v2.5 alone wrong on 4 of 124, agreement 0 of 113. Every amount is read back anyway. Drop the cheaper `literal` variant. Inferred from one clip: on a disagreement, go straight to the read-back, because the re-ask differed again.
- **(f) P5: the smaller one** (item 9). The closed arm is yes or no, so its voice path adds little (inferred).
- **(g) Hardening: finish round 4, one narrow check of its items, then stop.** Three rounds each found new faults because typed adversarial text has no end. Severity at the opening fell (16 of 64 third parties named the loan in round 2; 0 of 26 in round 3). Human callers are consenting testers on synthetic records, so a leak harms nobody. The next faults worth finding are in speech.

## 5. Stop doing

- More P3b verification. Round 5 tested a deleted sessions directory and a "result:" prefix. No judge or buyer will meet these.
- Typed retraction and amount probes on P3a. Measure how often Prisma output lacks punctuation on the cached transcripts once (15 minutes), then stop.
- Loan-book edge cases (non-ASCII digits in six scripts on a demo picker), mutation rounds, and adding to 4,400 tests. Run the whole suite once before publishing.
- New rows in the 158 KB claims ledger, interval tables on a simulated book, anything in Tamil or Kannada, long reports.
- Gating the user's work on agent verification. The gate for testers was met at round 3.

## 6. Claims check (verifiers' wording)

May say:
1. "On a held-out synthetic set built to stress amounts that skip a place-value group, Prisma v3.0 `transcribe` wrote a different amount for 40 of 68 such amounts (59%, 95% CI 47-70) on simulated 8 kHz phone audio, and for 0 of 68 matched controls. Its `verbatim` output of the same audio had the right number words in all 40, and v2.5 wrote none wrong."
2. "On 328 verifier-written Hindi and Hinglish text inputs, 64 of 65 genuine borrowers passed both checks in each of three arms."
3. "On 19 typed corrections away from the record value, the taken-back value was never the stated belief."

Must not say:
1. "v3.0 gets 14% (or 1 in 7) of amounts wrong", or any per-call or field rate.
2. "third parties learn nothing", "identity verified", "ready for real customers", "tested on speech".
3. "A retraction never yields a stated value." `DESIGN.md` §15 item 30 and the handoff still state this as a decision; `verify-P3a-r3.md` forbids it as a claim. Reword both.

For the video and write-up, from the claims ledger (read through a summariser):
- The "usual confirmation call" in the video is an illustration. The hero award (B1) "does not mention a verification call", and "asked for ₹5 lakh and received ₹4.48 lakh" is banned as a fact of that award (X5).
- "Teach-back rather than yes/no" is not what Samajh adds: Edesy (C2.3) and a hackathon entry, Saakshi (C2.5), already describe it. Lead with the record comparison, the evidence pack and the measurement.
- 85Y sets no channel and does not require random sampling, call-backs or an independent unit (A11, S8).
- The ledger has no row for the held-out amounts result; `verify-P6.md` is the wording source.

Also stale: `ORCHESTRATION.md` and `README.md` still say the phone cannot call a loan from the book and that P2 is unverified.

## 7. Not read or run

- Read through summariser agents, not myself: `verify-P2-r2`, `P2-report`, `verify-P3a-r2`, `P3a-report`, `verify-P3b-r2` to `-r4`, `P3b-fix2-report`, `verify-P1b` round 1, and the claims ledger (I read only its 85Y rows myself).
- Not read: `RUNNER-PLAN.md`, `eval/p5/VERIFY.md`, DESIGN outside §10, §13, §15, RESEARCH outside §1, any code.
- Not run: the server, any Gnani or LLM call, the test suite, any page in a browser. No audio heard. I did not rerun the informed demo call to confirm it now ends `clear` (the records now list `one_time_payment`).
- Ran: two typed calls with the word lists only (no classifier), and `samajh.ops demo` (refer 7 of 64, understanding gap 33 of 64).
- Inferences are marked. The scores, the hours and every statement about what a Gnani judge wants are my judgement, not measurements.
[payload] {"taskId":"task_b3e1ea61d7f1","dispatchId":"ctx_a71952f90d08","outcome":"succeeded"}

