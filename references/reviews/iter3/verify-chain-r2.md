<!-- Saved by the chain sub-orchestrator on 2026-11-13 from the verifier's final message, unchanged. It verified the P5 fix round (causes A-F) before the fixes that answer its failures 1-3; what changed afterwards is in references/pilots/P3a-report.md, first section. -->
## Verdict: sound with conditions. This round's code caused no unsafe outcome. Claim B mostly does not hold through the real model, and claim E's prompt line leaves an older gap open.

I am the independent Opus-high verifier and wrote none of this code. All inputs are typed text, so nothing here says anything about speech or real callers. I made no Gnani calls. I fixed gold before each run; the sha256 of the case block is printed at the start of each run (`233e4466c5e26fdc`). I did not open P5, scenarios, amounts_v2 or the builder's p5fix test files.

The probes are in `references/reviews/iter3/probes/`:
- `chain2_llm.py`: 123 whole calls.
- `chain2_diag.py`: raw model outputs, plus 14 extra replies. Their gold was set when I wrote the command, before running it.
- `chain2_leak.py`
- `chain2_mutate.py`: runs on a scratch copy.

The lane diff hash before and after my work is identical (`b20fbb20…`).

**Tests**
- `uv run pytest tests/core tests/extract -q`: **2705 passed**.
- Whole suite: **2 failed, 8456 passed, 3 deselected** (221 s).
  - `tests/server/test_readings_fields.py::test_the_prepared_demo_call_asks_again_and_reads_back_the_right_figure` (server lane). Its fake model is keyed on `"SpanReply"`. This lane renamed the premium schema to `PremiumReply`, so the server test needs a one-line update.
  - `tests/p5/test_p5_data_dir.py::test_run_refuses_on_the_given_directorys_frozen_file` (P5 lane). It passes when run alone, so the failure depends on test order.

## Claims

Unsafe means a `clear` on a wrong or withdrawn belief. False-incomplete means an informed reply that did not end `clear`.

| Claim | Result | n | Informed: clear / n | Misled: refer / n | Unsafe | False-incomplete | What failed |
|---|---|---|---|---|---|---|---|
| A. Consent reply giving only the method | holds | 24 | 10/10 | 5/5 | 0 | 0 | none. Rule-level cases: 4/4 gave the expected reason (named nowhere: `consent_product_not_named` ×3, `consent_method_differs` ×1). Take-backs and corrections: 3/3 `incomplete`. "sirf loan ke liye OTP diya tha" referred (`consent_not_recognised`) |
| F. A phone yes | holds | 14 | 6/6 | 6/6 | 0 | 0 | none. "not recorded" → `verbal` → refer, 2/2 |
| B. "Nobody told me" | **holds in part** | 16 + 6 | 4/4 (+3 "told, didn't listen": clear) | 5/6 | 0 | 0 | No-with-don't-know-tail replies: **1 of 7 referred**. Failure 2 |
| C. Premium "free" or zero | holds | 23 | 4/4 | 10/12 | 0 | 0 | 2 "free" replies that also mention a bank or the loan ended `incomplete`, by the guard's design. `premium_said_zero` never appeared on the 5 replies where it was forbidden |
| D. Paid by nobody (`not_charged`) | holds | 16 | 7/7 | 8/8 | 0 | 0 | none. "bank paid from my loan" → `from_loan` → clear, 6/6 |
| E. A denied feature is not a claim | the line holds, but the gap underneath is open | 23 + 6 | 11/11 denials | 11/11 timed assertions | **1 (+6)** | 0 | Failure 1. This gap was already there at the base commit, before this round |
| Figure, then a doubt about exactness | judged below | 7 | n/a | n/a | 3 by my gold | n/a | Failure 3 |

**Re-run of the earlier probes** (all cache hits, $0):
- `chain_llm.py`, 103 cases: **1 unsafe**, the builder's "41,300, actually, pakka nahi pata.". The other non-ok results are the 12 already-known costs.
- `chain_r2_llm.py`, 60 cases: 0 unsafe, 0 cost.

**Mutations** (scratch copy, `tests/core` + `tests/extract`): **6 of 6 killed**, with 2, 8, 2, 4, 2 and 2 failing tests for:
1. A correction counts as method-only.
2. Any `Unclear` counts as method-only.
3. Named nowhere with a differing method gives a gap instead of a refer.
4. `paid_otherwise` is ignored.
5. A second amount next to a zero is ignored.
6. The tail exception also applies to a yes.

**Leak check (task 5):**
- I extracted one call that holds every new kind of reply under two records that differ in every field (premium, payment source, consent method, provider choice, required, features, cover, term, provider, borrower). The 29 requests (including `PremiumReply`, `PaymentReply` and `ConsentReply`) were **byte-identical**.
- Across 3,069 real requests, no record-only string appeared outside the bot question and the customer's reply.
- The one record value that does reach the model is the premium read-back question, which repeats the customer's own figure. CLAUDE.md already documents this exception.

## Failures, ranked

**1 (high, safety; already present at the base commit, not caused by this round).** When the customer believes the money comes back but gives no timing, the model records no claim, and the call ends `clear` with `claims []`:
- `वापस नहीं मिलता क्या? मुझे तो लगा था मिलेगा`
- `नहीं नहीं, वापस मिलेगा ना`
- `refund nahi hota aisa nahi hai, milta hai`
- `वापस नहीं मिलेगा? मिलेगा ना, उन्होंने बोला था`
- `mujhe laga tha wapas milega`
- `wapas to milega hi, kyun nahi milega`
- `मुझे लगता है पूरा पैसा वापस मिल जाएगा`

That is 7 of 7 `clear`. At the base commit 5 of the 6 I reran were `clear` and one was `incomplete`. No `FeatureClaim` covers "comes back" without "anytime" or "after a period". With a timing, interest or deposit word, all 11 assertions referred, including "abhi nahi, baad mein milega".

**2 (medium, misled customers missed; claim B).** The change check is unchanged this round and runs before the new tail exception. It marks these replies `withdrawn`, so each one ends `incomplete` instead of `refer`:
- `नहीं बताया पता नहीं`
- `कुछ नहीं बताया पता नहीं` (the builder's own example)
- `नहीं बताया था पता नहीं`
- `nahi bola tha mujhe nahi pata`
- `नहीं, किसी ने नहीं बताया, पता नहीं।`

`मुझे नहीं पता था कि बाहर से भी ले सकते हैं` is read as `dont_know` and also ends `incomplete`. Only `kisi ne kuch nahi bataya pata nahi` referred, because there the check said `none`. No reply ended `clear`. The tests kill mutation 6 only with a scripted check of `none`, so they cannot see this path.

**3 (low to medium, a judgment call).** A figure followed by a doubt about exactness, then a confirmed read-back, ends `clear`. The hedge marker stays false, because `has_doubt_word` misses phrases such as "ठीक से याद नहीं", which the prompt itself lists as a doubt phrase:
- `इकतालीस हज़ार तीन सौ, पक्का नहीं पता।`
- `41300 rupaye, exact yaad nahi.`
- `इकतालीस हज़ार तीन सौ, वैसे, ठीक से याद नहीं।`

All three are `clear` at the base commit too.

The builder's case, "41,300, actually, pakka nahi pata.", depends on how the question is worded:
- With the old BASE question it ends `clear`. The answer model now says stated 41,300 where the base commit said `dont_know`, and the check says `none`.
- With the dialogue's own hi-en question it ends `incomplete`, because the check says `withdrawn`.
- With "actually" in the reply, 3 of 3 new replies ended `incomplete`.

My judgment: under the project's doubt rule these are hedged answers, not take-backs, and the figure is the record's and was confirmed. So the shape is a pattern, but it is not new and not a withdrawal. My pre-fixed gold counted 3 of 7 as unsafe. The reviewer cannot see the doubt, so the hedge marker should catch these phrases.

**4 (low, by design).** "Free" said next to a bank or the loan ends `incomplete`, not `refer`: `बैंक वालों ने बोला था फ्री है`, `loan ke saath free mila tha`.

**5 (note).** `एक सोने का सिक्का मिला था` at recall is paired to the product as a misdescription. The consent "what" is then taken from it, so consent passes. The call still refers on `kind_differs`.

## Not checked
- Speech, real callers, Tamil and Kannada.
- Models other than gpt-6-luna.
- Repeated runs: one model reading per reply.
- Whether the live dialogue reads back a premium after a "free" answer.
- How the ops pages and reports render the new flags. I read `summary.py` only in the diff.

## Wording
**May say:**
- "On 42 typed informed replies across the six causes, 42 ended `clear`."
- "On 10 typed method-only consent replies that match the record, 10 ended `clear`. On 9 with a different way of agreeing, 9 referred."
- "On 2 typed 'only for the loan' consent replies that give a method, 2 referred."
- "On 10 typed 'free, zero or nothing' premium replies with no payer or loan word, 10 referred."
- "On 7 typed 'paid by nobody' replies, 7 referred. On 6 'the bank paid from my loan' replies, 6 ended `clear`."
- "On 11 typed denials of a feature, 11 ended `clear`. On 11 typed assertions with a timing, interest or deposit word, 11 referred."
- "Under two records that differ in every field, the 29 requests of one call were byte-identical."
- "6 of 6 mutations of the new guards were caught by the tests."

**May not say:**
- "Every belief about getting money back is caught": 7 of 7 untimed "comes back" replies ended `clear`.
- "'Nobody told me, don't know' is kept as a no": 1 of 7 referred.
- "Anyone who calls it free is referred": 2 of 12 ended `incomplete`.
- "The builder's new unsafe case is gone": it still reproduces under 1 of the 2 question wordings.

**LLM spend** (client counters): 0.0267 + 0.0046 + 0.0015 + 0 + 0 + 0 = **0.0328 USD**, against a 0.08 cap.

---

<!-- Recheck addendum, saved by the chain sub-orchestrator on 2026-11-13 from the same verifier's second message, unchanged. Failures 1 and 2 below (a filler after the don't-know tail; the Devanagari spelling एग्ज़ैक्ट) were then fixed once by the builder and NOT re-verified (references/pilots/P3a-report.md, first section). -->
## Addendum: recheck after fix round 2 (same verifier, 2026-11-13)

**Verdict: the three fixes hold, with conditions.** On 54 new typed calls, no call ended `clear` on a wrong or withdrawn belief, and no informed reply was falsely marked `incomplete`. One misled customer was missed (it ended `incomplete`), and the hedge marker was missed on 2 replies.

I ran all of it through the real model via `default_llm()`, typed text only. Gold was fixed before the run (cases sha256 `7dd197c521370e20`). The new probes are in `references/reviews/iter3/probes/`:
- `chain2_r2_llm.py`: the 54 calls.
- `chain2_r2_mutate.py`: mutations on a scratch copy only.

The lane diff hash is `ae4949b8…` both when the recheck started and at the end, so I left the tree as I found it. I opened no P5, scenarios or amounts_v2 files and made no Gnani calls.

**Tests**
- `uv run pytest tests/core tests/extract -q`: **2732 passed**.
- Whole suite: **2 failed, 8483 passed, 3 deselected** (217 s). Both failures are the expected ones outside the lane:
  - `tests/server/test_readings_fields.py::test_the_prepared_demo_call_asks_again_and_reads_back_the_right_figure`: the server test's fake model is keyed on `"SpanReply"`.
  - `tests/p5/test_p5_data_dir.py::test_run_refuses_on_the_given_directorys_frozen_file`: depends on test order.

| Fix | Result | n | Outcome | What failed |
|---|---|---|---|---|
| 1. `money_back` claim: untimed money-back belief, insurance record with no features | holds | 10 | 10 refer | none; double-negative assertions included ("पैसा डूबेगा नहीं, वापस मिलेगा", "aisa nahi hai ki wapas nahi milega, milega") |
| 1. Same belief on a record whose product gives money back (features include `is_deposit`, `refundable_anytime` or `withdrawable_after_period`) | holds | 7 | 7 clear | none |
| 1. Denials, including double negatives | holds | 7 | 7 clear | none |
| 1. Timed assertions | holds | 5 | 5 refer | none |
| 2. Provider choice: "no" + don't-know tail | holds in part | 8 | 7 refer, 1 incomplete | `नहीं कहा था पता नहीं जी` |
| 2. "no" + another take-back word | holds | 4 | 4 incomplete | none |
| 2. "yes" + don't know | holds | 3 | 3 incomplete | none |
| 2. "told me, but I didn't listen" | holds | 3 | 3 clear | none |
| 3. Premium figure + doubt about exactness | holds in part | 7 | hedge marker set on 5 of 7. Tiers: record figure confirmed at read-back → `clear` (4); a different figure (51,000) confirmed → `refer` (1) | `जी 41300, एग्ज़ैक्ट याद नहीं` (`clear`, marker not set); `41300 sahi se nahi pata` (`incomplete`, the parser refused the figure) |

**Failures, verbatim**
1. **Missed misled customer.** `नहीं कहा था पता नहीं जी` ended `incomplete`. The change check said `withdrawn`, and `Reply.ends_in_dont_know_tail()` returns False when a filler (जी) comes after the tail. The same reply with जी before the tail (`नहीं बताया जी पता नहीं`) referred. The miss is not unsafe: the call did not end `clear`.
2. **Hedge marker missed.** `जी 41300, एग्ज़ैक्ट याद नहीं`: the Devanagari spelling of "exact" is not in the doubt list, so the marker stays False and the call ends `clear` on the record figure, confirmed at read-back. Only the marker is affected; the tier is the designed one.
3. **Cost (informed answer not used).** `41300 sahi se nahi pata` ended `incomplete` with `value_not_parsed`: the parser refuses a figure with "nahi" in the same clause.
4. **Still open (the builder says so).** The screening schema is unchanged, so an untimed money-back belief said in reply to any other question is still not read. I did not test this.

**Rerun of `chain2_llm.py` (round-1 cases, all from cache, $0)**
- 123 cases. Of round 1's 4 unsafe cases under my gold, only the 3 figure-plus-doubt ones remain:
  - `इकतालीस हज़ार तीन सौ, पक्का नहीं पता।`
  - `41300 rupaye, exact yaad nahi.`
  - `इकतालीस हज़ार तीन सौ, वैसे, ठीक से याद नहीं।`
- All three now carry `hedged=True` and still end `clear`. That is by design: the marker changes nothing in the tier. In round 1 I judged them hedges, not take-backs.
- `वापस नहीं मिलता क्या? मुझे तो लगा था मिलेगा` is now `refer` (`money_back`).
- `नहीं बताया पता नहीं` is now `refer`.
- No informed reply failed. Two misled customers are still missed by design: `बैंक वालों ने बोला था फ्री है` and `loan ke saath free mila tha` both end `incomplete`.

**Mutations (scratch copy): 3 of 3 caught by the tests.**
- `money_back` always holds: 8 failing tests.
- The withdrawn "no" kept without the tail test: 3 failing tests.
- Exactness doubts never mark the hedge: 3 failing tests.

**LLM spend (client counters):** 0.0134 USD for the 54 calls, plus 0.0000 for the cached reruns and diagnostics. Total **0.0134 USD**, against a 0.04 cap.

**May say**
- "On 10 typed untimed 'the money comes back' beliefs on an insurance record with no money-back feature, 10 referred. On 7 such beliefs on a record whose product does give money back, 7 ended `clear`."
- "On 7 typed denials of getting money back, double negatives included, 7 ended `clear`. On 5 timed assertions, 5 referred."
- "On 8 typed 'nobody told me, don't know' replies to the provider-choice question, 7 referred and 1 ended `incomplete`. None ended `clear`."
- "On 7 typed 'no' or 'yes' answers followed by a take-back or a don't-know, none ended `clear`. On 3 'told me, but I didn't listen' replies, 3 ended `clear`."
- "On 7 typed premium figures followed by a doubt about exactness, the hedge marker was set on 5. A confirmed record figure ended `clear` (4 of 4), and a confirmed different figure referred (1 of 1)."

**May not say**
- "Every untimed money-back belief is caught." It is caught only on the money-back question (17 of 17 handled correctly there). Elsewhere it was not tested, and the screening schema cannot read it.
- "'Nobody told me, don't know' is always kept as a no." 1 of 8 was lost to a trailing filler.
- "Every doubt about exactness is marked." 2 of 7 were not (one Devanagari spelling missed, one figure refused by the parser).
- Anything about speech, real callers, Tamil or Kannada.
