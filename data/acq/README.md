# ACQ customer set (synthetic)

160 synthetic customers (ACQ-C001 to ACQ-C160) for the open Samajh call against a closed yes/no call.
Built deterministically by `uv run python eval/acq/acq_build.py build` (seed `samajh-acq-2026-11-14`);
`check` re-derives and diffs; `freeze-inputs` writes `FROZEN_INPUTS.json`, which `eval/acq/acq_write.py run` requires.

- `records/acq-cNNN.json`: one `CallRecord` each, one credit-life product `P1`, ids `TEST-ACQ-LN-NNN`, names `<first name> Namoona`.
- `customers.jsonl`: kind, language, gender, writer model, the structured belief (per field `state` correct/false/dk and `value`) and the English fact sheet written from the belief alone.
- `gold.jsonl`: class (problem / knowledge_gap_only / no_problem), false and dk fields, ground, and the rule engine's tier and flags on perfect beliefs.
- `topics.json`: the twelve open-call topics (caller text copied from the P5 topics) with `field` and variants own, again, defer.
- `closed_statements.jsonl` and `closed_script.json`: one closed statement per field, display only.

Kinds: informed 32, knowledge_gap 48, misled 40, misled_with_gaps 40; half hi, half hi-en in each kind; writer model and gender balanced within each kind x language cell.

Generator rules that shape plausibility (not exclusions): a deposit belief always brings the money-back belief with it (2 false fields); a fee belief never sits with a money-back belief. `kind`, `source`, `required`, `consent` are never dk; `consent` is always correct.

Generator exclusions (combinations dropped because the engine disagreed with the gold rule): none. The engine agreed on all 160 (tier and every ground field).

Synthetic text only. Not human-reviewed. The customer mix is the builders' choice and says nothing about any real lender's customers.
