# P1b report: readings order, and the phone joined to the loan book

2026-11-10. Written by the P1b sub-orchestrator after a resume from disk (the first worker stopped at a usage limit; its edits were in the working tree, uncommitted). Builders: Opus medium. Verifiers: Opus high, separate, wrote none of the code. Round 1 verification: `references/reviews/iter2/verify-P1b.md`. Round 2 verification: section 4 below, verbatim from the verifier.

## 1. What changed

**Readings order.** `readings()` in `samajh/server/samajh_dialogue.py` is the one place that orders the two readings for `samajh.dialogue.step(state, customer_text, second_reading=...)`. The dialogue holds and reads back the first reading's figure where the two differ, and P2-contract section 5 asks for Prisma v2.5 `transcribe` first. The server now passes v2.5 first when it has text, and v3.0 first when v2.5 is missing, empty, late or failed (so a turn is never empty because v2.5 timed out). The contract and the dialogue code agree; the dialogue was not edited. The transport is unchanged: v3.0 is still the primary call and v2.5 the second, bounded at 2.5 s.

**The phone joined to the loan book.** New module `samajh/server/loanbook.py`. A session is created with `loan` (a loan id on the batch under `<state>/ops`) in place of `record`. Eligibility is checked once, at creation, with stable codes: `invalid_loan_id` and `invalid_call_date` (422, ASCII digits only), `loan_not_on_book` (404), `loan_not_drawn`, `attempts_ended`, `attempt_limit` (after `samajh.ops.model.MAX_ATTEMPTS` logged attempts), `before_draw`, `outside_window` (after day 30), `before_last_attempt`, `no_batch` (all 409), `record_and_loan` (422). The server writes the link (batch, draw, sale date, call date) into the session; a client that sends a link param is refused, on a packaged-record session too. The default call date is the draw day plus the attempts already logged, and never earlier than the day after the last attempt, so ingest can place it. `GET /api/loans` lists the drawn loans a call may be placed on; the phone's picker shows them under "Synthetic loan book" beside "Demo records". The lender name is spoken without "(synthetic)". The packaged demo records work as before.

**Case file (the contract with `samajh.ops ingest`).** `loan_id`; `record_id`; `book {batch_id, draw_id, sold_on, call_date, day_since_sale}` for a loan-book call and null otherwise; `started_at`; `customer_audio {mic, file, none}` (superseded takes not counted); per turn `source`, `readings[] {role, model, text, ok}`, `acted_on`, `readings_agreed`, `followed_by`, `degraded`; top level `degraded_turns` and `speaker_confirmed`.

**On the phone page.** Under the customer's bubble on a figure turn, and on the case card, one line with both readings and what the bot did next, built only from the server's fields. A model strip in the line monitor from `/api/health` `models` (the server's settings). A degraded turn (the classifier did not answer in time) is marked. "from an unconfirmed speaker" appears beside `do_not_call`, `human_requested` and `call_back_later` only when `speaker_confirmed` is false.

**A fourth demo record, `amount-check`.** A synthetic informed customer whose premium, "दो हज़ार बारह" (2,012), skips a place-value group. Recorded in the persona (`AMOUNT_CHECK.measured` in `samajh/server/prepare.py`): on its own 8 kHz Timbre clip, Prisma v3.0 `transcribe` wrote "2,000 रुपये रुपये दिए थे।" and v2.5 `transcribe` wrote "₹2,012 दिए थे". The text run of the call goes `premium.ask`, `premium.say_again`, `read_back.confirm`. On screen it is labelled as a clip chosen because the two models are known to write it differently: one example, not a rate.

**The stub dialogue** is no longer registered on a default server: a session request that names it gets `unknown_dialogue`, and a test pins that. It stays for tests and the in-process replay.

## 2. Files

- New: `samajh/server/loanbook.py`, `samajh/server/records/amount-check.json`, `tests/fixtures/server/calls/amount-check/` (17 clips and `call.json`), `tests/server/test_loanbook.py`, `tests/server/test_readings_fields.py`, `tests/server/test_two_readings.py`.
- Changed: `samajh/server/` `app.py`, `samajh_dialogue.py`, `casefile.py`, `sessionlog.py`, `dialogue.py`, `records.py`, `prepare.py`, `replay.py`, `__main__.py`; `web/` `phone.js`, `index.html`, `phone.css`, `api.js`; `tests/server/` `test_app.py`, `test_casefile.py`, `test_records.py`, `test_replay.py`, `test_samajh_dialogue.py`, `browser_check.mjs`.
- Not touched by P1b: `samajh/dialogue`, `data/prompts`, `samajh/ops`, `samajh/rules`, `samajh/extract`, `samajh/types.py`, `samajh/server/review_routes.py`, `web/review/` (the changes there are the P3b worker's).

## 3. Tests (builder's counts; not evidence)

`uv run pytest tests/server -q` at 20:55 IST after the resume: **375 passed, 1 deselected** (the live test). `ruff check samajh/server tests/server`: clean. `node --check` on `web/phone.js` and `web/api.js`: clean.

## 4. Verification

**Round 1** (`verify-P1b.md`, sound with conditions). On the verifier's own multi-draw batch: 65 of 70 creation and refusal cases as expected; 14 hand readings cases as claimed; a live Hindi call on loan SYN-PL-270210-0126 (draw D-2027-02-15) reached a `ready` case, `ops ingest` reported `1 session(s) on drawn loans, 0 outside the sample, 0 skipped`, and `ops report` showed it in the funnel (attempted 1 of 76; tier `incomplete`, so it was rightly not in the `refer` queue). H4 recount through the server adapter under that day's dialogue: 2 wrong figures held in 240 with v2.5 first against 16 with the old order (TTS audio, in-sample). Its conditions were then fixed: the call date strictly after the last attempt's day; link params refused on packaged-record sessions; the attempt limit; ASCII-only ids and dates; tests for the three surviving mutants; three tests stale against the committed cover read-back.

**Round 2** (after the fixes and additions; full report saved unchanged as `references/reviews/iter2/verify-P1b-r2.md`). In-process only: TestClient, fake speech, a failing LLM, the verifier's own batch of four draws. Its verdict, verbatim:

> **Verdict: sound.** All four round-1 fixes and all three round-1 mutants that had survived now hold, and my own inputs found no failures. Two small edges and one known trade-off are below; none of them blocks P1b.

What it found to hold, in its counts:

- Dates: 138 of 138 eligibility checks. Every call date the server accepts for a loan with logged attempts is after the last attempt's day; 9 such calls, including day 29 and the day-30 edge, were linked by `ops ingest` with 0 skipped (`9 session(s) on drawn loans, 0 outside the sample, 0 skipped`).
- Packaged records refuse link params (24 of 24, 422 `invalid_params`). The attempt limit holds at `MAX_ATTEMPTS` = 3 on 2 loans. Non-ASCII digits and odd forms give 422 (34 of 34). Unknown loan 404; not drawn 409; a loan from the first draw keeps its draw after three later draws; day 31 refused, day 30 accepted.
- Readings order: v2.5 first when it has text; 30 of 30 of its own Hindi and Hinglish pairs consistent across session JSON, dialogue state and case file.
- Case contract on a loan-book call and a packaged call; `degraded_turns` equal to the dialogue state's; `speaker_confirmed` null because today's state has no such field.
- The stub is unreachable on a default server (26 requests, no session ran it, no TTS call).
- The phone page: the model strip follows the server's settings (headless Chrome); the two-readings line parses no figure in the browser; "unconfirmed" shows only for false and only beside the three outcomes (32 of 32 combinations).
- The `amount-check` clip's two readings are as stated, from the client's cache and ledger (one clip, TTS audio, not a rate); the read-back is the v2.5 figure, 2,012.
- 13 mutations, all caught, the three round-1 survivors among them. Its test count: 375 passed, 1 deselected, at 20:55 and 21:05 IST; no breaks from other lanes.

What fails or needs a decision, verbatim:

> 1. **Known trade-off, round 1 item 5, unchanged.** A refusal heard only by v3.0 is not acted on when v2.5 has text.
>    - v3.0 `मुझे बात नहीं करनी, कॉल बंद करो` with v2.5 `हाँ`: next line `premium.reask`.
>    - v3.0 `मैं वो नहीं हूँ, उनका भाई बोल रहा हूँ` with v2.5 `₹52,000`: next line `premium.say_again`.
>    - With v2.5 `""` or a 504, the same refusal gives `end.declined`.
> 2. **Minor, theoretical.** `readings()` tests `if heard.second:`, so a v2.5 reading of only whitespace (`" "`) goes first. v3.0 refusal with v2.5 `" "` gives `premium.reask`; with `""` it gives `end.declined`. None of the 5,252 cached Prisma transcripts has leading or trailing whitespace, so this has not been seen live. A `.strip()` would close it.
> 3. **Cosmetic, page.**
>    - `readingsLine(R("2,000","₹2,012"), false, "read_back", undefined)` gives `… · differ, Undefined's figure read back`. This needs `acted_on` null on a read-back turn, which I never produced through the server.
>    - An ok but empty v2.5 reading shows `Prisma v2.5: (no text) · differ, asked again`, not "missing".
> 4. **Vocabulary.** `acted_on` is a role (`"second"`) in the session JSON and a model (`"prisma-v2.5"`) in the case file. The page handles both, but the report should say which it means.

None of items 1 to 4 was changed after the verification, so the code on disk is the code the verifier ran. On item 4: in this report `acted_on` means the case file's field, a model name.

## 5. Credits

The ledger is shared with every worker and has no per-package tag. Its totals for the hours P1b used Gnani (11:00 to 13:00 UTC) are 14.1 estimated credits across all workers, so P1b used at most that, against a cap of 70. Since the resume (20:50 IST): 0; the round 2 verifier made no Gnani or LLM call.

## 6. Not verified

- No person has used the phone on a loan-book call. Every customer turn so far is Timbre audio or fake speech.
- Starting a loan-book call from the picker in a browser (round 1 only loaded the page).
- The `amount-check` persona as a whole live call: the demo replay waits for the coordinator's word after P2 round 3. The pre-made prompts were not re-voiced.
- `speaker_confirmed` with a real value: today's dialogue state has no such field, so the server reads null. It is read defensively and shows nothing until P2 round 3 lands.
- Two sessions for the same loan created before either is ingested are both allowed; ingest skips the second (a known limit, stated in `loanbook.py`).
- A batch replaced after a session was created: after a restart that call can get no case file (round 1, item 4; behaviour as found, not changed).
- A refusal heard only by v3.0 is not acted on when v2.5 has text (round 1, item 5: the dialogue contract's trade-off; 0 of 240 H4 pairs hit it).
- The task asked for a headless `samajh.server.replay` of a loan-book loan. The evidence in hand is round 1's live call through the same HTTP routes; no replay was run after the resume.

## 7. Report versus code

- `CLAUDE.md`, the `samajh/server/` entry, is stale: it says "a loan from the loan book cannot be called yet", "three packaged demo records" (there are four) and "310 offline" tests (375). It should also say that the dialogue is given v2.5 first on figure turns. P1b may not edit it.
- `references/pilots/P1-report.md` does not name the order of the two readings and says the `stub` dialogue is in the server's registry. The code now gives the dialogue v2.5 first when it has text, and a default server registers only the Samajh dialogue.
