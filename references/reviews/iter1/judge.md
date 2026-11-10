# Judge's review of iteration 1

Date: 2026-11-10. Reviewer: independent judge (wrote none of the code or documents).

## Verdict: continue with changes

The idea is right and the foundations are sound. The plan for iteration 2 is not. Iteration 1 proved the components and never joined them: there is still no Samajh call on the phone, the headline experiment (E1) is true by construction, and the verdict logic sends an ordinary well-informed customer to review. Iteration 2 should build one real Hindi and Hinglish call end to end, redesign the call and the verdict for real people, build the reviewer queue and the half-yearly report, and replace E1 with evidence from customers the builders did not script.

**Score: 69/100 today** on the `IDEAS-HILLCLIMB.md` rubric (the idea scored 84). **79 after the recommended iteration 2 without human recordings, 82 with 20 human calls.**

### How I checked

"Ran" means I executed it today. "Read" means I read the primary artifact and did not rerun it. My probe scripts and transcripts are in `references/reviews/iter1/judge-probes/`.

| Check | How |
|---|---|
| Three full calls typed into `samajh.dialogue play` (misled Hinglish, informed Hindi, ordinary informed Hindi), then scored with `judge_run_text.py` through `samajh.pipeline` | Ran. OpenRouter spend about 0.006 USD |
| Six non-refusal replies at "may we go on?" (`judge_goahead_probe.sh`), with and without `--llm` | Ran |
| Five awkward-customer openings (call me later, speak Tamil, is this fraud, yes to everything, "I took nothing") | Ran, typed inline; the replies are quoted in section 3 |
| Call length | Estimated from word counts of `informed_hi_b.transcript.json` at 2.2 to 2.8 words a second. No audio was timed |
| Amounts headline recounted from `eval/amounts/run/scores.jsonl` (`judge_amounts_recount.py`) | Ran. Reproduces 221, 214, 156, 220 of 240; 199 of 200 agreeing; 17 silent wrong amounts |
| `samajh.scenarios verify`, `tests/dialogue/test_no_leak_and_termination.py` (41 pass), `references/claims/check_quotes.py` | Ran |
| What is wired to what (`grep` over `samajh/server`, `web`) | Ran |
| Text-path numbers (1 of 108, 0 of 36, the E1 table), API probe, voice-loop latency, vendor pages | Read only. The verifiers are recounting these |

One discrepancy: `check_quotes.py` now reports 3 spans not found in group D (all under D5.10, quotes of pilot lines that `DESIGN.md` v2 rewrote). `W3-report.md` shows 0. No claim fails; the checker is stale against the new design.

---

## 1. The thesis

**What is defensible now.** From 1 January 2027 a lender must seek feedback within 30 days of a sale to ensure the customer understood the product, and must prepare a half-yearly report on the findings (85Y, 101Y). Samajh is a working reference for that mechanism on one product family. Its finding for each customer rests on the customer's own quoted words compared with the lender's record by plain code, and its accuracy is measured and published with its failures. That is the whole claim. It is a claim about how the check is built and measured, not about a category nobody else is in.

**Is the four-part difference enough?** Not as stated. Taking each part:

- *An open question before any product is named.* This is a script choice a vendor can copy in a day. Edesy's page already describes the customer saying "I was told this is a fixed deposit" or "I thought the premium was one-time" and routing the case to a person (ledger C2.3). That is the hero case and scenario B03. What Samajh has that the blogs do not is a tested property: bot lines are word-for-word identical across two records that differ in every tested value (I ran the test; 41 pass). "The bot cannot leak the answer, and here is the test" is a real claim. "We ask open questions" is not.
- *Deterministic comparison with the record.* Ringg's page claims a comparison of understanding with policy information. The category is taken. The implementation is the difference: the model returns only spans and enums, code grounds every quote, and silence is never a pass.
- *Evidence pack.* Today it is a data type. No one can look at it.
- *Measured evaluation.* This is the real difference from every vendor page, and it is weaker than it looks because the customers are scripted by the team (section 2).

**What matters to a lender** is none of the four. A lender asks: is the unit that calls independent of sales, how many cases land on my reviewers per 100 calls, and what do I show for the half-yearly report. SquadStack's flow cross-sells in the same call (ledger C2.2), which is a sourced, sharp difference: Samajh's call carries no sales content and the lint enforces it. The other two questions Samajh cannot answer yet.

**What would make it clearly stronger:**

1. Lead with the artifact the rule names. Build the half-yearly findings report from a batch of calls. No vendor page shows one.
2. Replace "teach-back beats yes/no" with a matched comparison: a best-practice closed script that states the product, premium, cover and cancellation window, against the open call, on the same customers, with the customer's disposition applied to both arms.
3. State the reviewer load: referrals per 100 informed customers and misses per 100 misled ones.
4. Position it as a reference build and measurement kit that a vendor such as Gnani can put on its own agent stack, not as a rival to SquadStack. The ledger lists a saved Gnani page on banking feedback calls (C2.7). I did not read it; read it before the interview.

## 2. The evidence

**Would survive a sceptical BFSI interviewer**

- The regulatory grounding. 437 of 440 quoted spans are in the saved sources (ran; the 3 misses are stale design quotes).
- The measured Gnani API facts, especially where live behaviour contradicts the docs (read).
- The amounts finding as a statement about Prisma's number formatting. I recounted it from the scores file. It survives better than an accuracy rate would, because a formatting error is a text-layer fault: in 8 cases Prisma v3.0's own verbatim output has the right words and its `transcribe` output has the wrong digits, so the voice is not the cause.
- The extractor's grounding. On three calls I typed myself (not builder text), the misled customer got 11 flags with correct quotes, and the carefully informed customer on a compliant record came out `clear`.

**Would not survive**

- **E1.** Coached and acquiescent customers say yes to the closed call because the script says so, and the "never asked" stratum counts questions the five-question closed script was written without. 0 of 12 against 12 of 12 is a property of the script. The design admits this in every paragraph that cites it. A result that needs five caveats to state is not a headline.
- **False alarms 0 of 36.** It measures the extractor on templated replies. My ordinary informed customer (knows it is insurance, about ₹52,000, deducted from the loan, voluntary, signed a form; unsure of the cancellation window and exact figures) on a fully compliant record came out `flag_for_review` with one low flag and four gaps. "पचास बावन हज़ार के आसपास" produced no amount and no read-back. "जब तक लोन चलेगा" and "वापस तो नहीं मिलेगा शायद, बीमा है ना" were both unusable. That is one call, typed by me, but it is the modal real customer, and it shows the 0 says nothing about the field.
- **"Calls ended on a reply that was not a refusal: 0"** (`W9-dialogue-report.md` §4). Three of my six non-refusals ended the call as `declined`, with and without the LLM fallback: "ठीक है, जल्दी बोलिए थोड़ा बिज़ी हूँ", "ये फ्रॉड कॉल तो नहीं है? आप कहाँ से बोल रहे हो?" and "मुझे हिंदी ठीक से नहीं आती, तमिल में बोलिए".
- Every Tamil and Kannada number, the 1.18 s latency (12 turns of TTS clips), and anything described as phone audio (it is mu-law applied to clean TTS).

**Strongest honest headline today.** "On 240 synthetic spoken amounts over simulated phone audio, Prisma v3.0 returned a wrong rupee amount with no warning on 17. Amounts that skip a group are the clearest case: 'three lakh two hundred' comes back as 3,02,000. When v2.5 and v3.0 gave the same amount (200 of 240) it was right 199 times, so Samajh reads every amount with both models and reads it back." It is specific to Gnani, reproducible, and has its n. Two limits to state with it: only 96 of the 240 amounts fall between ₹1,000 and ₹2,00,000, where a retail premium lives (there v3.0 had 6 silent wrong amounts, and 84 of 85 agreeing readings were right), and all 16 voices are Timbre.

**The single piece of evidence that would raise it most: 20 improvised Hindi and Hinglish calls by real people through the real phone, scored against brief cards.** Nothing else answers both objections ("synthetic voices" and "you scripted the customers") at once. It needs the user and one to three consenting friends for about two hours.

**What can be done with no one recording, in order of value:**

1. A voiced end-to-end run with customers the builders did not script. A different model from the extractor plays each customer from a persona card (what they were told at the sale, how they talk, how readily they agree). Its replies go through several Timbre voices, the phone channel, Prisma, the real dialogue and the extractor. Disposition is a parameter applied to both the open call and the matched closed call, so the result is a curve (catch rate against the probability of agreeing), not a tautology. This would be the first voice number for the product itself. There is none today.
2. Real voices for the amounts finding. Mine IndicVoices and Kathbath Hindi transcripts for utterances that contain rupee amounts and run both Prisma models on them (evaluation only, per `references/real-voice-datasets.md`). It turns the lead finding from TTS-only into real speech. It needs the user to accept the dataset terms on Hugging Face, which takes minutes.
3. A perturbation suite on development transcripts: hedged, approximate, one-word, answer-ahead and off-topic replies. My ordinary-customer probe shows this is where the verdict breaks.
4. A fresh amounts set from a new seed, weighted to ₹500 to ₹5,00,000, frozen before any audio. The current set is in-sample for the parser.

**What truly needs humans:** improvised calls, the end-of-speech threshold on real microphones, and a fluent read of every prompt. The user can do all three for Hindi and Hinglish. No one can for Tamil and Kannada.

## 3. The product

**Is this a call a real person would finish? Not yet.** What I saw when I played it:

- **It opens with a one-minute monologue.** The disclosure is 140 of the bot's 365 words, in seven statements, before the customer says a second word. At 2.2 to 2.8 words a second the whole one-product call runs about 3.5 to 4.5 minutes (my estimate from word counts; no audio was timed). An unsolicited automated call that talks for a minute first will lose most people.
- **It hangs up on the customer most worth keeping.** "Is this a fraud call?" is the likeliest reply to that opening, and the bot ends the call. It does the same to a customer who agrees but is in a hurry, and to one who asks for Tamil. There is no "call me later" outcome and no language switch.
- **It interrogates a customer who has already said they bought nothing.** After "कुछ नहीं लिया, बस लोन लिया था" the bot starts its eight questions about "वो चीज़" anyway, and re-asks each one the customer cannot answer ("कौन सी चीज़? मैंने तो कुछ नहीं लिया" gets the same question again in other words). This is the Baramulla customer, the highest-value case, and the call turns absurd. It should ask one neutral follow-up, go to the consent question, and close with a high-severity referral.
- **The wording is stiff where it matters.** "आपके हिसाब से वो चीज़ क्या है?" is the price of never naming the product. It reads as a riddle. The provider-choice question is asked of everyone, though it matters only if the customer says the product was required. Asking it only then leaks nothing, because the branch depends on the customer's answer and not on the record.
- **The verdict is all or nothing.** `clear` needs every rule to pass and any flag makes `flag_for_review`. Most honest, informed customers do not know the cancellation window or the exact cover. In the field nearly every call will be a flag or unclear, and the output will not rank anything.
- **The case is noisy.** My misled customer produced 11 flags: `kind` twice, `bundling` three times, `belief_mismatch` three times. A reviewer wants three lines.

**Would a bank's non-sales unit deploy it?** As a pilot of the idea, yes: the evidence format is what compliance wants. As it stands, no: the review load is unbounded, there is no operating layer, and transcripts leave for OpenRouter.

**Missing between "flag" and "someone acts":**

1. **Sampling.** Random selection from loans sold in the last 30 days, with the day since sale logged.
2. **Call scheduling.** Attempts, retries, call-back-later, preferred language from the record, and the reach funnel (sampled, reached, completed, declined). The funnel is the denominator of the report.
3. **Triage.** Three outcomes in place of one: *refer* (kind, consent, loan-funded, bundling, belief mismatch, sale conduct), *understanding gap, report only* (cover, term, cancellation window, a product not named unprompted), *incomplete*. The low flags are exactly what 85Y's report is for: "38% of sampled customers could not state the cancellation window" is a finding that reviews a policy. They do not belong in a case queue.
4. **Reviewer queue.** One screen per case: record beside quotes with audio offsets, a deduplicated summary, a disposition (established, not established, call the customer), notes.
5. **The half-yearly report.** Generated from the batch.
6. **The loop back.** Reviewer dispositions are the first real labels for flag precision.

**Open decisions in `DESIGN.md` §15:**

| Item | Call | Why |
|---|---|---|
| 1 Reviewers per language | Adopt as a gate | Hindi and Hinglish aim for "supported"; Tamil and Kannada leave the call (section 5) |
| 3 Name | Defer | Not a constraint |
| 4 Second product family | Drop for iteration 2 | The call is already too long. Keep one slide: 85Y covers "any financial product", so the loan's own terms are the natural next family |
| 5 KFS check | Drop | Uncertain reach for bullet gold loans, no demo value |
| 6 Call timing | Adopt | It is one field in the sampler |
| 7 Fuller evidence log | Adopt | The audio hash and prompt log are what make "evidence pack" true |
| 9 Text-confirmation arm | Replace | Build the matched closed arm instead |
| 10 Dark-pattern slide | Drop | It is a related pattern, and it dilutes the hero case |
| 11 Retention setting | Defer | One sentence in the write-up |
| 14, 17, 18 "Not named" and "don't know" are flags | Keep as findings, change the routing | Report-only tier, not a referral |
| 16 Two readings on amount turns | Keep, and put it in the product | It exists only in the evaluation and the dialogue core. The server never calls it |
| 22 Extraction after the call | Keep; run the requests in parallel | My runs took 55 s and about 100 s one after another |
| 23 One bad model output fails the call | Change to field-level `unclear` | A human reviews it either way |

## 4. Fit with the challenge

**Category: Real Deal, with the video cut so it can also stand for Demo Day Drop.** One risk: the award's own examples are farmers, kirana and rural health workers, so frame the user as the borrower who was sold an "FD", and the bank as the payer. If Tamil and Kannada go, Main Character was never the target and nothing is lost. Jugaad Genius is the best alternative: using two Prisma versions against each other as the confidence score Prisma does not return is a creative use of Gnani's models, and it belongs in the written explanation whichever category is named.

**The 60-second demo.** The present plan (§10 step 4) puts a four-stratum table and five caveats on screen. Nobody can read that in ten seconds. Use this:

1. 0 to 5 s. One line of 85Y and the date 1 January 2027.
2. 5 to 15 s. The usual confirmation call: "Aapne policy li hai?" "Haan." Confirmed. Caption: this customer was told it is an FD.
3. 15 to 40 s. The Samajh call on the browser phone, a real human voice in Hinglish. "Loan ke saath aapne kya-kya liya?" "Ek FD, security ke liye, bavan hazaar." Split screen: the record on the right, the quote lighting up against it, and on the amount turn the two readings side by side ("v3.0 52,000 · v2.5 52,000 · agree"), then the read-back.
4. 40 to 50 s. The reviewer's card, then the half-yearly report page built from a batch of calls.
5. 50 to 60 s. Two numbers with n and source, then "Prisma v2.5 and v3.0, Timbre v3.0, Prisma Batch".

**Is Gnani incidental?** In the evaluation, no. The API probe and the amounts report are the most Gnani-specific work in the repository (2,640 transcriptions, both models, behaviour that contradicts the docs), and a Gnani engineer would respect them. In the product, today, yes. The server runs a three-question stub on v3.0 only. The Samajh dialogue is not imported anywhere under `samajh/server`. The second reading, Batch timestamps and pre-generated Timbre prompts are not on any call path. Iteration 2 must move the Gnani work from the harness into the call.

**Lead with:** the skipped-group formatting fault and two-model agreement, presented as found, isolated (v3.0's verbatim output is right), worked around (second reading and read-back) and reported. Hand Gnani a minimal reproduction: the 16 sentences and a one-file script. A clean bug report from an entrant is rare. Second: streaming rejects the comma-separated language list that the docs allow (13 of 13).

## 5. Scope

**Two languages. Cut Tamil and Kannada from the call, the prompts, the demo and every headline number.** The reasons are all in the project's own evidence: no fluent reviewer; 13 of 17 wrong fields and the only false clear are in those two languages; 14 of 15 v2.5 timeouts are too; the parser refuses Kannada fractions until a Kannada reader checks them; the amounts report itself calls some Tamil test sentences doubtful. The design's own bar for "supported" needs a reviewer and ten human calls. Gnani is a Bengaluru company. Machine-written Kannada that nobody on the team can read, played to a Kannada-speaking judge, is a liability. Keep the Tamil and Kannada amounts results as an appendix marked "not human-reviewed", because the number-formatting finding spans languages. Report the frozen set as Hindi and Hinglish (72 calls, 36 base cases) with the other 72 in the appendix.

**No second product family.** One family, done to the point where a person can complete the call and a reviewer can act on it.

## 6. Score

| Criterion | Max | Idea (round 5) | State today | After iteration 2 | Reason for today's score |
|---|---|---|---|---|---|
| Gnani and market fit | 20 | 20 | 18 | 19 | The buyer and the rule are right. The integrated product barely touches Gnani yet |
| Verified novelty | 20 | 14 | 11 | 12 | The claims check found three adjacent vendors, one describing the hero case |
| Evidence of demand | 15 | 11 | 10 | 11 | A dated rule and vendors already marketing to it; no payer, no bank statement |
| Feasibility | 15 | 11 | 11 | 12 | Every component exists and credits are fine (about 115 of 1,000); no humans, no integration |
| Measurability | 10 | 9 | 6 | 8 (9 with human calls) | The harness and discipline are excellent. What was measured is not the product's claim |
| Demo strength | 10 | 9 | 4 | 8 (9) | No Samajh call on the phone, no view of a case or a report |
| Headroom | 10 | 10 | 9 | 9 | Unchanged apart from the narrower language scope |
| **Total** | 100 | **84** | **69** | **79 (82)** | |

The 84 was scored before the claims check. Re-scored with what is now known about vendors, the idea itself is about 80.

---

## Iteration 2 plan, ranked

| # | Package | Goal | Why it ranks here | Proves it done | Depends on | Parallel? |
|---|---|---|---|---|---|---|
| 1 | **One real call, end to end** | The Samajh dialogue (hi, hi-en) on the browser phone: pre-generated Timbre prompts, Prisma v3.0 per turn, v2.5 second reading on amount turns with a timeout, extraction after the call with parallel requests, rules, a case file, Batch segment times and an audio hash in the evidence | Without it there is no working app, no demo and no voice number. Every part exists | `samajh.server.replay` runs a whole Samajh call from prepared audio to a case file; a person completes a call in Chrome; per-turn latency reported with n | Nothing | Code in parallel with 2 and 3. Live Gnani use must be serialised |
| 2 | **Call v2, for real people** | Opening under 20 s with the other lines on request; fix the three false declines; add call-back-later and language-switch outcomes; a short branch for "I took nothing"; ask provider choice only if the customer says it was required; a Hindi and Hinglish wording pass by the user | A call people abandon produces no evidence. These are cheap and I can reproduce each fault | The probe scripts in `judge-probes/` pass; an informed one-product call is at most 150 s of measured audio; the no-leak test still passes | Nothing | Yes. Owns `samajh/dialogue`, package 1 owns the adapter |
| 3 | **Triage, reviewer queue, half-yearly report** | Three-tier outcome; a deduplicated case summary; a reviewer page; a sampler (random, within 30 days, day logged) and attempt log over a synthetic loan book; the 85Y report page | It is the difference a lender cares about and the artifact no vendor shows. It also fixes the ordinary-customer false referral | From a synthetic book of about 200 loans: sample, run, queue, report all render; my ordinary-informed transcript is not a referral; my misled one is, in three lines | A rule-engine change in the core | Yes |
| 4 | **Human calls** | 20 improvised Hindi and Hinglish calls from brief cards (the user and one to three consenting friends), through the phone | The single most valuable evidence. Ranked fourth only because it needs 1 and 2 first | An E4 table for hi and hi-en with failures listed; the end-of-speech threshold set on this audio | 1, 2; people | After 1 and 2 |
| 5 | **Evaluation v2: customers we did not script** | Persona-driven customers from a different model; a matched closed arm; disposition applied to both arms; voiced through several Timbre voices and the phone channel; a perturbation suite. Report referrals per 100 informed, misses per 100 misled, text against voice | Replaces E1. It is the substitute if no human can record, and the scale evidence if they can | A report on at least 120 voiced calls (hi, hi-en) by persona class and tier; then one run of the frozen set on the voice path, hi and hi-en | 1, 2, 3. Roughly 300 Gnani credits (my estimate from the per-character and per-second rates) | Persona and closed-script writing in parallel; the run after 1 to 3 |
| 6 | **Harden the Gnani finding** | A fresh frozen amounts set weighted to retail amounts; real-voice amount utterances from IndicVoices and Kathbath; v2.5 `literal` tested as a second reading from the same request; the minimal bug report for Gnani | Makes the lead finding held-out and real-voice. Lower than 5 because the finding already stands on its mechanism | Amounts report v2 with held-out and real-voice numbers (n at least 100 real utterances); the reproduction file | The user accepts the dataset terms | Yes, apart from the key |
| 7 | **Demo and submission** | The 60-second video above, a two-page brief, the written explanation, a last claims recheck | Last by dependency | The video; the brief; `check_quotes.py` clean | All | No |

## What to cut

- **Tamil and Kannada** from the call, prompts, demo and headlines. Keep the files, label them experimental, spend nothing more on them.
- **E1 as the headline, and the scripted yes/no arm as evidence.** Keep the hero pair as an illustration in the video. Throw the stratum table away once package 5 reports.
- **The "any flag means review" verdict** and the seven-statement disclosure. Both get replaced, not patched.
- **The KFS check, the dark-pattern slide, the SMS arm, the second product family, the retention setting.**
- **More synthetic noise conditions.** The sweep answered its question.
- **The after-fix amounts numbers** from any summary. They are in-sample.
- **Report volume.** Iteration 1 produced about 2,700 tests (by the reports' own counts) and work-package reports of up to 55 KB each for a product with no integrated call, and a 75 KB design in which the same caveat ("70 of the 1,604 frozen replies also appear in the development set") appears five times. No judge or interviewer will read it. In iteration 2 a package reports in two pages, and the first deliverable is a call someone can make.

Nothing in the code base should be deleted. The clients, the core, the extractor, the harness and the transport are a good base. What iteration 1 got wrong is the order: it proved every part before making one thing work for one person.
