# P5b customer set: changes

## 2026-11-13, Stage 1: build, blind second labelling, one sheet edit, freeze

No customer words and no audio existed when these changes were made.

**What was built.** `build_customers.py` (an adapted copy of `data/p5/build_customers.py`; set seed `samajh-p5b-2026-11-13`) wrote 24 fact sheets, 24 records and 24 gold rows. The grounds table (`grounds()`) is P5's, unchanged; the build fails unless the rules that fire are exactly the rules cited, and unless no first name, surname, sanctioned amount or premium of a P5 record is reused and no P5b belief set equals a P5 gold belief set. The script loads `samajh/server/records.py` by file path, so the `samajh.server` package is not imported (the P5 script imported it).

**Allocation.** P5's 60 scaled to 24 by largest remainder (quota = P5 count x 24/60; floors give 18; the six remaining seats went to the largest remainders, ties in P5's kind order):

| Kind | P5 | Quota | P5b | hi / hi-en |
|---|---|---|---|---|
| misled | 14 | 5.6 | 6 | 3 / 3 |
| uninformed | 6 | 2.4 | 2 | 1 / 1 |
| ordinary_informed | 8 | 3.2 | 3 | 2 / 1 |
| well_informed | 6 | 2.4 | 2 | 1 / 1 |
| took_nothing | 4 | 1.6 | 2 | 1 / 1 |
| coached | 4 | 1.6 | 2 | 1 / 1 |
| in_a_hurry | 2 | 0.8 | 1 | 0 / 1 |
| fraud_suspicion | 2 | 0.8 | 1 | 1 / 0 |
| third_party | 6 | 2.4 | 2 | 1 / 1 |
| refusal | 3 | 1.2 | 1 | 0 / 1 |
| call_back_later | 3 | 1.2 | 1 | 1 / 0 |
| language_switch | 2 | 0.8 | 1 | 0 / 1 |

The 0.4 remainders (uninformed, well_informed, third_party) missed a seat. Even kinds split half and half; the extra customer of each of the six odd kinds alternates hi, hi-en in P5's kind order, giving 12 and 12.

**Builder's choices (not derived from P5):**
- `in_a_hurry` is `misled` underneath (C018) and `fraud_suspicion` is `ordinary_informed` underneath (C019); P5 had one of each per kind.
- The language switch (C024) asks for Telugu, not a call language. P5 used Tamil and Bengali.
- Two misled customers hold a belief about the type of cover: C002 thinks it is a health cover paying hospital bills up to two lakh, C018 an accident cover paying one lakh. No rule reads the type of insurance, so neither has a `kind` ground; each is `refer` on `cover` (the stated figure against the record's), C018 also on `bundling`.
- C005 holds the reverse `loan_funded` belief (the record says paid separately; he believes it was cut from the loan), a direction P5 did not have.
- Lenders: four invented names, two per type (नमूना बैंक, नमूना भारत बैंक, नमूना फ़ाइनेंस, नमूना क्रेडिट).

**Blind second labelling.** A labeller given only `eval/p5/gold-rules.md`, `customers.jsonl` and the records (no kind, no gold) labelled all 24. Class, expected outcome and expected tier: 24 of 24 agree. Grounds differed on two customers:

| Customer | Difference | Decision (coordinator's) |
|---|---|---|
| C014, C015 (took nothing) | The labeller added a `refer` ground on `loan_funded` ("does not know of any payment") | The builder's reading kept: only grounds reachable after a held denial count, the reading P5 used for C035 to C038. The labeller's reading is recorded in both gold rows' `notes` |

**Sheet edit after the labelling.** C016 and C017 (coached) had one extra line in `what_you_know` telling the writer that the customer would mention the coaching when asked whether anything else happened. It was removed so the coached customers are built as in P5: the coaching stays a fact in the sheet, and nothing tells the writer when to voice it. The cited line indices moved by one; the grounds, class and tier did not change. The labeller had seen the sheets with the line.

Changed by these two steps: `customers.jsonl` rows C016 and C017 (`fact_sheet` only); `gold.jsonl` rows C014, C015 (`notes`: the labeller's reading) and C016 (`notes`: the sentence about the removed line dropped). No record changed (records digest `ec5d44b0…` before and after). `customers.jsonl` sha256 `0ae47bec…` before, `2a0e2fc2…` after; `gold.jsonl` `f098b254…` before, `1983b491…` after.

**Topics and closed script.** `topics.json` is P5's with one line changed (the only seed string in either file):

```
305c305
<     "seed": "samajh-p5-2026-11-10",
>     "seed": "samajh-p5b-2026-11-13",
```

The descriptive "about" texts still say "P5". `closed_script.json` is a byte copy of P5's (sha256 `1874be1d…`).

**Freeze (Stage 1).** `customers.jsonl`, `gold.jsonl`, `topics.json`, `closed_script.json` and `records/` frozen by sha256 in `FROZEN.json` (`inputs`) at 2026-11-13 05:00:56Z. No customer words existed.

**Not done.** The edited C016 and C017 sheets were not labelled blind again (the edit removed a line and changed no fact). No person has reviewed any sheet, record or label.

## 2026-11-13, the words (Stage 2)

No audio existed.

- **Writer script.** `write_customers.py` is a copy of `eval/p5/write_customers.py`. Its prompts, models (`google/gemini-3.7-flash`, `deepseek/deepseek-v4.1-flash`, alternating within each language by sorted id), temperature (0.8), mechanical checks and retry rule are P5's. Two kinds of change were made:
  - **Paths:** `data/p5b` and its `FROZEN.json`, in four lines.
  - **`check_script`, narrowed mid-run.** During the run, `samajh/types.py` gained enum values in another lane. The original check required a closed-script line for every value of `ConsentMethod`, so the resume stopped before sending any request. The check now requires a line for every consent method the P5b records use (signed form, OTP, digital click, recorded call), and that every line names a known method. The rendered statements only ever use the records' methods. No prompt, model, reply or frozen input changed. All 24 closed requests sent equal the `render-closed` output: 20 sent before the change and 4 after.
- **Run 1** (`run`, cap USD 0.38) wrote C001 to C020, then stopped at the cap (spent USD 0.3623).
- **Run 2** (`run --resume`, after the check was narrowed) wrote C021 to C024 (USD 0.0466).
- **`add-defer`**: 24 requests, none repeated, none failed (USD 0.0725).
- **Repeated attempts, mechanical faults only:** 13 in 8 customers, all on the open arm:
  - no Devanagari: 12 (C002 ×2, C006 ×2, C008, C011, C015 ×2, C018 ×2, C022 ×2);
  - invalid output: 1 (C014's first DeepSeek open attempt).
- **Kept with a failed check:** 7 Hinglish replies with no Devanagari, all in Gemini-written open banks. They are C002 `how_much.go_along`, C006 `how_much.go_along`, C015 `year_of_birth.own`, `how_much.go_along` and `say_amount_again.own`, C018 `how_much.own`, and C022 `year_of_birth.own`.
- No rewrite by the other model was needed. No reply was edited or regenerated for its content.
- **Stage 2 freeze.** `replies.jsonl`, `closed_statements.jsonl` and `writer_requests.jsonl` frozen by sha256 in `FROZEN.json` (`words`), with `build_customers.py` and `write_customers.py` under `other`, at 2026-11-13 05:10:26Z.
- **OpenRouter spend** by the client's own count: USD 0.4814 in all, against a budget of 0.60.
