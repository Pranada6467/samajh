# Datasheet: P5b customer set

## What it is

24 synthetic customers (12 Hindi, 12 Hinglish), built the way P5 was built (`data/p5/README.md`), for a check after a fix round. P5b was written on 2026-11-13, after the first P5 run's failures were known to the team, by a builder and writer models that were shown nothing about those failures; it exists to check fixes made after that run.

Each customer has:
- a plain-English **fact sheet**;
- a **lender record** that is compliant on its face;
- a **gold label**;
- a **bank of spoken replies**, in the same shape as P5's: 70 open replies (28 `own`, 13 `again`, 12 `go_along`, 14 `defer`) and 20 closed replies (10 `own`, 10 `go_along`).

The replies are text. Nothing has been voiced or run.

Everything is invented:
- Loan ids read `TEST-P5B-LN-001` to `-024`, and record labels start "Synthetic P5b record.".
- Every fact sheet says "(An invented person.)".
- The surnames (Kritrim, Prayogik, Abhyasi, Nakli, Pratiroop) are made-up words. They also start the insurer names, each of which ends "(synthetic)".
- The four lenders are "नमूना …" ("sample").
- No first name, surname, sanctioned amount, premium or gold belief set is taken from P5; the build checks this.
- A pattern search found no phone number, account number, Aadhaar, PAN or IFSC.

## Files

All files are in `data/p5b/`. Digests are sha256.

| File | Holds | Frozen |
|---|---|---|
| `build_customers.py` | the 24 customers as Python, the grounds check (P5's table, unchanged) and the freshness checks against P5 | `other` (`b7c357d0…`) |
| `customers.jsonl` | id, kind, underlying, language, record_id, speaker, fact_sheet | Stage 1 (`2a0e2fc2…`) |
| `records/` | 24 `CallRecord` files, `p5b-c001.json` to `p5b-c024.json` | Stage 1 (`ec5d44b0…`, digest of the files) |
| `gold.jsonl` | beliefs, grounds with citations, class, outcome, tier, notes, rationale | Stage 1 (`1983b491…`) |
| `topics.json` | P5's with only the disposition seed changed to `samajh-p5b-2026-11-13` | Stage 1 (`523df0df…`) |
| `closed_script.json` | P5's, byte-identical | Stage 1 (`1874be1d…`) |
| `closed_statements.jsonl` | the closed call rendered per customer | Stage 2 (`2eb5458c…`) |
| `replies.jsonl` | the words | Stage 2 (`3a17acfb…`) |
| `writer_requests.jsonl` | all 85 requests to the writer models, messages as sent | Stage 2 (`59974372…`) |
| `write_customers.py` | P5's writer script; paths changed and `check_script` narrowed (CHANGELOG) | `other` (`e9aaddee…`) |
| `FROZEN.json` | the digests and freeze times: Stage 1 at 2026-11-13 05:00:56Z, before any words; Stage 2 at 05:10:26Z, before any audio | n/a |
| `CHANGELOG.md` | allocation, blind labelling, the sheet edit, the seed diff, the check change, the run | n/a |

```
uv run python data/p5b/build_customers.py               # rewrites customers, gold, records; bytes should not change
uv run python data/p5b/write_customers.py inputs-hash   # the five Stage 1 digests
uv run python data/p5b/write_customers.py render-closed --out closed_check.jsonl   # no LLM
```

The writers sampled at temperature 0.8, so a rerun reproduces `replies.jsonl` only from the local LLM cache.

## Counts

P5's 60 were scaled to 24 by largest remainder; the CHANGELOG has the table.

| Kind | hi | hi-en | Gold class | Expected tier or outcome |
|---|---|---|---|---|
| misled | 3 | 3 | problem 6 | refer 6 |
| uninformed | 1 | 1 | knowledge_gap_only 1, problem 1 | understanding_gap 1, refer 1 |
| ordinary_informed | 2 | 1 | knowledge_gap_only 3 | understanding_gap 3 |
| well_informed | 1 | 1 | no_problem 2 | clear 2 |
| took_nothing | 1 | 1 | problem 2 | refer 2 |
| coached | 1 | 1 | problem 2 | refer 2 |
| in_a_hurry (misled underneath) | 0 | 1 | problem 1 | refer 1 |
| fraud_suspicion (ordinary_informed underneath) | 1 | 0 | knowledge_gap_only 1 | understanding_gap 1 |
| third_party (father; flatmate, evasive) | 1 | 1 | procedural 2 | wrong_party 2 |
| refusal | 0 | 1 | procedural 1 | declined 1 |
| call_back_later (names a day) | 1 | 0 | procedural 1 | call_back_later 1 |
| language_switch (Telugu) | 0 | 1 | procedural 1 | language_switch 1 |
| **Total** | **12** | **12** | problem 12, knowledge_gap_only 5, no_problem 2, procedural 5 | refer 12, understanding_gap 5, clear 2, no tier 5 |

**Records (24).**
- Lender: bank 12, NBFC 12, under four names.
- Loan: personal 14, gold 10.
- Premium paid: from the loan 20, separately 4. Required for the loan: 4.
- Consent on file: signed form 8, OTP 7, digital click 6, recorded call 3.
- Cancellation window: 15 days 12, 30 days 12.
- Premium: INR 3,060 to 69,600 (2.8% to 6.2% of the loan).
- Cover equals the sanctioned amount in 23 of 24. Term equals tenure in 21 of 24.
- Fixed as in P5: one `credit_life` product, consent on file, provider choice offered, `one_time_payment`.

**Writer model.** Each model wrote 6 hi and 6 hi-en customers, and every arm of a customer is by the same model. Requests: 85 (open 37, closed 24, `defer` 24).

## How gold was set

- Gold is the customer's state, from the fact sheet and record under `eval/p5/gold-rules.md`. No rule engine, extractor or dialogue was run to set it.
- The builder wrote each customer's beliefs and a citation per ground. The build fails unless the rules that fire are the rules cited.
- **Blind second labelling.** A labeller given only the rules, the sheets and the records agreed on class, outcome and tier for 24 of 24.
  - The grounds differed only on C014 and C015, where the labeller added `loan_funded`.
  - The builder's reading was kept: after a held denial, only reachable grounds count, as in P5. The labeller's reading is in `notes`.
- After the labelling, one steering line was removed from the C016 and C017 sheets; gold did not change.
- Gold is looser than the code in the places `eval/p5/gold-rules.md` lists. Score the tier only as `refer` or not.
- In C008, C014, C015 and C017, an undecided "required?" answer may make a correct call end `incomplete`; all four are `refer` on other grounds.

## How the words were written

The prompts, models, temperature and mechanical checks are P5's (`data/p5/README.md`, "How the words were written"):
- three requests per customer (open, closed, `defer`);
- the open and `defer` requests saw the fact sheet and topics only, never the record;
- the closed request saw the rendered statements.

Outcome:
- 13 repeated attempts in 8 customers: 12 for no Devanagari and 1 for invalid output.
- 7 Hinglish replies in 5 Gemini-written open banks lack Devanagari and are kept (`checks.failed`).
- No `defer` reply was repeated or failed. No reply was edited.
- Spend: USD 0.48.

## How these customers are and are not independent of the builders

Independent:
- No project member or model wrote or edited a reply.
- Gold was fixed before the words, and both were frozen before any audio.
- The builder was told not to open `samajh/dialogue`, `samajh/rules`, `samajh/extract`, `samajh/scenarios`, `data/prompts`, `data/scenarios`, `eval/text_path`, `tests/`, `eval/p5/runs/`, `eval/p5/REPORT.md` or `references/reviews/iter3/`, and did not.
- The writer models saw only the fact sheets, the topics and the rendered closed statements.

Not independent:
- **Authorship.** The project chose the kinds and mix and wrote every situation, belief, record and gold row; one author wrote all 24.
- **Withholding broke once, after Stage 1 was frozen.** During the run, a diff of `samajh/types.py`, read to diagnose a failed check, showed the builder new enum names from another lane. The sheets and gold were frozen by then, and the writers never saw it.
- **Process imports.** `write_customers.py` imports `samajh.server.records`, which loads the whole `samajh.server` package into the process without calling it. `build_customers.py` loads the records module by file path and does not.
- **P5's limits carry over:** the topics paraphrase the bot's questions; every sheet settles every topic; two writer models, one prompt; no fluent person has read a sheet, reply or closed line; the records are face-compliant.

## Using the set

- Never tune on it. Before any audio, recompute the digests against `FROZEN.json` and stop on a mismatch.
- The unit is the customer (n = 24; 12 `problem`). Per-kind n runs from 1 to 6, so intervals are very wide.
- Report counts with n, by kind, arm and writer model, never as one pooled rate. A referral is evidence for human review, never a finding.
