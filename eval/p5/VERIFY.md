# P5-prep: independent verification

Round 1, 2026-11-10. An Opus-high subagent that wrote none of the package; read-only; its report is saved below as returned. What was done about each item, and the re-check, follow at the end of this file.

## P5-prep verification report (independent verifier, read-only, no network calls)

### 1. Verdict: **sound with conditions**

The data are honest. The hashes, the freeze order, the rebuilds and the "no reply edited" claim all hold. The builders kept out of the forbidden paths.

Conditions, all to be met before any audio:
1. Fix the wording of the open-vs-closed disposition claim, or regenerate the open `go_along` variant (A2).
2. Record that gold's expected tier ignores the gaps left by an undecided answer (D1).
3. Say how P4 is scored on the 7 `hero` cards and on H-07 (D3).
4. Note the four smaller gaps: the perturbation suite, the 120-call bar, two topic paraphrases, and the README's independence section.

### 2. Failing and partial items

**A2 FAIL: the disposition curve is close to true by construction.**
- What is wrong: in the open call there is nothing to agree with, so the writers made an open `go_along` reply a shortened `own` reply that still states the belief. In the closed call, `go_along` is "हाँ, ठीक है". At a = 1 the open arm still hears every misbelief and the closed arm hears yes. The open–closed gap as `a` rises is therefore set mostly by the variant definition in `topics.json`. This is the judge's E1 objection again.
- Evidence: all 9 problem customers I read.
  - C001 `what_is_it` go_along: "एफडी है". Closed go_along: 10 of 10 yes.
  - C004 `money_back` go_along: "वापस मिल जाएगा interest के साथ".
  - C006 `money_back`: "one year बाद money back मिल जाएगा".
  - C041 `money_back`: "ब्याज समेत वापस मिलेगा".
  - C044 `what_is_it`: "Investment plan ही है".
  - C002, C010, C013 and C045 are the same.
- Smallest fix: add to contract §8 "May not": "that the open call resists acquiescence. In this bank an open-call go_along reply is a shortened own reply, so the open arm is nearly flat in `a` by construction; the curve measures the closed script's sensitivity to yes-saying." Alternatively, before audio and with a new freeze, generate an open acquiescence variant that carries no content ("जी, जो आप कहें", or the last option of an either/or question).

**A1 PARTIAL: the perturbation suite is dropped without saying so.** The judge's plan row 5 lists "a perturbation suite", and `P5-contract.md` never mentions it. Fix: one sentence saying it is outside P5 and where it lives.

**A3 PARTIAL: length.** The contract is 1,370 words with two tables, likely over two pages. Fix: trim.

**A4 PARTIAL: stage 2 alone is 106 voiced calls (60 open plus 46 closed).** That is under the judge's "at least 120", yet §7 says the run "can end early with a usable result". Fix: state that the judge's 120 needs stage 3.

**B2/B3 PARTIAL: overlaps and paraphrases.**
- The closed statement `c_source` "यह प्रीमियम आपके लोन की रकम में से काटा गया" matches the frozen scenario set's yes/no line `yn.payment.from_loan` over 10 tokens (`samajh/scenarios/phrases/hi.py:279`). The Hinglish line matches over 7 tokens (`hi_en.py:280`). It appears in 50 closed requests. The closed-script builder's transcript shows no access to the scenario files, so I judge the wording convergent, not leaked.
- C041's sheet ("personal loan of three lakh … after three years the money comes back with interest") echoes scenario B02 (`cases.py:1114`: personal, 300,000, "after three years the money comes back with…"). I judge it coincidence: no access in the transcript, nothing in the brief.
- No shared run of 6 or more tokens with `_lexicon.py`, `interpret.py` or any `samajh/dialogue` file.
- Topic `anything_else` ("whether … any amount was taken for something") is not the bot's `open_recall.nothing` ("did anyone talk to you about anything other than the loan?"). It invites the took-nothing customers to name the deduction, and gold's `kind` ground for C037 and C038 rests on that reply.
- `figure_read_back_wrong` and `benefit_read_back_wrong` tell the writer "your reply must say your own figure again". That gives parser-friendly replies such as C002 "नहीं, वो eighteen thousand five hundred था, अठारह हज़ार पाँच सौ".
- Fix: list both topics as known limits in the README.

**D1 PARTIAL: `gold-rules.md` bends DESIGN §6 and the code while saying it "adds no rule".**
- "Does not know whether required" is treated as no ground. The code gives a bundling gap (`samajh/rules/checks.py:599-600`), which is tier `incomplete` (`types.py:758`). So C017–C020 have `expected_tier: understanding_gap` where a correct run gives `incomplete`.
- The consent gap and the `loan_funded` gap from DESIGN become notes. This affects only C036, where they are unreachable anyway.
- The cover rule makes any hedged figure a gap, but the code passes an approximate figure near the record (`checks.py:377`). That affects the cover ground of C026 (400k–450k against 450k); the tier holds through `term`.
- `recall_unmatched` is missing from the table.
- Fix: say this in `gold-rules.md` and contract §5, and score tier only as refer or not refer.

**D2 PARTIAL: replies that contradict the sheet or gold.**
- C016: "नहीं यार, और कुछ तो नहीं लिया मैंने" is a firm denial, while the sheet says "cannot think of anything" and gold has `names_product_unprompted: false`. Its `how_paid` own reply asserts the money came from the loan and its `how_often` again reply asserts one payment; the sheet says he knows neither.
- C011: "नहीं, मैंने सिर्फ लोन लिया था। और कुछ नहीं लिया।" against gold `true`. I found this one by scanning all 46 completing customers.
- Both route the call into the took-nothing branch, so gold's `kind` and `loan_funded` grounds become unreachable. The tier would stay `refer`, but for the wrong reason.
- C015 `how_paid` own: "मुझे नहीं पता कहाँ से", while the sheet says it was "cut from the loan money".
- C040: the coaching is voiced only in a re-ask (`again`) reply, so at level 0 it is likely never heard.
- Fix: list these in the README as known reply faults. Do not edit them.

**D3 PARTIAL: P4 cards.**
- H-07 is an "ordinary informed" card with `expected_tier: refer`. The packaged `informed` record lists no `one_time_payment`, so a truthful "paid once" raises `belief_mismatch`.
- 7 of the 20 counted cards (H-01, H-03, H-05, H-14, H-15, H-19, H-20) are on `hero`, which has `consent: null`. Every completed call on them is `refer` from the record alone, so a miss is impossible on 3 of the 6 misled cards.
- Fix: score P4 on call grounds, not tier, or move these cards to the extra records.
- Minor: the phone's picker shows two "Meena …" records, both born 1991 (`amount-check` and `p4-meena`).

**F1 PARTIAL: README.**
- The last line is a stray "EOF".
- The independence section omits two things. The research agent behind RUNNER-PLAN Part 2 read `samajh/dialogue/{__init__,__main__,machine,prompts,llm_fallback}.py`, `data/prompts/hi.toml` and `eval/text_path`, and after its report the sub-orchestrator added the `want_a_person` topic. The sub-orchestrator itself read `data/scenarios/README.md`.
- The "not checkable" line is now checked (B5).
- Write "para 85Y (101Y for NBFCs)": 29 of the 60 records are NBFC loans.

### 3. What passed
- **A, contract content:** it states the question, the arms, what matches them, the unit, the counts per 100 by kind, gold, the freeze order and the budget. Choices are marked "(chosen)". No claims-ledger breach: a referral is evidence for review, and 85Z applies only where mis-selling is established.
- **A, cost:** the arithmetic adds up (94 + 73 + 18 + 19 = 204; 32 + 23 = 55; total about 260).
  - Measured open `own` text per completing customer is a mean of 584 characters (max 838) against the 700 assumed, so it is conservative.
  - Closed is about 78 by my reckoning against 73. Stage 3 measures about 45 against 55.
  - Not counted: the new lender name "नमूना फ़ाइनेंस", about 4 credits. "About 320 calls" is 290 unless the opening kinds are rerun at every level.
  - Everything stays inside the 300 stop. The ledger reads 288.54 spent.
- **B1:** none of the 89 open requests holds the loan id, lender, provider, surname, record premium or cover digits, or date of birth. None refers to the closed call. All 153 of 153 requests rebuild byte for byte.
- **B4:** no project vocabulary and no hint of the conclusion in the fact sheets. The `kind` and `underlying` fields are never sent.
- **B5:** tool calls per builder: fact sheets 24, writer script 37, P4 cards 16, blind labeller 5. Zero touch a forbidden path. The blind labeller read only its two files.
  - Indirect only: `build_customers.py` and `write_customers.py` import `samajh.server.records`, which loads `samajh.dialogue`, `samajh.rules` and `samajh.extract` into the process without calling them.
- **B6, gold frozen before the words:**
  - The freeze is at 12:14:20Z, and `customers.jsonl` and `gold.jsonl` have that mtime. The first P5 writer request is at 12:14:50Z.
  - All 153 P5 request cache keys first appear after the freeze, with 0 cache hits.
  - Of 17 writer-model calls before the freeze, 10 match the smoke files and 5 are cached replies about the invented Ramesh and Mahesh. The other 2 (qwen) cannot be checked.
  - `frozen_problems` on a scratch copy refuses on an edited gold file, an edited record, an extra record, an unlisted topics file and a missing FROZEN.json. The 11:58Z transcript shows a live refusal.
- **C, reproducibility:**
  - All 11 FROZEN digests match my own code.
  - `build_customers.py` run in scratch reproduces customers, gold and 60 records byte for byte. `render-closed` reproduces the closed statements.
  - `build_cards.py` run in scratch reproduces all 28 outputs.
  - `load_book` gives 8 ids with the card records and 64 with the P5 records, with no error.
  - 120 of 120 reply arms equal a cached model output exactly, so no reply was edited.
- **D, P5 sample:** I labelled 17 customers myself: C002, C010, C015, C016, C040, C036, C037, C038, then a seeded draw of C047, C056, C029, C024, C055, C059, C045, C043, C013. Gold agrees with my labels on class, outcome, tier and grounds in all 17. There are no digits in any of the 4,380 replies.
- **D, P4 cards:** the type mix is 6/4/3/2/2/1/1/1 plus 4 spares, split 12 Hindi and 12 Hinglish. Every card names a picker label that resolves and gives the record's year of birth. No gold or project words appear. Every card matches its gold file.
- **E, safety:** no phone, Aadhaar, PAN or account patterns (the long numbers are timestamps in generation ids). `.samajh-human/` is gitignored. The transcripts wrote only to `data/p5`, `eval/p5` and `.samajh-human/cards`, nothing under `samajh/`, `tests/`, `web/` or `data/prompts`. No Gnani call: the transcripts ran only `--help` and `--dry-run`, and the 169 Gnani rows after 11:50Z match no P5 command.
- **F:** every README count I rechecked is true: kinds, tiers, writer by language (15 each), 53 + 20 replies, 32 regenerations in 18 customers, 13 kept failures in 7, grounds 12/10/9/9/7/7/4, the record mix, 108 + 12 birth-year replies, C005 "compulsory". The blind labelling agreed 60 of 60 on class and tier, with differences on 7 customers (5 refer, 6 gap), as the CHANGELOG says.
- **F, RUNNER-PLAN spot checks:** all five hold, and Part 1 follows from them.
  - `records.py:94-97` reads `SAMAJH_RECORDS_DIR`.
  - `client.py:177-182` and `:480-483`: the cap override, applied to the whole ledger.
  - `casefile.py:348-395`: extraction is not nested under Batch, and a Batch failure makes the case `failed`.
  - `app.py:379-390`: `bot_json` drops tags, while `:1161-1164` (the session read) keeps them.
  - `app.py:775`: only a `samajh` call gets a case file.
- **F, topic coverage:** `figure_read_back_wrong` and `benefit_read_back_wrong` fire only after a mishearing, so never on the text path. `bridge.moving_on`, `end.do_not_call` and `end.written` are new keys with no mapping; the planned mapping test would catch them.

### 4. Not verified
- The STT seconds per character. I assumed about 12–13 characters a second; no audio was measured.
- The content of the 2 qwen calls before the freeze (there is no cache file).
- The sub-orchestrator's message context. I scanned its tool calls, not its messages.
- The README's "312 of 322 figures agree" and its exact "45 of 460", which I did not recount; my word search is consistent with them.
- Hindi naturalness is my own reading, not a native reviewer's.

### 5. Wording for the project's documents
**Allowed:**
- "60 synthetic customers whose replies were written by two outside models (Gemini 3.7 Flash, DeepSeek V4.1 Flash) from fact sheets."
- "Gold was set and frozen by hash before any reply existed; an independent verifier reproduced every hash and rebuild, and found no reply edited."
- "The builders of the sheets, the writer script and the cards did not open the dialogue, rules, extractor, prompts or scenario set, checked from their transcripts."
- "Prepared, not run; no audio; no person has reviewed sheets, gold, replies or cards."

**Forbidden:**
- "Independent customers" or "real customers".
- "The open call resists acquiescence", or any reading of the disposition curve beyond the closed script's sensitivity to yes-saying, unless A2 is fixed.
- "The writers saw no bot line" without "topics paraphrase the bot's questions".
- "Gold follows the product's rules exactly" (D1).
- Any P4 miss rate on `hero` cards counted by tier.
- Any pooled rate, any prevalence, "mis-selling found", any Tamil or Kannada figure.

Scratch scripts, all in `/private/tmp/claude-501/-Users-masterpanda-projects-gnani-voice-ai-challenge/0f1feab6-71f2-48d8-9bc4-44a057cbe838/scratchpad/verify/`: `keys.py`, `frz.py`, `ngram.py`, `tx.py`, `tx2.py`, `show.py`, `edited.py`.
