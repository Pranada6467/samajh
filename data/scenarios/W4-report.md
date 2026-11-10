# W4 report: scenarios and gold

Date: 2026-11-10. Worker: W4 execution manager.

Goal as I understood it: every later Samajh measurement is scored against one synthetic scenario set, so the set needs gold a person would defend, a freeze that cannot drift unnoticed, and an honest account of where gold and the rule engine disagree.

## 1. What was built

- `samajh/scenarios/model.py`: the scenario types (record facts, the customer's beliefs, gold, source award, both scripted calls).
- `samajh/scenarios/cases.py`: 36 base cases with hand-written gold and a rationale each.
- `samajh/scenarios/phrases/{hi,hi_en,ta,kn}.py`: what customers and the bot say, keyed by meaning.
- `samajh/scenarios/script.py`: belief to scripted teach-back call, its perfect extraction, and the yes/no call.
- `samajh/scenarios/build.py`, `__main__.py`: `build`, `freeze`, `verify`, `check`, `stats`.
- `samajh/scenarios/consistency.py`: gold against the rule engine. The only module that imports `samajh.rules`.
- `data/scenarios/`: `gold.jsonl`, `calls.jsonl` (144 rows each), `FROZEN.json` (version 2), `CHANGELOG.md`, `README.md` (the datasheet).
- `tests/scenarios/test_scenarios.py`: 49 tests.

Plan, in brief. The data shape came first: a language-neutral base case holds the record, the beliefs and the gold; a scenario is one base case in one language. Each customer line is chosen from a phrase bank by the belief it expresses, so the script cannot drift from the belief. Gold never passes through the rule engine, and a test proves the build does not import it.

## 2. Evidence

```
$ uv run pytest tests/scenarios -q
.................................................                        [100%]
49 passed in 2.25s
exit: 0

$ uv run ruff check samajh/scenarios tests/scenarios
All checks passed!
exit: 0

$ uv run python -m samajh.scenarios verify
OK: files on disk and the generator match FROZEN.json
exit: 0

$ uv run python -m samajh.scenarios build
d002423a32eeb7c020526e01cf0b21083566ad2e593a67a30e1c9d7f0154f152  gold.jsonl  (144 rows)
b10111dfc64e5dd74061f553cdbf666db916491f9ce3ef647ae3d0778fad29f5  calls.jsonl  (144 rows)
exit: 0

$ uv run python -m samajh.scenarios check
path: beliefs   scenarios: 144
verdict and flag set agree: 136/144
  verdicts agree:           140/144
  flag sets agree:          136/144
  unclear-rule sets agree:  136/144
path: extraction   scenarios: 144
verdict and flag set agree: 135/144
  verdicts agree:           139/144
  flag sets agree:          136/144
  unclear-rule sets agree:  135/144
```

`tests/core` still passes (1223 passed); nothing outside the three W4 directories was edited.

**The agreement number.** Design section 14 expected 100% on perfect transcripts. The measured number is 136 of 144 scenarios (94.4%), which is 34 of 36 base cases, because the four languages share gold. What limits it is one rule reading:

- **U09 and U10, in all four languages (8 scenarios).** The customer says "I don't know" or "I don't remember" the premium. Gold says unclear, from `DESIGN.md:164` ("not stated → `unclear`"). The engine raises a medium `premium` flag. In U09 this changes the verdict.
- **U01-ta (extraction path only).** The amount parser reads "ஒரே" in "ஒரே தடவைதான் கட்டணும்" (to be paid only once) as the number 1 and refuses the turn. The other 143 scripted calls parse to the believed amounts, terms and windows.

On no scenario with a clear gold verdict does the engine raise a flag.

## 3. The set

- 36 base cases × 4 languages = 144 scenarios. The design planned 96 (24 base cases). The extra 12 are the cases the claims check requires and the coached group.
- Gold verdicts over base cases: 9 clear, 24 flag for review, 3 unclear.
- Required cases, each with a test: a required risk mitigant with a choice of provider (clear), a product sold as an FD and as a security deposit, a premium from the loan with and without consent, consent on file with the customer unaware, three coached customers, a premium inside (0.81%) and just outside (1.21%) the tolerance, "I don't know" customers, and fraction amounts in every language.
- 11 base cases are modelled on customer-relief awards and record the remedy each award ordered (5 refund, 4 conversion, 1 partial refund, 1 other). No award the insurer won is used. Compliant and near-miss cases are synthetic.
- Counts per rule, language and class are in `data/scenarios/README.md`, generated from the files.

## 4. Independent review (one Fable high-effort subagent that wrote none of the work)

The reviewer wrote its own verdict for all 36 base cases with gold hidden, without access to the rule engine, and read 38 scripted calls in full across the four languages.

- **Gold.** It agreed with the case verdict in 36 of 36 and with the full flag and unclear sets in 35 of 36. The one error was U10: `consent` and `belief_mismatch` should be flags under the current `DESIGN.md:169` and `:172`.
- **Scripts.** It found three problems to fix before audio: U10's consent line named a method the customer could not know; C03 answered three yes-or-no-shaped questions with "yes, absolutely", which reads as an answer; G02's lines contradicted each other.
- **Mechanics.** Eight tamper attempts on a copy were all caught by `verify`. Builds under four hash seeds were byte-identical. No personal data found.

What I changed (all in `CHANGELOG.md`, version 2):

- U10 gold: `consent`, `belief_mismatch` and `kind` moved from unclear to flag. The first two follow the design text. `kind` is our reading, because the design is silent on a customer who does not know what the product is.
- G01: the customer now says they do not know whether the money comes back, which adds a low `belief_mismatch` flag.
- Script fixes for U10, C03, G02, G01, the guaranteed-return line, NBFC customers saying "the bank", and five Tamil and Kannada wordings.

What I did not change, and why: a consent given to a misdescribed product stays unflagged (U08, V04, V06, C02), and a product recalled under the wrong name stays matched to the record. Both are documented as our readings.

One cause worth knowing: `DESIGN.md` section 6 was rewritten by another work package while version 1 gold was being written, so version 1 followed the older text on "I don't know".

## 5. Claims

Verified:
- Remedies of the 11 source awards against `references/claims/findings-B.md` (B1, B2, B4, B5, B7, B-N2, B-N6, B-N9, B-N10, B-N11, B-N17). A test pins them, and the reviewer checked them independently.
- Paragraph numbers are not stored in the set. Gold uses neutral rule ids only.

Not verified:
- Tamil and Kannada text has no human reviewer. Hindi and Hinglish text is model-written and model-reviewed only. Both labels are in the data.
- The yes/no script is our model of a confirmation call, not a transcript of any lender's call.

## 6. Failures, gaps and deviations

**Decisions the coordinator should make.**

1. **A premium "I don't know".** `DESIGN.md:164` says unclear; the engine flags it (medium). Gold follows the design. Either the engine changes, or line 164 changes and gold is refrozen with U09 and U10 flagged. This is the whole 5.6% gap.
2. **A kind "I don't know".** The design is silent. Gold and the engine both flag. Confirm, and add it to line 163.
3. **The Tamil parser miss on "ஒரே"** belongs to W1.

**Deviations from the process.**

- I wrote the code and the gold myself and spawned no builder subagents, as the task preamble told me to. The architect arena was skipped for the same reason; the plan was done inline.
- One review pass ran. The fixes made after it have tests, but **no independent reviewer has seen version 2**.
- No LLM was used. The task allowed cheap models for drafting utterances. I wrote the phrase banks by hand so that each line stays tied to the belief it expresses.

**Known gaps.**

- E1 is shaped by our choices. The scripted yes/no call misses 9 of the 19 base cases where the customer is not informed: 4 by assumed disposition (3 coached, 1 acquiescent) and 5 because the closed script never asks about that belief. Report E1 by stratum. The hero case U02 passes the yes/no call only because we assume an acquiescent customer.
- Disposition applies to the yes/no call only. U02, C01 and C02 answer the teach-back call candidly. This favours teach-back.
- The effective sample is 36 cases, and only 9 are gold-clear.
- Speech is templated: one to three variants per answer.
- Not covered: two products on one record, `recall_unmatched`, a premium corrected at read-back, "can cancel but not by when", a re-ask after an unclear answer.
- A savings policy is recorded as `kind: credit_life` with `risk_mitigant: false`, because the type has one product kind. I judged this expressible and did not ask for a type change.
- The freeze is a hash in a file. The three directories are untracked in git, so nothing outside them anchors it yet. **Commit before any audio is made.**

## 7. Spend

Gnani credits: 0. OpenRouter: 0 USD. Subagents: one reviewer.

## 8. Documents this work makes stale

- `DESIGN.md:231` (E2 row): "96 scenarios: 4 clauses × 6 … × 4 languages". Now 144 scenarios, 36 base cases × 4 languages.
- `DESIGN.md:318`: "96 scenarios with gold frozen" and "rule engine passes 100% of gold on perfect transcripts". Now 144, and 136 of 144 (34 of 36 base cases).
- `DESIGN.md:334` (open decision 8): the coached group is adopted (C01 to C03).
- `DESIGN.md:230` (E1 row): add that yes/no replies are scripted by disposition and E1 is reported by stratum.
- `DESIGN.md:238`: the template list. Used: BHP-L-021-1617-0529, BNG-L-041-1617-0797, PUN-L-036-1617-0228, AHD-L-001-1617-0203, CHD-L-019-1718-1436, BNG-L-033-1617-0600, BHP-L-013-1617-0436, Baramulla CC 33/2025, and three the line does not name: BHP-L-021-1617-0456, PUN-L-041-1617-0649, PUN-L-009-1617-0009. PUN-L-017-1617-0684 is not used.
- `DESIGN.md:245` and `:247` (demo steps 2 and 4): the yes/no PASS for the hero case rests on an assumed acquiescent customer. A truthful customer who believes it is an FD says no at the first closed question.
- `DESIGN.md:163` (`kind`): silent on a customer who does not know what the product is.
- `DESIGN.md:164` (`premium`): conflicts with the engine on "I don't know".
- `DESIGN.md:170` (`loan_funded`): does not say that a record of "paid separately" with a customer who does not know is unclear, which is what gold and the engine both do.
- `DESIGN.md:172` (`belief_mismatch`): the examples omit a single-payment claim (B03).
- `ORCHESTRATION.md:78`: W4 row says 96 scenarios, in progress.
- `README.md:17`: "the 96 test scenarios".
- `CLAUDE.md:57`: "scenarios … in progress". The Files section has no entry for `samajh/scenarios/` or `data/scenarios/`.

## 9. Next iteration, in this area

1. Decide the two "I don't know" readings, then refreeze if gold changes.
2. A second independent review of version 2, and a fluent Tamil and Kannada reviewer.
3. W5 should score extraction on status and value, cluster by base case, and treat the consent reading in U08, V04, V06 and C02 as a separate stratum (`data/scenarios/README.md`, "Using the set").
4. Key customer audio by a hash of the utterance text, not by the hash of `calls.jsonl`.
5. Add a matched closed arm to E1 (a confirmation script that states the cover, the window and the premium frequency), so E1 separates open-versus-closed from script coverage.
