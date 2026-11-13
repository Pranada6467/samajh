<!-- Saved by the CALL sub-orchestrator on 2026-11-13 from the verifier's final message, unchanged. -->
# Verification of the iteration 3, round 2 change: self-claims with a tail, removal at the opening, the go-ahead re-ask (typed text)

**Scope and inputs.** I am an independent verifier and wrote none of the code. The change under test is the uncommitted edit to `samajh/dialogue/interpret.py` and `machine.py`. I wrote 145 new Hindi and Hinglish cases, in Devanagari and romanised script. They use two borrowers: Ramesh (`record_gold_loan.json`, lender "Udaharan Bank") and Meena, a woman (`samajh/server/records/amount-check.json`, lender "नमूना बैंक"). I froze the cases before running either arm, and before reading `test_iter3_r2.py`, `data/p5` or `eval/p5/runs`. The only run before freezing used the word lists alone, to check that the route prefixes reach their stage (69 of 69 did).
- Inputs: `references/reviews/iter3/probes/r2_inputs.json`, sha256 `03d46d187d7e55fba641ab3a876efd13cda50c96e02242850bcdd1340f43babe`.
- Harness: `r2_run.py`, sha256 `be5877b8…6c`. It reuses `call_run.py` (sha256 `a1599373…eb`, unchanged) and adds the second lender to its "named" definition.
- Scorer, outputs and hashes: `r2_score.py`, `r2_out_{live,failing}.jsonl` and `r2_outputs.sha256`.
- Written after the frozen run, so not blind: the reroute `r2s_*` and the diagnostics `r2_diag*`.

Arms:
- **live:** `LlmFallbackInterpreter` over `LlmClient.from_env(timeout=3.0, max_attempts=1)`.
- **failing:** the same interpreter over a client that raises.

Settings: none, and year_of_birth with 1 attempt.

## Verdict
- **Claim 2 holds** on this n.
- **Claim 3 holds** with one live exception.
- **Claim 1 holds for third parties at both places and for genuine claims at the who-check, with one failing pattern for genuine borrowers.** A Devanagari address form ("भाई", "भैया") together with a question word ("किस", "कौन") is read as asking for someone else. At the opening that costs the borrower one more question. At the who-check it ends the call.
- **Nothing was named to a third party** in any case without a second check. With the year-of-birth setting on, one case let a third party hear the lender's name (below).

## Counts (live ; failing)

| Group | none | year_of_birth |
|---|---|---|
| (a) genuine claim plus chatter at the opening passes, nothing named before | 11/12 ; 11/12 | 10/12 ; 10/12 † |
| (b) genuine claim plus chatter at the who-check (go-ahead, recall) resumes, nothing named after the sign | 12/12 ; 12/12 | 12/12 ; 12/12 |
| (b) bare yes at the who-check ends `wrong_party` | 2/2 ; 2/2 | 2/2 ; 2/2 |
| (c) dressed third party at the opening does not pass, loan never named | 14/14 ; 14/14 | 14/14 ; 14/14 ‡ |
| (c) dressed third party at the who-check ends `wrong_party`, nothing named after the sign | 12/12 ; 12/12 | 12/12 ; 12/12 |
| (d) removal at the opening ends `do_not_call`, `speaker_confirmed` False, end line names nothing | 8/8 ; 8/8 | 8/8 ; 8/8 |
| (d) removal shaped as a third party ("mere bhai ka number hata do") ends `wrong_party` | 4/4 ; 4/4 | 4/4 ; 4/4 |
| (e) echo or short delay: one re-ask, then the next reply decides | 8/8 ; 8/8 | |
| (e) real later ends `call_back_later` | 4/4 ; 4/4 | |
| (e) refusal ends `declined` | 3/3 ; 3/3 | |
| (e) a delay twice ends `no_go_ahead` | 1/2 ; 2/2 | |

- No call got more than one re-ask (17 of 17).
- A later given after the re-ask with no time ("बाद में कॉल करना") gets "कब कॉल करें?" once, then ends `call_back_later`. I confirmed that with a follow-up turn.
- † Six of my 12 year-of-birth cases put the year at the go-ahead. With this setting, an explicit claim first gets the disclosure and the go-ahead, and the year comes after the go-ahead yes. I reran those six with the go-ahead yes added (`r2s_inputs.json`). The counts above use the rerun. Claim 1 is worded for "no second check", so this column is outside its scope.
- ‡ The loan was never named to a third party, but one live case heard the lender's name (below).
- **Degraded turns.** Live: 2 of 145 calls, c05 and c14 in the year setting. Both are third-party replies at the year question, degraded by design. Failing: every turn that asked the classifier is degraded (152 turns in 100 calls), by construction.

## Failing inputs, verbatim
- **a12, none, both arms.** "जी हाँ", then "हाँ भैया, मैं मीना हूँ, किस लिए फ़ोन किया?". Heard `purpose.before_confirm` and the direct question again; the call stays open.
  - Diagnostic (not blind): `doubts_claim` is True for this reply, for "मैं ही हूँ भाई, किस बारे में है?" and for "जी भाई साहब, रमेश बोल रहा हूँ, कौन बोल रहे हैं?". The `asks_for_another` test counts the address word as kin.
  - The same reply without the question passes, and so does the question without "भैया". The romanised "main hi hoon bhai, kis baare mein hai?" passes.
  - At the who-check, both Devanagari replies ended `wrong_party` in both arms: a genuine borrower loses the call.
- **e17, live.** "दो-तीन मिनट?", then "पाँच मिनट बाद". The classifier read the second reply as `call_later`, so the call asked "कब कॉल करें?" instead of ending `no_go_ahead`. Nothing was named.
- **Year-of-birth setting, outside claim 1 as worded:**
  - **a05 and a11, both arms, ended `wrong_party`:** "जी, मैं ख़ुद रमेश बोल रहा हूँ, पहले मेरे बेटे के पास फ़ोन था, अब बताइए" and "मैं ख़ुद मीना हूँ, अभी मेरे पति ने फ़ोन उठाया था, अब मैं बोल रही हूँ, बोलिए". Both pass with no second check. The new opening override runs only when `second_check is None` (`machine.py`).
  - **c04, live.** "मैं ही हूँ, आप किससे बात करना चाहते हैं?" is a third party. It got `disclosure.who` and `disclosure.recording`, which name the lender, then the go-ahead. The year question comes next. The `doubts_claim` guard is not applied on this path.
  - **Explicit claims.** In 4 of 4 live passes the lender was named before the year (C-y08, unchanged).

## Other checks
- `uv run pytest tests/dialogue -q`: 3726 passed.
- Whole suite: 5 failed, 8421 passed, 3 deselected, 36 errors. None is in `tests/dialogue`. The failures and errors are in `tests/ops` (39), `tests/p5/test_p5_data_dir.py` and `tests/server/test_readings_fields.py`. The visible cause is `KeyError: 'consent.insurance.phone_call'` in `samajh/scenarios/script.py`, which comes with other workers' uncommitted edits (ops, rules, types). I did not chase each one.
- `git diff data/prompts` and `git status data/prompts` are empty: no bot line differs from HEAD.

## Wording for the project's documents
**Allowed:**
- "On 145 verifier-written typed inputs (two borrowers, one a woman), no third party dressed as the borrower passed the opening or the who-check (26 of 26 at the opening and 24 of 24 at the who-check, each arm), and nothing naming the loan was spoken to one."
- "With no second check, 11 of 12 genuine self-claims followed by a question or chatter passed at the opening, and 24 of 24 resumed at the who-check, in each arm."
- "16 of 16 removal requests at the opening ended as do-not-call with the speaker unconfirmed; 8 of 8 removals of a relative's number ended as a wrong party."
- "At the go-ahead, 8 of 8 echoes or short delays got exactly one re-ask."

**Forbidden.** All bans in `verify-call.md` and the judge's §6 stay banned: "third parties learn nothing", "identity verified", "tested on speech", "ready for real customers", "works without the classifier", any pooled rate. Also banned:
- "address forms never block a claim";
- "a self-claim passes whatever follows it";
- "the year-of-birth setting accepts the same claims";
- "nothing names the lender before the year".

## LLM spend
About US$0.0032 by the client's own count:
- live run: 152 requests, 72 from the cache, 0 errors, slowest 1.71 s, US$0.00284;
- diagnostics: US$0.00034.

No Gnani calls.

## Not checked
- Speech and STT: everything is typed text.
- Tamil and Kannada.
- Records with more than one product.
- year_of_birth with 2 attempts.
- The server and case file.
- Whether the classifier's labels were right, beyond the outcomes.
- `close.verify` while a sign is unsettled.
- The follow-up replies were my own scripted choices.
