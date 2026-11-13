<!-- Saved by the P5 sub-orchestrator on 2026-11-13 from the independent verifier's (Opus, high effort) final message, unchanged. It checked run text-2568759 and the first draft of eval/p5/REPORT.md; the line numbers refer to that draft. -->

## P5 verification: text run `text-2568759` and `eval/p5/REPORT.md`

**Verdict: PASS, with corrections needed in REPORT.md.** I rebuilt every number in score.md tables 1–5 and 9 from the raw call files. Every count, Wilson interval and McNemar p agrees with the builders' scorer; the one problem is how one p-value is printed. The seven claims (a) to (g) are all true. REPORT.md has five lines to fix: four are factual errors and one leaves out a customer. No LLM or Gnani calls; no spend.

My scripts were written from the contract and the raw files, without importing `eval/p5/score.py`. Both are in `/private/tmp/claude-501/-Users-masterpanda-projects-gnani-voice-ai-challenge/107df994-3c23-4a0c-bd96-6e19c2197a7d/scratchpad/verify-p5/`:
- `verify_p5.py` recomputes the tables. Its output is in `out.txt`.
- `check_report.py` checks REPORT.md. Its output is in `report_check.txt`.

### Part 1: the run

**1. Frozen data: PASS, one caveat.**
- All 11 sha256 in FROZEN.json match, including the records digest computed as `how_to_recompute` says.
- The manifest's commit is 25687594189883d2…, and its frozen digests equal FROZEN.json.
- `git status` at run time, per the manifest: `samajh/ops/model.py`, `report.py` and `sessions.py` modified. `samajh/ops/book.py` has been modified since; it is probably not on the text path.
- The five harness files hash today to what the builder reported: player 3aac5211, text_run e4852255, run 2bcf8243, bank 35cb5dd7, score 1582b88b.
- **Caveat:** `player.py` is uncommitted. It differs from the copy in 2568759 (who_check, kind.ask_named and ack.neutral mappings, and the verify fix). It was saved at 04:20 UTC, before the run began at 04:23:36. The manifest records git status only for `samajh/` and the prompts, so it does not show this. REPORT §8 does disclose it.

**2. Completeness: PASS.**
- 590 of 590 calls present: open 300, closed 230, terse 60.
- None missing, duplicated, failed, unmapped or degraded. Every open call has a tier, and every closed call has 10 statements.

**3. Tables 1, 2, 3, 4, 5 and 9: PASS.** 0 disagreements in 228 rows. The definitions match the contract:
- Open miss = `clear` or `understanding_gap`.
- `incomplete` and ended-early are reported apart.
- Closed miss = `confirmed`.
- McNemar is computed at level 0 only.
- There is no open-minus-closed difference, and tables 1 and 2 have no pooled row.

Disagreements and points for the report:
- **D1. One p-value prints as 0.0.** Table 5's p for "no_problem_or_gap, all kinds" shows as **0.0** in score.md and score.json because it is rounded to 4 places. The exact value is 7.6e-6. REPORT's "≈8e-6" is correct.
- **Tier refer counts as caught even when the call ended early.** This affects 8 calls: C015 at L0, C001, C005, C016 and C037 at L0.25, C037 at L0.5, and C002 and C007 at L0.75.
- **Table 6 pools across kinds.** It gives per-100 rates by writer and gold class, which sits uneasily with contract §4.

**4. Spot checks: PASS.**
- Every reply in all 590 calls matches `replies.jsonl` word for word for its topic and variant.
- The disposition draw, recomputed from the topics.json rule, has 0 violations. The open and closed arms give way on the same matters in every case.
- I read C010, C015, C021, C029 and C055 (open, level 0) and C029 (closed, level 0). Each tier follows from its gaps and flags.

**5. Claims (a) to (g): all TRUE.** The numbers match exactly: 0 of 26 missed with C010 incomplete; 0/6, 2/14, 5/6 and 4/14; 20/20 primary and 14/20 lenient; 18 closed-only; third parties 6/6 with the loan never named; refusals 2/3; 8 consent gaps of which 6 stand alone; smoke ledger delta 4.9868. Two caveats:
- C015 counts toward (a) despite the dialogue fault REPORT §5H describes.
- The two false referrals in (b), C019 and C021, are misreadings of correct beliefs (REPORT §5E).

### Part 2: REPORT.md against the raw files

**Disagreements:**
- **Line 52 (terse).** "19 of the 20 ended incomplete or early" should be **20 of 20**: 19 incomplete and 1 ended early (C043). The line also leaves out 1 incomplete coached problem customer; the files have 4 misled and 1 coached incomplete.
- **Line 71 (pattern A).** Nine problem customers have a `consent no_usable_answer` gap, not seven: the seven named, plus C037 and **C038**. C037 is covered on line 72. C038 ("App में loan screen पर accept click किया था.") is not mentioned anywhere. The seven named are correct, and each has a reply giving only the method.
- **Line 85 (C010).** C010 is **male**: Imran, gender m in customers.jsonl, and he says "मैं Imran बोल रहा हूँ". "Her payment answer" and "caught her" should be "his" and "him".
- **Line 92 (C055).** "The only one of the 60 frozen replies to this question that ends in a question" is false. Four `is_this_you_again` replies end in "?": C048, C050, C051 and C055. The first three are third parties, so the true statement is "the only borrower's reply".
- **Line 36 (no early endings at level 0).** "No open call ended early at level 0" holds only for customers without a problem. C015, a problem customer, ended `wrong_party` at level 0 (tier refer).
- **Line 3.** "Independently recomputed: pending" is now out of date.

**Checked and correct:**
- **§3 tables, line 38, lines 42–44.** Writers: C019 is DeepSeek (1 of 9), C021 is Gemini (1 of 11).
- **Line 39 and §5G.** All 6 well-informed closed referrals are affirmatives to a negatively worded statement read as no. This happens in 6 well-informed and 11 of 14 knowledge-gap customers. The example quote is from C023.
- **Line 47.** Third parties all end at customer turn 1, except C050 at turn 2.
- **Line 48.** C053 and C054 ended declined.
- **Lines 50, 93, 94 (C059).** The go-ahead was read as yes; the switch came at customer turn 16; the cover read-back was asked 3 times. All quotes match.
- **§4 counts.** 25/17/10/5/0; 9/16/18/21; 0/0/3/5; 17–19; 0/0/0/1/14; 0/0/3/7/14. The two four-value lists cover levels 0.25 to 1 only.
- **§5A.** The consent question and all quotes match. Each method matches the record. Consent is asked once and is the last question. The extractor prompt quote is word for word (`samajh/extract/_prompt.py:324`). "6 of the 9" is correct.
- **§5B.** Bundling gaps are present in C017, C018 and C020, and in C019, which was referred.
- **§5C.** Premium was `value_not_parsed` for C018, C010, C016 and C019. Gold for C018 is premium dont_know with a premium gap.
- **§5D.** The closed quote is present in C010's closed call (closed_not_confirmed).
- **§5E.** The summary titles read "described the product as a deposit (FD)" and "agreed by word of mouth only".
- **§5H.** All 4 quotes match, `confirms_self` is in the file, and gold has payment_source = from_loan. Line 101 matches the docstring of `who_check_claim` (`interpret.py:984`); I did not run it.
- **§6.** Covered on all counts: 4 ready case files; C048 never hears "loan"; C006's said and heard text; C001's v3.0 "40,42,000" and v2.5 "₹82,000" with the literal intact, then a re-ask, `value_not_parsed` and tier refer; C007 "कितने साल चलेगा? वो नहीं बताया" read as asks_repeat; 8 kHz Timbre; Batch off; 3 of 4 calls match the text run.
- **§8.** The 12-hex hashes match. The committed `player.py` hashes a3c36e7dfff7. Spend is 0.21646.

**Could not check:**
- Harness file hashes at the moment of the run (I have only file modification times and the builder's word).
- Whether the run reproduces from the LLM cache.
- The `--workers 2` argument (not recorded in the manifest).
- Table 7's turn counts.
- `voice-smoke-rerun`.
- Whether gold itself is right.

---

<!-- Addendum saved by the P5 sub-orchestrator on 2026-11-13 from the same verifier's recheck message, unchanged. -->

## Addendum to verify-P5.md: recheck on commit 3b64086

**Verdict: PASS.** Both runs are complete, both frozen sets are unchanged, and my recount of tables 1–5 and 9 agrees with each `score.json`. Every builder claim you listed is true. Three caveats belong in the report section:
- C015 is still ended as a third party in the post-fix run.
- The fix round caused new identity failures: P5 C017 and C053 fail where 2568759 did not, and the 5 P5b customers fail the same way.
- A closed call that ends in the shared opening is counted as neither caught nor confirmed.

No Gnani or LLM calls were made. The only code I ran was the two deterministic functions in item 5.

My script is `/private/tmp/claude-501/-Users-masterpanda-projects-gnani-voice-ai-challenge/107df994-3c23-4a0c-bd96-6e19c2197a7d/scratchpad/verify-p5/verify_p5.py`, now run as `python3 -I verify_p5.py RUN_DIR DATA_DIR`. The earlier version is kept beside it as `verify_p5_v1.py`. The outputs are `out-postfix.txt`, `out-p5b.txt` and `out.txt` (2568759, rerun with the extended script: still 0 disagreements).

### 1. Frozen data: PASS
- **data/p5:** all 11 digests match FROZEN.json v2.
- **data/p5b:** all 10 digests match FROZEN.json v1, with records recomputed as its `how_to_recompute` says.
- **Order:** P5b Stage 1 was frozen at 05:00:56Z and Stage 2 at 05:10:26Z. The P5b run started at 06:59:03Z, and the post-fix run (on P5, frozen 2026-11-10) at 06:55:08Z. Both runs began after the freezes they rely on.
- **Manifests:** both name commit 3b64086d…, record an empty `git status` for samajh/ and the prompts, and list frozen digests equal to FROZEN.json.
- **Harness:** all 9 files in `harness_sha256` hash today to the manifest values.
- **Uncommitted run.py:** `eval/p5/run.py` differs from the commit by 2 lines, adding the `--label` option and the manifest field. The working-tree copy is the one recorded. The commit's copy hashes b75c8bd0728c.

### 2. Completeness: PASS
- **Post-fix run:** 590 of 590 calls (60 open × 5 levels, 46 closed × 5, 60 terse).
- **P5b run:** 239 of 239. 239 = 24 open × 5 levels (120) + 19 closed × 5 (95; the 5 procedural customers get no closed call) + 24 terse.
- **Both runs:** none missing, duplicated, failed, unmapped or degraded, and every open call has a tier.
- **Replies and disposition draw:** every reply matches the frozen replies word for word. The draw has 0 violations and 0 open/closed disagreements; P5b uses its own seed.

### 3. Tables 1–5 and 9: PASS, 0 disagreements in both runs
- **First pass showed a gap in my script.** I counted a closed call with fewer than 10 statements as no-result, which gave 20 + 4 + 15 disagreements.
- **Which calls.** These closed calls ended at the identity question with outcome `not_confirmed`: P5 C017 at every level, and P5b C009, C012, C013, C016 and C019.
- **Scorer's reading.** It counts them as ended early (neither caught nor confirmed), and in the paired test as not caught. That fits the contract, since the closed call never stated anything. I adopted the same reading, and all disagreements went away.
- **Contract choice for the report.** These calls are excluded from neither the n nor the McNemar pairs; they sit as "neither".
- **Exact p values:** post-fix, no problem, 0 against 19 gives p = 3.8e-6 (lenient 2.4e-4). P5b, no problem, 0 against 3 gives p = 0.25.

### 4. Builder claims
- **Open L0, 0 misses in both runs: TRUE.**
- **Post-fix P5, problem customers 26/26 caught: TRUE.** C010 is now refer. **But C015 still ends `wrong_party` after the mid-call who-check, with tier refer.** Her bot sequence is unchanged and the final line is `end.third_party`, so the scorer counts her as caught again.
- **P5b, problem customers 11/12 caught, C016 ended early at the opening: TRUE.**
- **0 open referrals of customers without a problem in both runs: TRUE.** In P5b this is partly empty, because both well-informed customers and 2 of the 5 knowledge-gap customers ended at the opening.
- **Post-fix well_informed 6/6 clear: TRUE.**
- **Open L0 changes from 2568759 to 3b64086 are exactly the 12 named: TRUE.** No other customer's tier or outcome changed. Two of the 12 are regressions:
  - C017 went from completed to `not_confirmed`: "जी हाँ, मैं ही रामप्रसाद हूँ।" at the direct question.
  - C053 went from declined to `not_confirmed`: "हाँ भाई, मैं ही भूपेंद्र हूँ।".
  - Four more calls changed their transcript but kept the same tier: C044, C046, C056 and C057.
- **P5b C009, C012, C013, C016 and C019 end `not_confirmed` at the direct identity question after giving their own name in Devanagari: TRUE in both arms.**
  - Each reply has the shape "(जी) हाँ, मैं ही <name in Devanagari> हूँ".
  - Each was read as `yes`/`confirms_self`, and each call then ended `end.third_party` after 2 customer turns.
- **P5b C024 ended `completed`, not `language_switch`: TRUE.** The Telugu request ("मेरी हिंदी कमज़ोर है, Telugu में बात कर सकते हैं?") came at the go-ahead and was read as yes. The whole call then ran in Hinglish, with tier understanding_gap.
- **Paired McNemar, post-fix no-problem 0 against 19, P5b no-problem 0 against 3: TRUE.**
  - Post-fix: 20 pairs, with C017 as "neither".
  - P5b: 7 pairs, with C009, C012, C013 and C019 as "neither".

### 5. Interpreter calls (deterministic, no LLM; Language.hi)

| Reply | First name | doubts_claim | claims_self | claims_self(closed=False) |
|---|---|---|---|---|
| "जी हाँ, मैं ही रामप्रसाद हूँ।" | Ramprasad | **True** | False | True |
| "हाँ, मैं मीना बोल रही हूँ।" | Meena | False | True | True |
| "जी हाँ, मैं ही Ramprasad हूँ।" (my control, Latin script) | Ramprasad | False | True | True |
| "जी हाँ, मैं ही ममता हूँ, बताइए।" (P5b C009) | Mamta | **True** | False | True |

This supports the builder's diagnosis: with the name in Devanagari after "मैं ही … हूँ", `doubts_claim` fires, while the same name in Latin script does not.

### Could not check
- Whether the post-fix rerun reproduces from the LLM cache.
- The P5b gold labels themselves.
- The score.md text: I compared against score.json, from which score.md is written.
