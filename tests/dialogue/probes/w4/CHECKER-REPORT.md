<!-- Saved by the W4 orchestrator on 2026-11-14 from the independent checker's final message (phase 2), unchanged except this header. The checker wrote none of the code and wrote its banks before reading it. Banks, harness and the writer scripts it used are beside this file (`banks/`, `harness/`, `gen/`; the scripts' .env path was made repo-relative). For references/reviews/iter4/verify-W4.md if the documentation worker wants it there. -->

## W4 independent check: full report (phases 1 and 2)

**Verdict:** language switching, the negated-again fix, the deferral re-ask and keeping the year from the classifier all hold on my banks. Five faults remain for the fix round:
1. The new opening path ends calls for genuine borrowers who claim and then ask who is calling (new in W4).
2. The word "एक"/"ek" blocks the consent follow-up.
3. The kind follow-up does not fire on "what it does" replies.
4. A refusal next to a deferral is lost when the classifier is on (new in W4).
5. Open-recall replies that name a thing but forget the amount still go to the took-nothing branch.

I wrote nothing in the repo, made no Gnani calls and ran no git command that changes state.

### Inputs (frozen before any arm; I wrote them before reading any W4 code)
- **A openings:** `banks/A-openings.jsonl`, n=229, sha256 `3b527123…44dd66`. 91 borrowers (A-057 ambiguous, so 90 scored); 56 third parties, of which 7 say yes twice (`accepted_residual`); 30 refusals; 22 call-backs; 30 language requests. 72 distinct first names.
- **B half answers:** `banks/B-half-answers.jsonl`, n=72, `c6679575…6b6124`. 42 consent cases and 30 kind cases.
- **C mid-call:** `banks/C-midcall.jsonl`, n=71, `c53ce1cb…6df6c4c`. 18 deferrals, 7 real refusals, 6 mixed refusals, 18 negated-again replies, 14 forgotten amounts, 8 took-nothing replies.
- **Y birth year:** `banks/Y-birth-year.jsonl` (10) `3e1fa6d5…12e259a`, and `banks/Y2-birth-year-chatty.jsonl` (10) `812ba9c4…62ca5`. I wrote both by hand.
- **Writers:** `openai/gpt-5-mini`, `google/gemini-2.5-flash` and `anthropic/claude-haiku-4.5`, in rotation. I set gold and listed every manual edit in `gen/finalize.py`.
- **Harness:** `harness/run.py` plays the banks, `harness/score.py` scores them, `harness/show.py` prints one case, `harness/chain.py` runs the post-call chain. The after arm runs with PYTHONPATH empty; `samajh.__file__` points into the repo, and every case reached its slot. The harness treats `defer.*` as a re-ask and `consent.follow_*` / `kind.follow_what` as follow-ups. B and C reach their slot through a fixed plain prefix played on the word lists.

### Metrics (k/n; Wilson 95% for the after live arm; L = live classifier, R = word lists only)
| # | Metric | 107a908 L / R | 29e0747 L / R | **After L** | After R |
|---|---|---|---|---|---|
| 1 | False rejections, genuine borrowers | 4/90, 6/90 | 1/90, 1/90 | **4/90 = 4.4 [1.7–10.9]** | 1/90 |
| 2 | Lender or loan named, or check passed, third parties | 0/49, 0/49 | 0, 0 | **0/49 [0–7.3]** | 0/49 |
| 2b | Yes-twice residual passed (by design) | 7/7 | 7/7 | 7/7 | 7/7 |
| 3 | Refusals asked a further question | 0/30, 0/30 | 0, 0 | **0/30 [0–11.4]** | 0/30 |
| 4 | Call-backs not honoured | 0/22, 0/22 | 0, 0 | **0/22 [0–14.9]** | 0/22 |
| 5a | Language with a file not honoured (ta 5, kn 5, en 4) | 14/14, 14/14 | 14/14 | **0/14 [0–21.5]** | 0/14 |
| 5b | Language without a file, not `language_switch` + `requested_language` | 2/15, 0/15 | 2/15, 0 | **0/15 [0–20.4]** | 0/15 |
| 5c | Requests inside a yes not honoured | 10/14, 9/14 | same | **0/14** | 0/14 |
| 6 | Consent partial answers left incomplete | 15/15 | 15/15 | **1/15 = 6.7 [1.2–29.8]** | 1/15 |
| 6 | Kind partial answers left incomplete: figure only, does only, kind only | 6/6, 4/6, 6/6 | same | **0/6, 5/6, 6/6** | 0/6, 6/6, 6/6 |
| 6 | Follow-up when both halves were given (consent, kind) | 0/7, 0/6 | same | 0/7, 0/6 | 0/7, 0/6 |
| 6r | Follow-up lines that reveal a record value, digit or product word | — | — | **0** | 0 |
| 6b | Deferrals ending `declined` | 0/18 | 0/18 | **0/18** | 0/18 |
| 6b | Deferrals not getting exactly one re-ask then moving on | 13/18, 16/18 | same | **0/18 [0–17.6]** | 2/18 |
| 6b | Of those, slot left a gap after the one re-ask | 2/18 | 2/18 | 13/18 | 9/18 |
| 6b | Real refusals not ending `declined` | 0/7 | 0/7 | **0/7** | 0/7 |
| 6b | Mixed refusals not ending `declined` | 0/6, 2/6 | 0/6, 2/6 | **1/6** | 2/6 |
| 6b | Negated-again read as a call-back | 2/18 | 2/18 | **0/18** | 0/18 |
| 6b | Negated-again: same question asked again | 0/18 | 0/18 | 0/18 | 0/18 |
| 6b | turn_limit (banks B and C) | 0/72, 0/71 | same | 0/72, 0/71 | same |
| 6b | Forgotten amount sent to the took-nothing branch | 4/14 | 4/14 | **4/14 = 28.6 [11.7–54.6]** | 4/14 |
| 6b | Genuine took-nothing not sent there | 0/8 | 0/8 | 0/8 | 0/8 |
| 7 | Void calls (any degraded turn, banks A+B+C) | 1/372 | 0/372 | **4/372 = 1.1 [0.4–2.7]** | 0 |
| 8a | Lender or loan named before the right-party pass | 0/229 | 0/229 | **0/229** | 0/229 |
| 8b | Classifier requests holding the year (Y2) | 6/6 | 6/6 | **0/20** (and 0/20 in Y) | 0 |
| 8c | Y2 genuine borrowers passing the year check | 9/10, 6/10 | 9/10, 6/10 | **7/10** | 6/10 |

- **Classifier latency (after, live), uncached calls only:** 295 uncached of 366 calls; 71 were cache hits (B 28, C 26, Y2 16, A 1). Median 1.15 s, p90 1.58 s, p99 2.99 s, max 3.81 s. 3 calls took over 2.5 s; 2 were ReadTimeouts. Before (107a908, uncached n=231): median 0.74 s, p90 1.12 s. Runs used 4 cases in parallel in every arm, so absolute times are not phone latency. The opening now asks the classifier on almost every reply: bank A made 192 calls after against 151 before.
- **Post-call chain (`run_text`), 14 partial consent cases plus 6 with both halves:** tier is `refer` in all 20, before and after; the fixed prefix answers drive it, so the tier shows nothing here. Extraction of the 14 partial cases: `consent_given` stated 7 → 13; `consent_method` stated 2 → 7; both halves stated 0 → 6.

### Failing inputs, after arm, live (verbatim, grouped by cause)
**F1. A claim followed by "who is calling?" ends `wrong_party` (new in W4).** The classifier said `confirms_self` each time. The word lists pass all three after one re-ask.
- A-001 (Rajkumari): "Namaste haan main Rajkumari bol rahi hoon, kaun bol raha hai thoda bataiye"
- A-002 (Bhavesh): "हाँ Bhavesh बोल रहा हूँ, क्या बात है, कौन बोल रहा है"
- A-009 (Mohammed): "हाँ Mohammed हूँ कौन बोल रहा है"
- Cause: `machine._on_identity_judged` ends the call on `third_party_sign(...)`, and `names_another_speaker` returns True for "कौन बोल रहा है"/"kaun bol raha hai". Before W4 that sign only led to a re-ask (the `doubts_claim` path).
- Related: `turn_context` sends wrong name hints, "बात: a different first name" and "रही: a different first name", because `judge_name` returns `other` for ordinary words.

**F2. A-019 (Satyanarayana): "हाँ जी मैं सत्यनारायण ही हूँ" ends `wrong_party`.** It passed at 107a908 and fails at 29e0747 and after, live and rules. `judge_name("सत्यनारायण", "Satyanarayana")` returns `other`, so `claims_another_name` vetoes the claim. This came in with W1 and W4 did not fix it.

**F3. The word "एक" blocks the consent follow-up.** B-025: "अरे मैंने एक फॉर्म साइन किया था बस और क्या है ना अंगूठा भी लगाया था" gets no follow-up. Cause: the reading parses "एक" as the figure 1 and `halves.consent_halves` counts any figure as the "what" half.

**F4. "What it does" replies get no kind follow-up.** B-044 "arey agar mujhe kuch ho gaya na toh ye mera jo loan hai na usko bhar dega woh aisa kuch tha", B-049, B-059 "agar mujhe kuch ho gaya to loan bhar dega", B-064, B-069. Cause: `_DOES` lacks भर/bhar, चुक/chuk, clear, pay, काम आएगा. Kind-only replies get no "what does it do" follow-up because none exists: design scope, not a bug.

**F5. A refusal next to a deferral is lost when the classifier is on (new in W4).** C-031: "haan ji aapke records mein likha hoga na, matlab kuch amount tha uske saath, lekin ab mujhe aur baat karne ki zaroorat nahi hai" → `defer.reask`; "…par mujhe zyada baatein nahi karni" → `bridge.moving_on`; call `completed`. Before W4 the classifier ended this call `declined`. Cause: a deferral is settled, so the classifier is never asked; a second deferral becomes `unclear`. Word lists only: C-026 also lost (as before W4); C-002 and C-005 not read as deferrals because `_NOT_DEFERRAL` contains "main/मैं".

**F6. Forgotten amount still goes to the took-nothing branch (unchanged).** C-060 "हाँ बिमा और ek scheme ली थी कितना हुआ था याद नहीं", C-061 "हाँ इन्शुरन्स लिया था कितने का याद नहीं है मुझे", C-062 "haan insurance liya tha kitne ka yaad nahi mujhe", C-063 "हाँ Insurance लिया था कितने का याद नहीं है मुझे". The reading is `dont_know` with `names_nothing=True`.

**F7. Chatty years now fail the year check.** Y2-02 "arey saal? 1984, kyun poochh rahe ho" and Y2-08 "साल 1984, पर ये क्यों चाहिए आपको" end `second_check_failed`. `_own_year` drops a loose year unless the reply has "I" or "my". This is the price of the year never reaching a model, and it only applies when a lender turns the year check on.

### What holds (checked)
- Language: 14 of 14 requests with a file switch, with `language.switched` said in the new language. A switch at the name question asks the name question again in the new language, so the self-claim in that turn is dropped and must be said again. 15 of 15 requests without a file end with the reworded `end.language`. Probes after a switch to Tamil or Kannada (my own sentences, not human-reviewed): a wife or son ends `wrong_party` (3 of 3, live); a Tamil yes said twice passes (the same residual as in Hindi); with word lists only, a genuine Tamil borrower ends `not_confirmed`.
- Negated-again: 0 of 18 read as a call-back or as a request to repeat. Deferrals: 18 of 18 get one `defer.reask` and then move on (live); none ends `declined`.
- Follow-up lines hold no digit, record value or product word. Year: in 40 Y/Y2 classifier requests none holds "1984", "84", "चौरासी" or "eighty".

### Spend
About $0.263 in total of the $3.00 cap: writers $0.226, classifier runs about $0.022, chain $0.013, probes about $0.002.

### What I could not check
Real speech or ASR noise (all typed text); the server or browser path and end-of-speech latency (classifier timing from 4-way parallel runs); Tamil and Kannada wording; tiers in the post-call chain; the colloquial meaning of the does-only kind replies; `samajh/server` and W5 code.

### Wording for the project's documents
**Allowed**, each with the n and "synthetic typed text":
- "On 30 synthetic typed language requests, the call switched live for 14 of 14 requests for Tamil, Kannada or English, and ended with `language_switch` for 15 of 15 requests for Telugu, Marathi or Bengali."
- "With the classifier on, no customer reply to the birth-year question was sent to any model (0 of 40 classifier requests on 20 year-check calls)."
- "A negated 'again' in an answer was read as a call-back 0 of 18 times (2 of 18 before)."
- "After a deferral the call asks once more and moves on (18 of 18)."
- "A half answer to the consent question now gets one follow-up for the missing half: 14 of 15 typed cases, against 0 of 15 before."

**Forbidden:** "the year of birth reaches no model" without "at the year question", or without saying that the context still holds earlier turns; "trailing questions after a claim pass" (F1); "the kind question asks for the missing half" (F4); "a refusal is never read as a deferral" (F5); "forgotten amounts no longer take the took-nothing branch"; any false-rejection rate below 4 per 100 for the live arm; any claim that the Tamil or Kannada lines or Tamil behaviour have been reviewed; "W4 fixes Satyanarayana-type names".
