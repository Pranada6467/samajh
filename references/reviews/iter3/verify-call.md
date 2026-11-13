<!-- Saved by the CALL sub-orchestrator on 2026-11-13 from the verifier's final message, unchanged. Part 2 (server, case file, phone) is appended below it when it arrives. -->
# Verification of the iteration 3 call package (part 1 of 2: dialogue, lines, ops; server, case file and phone follow)

**Scope.** I am an independent verifier and wrote none of this code. I wrote 151 new Hindi and Hinglish typed-text inputs (Devanagari and romanised) and froze them before any arm ran and before I read `test_p8_identity.py`, `test_iter3_call.py` or any builder or earlier-verifier probe. The only run before freezing used the word lists alone, to confirm that the route prefixes reach their stage (38 of 38 did).
- `references/reviews/iter3/probes/call_inputs.json`, sha256 `2df062a3bbaa6b9c019826a85e1e240ef7a9368569a9f6acce0be21b6561ede9`.
- Harness `call_run.py`, sha256 `a15993738274d47b407b985864fdebc19625ed44fde8b787c34654eddbfd9deb`.
- Outputs `call_out_{live,failing}.jsonl`, classifier log `call_out_live.requests.jsonl`, scorer `call_score.py`, ops check `call_ops_void.py`.

Record `record_gold_loan.json` (Ramesh, 1984), lender "Udaharan Bank". Settings: none, year_of_birth with 1 attempt, year_of_birth with 2 attempts.

Arms:
- **live:** `LlmFallbackInterpreter` over `LlmClient.from_env(timeout=3.0, max_attempts=1)`, as `samajh_dialogue.py` builds it.
- **failing:** the same interpreter over a client that raises.

"Named" uses the verify-P2-r4 definition. I edited nothing under `samajh/`, `tests/`, `data/`, `web/` or `eval/`; mutants ran in a scratch copy. No Gnani calls, no git changes.

## Verdict: the opening is ready as claimed; mid-call takeovers are not. Not ready for anyone but consenting testers playing customers.

**Held on this n:**
- The default opening, in both settings.
- Opening refusals (round 4 condition 4 now holds).
- A bare yes, a hedge or another name at the who-check ends the call, in every case that reached it.
- Two attempts at the birth year.
- The year never reaches a classifier prompt, a bot line, the identity record or an end-of-call record.

**New fault class: a takeover that does not reach the who-check.** After the right-party pass, the loan was named in reply to the takeover turn in 7 of 25 takeover inputs live (6 clear takeovers, 1 ambiguous) and 2 of 25 failing. Two causes:
1. **At the go-ahead the classifier overrides the word lists' `wrong_person`.** In `llm_fallback.interpret`, a go-ahead label of answer, yes or confirms_self becomes yes, and who_or_why becomes asks_who. `machine.step` runs no who-check at the go-ahead (it counts as before the loan), and it answers asks_who with `verify.after_loan` once the speaker is confirmed. The failing arm (word lists alone) ended E-n02 and E-y01 correctly; the live arm named the loan in both.
2. **Mid-call, a "whom do you want / who were you talking to?" question raises no takeover sign.** It is answered with `verify.after_loan`, which names the lender and "the loan".

## Counts (live / failing; "p of n")

| Group | none | year_of_birth |
|---|---|---|
| A genuine borrowers pass | 16/16 ; 12/16 (3 explicit claims got the direct question again, call still open; A-n13 ended `not_confirmed`) | 9/10 ; 9/10 (A-y09 near-spelling re-asked) |
| B third parties do not pass, nothing named | 16/16 ; 16/16 | 10/10 ; 10/10 |
| C false claimants who should not pass | 8/10 ; 9/10 | 5/7 ; 6/7 |
| C false claimants the design accepts (they pass) | 5/5 ; 4/5 (yes twice, or an outright false claim) | 3/3 ; 3/3 (knows the year) |
| D refusals end as asked, nothing named | 16/16 ; 16/16 | 10/10 ; 9/10 |
| E takeover ends `wrong_party`, nothing named after it | 7/10 ; 8/10 | 6/7 ; 7/7 |
| E genuine self-claim at the who-check resumes | 2/3 ; 0/3 | 1/1 ; 0/1 |
| E false self-claim at the who-check (accepted residual) | resumed 3/3 in each arm (2 none, 1 year of birth) | |
| E2 borrower mentions a relative: ended (cost) | 0/8 ; 3/8 | 2/5 ; 2/5 |
| F two attempts: wrong then right passes | | 4/5 ; 4/5 |
| F two attempts: two wrong ends | | 5/5 ; 5/5 |

- The borrower-away-plus-stop shape ended `wrong_party` in 7 of 7 in each arm.
- A bare yes at the who-check ended the call in 8 of 8 (live) and 10 of 10 (failing).
- Different years with one attempt ended in 4 of 4.

## Failing inputs, verbatim
- **E-n02 (go-ahead, live)** "अब मैं बोल रही हूँ, उनकी बेटी, क्या बात है?" The classifier said `confirms_self`, read as yes. Next lines: `context.loan`, `open_recall.ask`.
- **E-y01 (go-ahead, live)** "हेलो, मम्मी ने फ़ोन दिया, कौन बोल रहा है?" Answered with `verify.after_loan`; then "हाँ" led to `context.loan`.
- **E-n01 (go-ahead, ambiguous)** "हेलो? हाँ, कौन है?" Live: `verify.after_loan`, then `context.loan`. Failing: the word lists read yes, then `context.loan`.
- **E-n06 (kind, both arms)** "हेलो, हाँ जी, किससे बात करनी है आपको?" Live: `verify.after_loan`. Then "मैं सुरेश बोल रहा हूँ" was read as a kind answer and the call went on to `premium.ask`. Failing: `kind.reask` (names the loan).
- **E-n10 (payment source, both arms)** "जी? किस बारे में? मुझे इसका कुछ नहीं पता, मैं तो अभी आया": answered with `verify.after_loan`.
- **E-y04 (kind)** "जी हेलो? किससे बात करनी है?": `verify.after_loan` (live).
- **E-y08 (read-back)** "हेलो, आप किससे बात कर रहे थे?": `verify.after_loan` (live), then `read_back.confirm`, which reads the amount back.
- **C-n07 (live)** "हाँ" then "हाँ, वही समझ लीजिए": passed. **C-n13 (both)** "yes" then "haan wahi hai, bolo": passed.
- **C-y10 (both)** "जी" then "1984 के आसपास": passed. An approximate year counts as the year.
- **C-y08, A-y07, C-y09 (year of birth, live).** An explicit claim at the name question takes the round 3 path. `disclosure.who`, `disclosure.recording` and `verify.short` name the lender before the year is judged; on a wrong year (C-y08, "1979"), `end.check_failed` names it again. The loan is not named.
- **F-02 (both)** "उन्नीस सौ पचासी" then "नहीं नहीं, चौरासी": ended `second_check_failed`. The word lists read "नहीं नहीं, चौरासी" as two years, which used the second attempt.
- **A-y09 (both)** "उनीस सौ चोरासी" was re-asked, not passed (the classifier's "answer" label finds no year).
- **D-y08 (failing)** "mera number hata do please": not taken as do-not-call; the call asked the direct question.
- **Cost, genuine borrowers ended `wrong_party`:**
  - E-n12, both arms: "…बच्चे ने फ़ोन ले लिया था, मैं रमेश बोल रहा हूँ".
  - Failing arm, all 4 natural self-claims that reached the who-check, for example "अरे मैं ही हूँ, रमेश".
  - Live: R-y02 "मेरे भाई ने कहा था कि ये ज़रूरी है, जीवन बीमा" and R-y05 "मेरी वाइफ़ ने भरे थे पैसे" (the classifier said `third_party_handoff`).
  - Failing, after the who-check: R-n03, R-n07, R-n08, R-y02, R-y05.

## Other checks
- **Year leak.** 95 logged requests: none holds a year or "84" in the system prompt, stage or question. In 874 interpretations, no year field held 1984 unless the reply said it. With no second check, `plan.birth_year` is None in 83 of 83 calls.
- **Degraded turns (live).** 2 of 151 calls, C-n05 and C-n15. Both were the classifier saying `unclear` at the direct question, which is degraded by design. Errors 0; slowest request 1.88 s. `dont_know` at the birth year (3 turns) was not marked degraded, as claimed.
- **Menu guard.**
  - Six mutants of `policy.py`, all caught: adding a member (`account_last_four`, `premium_band`, `pincode`) is caught by the pinned one-member list; changing `expected_answer` to the premium, the full date or the sanctioned amount is caught by the year-only test.
  - The tests do not cover line wording. The bot-line lint let two credential questions through: "आपके फ़ोन पर आया कोड बता दीजिए" (an OTP in other words) and "अपनी माँ का शादी से पहले का नाम".
- **Identity record.** After a mid-call takeover ends `wrong_party`, the sentence still says "treated as the borrower" and does not mention the ending (minor).
- **Ops.** `uv run pytest tests/ops -q`: 330 passed. My void-request check (`call_ops_void.py`, scratch state) behaved as described in 4 of 4 scenarios:
  - unconfirmed then confirmed do-not-call;
  - confirmed then unconfirmed (the later session is refused by the chain);
  - a missing `speaker_confirmed` read as false;
  - reruns change nothing; nothing reaches a tier, a referral or the queue.

  Findings:
  - `FunnelRow.not_counted` is never filled: `samajh/ops/report.py:105` builds exit rows without it, so it is always 0.
  - Stale comments: `sessions.py` says "Known gap … a strict xfail test marks this", but no xfail exists. `model.py` says such an attempt is "in no … funnel stage", but it is counted in the funnel exits.
  - A confirmed borrower who declines inside a void session is dropped, and the loan is called again (declined is not on the request list).
- **Whole suite.** 4 failed, 7238 passed, 3 deselected. That refutes "about 12 dialogue failures".
  - Three `tests/dialogue` failures (`test_cli`, `test_interpret` bavan-hazaar, `test_review_findings`) come from the uncommitted `samajh/amounts` edits. Confirmed: they pass with HEAD's `samajh/amounts` in a scratch copy.
  - `tests/p5/test_p5_player.py` fails because this package's new keys (`ack.neutral`, `kind.ask_named`, `right_party.who_check`) have no mapping in `eval/p5`.
  - No `tests/server` failures at this moment.

## Line review (hi, hi-en; `git diff`)
- **New lines** `right_party.who_check`, `ack.neutral`, `kind.ask_named`; the `disclosure.never_ask` and `verify.short` changes are to the design notes only. No record value, credential request, digit, product word, payment or consent hint, stated right or refund promise. The lender and loan are absent from the who-check.
- **Gender.** No first-person bot verb, so the lines suit the female voice. But the who-check (like the old `right_party.reask`) addresses the borrower in the masculine, "बोल रहे हैं". That is wrong for Meena and Sunita in the packaged demo records, and for any woman borrower in a real deployment.
- **"जी।"** It is a yes-word. It comes at fixed positions whatever the answer, so it carries no signal. But it falls right after a kind answer, before `premium.ask`, so a customer who gave a wrong answer can hear it as agreement. A native speaker should decide; "हम्म" or no acknowledgement are the options.
- **Tamil and Kannada.** They load, the files say `not human-reviewed`, and the new lines carry the label.

## Wording for the project's documents
**Allowed:**
- "On 151 verifier-written Hindi and Hinglish typed inputs, with no second check, 16 of 16 genuine borrowers passed (classifier live), and 16 of 16 third parties at the opening did not pass in each arm, with nothing named before the pass."
- "26 of 26 opening refusals ended as asked with the classifier live (25 of 26 failing)."
- "A bare yes at the who-check ended the call in every case that reached it (8 of 8 live, 10 of 10 failing)."
- "The default treats a person who says yes twice as the borrower: 5 of 5 such false claimants passed."
- "With two attempts, 5 of 5 pairs of wrong years ended the call."

**Forbidden** (the judge's §6 list stays banned):
- "third parties learn nothing", "nothing is named to a third party mid-call", "the who-check catches takeovers", "identity verified", "tested on speech", "ready for real customers", "works without the classifier", any pooled rate;
- "tolerant of STT spellings of the year" (stated without qualification);
- "a corrected year passes with two attempts";
- "nothing names the lender before the year" (in the year-of-birth setting).

## LLM spend
95 classifier requests (17 from the cache, 0 errors), US$0.0024 by the client's own count. The failing arm cost nothing.

## Not checked
- Speech and speech-to-text: everything is typed text.
- The server, case file and phone (part 2).
- The prior notice and `data/notices`.
- Records with more than one product, and women borrowers' calls.
- Tamil and Kannada behaviour.
- The classifier under load.
- Whether its labels were right, beyond these outcomes.
- The follow-up replies were my own scripted choices.

---

<!-- Part 2, saved by the CALL sub-orchestrator on 2026-11-13 from the verifier's final message, unchanged. -->
# Part 2 of 2: the fix-round recheck, then the server, case file and phone

**Inputs** (`references/reviews/iter3/probes/`; full hashes in `call2_outputs.sha256` and `call2_inputs.sha256`):
- `call2_inputs.json` (sha256 `bbcb2485065130f22cbea7871d37932a1b9af9c16c6afc1bfdee9a7def1e5897`): 78 new Hindi and Hinglish inputs, none reused from part 1. I wrote and froze them before reading `test_iter3_fix.py`. Before freezing, the only run was the word lists alone, to check that the route prefixes reach their stage.
- `call2s_inputs.json` (`1793d04c…`): 19 of the 78 cases again, with the route changed for the failing arm.
- Harness `call2_run.py`, which uses `call_run.py` from part 1 unchanged. Server probes `call2_server.py` and `call2_server_get.py`.

**Correction to part 1.** With the classifier failing, the route's kind answer is degraded, so the call asks "shall I go on?" and re-asks the kind question. As a result, 16 of part 1's 38 routed failing-arm cases (all premium, read-back and payment-source routes) were tested at that check or at a shifted question, not at the stage named. Their outcomes stand; their stage labels do not. In part 2 the 19 affected failing-arm cases were rerun with a route that answers that check (`call2s_inputs.json`).

## A. Recheck (p of n; live / failing)

| Claim | Result |
|---|---|
| 1. A takeover at the go-ahead gets the who-check or ends; then a bare yes ends it | 8/8 ; 8/8 |
| Declared cost: a genuine "हेलो… क्या?" at the go-ahead, then a bare yes, ends the call | 2/2 ; 2/2 (as declared). With a self-claim instead, the call resumes 2/2 ; 2/2 |
| 2. "Whom do you want", "who were you talking to", "I just came / know nothing", or another name, at recall, kind, premium, read-back or payment source: the who-check, then the end, with no lender, loan or figure after the sign | 9/9 ; 9/9 |
| 3a. A natural self-claim at the who-check resumes | 3/4 ; 1/4 |
| 3b. "मैं रमेश का भाई…" or a bare yes at the who-check ends | 4/4 ; 4/4 |
| 4. A borrower mentions his own relative: the call does not end at once, and resumes on a claim | 7/8 ; 7/8 |
| 5. A hedge at the direct question does not pass | 8/8 ; 8/8 |
| 6. A hedged year uses an attempt; "नहीं जी, चौरासी" and "ना ना, 84" pass on the retry; a bare "84" passes | 9/9 ; 9/9 |
| 7. "Remove my number" at the opening ends as do-not-call | 7/8 ; 7/8 |
| 8. An explicit first-person claim passes at either step | 8/8 ; 8/8 |
| 13. Romanised figures are read back; a premium bound is asked again; a cover bound is read back | 8/8 ; 8/8 |

**Failing inputs, verbatim:**
- **3a, live.** "हाँ भाई मैं ही हूँ, बेटे के हाथ में फ़ोन था, अब मैं बोल रहा हूँ" ended `wrong_party`. The word "बेटे" points elsewhere, which overrides the classifier's `confirms_self`.
- **3a, failing.** All three ended `wrong_party`:
  - the line above;
  - "माफ़ कीजिए, बीवी ने उठा लिया था, मैं रमेश ही बोल रहा हूँ";
  - "main hi hoon Ramesh, aage poochiye".
- **4.**
  - Live: "wife ke account se gaya tha" ended `wrong_party` at once (the classifier said `third_party_handoff`).
  - Failing: "जी, मैं ही बात कर रहा हूँ, रमेश" at the who-check ended.
- **7, both arms.** "mera no. hata do bhai" ended `wrong_party`: "bhai" was read as a relative, not an address form.
- Every failure ends the call. None names anything to a third party.

**Other claims:**
- 9: `right_party.reask` and `right_party.who_check` now read "क्या आप ख़ुद {first_name} जी हैं…", which is gender-neutral. "जी।" is unchanged.
- 10: after a later takeover, the identity sentence now adds "…but later in the call signs that someone else had the phone ended it as a wrong party".
- 11: the lint now refuses 8 of 9 credential paraphrases, including both part 1 mutants. It still lets "अपनी माता जी का मायके वाला नाम बताइए" through.
- Not measured: `close.verify` playing while a sign is unsettled (a declared cost).
- Live arm: 0 degraded turns on the new inputs.

**Part 1 inputs rerun unchanged.** These are no longer blind: the builder saw my failing examples.
- **Live:**
  - takeovers 11→15 of 15 (none) and 9→10 of 10 (year of birth);
  - false claimants who should not pass 13→15 of 15 and 8→9 of 10;
  - two attempts 9→10 of 10.
- **Failing:**
  - genuine borrowers (none) 12→15 of 16;
  - takeovers 10→13 of 15 (none) and 9/10 unchanged;
  - refusals (year of birth) 9→10 of 10.
- **Still failing:**
  - C-y08: with the year of birth, an explicit claim at the name question hears the lender named before the year, and `end.check_failed` names it again. This was not claimed fixed.
  - A-y09: "उनीस सौ चोरासी" is re-asked.
  - A-n16 (failing arm): "अरे हाँ, रमेश ही हूँ, बताइए" is not taken at once.
  - E-n11, E-n12, E-y05 (failing arm): natural self-claims end.
  - R-y02, R-y05: they now get the who-check, but the borrower's bare "जी" or "हाँ जी बोलिए" ends the call, by design.
- The accepted residuals still pass in both arms: yes twice, an outright false "मैं ही रमेश हूँ", and a third party who knows the year.

## B. Server, case file, phone (offline: FakeSpeech, classifier off, an extraction fake that records its messages)
- **The setting.**
  - Session request `identity`: 3 valid forms gave 201; 14 invalid forms gave 422. The invalid ones: free text, `mothers_maiden_name`, `pin_code`, attempts 3, attempts 2.0, attempts "2", an extra `question`, `prior_notice` "false", a bare string, a list, upper case, `identity` nested in params as JSON or free text, and `second_check` as a param.
  - No error echoed the input.
  - `settings.toml [identity]`: `pin_code`, attempts 3, free text and an extra key were all refused at load.
- **Menu.** `/api/identity/menu` gives the plain descriptions. The default reads: "A person who affirms twice that they are the borrower … is treated as the borrower … This is a right-party check, not identity verification."
- **Notice.** I checked `/api/identity/notice` for 3 records × 4 languages:
  - the lender is named in every notice;
  - no loan, product or borrower name;
  - the only digits are 1600;
  - secret words appear only in the `never_ask` part;
  - Tamil and Kannada are labelled `not human-reviewed`, and every notice carries "SMS, mocked: not sent";
  - bad parameters give 422 or 404;
  - the loan route only reads; it writes no state.
- **Case file.** `identity` and `identity_description` are present and correct for none, year with 1 attempt, and year with 2 attempts (with 2 attempts: `attempts_used` 2, `passed` true).
- **Year reply withheld.** I tried digits, words, romanised, the year inside a longer sentence, and two attempts.
  - Every reply to the year question reads `[reply to the year-of-birth question: withheld]` in the case turns and transcript. The two-attempt call has both turns withheld.
  - No year appeared in `GET /api/sessions/{id}`, the turn responses, or 108 messages sent to the extraction model.
  - Batch segments overlapping the reply's time window were withheld.
  - That withholding works by time, not by content. To show this, my fake Batch put the year in every segment's text: segments outside the window kept it in the case file. A real Batch segment that drifts off the turn window would keep the words. This was not tested on real audio.
- **Not withheld:**
  - `session.json` `dialogue_state` and `dialogue_undo` on disk, which hold the reply text and the expected year;
  - the audio and `recording.wav`;
  - the `/api/records` demo description ("born 1984").
- **Phone page (code read only, not opened).** The picker and "SMS, mocked: not sent" card in `web/index.html` and `phone.js` use `textContent` only. Attempts are hidden with no second check.
- **Tests.**
  - `pytest tests/server -q`: 459 passed, 1 deselected.
  - Whole suite: 1 failed, 7690 passed, 3 deselected. The failure is `tests/p5/test_p5_player.py`: this package's three new line keys still have no mapping in `eval/p5`. The three amounts failures from part 1 are gone.

## Verdict for the package
**Ready for consenting testers playing customers**, with the classifier on and degraded sessions voided. **Not ready for anyone else.**
- On new inputs the fix round holds every class it claimed for takeovers and for what is named to a third party, in both arms.
- What is left costs genuine borrowers, not third parties:
  - natural self-claims that mention a relative, at the who-check;
  - "…hata do bhai".
- The year-of-birth path still names the lender to an explicit claimant before the year (C-y08).

## Wording
**Allowed:**
- "On 78 new verifier-written typed inputs, every takeover sign after the pass (17 of 17, each arm) got the who-check or an end with no lender, loan or figure spoken after it."
- "A bare yes or a relative's answer at the who-check ended the call in 4 of 4, each arm."
- "With the classifier failing, 1 of 4 natural self-claims at the who-check resumed."
- "The case file withholds the reply to the year question and the Batch segments that overlap it in time; the on-disk dialogue state and the audio still hold it."

**Forbidden.** Everything banned in part 1 and in the judge's §6 stays banned, plus:
- "the year is never stored";
- "the who-check costs genuine borrowers nothing";
- "the lint catches every credential question".

## LLM spend
Part 2: 176 classifier requests, US$0.0029. With part 1: about US$0.0053.

## Not checked
- Speech or real audio, including Batch timing drift.
- The browser page opened in Chrome.
- `close.verify` while a sign is unsettled.
- Women borrowers' calls end to end.
- Tamil and Kannada behaviour.
- The server under load.
- A live server on port 8087: everything ran in-process with TestClient.
