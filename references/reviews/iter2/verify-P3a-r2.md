# P3a fix rounds re-verified (ff960f7, b42e023, f79463e)

Saved by the coordinator on 2026-11-10 from the verifier's final message, unchanged.

Verifier: independent Opus-high. I wrote none of the code. No Gnani calls. LLM spend was 0.0052 USD through `samajh/clients/llm.py` (gpt-6-luna, 28 calls; everything else came from the cache or a scripted model). I edited nothing in the repo. Five new probes are in `references/reviews/iter2/probes/` and can be rerun: `p3a_r2_amounts.py`, `p3a_r2_chain.py`, `p3a_r2_llm.py`, `p3a_r2_mutate.py <scratch>` and `p3a_r2_single_flight.py <scratch>`.

**Verdict: sound with conditions.** Five fixes hold on fresh inputs: re-ask accounting, the conflict rule, the range bound, the hundreds-word "one", and single flight. The other four hold only in part:
- **The retraction fix introduces a new fault.** Informed customers get falsely referred.
- **The cover read-back tier has holes.** A confidently wrong cover can end up in `understanding_gap`.
- **The denial rule ignores the order of what was said.**
- **The "one before a verb" rule is a word list.**

## Each fix

| Fix | Result | n | What failed |
|---|---|---|---|
| Re-ask accounting (a failure on any asking wins; the last stated answer stands) | **holds** | 12 chain cases | none. A failure on the first or a later asking ends `incomplete`. Insurance then FD then insurance ends `refer`. An FD added in a second recall reply is `recall_off_record` |
| Conflict rule (only incompatible stated answers conflict) | **holds** | same 12 | none. "Don't know" before or after an answer is not a conflict, by contract. 41,300 against "करीब पचास हज़ार" is a conflict; 41,000 against 41,300 is not |
| Retraction in a later clause never yields a stated value | **holds in part; new fault** | 21 retractions, 7 over-firing cases | see 1 below |
| Denial persistence | **holds in part** | 11 | see 3 below |
| Cover read-back tier | **holds in part** | 15 | see 2 below |
| Structural fraction refusal | **holds, with one hole** | 51 | 50 of 51 read right or refused. Wrong: `तीन लक पचास हज़ार` → 50,000 (a misheard लाख: the "तीन" and the lakh are both lost). Old sweep: 0 wrong, unchanged |
| Range width bound (`MAX_RANGE_RATIO`) | **holds** | 30 range and hedge cases | `चालीस से इक्यासी हज़ार` and `एक से तीन लाख` are refused. Two problems outside the claimed fixes: `कम से कम पचास हज़ार` → 50,000 ("at least" read as the figure), and `पचास हज़ार दो बार कटे` → 50,000 (the old verifier found this; it is still there). `डेढ़ से दो लाख` is refused, which is safe |
| "One" after a hundreds word is part of the number | **holds** | 10 | none (301, 901, 41,301, 1,101 …) |
| "One" before a verb is ambiguous | **holds only for listed verbs** | 30 | 14 of 14 listed verbs are refused. **16 of 16 other verbs read as 50,000**: `पचास हज़ार एक जमा किए`, `…एक चुकाए`, `…एक कटवाए`, `…एक पे किए`, `…एक भर दिए`, `…एक गए`, `…एक लिए`, `…एक आए`, `…एक निकले`, `…एक लगाए`, `…एक ले लिए`, `…एक डाले`, `…एक हुए`, `fifty thousand one was deducted`, `50 thousand one gave`, `50 thousand one were cut`. `VERB_AFTER` holds 40 words, so the rule is a list, not a structure. In practice a 50,001 premium is rare (inferred) |
| One LLM request per cache key | **holds** | 3 scenarios, real OS processes | 4 processes × 6 threads on one key sent 1 HTTP request. 3 keys sent 3 requests, running concurrently. When the output is invalid, waiters retry one after another: 6 callers made 6 serial requests. That is expected, but a failure costs once per waiter |

### Finding 1 (high): the retraction rule turns informed customers into referrals
`kept()` in `samajh/rules/normalise.py` adds an `answers_conflict` whenever any text follows a listed phrase. It never checks that what follows is a different answer. On a refer-tier question that conflict makes the call `refer`.

With the real model I tested 7 informed replies. The model read every one correctly; the code then overrode it. 6 of 7 ended `refer` and 1 ended `incomplete`:
- `नहीं, वापस नहीं मिलता, नहीं नहीं, बिल्कुल नहीं।`
- `बीमा है, सॉरी, आवाज़ कट रही थी।`
- `नहीं, ज़रूरी नहीं था, नहीं नहीं, मर्ज़ी से लिया।`
- `नहीं, ज़रूरी नहीं था, वो नहीं था ज़रूरी।`
- `लोन में से कटा था, sorry, network problem था।`
- `नहीं, वापस नहीं मिलता, ऐसा तो नहीं था कि वापस मिलेगा।`
- The `incomplete` one: `बीमा है, एफ़डी नहीं, वो नहीं था।`

For the "sorry, network problem" reply the reviewer reads: *Customer gave differing answers about how it was paid for: "लोन में से कटा था", "sorry, network problem था".* Emphatic "नहीं नहीं" and a "sorry" about the line are ordinary phone Hindi. The frozen set happens to contain none of these, which is why its numbers did not move.

On the other side of the claim:
- **The code catches only listed phrases.** 16 of 16 unlisted retractions pass the code untouched when the model quotes the retracted clause, for example `बीमा है, नहीं, एफ़डी है।`, `insurance hai, no no, FD hai.`, `बीमा है नहीं नहीं एफ़डी है` (unpunctuated) and `…, I mean FD hai`. "Never" is therefore not true of the code.
- **The real model resolved all 16 to the corrected answer**, so I found no false clear end to end: 0 of 21 (16 unlisted, 5 listed). That is one model, on typed text.

### Finding 2 (medium): a confidently wrong cover can fall to `understanding_gap`
The decision says an unconfirmed wrong cover is `incomplete`. In the code, any cover gap is `understanding_gap`. Record cover 3,50,000, customer says "दस लाख" plainly:
- Read-back rejected ("नहीं", no correction): `understanding_gap`, as a `readback_rejected` gap. With no read-back at all the same call is `incomplete`, so asking the read-back lowers the tier.
- The bot reads back a different figure and the customer says yes: `understanding_gap` (`readback_mismatch`).
- The customer confirms 10 lakh, then repeats "दस लाख ही है" when cover is asked again: `understanding_gap`, not `refer`. The read-back now comes before the last stated figure. Whether the dialogue ever asks cover again after a read-back is inferred, not checked.
- Smaller point: a correction to the record figure given at the read-back is discarded unless a second read-back follows. It ends `understanding_gap`, which is safe.

### Finding 3 (medium): the denial rule ignores order
`recall()` in `samajh/rules/checks.py` retracts a denial whenever anything named exists, whenever it was said. So "एक बीमा लिया था" followed by a second recall reply "नहीं, कुछ नहीं लिया, बस लोन" ends `recall_not_named` (`understanding_gap`). The decision says "later names", so a denial that comes after the naming should stand.

`named` also counts a misdescribed item paired to the product. After a denial, "एक एफ़डी" gives `recall_not_named` with the title "then named this product". The contract says only naming "as the kind on record" retracts. Here the tier stays `refer` through `kind_differs`. Recall items are never checked for retraction: `बीमा लिया था, नहीं नहीं, कुछ नहीं लिया` with an item still counts as naming.

## Tests, mutations, frozen set
- `uv run pytest tests/core tests/extract -q`: **1,959 passed** (core 1,708, extract 251).
- Mutations, run in a scratch copy (the baseline copy passed 2,011 tests): 30 mutations, 25 caught by the tests. The 5 that survived:
  - "सॉरी" removed from the retraction list
  - "sorry" removed from the retraction list
  - "a denial is dropped when any recall item exists" (the old behaviour). The behaviour is correct by my probe, but no test covers it
  - approximate tolerance ignored in the conflict rule
  - `widen()` returning the model's span unchanged. Inferred: this may be redundant, because the whole reply must also parse the same
- Frozen set recomputed from the cache with 0 USD and 0 errors. It matches `frozen__openai-gpt-6-luna.md` on every Hindi and Hinglish row:
  - verdicts 143 of 144 (B03-ta wrong)
  - problem misses 2 of 38 (U07-hi, U07-hi-en)
  - informed on a compliant record: 0 of 18 referred
  - informed with a fault on the record: 8 of 16 referred
- The old probes rerun:
  - `p3a_tier_attacks`: 2 of 48 outside the old reading, both by coordinator decision
  - `p3a_fraction_sweep`: 0 wrong
  - `p3a_amounts_fresh`: misspelt fractions are now read correctly. "दो एफडी पचास हज़ार की" and "पचास हज़ार दो बार कटे" → 50,000 remain

## Not checked
Speech-to-text output (all inputs are typed text), Tamil and Kannada, models other than gpt-6-luna, and whether the P2 dialogue can produce the re-ask orders in findings 2 and 3. No native speaker has judged the gold for the "one" cases.

## Wording
**May say:**
- "On the verifier's 12 fresh re-ask and conflict cases, the chain followed the contract in all 12."
- "A failed model call on any asking leaves the field undecided."
- "24 concurrent identical requests across 4 processes sent one HTTP request."
- "The frozen-set numbers reproduce from the cache: problem misses 2 of 38 Hindi and Hinglish calls, informed customers on a compliant record 0 of 18 referred."
- "On 21 typed retractions the extraction model gave the corrected answer every time."

**May not say:**
- "A retraction never yields a stated value". The code catches only listed phrases, and the rule falsely refers informed customers who say "नहीं नहीं" or "sorry".
- "A wrong cover is always queued" or "unconfirmed wrong cover is incomplete" without the exceptions: a rejected or mismatched read-back gives `understanding_gap`.
- "A denial is refer whenever it stands": the code ignores order.
- "Ambiguous before any verb".
- "Misspelt units are always refused".
- Any claim about speech, real callers, or a rate.

**Before P5, fix:**
1. Add a conflict only when the text after the retraction holds a different answer. Do not treat emphatic "नहीं नहीं" or a "sorry" about the line as a retraction.
2. Make a rejected or mismatched cover read-back of a plain wrong figure `incomplete`.
3. Respect order in the denial rule, and count only naming as the kind on record.
4. Add tests for the five surviving mutations.

Re-verify on fresh inputs afterwards.
