# W3 (iteration 4): does the open call find what a yes/no call misses?

**Verdict, quotable.** On synthetic Hindi and Hinglish text, the open Samajh call turned 45 of 48 customers' own "don't know" into an understanding gap on the right field and referred 80 of 80 problem customers on their ground. Its advantage over a yes/no call rests entirely on the assumption that customers say yes to what they cannot recall. When customers give way to the lender as readily in the open call as in the yes/no call, the open call found one false belief the yes/no call confirmed (C126, said in another field's answer). At a = 0.5, r = 0, ground-matched referrals were 44 open against 55 closed, of 80. 1 pair was open-only and 12 closed-only, and all 12 came after the open call ended `declined` on a reply such as "आप records में देख लीजिए" ("check your records"). The symbolic yes/no call cannot end early, by construction.

**Retired:** "the open call resists acquiescence." The sentence that retires it: "Under this harness's matched-deference model, the open call can find a false belief the yes/no call confirms only when the customer says it in another field's answer (1 of 80, C126, at a = 0.25 and 0.5); and as built it found fewer, because a customer who leaves it to the lender's records is heard as declining the call."

## What was built (new directories only)
- `data/acq/`: 160 synthetic customers (`acq_build.py`, seed `samajh-acq-2026-11-14`): 32 informed, 48 knowledge_gap, 40 misled, 40 misled_with_gaps; half Hindi, half Hinglish. Each has a record, a belief per field (correct / false / don't know), gold class and ground, and a consistency check that the rule engine gives the gold tier on perfect input (160 of 160). `knowledge.jsonl`: replies written from a fact sheet built from the belief alone (the writer never saw the record) by `google/gemini-3.7-flash` (80) and `deepseek/deepseek-v4.1-flash` (80), in three variants: own, again and defer. `FROZEN.json` pins 19 files, the records and the source tree.
- `eval/acq/`: `acq_write.py` (writer), `acq_player.py` (deterministic player: open replies by `u_a`; symbolic closed answers by `u_r`, `u_a`), `acq_run.py` (freeze check, 160-of-160 entry preflight, resumable runner), `acq_score.py` (per cell and kind: Wilson, exact McNemar, ground match with provenance). `PLAN.md` (the frozen plan, with the review log in §11) and `REPORT.md` (every table, failures with quotes, the recompute).
- **Arms.**
  - Open: the call at commit 9c67da6, entered with fixed replies that never say a name ("हाँ जी।" / "हाँ जी, मैं ख़ुद ही बात कर रहा/रही हूँ।" / "हाँ जी, बोलिए।"), word lists only for those turns, scored from open recall.
  - Closed: ten record statements answered symbolically, strict (confirmed only on ten yeses) and lenient.
  - Grid r, a ∈ {0, .25, .5, .75, 1}, every customer in every cell, the same draws in both arms.
- **Run:** from a clean `git archive` snapshot of 9c67da6, so the other worker's uncommitted `samajh/dialogue` edits were not in it. Source-tree sha256 over `samajh/` and `data/prompts/`: `3e716a3abfe96a98dd03cd5677e65aca01f2c21cbe96e82798595d3bcc4f03b8`. Calls: 800 open, 4,000 closed; 0 no-result, 0 entry failures, 1 degraded turn.

## Measurements (unit = customer; full tables in `eval/acq/REPORT.md` and `eval/acq/runs/counted/tables.md`)
- **a = 0, open arm:**
  - problem customers: 80 of 80 referred on a gold ground [95.4–100];
  - knowledge gap: 45 of 48 found [83.2–97.9], plus 1 referral (C018) and 2 turn-limit endings;
  - informed: 28 of 32 clear [71.9–95.0], 0 referred.
- **Primary test H1** (knowledge gap, a = 0; b = found by the open call only, c = by the closed call only). It holds in all three pre-declared cells:
  - r = 0.5: b 16, c 3, p = 0.0044;
  - r = 0.75: b 25, c 1, p = 8e-7;
  - r = 1: b 45, c 0, p = 6e-14.

  The closed side of these pairs is arithmetic on the draws.
- **a > 0, open arm:**
  - problem customers referred on ground: 59, 44, 20 and 0 of 80 at a = 0.25, 0.5, 0.75 and 1;
  - `declined` endings not referred: 13, 27, 31 and 42 (raw `declined`: 15, 30, 32, 42);
  - silent misses: 0 at every a.
- **a > 0, closed arm (strict, r = 0):** confirmed 5, 13, 25 and 40 of 80.
- **H2** (ground-matched, r = 0): b against c is 1 v 10, 1 v 12, 0 v 6 and 0 v 0. The closed arm had more closed-only ground-matched pairs (10, 12, 6 against 1, 1, 0). Every closed-only pair followed an open call that ended `declined`, and the symbolic closed arm cannot end early, by construction. The one open-only pair is C126, a false belief said in another field's answer.
- **H3** (visibility) was decided before the run. Every open call at a ≥ 0.5 ends non-clear, informed customers included (0 of 32 clear).
- **LLM spend:** about USD 1.48 of the 6 allowed. Writers 0.79, plus 0.09 to rewrite 19 customers; smoke test and an accidental partial writer start 0.06; dry runs 0.02; the counted run 0.52. No Gnani calls.

## The independent checker, in its own words, and what I did
- **Plan review (before the freeze, 18 findings).**
  - "H1 is refuted before the run at every cell with a ≥ 0.5": tested at a = 0 only.
  - "H1's clause 'b does not fall as r rises' can never trigger": dropped; the r axis is declared arithmetic.
  - "H3 is decided before the run": demoted to descriptive.
  - "The premium figure is revealed under the kind draw": the open-recall reply now follows the premium draw.
  - "A canned reply states a fact that contradicts every customer": replaced by the customer's own recall reply.
  - "Flags that come from a deferral can count as findings": provenance rule added.
  - "The fact sheet and the gold disagree for fee and deposit customers": 19 sheets fixed and rewritten.
  - "P3 on no_problem customers reads as a win for the open arm": dropped as a test.
  - "The code is not pinned" (blocks the run): every file is frozen, the check refuses on a mismatch, and the run used the snapshot.
  - "'The customer never says a name…' is too strong": 160-of-160 entry preflight.
  - The rest are stated in `PLAN.md` §6 and §11.
- **Recompute (after the run).** "0 disagreements" in 5,325 values and 3,295 table rows. The closed arm rebuilt from the draws: 0 differences in 4,000 files. Hashes match `git archive 9c67da6`.
  - Its conditions are in `REPORT.md`: "must not present 'open beats closed' as a measured contrast"; the C126 leak; the two defer replies that contradict their belief (C079, C100); 4 customers already seen in the dry run before the freeze.
  - It corrected its own plan audit: 58 consent defers name a method, not about 22. The correction is in `PLAN.md` §11 and `REPORT.md` §7.
  - None of these needed a code fix, so there was no fix round on code.

## What is left open
- Every customer is synthetic and the replies are LLM-written. No fluent person has read them.
- The run is on text, not speech, and recognition bias is assumed.
- The deference model (`d(a) = a`, the same draw in both arms on false fields; "don't know" fields use u_a in the open arm and u_r in the closed arm) is one choice. Any other choice decides the a-axis result by assumption.
- The voice run of the open arm is not done.
- `eval/acq/runs/counted` is 43 MB of call files. The coordinator decides whether to commit it whole.

## Needed from others
- **Dialogue owner:**
  1. A deferring reply such as "आप records में देख लीजिए" or "आपको better पता होगा" is read as a refusal and ends the call `declined` (all 80 such endings at a = 0.25 and 0.5). It should be a non-answer and lead to a re-ask or the next question.
  2. "फिर कभी नहीं (देना पड़ा)" is read as `call_later`, and "दोबारा किसी ने नहीं माँगा" as `asks_repeat`. With a "talk now" reply, `payment_frequency.reask` ↔ `callback.when` loops 25 or 26 times to `turn_limit` (11 calls, 4 customers). The loop needs a cap.
  3. A recall reply "insurance लिया था, पर कितने का था वो याद नहीं" takes the took-nothing branch (C018).
- **Extract and rules owner:**
  - "जब तक लोन चलेगा" is `value_not_parsed` for the term in 9 of 56 replies.
  - "loan के साथ insurance को हाँ कहा, OTP phone पर आया था।" became consent `no_usable_answer` (C092).
  - `recall_off_record` outranks two correct don't-know flags (C018).
- **Documentation worker:** retire "the open question finds what yes/no misses" as a detection claim, using the verdict and retirement sentences above. The iteration 4 review §5 proposes leading with the record comparison and the evidence pack instead. The allowed and banned wording is in `REPORT.md` §6.

## Tests
`uv run pytest -q tests/acq` → 37 passed (in the repo and in the snapshot). Reproduce: `eval/acq/REPORT.md` §8.
