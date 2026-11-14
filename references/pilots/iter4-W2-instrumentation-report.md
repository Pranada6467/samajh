# W2 (iteration 4, wave 1): per-turn instrumentation and the human-session scoring kit

2026-11-14, on dev at 107a908 plus uncommitted work. Builders: Opus (low effort); independent check: Opus (high effort), on inputs it wrote itself. Runbook for tomorrow: `references/pilots/iter4-human-session-runbook.md`.

## What was built

**Session log, additive** (`samajh/server/sessionlog.py`, `app.py`). Nothing was renamed or removed, `LOG_VERSION` is still 2, and old logs load: the checker stripped every new field from a log, and it reloaded and built a ready case.
- `SttReading.cache_key` and `http_status` (200 when fetched, None on a cache hit, the upstream status on a failed second reading). A failed second reading now keeps the client's `attempts`.
- Per bot line, `TtsCall.synth_ms` (the Timbre call plus conversion). `cache_hit` tells a pre-made line from one synthesised during the call.
- `CustomerEvent.classifier`: `ran`, `label`, `latency_ms`, `wait_ms`, `model`, `degraded`.
  - `wait_ms` is the time spent inside `interpret`: what the classifier added to the turn.
  - `latency_ms` runs from the prefetch's `begin` to the answer. It is an upper bound on the LLM's own time and includes the wait for the second reading.
- `CustomerEvent.state_before` and `state_after`: the scalar fields of the dialogue's `position` only, never the state, which holds every turn's text.
- `CustomerEvent.browser` (`BrowserListen`): mode, cut, grace, VAD marks (`speech_start`, `pause` with its length, `cut`, `resume`, `grace_expired`, `send`), takes, `grace_used`, `eos_wait_ms`, `post_ms`, `echo_cancellation`.
- `BotEvent.browser` (`BrowserPlayback`): `bot_start_ms`, output latency, `played_ms`, `completed`, and `talk_over` (voiced runs on the mic while bot audio played).

**New endpoint** `POST /api/sessions/{id}/events/{seq}/browser`:
- The body is strict JSON of at most 16 KB, with every ms value from 0 to 600000.
- Errors: 404 for an unknown session or seq, 422 for the wrong event type or a bad value, 413 for an oversize body.
- It works whatever the call's status. It rewrites only `session.json`, never `call.wav`, the dialogue state or the status (the checker confirmed the `call.wav` sha before and after).

**Classifier record** (`samajh/server/dialogue.py` `Step.classifier`, and the `_Recording` proxy in `samajh/server/samajh_dialogue.py`). The coordinator approved editing both files. The proxy passes `begin` and `interpret` through unchanged and makes no extra LLM call. If its own bookkeeping fails, it gives `classifier=None` and the turn is unaffected. It stores no text.

**Browser** (`web/vad.js`, `web/phone.js`):
- `vad.js` has an optional `pauseMs` pause event, off by default; the existing events are unchanged.
- `phone.js` posts the two reports fire-and-forget and logs one `[samajh] …` console line per report.
- Talk-over runs a separate detector that only measures frames during bot audio and never keeps or sends them. The phone is still half duplex.

**`samajh/human`** (new package): `uv run python -m samajh.human …`
- `score --sessions DIR… [--cards] [--log] [--ledger] [--out]`, one markdown report:
  - per session: card, outcome, tier, match, void, and the gold grounds matched (from the call, from gaps, from the record, plus `unmappable` and `extra`);
  - class tables per 100 with Wilson intervals, rows adding up to n, void sessions apart, never pooled;
  - void rate;
  - latency (median, nearest-rank p90, max, n) split by mic or file;
  - STT health, with the ledger joined by `cache_key` and by time window;
  - failed steps;
  - pauses against the current cut;
  - talk-over;
  - two-reading agreement (agreed, differed, second missing, no figure).
- `refs`: a CSV of reference transcripts to fill in. It skips year-of-birth answers and keeps filled cells.
- `wer`: WER and CER after `_norm`, and exact-amount accuracy, per reading.
- `notes --in DIR --lang`: ffmpeg to 16 kHz and the simulated 8 kHz line (`MuLaw`); v3.0 and v2.5 `transcribe` through `live_client(PATIENT)`; a credit cap; a dry run; a refusal to write anywhere in the repo that git does not ignore; a default output under `.samajh-human/notes/`.

## Measurements (all TTS audio; nothing here is human speech)

**Gnani spend:** the ledger read 325.5976 before and 341.8675 after, so **16.27 estimated credits** against the raised budget of 40.
- An 8 kHz hero replay: 0.00 (every request was a cache hit).
- Four 16 kHz replays of the packaged calls: 11.89.
- Notes runs: 0.20 (3 clips), then 2.86 (32 Hindi clips) and 1.33 (14 Hinglish).

**Fresh 16 kHz replays** of `hero`, `amount-check`, `informed` and `third-party` (the replay tool on my own server on port 8086, sessions under `.samajh/w2-replay16`; 4 sessions, 46 counted turns). In ms:

| stage | median | p90 | max | n |
|---|---|---|---|---|
| STT primary | 1229 | 2462 | 3839 | 46 |
| STT second | 1194 | 2453 | 2518 | 10 |
| classifier wait | 12 | 1160 | 1160 | 6 |
| server per turn | 1414 | 2985 | 5834 | 46 |
| TTS line synthesised during the call | 3724 | 5411 | 7294 | 56 |
| bot utterance synth | 3371 | 10246 | 22938 | 46 |

- TTS lines: 31 pre-made, 60 synthesised during the call. No 16 kHz lines had been pre-made, so these synthesis times are the worst case; the phone defaults to 8 kHz.
- STT: 49 readings came back 200 and 6 were cache hits. The second reading timed out once (1 of 10 figure turns). The `cache_key` join found ledger rows for 50 readings, every one 200 with no retry. That includes cache hits whose first fetch fell inside the window. There were no error events.
- Two readings on figure turns: agreed 2, differed 1, second missing 1, no figure 6.
- The classifier ran on 6 turns, every label `answer`, none degraded.
- `bot_start_ms`, talk-over and the VAD marks show "not logged": the replay tool posts no browser reports.

**Scorer on `eval/p5/runs/voice-smoke*`** (8 sessions, 72 file turns; the same 4 customers run twice, so they are not independent). Report head:

> Sessions: 8; counted customer turns: 72; void sessions: 0; sessions with browser data: 0. Audio: 0 mic turns (human speech) and 72 file turns (TTS audio, not human).
> P5-C001 completed/refer, match yes, grounds 6 of 6; P5-C006 no_go_ahead/incomplete vs completed/refer, match no, 3 of 4 (missing belief_mismatch); P5-C007 completed/refer, match yes, 4 of 4 (payment_frequency unmappable); P5-C048 wrong_party, match yes, loan named no.
> problem (n = 6): referred (completed) 4/6 [30-90]; missed 0/6 [0-39]; ended early or no case 2/6 [10-70]. procedural (n = 2): outcome reached 2/2 [34-100]; loan named 0/2 [0-66]. Void 0/8 [0-49].

**WER on 46 fixture clips** re-encoded as ogg, m4a and opus. The references are the fixtures' scripted texts. The clips are 8 kHz Timbre audio, so "16k" here means upsampled.
- Hindi (32 clips): v3.0 0.171 WER / 0.216 CER; v2.5 text 0.114 / 0.110; v2.5 literal 0.043 / 0.017. Exact amount, v3.0: 3 of 5 at 16k, 5 of 5 at 8k. On two clips at 16k, v3.0 wrote "दो हज़ार बारह" as "2,000 रुपये रुपये".
- Hinglish (14 clips): v3.0 0.211; v2.5 0.411. The gap is mostly script: v2.5 on `hi-IN` writes "येस करेक्ट" where the reference has "yes, correct". This is in the runbook as a caveat.

## Independent check, in its words, and what was done
The checker ran its own fake sessions (void, a 504-then-200 retry, a split take, talk-over, a card mismatch, an early end, a third party with a loan line). It reported: "Every number in my own fake-session report matched my hand computation." That covered the Wilson intervals, the p90, the pause buckets, the would-have-split counts at the exact cut, and the ledger tallies. It found no blockers.

**Should-fix findings, all fixed:**
1. "'two readings agreed: false' mixes a missing second reading with a real disagreement." These are now separate counts.
2. "a failed second reading cannot be joined to the ledger, and its retries are lost." `attempts` is now taken from the error. The ledger is also tallied by time window, because a failed reading has no `cache_key`.
3. "failed turns are invisible in the report." There is now a "Failed steps" section.
4. "the 'classifier' latency includes the wait for the second STT reading." `wait_ms` was added and both rows are labelled.

**Minor findings fixed:**
- Latency is now split by source.
- `notes` keeps typed references for absent notes.
- A path in the wrong letter case can no longer slip past the out-path check (`samefile`).
- The report bodies are strict (`"yes"`, `true` and `"12"` are now 422).
- Duplicate gold rules count once, and record grounds are reported.
- Labels: "(no label, degraded)", "failed, no status", and a note that pauses under 200 ms are not measured.

**Minor findings left open:**
- An empty report `{}` overwrites an earlier one (last write wins).
- Reports on superseded events are accepted; the scorer ignores them.
- A talk-over run still open when playback ends is closed at the detector's clock, which includes up to 300 ms of hangover.
- The `cut` mark carries the configured `cut_ms`, not a measurement.

## Open
- **The browser part has not been opened in a browser by any agent.** The checker reviewed the code and ran `vad.js` under node. The runbook §2 lists the three things to check in the console on the first call:
  1. a `customer` line per turn with marks above 0 and no "refused" warnings;
  2. a `bot` line with a plausible `bot_start_ms`, and talk-over 0 while silent (above 0 means echo is counted);
  3. a mid-answer pause of about 1.5 s gives `takes=2 grace_used=true`.
- `bot_start_ms` and talk-over exist only for browser calls. Echo can count as talk-over.
- A classifier answer of "unclear" is not kept by `llm_fallback`, so it records as `ran=False`.
- Year-of-birth turns enter the latency and pause numbers but never their text: no new field holds the reply, which the checker confirmed with the year check on.
- The time-window ledger tally also counts other processes on the account.
- The `check_out` refusal can wrongly refuse an ignored path typed in another letter case. It fails safe.

## Needed from others
- **Documentation worker:** add `samajh/human`, the runbook, the browser endpoint and the new log fields to `CLAUDE.md`, `README.md` and `USER-GUIDE.md`. `settings.toml` says to set the cut and grace "once some are recorded"; the scorer's pause section is now the tool for that.
- **Wave 2 (latency):** TTS synthesised during the call took a median 3.7 s per line, and up to 22.9 s for one utterance, at 16 kHz with nothing pre-made. Pre-warming every line at the call's rate is the obvious fix.
- **Wave 2 (latency):** `replay.py` (not mine) posts no browser reports, so headless runs cannot measure `bot_start_ms`.
- **Possible follow-up:** the reports could move into `web/api.js` (not mine; for now `phone.js` calls `fetch` itself).
- **Seen while working:** other workers' uncommitted edits in `samajh/dialogue/` briefly broke 2 tests in `tests/server/test_readings_fields.py` mid-run; they passed on the final run.

## Files and tests
- Changed: `samajh/server/{app,sessionlog,dialogue,samajh_dialogue}.py`, `web/{phone,vad}.js`, `tests/server/{test_vad.py,vad_check.mjs}`.
- New: `samajh/human/` (`__main__`, `sessions`, `score`, `wer`, `notes`, `stats`), `tests/human/test_human.py`, `tests/server/test_instrumentation.py`, `tests/server/test_classifier_record.py`, and the runbook.
- `uv run pytest tests/server tests/human -q`: **530 passed, 1 deselected** (the baseline was 459 server tests).
- `uv run pytest tests/ops -q`: 335 passed.
- `uv run ruff check samajh/server samajh/human tests/server tests/human`: clean.
