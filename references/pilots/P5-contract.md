# P5 contract: customers the builders did not script, with a matched closed call

P5-prep sub-orchestrator, 2026-11-10; revised that day after independent verification (`eval/p5/VERIFY.md`), before any audio. **Prepared, not run**: the run waits for P1, P2 and P3a to be verified. Grounded in `references/reviews/iter1/judge.md` (section 2, "What can be done with no one recording", item 1; plan row 5) and `DESIGN.md` sections 9 (E6) and 15 (items 9, 27 to 30). My own choices are marked **(chosen)**.

## 1. The question
On customers whose words the builders did not write, voiced end to end through the phone path:
1. Of 100 customers with a problem, how many does the open Samajh call fail to refer? Of 100 without one, how many does it refer?
2. How do those counts compare with a best-practice closed confirmation call on the same customers, as the customer's readiness to give way to the caller rises?
3. How far is the voice path from the text path?

P5 replaces E1, which was true by construction (`DESIGN.md` section 15 item 9).

## 2. The two arms and what makes them matched
- **Open:** the Samajh call as built, from the phone server to the tier.
- **Closed:** a script that states one record value at a time and asks "is that correct?" (`data/p5/closed_script.json`). The judge asked for one that "states the product, premium, cover and cancellation window". **(chosen)** It states ten matters, one for each matter the open call tests, so there is no "never asked" stratum (the judge's objection to E1); it has no open last question.
- **Matched:** the same customer, record, language, voice, line, STT and opening steps; replies written from the same fact sheet; the same disposition draw.
- **Disposition** `a` is the chance that on a given matter the customer gives way to the caller instead of answering for themselves: one seeded draw per customer and matter, shared by the arms (`data/p5/topics.json`). Giving way is the `go_along` reply in the closed call (mostly a yes) and the `defer` reply in the open call, where there is nothing to say yes to: a reply written to carry no content. Levels **(chosen)**: 0, 0.25, 0.5, 0.75, 1 on text; 0, 0.5, 1 on voice.
- **Closed outcome (chosen, generous to it):** `confirmed` only when every statement gets a plain yes; anything else is `not_confirmed` and counts as caught.
- **Records (chosen):** all compliant on their face, so only the customer's words can raise a referral.

## 3. Unit of analysis and clustering
The unit is the customer: 60, each with one fact sheet, record and language (30 Hindi, 30 Hinglish). No rows share gold, so there is no clustering by base case. Arms and levels are compared within the customer (exact McNemar); intervals are Wilson on customers and wide (14 misled). Customers are not fully independent: one author wrote the situations, two writer models the words; results are also shown by writer model.

## 4. Metrics: counts per 100 with n, by kind of customer, never one pooled rate
1. **Misses per 100 customers with a problem** (gold class `problem`), by kind, arm and level. Open: a miss is tier `clear` or `understanding_gap`. Shown apart, neither catch nor miss: `incomplete`, and a call the customer's `defer` replies ended early. Closed: a miss is `confirmed`.
2. **Referrals per 100 customers without a problem**, by kind and gold class (`no_problem`, `knowledge_gap_only`), arm and level. Open: tier `refer`. Closed: `not_confirmed`.
3. **Opening kinds** (third party, refusal, call back later, language switch): expected outcome reached, per 100 by kind; as counts, third parties to whom the loan was named and refusals that got a further question. No closed arm here **(chosen)**: the arms share the opening.
4. **Text against voice:** tables 1 to 3 on both paths, and the calls whose tier differs.
5. A call that fails, drifts or yields no case file stays in its row as "no result"; none is dropped or rerun.

## 5. Gold standard
Gold is the customer's state, set from the fact sheet and the record alone under `eval/p5/gold-rules.md`: class, expected outcome, expected tier, each ground with the fact-sheet line it rests on. The builder who wrote the fact sheets set it; a second subagent labelled all 60 blind; the sub-orchestrator decided each difference in writing (`data/p5/CHANGELOG.md`). No rule engine, extractor or dialogue was run to set it; no person has reviewed it. Two limits: `gold-rules.md` is looser than the code where an answer is undecided (its last section), so the tier is scored only as `refer` or not; and gold is not the words, so a reply that fails to voice a belief on the fact sheet counts against the arm (known cases: `data/p5/README.md`).

## 6. What is frozen, and when
1. `customers.jsonl`, `records/`, `gold.jsonl`, `topics.json`, `closed_script.json`: sha256 in `data/p5/FROZEN.json` **before any customer words existed**; `eval/p5/write_customers.py` refuses to write words otherwise.
2. `replies.jsonl`, `closed_statements.jsonl` and every request sent to a writer model: sha256 added **before any audio**. A reply is regenerated only for a mechanical fault (empty, digits, wrong script, too long), never for content; none is edited by hand.
3. Voices, the Batch subset and the draws follow seeded rules in `eval/p5/RUNNER-PLAN.md`.

Nothing in the dialogue, word lists, extractor, rules or prompts may be tuned on a P5 failure; a later headline needs a new set. A changed frozen file needs a `CHANGELOG.md` entry and a new freeze (version 2 added the `defer` replies).

## 7. Credits
About 710 estimated credits remain of 1,000. **Proposed budget: a hard stop at 300 estimated credits, about 265 planned** (arithmetic: `eval/p5/RUNNER-PLAN.md`).

| Stage | What | Voiced calls | Estimated credits |
|---|---|---|---|
| 1 | Text path, both arms, five levels | 0 | 0 (LLM spend only) |
| 2 | Voice, level 0: 60 open, 46 closed | 106 | about 210 |
| 3 | Voice, levels 1 and 0.5, the 46 customers who talk through the call, both arms | 184 | about 55 |

The judge's "at least 120 voiced calls" needs stage 3. The estimate needs Prisma Batch off on all but 12 calls **(chosen)**: Batch does not change the tier and adds about 1.6 credits per open call. Rates are client estimates, perhaps 20% off. **Outside this contract:** the judge's "one run of the frozen set on the voice path" (72 calls; the coordinator's decision) and "perturbation suite" (not prepared; the `again` replies and the open call's terse `go_along` replies give a small part of it on text).

## 8. What may and may not be claimed
**May:** the counts of section 4 with n, interval, arm, level and kind; "replies written by two outside models from fact sheets; Timbre voices on a simulated phone line"; the paired comparison at level 0, where every customer answers for themselves in both arms; how each arm moves as `a` rises; the text-to-voice difference; every failure, listed.

**May not:** a pooled rate; "real customers" or any field rate; "independent customers" without the limits in `data/p5/README.md`; "the open call resists acquiescence" as a discovery (a `defer` reply carries no content by definition and silence is never a pass by design: the open arm can only show whether a customer who gives way ends `incomplete`, as designed, or is wrongly cleared or referred); "teach-back beats yes/no" in general; a prevalence (the mix of kinds is ours); "mis-selling found" (a referral is evidence for human review, never a finding; the 85Z refund duty arises only where mis-selling is established); any Tamil or Kannada number; a P5 number as a result on human speech (that is P4).
