# P5-prep: independent verification

Round 1, 2026-11-10. An Opus-high subagent that wrote none of the package; read-only; its report is saved below as returned. What was done about each item, round 2 and what was done about it follow at the end of this file.

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

---

# What was done about round 1's items

Written by the resumed P5-prep sub-orchestrator, 2026-11-10 late evening, from the disk and from round 2's findings (the first worker stopped at a usage limit before writing this section).

| Item | What was done | Round 2's finding |
|---|---|---|
| A2 | Version 2: a `defer` variant for the open call (840 replies, `topics.json` `open_defer`, a new freeze); contract section 8 forbids "resists acquiescence" | Partial: see round 2 below; then fixed in the contract's wording (arms compared at level 0 only) |
| A1 | The contract names the perturbation suite as outside P5 | Fixed |
| A3 | Contract trimmed from 1,370 to 1,267 words | Failed (1,331 words after tonight's additions); then trimmed to 1,192 words: two pages at 10 pt on A4, three at 11 pt (rendered and counted) |
| A4 | The contract says the judge's 120 voiced calls need stage 3 | Fixed |
| B2/B3 | Both topic paraphrases and both overlaps listed in `data/p5/README.md` Known limits | Fixed |
| D1 | `gold-rules.md` lists where it is looser than the code; the tier is scored only as `refer` or not | Fixed |
| D2 | Reply faults listed in the README; none edited | Partial: coaching unvoiced was not listed; then added |
| D3 | Cards rebuilt: 5 of 7 `hero` cards moved to extra records, H-07 moved to `p4-mohan`, the second Meena record removed | Partial: H-01 kept a stale ground; then no card is on a packaged record (below) |
| F1 | Stray "EOF" removed, independence section extended, "85Y (101Y for NBFCs)" | Fixed except this section, now written |

# Round 2, 2026-11-10 late evening

A second Opus-high subagent that wrote none of the package; read-only, no network. It checked the state after round 1's fixes and after tonight's edits for changed facts (runner plan Part 0, contract section 7, two datasheet sentences, three card index notes). Its report, as returned:

## 1. Verdict: **sound with conditions**

The data are intact and reproducible. The one real design problem: above level 0, the comparison between the open and closed arms is still set mostly by how the reply variants were defined. Some documents also make claims that are false or out of date.

Conditions:
1. Contract §1 Q2 and §8: limit the open-vs-closed claim to level 0 (A2). **Before any audio.**
2. README: list the unvoiced coaching, and correct the `defer` content counts (A2, D2). **Before any audio.**
3. Trim the contract to two pages (A3). Before any audio.
4. Write the "what was done about each item" section that `VERIFY.md` and the README promise, or delete the claim (F1). Before any audio.
5. P4 only, before any human call:
   - remove H-01's stale gold ground (D3);
   - stop the phone's on-screen record note from contradicting or leaking to speakers on H-01, H-08, H-14, H-16 and H-17 (F).

## 2. Failing and partial items

**A2 PARTIAL: above level 0 the comparison is still set by how the variants were defined.**
- The `defer` reply carries no content by definition. Contract §8 now forbids "resists acquiescence" as a discovery.
- But §1 Q2 still asks how the arms compare "as the customer's readiness … rises". §8 "May" still allows "how each arm moves as `a` rises", with no caveat.
- The two "giving way" variants are not matched:
  - closed `go_along` replies carry a no or "don't know" in 77 of 600 cases ("नहीं, सालाना है" C008 c_frequency; "पता नहीं" ×5 C012; "अरे नहीं, ऐसा तो नहीं था" C006);
  - so at a = 1 the closed arm still catches problem customers through content: C002, C004, C006, C008, C012, C015, C016, C035, C036, C044;
  - the open arm cannot, by definition, and §4 shows open `incomplete` apart from misses;
  - so a table of misses by level puts the open arm near 0 and the closed arm high, by construction.
- My draw of `defer` replies (seed `p5-verifier-round2-2026-11-10`): 160 random, plus every reply of C003, C023, C029, C052 and C055. That is 230 replies, with all four model × language cells at 37 to 43.
  - Product name, figure or "I don't know": 0. C051 "मैं कुछ नहीं कह सकती" is borderline.
  - Content about the matter: 6.
    - Clear: C003 `how_often` "वो तो चलता रहता है" (implies the payment recurs); C003 `anything_else` "हाँ, हाँ, वो तो चलता रहता है".
    - Weak: C003 `can_cancel` "वो सब हो जाएगा"; C003 `how_paid` "वो सब हो जाता है"; C024 `how_paid` "कुछ नहीं"; C024 `where_to_take_it_from` "ये सब चलता रहेगा".
  - An assent word (हाँ, जी, ठीक): 43 of 230. 7 of those are on questions where it reads as a yes: C004 `can_cancel` "ठीक है, आगे बोलिए"; C023 `can_cancel` "अच्छा, ठीक है"; C010 `anything_else` "हां हां ठीक है"; C005 and C003 `what_did_you_take`.
- Across all 840 `defer` replies, 140 contain an assent word. The CHANGELOG and README say "3 carry content … about 14 more borderline", which understates it.
- Fix:
  - §1 Q2: "at level 0, paired; above it, each arm's own behaviour".
  - §8 "May not": "any difference between the arms above level 0 as a measured advantage of either arm. Both variants are defined by the project (the open `defer` has no content; the closed `go_along` is mostly yes but says no or 'don't know' on 77 of 600). Above level 0, report only the end states of open calls (`incomplete`, ended early, wrongly `clear`, wrongly `refer`) and the closed `confirmed` count."
  - Mark the `defer` definition **(chosen)**.
  - Correct the README counts.

**A3 FAIL: length.** The contract is 1,331 words: 1,267 at HEAD, plus 64 tonight. With headings and a table that is roughly 2.4 pages. Fix: move §7's "Smaller run" and "Outside this contract" sentences (about 110 words) to RUNNER-PLAN Part 0. Shorten the header's provenance and §5's two limits to one line each, pointing to `gold-rules.md`.

**D2 PARTIAL: a fault the README does not list.** Coaching, which carries the `sale_conduct` refer ground, is never voiced in any `own` or `again` reply of C039, C041 or C042. C040 voices it only in `again`. So 0 of 4 coached customers voice it at level 0. Their tier comes from other grounds. Fix: add to the README's Known limits: "the `coached` rows measure the other grounds, not detection of coaching; 3 of 7 `sale_conduct` grounds are never voiced."

**D3 PARTIAL: H-01 has a stale ground.**
- H-01's gold holds the call ground `belief_mismatch` with "says it was paid once; record: hero has features [] (no one_time_payment)".
- Commit 403c48c (21:31) changed `hero.json` to `"features": ["one_time_payment"]`.
- `build_cards.py`'s constant `HERO_SINGLE` (line 109) still asserts the old record, and `INFORMED_SINGLE` is stale too.
- H-01 is scored on call grounds only, so this false ground counts.
- Fix: remove the ground and rebuild.

**F PARTIAL: the phone's record note.**
- `web/phone.js:930` shows `r.description` on screen, in HEAD and in the working tree.
- On `hero` it reads: "who believes what he bought with the loan is an FD … a case flagged for review". H-14's speaker plays a man who took nothing, and both H-01 and H-14 see the expected outcome.
- On `informed`, H-08 sees "Shows a call that ends with nothing to review".
- On `third-party`, H-16 and H-17 see "Shows the call ending before the lender or the loan is named".
- INDEX.md handles this only for S-04.
- Fix: have the operator pick the record and cover the note, or move these cards to extra records with neutral descriptions.
- Lesser points:
  - H-17 gives the speaker an exact phrase aimed at a known weakness ("answer out of habit with something like 'yes, tell me, who is this?'"), against USER-GUIDE's "No script for the speakers".
  - H-14 and H-15 reveal the bot's follow-up question.

**F1 PARTIAL.** `VERIFY.md` line 3 and README line 29 claim a "what was done about each item" section. It does not exist. The other F1 fixes are done.

## 3. What passed (my own counts)

- **A:** all required elements present; choices marked **(chosen)** except `defer`; A1 and A4 fixed. The ledger sums to 310.79 credits over 7,604 Gnani rows, so 689 remain. Stage arithmetic: 94 + 73 + 18 + 4 + 19 = 208 ≈ 210; plus 55 gives 263 ≈ 265. Smaller run: 94 + 18 + 4 = 116, plus 19 = 135. LLM spend: 418 × 0.0021 ≈ USD 0.88, plus at most 0.3. No claims-ledger breach.
- **B:** B2/B3 and D1 fixed. D3 fixed except as above: only H-01 and H-14 on `hero`; H-07 on `p4-mohan` (`one_time_payment`, 32,000), gold consistent; the duplicate Meena record gone.
- **C:** 0 of 153 open or `defer` requests hold the loan id, record id, lender, provider, surname, full birth date, `kind`, gold words or anything about the closed call (the fact sheets give the birth year only). Shared runs of 6 or more tokens, against 41 files (`samajh/dialogue`, `data/prompts`, `samajh/rules`, `samajh/extract`, `data/scenarios`, `samajh/scenarios`): the 11-token `c_source` closed line (known); "OTP, PIN, password or account number" (the `year_of_birth` paraphrase; English glosses in `ta.toml` and `kn.toml`); "the money comes back with interest" (`samajh/extract/_prompt.py`); C041 ~ scenario B02; "as long as the loan runs" (`normalise.py`). 217 of 217 requests rebuild byte for byte with the script's own functions. 64 of 64 `defer` requests went to the model that wrote that customer's open replies.
- **D:** 11 of 11 digests match. Version 1 replies (the `defer` additions removed) give `ba71c73e…`; the first 153 requests give `7a002d57…`; both match the history. A scratch rebuild reproduces customers, gold, 60 of 60 records and `closed_statements.jsonl`. Every frozen file equals HEAD. 180 of 180 reply arms equal a cached model output (215 of 215 generation ids found). Timeline: v1 inputs frozen 12:14:20Z; first request 12:14:50Z; last v1 request 12:29:42Z; v1 words frozen 12:30:38Z; v2 inputs frozen 13:04:37Z; `defer` requests 13:06:12–13:09:48Z; v2 words frozen 13:11:36Z. Audio: of 4,373 P5 texts, searched under 13 voices, 2 models, 5 language codes, 5 sample rates and 2 containers, 3 are in the TTS cache, all generic phrases that appear verbatim in other packages' files, so I found no P5 audio. `gold-rules.md` was changed after gold was frozen, but per the transcript only its first sentence and an appended section changed; the table is unchanged.
- **E:** seed `p5-verifier-r2-E-2026-11-10`, 16 customers, every kind covered: C006, C011, C018, C021, C025, C026, C034, C035, C039, C042, C044, C046, C052, C054, C057, C060. Labelled blind, 16 of 16 agree with gold on class, outcome, tier and both ground sets. I read 444 replies. Faults: C011's denial (already listed), coaching unvoiced in C039 and C042, and a weak C039 `how_long` `again`. Nothing else contradicts a sheet. Kinds, languages and every datasheet count recheck exactly. The judge's kinds are all present.
- **F:** 24 of 24 labels resolve to exactly one record (11-record book); name and birth year match; gold record and language match. Mix 6/4/3/2/2/1/1/1, languages 10/10, spares 2/2. All 18 completing cards cover every topic on USER-GUIDE's list. No real-looking identifier on a card (H-19's gold cites a public Ombudsman award number, which is in the claims ledger). `samajh.rules.evaluate` on a truthful, fully informed customer: 7 of 7 extra records and 60 of 60 P5 records come out `clear`; controls: `hero` `refer` (consent, loan_funded), `informed` `clear`. `build_cards.py` reproduces every output byte for byte.
- **G:** 14 statements of the runner plan checked, all true (readings order; `create_app(dialogues, records, profile, batch, state)`, `samajh_factory`, `prefetch`; `replay --dialogue {samajh, stub}`, `call.json` `"dialogue"`, `--no-case`, `--state`, the shared lock; `degraded`, `degraded_turns`, `speaker_confirmed`, `acted_on`, `dialogue_reads_first`; `SAMAJH_LLM_USD_CAP` default 1.0, `GNANI_CREDIT_CAP`, `wilson`, `mcnemar_exact`; non-samajh calls get no case file; a failed Batch makes the case failed; 64 records load with no duplicate label). The plan contains no code that calls Gnani. One note: a 1.3× stage tolerance on stage 2 alone (273) leaves stage 3 short under the 300 stop.
- **H:** no phone, PAN, Aadhaar or account pattern; long numbers are generation timestamps. `.samajh-human/` is gitignored and absent from git. Writes stayed in the allowed paths. Tamil appears only as C059's spoken request, written in Devanagari.

## 4. Not verified
- Whether tonight's research agent for Part 0 opened `samajh/dialogue`.
- How the dialogue reads the `defer` assents (the dialogue is changing).
- STT seconds and the credits for name lines.
- Topic coverage against P2-contract §5 (I checked USER-GUIDE's list).
- Hindi naturalness.

## 5. Wording

**May say:**
- "60 synthetic customers; replies written by two outside models from fact sheets; gold frozen by hash before any reply; an independent verifier reproduced every hash and rebuild and found no reply edited."
- "Prepared, not run; no audio; no person has reviewed sheets, gold, replies or cards."

**May not say:**
- Any open-vs-closed difference above level 0 as an advantage, or "the open call resists acquiescence".
- "Coached customers are caught for being coached."
- "The writers saw no bot line" without "the topics paraphrase it".
- "Gold follows the code exactly."
- "Independent customers" or "real customers".
- A pooled rate, a prevalence, "mis-selling found", or a Tamil or Kannada figure.

(Sections 3 and 4 above are condensed into single paragraphs per letter; sections 1, 2 and 5 are as returned. The verifier's scratch scripts were in the session scratchpad and are not kept.)

# What was done about round 2's conditions, and what no one has checked

**Nothing below has been independently verified: the coordinator stopped the package before the re-check.**

1. **Contract, claim limited to level 0:** done in sections 1, 2, 3 and 8 of `references/pilots/P5-contract.md`; `defer` marked (chosen). Runner plan Part 0 item 13 tells the scorer not to print an open-minus-closed difference above level 0.
2. **README:** the unvoiced coaching and the corrected `defer` counts are in Known limits; `CHANGELOG.md` has a correcting entry (the earlier entry is not rewritten).
3. **Contract length:** 1,192 words; two pages at 10 pt on A4 with 20 mm margins, three at 11 pt (rendered in headless Chrome and counted). The smaller run and the out-of-budget items moved to runner plan Part 0 (items 9 and 11).
4. **This section and the table above:** written.
5. **P4 cards:** an Opus-medium builder edited `build_cards.py` and rebuilt. By its report (not re-checked): no card is on a packaged record; H-01, H-08 and H-14 are on a new record `p4-deepak` and H-16 and H-17 on a new record `p4-savitri` (9 extra records now); H-01's stale ground and the `hero` record grounds are gone; H-14, H-15 and H-17 no longer hint at the bot's next question or hand the speaker a line; S-04's note about the screen is dropped; 17 cards and 19 gold files are byte-identical to before; the mix is 6/4/3/2/2/1/1/1 with 10 Hindi and 10 Hinglish, spares 2 and 2.

**Still to check (the skipped re-check):** the five moved cards against their new gold and records (H-01, H-08, H-14, H-16, H-17), the two new records under the rule engine, and that every label resolves to one record; the contract's new wording and length; the README and runner plan additions. **Open on the cards:** H-20's "On this call" paragraph still gives the speaker a quoted line ("yes, yes, all fine, it was all explained"), the same fault as H-17's; H-01, H-08 and H-14 share one record. **Not checked by anyone:** whether tonight's research agent opened `samajh/dialogue` (its brief forbade it); topic coverage of the cards against `P2-contract.md` section 5 after the dialogue's current fix round.

