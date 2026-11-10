# P3a fix round 3 re-verified

Saved by the sub-orchestrator on 2026-11-10 from the verifier's final message, unchanged. The verifier ran on the working tree as it stood at about 21:00 IST, before the carried-premium fix that answers its failure 1; notes on what changed afterwards are in `references/pilots/P3a-report.md`, "Fix round 3", not here.

I am the independent Opus-high verifier and wrote none of this code. I made no Gnani calls. LLM spend by my clients' own counters was **0.020 USD**, all gpt-6-luna through `samajh/clients/llm.py`. My request count cannot be separated from the coordinator's concurrent `eval/text_path` run in the shared ledger: 285 paid requests and 2,876 cache hits in the window, both runs together. I edited nothing else in the repo. Probes I added in `references/reviews/iter2/probes/`, all rerunnable:
- `p3a_r3_llm.py`, `p3a_r3_llm2.py`, `p3a_r3_llm3.py` (real model, 79 replies)
- `p3a_r3_orders.py` (cover, premium and denial orders; scripted)
- `p3a_r3_carry.py` (scripted; `--llm` and `--llm2` run the real model)
- `p3a_r3_amounts.py`, `p3a_r3_summary.py`
- `p3a_r3_mutate.py <scratch copy>`

`uv run pytest tests/core tests/extract -q`: **2,329 passed**.

**Verdict: sound with conditions.** The r2 findings 1–3 are fixed on fresh inputs. Two new false-clear paths exist, both cases where the stated value is one the customer took back.

| Claim | Result | n | What failed |
|---|---|---|---|
| (a) Informed customer with emphasis, filler, apology or restatement ends `clear` | holds in part | 20 | Non-amount questions: 17 of 17 clear (2 of them unpunctuated). Premium: only 1 of 3; the 2 with "sorry"/"सॉरी" ended `incomplete` (`value_not_parsed`) |
| (b) Correction toward the record value → `clear`, earlier words in `also` | holds in part | 13 | Non-amount: 12 of 12 clear. `also` was kept in 9 of the 10 punctuated cases. The premium correction ended `incomplete` (two amounts in the reply) |
| (c) Correction away from the record value → `refer`; the taken-back value never stated | holds | 19 | Taken-back value stated in 0 of 19. Kind and payment: `refer` in every case. Required-for-loan (4 cases): the belief was correctly `True`, but my harness asks no provider-choice question, so the tier was `incomplete` (`bundling:not_asked`). Premium: 1 `incomplete` |
| (d) Withdrawn with nothing in its place → not `clear` | holds for punctuated replies | 6 | none |
| (e/f) Withdrawn, unpunctuated (one clause, so the change check never runs) | **fails** | 10 with a take-back word | **4 of 10 end `clear` with the withdrawn value stated** |
| Carried premium respects a withdrawal | **fails** | 4 real model + 1 scripted | **4 of 4 `clear`**, with the premium the customer took back. The change check said `withdrawn` every time and was ignored |
| Conflicts across askings stay `refer`; A→B→A | holds | 3 | One A→B→A reply got the check answer `none`, so no `also` note |
| Cover read-back orders (3 figures × 7 orders) and "asking a read-back never lowers the tier" | holds | 21 grid cells; 12 monotonic comparisons | none |
| Premium read-back orders | holds | 10 | none |
| Denial orders | holds | 8 (scripted) | none; see note 4 |
| Amounts, fresh sentences | holds in part | 65 | 4 confident wrong figures; 2 good amounts refused, 1 read as approximate |
| Carried premium, other cases | holds | 8 (scripted) | none |
| Summary wording (addition C) | holds | 5 cases, 6 labels | none; tier unchanged in all 5 |
| Mutations | holds | 11 | 11 of 11 caught (list in "Mutations" below) |

## Failures

**1 (high): the carried premium ignores the recall reply's change check.** `_Assembly.carry` puts `Stated(span)` straight into `heard["premium"]`. `_recall_check` only drops recall items. The premium question is never asked, the bot reads back 41,300 and the customer says "हाँ जी।". Each reply below ended `clear` with premium `Stated(41300)`, and the recall check said `withdrawn` each time:
- `एक बीमा लिया था, इकतालीस हज़ार तीन सौ, नहीं नहीं, पता नहीं कितने का।`
- `एक बीमा लिया था, इकतालीस हज़ार तीन सौ का, नहीं, याद नहीं ठीक से।`
- `insurance liya tha, 41,300 ka, ruko, nahi, pakka nahi pata kitne ka.`
- `बीमा लिया था, इकतालीस हज़ार तीन सौ, अरे नहीं, वो तो लोन की किस्त थी।` (the customer says the figure was the loan EMI)

Expected: `incomplete` or `understanding_gap`. The same words given in reply to the premium question end `understanding_gap` (`premium_dont_know`). Whether the P2 dialogue reads a figure back after such a reply is inferred, not checked.

**2 (high): one-clause replies have no retraction protection.** The change check ran on 0 of the 26 unpunctuated replies (contract §5 says so). Everything rests on the answer model. These ended `clear` with the withdrawn value stated:
- `बीमा है नहीं पता नहीं क्या है` → insurance
- `बीमा है रुकिए मुझे पक्का नहीं पता` → insurance
- `लोन से कटा था नहीं याद नहीं` → from_loan (this one can be read another way)
- `insurance hai nahi pata nahi` → insurance (this one can be read another way)

Two hedge-only replies also ended `clear`: `loan se kata tha shayad nahi pata` and `लोन में से गया था पर पक्का नहीं याद नहीं`. The project's own prompt treats doubt without a take-back word as still leaning to the answer, so I do not count them as failures. Unpunctuated corrections (as against withdrawals) came out right in 9 of 9. How often Prisma output lacks punctuation was not checked.

**3 (medium): "sorry" makes an informed premium answer unusable.** The amounts lexicon tags "सॉरी" and "sorry" as `vague` across the whole reply:
- `जी, इकतालीस हज़ार तीन सौ रुपये, सॉरी, नेटवर्क चला गया था।` → `incomplete`. The same reply without "सॉरी" parses to 41,300.
- `matlab, iktalis hazaar teen sau rupaye, sorry line pe disturbance hai.` → `incomplete`. Romanised number words are also out of scope by design.

Expected `clear`. This affects any premium or cover reply.

**4 (low, design): the kind question can retract a denial.** After "कुछ नहीं लिया", a kind-question answer of "बीमा" picked from the bot's own list ("बीमा, एफ़डी, या कुछ और?") retracts the denial to `recall_not_named` (`understanding_gap`). This matches the contract. Separately, a same-reply "बीमा लिया था, नहीं नहीं, कुछ नहीं लिया" drops the item but keeps no denial: the wire records a denial only when no item was named. It ends `incomplete`, not `refer`. Both are safe but worth knowing.

**Amounts.** Gold was written before the run. Confident wrong figures (4):
- `पचास हज़ार तक।` → 50,000
- `up to 40,000 rupees.` → 40,000
- `do baar 20 hazaar kate.` → 20,000 (a count before the amount)
- `पचास हज़ार हर महीने, बारह महीने।` → 50,000 (arguable)

What held:
- "At least" or minimum forms: 5 of 5 refused.
- At most, maximum or "ज़्यादा से ज़्यादा": 3 of 3 refused.
- "से ज़्यादा" and "से कम": 4 of 4 refused.
- Other count forms: 6 of 8 refused.
- Misheard units: 7 of 7 handled safely (लैख is a listed spelling of lakh).
- "One" after a round amount and before a non-number word: 8 of 8 refused. `पचास हज़ार एक सौ` → 50,100.
- Digit figures in Hindi and Hinglish sentences: 5 of 5 parsed, including `Maine 50,000 rupees diye the.`

Plain amounts: 20 of 23 parsed. 2 were refused:
- `सात हज़ार रुपये महीने के नहीं, एक बार में।`
- (the second is from the real-model probe) `जी, इकतालीस हज़ार तीन सौ रुपये, सॉरी, नेटवर्क चला गया था।`

`Approx nahi, exact 32,000 tha.` came back approximate.

My own gold errors, which I removed from the count:
- `2 saal pehle 50,000 diye the.` → 50,000 is correct.
- `पचास हज़ार एक।` → 50,001 is a fair reading.

**Summary wording strings seen.**
- A call that never got to an item: "The call did not get to: the cover." It is never worded as the customer not knowing. "Customer did not know the cover." appears only when the customer said "पता नहीं।".
- A line on the record alone: "…no choice of provider was offered (from the lender's record; no customer statement)."
- An unfinished call (None, "" or `in_progress`): "Stopped before the call finished: the recording ends there (a hang-up or a dropped line)". An unknown outcome reads "Ended: some new outcome".
- When the customer answered the related question, a record-based line quotes that answer and carries no mark. Example: "नहीं, मर्ज़ी से लिया।" under "The record marks it as required…".

**Mutations** (11 of 11 caught): change check ignores `corrected`; ignores `withdrawn`; `stands = True`; change check only on 3+ clauses; denial order test removed; kind-on-record filter removed; the cover rejected-exact branch removed; old cover gap tier restored; premium carried even when asked; approximate tolerance ignored in the conflict rule; self-correction `also` dropped. Each kills exactly one test, so coverage is thin.

## Not checked
- Speech: all inputs are typed text. No real callers.
- Tamil and Kannada. Any model other than gpt-6-luna.
- Whether the P2 dialogue reads a premium back after a withdrawn recall amount.
- The `refer` tier for required-for-loan corrections when the provider-choice question is asked.
- How often Prisma output lacks punctuation.
- The frozen set.
- No native speaker judged my gold.

## Wording
**May say:**
- "On 17 typed informed replies with emphasis, filler, an apology or a restatement to the kind, payment and required questions, 17 ended `clear`."
- "On 19 typed corrections away from the record value, the taken-back value was never the stated belief."
- "On 6 punctuated withdrawals, none ended `clear`."
- "Across 21 cover read-back orders, asking a read-back never lowered the tier."
- "11 of 11 targeted mutations were caught."

**May not say:**
- "A retraction never yields a stated value." It is not true of the code: one-clause replies and the carried premium are unprotected. It is not true of the model either: 4 of 10 unpunctuated withdrawals and 4 of 4 carried-premium withdrawals ended `clear`.
- "An apology never makes an informed customer incomplete." It does in amount answers.
- "A correction to the record figure passes" for amounts.
- "Bounds ('up to', 'तक') and counts are refused."
- Any claim about speech, real callers, or a pooled rate.

## Fix before use (ranked)
1. Apply the recall reply's change check to the carried premium. Simplest: never carry from a recall reply whose check is not `none`.
2. Give one-clause replies protection: run the change check on unpunctuated replies (word-numbered), or at least on those with a take-back word after the answer. Measure Prisma's punctuation rate.
3. Limit "सॉरी" and "sorry" as doubt words to the amount's own clause.
4. Refuse "तक" and "up to" bounds, and a count word before the amount ("do baar").
5. Add more than one killing test for each guard; every mutation died on a single test.

Then re-verify on fresh inputs.

---

# Addendum: carried-premium fix re-verified (P3a r3)

Saved by the sub-orchestrator on 2026-11-10 from the same verifier's second message, unchanged. It was run after the carried-premium fix and on the restored change-check prompt.

Finding 1 is fixed: the carried premium now respects the change check. I tested it with the real model (gpt-6-luna) on fresh inputs, and all 24 replies came out as expected.

**Prompt timing.** Every result below is on the restored change-check prompt. `samajh/extract/_wire.py` was last modified at 21:14:28 IST. My measured run started at 21:15:56, and a second run at 21:17:48 reproduced it entirely from cache (0 USD). I threw away an earlier run (21:12) made under the changed docstring, but one result from it matters: see the table's second-to-last row.

**Spend:**
- Recheck: 0.010 USD (0.007 of it in the discarded run).
- Whole engagement: about 0.030 USD.

**Probe:** `references/reviews/iter2/probes/p3a_r3_carry2.py` (new; rerunnable).

**Setup.** The premium question is never asked. The open-recall reply gives a premium, the bot reads back 41,300, and the customer says "हाँ जी।". The record premium is 41,300.

| Claim | Result | n | What failed |
|---|---|---|---|
| (1) A premium taken back or replaced in the same recall reply is not carried, and the case is not `clear` | holds | 9 new, 4 regression | none. All 13 ended `incomplete` with `Unclear(readback_mismatch)`. The change check said `withdrawn` 10 times and `corrected` 3 times |
| (1) Only the product corrected, amount kept: `बीमा लिया था, नहीं, एफ़डी, इकतालीस हज़ार तीन सौ की।` | holds | 1 | `refer` (`kind_differs`); the premium was not carried. In my view `refer` is the right outcome. The premium arguably could have been carried, since the amount was not taken back, so leaving it undecided loses a little information. That direction is safe |
| (2) Informed replies (two or more clauses, with emphasis, filler or an apology) still carry the premium and end `clear` | holds | 8 | none. All 8 had check `none` and ended `clear` with premium `Stated(41300)`. Over-eager check on this n: 0 of 8 |
| (3) One-clause (unpunctuated) recall withdrawal | not `clear` | 2 | Both ended `incomplete` and nothing was carried. The protection here came from the amount parser, which refuses a reply with "नहीं नहीं पता नहीं कितने का" or "ruko yaad nahi" after the figure. It did not come from the check, which never runs on one clause. A one-clause reply whose take-back words the parser does not refuse is still unprotected (finding 2 stands; inferred, not run) |
| The guarantee rests on one model reading | observation | 1 | Under the briefly changed docstring, `बीमा लिया था, इकतालीस हज़ार तीन सौ, अरे नहीं, वो तो लोन की किस्त थी।` got check `none` and ended **`clear` with premium `Stated(41300)`**. On the restored prompt the same reply gets `withdrawn` and ends `incomplete`. So a wording change in the check's prompt alone flipped one of my 24 cases to a false clear |
| (4) The note line appears exactly when there is a self-correction, and the tier does not change | holds | 2 | none. `डिपॉज़िट है, ओह नहीं, बीमा है जी।` gives result and summary tier both `clear`, and one line with `tier=clear note=True`: "Customer first said "डिपॉज़िट है" about what the product is, then corrected it in the same reply." The plain BASE call gives `clear`, no self-corrections, and no lines |
| (5) `uv run pytest tests/core tests/extract -q` | holds | — | 2,345 passed, matching your count |

## Change to the verdict
Still **sound with conditions**:
- Finding 1 is now fixed on fresh inputs.
- Finding 2 (one-clause replies) is unchanged.
- Finding 3 ("sorry" makes an informed premium or cover answer unusable) is unchanged.
- The amounts holes are unchanged.

New condition: the carried premium's protection now depends on a single change-check reading. Any edit to the change-check prompt, including the `ChangeReply` docstring, should be followed by a rerun of the retraction probes.

## Wording
**May say (add):**
- "On 13 typed recall replies that gave a premium and then took it back or replaced it, the premium was not carried and the case was not `clear` (13 of 13, gpt-6-luna, restored prompt)."
- "On 8 typed informed recall replies with emphasis, filler or an apology, the premium was carried and the case ended `clear` (8 of 8)."

**May not say (change):**
- Remove "the carried premium ignores a withdrawal" from the problems list.
- Keep "A retraction never yields a stated value". One-clause replies are still unprotected by the code, and the carried case depends on one model reading: 1 of 24 flipped to a false clear under a prompt-text change.
- Do not say "the carried premium can never carry a withdrawn figure".
