# P5 report: unscripted customers, open call against a matched closed call (text path)

**Status.** This is **the held-out result on these 60 customers**. Run `text-2568759`: commit 2568759, 2026-11-13 04:23–04:38 UTC, 590 calls, 0 no-result. Settings: the call's default identity setting (no second check); the LLM turn classifier (`mistralai/mistral-small-3.2-24b-instruct`) with no wall-clock limit; extraction by `openai/gpt-6-luna`; no second STT reading (this run is text). Any rerun after fixes made in response to this run will be labelled "post-fix rerun of an evaluation already seen". **Independently recomputed** (all runs, including §9 and §10 in a recheck: 0 disagreements): an Opus-high verifier that wrote none of the code rebuilt every count, interval and p-value from the raw call files with its own script and found 0 disagreements in 228 table rows; it confirmed all frozen hashes and checked this report line by line (`references/reviews/iter3/verify-P5.md`). Its corrections to the first draft are applied here. **Later runs (§9, §10)** are on commit 3b64086, after fix rounds made in response to this run: §9 is a post-fix rerun of an evaluation already seen, not held-out; §10 is the first run on a fresh set (P5b). **Voice run: not done.** The coordinator withdrew it, because the account's single Gnani request slot is needed for the user's live calls. Only the 4-call smoke test (§6) exists.

## 1. The question
The question comes from contract §1. The customers' words were not written by the builders. Of 100 customers with a problem, how many does the open Samajh call fail to refer? Of 100 without one, how many does it refer? How does a closed confirmation call on the same customers compare? P5 replaces E1, which was true by construction. This run is the text path only. The voice comparison (§1.3) has not been run.

## 2. The arms, and what makes them matched
- **Open:** the Samajh call as built. **Closed:** ten record statements, each followed by "is that correct?". Both arms use the same customer, record, language and opening. Their replies were written from the same fact sheet, and both use the same disposition draw.
- **Disposition levels** 0, 0.25, 0.5, 0.75 and 1 set how often a customer gives way: `defer` in the open call, `go_along` in the closed call. The two kinds of giving way are not matched, so **the arms are compared only at level 0.**
- **The closed outcome rule is generous by design.** Anything but a plain yes counts as caught. So the closed arm's 0 misses, and its referral of every knowledge-gap customer (who says "don't know"), are largely true by construction. They are not a headline.

## 3. Result at level 0 (unit = customer; Wilson 95%; no clustering, contract §3)

**Customers with a problem (26).** An open miss is a call that ends `clear` or `understanding_gap`. A closed miss is `confirmed`.

| Kind | n | Open refer | Open miss per 100 | Open incomplete | Closed miss per 100 |
|---|---|---|---|---|---|
| misled | 14 | 13 | 0 [0–22] | 1 (C010) | 0 [0–22] |
| took_nothing | 4 | 4 | 0 [0–49] | 0 | 0 [0–49] |
| coached | 4 | 4 | 0 [0–49] | 0 | 0 [0–49] |
| uninformed | 2 | 2* | 0 [0–66] | 0 | 0 [0–66] |
| in_a_hurry, fraud_suspicion | 1 each | 1 each | 0 [0–79] | 0 | 0 [0–79] |

\*C015 is counted as caught, but her call ended as a third party partway through (§5H).

**Customers without a problem (20).** The table counts referrals. The closed column gives the primary reading, then the lenient one.

| Gold class, kind | n | Open refer per 100 | Open gap / clear / incomplete | Closed refer per 100 |
|---|---|---|---|---|
| no_problem, well_informed | 6 | 0 [0–39] | 0 / 1 / 5 | 100 [61–100]; lenient 0 |
| knowledge_gap_only, ordinary_informed | 8 | 12 [2–47] (C021) | 6 / 0 / 1 | 100 [68–100]; lenient 100 |
| knowledge_gap_only, uninformed | 4 | 25 [5–70] (C019) | 0 / 0 / 3 | 100 [51–100]; lenient 100 |
| knowledge_gap_only, in_a_hurry / fraud_suspicion | 1 / 1 | 0 [0–79] each | gap 1 each | 100 [21–100] each |

- No open call of a customer without a problem ended early at level 0. One problem customer's call did (C015, §5H); its tier was refer, and the scorer counts refer as caught however the call ended.
- All 27 open referrals rest on the customer's statement. None rests on the record alone.
- Writer model: no open misses for either writer. Open referrals of customers without a problem: 1 of 9 DeepSeek customers and 1 of 11 Gemini.
- **Why all 6 well-informed customers were closed referrals.** It is not the generous rule. Each one agreed with a statement worded in the negative, and the interpreter read that agreement as a no (§5G). The lenient reading, fixed before the counting run, refers 0 of 6.

**Paired comparison (exact McNemar, level 0).**
- Problem customers: both caught 25, closed only 1 (C010), open only 0; p = 1.0.
- Customers without a problem, primary reading: both referred 2, closed only 18, open only 0; p ≈ 8e-6.
- Same customers, lenient reading: both 2, closed only 12, neither 6; p ≈ 5e-4.

**Opening kinds** (open arm only):
- **Third parties:** 6 of 6 ended `wrong_party` [61–100]. The loan was named to 0 of them, and every one of these calls ended at the first or second turn.
- **Refusals:** 2 of 3 ended `declined` (C053, C054), and no refusal was asked a further question. C055 ended `not_confirmed` and his refusal was never heard (§5F).
- **Call back later:** 3 of 3.
- **Language switch:** 2 of 2 reached the switch, but C059 got there late (§5F).

**Terse condition** (open call with `go_along` replies, level 0, reported apart): 0 misses, with 5 problem customers ending incomplete (4 of 14 misled, 1 of 4 coached). 0 referrals of customers without a problem; all 20 ended incomplete (19) or early (1, C043).

## 4. Above level 0 (each arm on its own; no open-minus-closed difference)
- **Open arm.** Open calls end early more often as customers give way. Problem customers referred: 25, 17, 10, 5, 0 of 26 at levels 0, 0.25, 0.5, 0.75, 1. The others ended early (9, 16, 18, 21) or incomplete (0, 0, 3, 5). No problem customer ended `clear` or `understanding_gap` at any level. No customer without a problem was referred above level 0; 17 to 19 of the 20 ended early.
- **Closed arm.** Closed `confirmed` counts rise with the level. Problem customers: 0, 0, 0, 1, 14 of 26. Customers without a problem: 0, 0, 3, 7, 14 of 20.

## 5. Failures (open arm, level 0 unless stated; quotes as in the call files)

**A. The consent question asks two things, and the call never asks for the missing half (8 customers without a problem).** The question is "लोन लेते समय आपने किन-किन चीज़ों के लिए हाँ कही थी? और वो हाँ आपने किस तरह दी थी?" ("What did you say yes to, and how did you say it?").
- Eight answered only *how*, and each answer matches the record:
  - C029 "मैंने ब्रांच में फॉर्म पर दस्तखत किए थे।" (signed a form at the branch)
  - C030 and C034: clicked agree in the app
  - C031 "बैंक की रिकॉर्डेड कॉल पर हाँ कह दी थी।" (said yes on the bank's recorded call)
  - C032 "मैंने OTP से confirm किया था।" (confirmed by OTP)
  - C023: on a recorded call
  - C017 "मैंने बस कागज़ पर दस्तखत किए थे, जैसा उन्होंने बोला।" (just signed the paper as told)
  - C020 "App में box tick किया और agree दबा दिया।" (ticked the box in the app and pressed agree)
- The extractor's own prompt marks that half `unclear`: "only the way they agreed (\"yes, I gave the OTP\"), is \"unclear\"". The rules turn it into a `consent` `no_usable_answer` gap, and the tier becomes `incomplete`. Consent is the last question, so the call closes without asking again.
- On its own, this explains 6 of the 9 incomplete calls among customers without a problem: all 5 well-informed customers, plus C023.
- The same consent gap appears in 9 problem customers' calls: C004, C005, C014, C016, C040, C042, C044 and C038 ("App में loan screen पर accept click किया था.") answered only how; C037 is below. All 9 were referred on other grounds.
- Related: C037's "मैंने सिर्फ़ लोन के कागज़ों पर दस्तख़त किए थे।" (I signed only the loan papers) also became `unclear`. By that same prompt it should be "agreed only to the loan".

**B. Bundling: "don't know whether it was required" becomes a gap that makes the tier `incomplete` (C017, C018, C020; C019 was referred on another ground).** Examples:
- C017 "मुझे नहीं पता ज़रूरी था या नहीं" (don't know if it was required) … "किसी और कंपनी के बारे में कुछ नहीं बताया" (nothing said about another company)
- C018 "ज़रूरी था या अपनी मर्ज़ी से, मैंने पूछा नहीं था।" (I didn't ask whether it was required or my choice)

This is the documented gap between gold and code (`gold-rules.md`, last section). The code does what it was designed to do.

**C. Premium figures that could not be parsed.**
- C018 "बस कुछ हज़ार रुपये थे" ("just a few thousand"). Gold reads this as not knowing (a gap); the code reads it as `value_not_parsed` (`incomplete`). This case is not one of the three looser readings listed in `gold-rules.md`; it is a fourth difference.
- C010 "कुछ नहीं दिया जी, वो तो totally free था, zero rupees" (paid nothing, it was totally free).
- C016 and C019 ("कुछ हज़ार") were also unparsed; both were referred on other grounds.

**D. C010 is a misled customer who ends `incomplete`, not referred.** His payment answer "मैंने कुछ pay नहीं किया जी, bank ने ही भरा था।" (I paid nothing, the bank paid) fits neither source value (`from_loan`, `separately`). The `loan_funded` ground that gold rests on was therefore lost. The closed arm caught him: "नहीं, मुझे तो बोला था यह बिल्कुल free है।" (no, I was told it was totally free).

**E. Wrong referrals of customers who only have a knowledge gap (2).**
- C021 "यह पैसा वापस नहीं मिलता, बचत थोड़ी है।" ("this money doesn't come back; it's hardly savings"). This is correct knowledge, said with a colloquial negative, and it was read as "described the product as a deposit (FD)".
- C019 "बीमा के लिए हाँ कहा था, फोन पर।" (I said yes to the insurance, on the phone). The record says recorded call. The call read this as "agreed by word of mouth only" (`consent_method_differs`), so the fault is in how "on the phone" was mapped to a method.

**F. Opening.**
- **C055.** He said "हां भाई, मैं ही समीर हूँ. क्या issue है?" (yes, it's me, Sameer; what's the issue?) three times. Each time it was read as yes/`confirms_self`. The trailing question drew "purpose before confirm" and the direct identity question again. The call ended "हम Sameer जी से बाद में बात कर लेंगे" (we'll talk to Sameer later), outcome `not_confirmed`, and his refusal was never heard. Four frozen replies to this question end in a question (C048, C050, C051, C055); his is the only borrower's. It is scored as is.
- **C059.** "हाँ, पर मेरी हिंदी ठीक नहीं। तमिल में बोल सकते हैं?" (yes, but my Hindi isn't good; can you speak Tamil?) was read as yes at the go-ahead. The questions then ran in Hindi. The switch came only at customer turn 16: "हाँ, चलिए। तमिल में बोलिए।"
- Harness artefact in C059: the reply bank answers the cover read-back with "हाँ, सही है। नौ हज़ार।" (nine thousand), so the read-back was asked three times.

**G. Closed arm: agreeing with a negative statement is read as no.** Example: "हाँ, यह बचत नहीं है, पैसा वापस नहीं मिलता।" (yes, it isn't savings, the money doesn't come back). This happened in all 6 well-informed customers and in 11 of the 14 knowledge-gap customers.

**H. A borrower ended as a third party partway through the call (C015).**
- After "वो तो साहब ने काट लिया, मुझे नहीं पता कहाँ से।" (the officer cut it, I don't know from where), the call asked "क्या आप ख़ुद Kamla जी हैं, या उनकी जगह कोई और?" (are you Kamla herself, or someone in her place?).
- She replied "हाँ जी, कमला ही हूँ, बोलिए।" (yes, it's Kamla herself, go on). The classifier said `confirms_self`, but the call ended "हम Kamla जी से बाद में बात कर लेंगे".
- A reading of `who_check_claim`, not shown in the file: the call wants a first-person word such as "मैं", and her reply has none.
- The loan and premium had already been discussed with her.
- Her tier is still `refer`, on `funded_dont_know`. That is not one of gold's grounds (kind, consent, sale_conduct), and gold says she knows the premium was cut from the loan. The scorer counts her as caught.

## 6. Voice: a smoke test only, not a result
Four customers (C001, C006, C007, C048) on the open arm at level 0. Customer voices were Timbre TTS on a simulated 8 kHz line, with Batch off.
- All 4 calls produced ready case files. The third party (C048) ended `wrong_party` and was not told about the loan.
- **C006** (misled, not caught). "हाँ बिल्कुल, बोलिए, do-teen minute बात कर सकते हैं." (yes, go ahead, we can talk for two or three minutes). Prisma v3.0 heard it as "हाँ, बिल्कुल बोलिए 15 minute बाद कर सकते हैं।" (…can do it after 15 minutes). That was read as a possible refusal. The call asked whether to stop, the customer said carry on, and the same misreading came back on the re-ask (the same audio). The call ended `no_go_ahead`. On text, this customer was referred.
- **C001.** "यही लगभग चालीस-बयालीस हज़ार रुपये थे।" (about forty to forty-two thousand). v2.5 heard "यही लगभग ₹82,000 थे" while its literal kept the words; v3.0 heard "40,42,000". The readings disagreed and the call asked again. The premium ended `value_not_parsed`, so no wrong figure was kept. The tier was still `refer`.
- **C007.** STT punctuation turned two statements into questions: "कितने साल चलेगा? वो नहीं बताया" was read as a request to repeat. Still referred.
- In 3 of the 4 calls the tier matched the text run. In C006 the voice call ended incomplete where the text call referred.

## 7. What is and is not claimed (contract §8)
- **May claim:** the counts above with n, interval, arm, level and kind; "replies written by two outside models (Gemini 3.7 Flash, DeepSeek v4.1 Flash) from fact sheets the project wrote"; the paired comparison at level 0; above level 0, each arm on its own; the failures listed above.
- **Not claimed:**
  - real customers, a field rate or a prevalence;
  - a pooled rate;
  - any result on speech (this is scripted text);
  - "mis-selling found" (a referral is evidence for human review, never a finding);
  - any difference between the arms above level 0, or "the open call resists acquiescence";
  - "teach-back beats yes/no";
  - any Tamil or Kannada number (Hindi and Hinglish only).
- **Independence limits** (`data/p5/README.md`):
  - One author wrote all 60 situations, the records, gold, the topics and the closed script.
  - The topics paraphrase the bot's questions, and a bank cannot react to the bot's wording.
  - Every fact sheet settles every topic.
  - Gold was set by reading the rules, not by running them, and it is looser than the code.
  - No fluent person has read any reply.
  - Known reply faults: C011 and C016 deny taking anything; coaching is not voiced at level 0.

## 8. Reproduce
```
uv run python eval/p5/run.py --out eval/p5/runs/text-2568759 --arms open,closed,terse \
    --levels 0,0.25,0.5,0.75,1 --usd-budget 2.5 --workers 2      # 590 planned calls
uv run python eval/p5/score.py eval/p5/runs/text-2568759
```
- **Commit:** 25687594189883d246df1ce98072f3e812b982df. The frozen digests are in `manifest.json` and match `data/p5/FROZEN.json` (version 2).
- **Harness, sha256 first 12 hex (checked with shasum):**
  - `player.py` 3aac521140bc
  - `text_run.py` e4852255a650
  - `run.py` 2bcf82432620
  - `bank.py` 35cb5dd749c6
  - `score.py` 1582b88bad84
- **Note:** the `player.py` that ran is **not the committed one**. The commit's copy hashes a3c36e7dfff7. The working tree adds the `who_check`, `kind.ask_named` and `ack.neutral` mappings and a `verify.short` fix, and was saved before the run started.
- **LLM spend:** USD 0.22 (0.21646). The writers and the classifier are reproduced only from the local LLM cache (`.samajh/cache/openrouter`).

## 9. Post-fix rerun on P5 (an evaluation already seen)
Run `text-3b64086-postfix`: commit 3b64086, 2026-11-13 06:55–06:59 UTC, 590 calls, 0 no-result. The settings are the same as in the held-out run. **This is not a held-out result.** The fixes were made in response to §5, on these customers' replies. The improvements below show that the fixes work on those replies, and nothing more. The fresh check is §10.

Open arm, level 0. The columns give held-out 2568759, then post-fix.

| Customers | n | Held-out | Post-fix |
|---|---|---|---|
| Problem, all kinds | 26 | caught 25, incomplete 1 (C010) | caught 26 |
| no_problem, well_informed | 6 | clear 1, incomplete 5 | clear 6 |
| knowledge_gap_only, ordinary_informed | 8 | referred 1, gap 6, incomplete 1 | gap 8 |
| knowledge_gap_only, uninformed | 4 | referred 1, incomplete 3 | incomplete 3, ended early 1 (C017) |
| knowledge_gap_only, in_a_hurry / fraud_suspicion | 1 / 1 | gap 1 each | gap 1 each |
| Opening: third party / refusal / call back / language | 6 / 3 / 3 / 2 | 6 / 2 / 3 / 2 reached | 6 / 2 / 3 / 2 reached |

Customers whose open tier or outcome changed at level 0 (12):
- **C029, C030, C031, C032, C034 and C023 (§5A).** The answer that gives only *how* they agreed no longer leaves a consent gap. Five calls went from `incomplete` to `clear`, and C023 went to `understanding_gap`.
- **C010 (§5C, §5D).** Now `refer`, on "Customer said it cost them nothing" (`premium_said_zero`) and "Customer said they paid nothing for it" (`payment_says_not_charged`).
- **C021 (§5E).** The same reply, "यह पैसा वापस नहीं मिलता, बचत थोड़ी है।", is no longer read as a deposit: `refer` to `understanding_gap`.
- **C019 (§5E).** The consent-method ground is gone. The call still ends `incomplete`, because of the unparsed "कुछ हज़ार" and the bundling gap (§5B).
- **C055 (§5F).** He now passes the opening. At the go-ahead his refusal is heard: "मैं robots या automated calls से बात नहीं करता. disconnect करो call." (I don't talk to robots or automated calls; disconnect). The call ends `declined`.
- **Two regressions, both at the direct identity question:**
  - **C017:** "हाँ, मैं रामप्रसाद बोल रहा हूँ।", then "जी हाँ, मैं ही रामप्रसाद हूँ।" (yes, it's me, Ramprasad).
  - **C053:** "हाँ, भूपेंद्र बोल रहा हूँ। कौन?", then "हाँ भाई, मैं ही भूपेंद्र हूँ।".
  - Both calls end "हम … जी से बाद में बात कर लेंगे" (we'll talk to them later), outcome `not_confirmed`. C017's questions were never asked, and C053's refusal was never heard. §10 has the cause.
- Unchanged: C015 still ends as a third party at the mid-call who-check (§5H) and is still counted as caught; C059's switch to Tamil still comes only at turn 16.

Paired comparison at level 0: problem customers, both caught 26, p = 1.0. Customers without a problem, primary reading: closed only 19, neither 1 (C017, ended early in both arms). Lenient reading: closed only 13, neither 7; p = 0.0002. A closed call that ended in the shared opening never stated anything; it is counted as neither caught nor confirmed and stays in n and in the pairs.

## 10. Fresh check on P5b
Run `p5b-text-3b64086`: commit 3b64086, 239 calls, 0 no-result. P5b has 24 new customers (12 Hindi, 12 Hinglish). They were written after the P5 failures were known, by a builder and writer models that were shown nothing about those failures (`data/p5b/README.md`). **This is the first run on this set.** With 24 customers the intervals are very wide. Level 0, open arm, unit = customer, Wilson 95%:

- **Problem customers (12).** 0 misses: misled 0 of 6 [0–39], took_nothing 0 of 2 [0–66], uninformed and in_a_hurry 0 of 1 each [0–79]. 11 referred, 0 incomplete, 1 ended early: C016 (coached), at the opening. Closed arm: 0 confirmed under both readings; C016 again ended at the opening.
- **Customers without a problem (7).** 0 referred [0–35]; 3 `understanding_gap` (C007, C010, C011); 0 `clear`; 0 `incomplete`. 4 ended early at the opening (C009, C012, C013, C019). Both well-informed customers are among them, so this run says nothing about whether the open call clears a well-informed customer. Closed arm: 3 referred under both readings; the same 4 ended early.
- **Paired comparison:** problem customers, both 11, neither 1 (C016, ended early in both arms), p = 1.0. Customers without a problem: closed only 3, neither 4 (all four ended early in both arms), p = 0.25.
- **Opening kinds:** third party 2 of 2 [34–100], loan named to 0; refusal 1 of 1 [21–100]; call back later 1 of 1 [21–100]; language switch 0 of 1 [0–79] (C024; below).

**New fault: the direct identity question rejects a borrower who says their own name.** It ended **5 of the 19 P5b customers expected to complete the call at the opening (26 per 100, Wilson 12–49)**, plus P5 C017 and C053 (§9).
- **The replies** (each says the name in Devanagari; the record holds it in Latin script): C009 "जी हाँ, मैं ही ममता हूँ, बताइए।"; C012 "जी हाँ, मैं ही बलराम हूँ।"; C013 "हाँ, मैं ही रुखसाना हूँ।"; C016 "जी हाँ, मैं ही ओमप्रकाश हूँ।"; C019 "हाँ, मैं ही कुणाल हूँ।"
- **What the call did.** The classifier read every one as `confirms_self`. Every call still ended "… से बाद में बात कर लेंगे", outcome `not_confirmed`.
- **The cause** (checked offline on the pure functions at 3b64086; not recorded in the call files): `_is_name` does not match these Devanagari names to the Latin record names, though it matches some others (मीना/Meena, समीर/Sameer). So in "मैं ही <name> हूँ" the name counts as someone else's and `doubts_claim` returns True. The word order "<name> ही हूँ" still passes (P5b C007 "हाँ, मैं रविंद्र ही हूँ।").
- **What it costs.** A genuine borrower loses the call, and ops would retry it. No third party was told about the loan.

**A language request inside a yes is read as yes (P5b C024, as in P5 C059).** C024 said "हाँ, बात कर सकते हैं। मेरी हिंदी कमज़ोर है, Telugu में बात कर सकते हैं?" (yes, we can talk; my Hindi is weak, can we talk in Telugu?). It was read as yes; the call ran all its questions in Hindi and ended `completed`, tier `understanding_gap`.
