# P1b: independent verification (round 1)

Saved by the P1b sub-orchestrator on 2026-11-10 from the verifier's final message, unchanged. Verifier: independent, Opus high; it wrote none of the code. The fix round that followed is described in `references/pilots/P1b-report.md`.

**Verdict: sound with conditions.** Both claimed behaviours hold on my own inputs: the readings order, and loan-book calls through to ingest. Four things stand against them: one cross-side defect (a server-chosen date that ingest then skips), two server gaps, and three test gaps that survived mutation.

Probes live in `/private/tmp/claude-501/-Users-masterpanda-projects-gnani-voice-ai-challenge/10287c7b-c2fb-42e9-b7f9-063418bc7455/scratchpad/p1b-verifier/probes/`: `eligibility.py`, `calls.py`, `readings_http.py`, `h4_recount.py`, `picker.mjs`, `mutplug/p1bmut.py`. State directories are under `.../p1b-verifier/runs/`. I built my own batch with `ops init` and four draws at rate 0.4: 2027-01-18 (20 loans), 02-01 (17), 02-15 (20) and 03-01 (19). One copy got `ops run --analysis scripted` (102 attempts). I did not use SYN-PL-270107-0008, SYN-PL-270104-0001 or D-2027-01-11.

## What holds (n per class)

- **Creation and refusals:** 70 cases on HTTP with fake speech; 65 as expected, the other 5 are listed below.
  - The earlier-draw loan created after three later draws carried its own draw (`D-2027-01-18`, call date 2027-01-18).
  - Day 30 was accepted; day 31, `2099-01-01` and a default date pushed past day 30 (18 logged no_answer attempts) all gave `409 outside_window`.
  - Before the draw and before the sale gave `409 before_draw`.
  - 14 malformed dates gave `422 invalid_call_date`, including `२०२७-०१-२०`, `"2027-01-20\n"`, `20270120` and 5,000 characters.
  - 11 odd ids gave `422 invalid_loan_id` (lower case, spaces, `../`, 10,000 characters, empty, `hero`).
  - Unknown loans gave `404`; an eligible loan not drawn and a loan sold after the last draw gave `409 loan_not_drawn`.
  - A last attempt with any of the 8 ending outcomes gave `409 attempts_ended`. The 3 retry outcomes were accepted with call date = draw day + 1.
  - The default date is raised to the last attempt's day. A date before the last attempt gave `409 before_last_attempt`.
  - `record` plus `loan` gave `422 record_and_loan`; neither gave `422 invalid_params`; a client-sent `draw_id`, `batch_id` or `sold_on` gave `422 invalid_params`; no batch gave `409 no_batch` and `/api/loans` returned `[]`.
  - After `ops run`, `/api/loans` lists exactly the one loan whose chain is still open; the others give `attempts_ended`.
- **Readings, 14 hand cases over HTTP on a loan-book loan:** all as claimed.
  - v2.5 empty, v2.5 504 (`error: gnani_server_error`) and v2.5 late (`error: timeout`): v3.0 acted on, `acted_on=primary`.
  - v3.0 empty with v2.5 text, and readings differing twice: the v2.5 figure 52,000 was read back.
  - v2.5 with no figure: the dialogue swapped and v3.0 was acted on (`primary`).
  - Read-back with one yes and one other figure, either way round: the read-back was said again (`read_back.reconfirm`).
  - Case-file labels in those 14 case files: 0 mismatches between `turns[].text` and `acted_on` and the log; every reading is labelled with its role and model.
- **Case contract C,** on a call with a restart mid-call and a superseded take:
  - The call used a mic/file/none mix, the restart was a second app over the same state, and a completed attempt was logged for the loan before the case build (no re-check: the case built).
  - `customer_audio {'mic': 8, 'file': 8, 'none': 1}`; the superseded take is excluded (with it, file would be 9).
  - `started_at` equals the session's `created_at`, unchanged after a failed case (Batch error) was rebuilt after ingest.
  - `book` is exact, `loan_id == record_id`, and `turns[].source` matches the log (17 turns).
  - Ingest linked the call both times; reading the session and case after ingest, and from a fresh app, gave 200; a second session gave `409 attempts_ended`.
- **New outcomes:** loan-book calls ending in `do_not_call` and `written_requested` (said at `kind.ask`) reached `ready` case files with those `call_outcome`s. Ingest logged both, and a later session gave `409 attempts_ended`.
- **Packaged records:** all 3, with and without a batch: `ready`, `book: null`; with a batch, ingest put them as `3 outside the sample`.
- **Leak scan** (bot lines, `/api/loans`, session JSON, all 46 extraction requests):
  - No premium, cover, term, cancel window, provider, full name, surname, birth year or loan id in the bot lines or the LLM requests. The one hit ("तीन लाख") is a fixed example in the extraction prompt.
  - The first name is spoken; the lender is spoken as "Namoona Bank", without "(synthetic)".
  - `/api/loans` and the picker note show the first name and the **birth year** (the answer to the second identity check), as designed.
- **Picker** (headless Chrome against my server on port 8086):
  - "Demo records" (3) and "Synthetic loan book" (68 = 76 drawn − 8 ended).
  - `?loan=SYN-PL-270205-0108` preset the loan and the language.
  - Only 1 of 4 Chrome launches returned; the other 3 timed out at startup.

## What fails or needs a decision

1. **Server and ops: a date the server accepts that ingest skips. Reproduced.**
   - Setup: a no_answer attempt logged on day 30 at 23:00 IST. The server's default call date was that same day (`2027-03-18`).
   - Ingest output, verbatim: `skipped 20261110T121629-7c0ef4be8e83: the call is dated 2027-03-18T17:46:29.626000+05:30, not after the loan's last logged attempt (attempt 1, 2027-03-18T23:00:00+05:30); it cannot be put before it without renumbering`.
   - An explicit `call_date` equal to the last attempt's day is also accepted.
   - The simulator dates the next attempt the *day after* the last one; the server raises only *to* that day. The fix belongs on the server side (`open_call`).
   - No other accepted date is skipped by ingest's date rules: the server refuses dates before the sale, before the draw, after day 30, and on ended chains.
   - Separately, the known two-session limit: ingest output, verbatim: `skipped 20261110T121629-cebdd6171399: the loan's attempts had already ended: attempt 1, on day 8 from the sale, ended as completed`.
2. **Server: a packaged-record session stores client link params.**
   - Input `{"record":"hero","language":"hi","draw_id":"D-2027-01-18"}` gives `201`, with params stored as `{'record': 'hero', 'language': 'hi', 'draw_id': 'D-2027-01-18'}`. The same happens with `call_date`.
   - It has no effect (`book` stays null and ingest lists the call as outside).
   - Cause: `samajh_factory` accepts `LINK_PARAMS` for every session, and `_link` returns early when there is no `loan`.
3. **Server: a 4th attempt is accepted.** After 3 no_answer attempts (the simulator's `max_attempts=3`; the README says "up to 3"), the loan is listed and creation gives `201` with call date draw day + 3. This is not in the claimed refusal list, and ingest has no limit either.
4. **Server, behaviour as found: a batch replaced after creation** (different `batch_id`).
   - The same app continues the call.
   - After a restart the next turn gives `409 session_not_active`, and the case build gives `409 no_case_file` ("the call's record is not on this server"). That call can never get a case file.
5. **Dialogue contract trade-off.** A refusal heard only by v3.0 is not acted on when v2.5 has text:
   - v3.0 `मुझे बात नहीं करनी, कॉल बंद करो` with v2.5 `बावन हज़ार`: the next line is `premium.say_again`.
   - With v2.5 `हाँ जी`: the next line is `premium.reask`.
   - "मैं वो नहीं हूँ, उनका भाई बोल रहा हूँ" heard by v3.0 only: the next line is `premium.say_again`.
   - How often the H4 pairs hit this: 0 of 240.
6. **Minor:** `SYN-PL-२७०११८-0001` gives `404 loan_not_on_book` rather than 422, because `\d` matches Devanagari digits. It is still refused.

## Mutations

Monkeypatched in a private snapshot of the tree; nothing in the checkout was edited.

- **Caught:**
  - (a) the old readings order: 3 new failures.
  - (b) each check removed: invalid_loan_id, loan_not_on_book, loan_not_drawn, attempts_ended, before_draw, outside_window, a window off-by-one, before_last_attempt, the default raise, record_and_loan, refusal of client link params.
  - (c) eligibility re-checked in `resolve`.
  - (d) `started_at` taken from now (3 failures).
  - Also caught: `acted_on` always primary, transcript always primary, the dialogue not reporting `heard`, `draw_of` returning the last draw, a premium in the listing, the lender keeping "(synthetic)".
- **Survived:**
  - **(e) `customer_audio` counting superseded turns:** no test has a superseded take. My probe shows the code is right.
  - **The `_DATE` regex removed:** the tests do not exercise it.
  - **The default date ignoring logged attempts** (`draw.as_of` alone): no test checks the default with attempts logged. My probe shows the code is right.
  - Client params overriding the link: an equivalent mutant (only `call_date` can get through, and it equals the link's).

## H4 recount

240 real Prisma v3.0/v2.5 pairs through `SamajhDialogue` under today's dialogue; on `premium.say_again` the same pair is played again.

- New order: 238 right, **2 wrong** (kn, ta), 0 none.
- Old order: 224 right, **16 wrong**.
- 31 of 240 got `say_again`.
- `_acted_on` against what the dialogue recorded: 0 mismatches over every turn in both orders.
- Limits: TTS audio, in-sample for the parser, and the "same pair repeated" assumption.

## Live call

- Loan SYN-PL-270210-0126, Hindi, draw D-2027-02-15; session `20261110T123101-f5bf3da878ba`.
- Outcome `completed`, ended by the dialogue; case `ready`, tier `incomplete`.
- Fields:
  - `loan_id` = `record_id` = SYN-PL-270210-0126.
  - `book {'batch_id':'B-2027H1-ec2bdb3e','draw_id':'D-2027-02-15','sold_on':'2027-02-10','call_date':'2027-02-15','day_since_sale':5}`.
  - `started_at 2026-11-10T12:31:01.696+00:00`, equal to `created_at`.
  - `customer_audio {'mic':0,'file':16,'none':0}`.
  - `dialogue_reads_first "prisma-v2.5 when it has text, else prisma-v3.0"`.
- On the 3 figure turns (seq 11, 21, 23) the transcript is the v2.5 text and `acted_on=prisma-v2.5`, e.g. v2.5 "…ढाई लाख तक का कवर है।" against v3.0 "…2.5 लाख तक का cover है।".
- Ingest (12:32 UTC; `samajh/ops` had batch, book, model, report, sampler, sessions, simulate, store, views, wording modified and chain.py new): `1 session(s) on drawn loans, 0 outside the sample, 0 skipped`.
- The attempt was logged at `2027-02-15T18:01:01.696+05:30`, `phone_session`, completed.
- `ops report`: rc 0; funnel attempted 1 of 76; tiers incomplete 1 of 1.
- Review API: `/api/review/attempts` lists the attempt with the session id. `/api/review/queue` is `{"items": []}`, which is right because the queue takes `refer` only.
- Outside P1b: the case line reads "The call did not get to: the premium." although the customer gave 25,000 in open recall and confirmed the read-back. This is the dialogue or extraction owner's to look at.

## Tests

`uv run pytest tests/server -q`, 12:32 UTC: **3 failed, 321 passed, 1 deselected.**

- All three expect only the premium question to get a second reading.
- Evidence: `test_casefile` lists the twice-read turns as `['बावन हज़ार', 'हाँ, सही है', 'पैसा सुरक्षित रहेगा']`, and the third is the cover answer. `test_samajh_dialogue` has `second_reading` True at index 11 on a non-premium question.
- P1b touches neither those tests nor that flag.

Two transient breaks came from other workers, not P1b:

- At 12:19 UTC `import samajh.server` failed: `ImportError: cannot import name 'RuleFinding' from 'samajh.ops.views'`.
- At about 12:20 UTC every case failed with `ValueError: 'recall' is not a valid Question` (11 failed tests) while `samajh/extract` and `samajh/rules` were mid-edit. My mutation runs therefore used a snapshot with those files taken from HEAD; its baseline was 3/321.

**Credits:** ledger 284.3961 before, 287.2427 after, so at most **2.85** (other workers share the ledger).

## Not checked

- A microphone call in the browser, and starting a loan call from the picker (I only loaded the page).
- `?loan=../x` in the picker (that Chrome run timed out).
- A live Hinglish call, and Tamil or Kannada calls beyond creation.
- Two creations racing, `ops run` after a phone session, two retry sessions on the same default date.
- A real process restart mid-call (I used a second app in the same process).

## Wording the P1b report may use

- "v2.5 first when it has text."
- "In the H4 recount through the server adapter under today's dialogue: 2 wrong figures held in 240 against 16 with the old order (TTS audio, in-sample)."
- "Eligibility checked once at creation, with the listed codes; verified on an independent multi-draw batch."
- "The case file carries `book`, `started_at` and `customer_audio` as agreed; ingest linked a live loan-book call."

## It may not say

- That every date the server accepts is ingestable (same-day dates are not).
- That the tests pin `customer_audio`, the date regex or the default date with attempts logged (all three mutants survived).
- That client link params are refused on every session (packaged-record sessions accept them).
- That a refusal heard by either model ends the call.
- That anything was tested with real callers.
