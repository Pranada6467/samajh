# W5 (iteration 4, wave 2): reply delay

2026-11-14, on dev after 2f773f5, uncommitted. Orchestrator Opus (high). Builders Opus (low): harness, checkpoints 1, 2, 3a, 3b, the ledger fix, the lag fix, two fix rounds, Smart Turn probe. Research: Sonnet. Independent check: Opus (high), on held-out clips it wrote itself. **Every customer clip below is Timbre TTS audio, not human speech. No person has used this code.**

## What was built
- **Checkpoint 1: pre-made lines** (`samajh/server/prompts.py`, `app.py` lifespan, `settings.toml [prewarm]`). At start the server makes every static line and every first-name line of the record book (packaged records and `SAMAJH_RECORDS_DIR`, so the human cards too). It covers hi, hi-en, ta and kn at 8 kHz, because W4's live language switch can reach ta and kn. Then it accepts calls. The start fails with the list of lines if a line cannot be made, and fails before making anything if the estimate exceeds `max_credits = 40`. With no Gnani key it only warns. A loan-book loan's first-name lines are made inside session create (8 s bound). `uv run python -m samajh.server.prompts check --lang hi --lang hi-en --lang ta --lang kn` lists what is missing and makes no request.
  - **Lines that can still be spoken without pre-made audio:** the amount read-backs (`amount_words` templates), in every language. Also a loan-book first name, if its make at session create failed or went past 8 s. And any line at 16 kHz, which is not prewarmed.
  - Last live start: "320 static and record-book first-name lines checked, 0 missing".
- **Checkpoint 2: per-line playback** (`app.py`, `web/phone.js`). A reply's lines start being made right after the turn's STT and dialogue step. The phone fetches `GET /api/sessions/{id}/lines/{seq}/{i}.wav` and plays line 1 while line 2 is still being made. The joined `bot-NNN.wav`, the log fields and the recording are as before. Nothing is committed, served or recorded after a hang-up, a close or a supersede. A later take cancels the earlier reply's remaining lines.
  - **Not built: "synthesise the likely next line while the customer speaks".** Once fixed lines are pre-made, the only unmade lines are read-backs, which need the customer's figure. A background warmer did exist, and was deleted after it caused a live `gnani_busy` (checker-independent finding below).
- **Ledger fix** (`samajh/clients/gnani/tally.py`, `client.py`). This is the largest single gain.
  - `_check_cap` used to parse the whole shared ledger (315,471 rows, 124 MB) before every uncached request, inside the one-slot lock: 0.73 s each time.
  - It now reads only appended rows: 0.07 to 0.13 ms per check. The totals are identical (`==`), including under three concurrent writer processes (checker).
- **Checkpoint 3: streaming STT, default off** (`samajh/clients/gnani/stream.py`, `samajh/server/stream.py`, the WS route `/api/sessions/{id}/stream`, phone streamer, `[streaming]` in `settings.toml`).
  - The browser streams 40 ms PCM chunks at the line rate and sends `commit` at its own VAD cut. The server uses the stream's final text as the primary reading (`SttReading.mode="stream"`).
  - Any failure, and every later take, falls back to REST with `params.stream_fallback` = no_stream, error, timeout, budget, disconnected, no_commit, superseded, ended or later_take.
  - The v2.5 REST second reading is unchanged.
  - Streaming never takes the REST lock and keeps a `stt.stream` ledger row with audio seconds. Billing is unknown, so `max_stream_seconds = 3000` acts as a budget.
  - **Hinglish streams as `hi-IN`:** v3.0 streaming rejects `hi-IN,en-IN`. On 2 Hinglish clips `hi-IN` matched REST `hi-IN,en-IN`; `multi_lang_codes` changed nothing; `en-IN` romanised the Hindi.
  - `min_silence_ms = 2000` kept the 600 and 1,000 ms spliced pauses in one segment (2 of 2), so the client owns the cut.
- **W4 follow-ups:** the new lines are prewarmed. `test_prefetch` counts classifier calls from the recall turn on. On right-party replies, Prisma v3.0 REST gets the first name as its one `keyterm`; the log carries `params.keyterms="1"`, not the name.
- **Checkpoint 4 (barge-in): not built.** The phone is still half duplex.
- **Tools:** `tests/server/browser_calls.mjs` drives whole calls hands-free in headless Chrome. Every turn goes through a synthetic microphone, so the real VAD cut, grace, playback and `bot_start_ms` run. `tests/server/probes/latency_runs.py prepare|run|summarise` adds ±1 LSB dither per seed, so STT is never a cache hit. `tests/server/probes/smart_turn_probe.py`.

## Measurements
Method: 4 packaged calls (`hero`, `amount-check`, `informed`, `third-party`; 46 customer turns), every turn a hands-free microphone turn in headless Chrome. `bot_start_ms` is the phone's own figure: end of speech to the first reply sample. Every STT reading was uncached (n counts only those). Each run was a separate server on port 8087.

| run | code | bot_start_ms median / p90 / max (n) | server stt_ms median | lines made on the call |
|---|---|---|---|---|
| before (warm cache) | 05d829b + wave-1 tree | 2,795 / 3,850 / 4,682 (46) | 1,318 | 0 of 91 |
| after 1+2 + ledger fix | same, plus W5 | **1,904 / 3,478 / 5,081 (46)** | 375 | 0 of 89 |
| before, cold cache (voice Vasudha) | baseline | 7,114 / 17,088 / 24,600 (32) | 1,438 | **49** (26 in `hero`) |
| after, cold cache (voice Tarika) | W5 | 2,964 / 5,373 / 6,120 (18; 1 call failed `gnani_busy`, 1 Chrome start failure) | 502 | 5 (right-party and read-backs) |
| final, REST | final tree | 1,822 / 1,988 / 6,401 (46) | 280 | 1 (a read-back, 4.6 s) |
| final, streaming on | final tree | 1,822 / 1,846 / 2,300 (46) | 7 (stream final) | 0 |

- **Read the rows in pairs.** The first two rows are a fair pair, because the LLM classifier worked in both. The cold pair ran while OpenRouter returned 402 (out of credit), and so did the final pair: 7 of 14 and 10 of 15 classifier turns were degraded, so dialogue time is understated there.
- **What limits the reply now:** the grace window (open questions: 1,800 ms; yes/no: 1,000 ms). Final medians by question kind: open 1,827 / 1,830 ms, yes/no 1,403 / 1,142 ms.
  - With a working classifier (median 1.2 s on open turns in the "after" run), open turns go back to being dialogue-bound: cut 1,100 + server about 1,500 ≈ 2.6 s.
  - The next gains are therefore the classifier's time (W4's code) and the grace setting. Neither is mine to tune without human audio.
- **The streaming path itself:**
  - The first build lost about 800 ms because `commit()` waited for the upstream close handshake. After the fix, the server waits a median 7 ms after the turn arrives (the final often lands before the upload).
  - 46 of 46 primary readings were streamed, with no errors and 0 splits.
  - Text differs from REST mostly in script. In the checker's held-out comparison, 1 of 13 same-audio pairs differed ("loan के time एक FD" against "लोन के टाइम एक एफडी"), with the same parsed amount.
- **Smart Turn v3.2** (BSD-2, lists Hindi, 22 ms per call on CPU): not adopted, not even behind a setting.
  - At p > 0.5 it called 44 of 48 finished answers complete, but also 28 of 34 natural pauses inside answers and 7 of 21 mid-number cuts.
  - It cannot see a customer who is about to resume.
  - It would save about 575 ms per turn at that error rate.
  - LiveKit's turn models are licensed for LiveKit Agents only. TEN and Vogent do not cover Hindi.
- **Cut and grace are unchanged.** No human session exists under `.samajh-human/` yet. The wave-1 scorer is the tool for that once the user's calls exist.
- **Gnani spend:** the ledger read 459.3192 at my first reading and 548.8231 at the end, +89.5 estimated credits. The ledger is shared, but by the row windows nearly all of it is this package. By kind: TTS 48.8 (mostly prewarm: ta/kn 23.2, the cold-cache voices about 26), Prisma Batch case files 29.9 (the phone starts one after every call), REST STT 7.3, streaming 3.9. The checker spent about 28 of the total.

## Independent check (its words, abridged) and what was done
- **"Budget overrun … a server start made 160 Tamil and Kannada lines before it accepted any connection: 23.21 credits; prewarm has no limit."** Fixed: `max_credits` (above).
- **"Hinglish calls send Batch the wrong language when streaming is on"**: `casefile.batch_options` takes `language_code` from the first reading, which is `hi-IN` when streamed. Open: `casefile.py` is not mine (see "Needed from others").
- **"Some fallbacks to REST are not marked"** (the phone never sends `stream=1`). Fixed: a hands-free part-1 microphone take in a streaming session counts as requested.
- **"A socket for an old reply is accepted and kills the current stream."** Fixed: only the prompt now waiting is accepted.
- **"Streaming can block the server's event loop for up to about 2 s"** (`send` → `_finish` after an upstream error). Fixed: `send` raises at once and closes in the background.
- **"The second half of an answer was lost after an 832 ms pause"** on the streaming run. The resume was marked at 1,799 ms against an 1,800 ms grace on the REST run. The builder found no cause in the streaming code. Open: an edge of the grace window, n = 1.
- **"OpenRouter is out of credits."** Reported to the coordinator.
- **"With no Gnani key the server starts with a warning."** Kept, by design: tests and `/api/health` need it.

Also found by the orchestrator's own runs:
- **The session warmer made a 7.0 s line while the customer answered**, so the turn failed `gnani_busy`. Fixed by deleting the warmer.

## Open
- The browser was driven only headless, with digital audio in and the speaker muted. Not exercised: a real microphone, echo and echo cancellation, a speaker, room noise, Safari, Firefox, phones, `wss`.
- Timbre was slow during these runs: single lines took 2 to 7 s. A read-back still costs that on the turn.
- A call that starts while the previous call's Batch upload holds the slot can get `gnani_busy`. Inferred from the ledger; not measured.
- Streaming billing is unknown: read the dashboard. The `stream_split` path has never fired.

## Running Samajh dialogue `step` inside a telephony framework (facts read 2026-11-14)
- **Pipecat 1.16 (BSD-2)** ships an `ExotelFrameSerializer`: Exotel Voicebot applet, 16-bit PCM at 8 kHz, chunks in multiples of 320 bytes. It also ships Twilio and Plivo (mu-law), a FastAPI WebSocket transport, a SIP transport, interruption frames (barge-in), and a Gnani plugin (`pipecat-gnani` 0.6: REST and WebSocket STT, TTS).
- **The port:** one `FrameProcessor` between STT and TTS that holds `CallState` and calls the pure `step(state, text, second_reading=…)` on each final `TranscriptionFrame`. It emits the utterance's lines as `TTSSpeakFrame`s, or lets the existing per-line cache serve them as audio frames.
- **What is lost in the port:**
  - the two-reading figure turn (a v2.5 REST call has to be made inside the processor);
  - the one-slot lock: neither plugin documents the 1-request account limit, so REST STT, TTS and Batch need the repo's client, not the plugin's;
  - the session log and case-file pipeline, which have to be fed from the processor.
- **LiveKit Agents 1.8** has SIP quickstarts for Twilio, Plivo and Telnyx, but no documented Exotel route. `livekit-plugins-gnani` streams with a language list by default, which our probe says v3.0 rejects.
- **Estimate:** one to two days for a Pipecat Exotel prototype that reuses `samajh/dialogue` and `samajh/clients/gnani` unchanged. Not built.

## Needed from others
- **`casefile.py` owner:** take the Batch language from the bot event's language (or from the REST options), not from a streamed reading's `language_code`.
- **`web/api.js`:** a `stream` option on `postTurn` and an `AbortSignal` on `bytes`, so a hang-up cancels in-flight line fetches.
- **`browser_calls.mjs` / phone:** a no-case flag. Each measured call starts a Batch case file (about 1.5 credits).
- **Documentation worker:**
  - The `CLAUDE.md` credit figures are stale: the ledger reads 548.82.
  - Add the prewarm, the `prompts check` command, the per-line route, the `[streaming]` setting, the tally, `browser_calls.mjs` and `latency_runs.py`.
  - "Streaming is not built into the server" is now false: it is built, and off by default.
- **Coordinator:** OpenRouter still returned 402 at 23:37Z. Re-measure the final pair once it is funded.

## Tests
`uv run pytest tests/server tests/clients -q -m "not live"`: **858 passed, 3 deselected** (68.7 s). `uv run ruff check samajh/server samajh/clients tests/server/test_*.py tests/clients`: clean. `node --check web/phone.js`: ok. (`ruff` flags style in the two probe scripts under `tests/server/probes/`.)
