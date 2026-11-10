# W7 voice loop: transport, measurements and what we chose (2026-11-10)

Goal: the audio loop a Samajh call runs on. A FastAPI backend owns the Gnani key. A browser phone plays the bot's prompt, captures the customer's turn, has Prisma transcribe it and hands the transcript to a `Dialogue`. This file reports what was built, what was measured, and the turn-taking decision.

Every number here is from Timbre TTS voices. No human speech was recorded. Tamil and Kannada text is not human-reviewed. Nothing below is an accuracy claim about real callers.

## 1. Decision

**REST per turn is the default and the only path shipped.** The browser decides end of speech with an energy detector (700 ms of silence), or the customer holds a push-to-talk button. Prisma WebSocket streaming was measured with a probe and is not built into the server.

Why:

1. **Streaming is not faster at the same silence threshold.** The wait for silence dominates both paths. Streaming with the server's default 500 ms threshold returned the transcript a median 0.78 s after the end of speech (n = 20). The browser detector at 500 ms plus a REST call comes to about 0.71 s on the same clips (0.485 s detector + 0.224 s STT, both medians, n = 20 each). At 1,000 ms streaming took 1.29 s (n = 6).
2. **A 500 ms threshold cuts a customer who pauses to think.** All 4 clips with a spliced 600 or 900 ms pause came back from streaming as two segments, and both splits changed the text in small ways (section 3). REST returned each as one transcript. The browser detector at 700 ms kept the three 600 ms clips whole and split only the 900 ms one.
3. **REST calls are cached, counted and locked by the shared client.** A replayed call costs nothing the second time, which evaluation needs. Streaming has no cache, its billing is unknown, and it bypasses the client's ledger.
4. **Streaming needs things this repo does not have.** A WebSocket library on the server (not in `pyproject.toml`), resampling to the line rate in the browser, and code that joins segments back into turns.
5. **One path for the phone and for evaluation.** The headless replay tool sends files through the same HTTP route as the phone.

What would change this: human callers who pause longer than 700 ms often enough that turns are cut, or a need for barge-in. Streaming's server-side detector takes `x-min-silence-ms` up to 2,000 `[docs]` and may cope with noise better than an energy threshold. Neither was tested.

## 2. What was built

| Path | What |
|---|---|
| `samajh/server/dialogue.py` | `Dialogue` protocol (`next(call, heard) -> BotUtterance`), `BotUtterance`, `Heard`, `CallView`, and `StubDialogue` (three fixed Hindi questions, each echoing what was heard) |
| `samajh/server/sessionlog.py` | Session log models, `SessionStore`, recording assembly |
| `samajh/server/audio.py` | Untrusted upload in, mono 16-bit WAV at the line rate out (ffmpeg, forced WAV demuxer) |
| `samajh/server/speech.py` | `SpeechClient` protocol, live and patient client profiles, STT and TTS options |
| `samajh/server/errors.py` | The one table that maps client errors to what the phone sees |
| `samajh/server/app.py` | `create_app`, routes, body limits |
| `samajh/server/replay.py` | Headless whole-call runner: library function and CLI |
| `web/` | The phone: `index.html`, `phone.css`, `phone.js` (state machine), `api.js`, `vad.js`, `wav.js`, `capture-worklet.js` |
| `tests/server/` | 183 offline tests, 1 live test, `vad_check.mjs`, `browser_check.mjs` (headless Chrome with a WAV as the microphone), `probes/turn_taking_probe.py` |
| `tests/fixtures/server/stub-call/` | Three 8 kHz Timbre answers (voice Avinash) for the stub call |

### HTTP API

```
GET  /api/health                         never calls Gnani; reports the key as a bool only
GET  /api/clips, /api/clips/{name}       prepared turn audio
POST /api/sessions                       {"dialogue","line_rate":8000|16000,"stt_model","params"} -> first bot utterance
POST /api/sessions/{id}/turns?source=mic|file&reply_to=<bot seq>[&eos_wait_ms=]    body: WAV bytes
POST /api/sessions/{id}/turns?source=none                       nothing was said
GET  /api/sessions/{id}/audio/{name}     bot audio is synthesised on first fetch, then served from the session
POST /api/sessions/{id}/end              hang up
GET  /api/sessions/{id}                  the full event log
GET  /api/sessions/{id}/recording.wav    the whole call as one WAV
```

A turn returns the transcript and the next bot utterance without waiting for Timbre. The phone shows the transcript, then fetches the audio. A failed step is logged as an error event and does not advance the dialogue, so the phone can send the same audio again. `reply_to` names the prompt being answered: a turn sent twice gets the stored reply and advances the dialogue once. Requests for another host name, or from a page of another origin, get 403.

### For the dialogue worker

Implement `Dialogue.next(call: CallView, heard: Heard | None) -> BotUtterance` and register a factory: `create_app(dialogues={"samajh": factory})`, where `factory(params) -> Dialogue` gets the session's `params` (for example a scenario id). One `Dialogue` object serves one call. `heard` is `None` at call start. `Heard(text="")` means nothing was heard. `BotUtterance.tags` is copied to the log untouched (step, asks, product id). The reply to an utterance is transcribed in the utterance's language: `hi-en` becomes `hi-IN,en-IN` on v3.0 and `hi-IN` on v2.5.

### Session log

`.samajh/sessions/<id>/session.json`, `audio/bot-NNN.wav`, `audio/customer-NNN.wav`, `call.wav`. Each customer event holds the audio reference, the transcript (and v2.5's `literal`), the STT model and exact params, cache hit, attempts, estimated credits, and latencies (resample, STT, dialogue, server total, the phone's end-of-speech wait). Each event has two clocks: `at` is wall time since the session was created; `rec_start` and `rec_end` are positions in `call.wav`. The recording joins events in order with 0.5 s of silence between them and carries a SHA-256.

**Prisma Batch over an assembled recording works** (n = 1 call, bot voice Shivani, customer voice Avinash): 8 segments over 37.32 s, the bot as speaker 1 and the customer as speaker 2 in every segment, each customer turn in its own segment, and each customer segment starting within 0.26 s of the logged `rec_start` (5.47 vs 5.46, 13.88 vs 14.14, 25.44 vs 25.70). One bot prompt was split in two at a pause. Batch wrote "loan" and "call" in Latin script where REST wrote "लोन", as the client probe had seen.

## 3. Measurements

Clips: 20 Timbre v3.0 clips at 8 kHz, voices Avinash and Kalpana (the bot is Shivani). 16 single sentences with one amount each (4 Hindi, 4 Hinglish, 4 Tamil, 4 Kannada, the amounts pilot's sentences), 1.8 to 3.2 s. 4 "paused" clips (3 Hindi, 1 Hinglish): two sentences with 600 ms (3 clips) or 900 ms (1 clip) of digital silence spliced between them, 4.3 to 4.9 s. The true end of speech is the last 10 ms frame above -40 dBFS. Gold amounts were fixed before any call. "Amount right" means `samajh.amounts.parse_amount` on the transcript equals the gold rupee value. Script: `tests/server/probes/turn_taking_probe.py`; raw rows in `.samajh/w7/results.jsonl`.

### REST (through the client, key not busy)

| Model | n | STT call, median | max | Amount right |
|---|---|---|---|---|
| prisma-v3.0 `transcribe` | 20 | 0.224 s | 0.349 s | 20/20 |
| prisma-v2.5 `transcribe` | 20 | 0.198 s | 0.547 s | 20/20 |

Each paused clip came back as one transcript on both models.

### End-of-speech detector (`web/vad.js`, run under Node on the same 20 clips plus 2 s of silence)

| Silence threshold | Decision after true end of speech, median (min to max) | Turns cut at the pause |
|---|---|---|
| 700 ms (shipped) | 685 ms (530 to 700) | 1 of 4 (the 900 ms pause) |
| 500 ms | 485 ms (330 to 500) | 4 of 4 |

Start of speech was detected a median 115 ms late; the phone keeps a 300 ms pre-roll, so nothing is lost. What limits this: clean TTS against digital silence. A noisy room will behave differently.

### Streaming (`wss://api.vachana.ai/stt/v3/stream`, prisma-v3.0, 8 kHz PCM in 1,024-byte frames at real-time pace)

Time is from the true end of speech in the clip to the arrival of the last transcript.

| Mode | n | Median | Min to max | Paused clips split | Amount right | Same text as REST |
|---|---|---|---|---|---|---|
| Server decides, default 500 ms silence | 20 | 0.784 s | 0.716 to 0.993 | 4/4 | 20/20 | 12/20 |
| Server decides, `x-min-silence-ms: 1000` | 6 | 1.290 s | 1.275 to 1.362 | 0/3 | 6/6 | 4/6 |
| Client sends `commit` after the last frame | 20 | 0.311 s | 0.178 to 1.031 | 4/4 | 20/20 | 13/20 |
| `commit`, prisma-v2.5 | 6 | 0.363 s | 0.252 to 0.494 | 1/1 | 6/6 | n/a |

- Opening a session took a median 0.19 s (max 0.59 s). The server's own `latency` field was a median 119 ms.
- `commit` is what push-to-talk would use. REST with a known end of speech costs one upload plus the 0.22 s call, so the two are level.
- `commit` does not undo a split: the server had already closed the first segment at the pause.
- Where streaming text differed from REST, most were spelling and format (`loan` for `लोन`, `52,000` for `52000`, `1,50,000` for `1.5 लाख`, a full stop at the split). Two were word errors: `पियम` for `प्रीमियम` at the start of a clip (both modes), and `आपका` for `उसका` after a split. n = 1 each.
- Sending a clip as fast as the socket takes it also worked (n = 4, same text as paced, transcript 0.18 to 0.58 s after the first frame). The docs say not to do this.

### Phone, end to end (headless Chrome, a WAV file as the microphone, real server, real Prisma)

Hands-free microphone turns: 48 kHz capture, detector, WAV upload, server resample to 8 kHz, prisma-v3.0. The clips are five of the 48 kHz Timbre clips and one stub answer, each played into the fake microphone at two offsets. The time is the phone's own figure: from the last voiced frame to the transcript arriving in the page.

| Run | n | End of speech to transcript, median (min to max) | Detector wait | Resample | STT step, median | Failed |
|---|---|---|---|---|---|---|
| After the review fixes, key lightly used | 12 | **1.18 s** (1.09 to 1.26) | 702 to 708 ms | 83 to 120 ms | 346 ms (278 to 406) | 0 |
| Before, while another worker's evaluation used the key | 12 | 1.2 to 4.2 s on the 8 uncached turns | 702 to 706 ms | 46 to 74 ms | lock wait median 470 ms (max 1,030), Prisma median 427 ms (max 2,374) | **3 (`gnani_busy`)** |

- The STT step includes the wait for the key lock, so it is higher than the 0.22 s of the quiet REST pass. The key was never idle during either run.
- In the second row the lock was not free within the live profile's 5 s on 3 turns. The phone showed the code and message and offered "Send again". One further turn was a cache hit and showed 0.77 s.
- The Hindi and Hinglish clips were transcribed with the right amount in every successful turn. The Tamil and Kannada clips were only timed: the stub asks in Hindi, so they were transcribed as `hi-IN`.
- Expected with the key idle, from the parts measured separately: 0.685 + 0.09 + 0.224 ≈ 1.0 s. Not measured as one number.

### 8 kHz against 16 kHz

Five 48 kHz Timbre clips (2 Hindi, 1 Hinglish, 1 Tamil, 1 Kannada) resampled by the server to each line rate, prisma-v3.0: the transcripts were identical at both rates, 5 of 5. On clean TTS the phone-line rate costs nothing visible. Resampling took 43 to 66 ms.

### Failure behaviour

| Case | Result |
|---|---|
| Another process holds the key lock | 503 `gnani_busy`, `retryable`, after 5.15 s. Error event logged with the customer audio. Sending again after release: 200 in 0.31 s |
| Two calls answer at the same instant, uncached | Both 200, no 429. STT step 574 ms and 827 ms: the second waited for the first |
| Gnani host unreachable or silent, live profile | `TransportError` after 12.3 s (2 attempts of 6 s). The lock is held that long. Run with a private state directory so the shared lock was not touched |
| Upstream answers, then sends one body byte every 4 s | Lock held 16.3 s with the server's total deadline (8 s per attempt). 96.4 s before the fix (reviewer's repro, local fake upstream) |
| The same turn posted three times at once | 409 `turn_in_progress` twice, 200 once; the dialogue advanced once |
| A turn sent again after its reply was lost | 200 with the stored reply; no second STT call |
| Request with `Host: evil.example`, or `Origin` of another site | 403 `host_not_allowed`, 403 `foreign_origin` |
| 244-byte WAV declaring 100 MHz; MP3, AAC, FLAC or ADPCM inside a WAV | 422 `audio_unreadable` before ffmpeg starts |
| Upload over 6 MiB | 413 `audio_too_large`, with or without `Content-Length` |
| Microphone refused | The call runs in file mode and says so (checked in headless Chrome) |
| Streaming, `language_code: hi-IN,en-IN` on v3.0 | `error` "exactly one locale is required ... Use multi_lang_codes", then close 1008. 13 of 13 attempts. **The docs say v3.0 takes 1 to 4 codes.** REST accepts the list |
| Streaming, no `language_code` | `error`, close 1008 |
| Streaming, no audio, `x-idle-timeout-sec: 5` | `error` at 5.2 s, then `session_end` (`idle_timeout`), close 1001 |
| Streaming, 3 s of digital silence then `commit` | No message at all within 3 s. A client must time out on its own |
| Streaming, socket dropped mid-utterance | Nothing to observe from the client. Whether it was billed is unknown |

## 4. Evidence

Final runs on the fixed code:

```
$ uv run pytest tests/server -q
183 passed, 1 deselected, 1 warning in 4.53s
$ uv run pytest tests/server -m live -q
1 passed, 183 deselected, 1 warning in 0.17s
$ uv run ruff check samajh/server tests/server
All checks passed!
$ uv run ruff format --check samajh/server tests/server
21 files already formatted
```

The warning is Starlette deprecating httpx under its `TestClient`. The live test took 8.35 s on its first run, when it made 3 real Prisma calls and 4 real Timbre calls; the run above replayed them from the cache. After the fix round the real network path was exercised again by the 12 uncached browser turns in section 3 and by one uncached Timbre call (0.65 s) and Prisma call (0.25 s) through the server's client.

Secret scan after all runs: 272 files under `samajh/server`, `web`, `tests/server`, `tests/fixtures/server`, `references/pilots`, `.samajh/sessions` and `.samajh/w7`; none contains the key or its first 16 characters.

One full stub call through the real HTTP API of a running server, from prepared audio:

```
$ uv run python -m samajh.server --port 8085 &
$ uv run python -m samajh.server.replay tests/fixtures/server/stub-call --url http://127.0.0.1:8085
session 20261110T032339-b41b3f41b032  dialogue stub  line 8000  prisma-v3.0 transcribe  timbre-v3.0 Shivani
status ended (dialogue)  recording call.wav 37.32 s, 8000 Hz, gap 0.5 s, sha256 7403f802...
0 bot       rec 0.00-4.96    नमस्ते। यह समझ की परीक्षण कॉल है। आपने कितने रुपये का लोन लिया था?
1 customer  rec 5.46-7.78    file  hi-IN  "मैंने 5,00,000 रुपये का लोन लिया था।"
2 bot       rec 8.28-13.64   मैंने सुना: मैंने 5,00,000 रुपये का लोन लिया था। आपकी हर महीने की किस्त कितनी है?
3 customer  rec 14.14-17.18  file  hi-IN  "हर महीने की किस्त 11,500 रुपये है।"
4 bot       rec 17.68-25.20  मैंने सुना: ... लोन के साथ आपने और क्या लिया, और कितने का?
5 customer  rec 25.70-30.02  file  hi-IN  "बस एक FD ली थी loan security के लिए 52,000 की।"
6 bot       rec 30.52-37.32  मैंने सुना: ... धन्यवाद। यह कॉल अब समाप्त होती है।  (end_call)
```

Every Gnani call in that run was a cache hit (0 credits, STT step 0.5 to 1.7 ms), because the live test had made the same calls minutes earlier. That is the rerun behaviour evaluation needs. The uncached figures are in section 3.

## 5. Claims

**Verified live:** the streaming protocol as used (upgrade headers, 1,024-byte PCM frames, `commit`, `speech_start`, `transcript`, `x-min-silence-ms`, `x-idle-timeout-sec`, close codes 1008 and 1001, a `session_end` message the docs do not list); streaming rejects a comma-separated `language_code`; REST accepts it; Batch segments an assembled recording at the 0.5 s gaps.

**Read in the docs, not exercised** `[docs]` (docs.gnani.ai `stt-websocket.md`, `limits.md`, read 2026-11-10): 15-minute session limit; `x-vad-threshold`, `x-min-speech-ms`, `x-max-speech-s`; `update_settings`; a per-organisation session cap with no number given; handshake 402 and 429.

**Still unknown:** how streaming is billed (61 sessions and 234 s of audio were sent; the ledger books them at the REST rate under `stt.stream`); `multi_lang_codes` on streaming; every behaviour on human speech.

## 5b. Independent review

A Fable reviewer at high effort, which did not write the code, ran offline against a fake Gnani client and a local fake upstream.

**Held:** no route returns the key (44 raw-socket paths including `/.env` and encoded variants; an upstream that echoes the key in its error bodies; logs, ledger, cache and stdout). No path traversal through session ids, audio names, clip names or symlinks. The byte limits hold with and without `Content-Length` (300 MiB chunked gives 413 with flat memory). The 30 s limit holds (30.0 s accepted, 30.001 s refused). The event loop stays responsive during a slow turn (a GET answered in 4 ms). Eight simultaneous fetches of one prompt make one Timbre call. 40 random calls of 25 operations broke no log or recording invariant.

**Proven and fixed** (each has a test or a rerun of the reviewer's script):

1. A turn sent again after a lost reply advanced the dialogue twice. Fixed with `reply_to` and one upload per call at a time.
2. The live timeout was per socket operation: a dripping upstream held the key lock 96.4 s. Fixed with a total response deadline in the server's client (16.3 s on the same script).
3. A 244-byte WAV declaring 100 MHz cost ffmpeg 4.2 s and up to 820 MiB. Fixed: the header is checked before ffmpeg, and at most two ffmpeg processes run at once.
4. A WAV with a false `block_align` was logged as 0.001 s and passed the credit cap and the 30 s limit. Fixed: the pass-through pins every header field.
5. Fetching a prompt repeatedly while Timbre failed filled the log until the call hit its turn limit. Fixed: a repeated TTS error is logged once.
6. Turn bodies were buffered before the session lock with no deadline. Fixed: one upload per call, 20 s to arrive, `limit_concurrency=32` in uvicorn.
7. No Host or Origin check, so a web page in the same browser could create sessions. Fixed. A finished call is now dropped from memory before one in progress.
8. Microphone permission granted after a hang-up attached a dead track to the next call. Fixed.
9. `eos_wait_ms` grew by the time spent on an error screen. Fixed: measured once.
10. The upload could choose a non-PCM decoder inside a WAV. Fixed: PCM only.
11. `replay` left a failed call marked active, and a prompt fetched after a hang-up was synthesised. Fixed both.

**Suspected by the reviewer, not proven on a microphone:** steady room noise above the threshold produces a noise-only turn on every turn. Changed anyway: the noise estimate now carries from one turn to the next (capped), tested on synthetic noise. The first turn in a noisy room can still misfire.

**Not fixed:** the time to the response headers is bounded only by the 6 s per-operation timeout (the fix belongs in `GnaniClient._api`); DNS resolution is probably outside that timeout (reviewer's suspicion, not measured); there is no cap on the number of sessions written to disk. The fix round was checked by its tests, by rerunning the reviewer's scripts and by my reading, not by a second independent review.

## 6. Not verified, gaps, and changes from the spec

- **No human used the phone.** Real microphone, real speaker, a human voice, echo from speaker to microphone, Safari, Firefox and phones are untested. Chrome was driven headless with a file as the microphone.
- **The detector was tuned and tested on clean audio only.** Steady noise above the threshold produces one false turn before the floor adapts (builder's test).
- **Latency in the browser was never measured on an idle key.** Other workers used it throughout.
- **Changed from the spec: no backend WebSocket proxy was built.** The streaming measurements come from a direct probe. A proxy would add one local hop and would not change the comparison. Streaming is not kept in the server.
- **Changed from the spec: the server resamples, not the browser.** The phone uploads what it captured and the server writes the 8 or 16 kHz line audio with ffmpeg. One resampler serves the microphone, uploads and replay, and a prepared 8 kHz clip keeps its bytes and its cache key.
- **Live turns can fail when another process is busy on the key.** The live profile waits 5 s for the lock. An evaluation run on the same machine will make a demo call stall or fail.
- **Worst-case lock hold for one live turn is about 12 s on a dead network and 16 s against a dripping body** (both measured), against about 4.5 minutes at the client's defaults.
- **Changed from the spec: `reply_to` on a turn, and a Host and Origin check.** Both came from the review. `--allow-host NAME` admits another host name, for a phone on the LAN.
- **The server has no authentication.** It binds 127.0.0.1 and refuses other host names and origins. Any local process can still spend credits up to the client's cap.
- **Sessions on disk are never deleted.** At most 64 calls are live in memory; older ones stay readable and cannot be continued.

## 7. Spend

About 10 estimated credits of a 40-credit budget: Timbre clips and prompts 4.1, REST probes and comparisons 1.5, streaming 2.3 (booked at the REST rate; true cost unknown), browser and replay turns 1.0, the live test and one Batch job 1.2. These are estimates at the client's rates: the ledger does not separate workers, and it stood at 114 credits for the whole project when this was written. OpenRouter: none.

## 8. Next

1. Record human turns and rerun the detector and the phone path on them. Decide the 700 ms threshold on that data.
2. Keep evaluation jobs off the key while a live demo runs, or give live calls priority in the client's lock.
3. Read the dashboard for the streaming line to settle its billing.
4. The dialogue worker registers its `Dialogue`; read-backs of heard amounts are synthesised on the turn path (about 0.7 s of Timbre), fixed prompts are cache hits.
5. If turns are cut on human speech, test streaming with `x-min-silence-ms` near 1,000 before building a proxy.

## 9. Documents this makes stale (not edited: outside W7's paths)

- `CLAUDE.md` line 27, "v3.0: `indic-auto` and comma-separated language lists work": true for REST only. Live, the streaming endpoint rejects a comma-separated `language_code` on v3.0 with "exactly one locale is required" and close 1008 (13 of 13 attempts), although the docs allow 1 to 4 codes.
- `CLAUDE.md` line 28, "WebSocket streaming (`/stt/v3/stream`) is reachable (probed, not built)": now measured against REST and still not built into the server; point to this file.
- `CLAUDE.md` "Files": add `samajh/server/` (voice transport), `web/` (browser phone) and this report.
- `DESIGN.md` line 70 and open decision 12 (line 327), "Whether to adopt [streaming] for iteration 2 is open": decided here. REST per turn; streaming not adopted; the reasons are in section 1.
- `README.md` line 18 and line 23 ("No end-to-end run exists yet"), and `ORCHESTRATION.md` line 80 (W7 "In progress") and line 86 ("W7 not yet reported"): W7 is done; a full stub call runs end to end through the HTTP API and in a headless browser; W7 used about 10 estimated credits.
