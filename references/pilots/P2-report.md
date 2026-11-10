# P2 report: call v2, a call real people can finish (round 2)

2026-11-10, P2 builder. Edited `samajh/dialogue/`, `data/prompts/`, `tests/dialogue/`; wrote this file, `P2-lines-for-review.md` (regenerated; round-2 lines marked) and §5–§6 of `P2-contract.md`. No Gnani calls. OpenRouter: 0.0043 USD (the first live classifier run, 129 uncached calls; reruns were cache hits). Everything is synthetic text, not speech; no fluent human has read a line; Tamil and Kannada are not human-reviewed.

## 1. Round 2: what changed, and why it is structural

The iteration-2 verifier showed that the word lists do not generalise. This round adds no reviewer sentence to any list. The changes are to who decides, and to the defaults when nobody can.

1. **Asymmetric defaults at the opening.** Only an explicit first-person claim confirms ("हाँ जी, मैं ही बोल रहा हूँ", "speaking"). An acknowledgement ("हाँ बोलिए", "जी", "hello", "namaste") gets the re-ask "क्या आप ख़ुद {name} जी बोल रहे हैं?" once, and a second non-claim ends as `not_confirmed`. A reply with a name, a title or any other word goes to the classifier (an LLM). With no classifier, or one that fails, times out or says `unclear`, nobody is confirmed. A classifier `confirms_self` also needs a first-person word in the reply. At the year step, a year among other words (`loose_year`) passes only when the classifier reads it as the speaker's own. Relation, title and third-person words end the call at any opening step. "साहब मीटिंग में हैं" is a third party: a busy signal without "I" at the opening means someone else.
2. **The classifier as primary judge.** It is asked about every go-ahead reply and every reading the rules do not settle. Its labels are confirms_self, wrong_person, third_party_handoff, yes, no, answer, dont_know, asks_repeat, who_or_why, refuse, stop, human_request, call_back, remove_number, written_request, off_topic and unclear, and every one is honoured. New outcomes: `do_not_call` and `written_requested`; a hand-off ends as `wrong_party`. When the classifier fails later in the call, the bot asks "क्या मैं आगे बढ़ूँ?" once per call instead of taking the reply as an answer. No exception from a client or an interpreter leaves `step`. Two guards cover cases where the classifier and the rules disagree: a weak stop signal stays one question unless the classifier reads an answer or an end, and a go-ahead word against an end label asks once.
3. **"What is this about?"** Before a claim: `purpose.before_confirm` (no lender, no loan), then the re-ask. After a claim: `verify.*` (purpose and how to check), then the pending question. Asking twice does not end the call, and at open recall it is never taken as the answer.
4. **Disengaged customers.** Two unusable replies, or three "I don't know"s in a row, get one "क्या मैं आगे पूछूँ, या यहीं रोक दूँ?" per call. A single figure given in open recall is not asked for again: it is read back after the kind question and recorded in `carried_forward`. **Dependency:** the extractor must accept the recall turn as the premium quote for these, or the premium reads as a gap.
5. **Amounts.** The cover question follows the premium's two-reading rule (`cover.say_again`). An ambiguous figure is never read back; the bot asks once more. Read-backs say the figure in words only.
6. **Product count.** Tested over records with 0, 1, 2 and 3 products: a customer who has named nothing hears identical lines until the follow-up is answered. **What a listener can infer, and when:** nothing about the count before they name something or answer the follow-up. After that, `teach_back.intro` means one product, `teach_back.intro_nth` ("हमारे रिकॉर्ड में … पहली चीज़") means two or more, and going straight to the consent question means none. With 2 or more products, the lines are identical until the first product's questions end.
7. **Wording.** The verifier's eight changes are adopted (the computer-voice line, the recording/notice line, "आपने हाल ही में {lender} से जो लोन लिया", "और वो हाँ आपने किस तरह दी थी?", "बस हाँ या ना कह दीजिए", "हमारी टीम के किसी व्यक्ति से", the short third-party ending, `verify.short` at the year question). The opening is still 19.6 s by word count at an assumed 2.5 words/s (test-pinned). An informed one-product Hindi call takes **150.0 s**, exactly at the limit.

## 2. Evidence

`uv run pytest tests/dialogue -q` → `974 passed`; `uv run ruff check samajh/dialogue tests/dialogue` → `All checks passed!`. Mutations (`tests/dialogue/probes/p2_round2_mutate.py`, on a scratch copy): **17 of 17 caught**. They cover the opening defaults, the classifier labels and failures, exception escape, "who/why", the disengaged check, carry-forward, cover say-again, the product count and the limits. The verifier's own `p2_mutate.py` anchors on code that changed, so most of its mutations no longer apply.

**Fresh set** (`tests/dialogue/probes/p2_round2_fresh.py`, hi and hi-en, written after the code and run once before any further change; `p2_round2_measure.py rules|llm|down`):

| n = 25 each | rules only | classifier live | classifier failing |
|---|---|---|---|
| Third parties told about the loan | 0 | 0 | 0 |
| Lender named to a third party | 1 (a false "हाँ, मैं ही हूँ") | 1 | 1 |
| Refusals that got the next question | 15 | 4 | 2 (15 got "shall I go on?") |
| Non-refusals that ended the call | 1 | 0 | 1 |

After that run I made three generic fixes: a first-person guard on `confirms_self`, weak stop signals kept, and a go-on word that overrides an end label. The rerun is contaminated by having seen that run: live refusals 2/25, everything else unchanged.

**The verifier's scripts** (`p2_third_party.py` and `p2_refusals.py`, run unchanged on scratch copies so its saved outputs were not overwritten):

| | Before round 2 | Rules only | Classifier live |
|---|---|---|---|
| Third parties told about the loan (n=47) | 11 | 1 | 1 |
| Lender named to them | 20 | 1 | 1 |
| Refusals that got the next question (n=45) | 25 | 24 | 4 |
| Non-refusals that ended the call (n=48) | 1 | 1 | 1 (plus 3 asked "shall I go on?") |

The remaining third party ("हाँ मैं ही हूँ", "हाँ", "1984") is a false claim plus the right year; no rule can catch it.

**Classifier latency** (mistral-small-3.2, 2.5 s limit per turn): uncached calls n = 129, median 0.78 s, p95 2.00 s. The slowest call took 6.1 s, but the turn stops waiting at 2.5 s. It is invoked on **10 of 16** customer turns of an ordinary informed call (the go-ahead and every free-text answer), so it adds roughly 8 s of silence per call at the median.

**Held-out turn set, rules only:** fold 0 180/209 and fold 1 150/199 (were 189 and 155). The loss is by design: acknowledgements and named claims at the first name are now re-asked. Part of it is not mine: P3a's `parse_amount` now marks "Maine 50,000 rupees pay kiya" as malformed.

## 3. Transcripts (inputs in `tests/dialogue/fixtures/p2_calls/`, record `record_gold_loan.json`, lender "Udaharan Bank")

**Third party (hi), 9.6 s.** B: नमस्ते, क्या आप Ramesh जी हैं? / C: हाँ जी, मैं उनकी पत्नी बोल रही हूँ / B: हम Ramesh जी से बाद में बात कर लेंगे। धन्यवाद। `[wrong_party]`

**Took nothing (hi), 88.4 s.** C: हाँ जी, मैं ही बोल रहा हूँ → four opening lines → C: हाँ → B: हम आपसे कभी ओ-टी-पी, पिन, पासवर्ड या खाता नंबर नहीं माँगेंगे। शक हो तो फ़ोन रखकर Udaharan Bank कस्टमर केयर पर ख़ुद पूछ सकते हैं। पक्का करने के लिए, अपने जन्म का साल बता दीजिए। सिर्फ़ साल। / C: 1984 → loan line, stop-any-time line, recall / C: कुछ नहीं लिया, बस लोन लिया था / B: अच्छा। लोन लेते समय किसी ने आपसे लोन के अलावा किसी और चीज़ की बात की थी? / C: नहीं, ऐसी कोई बात नहीं हुई / B: (consent) / C: बस लोन के कागज़ों पर हाँ की थी / close `[completed]`

**Ordinary informed (hi), 150.0 s.** The recall reply holds "बावन हज़ार", so after "वो क्या है?" the bot reads it back ("तो आपने उसके लिए बावन हज़ार रुपये दिए। सही है?") instead of asking it again. Provider choice is skipped ("मेरी मर्ज़ी से लिया"). The cover is read back ("तो उससे पाँच लाख रुपये तक मिलता है। सही है?") `[completed, 0 unresolved]`.

**Misled (hi-en), 196.0 s.** C: haan ji boliye / B: re-ask / C: kaun bol raha hai? kis baare mein hai ye? / B: यह एक customer care feedback call है; बाक़ी बात सही person से बात confirm होने के बाद। (re-ask) / C: haan ji, main hi bol raha hoon → opening … all ten questions answered `[completed]`. The earlier script, which never says "main hi", now ends as `not_confirmed`: that is the price of the asymmetric default.

## 4. Gaps

- No independent review of round 2.
- The fresh set is one writer's sentences (mine). The fix pass after its first run contaminates the rerun.
- The classifier adds about 8 s of median silence per call. The `down` column counts "shall I go on?" per probe; in a real call it is asked once.
- A false first-person claim plus the right year still passes.
- Carry-forward needs an extractor change (see §1.4).
- Tamil and Kannada got only the new keys; their openings are long.
- `tests/server` could not be collected earlier because `samajh/ops` was mid-edit by another package.

## 5. Document lines made stale

- `DESIGN.md` §5 steps 1-3, 5, 6 and 8 (lines 79-86): the opening, who is believed, the recall wording, the ten questions, the read-back position and digits.
- `DESIGN.md` line 104 ("51 lines", now 69), line 124 ("eight outcomes", now thirteen), lines 113-122 (the position table), lines 126-136 (limits, third parties, second reading, "LLM fallback … off by default … never ends a call"), lines 143, 371 and 414 ("671 tests", now 974).
- `CLAUDE.md` line 59 (the disclosure size; "the LLM fallback client a short timeout"), line 60 ("671", "never ends a call"), line 61 ("51 lines each"; the `verify.*` lines also deny OTP/PIN).
- `references/pilots/W9-dialogue-report.md` is superseded for behaviour.

## 6. Round 3: what changed (numbers to be added by the coordinator)

- Ordinary confirmations ("हाँ जी", "बोलिए", "हाँ, <name> जी से हो रही है", "yes") no longer end as
  `not_confirmed`: they go straight to the birth-year question, and the lender is named only after the
  year passes. The strong first-person path is unchanged. Contract §7 has the order of lines.
- At open recall and its follow-up, a "don't know" or "nothing" reading that still names a figure, a thing
  or something done goes to the product questions, not the nothing branch.
- At a read-back, repeating the same figure confirms it.
- On a two-reading turn, a stop signal or third party in either reading is acted on.
- The classifier is asked less (plain go-ahead yes/no; free answers that speak of the sale), and can be
  started early (`begin`, `prefetch`); the server still has to call `prefetch`.
- One line changed (coordinator's decision): `verify.before_loan` in hi and hi-en no longer promises the
  topic "after the birth year" but "after identity is confirmed"; `P2-lines-for-review.md` regenerated.
- Tests: `tests/dialogue/test_p2_round3.py`, plus the round-2 tests updated to the new behaviour.
- Wave 2 (verifier conditions): the substance skip needs no risk cue; address forms and a confirmation
  with a who-question confirm; a go-on word turns a refusal phrase into a question, never an end; "now"
  at the call-back question resumes the call; the birth year gets one attempt; `speaker_confirmed`;
  a possible takeover with no classifier judgment gets a "who is speaking?" check; recall denials that
  name nothing go to the follow-up; `cancel_window.reask` and `teach_back.intro_nth` reworded (hi,
  hi-en), and the first product is introduced the same way whatever the count.
  Tests: `tests/dialogue/test_p2_round3_wave2.py`.
- Wave 3: dates of birth, guesses end the year check, cooperative go-ahead replies and "now, go on" at the
  call-back question continue, more takeover frames (a classifier cannot clear one), romanised recall
  evidence, any-length yes at the re-ask. Tests: `tests/dialogue/test_p2_round3_wave3.py`.
- Wave 4: romanised Hindi number words are read as years ("unnees sau chaurasi"). Contract §7, wave 4.
  Tests: `tests/dialogue/test_p2_round3_wave4.py`.
- Wave 5 (after a fresh opening set, `tests/dialogue/probes/p2_round3_openings_fresh2.py`, 36 genuine and
  36 third-party openings written blind): the right birth year is taken as the speaker's own unless the
  reply points at someone else, negates, asks or guesses (hi and hi-en; Tamil and Kannada keep the older
  allow rule). Before: 31 of 36 genuine borrowers passed both checks with the word lists alone and with
  the classifier failing, 36 of 36 with the classifier live. Refused before, passing now:
  "उन्नीस सौ चौरासी, और क्या", "अरे उन्नीस सौ चौरासी", "चौरासी वाला साल", "arre yaar, nineteen eighty four",
  and at the go-ahead "हाँ, पर ज़्यादा लंबा मत करना" (a yes with a keep-it-short request). From the
  earlier year set (`year2`, 30 genuine and 14 guesses): "Ya, 1984.", "Mera DOB 15-06-1984 hai.",
  "मेरा जन्म पंद्रह तारीख़ जून चौरासी को हुआ।" and "Nineteen eighty four, main abhi office mein hoon toh
  jaldi kijiye." now pass, and the guess "अंदाज़े से चौरासी।" now ends the check. A wrong year still gets
  one attempt. Tests: `tests/dialogue/test_p2_round3_wave5.py`.
- Builder counts after wave 5 (2026-11-10, text not speech; an independent verifier follows):
  `uv run pytest tests/dialogue -q` 1,783 passed. Fresh opening set, each of the three arms (word lists
  alone; classifier live, replayed from the response cache, 57 requests and none new; classifier
  failing): 36 of 36 genuine borrowers reached the year question and passed both checks; the loan or a
  product was named to 0 of 33 third parties who did not both claim to be the borrower and give the right
  year, and to 3 of 3 who did (a false claim with the right year passes: known, section 4). With the
  classifier live the lender was named, with no loan or product word, to 5 of 5 false claimants who then
  gave a wrong year or none (the first-person path names the lender before the year).
- Known after wave 5, not fixed: with the word lists alone and with the classifier failing,
  "बंद मत कीजिए, बोलिए" and "phone mat kaatna, haan pucho" are asked "shall I go on?" and end as
  `no_go_ahead` only if the same reply is given again (live they continue), and "Nahi, I'm free, go." ends
  as `declined` (live it continues); "नहीं नहीं, अभी कर लीजिए।" and "Na, later nahi, abhi karte hain." at the call-back question end
  as `call_back_later` in every arm; "साल? वो तो याद नहीं अभी" at the year ends as `wrong_party` ("वो");
  on a two-reading turn "Mera number list se hata do." beside a figure is asked to say the figure again
  (live it ends as `do_not_call`); "office" is still a relation word outside the year question.

## 7. Round 4 (builder's report; an independent verifier follows)

Typed text, not speech. Inputs from the round 3 verifier (`references/reviews/iter2/verify-P2-r3.md`) were
used only as examples of a class; none was added to a word list. No line text changed.

1. **The who-check** (`right_party.reask` after a sign of another speaker). Root cause: the reply was read
   as an ordinary stop-check answer, where takeover cues were not computed, so a leading "हाँ" resumed the
   call. Now, in every arm: a reply that points elsewhere (a relation word that is not a form of address,
   a third-person word or possessive, an absent or "not me" cue, a denial, a takeover sign) ends as
   `wrong_party` with `end.third_party`. The call resumes only on an affirmation by a closed vocabulary
   (yes-words, first-person claim words, the borrower's first name, address forms, go-on words, fillers;
   every word must be explained), or on the classifier's `confirms_self` with a first-person word. A stop
   request ends as asked; anything else ends as `wrong_party`. Every `wrong_party` end now carries
   `speaker_confirmed` False. Known and accepted: a third party who answers with a false "हाँ" or
   "हाँ मैं ही हूँ" passes; no text rule can catch that.
2. **Takeovers with the classifier off or failing.** Root causes: the takeover frames needed "I + their +
   relation + am" ("मैं उनका भाई," without "हूँ" missed), romanised "chale" was not folded, "मुझसे बात करो" and
   a restart ("हेलो? क्या पूछ रहे थे") were no sign at all, so the turn was taken as an answer; and with a
   failed classifier, "shall I go on?" came before the takeover check. Now the word lists see two tiers of
   signs (contract §8). Any sign with no usable classifier label, or with a label that says nothing about who
   is speaking (`asks_repeat`, `who_or_why`, `off_topic`, `unclear`), gets the who-check before anything
   else is said or taken as an answer, at every answering position after the opening, including the stop
   checks and the call-back question. A strong sign keeps round 3's rule: a label can end the call but
   not clear it. The who-check has its own cap (`Limits.max_who_checks`, 2); past it the call ends as
   `wrong_party`.
3. **The birth year.** A word one edit (Devanagari code points; romanised: folded key, at least 5 letters)
   from exactly one number word is read as that word; the year must still match. Built also: a word right
   after "सौ"/"हज़ार" two edits from a number, or one edit from two numbers, makes the reply "no year" (the one
   re-ask), not 1900. Neighbours among the 306 Devanagari number words `samajh.amounts` reads (120 values):
   61 pairs of different values lie one edit apart (for example पचास/पचासी, छियासठ/छियासी, उन्नीस/उनतीस,
   चौबीस/चौतीस), 710 two apart. चौरासी has no valid word one edit away and only तिरासी two away; a slip
   from one valid year word to another (पचासी) is a different year and still fails. What a false claimant
   gains: nothing from the correction itself, which only reaches the record's year from a non-word next to
   it; and a second attempt when the first reply holds an unreadable number-like word ("उन्नीस सौ पचासि"
   is one edit from both पचासी and पचास, so it is re-asked).
4. **A refusal at the opening.** Root cause: "नहीं करनी कोई बात" matched no refusal phrase, so "नहीं" read as
   "not me". A refusal to talk is now read by structure at every stage (a no-word, a talk or listen word and
   a wanting or doing word within three words of the talk word, or a hang-up word with a no-word). At the
   first-name question and its re-ask it ends as `declined` (`do_not_call` when the words ask so), with
   `end.declined` (names nothing) and `speaker_confirmed` False. A bare "नहीं", or a refusal with a third
   party or a third-person word, stays `wrong_party`.
5. **`verify.before_loan`** plays only before the year has passed; after it, a who/why question gets
   `verify.after_loan` and the pending question. No line text changed.
6. **Residuals.** At the call-back question a no-word answers "later?" unless it negates the now ("अभी
   नहीं") and a "later" counts only when not negated, so "नहीं नहीं, अभी कर लीजिए।" and "Na, later nahi, abhi
   karte hain." resume. At the year, "वो" before "तो", a year word or a number is "that", not a person:
   "साल? वो तो याद नहीं अभी" gets the one re-ask, "वो बाहर गए हैं" still ends as `wrong_party`, and
   "अरे वो उन्नीस सौ चौरासी" (round 3's known residual) now passes.

**Evidence.** `uv run pytest tests/dialogue -q`: 2,181 passed (1,786 before; the new tests are
`tests/dialogue/test_p2_round4.py`). `uv run ruff check samajh/dialogue tests/dialogue`: all checks passed.
Round 3 tests changed: `test_p2_round3_wave3.py::test_an_account_is_not_a_takeover` ("मेरे भाई का भी वहीं लोन
है" now gets the who-check with no label or a label silent on the speaker) and
`test_p2_round3_wave2.py::test_a_product_word_with_a_risk_cue_goes_to_the_classifier` ("Insurance ki baat
mujhe phone pe nahi karni" is now a refusal; moved to its own test).

**Blind probe** (`tests/dialogue/probes/p2_round4_fresh.py`, 127 hi and hi-en inputs written before the round
4 code ran on them; setup turns by the word lists, the probe turn by the arm). First run, as expected:

| group (n) | rules | failing | live |
|---|---|---|---|
| W who-check replies: resume (11) / end (13) | 11 / 13 | 11 / 13 | 11 / 13 |
| T takeovers: who-check or end next (22) | 22 | 22 | 19 |
| Tc genuine answers: plain, no who-check (5) / ambiguous (3) | 5 / 3 | 5 / 3 | 5 / 3 |
| Y year: genuine pass (16) / other year fails (7) / slip not ended (1) | 13 / 6 / 1 | 13 / 6 / 1 | 13 / 6 / 1 |
| R opening: declined (11) / do_not_call (4) / wrong_party (7); later stages declined (3) | 9 / 4 / 7; 3 | 9 / 4 / 7; 3 | 10 / 4 / 7; 3 |
| C call-back: now (10) / later (5); year: re-ask (6) / wrong_party (3) | 10 / 5; 6 / 3 | same | same |

The probe's judge printed the 3 later-stage refusals as misses because it wanted `speaker_confirmed` False
after the year too; the outcomes were `declined` (judge fixed). Misses: years "उनीस सौ चौरासी", "unnees sau
chorasi", "उन्नसी सौ चौरासी" (two edits; re-asked once, not ended); "उन्नीस सौ पचासि" re-asked instead of
failing; "नहीं भाई, अभी बात नहीं करनी, फ़ोन रखो" ended `wrong_party` ("भाई"); "रहने दो, नहीं करनी कोई बात" got
"shall I go on?" (rules, failing); live, three weak signs went on: "हैलो? हाँ, अब मैं बात कर रहा हूँ, क्या
चाहिए", "hello? kaun? kya baat chal rahi thi?", "hello? ye kiska phone hai? kya puch rahe ho?". After that run
(the rerun is contaminated): labels silent on the speaker no longer let a weak sign pass, the refusal
window grew from two to three words, and a relation word not covered by an address form points elsewhere at
the who-check. Rerun: T live 21 of 22 (the "अब मैं बात कर रहा हूँ" turn, labelled `answer`, still goes on);
R declined 10 of 11 in each arm; everything else unchanged. The round 3 verifier's 3 who-check replies and 5
takeovers (at two stages) end as `wrong_party` with the classifier live. Classifier: 63 new requests,
about US$0.0028 (client figures); reruns from the cache.

**Not covered.** A takeover with no lexical sign ("हाँ", "पता नहीं" from someone else), in any arm. A weak sign
the classifier labels `answer`. Relation words outside the list. Another person's name at the who-check is
caught only as an unexplained word (word lists) or by the classifier. Tamil and Kannada have no weak signs
and no near-spelling rule. A genuine borrower who mentions a relative's act ("मेरे बेटे ने फॉर्म भरा था") gets
one who-check when no classifier label decides it.

**Round 4 follow-up (item 4).** At the first-name question and its re-ask, an address form inside a structural refusal ("नहीं भाई, बात नहीं करनी", "sir nahi chahiye, phone rakho") is address when there is no possessive, no third-person word and no "हूं / बोल रहा / am" after it: the call ends `declined`. At the who-check, a leading no-word before a first-person claim ("नहीं भाई, मैं ही हूँ") is read as "no, it is me". Rerun of the blind probe (contaminated): opening refusals declined 11 of 11, do_not_call 4 of 4, wrong_party 7 of 7, later stages 3 of 3, in rules and in failing; the other groups did not change.
