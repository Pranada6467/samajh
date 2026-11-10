# Samajh product review, 2026-11-10 (independent, read-only)

Reviewer built none of it. No Gnani calls, no server started, nothing edited. "Mic call" below is today's only human-voice session with a case file, `.samajh/sessions/20261110T112446-f7770ec63c07` (Hinglish, 141 s, JSON read only).

## 1. Gains that fit tonight, ranked

**1. Pre-build the bot's lines: most of the dead air in the mic call was Timbre being made on the turn.**
- Today: 14 of 26 bot lines in the mic call were cache misses (0.6 to 2.1 s each). End of speech to bot audio: median 3.4 s, 5 of 16 turns over 4 s; the turn after the birth year waited 6.7 s (5.35 s of it TTS for three lines).
- Change: when P2's lines are final, run `uv run python -m samajh.server.prompts build --lang hi --lang hi-en`, then check a replay shows every fixed line as `cache_hit`.
- Files: none. Effort: 10 min, about 13 estimated credits (P1's figure for 101 lines). Risk: must run when no call is live; rerun after any line change. Re-verification: one replay. Wording review: no.

**2. A confused borrower is sent down the "took nothing" branch at open recall.**
- Today, typed by me (Hindi, same with and without `--llm`): "पता नहीं क्या था, कुछ बावन हज़ार कटे थे" gets "अच्छा। लोन लेते समय किसी ने आपसे लोन के अलावा किसी और चीज़ की बात की थी?". So do "पता नहीं, बैंक वाले ने कुछ एफ़डी जैसा करवाया था सिक्योरिटी के लिए" and "हाँ कुछ तो लिया था, नाम याद नहीं" (3 of 6 recall replies I tried; a 4th, naming nothing, went there rightly). At that follow-up, "बोला था कि ये करवाना पड़ेगा, वरना लोन नहीं मिलेगा" went straight to the consent question: no product question was asked (1 of 4 follow-up replies).
- Why it matters: this is the customer the product exists for. Inferred, not run: with the kind never asked, the case ends `incomplete`, not `refer`.
- Change: in `_on_recall` and `_on_follow_up`, a "don't know" or "no" goes to the nothing branch only when the reply holds no figure and no thing done or taken; otherwise start the product questions.
- Files: `samajh/dialogue/machine.py:929-945`, `interpret.py`, `tests/dialogue`. Effort: 45 to 60 min. Risk: P2's lane, being edited now; no leak, the branch still depends only on the customer's words. Re-verification: yes, fresh inputs. Wording review: no.

**3. Show the two Prisma readings where a viewer can see them.**
- Today: on the phone they sit inside a collapsed latency box as "Reading by prisma-v2.5" (`web/phone.js:604-610`). The reviewer case page shows no reading at all. The data is good: in today's sessions v3.0 wrote "52,000" and v2.5 "52 हज़ार।" or "52 थाउज़ंड", agreed.
- Change: on a figure turn, one visible line under the customer's bubble: "Prisma v3.0: 52,000 · Prisma v2.5: 52 हज़ार · same amount, read back" (or "differ, asked again"). Add the same line to the premium and cover rows of the case page. A one-line model strip in the line monitor (Prisma v3.0 and v2.5, Timbre v3.0, Prisma Batch): the page names Timbre nowhere.
- Files: `web/phone.js`, `phone.css`; `samajh/server/app.py` if the turn reply lacks the agreed flag (not checked); `web/review/review.js`, `samajh/ops/views.py`. Effort: phone 30 to 40 min, case page 45 min. Risk: low; `phone.js` is being edited by P1b. Re-verification: browser check. Wording review: no.

**4. One prepared clip that makes the finding happen in a call.**
- Today: the 40 of 68 result is in reports only. No demo record has an amount that skips a group, so the re-ask after a disagreement is never seen.
- Change: a fourth demo record (for example a large loan, premium ₹1,00,300) and a prepared customer clip taken from the held-out set's listed failures. v3.0 and v2.5 differ, the bot asks again, then reads back. Label it on screen as a clip chosen because it is known to fail, not a rate.
- Files: `samajh/server/records/`, `prepare.py` persona, the line from gain 3. Effort: 45 to 60 min, a few credits. Risk: 23 of the 68 were read right, so pick a sentence already seen to fail; an odd-looking premium. Re-verification: one replay. Wording review: no.

**5. The summary says things about the customer that the call never asked.**
- Today: a one-turn wrong-party call (`…103036-51c4162ca18a`) carries the line "Customer did not know, or gave a different answer about: the cover; the term; the cancellation window; naming the product unprompted." A call hung up at 42 s (`…111501-cfb03ade882d`) is tier `refer` with "Call outcome: in progress", on the record's missing consent alone (quote null).
- Change: when every item in a group is a gap, say "The call did not get to: …" (`samajh/rules/summary.py:280`). Mark record-only lines "from the lender's record; no customer statement". Show "hung up" for an unfinished call.
- Files: `summary.py`, `web/phone.js:918`, `web/review/review.js`. Effort: 25 min. Risk: tests pin titles; P3a's lane. Re-verification: light. Wording review: no.

**6. The half-yearly report opens with caveats; the first result is about 3,000 px down.**
- Today (committed render, known stale): title, eight "what this report is not" bullets, mechanism, a nine-row draws table, then reach. The queue page has four number tiles; the report has none.
- Change: a tile strip at the top (sold, sampled, completed within 30 days, referred, understanding gap, most common gap), with the synthetic label on the strip; caveats stay directly below.
- Files: `web/review/review.js` (near line 892), `review.css`. Effort: 30 min. Risk: low; P3b is re-rendering these pages. Re-verification: banned-word probe. Wording review: no.

**7. Two opening lines.**
- Today: at "क्या दो-तीन minute बात करें?", asking "kis baare mein hai?" gets "किस बारे में है, यह birth year confirm होने के बाद बताएँगे", before any birth year has been asked. Before the year question the bot also says "शक हो तो फ़ोन रखकर … ख़ुद पूछ सकते हैं", which is said again at the close and on request.
- Change: at the go-ahead step say "पहचान पक्की होने के बाद"; drop the "शक हो तो" line from the default path (about 5 s by word count).
- Files: `data/prompts/hi.toml`, `hi-en.toml`, the line list in `machine.py`. Effort: 15 min plus rebuilt clips. Risk: opening tests are pinned. Re-verification: tests. Wording review: yes.

**8. Ten questions in a row with no acknowledgement, and "वो क्या है? अपने शब्दों में बताइए।" straight after the customer said "एक बीमा लिया था".**
- Change: a neutral "जी।" clip before every second or third question, chosen by position, never by the answer; a kind-question variant for a customer who already named something ("जो आपने बताया, उसे थोड़ा समझाइए: वो क्या है और किस काम आता है?").
- Files: prompts, `machine.py`. Effort: 30 to 40 min. Risk: "ठीक है" after a wrong answer can sound like agreement, so use "जी" only; no-leak test must pass. Re-verification: no-leak test. Wording review: yes.

**9. No way from the finished call to the reviewer's page.**
- Today: the phone ends on a list and "Case file (JSON)". The strongest page (record beside quote, "Play the recording from 1:27") needs `ops ingest` in a terminal first.
- Change: an "Open the reviewer's page" link once the case is ready. Inferred: needs a route that ingests one session; may overlap P1b and P3b's ingest fixes, so check before building.
- Effort: 30 to 45 min. Risk: ingest is the weak part per `verify-P3b-r2`. Re-verification: yes.

## 2. Direction

1. **`refer` mixes a record check with what the customer said.** A missing consent on the record refers a call the customer left after 42 s. That check needs no call. Referral counts then partly measure the lender's database (the text-path "8 of 16 informed customers with a record fault referred" is the same effect). Report record faults as their own count.
2. **The first question arrives at about 55 s.** In the mic call the first substantive answer starts at 54.7 s of 141 s: name, four opening lines, go-ahead, three second-check lines, year, two context lines. The birth-year step costs roughly 15 to 20 s and P2's own report says a false claim plus the right year passes. Whether it earns its time is undecided.
3. **Silence after each answer is designed in.** Even with every line cached, an open question waits 1.1 s (detection), about 0.35 s (STT), then the classifier (0.6 to 2.5 s in the mic call, on 9 of 16 turns). Nothing fills it. State the measured figure; do not show "1.1 s" from the yes/no turns.
4. **The Gnani finding is in reports, not the product.** No page says why amounts are read twice. For Jugaad Genius that is the whole case (gains 3 and 4).
5. **Mixed Vibes is not targeted** (`DESIGN.md` §10 names Real Deal, Demo Day Drop, Jugaad Genius), though Hinglish is a product language and the mic call is code-mixed ("amount तो नहीं मिलता but हर महीने मैं एक amount डालता हूँ इसका"). Inferred from the one-line award description only.

## 3. Looked at, and not

- **Read:** CLAUDE.md, README, DESIGN §5 to §10, the coordinator handoff, `judge.md`, `verify-P3b-r2.md`, P1 and P2 reports, RESEARCH §1; `verify-P3a-r2.md` verdict and table only.
- **Played:** about 35 text calls or openings (hi, hi-en): cooperative, confused, third party, refuser, spoken-year forms; 15 of them with `--llm` (small OpenRouter spend through the play command, not measured). Romanised Hindi failed in places ("chaurasi"); I treat that as my typing, since Prisma returned Devanagari and digits in today's sessions.
- **Session data:** three of today's seven case files and one session log, JSON only.
- **Pages:** source of `web/` and `web/review/`; committed screenshots (phone case panel, queue, case, report), which the verifier says are stale.
- **Not done:** no page opened in a browser, no audio heard, no tier run on my typed calls, nothing timed by me, the bot's voice not judged, Tamil and Kannada not looked at. Line-length judgements are from text, not sound.
