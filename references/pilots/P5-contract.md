# P5 contract: customers the builders did not script, with a matched closed call

P5-prep sub-orchestrator, 2026-11-10; revised after two independent verifications (`eval/p5/VERIFY.md`), before any audio. **Prepared, not run** (waits for P1, P2 and P3a to be verified). Sources: `references/reviews/iter1/judge.md` (section 2, "What can be done with no one recording", item 1; plan row 5) and `DESIGN.md` sections 9 (E6) and 15 (items 9, 27 to 30). My choices are marked **(chosen)**.

## 1. The question
On customers whose words the builders did not write, voiced end to end through the phone path:
1. Of 100 customers with a problem, how many does the open Samajh call fail to refer? Of 100 without one, how many does it refer?
2. How do those counts compare with a closed confirmation call on the same customers when they answer for themselves (level 0, paired)? As they give way more often, how does each arm behave on its own?
3. How far is the voice path from the text path?

P5 replaces E1, which was true by construction (`DESIGN.md` section 15 item 9).

## 2. The two arms and what makes them matched
- **Open:** the Samajh call as built, from the phone server to the tier.
- **Closed:** a script that states one record value at a time and asks "is that correct?" (`data/p5/closed_script.json`). The judge asked for "the product, premium, cover and cancellation window"; **(chosen)** it states ten matters, one for each the open call tests, so there is no "never asked" stratum (the judge's objection to E1).
- **Matched:** the same customer, record, language, voice, line, STT and opening steps; replies written from the same fact sheet; the same disposition draw.
- **Disposition** `a` is the chance that on a given matter the customer gives way: one seeded draw per customer and matter, shared by the arms (`data/p5/topics.json`). **(chosen)** Giving way is `go_along` in the closed call (mostly a yes) and `defer` in the open call (written to carry no content); both are the project's definitions, not matched to each other. Levels **(chosen)**: 0, 0.25, 0.5, 0.75, 1 on text; 0, 0.5, 1 on voice.
- **Closed outcome (chosen, generous to it):** `confirmed` only when every statement gets a plain yes; anything else is `not_confirmed` and counts as caught.
- **Records (chosen):** all compliant on their face, so only the customer's words can raise a referral.

## 3. Unit of analysis and clustering
The unit is the customer: 60 (30 Hindi, 30 Hinglish), each with its own fact sheet, record and gold, so there is no clustering by base case. The arms are compared within the customer at level 0 (exact McNemar); intervals are Wilson on customers and wide (14 misled). One author wrote all the situations and two writer models the words, so results are also shown by writer model.

## 4. Metrics: counts per 100 with n, by kind of customer, never one pooled rate
1. **Misses per 100 customers with a problem** (gold class `problem`), by kind, arm and level. Open miss: tier `clear` or `understanding_gap`; `incomplete`, and a call that `defer` replies ended early, are shown apart as neither. Closed miss: `confirmed`.
2. **Referrals per 100 customers without a problem**, by kind and gold class (`no_problem`, `knowledge_gap_only`), arm and level. Open: tier `refer`. Closed: `not_confirmed`.
3. **Opening kinds** (third party, refusal, call back later, language switch), open arm only **(chosen)**: the arms share the opening. Expected outcome reached, per 100 by kind; counts of third parties to whom the loan was named and of refusals asked a further question.
4. **Text against voice:** tables 1 to 3 on both paths, and the calls whose tier differs.
5. A call that fails, drifts or yields no case file stays in its row as "no result"; none is dropped or rerun.

## 5. Gold standard
Gold is the customer's state, set from the fact sheet and the record alone under `eval/p5/gold-rules.md`: class, expected outcome, expected tier, each ground with the fact-sheet line it rests on. The builder of the fact sheets set it; a second subagent labelled all 60 blind; the sub-orchestrator decided each difference in writing (`data/p5/CHANGELOG.md`). No rule engine, extractor or dialogue was run to set it; no person has reviewed it. The tier is scored only as `refer` or not (`gold-rules.md`, last section). A reply that fails to voice a belief counts against the arm (known cases: `data/p5/README.md`).

## 6. What is frozen, and when
1. **Before any customer words existed:** `customers.jsonl`, `records/`, `gold.jsonl`, `topics.json`, `closed_script.json` (sha256 in `data/p5/FROZEN.json`; `eval/p5/write_customers.py` refuses to write words otherwise).
2. **Before any audio:** `replies.jsonl`, `closed_statements.jsonl` and every request sent to a writer model. A reply is regenerated only for a mechanical fault, never for content; none is edited by hand.
3. Voices, the Batch subset and the draws follow seeded rules in `eval/p5/RUNNER-PLAN.md`.

No part of the product may be tuned on a P5 failure; a later headline needs a new set. A changed frozen file needs a `CHANGELOG.md` entry and a new freeze (version 2 added `defer`).

## 7. Credits
About 689 estimated credits remain of 1,000 (ledger 310.79, 21:45 IST). **Proposed budget: a hard stop at 300 estimated credits, about 265 planned**, plus about USD 1 of LLM spend. Arithmetic, a smaller run the iteration 2 judge proposes (about 135) and what is outside the budget: `eval/p5/RUNNER-PLAN.md`, Parts 0 and 1.

| Stage | What | Voiced calls | Estimated credits |
|---|---|---|---|
| 1 | Text path, both arms, five levels | 0 | 0 |
| 2 | Voice, level 0: 60 open, 46 closed | 106 | about 210 |
| 3 | Voice, levels 1 and 0.5, 46 customers, both arms | 184 | about 55 |

The judge's "at least 120 voiced calls" needs stage 3. Prisma Batch runs on 12 calls only **(chosen)**: it does not change the tier. Rates are client estimates, perhaps 20% off. **Outside this contract:** the judge's run of the frozen set on the voice path (the coordinator's decision) and his perturbation suite (not prepared).

## 8. What may and may not be claimed
**May:** the counts of section 4 with n, interval, arm, level and kind; "replies written by two outside models from fact sheets; Timbre voices on a simulated phone line"; the paired comparison at level 0; above level 0, each arm on its own (open end states: `incomplete`, ended early, wrongly `clear`, wrongly `refer`; closed `confirmed` count); the text-to-voice difference; every failure, listed.

**May not:** a pooled rate; "real customers" or any field rate; "independent customers" without the limits in `data/p5/README.md`; any difference between the arms above level 0 as an advantage of either, or "the open call resists acquiescence" (`defer` has no content by definition; closed `go_along` says no or "don't know" in 77 of 600 replies); "coached customers are caught for being coached" (not voiced at level 0); "teach-back beats yes/no" in general; a prevalence; "mis-selling found" (a referral is evidence for human review, never a finding; the 85Z refund duty arises only where mis-selling is established); any Tamil or Kannada number; a P5 number as a result on human speech (that is P4).
