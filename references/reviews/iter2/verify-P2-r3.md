# Verification of P2 round 3 (the call dialogue)

**Scope.** I am an independent verifier and wrote none of this code. Under test: the working tree's `samajh/dialogue/` and `data/prompts/hi.toml` / `hi-en.toml`, on top of 993edf4. The inputs are **typed text, not speech**: no audio, no speech-to-text, no human voice. I wrote 328 Hindi and Hinglish inputs before reading any round 3 test or earlier input set (`probes/p2_r3_inputs.json`, sha256 `580e02f3ed7956b382c1f585baca4ee99382d2dc08b37ab9a350228891fd3373`). Record: `record_gold_loan.json` (borrower born 1984, one product). Each input ran in three arms: **rules** (word lists only), **live** (the dialogue's classifier, `FALLBACK_MODEL`), and **failing** (the same classifier with a client that raises an error). Extras: 12 false-claimant calls with an adaptive flow (`p2_r3_fc_live.py`), extra calls outside the frozen set (`p2_r3_extras.py`, `p2_r3_whocheck.py`, `p2_r3_survivor.py`), and 8 mutants. No Gnani calls.

## Verdict: ready with conditions (consenting testers playing customers only)

1. **The classifier is on for every call, and a session with a degraded turn is voided.** With the classifier down, a mid-call takeover (someone else takes the phone) gets no "who is speaking?" check in 10 of 20 (rules), or only "shall I go on?" in 10 of 20 (failing). A third party who then says "हाँ" goes on to the loan questions.
2. **The who-check must not resume on a yes that comes with an admission.** "हाँ, मैं उनका बेटा, बोलो" at "क्या आप ख़ुद Ramesh जी बोल रहे हैं?" resumes the call and names the loan: 3 of 3 such replies, in both rules and failing. Not checked with the classifier live.
3. **Testers are told the birth year gets one attempt.** "उन्नीस सौ चौरसी" (one vowel sign dropped, as speech-to-text might do) ends a genuine borrower as `second_check_failed` in all three arms. Inferred: on speech, any transcription slip in the year ends the call.
4. **A refusal is not logged as a wrong party.** "नहीं करनी कोई बात, रखो" at the opening ends `wrong_party` in all three arms.
5. **Reword `verify.before_loan`** (section 5).

**For anyone else: not ready.** A false claimant who gives the right year passes (3 of 3, all arms). With the classifier live, the lender is named to 8 of 9 false claimants who then fail the year. No person has spoken to it.

## The seven old conditions (n per arm; rules / live / failing)

| # | Condition | Status | Evidence |
|---|---|---|---|
| 1 | Opening cuts off borrowers | **Held** | 0 of 40 ended in each arm (30 at the opening, 10 at the re-ask); a plain "हाँ" at the re-ask passes 10 of 10 in each arm |
| 2 | Classifier "answer" at the go-ahead falls through to an end | **Held in code** (`llm_fallback.py` turns it into a yes or asks again) | Cooperative replies still ended: 2 / 2 / 2 of 20; live, 1 more was asked "when shall we call?" |
| 3 | Any reply at the call-back question ends the call | **Held** | "now": 14 of 14 resume, each arm; a time: 4 of 4 end, each arm |
| 4 | "हाँ भाई बोलो" ends `wrong_party` | **Held** | goes to the year question and passes, each arm (1 extra input; "haan bhai bolo" from the set passes too) |
| 5 | Two lines break the wording rules | **Held** | both reworded; no rule broken on my read |
| 6 | Server `stub` selectable by a session request | **Held, by code read only** | `app.py` about line 1044 builds only `{"samajh": …}` unless a caller passes `dialogues`. Another worker may be changing this file; not tried over HTTP |
| 7 | Keep the classifier on; void degraded sessions | **Still needed** | Opening cut-offs with the classifier down are fixed (group 1 is equal in all arms); takeovers are not (group 2). Degraded test turns: 0 / 1 / 112 of 328. `sessionlog.py` has a `degraded` field; whether voiding is enforced was not checked |

## Results by group (rules / live / failing)

**G1, genuine borrowers (n = 65: 30 opening, 25 year, 10 re-ask).**
- Passed both checks: 64 / 64 / 64 of 65.
- Re-asked once at the opening: 2 / 1 / 2. No borrower was re-asked twice.
- Year asked again: 1 / 0 / 1. The input was "अरे वो उन्नीस सौ चौरासी"; this is the known "वो" residual.
- Wrongly ended: 1 / 1 / 1, "उन्नीस सौ चौरसी" (**new**).

**G2, third parties (n = 58).**

| | rules | live | failing |
|---|---|---|---|
| Opening (21) and year (5): ended `wrong_party`; anything named afterwards | 26; 0 of 26 | 26; 0 | 26; 0 |
| Takeover mid-call (20): ended at once | 0 | 20 | 0 |
| … next line: "who is speaking?" / next question / "go on?" | 10 / 10 / 0 | – | 10 / 0 / 10 |
| … loan named later (follow-ups "हाँ", "पता नहीं") | 15 of 20 | 0 of 20 | 20 of 20 |
| False claimant, wrong year (5) or guess (4): ended after one attempt | 9 of 9 | 9 | 9 |
| False claimant, right year (3): passed and heard the loan | 3 of 3 | 3 | 3 |

- Takeovers that went straight on to the next question in rules (**new**; the builder says such a turn gets a who-check): "हेलो? मैं उनका भाई, क्या पूछ रहे थे"; "ये मेरे पति का लोन है, मुझसे बात करो"; "hello main unka beta, papa chale gaye"; "haan ab main bol raha hoon, unka bhai"; "sir wo chale gaye, main unka driver". Each was tried at two stages.
- At the who-check, "मैं उनका बेटा हूँ" ends the call `wrong_party`. A yes in front of the same admission resumes the call (condition 2).

**G3, refusals, do-not-call, call-back, wants a human (n = 81).**

Single reading, 61 inputs across six stages:

| | rules | live | failing |
|---|---|---|---|
| Correct end, or "when?" for a call-back | 46 | 60 | 46 |
| Went on to the next question or repeated the same one | 10 | 0 | 4 |
| Asked "shall I go on?" | 4 | 0 | 10 |
| Ended with the wrong outcome | 1 | 1 | 1 |

- "मेरा नंबर लिस्ट से हटा दो" went on at all 6 stages in rules. This is the known two-reading residual, now seen on ordinary turns too.
- "नहीं करनी कोई बात, रखो" went on at 4 stages in rules and ended `wrong_party` at the opening in all three arms (**new**).
- Stop intent in only one of the two readings of a figure turn (10 inputs per order): in rules and failing, 8 of 8 stop intents ended correctly and 2 of 2 takeovers got the who-check, in both orders. Live, 10 of 10 per order ended correctly.

**G4, cooperative replies that contain refusal words (n = 43).**
- At the go-ahead (20), wrongly ended: 2 / 2 / 2. In rules and failing, "फोन मत काटो, सुन रहा हूँ" ended `do_not_call` and "मैं मना नहीं कर रहा" ended `declined`. Live, "mana nahi hai, bolo" and "no no, continue" ended `declined`.
- At the go-ahead, asked the same question again: 15 / 2 / 15. Live, "nahi yaar time hai, bolo" was asked "आपको कब कॉल करें?".
- These are the same family as the known "phone mat kaatna" residual, but they end the call instead of asking (**new**).
- At recall (5): went on 5 / 5 / 0 (failing asked "go on?" 5 times).

**G5, open recall (n = 41).**
- Confused borrowers (25) sent to the product questions: 22 / 22 / 19. Sent to the "nothing" follow-up 3 / 3 / 3 (**new**): "कुछ नहीं लिया पर लोन में से पैसे कम आए"; "kuch nahi liya, bas loan se paisa kam aaya"; "maloom nahi, manager ne kuch add kiya".
- Took nothing (16), sent to the nothing branch: 15 / 15 / 11. "sirf gold loan" went to the product questions in every arm (**new**).

**G6, read-back of ₹5,200 (n = 40).**
- Same figure: confirmed 9 / 9 / 9 of 10. "paanch hazaar do sau" was read back again.
- Different figure: 9 of 10 read back the customer's new figure, each arm. "nahi, baavan hazaar" got "तो सही amount कितना है?".
- Yes: 10 of 10 go on. No: 10 of 10 restate.
- Inferred: both misses are romanised number words that the amount parser does not read, outside `samajh/dialogue`.

## Wording (group 7)

Only three lines changed since 993edf4, in each of hi and hi-en. I read them as a listener would hear them.
- **`teach_back.intro_nth`, pass.** "अच्छा। लोन के साथ अगर कोई और चीज़ भी ली थी, तो अब उसके बारे में कुछ छोटे सवाल हैं।" Inferred: this line plays only when the record holds a second product, so hearing it tells the customer there is one. The number of products is not on the rule list.
- **`cancel_window.reask`, pass.** "मतलब, उसे बंद या कैंसल कराने के बारे में किसी ने कुछ बताया था? जो याद हो, बताइए।" It states no right and no time window.
- **`verify.before_loan`, fault: inaccurate, not a rule breach.** "यह {lender} कस्टमर केयर की फ़ीडबैक कॉल है; किस बारे में है, यह पहचान पक्की होने के बाद बताएँगे। …" plays at the go-ahead after the year has already passed. Inputs: "हाँ जी", "1984", "आप कौन बोल रहे हो?". At that point identity is already confirmed, so the promise is stale. At the early year question a who-asks reply gets `purpose.before_confirm` and no lender: 2 of 2.

## Tests and mutants

- `uv run pytest tests/dialogue -q`: 1,783 passed, 0 failed.
- Eight mutants ran in a scratch copy (`probes/p2_r3_mutate.py`). One test was left out because it reads `references/`, which the copy does not hold. An unmutated control passed.
- **6 of 8 killed:** year off by one; takeover check off; stop in the second reading ignored; repeated figure not confirming the read-back; "don't know" at recall sent to the nothing branch; "now" at the call-back question ignored.
- **Survivors:**
  - M2: a reply with two years is accepted when one of them matches.
  - M4: the who-check resumes even when the reply is flagged as a takeover.
  - Neither mutant changed the outcome of 5 targeted inputs. Inferred: M2 may behave the same as the original; M4's guard matters only for replies the word lists flag, and the replies in condition 2 are not flagged.

## LLM spend

- 354 classifier requests through `LlmClient`: 147 new, 207 answered from the cache. US$0.0049, as reported by the client.
- A first live run at 10 threads had 108 turns time out. Cause: the classifier's thread pool is shared by the whole process and has 4 workers (`llm_fallback.py` line 52). The rerun at 3 threads had 0 timeouts. Inferred: one server process running more than about 4 calls at once will degrade turns.

## Wording for the project's documents

**Allowed:**
- "On 328 verifier-written Hindi and Hinglish text inputs, 64 of 65 genuine borrowers passed both checks in each of three arms."
- "Third parties at the opening or the year question heard no loan, lender or value: 0 of 26, in every arm."
- "With the classifier live, 20 of 20 mid-call takeovers ended the call."
- "The birth year gets one attempt; a false claimant with the right year passes."

**Forbidden:**
- "third parties learn nothing"
- "identity verified"
- "works without the classifier"
- "every refusal is honoured"
- "tested on speech"
- "ready for real customers"
- any pooled rate

## Not checked

- Speech and speech-to-text.
- Tamil and Kannada.
- Records with more than one product (`teach_back.intro_nth` was never reached).
- The server over HTTP, `prefetch`, and voiding of degraded sessions.
- Whole calls from start to finish.
- Classifier latency (most live answers came from the cache).
- The classifier's labels on the two live go-ahead ends.
- The who-check with the classifier live.
- My follow-up "हाँ" after a takeover was my own scripted choice.
