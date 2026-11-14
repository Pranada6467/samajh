# ACQ report: the open call against a yes/no call, with recognition bias and acquiescence (text path)

**Status.** The one counted run of the plan frozen in `data/acq/FROZEN.json` (`eval/acq/PLAN.md`). Run `eval/acq/runs/counted`, 2026-11-14 IST, from a clean `git archive` snapshot of commit 9c67da6 (the shared worktree's uncommitted `samajh/dialogue` edits were not in it). The source-tree sha256 over `samajh/` and `data/prompts/` is `3e716a3abfe9…`. 800 open calls and 4,000 closed answer sets; 0 no-result, 0 entry failures, 1 degraded turn. Independent recompute: section 7. Full tables, every cell and kind: `eval/acq/runs/counted/tables.md` (and `scores.json`).

**Verdict.** On synthetic text, the open call turned 45 of 48 customers' own "don't know" into an understanding gap on the right field and referred 80 of 80 problem customers (misled, with or without gaps) on their ground. A yes/no call confirms those knowledge gaps whenever customers say yes to what they cannot recall: at a = 0, r = 0.5, 16 customers were found only by the open call and 3 only by the closed call, of 48 (exact McNemar p = 0.004). But that contrast is arithmetic on the harness's assumed recognition bias; only the open side was measured. When customers give way to the lender as readily in the open call as in the yes/no call, the open call found one false belief the yes/no call confirmed (C126, said in another field's answer). At a = 0.5, r = 0, ground-matched referrals were 44 open against 55 closed, of 80. 1 pair was open-only and 12 closed-only, and all 12 came after the open call ended `declined` on a reply such as "आप records में देख लीजिए" ("check your records"). The symbolic yes/no call cannot end early, by construction.

## 1. Set-up in one paragraph
There were 160 synthetic customers: 80 Hindi and 80 Hinglish, 32 informed, 48 knowledge_gap, 40 misled and 40 misled_with_gaps. Each had a lender record and a belief per field (correct, false or "don't know"). Two outside writer models wrote each customer's own words from the belief alone, never seeing the record: `google/gemini-3.7-flash` wrote for 80 customers and `deepseek/deepseek-v4.1-flash` for 80. Recognition bias r and acquiescence a run over {0, 0.25, 0.5, 0.75, 1}, and every customer is played in every cell.
- **Closed arm.** Ten record statements, answered symbolically: a false field gets a yes if u_a < a, a "don't know" field gets a yes if u_r < r. Strict rule: the call is confirmed only on ten yeses.
- **Open arm.** The Samajh call as built. It is entered with a fixed reply that never says the name, and scoring starts at open recall. The customer defers on field f if u_a(f) < a, with the same draw as the closed arm (the closed arm uses this draw on false fields only; on "don't know" fields it uses u_r, so those fields are not matched between the arms).
- **r never reaches the open arm**, because no bot line states a record value.

## 2. a = 0: what the open call does with customers who answer for themselves
Unit = customer, Wilson 95%.

| Kind (n) | Open | Closed, strict |
|---|---|---|
| misled (40) | refer 40, all on a gold ground, all on the customer's words | caught 40 at every r |
| misled_with_gaps (40) | refer 40, all on a gold ground | caught 40 at every r |
| knowledge_gap (48) | gap found 45 (93.8 [83.2–97.9]); refer 1 (C018); turn limit 2 (C010, C047) | gap found 48 / 41 / 32 / 21 / 0 at r = 0 / 0.25 / 0.5 / 0.75 / 1 |
| informed (32) | clear 28 (87.5 [71.9–95.0]); understanding_gap 2 (C005, C073); incomplete 1 (C092); turn limit 1 (C014) | caught 0 (by construction) |

**Primary test H1** (knowledge_gap customers, a = 0; b = found only by the open call, c = found only by the closed call). **H1 holds in all three pre-declared cells.**

| r | b | c | both | neither | p |
|---|---|---|---|---|---|
| 0.5 | 16 | 3 | 29 | 0 | 0.0044 |
| 0.75 | 25 | 1 | 20 | 2 | 8.0e-7 |
| 1 | 45 | 0 | 0 | 3 | 5.7e-14 |

The closed column is arithmetic on the draws (`PLAN.md` §6), so this table is not a measured contrast between two calls. The measurement is the open column: of 48 customers who said "don't know" in their own words, the call turned 45 into an understanding gap on the right field (46 of 48 had every dk field flagged). The same 48 customers appear in the scorer's primary table twice (by kind and by class); that is one test per cell, not two.

## 3. a > 0: giving way, matched by the same draw
Open arm (it does not depend on r), counts out of n:

| a | Problem (80): refer on ground | incomplete | ended `declined`, not referred | Knowledge gap (48): found | incomplete / declined | Informed (32): clear | incomplete / declined |
|---|---|---|---|---|---|---|---|
| 0 | 80 | 0 | 0 | 45 | 0 / 0 | 28 | 1 / 0 |
| 0.25 | 59 | 8 | 13 | 9 | 28 / 8 | 4 | 20 / 3 |
| 0.5 | 44 | 9 | 27 | 3 | 26 / 16 | 0 | 23 / 8 |
| 0.75 | 20 | 28 | 31 | 0 | 28 / 18 | 0 | 21 / 11 |
| 1 | 0 | 37 | 42 | 0 | 24 / 23 | 0 | 18 / 14 |

No problem customer ended `clear` or `understanding_gap` at any a (0 silent misses).

Closed arm, strict, problem customers confirmed (a miss), out of 80:

| r \ a | 0 | 0.25 | 0.5 | 0.75 | 1 |
|---|---|---|---|---|---|
| 0 | 0 | 5 | 13 | 25 | 40 |
| 0.5 | 0 | 7 | 15 | 31 | 52 |
| 1 | 0 | 12 | 25 | 54 | 80 |

**H2** (false beliefs under acquiescence; ground-matched referrals, problem customers, r = 0). It was declared before the run to fail by construction, and it failed in the other direction; the closed arm's advantage here is the harness's: it asks all ten statements and never ends early:

| a | b | c | p (descriptive) |
|---|---|---|---|
| 0.25 | 1 | 10 | 0.012 |
| 0.5 | 1 | 12 | 0.003 |
| 0.75 | 0 | 6 | 0.031 |
| 1 | 0 | 0 | 1 |

The closed arm catches a false field the customer did not give way on, even after giving way on another field. The open call often ended at the first deferral: all 80 `declined` endings at a = 0.25 and 0.5 (all 160 customers) come straight after a defer reply. Raw `declined` outcomes of problem customers, referred or not: 15, 30, 32, 42 at a = 0.25 to 1. **The one open-only b** is C126 (misled_with_gaps; false: kind = deposit, money back), at a = 0.25 and 0.5. Both false fields were deferred, so the closed arm confirmed. The consent reply, not deferred, says "मैंने loan के साथ FD के लिए हाँ कही", which gave `feature_contradicted` on the money-back ground. That is a leak through another field's answer, the exception `PLAN.md` §6 item 2 named. P2b's other open-only pair (C079 at a ≥ 0.75, r ≥ 0.75) is a `consent_method_differs` referral from a **defer** reply that contradicts its belief: "जो साइन किया है, वही मेरी मंज़ूरी है।" (record and belief: OTP). The same fault in C100's defer "जो मैंने साइन किया, वही।" (record: digital click) gives the one knowledge-gap referral at every a > 0.

**H3** (visibility) was decided before the run. Every open call at a ≥ 0.5 has a deferral and ends non-clear. That holds for problem customers (P3 b = 13 to 80, c = 0) and equally for informed ones (0 of 32 clear at a ≥ 0.5). It shows nothing that separates problem customers from the rest.

## 4. Failures, with quotes (a = 0 unless stated)
- **A deferral is heard as a refusal and ends the call** (80 of 80 `declined` endings at a = 0.25 and 0.5): "आप records में देख लीजिए।" (8), "आप अपने रिकॉर्ड में देख लीजिए।" (7), "आप फाइल में देख लीजिए।", "आप system में check कर लीजिए।". The questions after it are never asked, which is why the closed arm wins H2's pairs.
- **A payment-frequency loop to the turn limit** (C010, C014, C047 at a = 0; 11 calls across 4 customers in the run, C030 losing the cover question to it). "दोबारा किसी ने नहीं माँगा" ("nobody asked again") is read as `asks_repeat`, and "फिर कभी नहीं देना पड़ा" ("never had to pay again") as `call_later`. The bot asks when to call back, the customer's fixed "अभी बात कर लीजिए।" sends it back to the re-ask, with 25 or 26 call-later readings per call (`payment_frequency.reask` ↔ `callback.when`) until `turn_limit`. The fixed callback reply is a harness choice; the two misreadings are the call's.
- **"As long as the loan" is not parsed as a term** (9 of 56 such replies at a = 0; informed C005 "जब तक मेरा लोन चलेगा, तब तक रहेगा।", C073): `term` `value_not_parsed`, so tier `understanding_gap` for a customer who knows the term. The gold assumed this reply gives the term; in 9 of 56 such replies the extraction did not.
- **A consent answer with both halves read as unusable** (informed C092): "loan के साथ insurance को हाँ कहा, OTP phone पर आया था।" became `consent` `no_usable_answer`, tier `incomplete`.
- **An off-record recall referral** (knowledge_gap C018). The recall reply "insurance लिया था, पर कितने का था वो याद नहीं" was read as don't-know, so the bot took the took-nothing branch. The follow-up "लोन के साथ एक बीमा लिया था" then gave `recall_off_record` (refer), which outranks the right `premium_dont_know` and `cover_dont_know`.
- **Writer faithfulness.** None of the replies in the 7 calls behind the a = 0 misses contradicts its belief (the checker read each). Of the 160 consent `defer` replies in the knowledge file, 58 name a consent method by a word match, and 2 contradict their belief (C079, C100, above). Defer replies are played only at a > 0.

## 5. By writer and language
At a = 0 (counts only, no test; full table in `scores.json` "breakdown"):

| | Problem: refer | Knowledge gap: understanding_gap / refer / ended early | Informed: clear / understanding_gap / incomplete / ended early |
|---|---|---|---|
| Gemini | 40 of 40 | 23 / 1 / 0 of 24 | 14 / 2 / 0 / 0 of 16 |
| DeepSeek | 40 of 40 | 22 / 0 / 2 of 24 | 14 / 0 / 1 / 1 of 16 |
| Hindi | 40 of 40 | 21 / 1 / 2 of 24 | 14 / 2 / 0 / 0 of 16 |
| Hinglish | 40 of 40 | 24 / 0 / 0 of 24 | 14 / 0 / 1 / 1 of 16 |

## 6. What may and may not be said
- **May:** the counts above with n, cell, kind and arm. "On synthetic Hindi and Hinglish text written by two outside models from beliefs alone, at a = 0 the open call referred 80 of 80 problem customers on a gold ground and turned 45 of 48 customers' own 'don't know' into an understanding gap on the right field." "Where customers say yes to statements they cannot recall (an assumption of the harness), a yes/no call confirms knowledge gaps the open call finds (H1, three pre-declared cells); the yes/no side of that comparison is computed from the assumed recognition bias, not observed." "A reply that leaves it to the lender's records ends the open call as declined; under matched giving way the yes/no call caught more false beliefs on ground than the open call; every closed-only pair followed an open call that ended `declined`, and the symbolic yes/no call cannot end early."
- **May not:** real customers; a prevalence or field rate; "teach-back beats yes/no" in general; "the open call resists acquiescence"; "mis-selling found"; that recognition bias exists or how large it is; any result on speech; a pooled rate across cells; any Tamil or Kannada number.
- **The sentence that retires the acquiescence claim:** "Under this harness's matched-deference model, the open call can find a false belief the yes/no call confirms only when the customer says it in another field's answer (1 of 80, C126, at a = 0.25 and 0.5); and as built it found fewer, because a customer who leaves it to the lender's records is heard as declining the call."

## 7. Independent recompute
An Opus high-effort checker that wrote none of the code reviewed the plan before the freeze (18 findings; `PLAN.md` §11 lists what was done) and then recomputed the counted run with its own script, importing nothing from `eval/acq`.
- **Numbers:** 0 disagreements in 5,325 values (every k, n, per-100 figure, Wilson interval, McNemar b, c and p in 25 cells × 7 groups) and 0 in 3,295 table rows.
- **Closed arm:** rebuilt from the beliefs and the sha256 draw, 0 differences in 4,000 files.
- **Hashes:** all 19 `FROZEN.json` files and the records digest match. The snapshot tree equals `git archive 9c67da6` (`3e716a3a…`), and the run imported the snapshot's `samajh`. The repo tree now differs (uncommitted dialogue edits), so a rerun must use the snapshot.
- **Where plan wording and code differ** (no number changes): the provenance rule on `gap_found` (identical either way); the silent miss on completed calls only (the same); `refer_ground` = `refer_ground_any_source` everywhere, so the provenance and `*_dont_know` rules never changed a referral; provenance is not tied to the field's own topic (29 of 144 ground-matched flags at a = 0 quote another topic's reply, mostly the premium from the recall reply); P2a at a = 0 is a miss count (b = c = 0), not a test.
- **Seen before the freeze:** 4 customers (C005, C011, C021, C032) at a = 0 and 1 ran in `dryrun-unfrozen-2` with the final knowledge file; their counted calls are cache replays.
- **Other:** 1 degraded turn (C008, a = 0.75) and 0 unmapped lines.
- **Correction to its own plan audit:** "about 22 of 1,920 defer replies state a fact, each consistent with the belief" was wrong. Its regex missed "साइन"; 58 consent defers name a method and 2 contradict the belief.

## 8. Reproduce
```
# from a git archive snapshot of 9c67da6 with eval/acq, data/acq copied in, shared cache via SAMAJH_STATE_DIR
uv run python eval/acq/acq_run.py --out eval/acq/runs/counted --usd-budget 3 --workers 2
uv run python eval/acq/acq_score.py eval/acq/runs/counted --out tables.md --json scores.json
```
LLM spend: writers USD 0.79 + 0.09 (19 rewritten after the plan review), smoke and an accidental partial writer start 0.06, dry runs 0.02, counted run 0.52; about USD 1.48 in total.
