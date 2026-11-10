# P5 customer set: changes

## 2026-11-10, before the first freeze: blind second labelling and its decisions

No customer words and no audio existed when these changes were made.

**What was done.** The builder who wrote the 60 fact sheets set gold (`gold.jsonl`, sha256 `8296d8cb…`). A second subagent, given only the fact sheets, the records and `eval/p5/gold-rules.md` (no kind, no gold), labelled all 60 by reading.

**Agreement.** Class, expected outcome and expected tier: 60 of 60. The set of rules with a `refer` ground differed on 5 customers and the set with a gap ground on 6 (7 customers in all).

**Decisions (the P5-prep sub-orchestrator's), applied in `build_customers.py`:**

| Customer | Difference | Decision |
|---|---|---|
| C010 | "It was free, the bank pays": the builder read a stated premium of zero (`refer`), the labeller a customer who knows no amount (gap) | Gap. "Free" is not a figure anyone can read back. The fact sheet now says plainly that he knows of no amount and thinks the shortfall was processing charges. Still `refer`, on `loan_funded` |
| C015 | The labeller added `consent` and `sale_conduct` and read recall as a gap | Adopted. The fact sheet now says nobody explained the second paper and she does not know what she agreed to by signing it |
| C016 | The labeller added `consent` and `loan_funded` | Adopted. The fact sheet now says he knows the money came short but not why, and does not know what he agreed to by clicking |
| C035 to C038 (took nothing) | The builder listed grounds under every product question; the labeller listed only recall and consent (and `kind` for C037 and C038) | The labeller's reading. A call that hears a firm "I took nothing" asks one follow-up and what the customer agreed to, and no product question (`DESIGN.md` section 5 step 5). The other grounds moved to `notes` as "not reachable when the denial stands"; `beliefs` is unchanged |
| C040 | The fact sheet contradicted itself on whether she was told it was needed | Fixed in the fact sheet (she was told it was needed). Gold unchanged |
| C002 | The fact sheet did not say how long she thinks it runs | Added ("until the loan ends"). Gold unchanged |

Changed rows: `customers.jsonl` C002, C010, C015, C016, C040; `gold.jsonl` C010, C015, C016, C035 to C038. No record changed. No class or tier changed. After the change: `customers.jsonl` sha256 `a1a06191…`, `gold.jsonl` sha256 `979f6120…`.

**Not done.** The five rewritten fact sheets were not labelled blind a second time; their final grounds rest on the decisions above. The labeller also pointed out five premiums that sit just over the 1% line (C005, C014, C023, C028, C039); they stay as written and are gaps under the rule. No person has reviewed any label.

## 2026-11-10, first freeze (stage 1) and the words (stage 2)

- **Stage 1, 12:14 UTC.** `customers.jsonl`, `gold.jsonl`, `topics.json`, `closed_script.json` and `records/` frozen by sha256 in `FROZEN.json` (`inputs`). No customer words existed.
- **Words written after it.** `eval/p5/write_customers.py run` (it refuses to run unless the five inputs match `FROZEN.json`): 60 customers, two requests each (open, closed), 15 customers per writer model per language (`google/gemini-3.7-flash`, `deepseek/deepseek-v4.1-flash`). A third candidate, `qwen/qwen3.8-flash`, was rejected in the smoke test on two invented example customers, before the run: it wrote Hinglish in Latin script only.
- **Mechanical regenerations.** 32 attempts were repeated: 31 because at least one reply held no Devanagari, 1 because the model's output did not validate (counts of the rows' `checks.regenerated` entries; the saved requests show one more invalid output, P5-C044's third DeepSeek attempt, which the rewrite below replaced). 18 of the 60 customers had at least one repeated attempt. No reply was regenerated or edited for its content.
- **One rewrite by the other model.** P5-C044's open-call bank came back in Latin-script Hindi on all three attempts from DeepSeek (53 of 53 replies). `write_customers.py rewrite` sent the identical request to Gemini (three attempts, the third kept). Its closed-call replies are DeepSeek's. The row records this under `checks.rewritten` and `writer_model_by_arm`. This step was not in the script when the run started: the sub-orchestrator added it on seeing the fault, before the words were frozen and before any audio. It is a wrong-script fault, which the contract allows regenerating.
- **Kept with a failed check.** 13 replies in 7 customers are Hinglish replies wholly in English ("One lakh fifty thousand.") and fail the "contains Devanagari" check after three attempts. They are kept as written and listed in each row's `checks.failed`.
- **Stage 2.** `replies.jsonl`, `closed_statements.jsonl` and `writer_requests.jsonl` (all 153 requests, with the full messages as sent) frozen by sha256 in `FROZEN.json` (`words`). No audio exists.
- OpenRouter spend for the writer models, smoke tests and the rejected model included: about USD 1.20 by the client's ledger.

## 2026-11-10, version 2: the `defer` replies, after independent verification

No audio existed. Full report: `eval/p5/VERIFY.md`.

- **Why.** The verifier found that the writers had made the open call's `go_along` reply a shortened `own` reply that still states the belief ("एफडी है"), while the closed call's `go_along` is a yes. With that, the open arm would hear every belief at every disposition level and the comparison with the closed arm would be close to true by construction.
- **What changed.** `topics.json` gained the section `open_defer` (a `defer` variant: a few words that give no information about the matter, for the 14 open topics that have a group) and a revised `disposition.rule`: a customer who gives way says `defer` in the open call and `go_along` in the closed call. The open call's `go_along` replies stay in the file as a separate "terse customer" condition for the text path.
- **Freeze.** `FROZEN.json` version 2. Of the five inputs only `topics.json` changed; `customers.jsonl`, `gold.jsonl`, `records/` and `closed_script.json` have the same sha256 as in version 1, which is kept under `history`.
- **Words.** `write_customers.py add-defer`: one new request per customer to the model that wrote its open replies (64 requests with 4 mechanical regenerations: 2 with no Devanagari, 2 over 60 characters; none kept with a failed check). 840 `defer` replies. Every other field of every row is byte-identical to version 1 (checked by removing the `defer` additions and comparing), and the 153 earlier requests still rebuild byte for byte. `writer_requests.jsonl` now holds 217 requests.
- **Known about the `defer` replies** (the builder's reading of all 840; none was changed): none names the product, gives a figure or says "I don't know"; 3 carry some content (P5-C024 `anything_else` and `how_paid`, P5-C003 `how_often`) and about 14 more are borderline, among them assents ("सब okay है", P5-C042). Many say "leave that, move on", which the dialogue may read as unwillingness and end the call: that outcome is counted, not avoided. Three customers who ask for a later call do so in every `defer` reply (P5-C049, P5-C057, P5-C058).
- **Also recorded after verification, with no data change:** `eval/p5/gold-rules.md` now lists where it is looser than the code, and the tier is scored only as `refer` or not; the reply faults and the two topic paraphrases the verifier found are listed in `README.md`.
- OpenRouter spend for this step: about USD 0.23.
