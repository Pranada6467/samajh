# Verification of P2 fix round 2 (the call dialogue)

Independent verifier; commit 993edf4; no Gnani calls; new files only `probes/p2_r2_*`. **Model-typed text, not speech.** Appendix A: full report; B: wording read.

## Verdict: ready with conditions, for consenting testers playing customers

The two wording violations (§5) are spoken only to confirmed borrowers: category unchanged, conditions 5-6 added (before P4/P5).

1. Opening cuts off borrowers: live, 28 of 45 re-asks override a `confirms_self` label (first-person guard); a plain "हाँ" after the re-ask ends 45 of 45.
2. Go-ahead: a classifier "answer" falls through to the word lists' end (`_READS_AS[go_ahead]` has no `answer`).
3. Callback time: any reply ends the call.
4. "हाँ भाई बोलो" ends as `wrong_party` in every arm.
5. Fix the two violating lines; rerun tests.
6. Make the server `stub` dialogue unreachable (asks loan amount and instalment, no identity check; selectable by session request, `app.py` 1017).
7. Keep the classifier on (down: 10 of 17 whole calls end at the opening); void sessions with degraded turns.

Re-verify 1-6 on fresh inputs.

**For anyone else, not ready:** mid-call takeover with the classifier down continues with the third party (14 of 14); false claim plus right year passes (two guesses); an unconfirmed speaker can set `do_not_call`, `human_requested` or `call_back_later`; no human has spoken to it.

**Inputs:** 266 cases, 17 calls, written first (13 duplicates flagged). **Arms:** rules; live; failing; failturn (tested turns only); slow.

## 1. Third parties (n = 66: 42 opening, 10 year, 14 mid-call)

| | rules | live | failing | failturn |
|---|---|---|---|---|
| Opening: loan, lender or value named | 0 of 42 | 0 of 42 | 0 of 42 | 0 of 42 |
| Year: loan / lender again | 0 / 1 of 10 | 0 / 0 | 0 / 1 | 0 / 1 |
| Mid-call: went on, loan + lender again | 14 of 14 | 1 of 14 | 14 of 14 | 14 of 14 |

No record value spoken in any arm.

**False claims (n = 14):** live, 14 of 14 pass the name question and hear the lender three times; 5 of 14 pass the year: "1983" then "1984"; "1984"; "84"; "1984 ya 85"; "1984 है ना? सही है?". Two tries, identical re-ask. Inferred: relatives know the year, so it stops strangers, not family.

## 2. Refusals (n = 64: 16 opening, 16 go-ahead, 9 year, 23 mid-call)

| Spoken, n = 53 | rules | live | failing | failturn |
|---|---|---|---|---|
| Went on (next + same) | 9+11 | 0+3 | 6+11 | 0+11 |
| Wrong outcome | 26 | 8 | 25 | 24 |
| "Shall I go on?" | 0 | 0 | 4 | 10 |

Silence: `no_response` 6 of 6, every arm. Live wrong outcomes include "बच्चे को स्कूल से लाना है, अभी नहीं हो पाएगा" → `declined`; "जो भी है लिख के भेज दो" → `wrong_party`; "तुम लोग चोर हो, सब फ्रॉड है" → go-ahead asked again. Rest: Appendix A §2.

## 3. Genuine borrowers (64 opening, 16 year)

| | rules | live | failing / failturn |
|---|---|---|---|
| Passed / re-asked / ended | 2 / 61 / 1 | 17 / 45 / 2 | 2 / 61 / 1 |
| Re-ask, "हाँ हाँ, मैं ही हूँ": passes | 61 of 61 | 45 of 45 | 61 of 61 |
| Re-ask, "हाँ": `not_confirmed` | 61 of 61 | 45 of 45 | 61 of 61 |
| Year in ordinary words passed | 12 of 16 | 16 of 16 | 12 of 16 |

Live, "हाँ, रमेश जी से हो रही है।" is re-asked; then "हाँ जी, बोलिए" → `not_confirmed`; "हाँ जी, रमेश ही बोल रहा है" → `not_confirmed`; "हाँ, मैं ही बोल रहा हूँ" → passes.

## 4. Cooperative replies with refusal words (n = 42: 2 opening, 12 go-ahead, 2 year, 26 mid-call)

| | rules | live | failing | failturn |
|---|---|---|---|---|
| Call ended | 11 | 3 (+4 asked "when?") | 11 | 11 |
| "Shall I go on?" | 0 | 0 | 11 | 19 |

Live, classifier said "answer": "बंद मत कीजिए, बोलिए" → `declined`; "phone mat kaatna, haan pucho" → `do_not_call`. "अभी बिज़ी था, अब बोलो" → "आपको कब कॉल करें?" → "अभी बोलिए, अभी फ़्री हूँ" → `call_back_later`.

## 5. Bot lines (Appendix B)

**Violations, 2 of 69, hi and hi-en:**
- `teach_back.intro_nth`: "अब हमारे रिकॉर्ड में लोन के साथ जो {ordinal} चीज़ है, उसके बारे में कुछ छोटे सवाल हैं।"
- `cancel_window.reask`: "मतलब, क्या बताया गया था कि उसे कैंसल करा सकते हैं, और कब तक?"

**Borderline, 9:** `provider_choice.ask`/`.reask`, `consent.ask`/`.reask`, `read_back.cover_confirm`, `cover.say_again`, `open_recall.ask`, `disclosure.rights`, `end.human`. Tamil/Kannada load (69 keys, `not human-reviewed`), not read.

**Confirmed by my runs:** 14 of 14 live read-backs repeat the customer's figure; `cancel_window.reask` spoken 2 times to confirmed borrowers; unconfirmed openers set `do_not_call` 2, `human_requested` 1, `call_back_later` 4-5 times; the stub. **Carried:** `teach_back.intro_nth` (unreached with one product).

## 6. Whole calls (17 per arm)

| | live | rules | failing |
|---|---|---|---|
| Completed | 12 | 5 | 5 |
| Correctly ended | 4 | 2 | 2 |
| `not_confirmed` at opening | 1 | 10 | 10 |

No loops. "शायद कुछ बीमा जैसा था, ठीक से याद नहीं" → "took nothing" in every arm. Classifier (live, uncached, n = 275): median 0.771 s, p95 1.731 s, 4 over 2.5 s; full calls median 8.17 s (5 calls); 9-12 of 15-21 turns; slow arm cut at 2.507 s max (18 turns).

## 7. Tests and mutants

974 of 974 passed (0 failed, 0 skipped, 73.3 s). Mutants on a scratch copy: 10 of 12 killed; both survivors (opening default) change no outcome on 120 opening inputs (inferred redundant).

## Builder's claims

| Claim | Result |
|---|---|
| Loan to third parties 0/25 | Reproduced opening/year (0 of 52); not mid-call (14 of 14) |
| Refusals next question 15/4/2 of 25 | Live reproduced (0 of 53); failing not (17 of 53) |
| Non-refusals ended 1/0/1 | Not reproduced: 11, 3 (+4), 11 of 42 |
| No "main hi" means cut off | Reproduced, wider |
| Median 0.78 s, ~8 s/call, 2.5 s bound, false claim passes, 974 pass | Reproduced |
| p95 2.00 s; 17 of 17 mutants | Not reproduced (1.73 s); not checked |

## Wording

**May use:** "On 52 verifier-written third-party replies at the opening and year question, the loan was named to none, in all four arms (text, not speech)." "Every read-back repeats the customer's own figure." "Live, 3 of 53 written refusals were asked again."

**May not use:** "third parties learn nothing"; "no bot line reveals a record value"; "no bot line states a right"; "identity verified"; "ready for real customers"; "tested on speech"; any pooled rate.

## Not checked; inferred

Not checked: Tamil/Kannada, speech, server HTTP, two-reading amounts, multi-product records. Inferred: who knows a birth year; mutant equivalence.

Spend: 462 classifier calls, US$0.00985 (client).

Rerun: `uv run python references/reviews/iter2/probes/p2_r2_run.py groups|calls <arm>` (writes timestamped copies).

---

## Note from the sub-orchestrator (not part of either verifier's report)

- The report above is the dynamic verifier's final message, unchanged: an Opus-high subagent that wrote none of the code. It is its own cut of a longer final version to two pages; it was told to change no number, verdict or condition in the cut. Appendix A is its first full report, unchanged, written before it had seen the wording read (so its section 5 is a placeholder and its verdict lists four conditions, not seven). Appendix B is the second Opus-high verifier's wording read, unchanged. Only the heading levels of the appendices were lowered.
- The verifier stated that none of its runs was still going when it wrote the final report and that no number changed.
- One spot-check by the sub-orchestrator, rules only, through `start`/`step` with `tests/dialogue/fixtures/record_gold_loan.json`: "हाँ, रमेश जी से हो रही है।" got `right_party.reask`; then "हाँ" and "हाँ जी, बोलिए" each ended as `not_confirmed`; "हाँ हाँ, मैं ही हूँ" went on to the disclosure. This matches section 3.
- The two verifiers cite the `stub` registration at different lines of `samajh/server/app.py` (1009 and 1017). Inferred: another worker was editing that file between the two reads.

---

# Appendix A: the dynamic verifier's first full report (unchanged)

## Verification of P2 fix round 2 (the call dialogue)

Verifier: independent Opus, wrote none of the code. No Gnani calls. The only repo edits are new files `references/reviews/iter2/probes/p2_r2_*`. Code under test: 993edf4; `git status` is clean for `samajh/dialogue`, `data/prompts` and `tests/dialogue`. Date 2026-11-10. **Every input is text typed by a model. Nothing here is speech or a real caller.**

**Verdict: ready with conditions, for a line where the callers are consenting testers playing customers.** No record value reached a third party in any run. At the opening, and at the birth-year question, the loan was named to 0 of 52 third parties in every arm. With the classifier live, refusals are mostly handled. The conditions:
1. **The opening cuts off real borrowers.** With the classifier live, 45 of 64 ordinary confirmations were re-asked and 2 of 64 were ended. After a re-ask, a plain "हाँ" ended the call in 45 of 45 cases.
   - This includes the reply a real person gave on the phone today, "हाँ, रमेश जी से हो रही है।".
   - In 28 of the 45 re-asks the classifier said `confirms_self`. The first-person-word guard (`speaks_in_first_person`, `llm_fallback.py`) overrode it.
   - Fix and re-verify before P4. Briefing testers to say "मैं ही" would bias P4 and P5.
2. **Two fall-throughs end cooperative calls.**
   - At the go-ahead question, `_READS_AS` has no `answer` entry, so a classifier "answer" leaves the word lists' end reading in place. "बंद मत कीजिए, बोलिए" ended as `declined`; "phone mat kaatna, haan pucho" ended as `do_not_call`.
   - At the callback-time question, any reply ends the call. "अभी बिज़ी था, अब बोलो" is followed by "आपको कब कॉल करें?", and then "अभी बोलिए, अभी फ़्री हूँ" ends as `call_back_later`.
3. **The classifier must be on and watched.** With it down for the whole call, 10 of 17 whole calls end at the opening as `not_confirmed`, and refusals at the go-ahead and birth-year questions are asked the same question again. Treat a session with degraded turns as void.
4. **"हाँ भाई बोलो" ends as `wrong_party` in every arm.**

**For anyone other than consenting testers it is not ready:**
- When a third party takes over mid-call and the classifier is down, the bot keeps asking product questions and repeats the lender and the loan (14 of 14).
- A false claim plus the right year passes. A caller gets two year guesses per call, and live, "1984 ya 85" was accepted.
- Refusals at the opening are logged as `wrong_party`.
- Hedged mentions of a product are routed to "took nothing".
- Nobody has spoken to it.

### Inputs and arms

- **Inputs:** 266 single-point cases (`p2_r2_inputs.json`) plus 14 fresh whole-call personas and the 3 packaged ones. Written before I read `_lexicon.py`, `tests/dialogue` or the old verifier's lists.
- **Overlap:** 13 of 266 lead turns are exact duplicates of the builder's or the old verifier's strings (`p2_r2_overlap.json`). Most are minimal replies the brief asked for ("हाँ बोलिए", "जी", "जी हाँ", year forms, "hmm", two false claims). They are flagged, not dropped.
- **Records:** the gold-loan fixture with the first name varied: Ramesh in Latin and in Devanagari script, Sunita, Irfan, Gurpreet, Lakshmi. Lender "Udaharan Bank".
- **Arms:**
  - rules: word lists only.
  - live: wired like `samajh_dialogue.py` (`LlmClient.from_env(timeout=3.0, retry=1 attempt)`, `mistral-small-3.2`).
  - failing: the client raises on every turn.
  - failturn: live for the prefix turns, raising on the turns under test.
  - slow: the client sleeps 4 s; 15 cases.

### 1. Third parties (n=66: opening 42, birth year 10, mid-call 14; plus 14 false claims)

Each call was continued with "कौन बोल रहा है? किस बारे में है?", "मुझे बता दीजिए…" and "किस बैंक से हो आप?".

| Point | rules | live | failing | failturn |
|---|---|---|---|---|
| Opening: loan / lender / record value named after their reply | 0 / 0 / 0 of 42 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Birth year: loan named; lender said again | 0; 1 of 10 | 0; 0 | 0; 1 | 0; 1 |
| Mid-call: the call went on with them; loan and lender said again | 14; 14 of 14 | 1; 1 | 14; 14 loan, 11 lender | 14; 14 loan, 7 lender |

- **Mid-call:** the loan had already been named to the borrower before the takeover. When the call went on, the third party was asked `kind.ask` or `premium.ask`. `verify.after_loan` answered "who is calling?" with the lender and the loan. No record value was spoken in any arm.
- **Live mid-call leak (1 of 14):** "मेरे पति को कुछ नहीं पता, मैं बताती हूँ, मैं उनकी पत्नी हूँ" was read as "took nothing".
- **First line:** "नमस्ते, क्या आप Ramesh जी हैं?" reveals the first name only. The re-ask ("यह Ramesh जी के लिए एक ऑटोमेटेड कस्टमर केयर कॉल है") and `purpose.before_confirm` name no lender.
- **Prior verifier:** loan named to 16 of 64 (rules). Not directly comparable: their scripts were mostly at the opening and had no mid-call takeovers. My opening and birth-year set reads 0 of 52.

**False claims (n=14).**
- **Getting past the first-name question:** live, 14 of 14 passed it. With rules or a failed classifier, 7 of 14 passed; claims that carried a name were re-asked, and then "haan" ended the call.
- **What a false claimant hears before the year check:** the lender's name three times (`disclosure.who`, `disclosure.recording`, `verify.short`), that it is a computer voice, a feedback call and recorded, the never-ask line, and the year question.
- **Year check:** two tries per call. The re-ask is identical for a wrong year, "याद नहीं" and several years ("एक बार फिर, सिर्फ़ अपने जन्म का साल बताइए।"). The bot never says which year is wrong. Even so, the re-ask after a wrong guess and the loan line after the right one make a two-guess oracle.
- **Live passes:** 5 of 14 passed the check and heard the loan named: "1983" then "1984"; "1984"; "84"; "1984 ya 85"; "1984 है ना? सही है?". "1980 ya 1981" and "1982, 1983 ya 1984" were re-asked. "याद नहीं" twice, or two wrong years, ended as `second_check_failed`.
- **Inferred, not tested:** spouses, parents and siblings commonly know the borrower's year of birth, so the check stops strangers more than family.

### 2. Refusals (n=64: opening 16, go-ahead 16, birth year 9, mid-call 23)

"Went on" means the bot asked a question again. In the table it is shown as the next question + the same question again.

| Category (n) | rules: went on / wrong outcome | live | failing | failturn |
|---|---|---|---|---|
| busy (8) | 1+1 / 5 | 0+1 / 2 | 0+1 / 5 | 0+1 / 5 |
| not interested (8) | 1+0 / 2 | 0 / 0 | 1+0 / 2 | 0 / 1 |
| stop calling (7) | 2+2 / 4 | 0 / 1 | 1+2 / 4 | 0+2 / 4 |
| call later (8) | 0+1 / 1 | 0 / 0 | 0+1 / 1 | 0+1 / 1 |
| human (7) | 2+1 / 3 | 0+1 / 1 | 2+1 / 3 | 0+1 / 3 |
| writing (7) | 2+2 / 5 | 0 / 2 | 2+2 / 5 | 0+2 / 5 |
| hostile (8) | 1+4 / 6 | 0+1 / 2 | 0+4 / 5 | 0+4 / 5 |
| **spoken total (53)** | **9+11 / 26** | **0+3 / 8** | **6+11 / 25** | **0+11 / 24** |
| silent (6), 2 empty turns | `no_response` 6 of 6 in every arm | | | |

- **"Shall I go on?" lines:** 0 in rules, 0 live, 4 failing, 10 failturn.
- **Prior verifier:** 25 of 45 went on with rules and 16 of 45 with the classifier, each a single turn at a named question. That is partly comparable to my 20 of 53 and 3 of 53.
- **The 8 live wrong outcomes:**
  - "अरे अभी दुकान पे ग्राहक खड़े हैं": the year question was asked again.
  - "बच्चे को स्कूल से लाना है, अभी नहीं हो पाएगा" → `declined`.
  - "दोबारा कॉल किया तो शिकायत कर दूँगा" → `declined`.
  - "koi agent hai kya? usko line pe lo" → treated as "who is calling", then `kind.ask`.
  - "जो भी है लिख के भेज दो" (at the opening) → `wrong_party`.
  - "sms bhej do, abhi baat nahi kar sakta" → `call_back_later`.
  - "फ़ालतू का फ़ोन, दिमाग़ मत ख़राब करो" (at the opening) → `wrong_party`.
  - "तुम लोग चोर हो, सब फ्रॉड है": the go-ahead was asked again.
- **failturn pattern:** in failturn every refusal that went on (11 of 53) was asked the same question again, at the opening, go-ahead or birth-year question. Mid-call refusals got "shall I go on?", and "no" then ends as `declined`, which loses `do_not_call`, `human_requested` and `written_requested`.
- **Noise taken as an answer** (failing arm): "(background TV noise)" at `kind.ask` was taken as the answer and the next question was asked. Live, "उम्म" in reply to the disengaged check led to the "took nothing" follow-up.

### 3. Genuine borrowers at the opening (n=64) and at the year question (n=16)

| | rules | live | failing / failturn |
|---|---|---|---|
| Passed at once | 2 | 17 | 2 |
| Re-asked once | 61 | 45 | 61 |
| Ended (`wrong_party`) | 1 | 2 | 1 |
| After a re-ask, "हाँ हाँ, मैं ही हूँ" | passed 61 of 61 | 45 of 45 | 61 of 61 |
| After a re-ask, plain "हाँ" | `not_confirmed` 61 of 61 | 45 of 45 | 61 of 61 |
| Year said in an ordinary way | 12 passed, 4 re-asked | 16 passed | 12 passed, 4 re-asked |

- **Live re-asks (45):** 13 plain acknowledgements (by design), 28 classifier `confirms_self` labels overridden by the guard, 2 `unclear`, 2 timeouts.
- **Overridden examples:** "हाँ, रमेश जी से हो रही है।" (with both scripts of the record name, and the same pattern for Sunita, Irfan, Gurpreet and Lakshmi), "रमेश", "हाँ जी, हम रमेश बोल रहे हैं", "ji Irfan bol raha", "haanji, Gurpreet bol rahi aan".
- **The phone pattern end to end** (`p2_r2_extras`): "हाँ, रमेश जी से हो रही है।" followed by "हाँ जी, बोलिए" ends as `not_confirmed`. Followed by "हाँ जी, रमेश ही बोल रहा है", it also ends.
- **Ended live:** "हाँ भाई बोलो" and "हाँ जी रमेश जी से बात हो रही है आपकी" (the latter labelled `third_party_handoff`).
- **Year:** with the classifier failing, "mera 1984 hai" said twice ends as `second_check_failed`.
- **Bookkeeping:** turns overridden by the guard are logged in `degraded_turns` as if the classifier had failed.

### 4. Cooperative replies with refusal-like words (n=42: opening 2, go-ahead 12, birth year 2, mid-call 26)

| | rules | live | failing | failturn |
|---|---|---|---|---|
| Call ended | 11 | 3, plus 4 asked "आपको कब कॉल करें?" | 11 | 11 |
| Got "shall I go on?" | 0 | 0 | 11 | 19 |

- **The 4 callback asks end the call on any reply:** checked on 2 of them.
- **Live ends:** "बंद मत कीजिए, बोलिए", "phone mat kaatna, haan pucho", and "मैं किसी इंसान से बात नहीं करना चाहता, आप ही पूछो, वो बीमा है" (settled by the word lists, so the classifier was never asked).
- **Ended with rules or a failed classifier:**
  - "नहीं नहीं, बोलिए, मैं ही हूँ" → `wrong_party`.
  - "अभी बिज़ी था, अब बोलो" → `wrong_party`.
  - "koi dikkat nahi, pucho" → `declined`.
  - "नहीं कोई बात नहीं, पूछ लीजिए" → `declined`.
- **Every case:** in `p2_r2_groups_*.jsonl`.

### 5. Bot lines (wording read)

*[Placeholder for the second verifier's section.]* Seen in my runs:
- No digit appears in any bot line.
- OTP, PIN and password appear only in `disclosure.never_ask` and `verify.*`.
- `features.ask` ("अगर आप उसमें लगे पैसे वापस चाहें, तो क्या होगा?") asks about money back but promises nothing. Flagged for the wording read.

### 6. Whole calls (17 personas per arm)

- **Personas:** the packaged `hero`, `informed` and `third-party` (`tests/fixtures/server/calls/*/call.json` with `samajh/server/records/`), and W01–W14.
- **Stale packaged scripts:** they have no reply for `payment_frequency.ask` (both) or `read_back.cover_confirm` (`informed`). I filled neutral answers and noted it; the P1 fixtures need re-voicing.

| Outcome | live | rules | failing |
|---|---|---|---|
| Completed | 12 | 5 | 5 |
| Correctly ended (third party, mid-call refusal, mid-call takeover, language switch) | 4 | 2 (third party, language) | 2 |
| `not_confirmed` at the opening | 1 (W11, the phone pattern) | 10 | 10 |

- **Loops and dead ends:** none. No line was said more than twice; 1 to 21 customer turns per call.
- **W04 (hedged), every arm:** "शायद कुछ बीमा जैसा था, ठीक से याद नहीं" went to "took nothing", and no product question was asked.
- **Classifier time (live, first run):**
  - Per uncached classifier call (n=275 across all live runs): median 0.771 s, p95 1.731 s, max 3.684 s; 4 of 275 went past 2.5 s.
  - Per full-length completed call with no cache hits (5 calls): 6.72, 7.74, 8.17, 8.67, 10.18 s added; median 8.17 s. The classifier was consulted on 9 to 12 of 15 to 21 customer turns.
  - Cache hits: 19 of 116 classifier calls in the whole-call run.
- **Slow arm:** 18 turns waited and were cut off at 2.501 to 2.507 s. 14 of 15 paths matched the failing arm. The 15th differs only because the slow run predates a fix to my prefix.

### 7. Tests and mutants

- `uv run pytest tests/dialogue -q`: 974 collected, 974 passed, 0 failed, 0 skipped, 73.3 s.
- **Mutants:** 12, run on a scratch copy whose own baseline passes 974 of 974.
  - **Killed (10):** classifier made secondary again, first-person guard removed, plain decline falls through, `do_not_call` dropped, `written_requested` dropped, the "shall I go on?" after a failure removed, the 2.5 s bound removed, the weak-stop-signal guard removed, the callback-time ask removed, the mid-call hand-off end removed.
  - **Survived (2):** a failed classifier at the first-name question keeps the word lists' yes; `_unjudged` no longer downgrades a yes at identity. On my 120 opening inputs these mutants change no outcome, so the guard may be redundant. Inferred, not proven.

### Builder's claims

| Claim | Result |
|---|---|
| Third parties told about the loan: 0 of 25 in every arm | **Reproduced at the opening and birth-year questions** (0 of 52). **Not reproduced mid-call:** 14 of 14 with rules or a failed classifier, 1 of 14 live |
| Refusals given the next question: 15, 4 and 2 of 25 | **Live reproduced** (0 of 53 next, 3 went on). **Failing not reproduced:** 17 of 53 went on with the classifier down all call, 11 of 53 when it fails on that turn only, and few "shall I go on?" lines |
| Non-refusals ended: 1, 0 and 1 of 25 | **Not reproduced:** 11, 3 (+4 callback asks) and 11 of 42 |
| "A borrower who never says 'main hi' is now cut off" | **Reproduced, and wider:** first-person verb forms and named self-reference are also re-asked, and a plain second "हाँ" ends 45 of 45 |
| Median 0.78 s; about 8 s per call; classifier on 10 of 16 turns | **Reproduced:** 0.771 s; median 8.17 s; 9 to 12 of 15 to 21 turns |
| p95 2.00 s | **Not reproduced:** 1.731 s, lower |
| The turn stops waiting at 2.5 s; no exception leaves `step` | **Reproduced** |
| A false claim plus the right year passes | **Reproduced**, and it also passes with two years in one turn |
| 974 passed | **Reproduced** |
| 17 of 17 mutants caught | **Not checked** (their script); mine: 10 of 12 killed |

### Wording

**May use:** "On 52 verifier-written third-party replies at the opening and the birth-year question, the loan was named to none, in all four arms (text, not speech)." "With the classifier live, 3 of 53 written refusals got a question again (0 got the next question), and silence ended as `no_response` in 6 of 6." "The classifier adds a median of about 8 s per full call (5 calls)."

**May not use:** "third parties learn nothing" (mid-call takeovers with the classifier down: 14 of 14). "Ready for real customers". "Refusals handled" without the arm. "Verified on human speech". Any pooled rate across arms or categories. "Identity verified": a two-guess year check is not verification.

### Not checked, and how to rerun

- **Not checked:** Tamil and Kannada; speech or STT; the server's HTTP path; two-reading amount behaviour; read-back loops on figures; records with more than one product; the wording read.
- **Inferred:** who knows a year of birth; that the surviving mutants are equivalent.
- **LLM spend:** 462 classifier invocations through the client live, plus 135 cache hits in failturn's prefixes. 275 went out uncached and 322 were cache hits. The client reported US$0.00985.
- **Probe files:** everything is in `references/reviews/iter2/probes/`. Scripts: `p2_r2_run.py`, `p2_r2_summary.py`, `p2_r2_extras.py`, `p2_r2_mutate.py`, `p2_r2_overlap.py`, and the input builders. Data: the inputs, personas, `groups_*`, `calls_*`, `extras_*`, `slow`, the timestamped latency files, and `mutate.json`.
- **Rerun:** `uv run python references/reviews/iter2/probes/p2_r2_run.py groups|calls rules|live|failing|failturn`, `… slow`, then `p2_r2_summary.py`.
  - A rerun never overwrites: it writes timestamped copies, and live reruns are cache hits.
  - Run `p2_r2_mutate.py <dir>` only on a copy that contains `references/pilots/P2-lines-for-review.md`.

---

# Appendix B: the wording read in full (second verifier, unchanged)

### 5. Bot lines (wording read)

**Result:** 2 of 69 lines break a binding rule in `hi.toml`, and the same 2 of 69 in `hi-en.toml`. 9 of 69 more are borderline in each file. Each file has 69 templates, not the 63 that CLAUDE.md states (round 2 added 6). Both files have the same key set (`load_prompts` enforces it), and I found no difference in meaning that matters between them. They differ only in wording: `premium.reask` is "how much did it cost" in hi and "what was its amount" in hi-en; `verify.before_loan` is "after we get the year" in hi and "after the year is confirmed" in hi-en. `references/pilots/P2-lines-for-review.md` matches all 69 current lines in both languages (checked by script).

I looked for:
- record values revealed or hinted (kind, premium, payment source, cover, term, cancel window, consent, provider choice), including through leading or yes/no wording, presupposition, example lists, deduction wording and consent wording;
- rights stated and promises made;
- digits, and number words that stand for record values;
- requests for credentials;
- product words in English, Devanagari and synonyms (बीमा, पॉलिसी, किस्त, जमा, कवर).

Found: no digits, no product words, no credential request, no money-back promise.

| File | Key | Verbatim (hi; hi-en has the same meaning) | English | Rule | Why |
|---|---|---|---|---|---|
| both | `teach_back.intro_nth` | अब हमारे रिकॉर्ड में लोन के साथ जो {ordinal} चीज़ है, उसके बारे में कुछ छोटे सवाल हैं। | "Now some questions about the {first/second} thing on our record with the loan." | **Violation**: reveals a record value | It tells the customer the record holds a first, then a second, product. My scratch run: the customer recalled one thing, and the bot then said "दूसरी चीज़ … हमारे record में". The existence of a product the customer did not recall is what open recall measures. This is my judgment: the product count is not in CLAUDE.md's list in brackets. |
| both | `cancel_window.reask` | मतलब, क्या बताया गया था कि उसे कैंसल करा सकते हैं, और कब तक? | "Were you told you *can cancel it, and until when*?" | **Violation**: states a right / hints the cancel window | The listener hears "you can cancel". "कब तक" assumes a deadline exists. The line's own design note says "still states no right". |
| both | `provider_choice.ask` / `.reask` | …कि यह आप कहीं और से भी ले सकते हैं, या नहीं? / क्या किसी ने कहा था कि यह आप किसी दूसरी जगह से भी ले सकते हैं? | "…that you can get this elsewhere too?" | Borderline: right embedded in a question | The right sits inside a "were you told" frame. The re-ask is a one-sided yes/no question, so it pulls toward "yes". |
| both | `consent.ask` / `.reask` | …वो हाँ आपने किस तरह दी थी? / आपसे किस चीज़ के लिए हाँ ली गई… | "how did you give that yes?" / "what was your yes taken for?" | Borderline: assumes consent | Both assume a "yes" was given, and "किन-किन चीज़ों" (which things) assumes more than one. They do not suggest *how*. The fixture record has `consent: null`. |
| both | `read_back.cover_confirm`, `cover.say_again` | तो उससे {amount_words} रुपये तक मिलता है। / …कितने तक का मिलता है? | "you get *up to* X" | Borderline: the read-back adds framing | "तक" (up to) turns the customer's figure into a ceiling. That is insurance-cover framing the customer may not have used. |
| both | `open_recall.ask` | …अगर हाँ, तो क्या, और कितने का? | "…if yes, what, and for how much?" | Borderline (weak) | It assumes the extra item had a price. Softened by "if yes". |
| both | `disclosure.rights` | रुकना हो या किसी इंसान से बात करनी हो, तो कभी भी बोल दीजिए। | "say any time if you want to stop or talk to a human" | Literal reading only | It states a right about the call, not the product. The design requires it; I judge it acceptable. |
| both | `end.human` | हमारी टीम का कोई व्यक्ति आपसे संपर्क करेगा। | "someone from our team will contact you" | Borderline: an unbacked promise | A stranger can trigger it before identity. I did not check whether ops acts on it. |

**Said before identity is confirmed.** There are two gates: G1 is the first-person claim, G2 is the birth year. The loan is first named in `context.loan`, after G2.

| Stage | Lines | What a stranger learns |
|---|---|---|
| Before G1 | `right_party.ask`, `right_party.reask`, `purpose.before_confirm` (on "who is this?"), `stop_check.decline`, `stop_check.human`, `callback.when`, `end.third_party`, `end.declined`, `end.human`, `end.call_back`, `end.language`, `end.no_response`, `end.do_not_call`, `end.written` | The first name, in ask, reask and third-party. Reask: "an automated *customer care* call for X", i.e. X is someone's customer. No lender, no loan. A third party can also trigger do-not-call, written-request, human and call-back records for the borrower (inferred from `machine.py` 780-799; a matter for the dynamic test). |
| After G1, before G2 | `disclosure.who`, `disclosure.not_sales`, `disclosure.recording`, `disclosure.go_ahead`, `disclosure.reask`, `verify.before_loan`, `disclosure.never_ask`, `verify.short`, `second_check.ask`, `second_check.reask`, `end.neutral`, `end.check_failed`, plus the lines above | The **lender name** is in who, recording, disclosure.reask, verify.before_loan (twice), verify.short and check_failed. These say the borrower is that lender's customer. `never_ask` (OTP, PIN, account number) hints at a financial relationship. "Loan" is never said. If a lender's name itself means lending (for example a gold-loan NBFC), the name alone tells a stranger there is a loan (inferred). Naming the lender after G1 is a documented design choice (P2-contract §1). |

**Where the read-back figure comes from: confirmed.** It can only come from the customer's speech.
- `_read_back_line` takes the figure from `AtReadBack.amount_inr`/`low` (`machine.py` 402-415).
- `AtReadBack` is built only in `_read_back_at` (639-647), from `_figure(heard/other)` (625-632), and in `_carry_forward` (657-675). `_carry_forward` uses `recall_figure`, which is set from the customer's recall turn (825-826).
- `RuleInterpreter` takes figures from `parse_amount(text)` on the customer turn only (`interpret.py` 242-266). The LLM classifier returns a label only.
- `CallPlan` (86-92) keeps only loan_id, first name, birth year and product ids. The birth year is compared (918) and never spoken.
- `render` and `load_prompts` refuse any slot a line does not declare (`prompts.py` 136-141, 167-171).

Scratch run (record premium 52,000):
- customer said "तीस हज़ार": the bot read back तीस हज़ार;
- the two readings disagreed (30k vs 13k): `say_again`, then 30k;
- a figure given in recall ("बीस हज़ार का"): read back 20k;
- "दो सौ करोड़": no read-back, the question was re-asked.

**Strings built in code.** `machine.py`, `prompts.py` and `__main__.py` contain none. The only text assembled in code is the range "<low> <range_word> <high>" (`machine.py` 411-415), and `range_word` comes from the toml.

Outside the package, `samajh/server/dialogue.py` 104-115 has an unlinted stub with hard-coded Hindi:
- It opens with "आपने कितने रुपये का लोन लिया था? आपकी हर महीने की किस्त कितनी है?" ("How big was your loan? What is your monthly instalment?"), with no identity check.
- It echoes "मैंने सुना: …" ("I heard: …").
- It is registered in the live server (`app.py` 1009), and a session request can select it with `dialogue: "stub"` (`app.py` 121, 459).

**Lint gaps.** The lint checks two things:
- any Unicode digit;
- whole-word or prefix matches against nine ban lists: findings, refunds, regulator, product words, rights, payment source, consent method, secrets, sales and offers.

In the keys allowed to deny a banned word, one denial word *anywhere* in the line is enough. It cannot see synonyms or inflections it does not list, number words, presupposition, leading structure, or how far a denial reaches. These pass `lint_line` (tested):
- `premium.ask` "क्या आपने उसकी सालाना किस्त भरी थी?" ("did you pay its yearly instalment?")
- `payment_source.ask` "क्या वो पैसे लोन की रकम में से ही काटे गए थे?" ("was it cut from the loan amount?")
- `cancel_window.ask` "आप तीस दिन के अंदर इसे कैंसल करा सकते हैं, पता था?" ("you can cancel within thirty days")
- `features.ask` "घबराइए मत, आपका पूरा पैसा लौट आएगा।" ("don't worry, all your money will come back")
- `second_check.ask` "…अपनी पैदाइश की पूरी तारीख़ बता दीजिए।" ("tell me your full date of birth")
- `verify.before_loan` "पक्का करने के लिए अपना ओ-टी-पी बताइए, घबराइए नहीं।" ("tell me your OTP, don't worry"; passes because "नहीं" appears)
- `disclosure.not_sales` "यह सेल्स कॉल है, फ़ीडबैक नहीं।" ("this *is* a sales call", inverted)

None of the current lines is among these.

**Tamil and Kannada.** Both load through `load_prompts`, have the same 69 keys as hi, and keep `review = "not human-reviewed"`. I did not read their wording.

**Stale text in the repo.** The toml header comments and `P2-lines-for-review.md` still mention `{amount_digits}`. The `read_back.confirm` design note says "words and digits", but the code speaks words only. CLAUDE.md says 63 templates; there are 69.

**Fluency** (a model's opinion, for the user's wording review):
1. `purpose.before_confirm` has no verb and says "बात…बात" twice; it is unclear on a phone line.
2. In `disclosure.who`, "कंप्यूटर से चलने वाली आवाज़" sounds clunky.
3. `verify.before_loan` is about 40 words in three sentences and names the lender twice: long for speech.
4. In `open_recall.reask`, "कोई और चीज़ भी हुई थी" ("did something else *happen*") is vague.
5. In `payment_source.reask`, "भरा गया" goes with premium or instalment ("premium भरना") and may suggest an instalment.
6. In `teach_back.intro_nth`, "चीज़" for a financial product sounds odd.
7. In `features.ask`, "उसमें लगे पैसे" ("money put into it") sounds like an investment.
8. The demo records use Latin-script names, so the Hindi line becomes "क्या आप Ramesh जी हैं?". I did not check how Timbre voices that.

**Not checked:** the Tamil and Kannada wording; how the lines sound when voiced; the full DESIGN.md text behind each cited paragraph; reachability of every line in a live call (left to the dynamic verifier); whether ops acts on `end.human` or `do_not_call`. No repo files were changed and no Gnani or LLM calls were made.
