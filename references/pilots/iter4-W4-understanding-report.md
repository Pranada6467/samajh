# W4: the call uses what it knows (iteration 4, wave 2)

Base 29e0747 (after W1), branch `dev`, uncommitted. **How it was built:** I orchestrated. One Opus-low builder did four checkpoints (Parts 1, 2 and 3, then Part 4, the faults W3 found) and one fix round. I reviewed each diff and ran the tests. One Opus-high checker wrote fresh banks before reading any W4 code; there was one fix round, then I stopped. Typed text only: no speech, no Gnani calls.

## What was built
- **Part 1: a context-aware classifier decides at the opening** (`samajh/dialogue/llm_fallback.py`, `machine.py`, `interpret.py`).
  - At the name question and the go-ahead, every reply goes to the classifier with: the stage, the record's first name, name hints from W1's `judge_name`, the previous exchange, and a strict per-stage closed label set (`create_model`).
  - Word lists are only hard vetoes, and a veto reply is never sent: decline, do-not-call, a human, a call-back, written, `wrong_person`, a language request, and a takeover sign at the go-ahead.
  - In the machine (`_on_identity_judged`), `confirms_self` passes. A third-party sign or another name still ends `wrong_party`, except that a who-is-calling question only re-asks once. `doubts_claim` is split into `third_party_sign` (a veto) and `hedges_claim`; a hedge on the claim itself still blocks the pass.
  - Failure, timeout or `unclear` gives today's reading, marked degraded, so the session is voided. The 2.5 s limit is unchanged.
  - A context reaches only an interpreter with `wants_context = True`; old stubs and `RuleInterpreter` are unchanged.
  - **Review §3 item 8 is fixed: the reply to the year question is no longer sent to any model.** It is never begun or asked, and the context drops any `second_check` turn. A loose year passes on "my/I", or when the reply has one year and no third-person, kin or other-name word.
- **Part 2: a language request is heard.**
  - A new classifier label `language_request` has a `language` enum. A word-list `other_language` is a veto at every stage, so a yes cannot overrule it.
  - With a prompt file (ta, kn; English → hi-en, the closest file), the call switches live. It sets `state.language`, logs a `LanguageSwitch` in `CallState`/`EndOfCall.language_switches`, says `language.switched` in the new language and puts the pending question again. The limit is 2 switches, and there is no switch while `speaker_doubt` holds.
  - Without a file (Telugu and others), the reworded `end.language` says the call cannot go on in that language. The call ends with the existing `Outcome.language_switch`, which ops treats as a retry in that language, and `requested_language` is kept.
- **Part 3: one follow-up for a half answer.**
  - `samajh/rules/halves.py` (new, pure): `method_only` (calls `checks._method_only`, unchanged), `what_only` and `missing_half`, exported from `samajh.rules`. No rule outcome changed (`tests/core` passes, no edits).
  - `samajh/dialogue/halves.py`: a deterministic reading of the consent reply into `Answer` values, plus `kind_is_half`.
  - At most one follow-up per slot (`CallState.follow_ups`): `consent.follow_what`, `consent.follow_how`, `kind.follow_what`. The choice depends only on the customer's words.
  - The extractor reads a follow-up reply as another reply to the same question: `samajh/extract/_extract.py:204` and `_resolve`.
- **Part 4 (W3's faults).**
  - A deferral ("you check the records") is `Intent.defers`: one `defer.reask`, then the next question, with the slot left a gap. A refusal said with it stays a refusal.
  - A negated again-word is no longer a call-back or a repeat request.
  - Each slot can be put at most twice (`CallState.puts`), with a seeded random-walk termination test.
  - Recall that names a thing with a forgotten amount goes to the product questions.
- **Fix-round side change:** W1's matcher now treats two keys of 8 or more letters that differ only by a final vowel as `same` (Satyanarayana/सत्यनारायण). Amit/Amita, Vijay/Vijaya and Kamal/Kamla stay different, and the dev-list counts are unchanged.
- **New lines (for the user's wording review; no fluent reader has seen them; Tamil and Kannada `not human-reviewed`):** `language.switched`, `end.language` (reworded), `consent.follow_what`, `consent.follow_how`, `kind.follow_what` and `defer.reask`, in 4 files, 77 lines each. The hi text, for example: "और वो हाँ किस चीज़ के लिए थी?", "और वो हाँ आपने किस तरह दी थी?", "और उस चीज़ को आप क्या कहेंगे, वो क्या है?", "हम यह जानना चाहते हैं कि आपको ख़ुद क्या याद है, रिकॉर्ड में क्या है वो नहीं।", "ठीक है, अब हिंदी में बात करते हैं।". All lines are in `references/pilots/P2-lines-for-review.md` (regenerated).
- **Tests:** 4 new files, `tests/dialogue/test_w4_{context_classifier,language,follow_up,w3_faults}.py`, 73 cases. 8 existing files were changed for intended behaviour: the opening now reaches the classifier, the year never does, the shared consent fixture is no longer HOW-only, and a Tamil request now switches. The checker's banks, harness and full report are in `tests/dialogue/probes/w4/` (`CHECKER-REPORT.md`).

## Measurements (synthetic typed text; Wilson 95%)
**Fresh bank, before vs after.** The checker's live classifier arm, written before the code was read. "Before" is 107a908.

| Metric | 107a908 | W4 before fix round (held-out) | After fix round (rerun of a seen set) |
|---|---|---|---|
| False rejections per 100 genuine borrowers | 4/90 = 4.4 [1.7–10.9] | 4/90 = 4.4 [1.7–10.9] | rules 0/90 [0–4.1]; live 0/90* |
| Loan or lender named per 100 third parties | 0/49 [0–7.3] | 0/49 [0–7.3] | 0/49 |
| Yes-twice third parties passed (accepted by design) | 7/7 | 7/7 | 7/7 |
| Refusals asked a further question per 100 | 0/30 [0–11.4] | 0/30 [0–11.4] | 0/30 |
| Language with a file honoured per 100 | 0/14 [0–21.5] | 14/14 [78.5–100] | 14/14 |
| Language without a file: ends `language_switch` with the language recorded | 13/15 | 15/15 [79.6–100] | 15/15 |
| Language request inside a yes honoured | 4/14 | 14/14 | 14/14 |
| Consent half answers left incomplete per 100 | 15/15 | 1/15 = 6.7 [1.2–29.8] | 0/15 [0–20.4] |
| Kind half answers (figure or does-only) left incomplete | 10/12 | 5/12 | 3/12 |
| Follow-ups that revealed a record value, digit or product word | — | 0 | 0 |
| Deferrals ending `declined` per 100 | 0/18 | 0/18 | 0/18 |
| Negated-again read as a call-back | 2/18 | 0/18 | 0/18 |
| Forgotten amount sent to took-nothing | 4/14 | 4/14 | 0/14 |
| Year replies in any classifier request (20 year-check calls) | 6/6 requests held it | 0/40 | 0/40 |
| Lender or loan named before the right-party pass | 0/229 | 0/229 | 0/229 |

\* The post-fix live arm is contaminated. Midway, OpenRouter returned **HTTP 402 "Insufficient credits"**, so 62 uncached classifier calls failed and 57 of 372 calls were voided as degraded. The live post-fix numbers mix classifier and fallback readings. Only the before-fix column is held-out.

- **Classifier latency** (checker's after arm, live, uncached n=295, 4 cases in parallel): median 1.15 s, p90 1.58 s, max 3.81 s, 3 calls over 2.5 s. At 107a908 (uncached n=231): median 0.74 s, p90 1.12 s. The opening now asks on almost every reply: bank A made 192 requests, against 151.
- **Void rate** (calls with a degraded turn, held-out after arm): 4/372 = 1.1 [0.4–2.7]; before, 1/372.
- **Iteration 3 probes rerun** (`call`, `r2`, `call2` plus the `s` variants, 151 + 151 + 97 inputs), beside the stored outputs. Live arm, after checkpoint 4:
  - `call`: genuine 16/16 and 9/10 (unchanged); third parties 26/26 (unchanged); false claimants 15/15 and 10/10 (was 13/15 and 8/10); refusals 26/26; takeovers 15/15 and 10/10 (was 11/15 and 9/10); year in bot lines or records: none.
  - `r2`: every count identical, including the known year-of-birth faults (a_open_claim yob1 6/12; the lender named before the year 4/12, the documented C-y08 class).
  - `call2`: K3 8/8 (was 7/8), K7 8/8 (was 7/8), K4 own relative 6/8 (was 7/8). In the two K4 cases a genuine borrower who mentions a relative ends `wrong_party`; that is the cost direction, and nothing is named.
  - Failing arm, after the fix round: every group equal to or better than stored. The lender named before the pass: none.
  - My spend on these reruns was about USD 0.008. The scratch copy of `call_run.py` needed one fix: it assumed the label is an enum, and the new per-stage schema returns a string.
- **LLM spend for W4:** about USD 0.27 (the checker 0.263, me about 0.008, builders 0).

## The checker's findings (its words) and what I did
- F1 "A claim followed by 'who is calling?' ends `wrong_party` (new in W4)." Fixed: a who-question is no longer read as another speaker, and a whom-only sign re-asks once. Name hints no longer label ordinary words.
- F2 "Satyanarayana … ends `wrong_party` … came in with W1." Fixed with the final-vowel rule.
- F3 "The word 'एक' blocks the consent follow-up." Fixed: only a figure of 100 or more counts as the WHAT half.
- F4 "'What it does' replies get no kind follow-up." Widened; 3 of 12 are still left incomplete. Kind-only replies get no "what does it do" follow-up, by design.
- F5 "A refusal next to a deferral is lost (new in W4)." Fixed: a refusal said with a deferral is not a deferral, and a long deferral goes to the classifier.
- F6 "Forgotten amount still goes to the took-nothing branch." Fixed.
- F7 "Chatty years now fail the year check." Fixed: a single year with no third-person word counts. Y2 now passes 9/10.

## Left open (said plainly)
- **New in the fix round (word lists only):** a refusal to answer ("ये सब बातें मैं आपको क्यों बताऊँ?") is read as a deferral and gets `defer.reask` (2 of 7 consent refusals). The live arm had 0 of 7. Not fixed: the one fix round was spent.
- **OpenRouter credits ran out (HTTP 402) during my post-fix rerun.** With no credits, every opening reply is degraded and every session voided. This must be topped up before the human calls on 2026-11-15.
- **No P5b post-fix rerun:** the `eval/p5` player does not map the five new keys (`tests/p5/test_p5_player.py` fails), and there are no credits.
- **Not tried:** AI4Bharat IndicXlit, IndicLID and `indic-transliteration`.
  - Language detection already caught 29 of the 29 countable requests on the fresh bank, so there was no measured gap for IndicLID.
  - Names were left to W1's matcher. IndicXlit was not evaluated for lack of time.
- **Smaller items:**
  - The opening adds about 0.4 s median latency per turn.
  - A self-claim said in the same turn as a language switch must be said again.
  - With word lists alone, a genuine Tamil borrower ends `not_confirmed`.
  - The stop words in the deferral rule are a word list, so a short refusal phrased outside it still reads as a deferral.
  - The final-vowel rule needs 8 or more letters.
  - A year passes without "my" (the F7 trade-off).

## Needed from others
- **Coordinator:**
  - Voice the six new or changed lines (`uv run python -m samajh.server.prompts build --lang hi --lang hi-en`; also `ta` and `kn` if a live switch will be demoed).
  - Top up OpenRouter.
  - The server needs no change for the live switch: STT and TTS follow `BotUtterance.language` (`samajh/server/speech.py:115`).
- **Server owner:** `tests/server/test_prefetch.py::test_a_classifier_begun_in_prefetch_is_not_asked_again_by_step` asserts no classifier call before open recall. That is now intended: the opening always asks, so count calls from the recall turn on. Consider adding `language_switches` and `judged` to the session log and the case file.
- **P5 owner:** map `language.switched`, `consent.follow_what`, `consent.follow_how`, `kind.follow_what` and `defer.reask` in the `eval/p5` player.
- **Ops owner:** report the requested languages from `language_switch` endings.
- **Documentation worker:**
  - The year reply no longer reaches the classifier. Use the checker's allowed wording, which says "at the year question".
  - The language switch.
  - The follow-ups.
  - The checker's report could live at `references/reviews/iter4/verify-W4.md`.
  - The checker's forbidden list stands, for example no live false-rejection rate below 4 per 100 from a held-out run.

## Tests
- `uv run pytest tests/dialogue -q`: **3804 passed** (126 s).
- `uv run pytest tests/core -q`: 2239 passed (in the combined dialogue+core run, 6043 passed).
- Whole offline suite (`uv run pytest -q -m "not live"`): **6 failed, 8754 passed**. The failures:
  - `tests/p5/test_p5_player.py` and 2 in `tests/server/test_prefetch.py`: other owners' files, failing on intended W4 changes (listed above).
  - 3 in `tests/server/test_stream_turns.py`: W5's work in progress. They pass alone (14 passed).
- Prompt lint: `load_prompts` passes for hi, hi-en, ta and kn (77 lines each).
- `ruff check` on the changed dialogue files is clean.

## Addendum (2026-11-14, after commit abbf0cd): two follow-ups, builder-verified (no independent check, no LLM)
- **A one-time frequency answer ended a classifier-less call `declined`.** On the latency worker's replay with the classifier failing (HTTP 402), "One time, एक ही बार।" at `payment_frequency.ask` went to `stop_check.decline`, then `end.declined`.
  - **Cause:** no stop or refusal word list was involved. The answer held no word of the sale's vocabulary (`Lexicon.substance` had साल/महीने/month but nothing for "once"), so the word lists left it unsettled. The classifier was then asked and failed, so the turn was degraded. The degraded path asks "shall I go on?" once, and the replay's next scripted answer held a no-word, which ended the call.
  - **Fix (`samajh/dialogue/_lexicon.py`):** one-time and count phrases added to `substance`: एक बार, एक ही बार, दो बार, हर बार, ek baar/bar, ek hi baar/bar, do baar, har baar, one time, onetime, once, single payment, किश्तों, kishton. Such an answer is now settled by the word lists, and the classifier is not asked.
  - **Neighbours checked at the frequency question**, hi and hi-en, word lists alone and with a failing classifier: one time, ek baar, ek hi baar, sirf ek baar, एक ही बार दिया था, har mahine, monthly, saal mein ek baar. All move on to the next question with no stop check and no degraded turn.
  - "मुझे बात नहीं करनी" and "एक बार, पर अब मुझे बात नहीं करनी, फ़ोन रखिए" still end `declined`, and "ek baar phir se boliye" still reads as a request to repeat.
  - The new test fails on the committed lexicon and passes with the fix.
  - Not changed: a degraded free answer at any later question still gets one "shall I go on?". That is the documented degraded path, and such a session is void.
- **The P5 player now maps the W4 keys (`eval/p5/player.py`).**
  - `consent.follow_what` and `consent.follow_how` map to `what_you_agreed_to`, and `kind.follow_what` maps to `what_is_it`: the same frozen topic as their question.
  - `language.switched` and `defer.reask` go to `NO_REPLY`, because they only lead into a question. A new dialogue test checks they are never the last line of an utterance.
  - P5 and P5b were not rerun.
- **Tests:**
  - `tests/dialogue/test_w4_w3_faults.py` has 4 new functions (17 cases).
  - `tests/p5/test_p5_player.py` has 1 new test.
  - `uv run pytest tests/dialogue tests/p5 -q` gives **3867 passed**, and `tests/p5/test_p5_player.py` now passes.
  - `ruff check` is clean.
