# Verification of P2 round 4 (narrow check)

**Scope.** I am an independent verifier and wrote none of this code. The coordinator decided to keep this check narrow: four groups, two arms, one run each. I wrote 48 new Hindi and Hinglish typed-text inputs before running anything and before reading any round 4 test, probe, P2-report §7 or `p2_r3_inputs.json`: `references/reviews/iter2/probes/p2_r4_inputs.json`, sha256 `c68508e1deed2f10bcc53d2ab599d6f993bb5238ba2fb66883f840deb60f3b9f`. Record `record_gold_loan.json`, lender "Udaharan Bank". Arms: **live** (`LlmFallbackInterpreter` over `LlmClient.from_env(timeout=3.0, max_attempts=1)`, built the same way as the r3 harness, 3 threads) and **failing** (the same interpreter with a client that raises). Harness: `probes/p2_r4_run.py`. Outputs: `probes/p2_r4_out_{live,failing}.jsonl`, viewer `p2_r4_show.py`. I edited nothing under `samajh/`, `tests/`, `data/` or `web/`. No Gnani calls, no git changes.
**Route to the who-check (G1):** borrower prefix "हाँ जी" / "1984" / "हाँ", then at recall "हेलो? हाँ, कौन बोल रहा है?". It reached `AtStopCheck(wish=who)` on 12 of 12 inputs in each arm. The other two candidate routes were never needed.
**"Named"** means: the text contains `Udaharan|उदाहरण`, `लोन|loan|ऋण|क़र्ज़|कर्ज`, or `बीमा|insurance|policy|पॉलिसी|premium|प्रीमियम|कवर|cover`; or a line key is `context.loan`, `teach_back.*`, `verify.after_loan` or `verify.before_loan`. Every bot line after the tested turn was searched.

## Verdict: ready with conditions (consenting testers playing customers only); not ready for anyone else
- **Round 3 condition 1 still stands:** the classifier must be on, and sessions with a degraded turn must be voided (see G2, failing).
- **Condition 2 (a yes plus an admission at the who-check resumes the call): held on this n.** 6 of 6 ended `wrong_party` in each arm, with nothing named afterwards.
- **Condition 3 (the year gets one attempt): held on this n.** No slip ended the call. Every clearly different year ended at once. Keep telling testers that a different year gets one attempt.
- **Condition 4 (a refusal is not logged as a wrong party): not held.** 2 of 7 refusals still end `wrong_party` in both arms.
- **Classifier-failing takeover finding: partly held.** 9 of 9 takeovers got the who-check or an end, and nothing was named before a who-check passed. But a bare "हाँ" from the third party passes the who-check, and the loan was then named in 6 of 6.
- **Condition 5 (`verify.before_loan` wording): not checked here.**

## Counts (live / failing)
**G1, who-check replies (n = 12).**
- Admission with a yes (6): ended `wrong_party` 6 / 6, nothing named 6 / 6. Live, 2 of the 6 turns were degraded and read by the word lists, so the classifier itself judged 4.
- Refusals to say (2): ended `wrong_party` 2 / 2, nothing named.
- Affirmations (4): resumed at recall 4 / 4. The resumed line names the loan, as designed.

**G2, takeovers after the year passed (9: 3 each at go-ahead, recall and kind).**
- Live: ended `wrong_party` at once 9 of 9, nothing named.
- Failing: 3 ended at once (all at the go-ahead). The other 6 (recall, kind) got `right_party.reask`, with nothing named before the reply.
- Failing, after the follow-up "हाँ": the who-check passed on that "हाँ" in 6 of 6, and the loan was named afterwards in 6 of 6 (`open_recall.reask`, `kind.reask`, …).

**G2, relatives mentioned by the borrower (3).**
- Live: 2 went straight on (`teach_back.intro` or `open_recall.nothing`). 1 got the who-check, passed on "हाँ" and resumed (that turn was degraded).
- Failing: 3 of 3 got the who-check, then resumed on "हाँ".
- A who-check here is a cost, not a fault.

**G3, birth year (n = 12).**
- Slips (6): passed 5 / 5, re-asked once 1 / 1, ended 0 / 0.
- Clearly different years (4): ended `second_check_failed` at once 4 / 4. None passed and none got a second attempt, in either arm.
- "Don't remember" (2): re-asked once 2 / 2 (degraded in both arms).

**G4, opening refusals (n = 12).**
- Correct outcome: 9 / 9.
- `speaker_confirmed` was False on 12 / 12, and nothing was named in any end line on 12 / 12. The end keys were `end.declined`, `end.do_not_call` and `end.third_party` only.

## Failing inputs, verbatim (the same result in both arms)
- G4-02 (opening) "nahi bhai, interested nahi hoon" → `wrong_party` (expected `declined`). Inferred: the address form "bhai" followed by "hoon" falls outside §8's follow-up rule for address forms, which requires no "हूं / am" after the address form.
- G4-05 (re-ask) "नहीं जी, मैं ऐसी कॉल पे बात नहीं करता" → `wrong_party` (expected `declined`). Live, this turn was degraded.
- G4-10 (re-ask) "रमेश जी नहीं हैं, बाद में भी मत करना फोन" → `declined` (expected `wrong_party`; a third party logged as the borrower refusing). Nothing was named.
- G2, failing arm, 6 takeovers at recall and kind, for example "hello? ab main baat kar raha hoon, unka cousin" and "अरे मैं उनकी भाभी हूँ, वो सो गए". Each got the who-check, the third party's "हाँ" resumed the call, and the loan was named.
- G3-02 "उनीस सौ चौरासी" was re-asked rather than passed. That is allowed, not a fault.

## Wording for the project's documents
**Allowed:**
- "On 48 verifier-written Hindi and Hinglish text inputs, a yes plus an admission at the who-check ended `wrong_party` in 6 of 6 in each arm."
- "With the classifier live, 9 of 9 mid-call takeovers ended the call at once."
- "With the classifier failing, 9 of 9 takeovers got the who-check or an end, but a bare 'हाँ' at the who-check resumed the call and the loan was named in 6 of 6."
- "No clearly different year passed or got a second attempt (4 of 4 ended, each arm); 5 of 6 spelling slips of the right year passed."
- "2 of 7 opening refusals are still logged as `wrong_party`."

**Forbidden:** "tested on speech", "identity verified", "third parties learn nothing", "works without the classifier", "every refusal is honoured", "ready for real customers", any pooled rate, "condition 4 fixed".

## LLM spend
- 37 classifier requests: 11 from the cache, 2 client errors, 1 slower than 2.5 s. US$0.00076, as reported by the client.
- Live, 7 of 48 tested turns were marked degraded and read by the word lists: G1-01, G1-03, G2-12, G3-11, G3-12, G4-05, G4-12. Only 2 errors and 1 slow request were seen, so the cause of the rest was not traced.

## Not checked
- Speech and speech-to-text. Everything here is typed text.
- The rules-only arm.
- Whole calls from start to finish.
- Mutants.
- The call-back replies and "now".
- The classifier pool and latency under load.
- Tamil and Kannada.
- Records with more than one product.
- `verify.before_loan` timing and wording.
- The server, voiding of degraded sessions, and the ops changes.
- False claimants who give the right year (round 3's open finding stands untested).
- Whether the classifier's labels were right, beyond the outcomes above.
- The follow-up "हाँ" / "पता नहीं" after a takeover was my own scripted choice.
- No recheck after this report.
