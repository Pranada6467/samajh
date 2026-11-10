# P1b: independent verification (round 2)

Saved by the P1b sub-orchestrator on 2026-11-10 from the verifier's final message, unchanged. Verifier: independent, Opus high; it wrote none of the code and did not see round 1's inputs reused (it chose its own loans, draws and dates). Round 1: `verify-P1b.md`. The package report: `references/pilots/P1b-report.md`.

**Verdict: sound.** All four round-1 fixes and all three round-1 mutants that had survived now hold, and my own inputs found no failures. Two small edges and one known trade-off are below; none of them blocks P1b.

Everything ran in-process: FastAPI TestClient, the fake speech client, and a failing LLM. My batch came from `ops init` as a library, with draws on 2027-01-20 (24 loans), 02-03 (18), 02-17 (21) and 03-03 (15) at rate 0.4. I avoided the named loans and D-2027-01-11. Probes are in `/private/tmp/claude-501/-Users-masterpanda-projects-gnani-voice-ai-challenge/6927cbdf-011f-4bdb-9f0a-6ee41d3efe96/scratchpad/p1b-verify-r2/` (`elig.py`, `readings_probe.py`, `readings_probe2.py`, `case_probe2.py`, `amountcheck_probe.py`, `cache_probe.py`, `mutate.py`, `js_probe.mjs`, `serve8086.py`).

## What holds (n per class)

- **2a, date after the last attempt (138 of 138 checks in `elig.py`).**
  - Setup: 8 loans, two each of the 4 retry outcomes (call_back_later, language_switch, no_answer, request_unconfirmed). Each had one attempt at 23:59, 00:01, 12:00 or 20:01 on draw day +1 to +3.
  - On all 8 loans:
    - An explicit date equal to the attempt's day gave 409 `before_last_attempt`.
    - The day before was refused.
    - `/api/loans` listed a date strictly after the attempt.
    - Creation was accepted strictly after it (4 on the default date, 4 on an explicit date +2 days), and each call reached a `ready` case.
  - Day 30, last attempt at 23:30: the default gave 409 `outside_window`, explicit day 30 gave `before_last_attempt`, day 31 gave `outside_window`, and the loan was not listed.
  - Day 29, attempt at 23:59: the default was day 30 and the case was `ready`.
  - `uv run python -m samajh.ops ingest --state …` printed, verbatim: `9 session(s) on drawn loans, 0 outside the sample, 0 skipped; …`. 9 of 9 sessions were linked to their loans.
- **2b, link params on packaged records:** 4 records (hero, informed, third-party, amount-check) × 6 inputs (`draw_id`, `batch_id`, `sold_on`, `call_date`, `call_date=""`, `draw_id="x"`). All 24 gave 422 `invalid_params`; the 4 plain creations gave 201, and exactly 4 session directories exist.
- **2c, attempt limit (MAX_ATTEMPTS=3):** checked on 2 loans, one with all no_answer and one mixing call_back_later and no_answer. With 2 attempts the loan was accepted and listed. With 3, both the default and an explicit date gave 409 `attempt_limit`, and the loan was not listed.
- **2d, non-ASCII digits:** 6 scripts (Devanagari, Arabic-Indic, extended Arabic-Indic, full-width, Bengali, Tamil), each applied to all digits or one digit, in the loan id and in the date. All 24 gave 422. 10 more odd ids and dates (newline, leading or trailing space, an extra digit, `2027-1-20`, `T00:00`, a leading `+`, U+2212 minus signs) also gave 422, and no session was created.
- **2e, the basics on fresh inputs:**
  - Unknown loan: 404. Not drawn, and sold after the last draw: 409 `loan_not_drawn`.
  - A loan from the first draw, created after 3 later draws, kept `D-2027-01-20` and call date 2027-01-20.
  - Day 31: `outside_window`. Day 30: 201. Before the draw: `before_draw`. `2026-02-29`: `invalid_call_date`.
- **3, readings order:** 30 pairs through the adapter over HTTP, with `samajh.dialogue.step` spied, in Hindi and Hinglish. They include skipped-group amounts (3,02,000/₹3,00,200; 1,300/₹1,00,300; 5,26,000/₹5,00,26,000; 3,40,000/₹3,00,040; 7,05,000/₹7,00,500; 1,10,000/₹1,00,10,000), a v2.5 reading that was empty, a 504 or late, v2.5 text with no figure, both empty, v3.0 empty, and refusals.
  - 30 of 30 consistent: the dialogue got v2.5 first whenever v2.5 had text.
  - `turns[].text` equals the text in the dialogue state; `acted_on`, the readings' role/model/ok, `readings_agreed` and `followed_by` all match the state and the next line.
  - In 6 case files, `text`, `acted_on`, `readings_agreed` and `followed_by` match the session.
  - A GET from a fresh app carries the fields: 25 sessions, 150 turns.
- **4, case contract:** a loan-book call (hi-en) and a packaged call (informed, hi). Each had 22 live turns, 1 superseded take, and sources mic 8 / file 10 / none 4.
  - `customer_audio` leaves out the superseded take.
  - `book` is exact on the loan-book call and null on the packaged one; `started_at` equals `created_at`.
  - The classifier was made to raise on the first open and first amount turns. `degraded_turns` came out as `[15, 26]`, equal to `CallState.degraded_turns`; the per-turn `degraded` flags and the session JSON (2 turns) agree.
  - `speaker_confirmed` is null in both the case and the session. `CallState` has no `speaker_confirmed` field today, so null comes from that absence, not from the outcome: a mutant that guesses it from the outcome is caught.
- **5, stub unreachable on a default app:** 26 requests. Health shows `dialogues: ["samajh"]`. 0 sessions ran anything but samajh, and no TTS call was made.
  - Refused: "stub", "Stub", "STUB", " stub", "stub ", "stub\n", "ｓｔｕｂ", "samajh ", "Samajh" (422 `unknown_dialogue`). Also refused: a list, an object, an extra `Dialogue` key, a `params.dialogue` and `record: "stub"` (422).
  - A query string, a header or `"dialogue": ""` gave 201 with samajh.
  - Duplicate JSON keys: the last one wins, so `stub` then `samajh` gave samajh, and `samajh` then `stub` gave 422.
- **6, phone page:**
  - **Headless Chrome** (`--dump-dom`, port 8086, fake speech):
    - The strip read `Prisma v3.0 transcribe and Prisma v2.5 transcribe (figures) · Timbre v3.0 voice · Prisma v3.0 Batch after the call`.
    - With the settings' `tts.model` changed in-process to timbre-v2.5, it read `Timbre v2.5 voice`.
    - No Timbre literal is in `web/index.html` or `web/phone.js`.
  - **Code reading:** `readingsLine` is built only from the server's fields; no figure is parsed in the browser (no regex or `Number` on any text).
  - **Functions run in node:** `outcomeText` gave the right result for all 32 outcome × {true, false, null, undefined} combinations: "unconfirmed" appears only for false and only beside do_not_call, human_requested or call_back_later. `readingsLine` was run on 10 combinations.
  - Degraded turns get a mark on the turn and a count on the case card.
- **7, amount-check:**
  - **The claim is established from the cache, with no network call:**
    - v3.0, key `292b6436f37b…`: `"transcript":"2,000 रुपये रुपये दिए थे।"`.
    - v2.5, key `10d9c26b6eb5…`: `"transcript":"₹2,012 दिए थे"`, literal `दो हज़ार बारह रुपए दिए थे`.
    - The ledger shows the first rows for these keys live at 2026-11-10T12:47:23Z: status 200, attempt 1, 0.02 estimated credits each, 2.0 s of audio.
    - `06.wav` is already in the server's normalised form (same key), and `07.wav` is byte-identical to it.
  - **Text run:** right_party.ask → disclosure.go_ahead → second_check.ask → open_recall.ask → kind.ask → premium.ask → premium.say_again → read_back.confirm → … → close.bye.
    - The readings differ on both takes. The read-back is `तो आपने उसके लिए दो हज़ार बारह रुपये दिए। सही है?`, which is v2.5's 2,012 and equals the record's premium.
  - **Leak scan:** the premium words appear only in read_back.confirm, and the cover "एक लाख" only in read_back.cover_confirm; both repeat the customer's own figure. No term, cancel window, provider, surname or birth year appears in any bot line.
  - **Labels:** the description says "One chosen clip, not a rate."; the readings note says "Chosen clip … One example, not a rate."

## What fails or needs a decision

1. **Known trade-off, round 1 item 5, unchanged.** A refusal heard only by v3.0 is not acted on when v2.5 has text.
   - v3.0 `मुझे बात नहीं करनी, कॉल बंद करो` with v2.5 `हाँ`: next line `premium.reask`.
   - v3.0 `मैं वो नहीं हूँ, उनका भाई बोल रहा हूँ` with v2.5 `₹52,000`: next line `premium.say_again`.
   - With v2.5 `""` or a 504, the same refusal gives `end.declined`.
2. **Minor, theoretical.** `readings()` tests `if heard.second:`, so a v2.5 reading of only whitespace (`" "`) goes first. v3.0 refusal with v2.5 `" "` gives `premium.reask`; with `""` it gives `end.declined`. None of the 5,252 cached Prisma transcripts has leading or trailing whitespace, so this has not been seen live. A `.strip()` would close it.
3. **Cosmetic, page.**
   - `readingsLine(R("2,000","₹2,012"), false, "read_back", undefined)` gives `… · differ, Undefined's figure read back`. This needs `acted_on` null on a read-back turn, which I never produced through the server.
   - An ok but empty v2.5 reading shows `Prisma v2.5: (no text) · differ, asked again`, not "missing".
4. **Vocabulary.** `acted_on` is a role (`"second"`) in the session JSON and a model (`"prisma-v2.5"`) in the case file. The page handles both, but the report should say which it means.

## Mutations (13 run in a snapshot; all caught)

- Round 1's three survivors are now caught:
  - `customer_audio` counting superseded turns (`test_customer_audio_counts_the_take_that_replaced_another…`).
  - `_DATE` regex removed (`test_only_ascii_ids_and_dates…[params2]`).
  - The default date ignoring attempts (`test_every_reason…`).
- Also caught: the default date raised only up to the last attempt's day, an equal day allowed, the attempt limit off by one, packaged link params allowed, the old readings order (`test_readings_fields…differ_twice…`), v2.5 first even when empty, `speaker_confirmed` guessed from the outcome, `degraded` never set, `followed_by` always other, and `readings_agreed` without the figure gate.

## Tests

- `uv run pytest tests/server -q`: `375 passed, 1 deselected`, at 20:55:24 IST and again at 21:05 IST.
- No breaks from other lanes during my run.

## Not checked

- A figure turn or the case card rendered in Chrome: I covered them by reading the code and running the functions in node.
- A microphone call.
- Two sessions created on the same loan before ingest (known limit).
- A batch replaced mid-call (round 1 item 4).
- A real process restart.
- Tamil and Kannada.

## Wording the P1b report may use

- "Every call date the server accepts for a loan with logged attempts is after the last attempt's day; an independent run of 9 such calls, including day 29 and the day-30 edge, was linked by ingest with 0 skipped."
- "Packaged-record sessions refuse batch-link params; the attempt limit is the ops constant; non-ASCII digits give 422."
- "v2.5 first when it has text; 30 of 30 independent pairs consistent across session JSON, dialogue state and case file."
- "The amount-check clip's two readings are as stated, from the client's cache and ledger (one clip, TTS audio, not a rate)."
- "`speaker_confirmed` is null with today's dialogue (the state has no such field)."

## It may not say

- That a refusal heard by either model ends the call.
- That the models are "known" to differ in general: the evidence is one measured clip.
- That the case file shows who was speaking: `speaker_confirmed` is always null today.
- That anything was tested with real callers or human audio.

## Credits used

0. I made no Gnani or LLM calls, and the ledger's estimated total read 288.5443 before and after my probes.
