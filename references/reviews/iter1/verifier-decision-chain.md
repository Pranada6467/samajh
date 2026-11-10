# Iteration 1 verification, part 1: the decision chain

Independent verifier, 2026-11-10. Scope: `samajh/types.py`, `samajh/amounts`, `samajh/rules`, `samajh/scenarios` with `data/scenarios`, `samajh/extract`, `samajh/pipeline.py`, `eval/text_path`.

## Verdict in brief

The chain is sound enough to build the voice path on. The rule engine and the code that checks the model's output held against every attack that code can stop, and every headline number I rescored came out as reported. Four things should change before any result is shown as a result:

1. A wrong belief that no question asks about is caught only when the customer volunteers it in the right words. The one frozen-set false clear (B03 in Tamil) is this, and I reproduced the same miss in Hindi and Kannada.
2. When a question is asked twice, the later answer silently replaces an earlier answer that would have flagged.
3. A fraction word the amount parser does not know is dropped without warning, and the extractor trims it out of the model's span, so the one check that would catch it passes.
4. E1 measures no difference between open and closed questions. Every yes/no miss in it is fixed by how the set was written.

## How to read this report

- **Reproduced** means I ran something or read the primary artifact, and the table says which. The work-package reports were my map, not my evidence.
- All probe scripts are in `references/reviews/iter1/probes/`. That folder is shared with the part 2 verifier. Mine are the eleven files named in this report.
- I did not read `references/reviews/iter1/judge.md`, so this report is not anchored on it.
- I am fluent in Hindi and English only. Tamil and Kannada judgements below are from a non-fluent reader and are marked.

What I ran, and what it cost:

| Item | Detail |
|---|---|
| Gnani API | No calls. Cached transcripts under `eval/amounts/run/` were read |
| OpenRouter | 0.008 USD, all in `extractor_live.py` (cap 0.10). Every other LLM-backed check ran from the cache with a cap of 0, so a miss would have raised instead of spending |
| Writes | Only under `references/reviews/iter1/`. The LLM client appended its own rows to `.samajh/ledger.jsonl` and added cache entries for the live probe |
| Git | Read-only: `log`, `diff`, `show --stat`, `status`, and `archive` into the scratch directory to rebuild older parser versions |
| Frozen set | Measured, never tuned on. Nothing was changed as a result of any measurement |

Two mistakes of my own, both corrected before any number here was taken:

- My first mutation run was invalid. The scratch copy failed at collection (a fixture file was missing), so every mutant looked killed. I made the harness refuse to run unless the unmutated copy passes, then reran everything.
- A helper in `extractor_attacks.py` replaced the read-back row together with the premium row. Fixed and rerun.

## 1. Claims checked

| # | Claim | Source | Reproduced | How |
|---|---|---|---|---|
| 1 | The whole test suite passes and ruff is clean | README, ORCHESTRATION | Yes, on the second run | `uv run pytest -q`: first run 3,089 passed and 5 failed, all in `tests/dialogue/test_llm_fallback.py`, a file another worker was editing at that moment (it passed when run alone). After commit `d1237e5` the rerun gave 3,094 passed, 0 failed. `uv run ruff check samajh tests eval`: clean. In-scope suites alone (`tests/core tests/scenarios tests/extract`): 1,526 passed |
| 2 | 1,223 core tests | README, ORCHESTRATION | No, stale | `tests/core` now collects 1,300. The second parser fix added 77 |
| 3 | 176 extractor tests, 50 scenario tests | README | Yes | `pytest --collect-only` |
| 4 | The scenario set verifies at version 3, `gold.jsonl` sha256 beginning `14e49b58` | DESIGN §9 | Yes | `uv run python -m samajh.scenarios verify` exits 0; `shasum -a 256` matches `FROZEN.json` |
| 5 | Gold was frozen before the extractor's frozen run | DESIGN §9, commit `0c94495` | Yes | Commit `0c94495` (10:52:52 IST) precedes `11fe56c` (11:19:59). `gold.jsonl` was last written at 10:51:34. In `.samajh/ledger.jsonl`, the first live request for each of the 1,224 cache keys the frozen run uses falls between 11:08:29 and 11:14:37 |
| 6 | The frozen set was run once and nothing was changed afterwards | DESIGN §9 | Partly | The ledger shows one burst of live requests for those keys and no earlier burst of that size for any model. No pipeline, rule, parser, extractor or scoring file was modified after 11:05:27, before the run began (`negation_probe.py`, a separate probe, was saved at 11:08:59). The cache keeps responses and not requests, so I cannot rule out a partial earlier run under a different prompt |
| 7 | The rule engine agrees with gold on 144 of 144, on both paths | DESIGN §9 | Yes | `uv run python -m samajh.scenarios check` reports 0 disagreements; my own recount on the scripted-extraction path gives 144 of 144 on verdict and flag set |
| 8 | 36 base cases: 9 clear, 25 flag, 2 unclear. 19 customers not informed; the yes/no call confirms 9 of them | DESIGN §9 | Yes | Counted from `gold.jsonl`; `scenarios stats` |
| 9 | 11 base cases templated on awards; remedies 5 refund, 4 conversion, 1 partial refund, 1 other | DESIGN §9 | Yes | Counted from the `template` field |
| 10 | One independent review agreed with 35 of 36 base cases at version 1 | DESIGN §9 | No | Version 1 gold is not in git (only its hash is recorded) and the reviewer's verdicts are not saved |
| 11 | Frozen run: 1 false clear of 108, 0 false alarms of 36, verdicts 143 of 144, product verdicts 143 of 144 | DESIGN §9, README | Yes | `rescore_frozen.py`: 3,391 requests, all cache hits, 0 USD. The builders' scorer and my own recount from verdicts agree |
| 12 | The one false clear is B03 in Tamil; by language 0, 0, 1, 0 of 27 | DESIGN §9 | Yes | Same run |
| 13 | Fields 2,163 of 2,180; 17 wrong in 16 calls; Tamil 8, Kannada 5, Hindi 2, Hinglish 2 | DESIGN §9 | Yes | Same run. All 17 are listed in its output |
| 14 | Flag precision 282 of 284 and recall 282 of 284; the two missed flags and the two extra `recall` flags | DESIGN §9 | Yes | Same run |
| 15 | E1 by stratum: coached 12/12 against 0/12, acquiescent 4/4 against 0/4, never asked 19/20 against 0/20, asked 40/40 against 40/40, informed 32/32 against 4/32 | DESIGN §9, README | Yes | Same run. What the table can support is in §3.3 |
| 16 | 0 of 802 spans not in the reply; 0 of 1,195 clause numbers out of range | DESIGN §7 | Yes | Same run. The second number is a weak check: see finding 9 |
| 17 | 3,391 LLM requests, 1,224 distinct | DESIGN §9 | Yes | Distinct cache keys in the ledger rows of my rescore |
| 18 | Cost 0.24589 USD, 0.00171 per transcript, 0.00007 per request; median 1.88 s, p90 3.38 s | DESIGN §7 | Yes | From `eval/text_path/runs/calls.jsonl` by generation id: 0.24598 USD, 0.00171, 0.00007, 1.878 s, 3.38 s |
| 19 | A transcript takes 20 to 24 requests | DESIGN §7 | Partly | 20 to 27 on the frozen set |
| 20 | The only record value in a bot turn shown to the model is the premium in a read-back (120) | CLAUDE.md, W5 report | Yes | The builders' check, plus my own lexical check for borrower name, birth year, loan id and provider: none found. One apparent hit was the word "Namoona", shared by the synthetic borrower and the synthetic bank |
| 21 | 70 of 1,604 frozen replies are word for word in the development set, 28 longer than three words | DESIGN §9 | Yes, and it understates | The builders' function gives 70 and 28. `overlap.py` finds 238 of 1,604 near matches: see finding 4 |
| 22 | Development set: verdicts 20, 20, 17, 13 of 20; fields 304, 303, 298, 285 of 304; false alarms 0, 0, 3, 7 of 7 (gpt-6-luna, Haiku, Mistral, Gemini) | DESIGN §7 | Yes | `rescore_dev.py`, all from the cache |
| 23 | Negation probe: 24, 24, 20, 18 of 24 | DESIGN §7 | Yes | The builders' `probe()` run from the cache with a cap of 0 |
| 24 | Mistral gave 18 of 20 in one run and 17 in another | DESIGN §7 | Yes | `runs/before-review/dev__comparison.md` shows 18; the current run shows 17 |
| 25 | Amounts note, before and after the parser fix: 214 (6 wrong) to 224 (1 wrong); 216 to 225; 219 to 238; 221 to 222; 221 to 221; 199 of 200 to 208 of 209 | `eval/amounts/REPORT.md`, DESIGN §6 | Yes, all six rows | `rescore_amounts.py` on `eval/amounts/run/stt.jsonl`, with the parser rebuilt at commits `808690e` (before), `f896c15` (first fix) and the working tree. The second fix changes none of the six |
| 26 | Before the fix, v3.0 on phone audio: 19 failures, 17 a wrong amount and 2 no answer | DESIGN §6 | Yes | Same script |
| 27 | Where the two readings did not agree (40 sentences), at least one was right 37 times | DESIGN §6 | Yes | Same script |
| 28 | The parser refuses the shapes it cannot decide | DESIGN §6, parser docstring | Partly | Refused in my probe: a number word before digits (5 of 5), Kannada "ondu kaalu" and "ondu mukkaalu", "3/4 lakh", and 35 of 36 romanised Hindi inputs. Not refused: see findings 3 and 8 |
| 29 | "एक लाख बीस" is read as 1,00,020 | W1 report | Yes | `amounts_fresh.py` |
| 30 | A fabricated span or an out-of-range clause number never becomes an answer | DESIGN §7 | Yes | `extractor_attacks.py` cases 1 to 4: `unclear` or an evidence gap each time |
| 31 | "Every quote must be a verbatim whole clause, never a fragment that stops short of a later 'not'" | CLAUDE.md | Partly | True through the extractor, which always keeps the whole reply. `to_beliefs` itself accepts a first-clause quote from a reply whose second clause denies it (case 9) |
| 32 | The lender's record never reaches the prompt | W5 report | Yes | Read `_prompt.py`: it takes a question and a reply. A mutant that adds a record value to the prompt is killed by 60 tests |
| 33 | The two identity checks are never sent to the model | W5 report | Yes | Mutant killed; case 14 confirms the reply is not sent |
| 34 | A matching premium passes only after a confirmed read-back of that same amount | DESIGN §6 | Yes | `engine_adversarial.py` (four read-back cases, all `unclear`); mutants M02, M10 and M34 killed |
| 35 | Silence is never a pass | DESIGN §6 | Partly | Of 29 missing-answer cases in `engine_adversarial.py`, 27 end `unclear` or `flag`. Two end `clear` by design: the kind question not asked when the customer named the product correctly in open recall, and the provider-choice question not asked for a product that is not required. A third silent pass is in finding 10 |
| 36 | A clean product does not clear another product on the same record | Task item 2 | Yes | Nine two-product cases in `engine_adversarial.py` |
| 37 | OpenRouter ledger total 0.52 USD | ORCHESTRATION | Partly | The ledger now reads 0.558 USD, with later workers and my 0.008 included |

## 2. Findings

Ranked by what they can do to a real call. Each has a minimal reproduction.

### High

**1. A belief that no question asks about is caught only if the customer volunteers it in words the model recognises. This is not a Tamil-only miss.**

- No question asks how often the premium is paid. A single-payment belief on a regular-premium product reaches the rules only through the screening call, when the customer happens to say it.
- I wrote eleven fresh replies to the premium question and ran them through the real model:

| Reply | Meaning | Claim found |
|---|---|---|
| "इकतालीस हज़ार तीन सौ, बस एक बार देना था।" | had to pay just once | Yes |
| "41,300, one time payment है, दोबारा नहीं देना।" | one-time payment | Yes |
| "एक ही बार इकतालीस हज़ार तीन सौ दिए।" | paid 41,300 just once | Yes |
| "इकतालीस हज़ार तीन सौ रुपये एकमुश्त।" | 41,300 as a lump sum | **No. The whole call ended `clear`** |
| "एक ही बार, इकतालीस हज़ार तीन सौ रुपये।" | only once, 41,300 | **No** |
| Tamil, "paying once is enough" and "must be paid only once" (2 replies) | | Yes |
| Tamil, "41,300 rupees, only once" | | Yes |
| Tamil, "only once, 41,300 rupees" (the word order of the frozen miss) | | **No** |
| Kannada, "paying once is enough" | | Yes |
| Kannada, "41,300, only once" | | **No** |

- So the bare "only once" form is missed in Hindi, Tamil and Kannada, and "एकमुश्त" is missed in Hindi. DESIGN §13 calls the frozen miss "one Tamil reading and not the rule". That is not supported.
- Limits: eleven replies, one run each, written by me, Tamil and Kannada by a non-fluent writer. It shows a pattern, not a rate.
- Reproduce: `uv run python references/reviews/iter1/probes/extractor_live.py` (cache hits now). The rule side: `engine_adversarial.py`, case "regular-premium product; customer believes paid once but never says so" ends `clear`.
- Real call: a customer sold a regular-premium policy as "pay once" is reported clear unless they phrase it the way the model expects. The same holds for any belief outside the ten questions.

**2. A question asked twice keeps only the later answer, even when the earlier one would have flagged.**

- `_Assembly.put` in `samajh/extract/_extract.py` replaces an earlier usable answer with any later usable one.
- Reproduce: `extractor_attacks.py` case 10. The kind question gets "एफ़डी है, जमा किया है।", the bot asks again, the customer says "अच्छा, बीमा।". Verdict `clear`, with no flag, no gap and no trace of the FD answer. Case 11 does the same with "paid separately in cash" then "from the loan".
- Real call: DESIGN §5 has the bot ask an unclear answer once more, so two answers to one question is a normal event. The dialogue decides to re-ask with its own reader, and the extractor reads the call afterwards with another. Whenever they disagree on whether the first answer was usable, the customer's first words are thrown away. A customer who says "FD", hears the options again and says "insurance" is the hero case, cleared.
- Whether the dialogue as built can re-ask after an answer the extractor finds usable is for part 2. The frozen set has no re-asked question, so no reported number covers this.

### Medium

**3. A fraction word the parser does not know is dropped silently, and `tighten` removes it from the model's span.**

- `parse_amount` ignores an unknown word in front of a complete number by design; `exact=True` is meant to catch it. But `samajh/extract/_ground.py::tighten` trims the model's span to the part that reads exactly, so the exact check in `to_beliefs` then passes.
- Reproduce: `uv run python -c "from samajh.amounts import parse_amount; print(parse_amount('सारे तीन लाख'))"` gives 3,00,000. End to end: `extractor_attacks.py` case 12, record premium 3,00,000, reply "सारे तीन लाख रुपये।", verdict `clear`.
- How wide: of 55 native-script spellings I tried (Hindi, Tamil and Kannada), 9 were read with the fraction dropped, all of them Hindi ("सारे", "साढ़ें", "पौना", "पौनें", "स्वा", "सवां" and others); 41 were right and 5 refused. Of 170 romanised fraction spellings placed before digits ("pauney 2 lakh", "sarhe 3,00,000"), 135 were read with the fraction dropped. The spellings are mine; whether Prisma writes any of them is not known.
- Real call: this is the "paune do lakh heard as 2,00,000" failure the design is built around, coming back for any spelling outside the lexicon. If both Prisma models spell the word the same way, the two readings agree on the wrong amount. Only the customer's "no" at the read-back is left.
- W1's review fix for this (its finding F5) added named spellings to a list. The hole is the rule, not the list.

**4. The field-accuracy figure counts the same easy replies many times, and the overlap with the development set is larger than 70.**

- The 1,604 replies are 560 distinct (by language, question and text). One reply is used up to 17 times, and an identical request returns the cached output.
- All 17 wrong fields sit on replies used exactly once. Per distinct reply that is 17 of 560, 3.0% (Wilson 95%: 1.9% to 4.8%), against 0.8% per field. The single-use replies are the ones that carry each scenario's problem.
- Near-overlap with the development set: 70 exact, 138 identical once numbers are masked, 238 (14.8%) with a similarity of 0.85 or more after masking.
- Does it inflate the result? The verdict numbers, no: one false clear stays one. The 99.2% field figure, yes, mostly through reuse and a little through overlap.
- Reproduce: `distinct_errors.py`, `overlap.py`.

**5. The false-clear denominator of 108 includes 32 calls where the customer is informed.**

- Those 32 are flagged for a fault on the lender's side or for a rule's boundary cost (G03, G05, R01, U05, U09, V02, V03, W01). A clear there would not pass a misled customer.
- Among customers with a problem of their own (misled, unaware, did not agree): **1 of 76 calls** (Wilson 0.2% to 7.1%), **1 of 19 base cases** (0.9% to 24.6%).
- Reproduce: `distinct_errors.py`.

**6. E1 cannot show that open questions catch more than closed ones.** See §3.3. The docs disclose each assumption; the demo plan in DESIGN §10 still puts "12 of 12 against 0 of 12" on a slide.

**7. "0 false alarms of 36" is measured on customers who recite every figure exactly.**

- The nine gold-clear base cases answer about ten questions with the exact premium, cover, term in months, cancellation window and consent method. A pass needs all of them at once.
- From `engine_adversarial.py`, each of these informed customers is flagged: a premium rounded 3% ("about 40,000" for 41,300); a term given as 35 months for 36; "OTP" where the record says a click on a screen; the product left out of open recall; a mention of an older policy of their own (medium `recall_unmatched` flag).
- U09 is in the set: an informed customer who forgot the amount gets a medium flag and an evidence pack.
- Real use: expect most calls to end as flag or unclear. That is safe, but a flag then carries little information, and the 0 of 36 says nothing about ordinary compliant customers.

**8. The parser returns confident wrong amounts for some shapes it is described as leaving alone.**

- Fresh inputs, written before running the parser (`amounts_fresh.py`):

| Inputs | n | Right | Refused | Wrong amount |
|---|---|---|---|---|
| Ordinary shapes, four languages | 176 | 174 | 2 | 0 |
| Shapes the builders said they left | 53 | n/a | 44 | 9 |

- By language, ordinary shapes: Hindi 55 of 55, Hinglish 42 of 43, Tamil 41 of 42, Kannada 36 of 36 (Tamil and Kannada gold from a non-fluent reader).
- The nine wrong amounts: an amount followed by a count of two or more gives 50,002 in all four languages ("पचास हज़ार दो एफडी", "fifty thousand two FDs"); a bare number after a lakh gives 1,00,020 and the like; one romanised fraction spelling (finding 3).
- Also from the first fix round's new rule: "5,00,000 बावन हज़ार" (two amounts, digits then words, no comma) is read as 5,52,000.
- Real call: these mostly differ from the record, so they produce a flag and a read-back, not a clear. They are still wrong amounts with no warning, and the docs describe these shapes as refused.

### Low

**9. Code validation of an enum answer is a range check.** The model's clause number only has to exist. The kept evidence is the whole reply, so a wrong value on a real reply passes (`extractor_attacks.py` cases 7 and 8), which the docs say. "0 of 1,195 clause numbers out of range" therefore shows nothing about correctness. The real model did well where code cannot help: 24 of 25 fresh adversarial Hindi and Hinglish replies (later-clause negation, double negatives, an injected instruction, yes-saying) did not end clear. The 25th is the "एकमुश्त" reply of finding 1.

**10. Three silent passes in the engine.**
- Bundling passes when "was it required?" was never asked, if the record says required and the customer confirms a choice of provider.
- An amount named in open recall is compared with nothing: recall says 20,000, the premium answer says 41,300 and is confirmed, verdict `clear`.
- The record says voluntary, the customer says they were told it was compulsory and confirms a choice of provider: `clear`. DESIGN §6 as written allows it. A customer told "compulsory" about a product the lender records as voluntary is a mismatch a reviewer would want.
- The first two are documented in W1's report (F9). Reproduce: the three `FALSE CLEAR` rows of `engine_adversarial.py`.

**11. Words said where no model call looks.** A reply to either identity check is never sent, so coaching mentioned there is lost and the call ends `clear` (case 14). Replies under three words are not screened.

**12. Tests.** 48 mutants across the ten behaviours I ranked most important and the next tier; 46 killed. Survivors:
- M10b: a read-back "yes" given before the premium answer still must not confirm it. No test covers that order.
- M33: the last read-back reply must replace an earlier one even when the last is unusable.

Killed, among others: a gap blocks clear; an unconfirmed premium does not pass; an unrecognised product is a consent flag; a kind that differs is a flag; no consent on a loan-funded premium is a flag; both bundling flags; a contradicted belief is a flag; an answer counts only for its own question; whole-clause quotes; the read-back must be of the same amount; the span must agree with the parser; two amounts are refused; a hedged amount is refused; the scorer's false-clear count; a changed gold case fails the set's tests. Reproduce: `uv run python references/reviews/iter1/probes/mutate.py <a directory outside the repo>`.

**13. Stale or loose wording.** 1,223 core tests (now 1,300). "20 to 24 requests per transcript" (20 to 27). CLAUDE.md's quote rule (claim 31). DESIGN §13's "one Tamil reading and not the rule" (finding 1). `default_llm()` fetches OpenRouter's model list on every call, which W5b's report already lists.

## 3. Gold integrity

### 3.1 The audit

I read the scripted customer text of 36 scenarios: U09, U10, B03, C01, C02 and C03 in all four languages (24), plus U02-hi, V06-hi-en, V01-ta, W05-kn, G05-hi, W06-ta, B04-kn, U04-hi, U05-hi-en, R01-kn, G04-ta and V05-hi.

- In all 36 the gold verdict is what DESIGN §6 gives for that text. I found no gold verdict a careful reader of the rules would overturn.
- Gold is "what the rules say", not "is this customer misled". U05 (rounds 12,350 to 12,500) and U09 (forgot the amount) are informed customers with a flag. That is consistent, and it is why finding 5 matters.
- B03 rests on one volunteered phrase. The Hindi "एक ही बार का है" and the Kannada "ಒಂದೇ ಸಲ ಕಟ್ಟೋದು" state a property of the product. The Tamil "ஒரே தடவைதான், ஐம்பத்திரண்டாயிரம் ரூபாய்" can also be read as "I paid once" (non-fluent reading). Gold takes the safer reading, which is right for a false-clear measure, but the model's reading of that sentence is not absurd.
- C02, U08, V04 and V06: the customer "agreed" to a product described to them as something else, and gold does not flag consent. The datasheet calls the other reading defensible. No verdict depends on it.
- All speech is templated and written by the same model family as the prompt. No human has reviewed it.

### 3.2 Is "premium, I don't know" as a flag defensible?

Yes, as a rule. The customer did answer, a person cannot resolve it by listening again, and it matches how cover, term and cancellation are treated. Three things should be said with it:

- It was decided after the comparison was seen and it went the engine's way. Every gold change from version 1 to version 3 moved gold towards the engine (U10 on kind, consent, belief and premium; U09 on premium). The engine was never changed for gold.
- It cannot move the false-clear or false-alarm counts: both "flag" and "unclear" are not clear. It moved 4 call verdicts (U09) and 8 flag entries into agreement. Against version 2 gold, the frozen run would read 139 of 144 verdicts.
- Its cost is on the review side: an informed customer who forgot a number gets a medium flag and an evidence pack.

Version 1 gold is not in git, so "written before any engine run" rests on the changelog alone.

### 3.3 Is E1 rigged by construction? What it can and cannot support

Rigged is too strong, because nothing is hidden. But no row of the table measures open against closed questions.

| Stratum | Why the yes/no call misses or catches | Measured or assumed |
|---|---|---|
| Coached, acquiescent (16 calls) | The customer says yes to every closed question by definition, and answers the teach-back call candidly. C01 even tells the bot about the coaching | Assumed |
| Never asked (20 calls) | The five-question closed script, written by the same team, does not ask about cover, cancellation, withdrawal, return or payment frequency. A confirmation script that states those features would catch a truthful customer | Fixed by the script |
| Asked (40 calls) | A truthful customer and a question about the wrong belief | Equal: 40 against 40 |
| Informed, flagged (32 calls) | Most teach-back "catches" are faults on the record (no consent, no choice of provider) that need no call | Not a comparison |

E1 can support:
- On scripted text, the pipeline does not clear a scripted misled customer who answers candidly, in 75 of 76 calls.
- A closed script cannot detect a wrong belief about a feature it never mentions.

E1 cannot support:
- That open questions catch more than closed questions in practice, or any rate.
- Anything about coached customers. A person coached to say yes can be coached to say "insurance, 52,000".
- The "12 of 12 against 0 of 12" contrast as a finding. It is an input.

The fair test is the matched closed arm that DESIGN §9 already names as missing.

## 4. The unreviewed fix rounds

| Round | Diff read | Result |
|---|---|---|
| W1b's post-review fixes | Not separable in git (one commit, `cd034f6`), so tested by behaviour | Whole-clause quotes, read-back of the same amount, same-clause hedges and the consent-method gap all hold, and each has a mutant that tests kill. F5 (unknown fraction words) is a list and leaks: finding 3. F4 guards only the clause that holds the number: `extractor_attacks.py` case 6 |
| Parser fix 1, `f896c15` | `git diff 808690e f896c15 -- samajh/amounts` | Reproduces the "after" numbers exactly. Adds the digits-then-words rule ("5,00,000 दो सौ" is 5,00,200), which also merges two adjacent amounts: finding 8 |
| Parser fix 2, `8e9a86b` | `git diff f896c15 8e9a86b` | "One" before a non-money word is a determiner. Changes none of the 240-sentence numbers. Covers "one" only: "two FDs" still gives 50,002 |
| W5b's seven fixes | `git diff f46aa06 11fe56c` | Sound. Keeping the whole reply as the quote makes the evidence honest and turns the clause pointer into a range check (finding 9). Skipping the identity checks creates the blind spot of finding 11. The prompt in the working tree is the prompt of the frozen run: every one of the 3,391 requests is a cache hit |
| Gold versions 2 and 3 | `git diff f46aa06 0c94495`; `CHANGELOG.md` | Version 3 changes 8 gold entries and one class label, as the changelog says. `calls.jsonl` has the same hash in versions 2 and 3. Version 1 is not in git |

## 5. Numbers in DESIGN.md and README.md I could not reproduce

Not reproducible from what is in the repository:
- "One independent model reviewer agreed with 35 of 36 base cases at version 1" (36 of 36 on the verdict).
- That version 1 gold was written before any engine run.
- "Of the 22 awards we read, about two-thirds ordered a refund" (the sources are local-only).
- "About 40 s per transcript" (the docs say it is inferred).

Checked and different:
- 1,223 core tests: 1,300 now.
- 20 to 24 requests per transcript: 20 to 27.
- OpenRouter ledger 0.52 USD: 0.558 now, with later work.

Not attempted in this part (amounts evaluation beyond the dated note, and cost figures for other models):
- Naive digit reading (220 and 156 of 240), "58 recovered, 43 of them fractions", McNemar p = 0.32.
- "8 of the 19 are proven formatting errors", the skipped-group counts (6 of 16, 161 of 164, 15 of 16), "22 of the 26" failure labels.
- The noise table (102 to 93 of 112 and the rest), STT latency medians, the 504 counts.
- Development-set cost per transcript for each model, and per-request latency for models other than gpt-6-luna.
- "0 of 49 prompt examples are a frozen reply."

## 6. Verdict

The decision chain is sound enough to build the voice path on, with conditions. The parts that are code do what they claim: a fabricated span, an out-of-range pointer, an answer taken from the wrong question, an unconfirmed premium and a missing answer all end as unclear or a flag, 46 of 48 mutants of the most important behaviours are killed, a clean product never clears another, and every headline number (1 of 108, 0 of 36, 143 of 144, 2,163 of 2,180, E1 by stratum, the amounts table) reproduces from the cached calls, with gold frozen before the run. What the numbers do not show is the size of the false-clear risk on a real call. It sits in three places that code does not guard: a belief nobody asks about and the customer does not volunteer in the expected words (finding 1), an earlier answer overwritten by a re-ask (finding 2), and a fraction word outside the lexicon (finding 3). Before the voice path is measured I would add a question on how often the premium is paid, make two differing answers to one question unclear, and stop `tighten` from trimming a word it cannot read. I would also report false clears over the 76 calls with a customer problem, and present E1 as a demonstration until a matched closed arm exists. None of this needs the frozen set to be touched.
