# P1c report: the server matched to dialogue round 3, re-voiced and replayed

Builder evidence, not independent verification. Finished 21:26 IST, 2026-11-10. Nothing committed.

## 1. The three failing tests

- `test_server_prompts.py::test_the_fixed_lines_are_every_line_that_does_not_carry_the_customers_figure[hi]` and `[hi-en]`: **both a stale test and a server bug.** The test pinned the round 2 fact that `teach_back.intro_nth` carries an ordinal in every language (round 3 removed it in hi and hi-en on purpose). It also showed that `samajh/server/prompts.py` voiced `intro_nth` with the first ordinal, a clip round 3 never speaks (the first product now always gets `teach_back.intro`). Server fix: `_fillings` makes `intro_nth` only for the second and later products, so a one-product record gets none. Test fix: a two-product record is added; ta and kn keep the old assertion.
- `test_samajh_dialogue.py::test_with_a_key_the_fallback_client_gets_a_short_timeout_and_one_attempt`: **stale test; the wiring is intact.** Round 3 asks the classifier less, so all 16 replies of the scripted informed customer are settled by the word lists and the failing LLM was never asked. The test now gives one reply the word lists leave unsettled, and also asserts that turn is marked degraded.

## 2. Server changes

- **`prefetch` wired:** `samajh/server/app.py:614` calls it as soon as the Prisma v3.0 transcript exists and before the v2.5 reading is asked. It never raises into a turn, skips empty text, and the stub dialogue has a no-op. A call begun there is reused by `step` (same text, language, expecting, question). It gives a head start only on two-reading turns; on a one-reading turn `step` follows at once.
- **`speaker_confirmed` and degraded turns:** no server fix needed. Real values now reach the turn response, the session and the case file (True after the birth-year check, False before it, never null). New test: `tests/server/test_readings_fields.py`.
- **Tests:** `uv run pytest tests/server -q`: **381 passed, 1 deselected** (the live test). `tests/dialogue`: 1,783 passed. New file `tests/server/test_prefetch.py` (5 tests).
- **Files changed:** `samajh/server/` `app.py`, `samajh_dialogue.py`, `dialogue.py`, `prompts.py`; `tests/server/` `test_server_prompts.py`, `test_samajh_dialogue.py`, `test_readings_fields.py`, `test_prefetch.py`; `tests/fixtures/server/calls/` (hero and informed re-prepared: 15 turns each; third-party and amount-check came out byte-identical).

## 3. Voiced

- Fixed lines, hi and hi-en: 92 new clips (47 + 45), about 12.6 estimated credits. Far more than the three changed lines, because nothing had been re-voiced since round 2. After the `prompts.py` fix a rebuild gave 70 lines per language, 70 cache hits.
- The loan-book call's name and lender lines: 6 new clips, 1.5 credits (made through `prompts.build`, since the CLI takes only packaged records).
- **The lines are not final: the voiced lines must be rebuilt after the user's wording review.**

## 4. Replays (own server on port 8086, scratch state directories outside the repo)

| Call | Outcome | Tier | Fixed lines: cache hits | Latency median / max / n | Turns with an uncached STT reading |
|---|---|---|---|---|---|
| third-party (hi) | wrong_party | incomplete | 2 of 2 | 28 ms / 28 ms / 1 | 0 |
| hero (hi) | completed | refer | 25 of 25 | 3 ms / 1,879 ms / 15 | 2 |
| informed (hi-en) | completed | **refer** | 24 of 24 | 3 ms / 1,704 ms / 15 | 2 |
| amount-check (hi) | completed | **refer** | 26 of 26 | 451 ms / 2,429 ms / 17 | 12 |
| loan SYN-PL-270202-0095 (hi) | completed | understanding_gap | 24 of 24 | 417 ms / 2,037 ms / 15 | 7 |

- **Every fixed line in every replay was a cache hit.** The only Timbre calls made on a call were the read-backs, which carry the customer's figure.
- **Latency is server time only:** upload received to the reply's audio made (`server_ms` plus the reply's Timbre time). It leaves out the phone's end-of-speech wait and grace window, and most STT readings were cache hits, so the medians are not line figures. The maxima are turns where the classifier was consulted (1.3 to 1.9 s in the dialogue), all one-reading turns where prefetch cannot help.
- **Amount disagreement, as wanted:** v3.0 wrote "2,000 रुपये रुपये दिए थे।", v2.5 wrote "₹2,012 दिए थे"; the bot asked again, the readings differed again, the bot read back, the customer confirmed.
- `speaker_confirmed` True on the four completed calls, False on third-party; no degraded turn in any call.
- The four persona replays first ran one formatting edit before the builder's last save of `app.py`; rerun on the final code they gave the same outcomes, tiers and cache hits. The latency figures are from the first runs. The loan call ran on the final code.
- **Ingest:** `1 session(s) on drawn loans, 0 outside the sample, 0 skipped; 0 of those brought in had a case file changed after it was brought in` (batch B-2027H1-ec2bdb3e, draw D-2027-02-15).

## 5. Found, not fixed

**The informed and amount-check personas end in `refer`, not `clear`.** Round 2's payment-frequency question gets "one time, एक ही बार"; the rules (`samajh/rules/checks.py:257` and `:672`) check that against `one_time_payment` in the record's `features`, and all packaged demo records have `features: []`. The flag reads "Customer believes it is paid only once; the record does not list this feature", and it also adds a fifth refer line to the hero pack. P1's informed run 2 was `clear`. The likely fix is one line per record in `samajh/server/records/*.json` (list `one_time_payment` for these single-premium products deducted from the loan), but it changes what the demo shows, so it is left for the coordinator's decision.

## 6. Credits

About 22.3 estimated Gnani credits of the 60 allowed (Timbre 15.5, Batch 6.1, STT 0.7), from the client ledger since 21:15 IST. OpenRouter about $0.015.

## 7. Not run or not checked

- No person and no microphone: every customer turn is Timbre audio.
- No mutation check that the prefetch-reuse test fails without reuse (the builder argued it from the call count).
- Dialogue limit, not the server's: when both readings have the same text, `step` asks the classifier a second time for it.
- Scratch outputs (replays, case files, session copies): `/private/tmp/claude-501/-Users-masterpanda-projects-gnani-voice-ai-challenge/0d303c72-2c71-4f88-8b56-b36934c40ed1/scratchpad/` (`out/`, `out2/`, `state-book/`, `analyse.py`).
