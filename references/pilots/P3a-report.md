# P3a report: decision chain v2

Builder, 2026-11-10. Took over from three cut-off workers; their committed work (types, tiers, checks, summary, extractor) was kept. Not yet independently verified. Synthetic text only, no speech. Tamil and Kannada not human-reviewed.

## 1. What changed in this pass

| Path | Change |
|---|---|
| `samajh/amounts/_approx.py` (new), `__init__.py` | `Approximate`, `parse_approx_amount`, `has_doubt_word`, `is_loan_tenure`, as in `P3a-contract.md` §4. A hedge ("करीब", "शायद", "के आसपास", "I think") or a narrow range ("पचास बावन हज़ार", "50-52 hazaar", "50,000 से 52,000", "एक से डेढ़ लाख") reads as (low, high). Stays refused: corrections, a negator or comparison in the same clause, "और"/"and", three ends, high more than twice low, mixed forms, restarts, romanised number words, misspelt fraction or unit words. Hindi, Hinglish and English doubt words only |
| `samajh/rules/normalise.py` | `to_beliefs` now passes on payment frequency, conflicts, the recall denial and unscreened replies, each only where its quote is in the call (otherwise an evidence gap). Amounts go through `parse_approx_amount` and carry `hedged`, `approximate` and `low`. A read-back confirms a range only when the bot line has the same two ends. "जब तक लोन चलेगा" is the record's `tenure_months`, or a `not_comparable` gap when the record has none |
| `samajh/rules/checks.py` | A premium with no read-back now quotes the customer's amount in its gap |
| `tests/extract/extractkit.py`, tests | Recorded outputs that predate `took_nothing` replay it as false. Tests from before the change that assumed the old behaviour (trimming, one failure fails the whole call, "दो तीन लाख" refused, timing in `run_text` equality) were rewritten to the new contract |

From the earlier workers and kept unchanged: the `Tier` type and `tier_of`, `FLAG_TIER`, the conflict flags, `summarise`, the misspelt-fraction refusal in `parse_amount`, the extractor (parallel requests, field-level `extraction_failed`, kept conflicts, the payment-frequency question `Question.payment_frequency`, `took_nothing`, no trimming), and the text-path triage scorer.

## 2. Evidence

```
$ uv run pytest tests/core tests/extract tests/scenarios -q
1954 passed in 12.99s          # core 1662, extract 242, scenarios 50
$ uv run ruff check samajh/types.py samajh/rules samajh/amounts samajh/extract samajh/pipeline.py tests/core tests/extract eval/text_path
All checks passed!
```

Verifier probes (run from `references/reviews/iter1/probes/`; the extractor probe from a copy that adds `"took_nothing": false` to its scripted recall outputs, because the field is now required):
- `extractor_attacks.py` case 10 (FD, then "बीमा" after a re-ask): was `clear`, now `flag_for_review` with a kind flag. Case 11 (cash, then "from the loan"): now flagged. Case 12 ("सारे तीन लाख"): was `clear`, now `value_not_parsed` gap. The probe's printed commentary is static and still describes the old behaviour.
- `amounts_fresh.py`: ordinary shapes 174 of 176 right, 2 refused (unchanged); shapes left by the builders 8 wrong (was 9: the romanised fraction is now refused), 45 refused.
- `engine_adversarial.py`: 104 cases, 5 differ from the verifier's reading, 4 of them the false clears of verifier findings 1 and 10 (not in this package; see §4).

## 3. Numbers

**Frozen set, one rerun** (version 3, 144 scripted calls, `openai/gpt-6-luna`; never tuned on). 3,391 requests, 2,733 from the cache, 0.053 USD. Groups come from the set's customer labels; a miss is a customer with a problem ending `clear` or `understanding_gap`. Wilson 95% intervals.

| Hindi + Hinglish (72 calls, 36 base cases) | calls | base cases |
|---|---|---|
| Customers with a problem: misses | 4 of 38 (11 per 100; 4 to 24) | 2 of 19 (3 to 31) |
| ... their tiers | refer 30, incomplete 4, understanding_gap 4 | |
| Informed, compliant record: referrals | 0 of 18 (0 to 18); all 18 `clear` | 0 of 9 |
| Informed, a fault on the record: referrals | 8 of 16 (refer 8, incomplete 2, understanding_gap 6) | 4 of 8 |

- The 2 missed base cases are U06 (told cover ₹10 lakh, record ₹3 lakh) and U07 (told 15 days to cancel, record 30). Both are wrong beliefs about cover and the cancellation window, which the contract's tier table puts in `understanding_gap`. The rule engine on the set's own extraction misses the same 4 calls, so the cause is the tier table, not the extractor. Whether a wrong figure (not "I don't know") for cover or the window should be `refer` is a coordinator decision. It must not be changed because of this run.
- Tamil (experimental): misses 3 of 19 (B03 false clear, U06, U07). Kannada (experimental): 2 of 19. Referrals of informed customers on a compliant record: 0 of 9 each.
- Strict verdicts: 143 of 144 from the cache (B03-ta, the iteration-1 false clear: needs the payment-frequency question in the dialogue). Fields 2,163 of 2,180. The live pass gave 142 of 144: U04-ta's cover request was sent twice at the same time, the two live answers differed, and the cache kept the second. The live pass is in `eval/text_path/runs/p3a__frozen-live-pass.md`, the cached rerun in `frozen__openai-gpt-6-luna.md`. Hindi and Hinglish rows are identical in both. The iteration-1 report is in `runs/iter1/`.
- A regression from dropping trimming: U07-hi's cover span came back "तीन लाख तक" and is now refused (`value_not_parsed`). Before, `tighten` cut it to "तीन लाख". It changes no tier.

**The judge's three typed transcripts** (`references/reviews/iter1/judge-probes/`, compliant record), run with `eval/text_path/run_transcript.py`:

| Transcript | Tier | Before (iteration 1) |
|---|---|---|
| misled Hinglish | `refer`: 6 flags and 6 gaps, merged into 4 summary lines (FD; guaranteed return and withdrawal; premium, consent, payment and bundling undecided; term, cover and window) | 11 flags |
| informed Hindi (b) | `clear` | clear |
| ordinary informed Hindi | `incomplete`: premium range read (₹50,000 to ₹52,000) but never read back, because the iteration-1 dialogue made no read-back; the window "don't know", cover with no figure and term `not_comparable` are `understanding_gap` | `flag_for_review`, 1 flag and 4 gaps |

The ordinary customer is no longer a referral. With a read-back of the range added and `tenure_months: 24` on the record (my variant, in the scratchpad), the call is `understanding_gap`. The misled customer's "bavan hazaar" is romanised and still refused: romanised Hindi amounts are out of scope.

Spend: OpenRouter 0.053 USD in this pass (ledger 0.5763 to 0.6297 USD, all chat rows). No Gnani calls.

## 4. Left open

- Verifier findings 10 (three silent passes in the engine) and 8 (50,002, 1,00,020): not in this package.
- `extractor_attacks.py` case 6 ("…, ऐसा तो नहीं था" negating in the next clause) still ends `clear` when the model says stated.
- Finding 1 needs the dialogue to tag a bot turn `asks=payment_frequency`. The extraction field and the rule exist.
- Trimming: an allow-list of harmless words to the right of a number ("तक", "का", "कटे") would recover U07-hi. Design it on the development set and measure it on a fresh set, not on this one.
- Concurrent identical requests in one run can get two different live answers (U04-ta). The fix belongs in the LLM client (single-flight per cache key), which is outside these paths.
- The probe scripts need `"took_nothing": false` in their scripted `RecallReply` outputs.
- No independent review yet.

## 5. Document lines made stale

- `ORCHESTRATION.md:77` "1,223 core tests pass": now 1,662. `:81` "176 tests pass (`tests/extract/`)": now 242.
- `README.md:12` "1,223 core tests pass": now 1,662. `README.md:16` "176 extractor tests": now 242.
- `CLAUDE.md:71` "Tests: `tests/extract/` (176 …)": now 242. The `samajh/extract/` entry should add that one failed model call makes only its own fields `Unclear(extraction_failed)` and that spans are never trimmed.
- `DESIGN.md:222` "Any product with a flag → `flag_for_review`": verdicts stay for gold, and triage now reads `Tier` (`refer`, `incomplete`, `understanding_gap`, `clear`; table in `references/pilots/P3a-contract.md` §1).
- `DESIGN.md:405` "Hedged amounts and two amounts in one reply are not taken": the parser now reads hedged amounts and narrow ranges (`parse_approx_amount`). The dialogue side belongs to P2.
- `DESIGN.md:461` (open item 23): decided. One bad output makes only that field `unclear`.
- `references/pilots/W5-extractor-report.md:442` "One invalid output fails the whole call": superseded.
