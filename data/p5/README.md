# Datasheet: P5 customer set

## What it is

60 synthetic customers for evaluation P5 (`references/pilots/P5-contract.md`): customers the builders did not script. Each is met by the open Samajh call (the callback under RBI's para 85Y post-sale feedback rule (101Y for NBFCs)) and by a matched closed call that reads ten record statements and asks "is that correct?". Each has a plain-English **fact sheet**, a **lender record** compliant on its face, a **gold label**, and a **bank of spoken replies** in Hindi (30 customers) or Hinglish (30): 67 to the open call's 28 topics (`own`, `again`, `go_along`, `defer`) and 20 to the closed call's ten statements (`own`, `go_along`). Version 2 added `defer` after independent verification (`eval/p5/VERIFY.md`). Prepared 2026-11-10; the replies are text and nothing has been voiced or run.

Everything is invented: loan ids read `TEST-P5-LN-001` to `-060`; record labels start "Synthetic P5 record."; fact sheets say "(An invented person.)"; the five surnames (Namoona, Udaharan, Kalpanik, Banawati, Pareekshan) are made-up words that also start the insurer names, each ending "(synthetic)"; both lenders are "नमूना ..." ("sample"). A pattern search found no phone number, account number, Aadhaar or PAN. Ids are `P5-Cnnn`; below, `Cnnn`.

## Files

Paths are in `data/p5/` unless shown. `FROZEN.json` is version 2, with version 1 under `history`. Version 2 re-froze `topics.json`, the only input that changed, at Stage 1 (2026-11-10 13:04:37Z) and the words at Stage 2 (13:11:36Z); version 1 was frozen at 12:14:20Z and 12:30:38Z. No words existed at Stage 1 and no audio at Stage 2. Digests are the first 8 characters of sha256.

| File | Holds | Frozen |
|---|---|---|
| `build_customers.py` | the 60 customers as Python (sheets, records, beliefs, citations) and the check that derives gold grounds | listed under `other` (`6f0891e5`), not a gate |
| `customers.jsonl` | id, kind, underlying, language, record_id, speaker, fact_sheet | Stage 1 (`a1a06191`, same in v1) |
| `records/` | 60 `CallRecord` files, `p5-c001.json` to `p5-c060.json` | Stage 1 (`4ff92b0e`, digest of the files, same in v1) |
| `gold.jsonl` | `beliefs`, grounds with citations, class, outcome, tier, notes, rationale | Stage 1 (`979f6120`, same in v1) |
| `topics.json` | the 28 open topics and variants, `open_defer` (the `defer` definition and its 14 topics), the ten closed statements, the disposition rule | Stage 1 (`95351109`; v1 `a2fbb50c`) |
| `closed_script.json` | closed-call wording templates in hi and hi-en ("model-written, no human review") | Stage 1 (`1874be1d`, same in v1) |
| `closed_statements.jsonl` | the closed call rendered per customer from record and script | Stage 2 (`79e6fae7`, same in v1) |
| `replies.jsonl` | the words: `open`, `closed`, `writer_model`, `writer_model_by_arm`, `checks` | Stage 2 (`cb44eecb`; v1 `ba71c73e`) |
| `writer_requests.jsonl` | all 217 requests to the writer models, messages as sent | Stage 2 (`b8d4b763`; v1 `7a002d57`) |
| `FROZEN.json` | digests (`inputs`, `words`, `other`), times, `history` | n/a |
| `CHANGELOG.md` | blind-labelling decisions, the freezes, regenerations, version 2 | n/a |
| `eval/p5/gold-rules.md` | how gold is set; its last section lists where it is looser than the code | `other` (`e6d78c6c`; v1 `dd424619`) |
| `eval/p5/write_customers.py` | writer prompts, checks, commands (`run`, `rewrite`, `add-defer`); refuses to write words unless Stage 1 matches | `other` (`d5bd7315`; v1 `0852e9da`) |
| `eval/p5/RUNNER-PLAN.md` | Part 1: run decisions fixed before audio; Part 2: research notes | not hashed |
| `eval/p5/VERIFY.md` | the independent verifier's report and what was done about each item | not hashed |
| `references/pilots/P5-contract.md` | the contract | not hashed |

```
uv run python data/p5/build_customers.py                  # rewrites customers.jsonl, gold.jsonl, records/; bytes should not change
uv run python eval/p5/write_customers.py inputs-hash      # the five Stage 1 digests
uv run python eval/p5/write_customers.py render-closed --out closed_check.jsonl   # no LLM; diff with closed_statements.jsonl
(cd data/p5/records && shasum -a 256 *.json | shasum -a 256)   # the records digest
shasum -a 256 data/p5/replies.jsonl data/p5/closed_statements.jsonl data/p5/writer_requests.jsonl \
  data/p5/build_customers.py eval/p5/write_customers.py eval/p5/gold-rules.md
```

`write_customers.py run` and `add-defer` refuse to start unless the Stage 1 digests match, and refuse while their replies exist unless given `--resume`. The writers were sampled at temperature 0.8, so a rerun reproduces `replies.jsonl` only from the local LLM cache (`.samajh/cache/openrouter`, gitignored). A machine without it gets different words.

## Counts

**Customers by kind, language and gold.**

| Kind | What the customer is | hi | hi-en | Gold class | Expected tier or outcome |
|---|---|---|---|---|---|
| misled | holds a belief the record contradicts (5 take it for a deposit or FD) | 7 | 7 | problem 14 | refer 14 |
| uninformed | signed without understanding | 3 | 3 | knowledge_gap_only 4, problem 2 | understanding_gap 4, refer 2 |
| ordinary_informed | knows what it is; some figures rough | 4 | 4 | knowledge_gap_only 8 | understanding_gap 8 |
| well_informed | states every fact as on the record | 3 | 3 | no_problem 6 | clear 6 |
| took_nothing | says they took only the loan, and keeps to it | 2 | 2 | problem 4 | refer 4 |
| coached | was told to say yes to the checking call | 2 | 2 | problem 4 | refer 4 |
| in_a_hurry | short answers; underlying ordinary_informed 1, misled 1 | 1 | 1 | knowledge_gap_only 1 (hi), problem 1 (hi-en) | understanding_gap 1, refer 1 |
| fraud_suspicion | asks if the call is genuine, then goes on; underlying ordinary_informed 1, misled 1 | 1 | 1 | problem 1 (hi), knowledge_gap_only 1 (hi-en) | refer 1, understanding_gap 1 |
| third_party | answers the borrower's phone | 3 | 3 | procedural 6 | wrong_party 6 |
| refusal | refuses (C054 only after the year-of-birth check) | 2 | 1 | procedural 3 | declined 3 |
| call_back_later | asks for a later call | 1 | 2 | procedural 3 | call_back_later 3 |
| language_switch | asks to switch (C059 Tamil, C060 Bengali) | 1 | 1 | procedural 2 | language_switch 2 |
| **Total** | | **30** | **30** | problem 26, knowledge_gap_only 14, no_problem 6, procedural 14 | refer 26, understanding_gap 14, clear 6, no tier 14 |

Completed calls are expected for 46 customers. Gold never expects `incomplete`. Refer grounds (a customer can have several): kind 12, belief_mismatch 10, bundling 9, consent 9, loan_funded 7, sale_conduct 7, recall 4. None comes from the record.

**Writer model.** Within each language, customers sorted by id alternate Gemini, DeepSeek. C044's open and `defer` arms are Gemini's (rewrite, below).

| Writer | hi | hi-en | Open arm | Closed arm | `defer` arm |
|---|---|---|---|---|---|
| `google/gemini-3.7-flash` | 15 | 15 | 31 | 30 | 31 |
| `deepseek/deepseek-v4.1-flash` | 15 | 15 | 29 | 30 | 29 |

**Replies.** Per customer: 67 open (28 `own`, 13 `again`, 12 `go_along`, 14 `defer`) and 20 closed, 87 in all. In all: 4,020 open (1,680, 780, 720, 840) and 1,200 closed, 5,220. The 14 opening-kind customers hold 280 closed replies the contract never uses. **Requests:** 217 (open 89, closed 64, `defer` 64), 3 of them C044's rewrite.

**Records (60).**

| Field | Counts |
|---|---|
| Lender | bank 31, NBFC 29 |
| Loan | personal 32, gold 28 |
| Premium paid | from the loan 50, separately 10 |
| Product required for the loan (record) | yes 8, no 52 |
| Consent method on file | signed form 21, OTP 18, digital click 14, recorded call 7 |
| Cancellation window | 30 days 31, 15 days 29 |
| Premium | INR 2,050 to 148,000 (2.7% to 13.0% of the sanctioned amount) |
| Cover | INR 70,000 to 1,500,000; equals the sanctioned amount in 59 of 60 (C034: 180,000 on 200,000) |
| Product term | 6 to 60 months; equals the loan tenure in 29 of 60 |
| Fixed in all 60 | one `credit_life` product, consent on file, provider choice offered, `one_time_payment` |

## How gold was set

Gold is the customer's state, from the fact sheet and record under `eval/p5/gold-rules.md`. No rule engine, extractor or dialogue was run to set it.

- The builder wrote each customer's `beliefs` and a citation per ground. A table in `build_customers.py` (`grounds()`) restates the rules; the build fails unless the rules it fires are the rules cited. The script imports only `samajh.server.records` (to validate records), which loads the dialogue, rules and extractor modules into the process; the script calls none.
- A second subagent, given only the sheets, records and rules, labelled all 60 blind: 60 of 60 agree on class, outcome and tier; the grounds differed on 7 customers, each decided in `CHANGELOG.md` (five sheets changed; for C035 to C038 unreachable grounds moved to `notes`). No class or tier changed. Gold was frozen before any words existed, and version 2 did not touch it.
- `gold-rules.md` is looser than the code in three places (its last section): an undecided answer (the code gives a gap that makes the tier `incomplete`), a hedged cover figure, and `recall_unmatched`. Tier is therefore scored only as `refer` or not.

## How the words were written

Two models from outside the project's families (Anthropic models build; `openai/gpt-6-luna` extracts; `mistralai/mistral-small-3.2-24b-instruct` classifies turns): `google/gemini-3.7-flash` and `deepseek/deepseek-v4.1-flash`, through `samajh/clients/llm.py`. Three separate requests per customer: open, closed and (version 2) `defer`, the last to the model that wrote the open replies.

- **Saw:** a fixed system prompt (spoken language only, stay inside the sheet, numbers as words, the variants), the fact sheet, and the caller topics: 28 (open), the ten statements as rendered, which carry the record's provider, premium, cover, term, window, payment source and consent method (closed), or the 14 grouped topics (`defer`). The `defer` request replaces the variant lines with one definition: "what this person says when they do not want to think about it or commit to anything and only want the caller to move on: a few words that give no information about the matter itself (no fact, no figure, no name of anything, and not that they do not know)".
- **Never saw:** the record (open and `defer`), `data/prompts`, the code or word lists in `samajh/dialogue`, `samajh/rules` and `samajh/extract`, the scenario set, gold. `writer_requests.jsonl` holds every request as sent.
- **Mechanical checks only:** empty, a digit, over 240 characters (60 for `go_along` and `defer`), no Devanagari, more than three Latin words in a row (Hindi). A failing set was asked again at most twice.
- **Outcome:** 36 repeated attempts in 21 customers (version 1: 32 in 18; `defer`: 4). One rewrite: C044's open replies came back in Latin script on all three DeepSeek attempts, so the same request went to Gemini (third attempt kept; closed replies stay DeepSeek's), a step added after the fault was seen, before the freeze and any audio. 13 replies in 7 customers still lack Devanagari and are kept (`checks.failed`); no `defer` reply failed. No reply was edited.

## How these customers are and are not independent of the builders

Independent:
- The words: no project member or model wrote or edited a reply. The writers saw no bot line, word list, rule, extractor prompt or scenario (the topics paraphrase the bot's questions; see below) and are from other families than the extractor and the classifier.
- Gold was fixed before the words existed.
- The builders of the sheets, writer script, P4 cards and blind labels were told not to open `samajh/dialogue`, `samajh/rules`, `samajh/extract`, `samajh/scenarios`, `data/prompts`, `data/scenarios`, `eval/text_path` or `tests/`. The verifier read their four transcripts: zero tool calls on a forbidden path. The two build scripts import `samajh.server.records`, which loads the dialogue, rules and extractor modules into the process without calling them.

Not independent:
- The project (Anthropic models under the sub-orchestrator's brief) chose the kinds and mix and wrote every situation, belief, record, gold row, topic description and the closed script; one author wrote all 60 situations. It defined `defer` after seeing the first words, before any audio.
- The sub-orchestrator who wrote the topics and gold rules had read the design and the dialogue's contract (not its word lists or the scenario rows), `data/scenarios/README.md` (the datasheet, not the rows), `samajh/server/prepare.py` (which holds three builder-written personas' replies) and `DESIGN.md` section 5 (which quotes example lines).
- The research agent behind Part 2 of the runner plan read `samajh/dialogue` files, `data/prompts/hi.toml` and `eval/text_path`; after its report the sub-orchestrator added the `want_a_person` topic and settled how unmapped lines are answered.
- The topics paraphrase what the bot asks, so replies answer the question the bot is known to ask. In the run the bot's line key picks the reply: a script for which topic comes when, not for the words. A bank cannot interrupt, drift or react to the bot's wording.
- Every sheet settles every topic; real customers do not. Two writer models, one prompt. No fluent person has read a reply, a sheet or the closed script.
- Gold applies the product's rules by reading, not by running code, and is looser than the code in three places.

## Using the set

- Never tune the dialogue, word lists, extractor, rules or prompts on it; a later headline needs a new set. Before any audio, recompute the digests and compare them with `FROZEN.json`; stop on a mismatch. A changed file needs a `CHANGELOG.md` entry and a new freeze; a reply is regenerated only for a mechanical fault, never edited.
- The unit is the customer (n = 60). Report counts per 100 with n, by kind, arm, level and writer model; never one pooled rate. Compare arms within the customer (exact McNemar, Wilson intervals).
- Disposition: one seeded draw `u` per customer and grouped matter, shared by the arms (`topics.json`). If `u < a` the customer gives way (`go_along` in the closed call, `defer` in the open call); otherwise `own`. On a re-ask a customer who gave way repeats that reply and one who answered gives `again`. The open `go_along` replies are a separate "terse customer" condition on text.
- Gold is the customer's state, not the words: a reply that fails to voice a belief counts against the arm. Score the tier only as `refer` or not.
- Open call: a miss on a `problem` customer is tier `clear` or `understanding_gap` (`incomplete` shown apart); `refer` on a `no_problem` or `knowledge_gap_only` customer is a false referral. Closed call: `confirmed` only when every statement gets a plain yes, else `not_confirmed`, which counts as caught. A failed call stays as "no result". The closed arm is not run for opening kinds.
- A `defer` reply carries no content by definition: do not present the open arm's curve as "the open call resists acquiescence". A referral is evidence for human review, never a finding of mis-selling. No pooled rate, "real customers", prevalence or Tamil or Kannada claim (contract section 8).

## Known limits

- Synthetic and text. No person has reviewed any sheet, record, label, reply, topic or closed line. Timbre voices and the simulated phone line will add faults of their own.
- Records are face-compliant, so nothing here tests record faults (no gold ground comes from a record). Each has one product.
- Small n: 14 `misled`, 26 `problem` in all, per-kind n from 2 to 14; intervals are wide.
- Gold is looser than the code: a correct call can end `incomplete` where gold says `understanding_gap` (C017 to C020; 14 customers' notes record an undecided answer); a hedged cover figure changes one ground (C026), no tier.
- Reply faults the verifier found, kept as written: C016 and C011 deny taking anything (`what_did_you_take`), which sends the call down the took-nothing branch and makes some of their gold grounds unreachable (tier still `refer`, for the wrong reason); C015 `how_paid` `own` says she does not know where from, against her sheet; C016 `how_paid` `own` and `how_often` `again` assert what his sheet says he does not know; C040 voices the coaching only in an `again` reply, so at level 0 it is likely never heard.
- Two topics are not what the bot asks: `anything_else` invites took-nothing customers to name the deduction (gold's `kind` ground for C037 and C038 rests on that reply), and `figure_read_back_wrong` and `benefit_read_back_wrong` tell the writer to say its own figure again, which gives parser-friendly replies (C002: "नहीं, वो eighteen thousand five hundred था, अठारह हज़ार पाँच सौ").
- Closed statement `c_source` (50 customers) matches a yes/no line of the frozen scenario set over 10 tokens in Hindi and 7 in Hinglish, and C041's sheet resembles scenario B02. The verifier judged the first convergent and the second a coincidence; the builders' transcripts show no access.
- `defer`: none names the product, gives a figure or says "I don't know" (the builder's reading of all 840). 3 carry content (C024 `anything_else` and `how_paid`, C003 `how_often`); about 14 more are borderline, among them assents (C042, "सब okay है"). Many say "move on", which the dialogue may read as unwillingness and end the call: counted, not avoided. C049, C057 and C058 ask for a later call every time. Five customers have one text for all 14 (see Checks). The request's system prompt still holds two sentences written for the other variants (my reading): "go_along replies a few words" and "answer as that person honestly would (often that they do not know)".
- The five rewritten sheets were not blind-labelled again. Five premiums sit just over the 1% line (C005, C014, C023, C028, C039) and are gaps by the rule.
- 13 Hinglish replies are wholly English ("One lakh fifty thousand.") and were kept. Writer model and kind are not crossed evenly: both `fraud_suspicion` customers and 8 of 14 `misled` are Gemini; 4 of 6 third parties are DeepSeek.
- The closed script is the project's own and unreviewed. It tells the customer the product is insurance and names the insurer; the open call does not. A closed `go_along` reply is not always a yes (see Checks).
- The six third parties answer the borrower's phone; gold expects `wrong_party` and that the loan is never named to them. Three are evasive at first by design (C048, C050, C051); their later replies ("I don't know") show only what a call that wrongly continues would hear.

## Checks made while writing this datasheet

| Checked | Found |
|---|---|
| The 11 digests in `FROZEN.json` (version 2) against the files | all 11 match |
| Rebuild, in memory, nothing written | the build reproduces `customers.jsonl`, `gold.jsonl` and 60 of 60 records; `render_closed` reproduces `closed_statements.jsonl`; the writer assignment reproduces `writer_model` for 60 of 60; each `defer` model equals the customer's open-arm model |
| Saved requests | 217 of 217 equal the messages rebuilt from the frozen inputs; 0 open or `defer` requests hold a loan id, lender name or provider name; 2 returned invalid output, as the CHANGELOG says: C054 open attempt 1 (repeated) and C044's third DeepSeek open attempt (replaced by the rewrite) |
| Repeated attempts | 36 in the rows' `checks.regenerated` and 36 requests with attempt above 1: open 27 no Devanagari and 1 invalid output, closed 4 no Devanagari, `defer` 2 no Devanagari and 2 over 60 characters (C020, C056, C060) |
| Replies | 0 empty, 0 with a digit, 0 `again` equal to its `own`, 0 `defer` equal to another version of its topic; 60 of 60 customers hold 67 open and 20 closed |
| `defer` repeats | 5 customers (C032, C039, C048, C054, C057) have one text for all 14 replies; 12 customers repeat a text (94 replies share a text with another in the same bank; 731 distinct texts in 840); all 12 are DeepSeek-written (of 29 DeepSeek `defer` banks; none of 31 Gemini) |
| `defer` content | the amount parser reads 0 as a figure; 0 contain पता, मालूम or "know"; 624 of 840 contain a move-on word (आगे, छोड़, बढ़, चलो, चलिए, move on, next, skip; word search); C049, C057 and C058 mention later or not now in 14 of 14 |
| Birth years | of 108 borrower replies, 107 give the record's year in full and 1 (C023, "सत्तर का साल") gives only the year-of-century; of 12 third-party replies, 11 give no year and C049 gives his own (1986, which his sheet holds) |
| Premium and cover figures (`defer` excluded) | of 322 replies from the 46 customers who complete the call (parsed with `samajh.amounts`, hedges read by eye), 312 agree with the gold belief; 10 replies in 3 customers state a figure where gold says none is known: C010 "zero rupees", C020 "ten or fifteen thousand", C039 "eighteen thousand" in the cover answer; each figure is on the sheet |
| Closed `go_along` (recounted) | 45 of 460 replies from those 46 customers say no or "don't know" instead of yes (word search, read through), in 10 customers (C002, C006, C008, C012, C015, C016, C028, C035, C036, C044); at level 1 none of the 10 can be `confirmed` |
| Script | Hindi replies with any Latin letter: 1 of 2,610 (C005, "compulsory"); Hinglish replies with no Devanagari: 13 of 2,610, the kept failures, all in Gemini-written open banks |
| Verifier's checks | see `eval/p5/VERIFY.md` (builders' tool calls, hashes, rebuilds, 17 labels); it did not read the sub-orchestrator's messages |
