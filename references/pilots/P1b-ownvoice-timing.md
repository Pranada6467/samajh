# Own-voice turn-taking: two practice calls on 2026-11-10

Saved by the P1b sub-orchestrator from a measurement worker's final message (Opus medium), lightly trimmed. **Not independently verified.** Read-only analysis: no setting was changed, no Gnani or OpenRouter call was made, and the audio stays in `.samajh/sessions/` on the user's machine.

**Scope.** One speaker, 2 calls, one room, one microphone, one day: 20 microphone turns in all. No rate here generalises. Any setting suggested below is a starting point for the next human calls; it has not been checked on anyone else.

## Calls

- **Call 1 (`20261110T111501-cfb03ade882d`)**: hero record, hi-en, 4 customer turns, all from the microphone, hands-free (`phone.mode = vad` on every turn). It ended in a hang-up at the birth-year re-ask.
- **Call 2 (`20261110T112446-f7770ec63c07`)**: 16 customer turns, all microphone, hands-free. Outcome `completed`.
- No turn in either call had a part 2, a superseded event or an error event.
- Turns by question kind: yes_no 6, short 2 (both birth year), amount 1, open 11.

## How it was measured

Each saved customer WAV (8 kHz) was split into 20 ms frames and the RMS of each frame taken, under three thresholds: **A** the server's own rule (3 × the clip's 10th-percentile frame, floor 0.004); **B** a fixed −45 dBFS; **C** the clip's 10th-percentile frame plus 12 dB. `web/vad.js` was also ported to Python and run on the same frames with the cut in force; on every turn its last voiced frame matched the phone's within one frame (inferred from where the clip ends, since the phone keeps 200 ms after the last voiced frame).

Two built-in limits on the audio:

- The phone stores only 200 ms after its last voiced frame (`TAIL_MS`). Trailing silence in a saved turn therefore cannot show a late cut, and the audio after a cut is never kept.
- Any pause longer than the cut would end the take, so the pauses seen inside turns are censored at the cut.

## Cuts by question kind

Rules: **late** = the detection wait is more than 50 ms above the cut; **early, recovered** = a part 2 exists.

| Kind | cut / grace (ms) | n | Early, recovered | Early, lost | Late | Fine | Can't tell | Longest pause inside an answer (A / B / C, ms) |
|---|---|---|---|---|---|---|---|---|
| yes_no | 700 / 1000 | 6 | 0 | 0 | 0 | 6 | 0 | 40 / 80 / 60 |
| short | 800 / 1200 | 2 | 0 | 0 | 0 | 1 | 1 | **620** / 560 / 540 (the birth-year answer) |
| amount | 1000 / 1600 | 1 | 0 | 0 | 0 | 1 | 0 | 60 / 0 / 0 |
| open | 1100 / 1800 | 11 | 0 | 0 shown | 0 | 10 | 1 | 160 / 80 / 180 |

The detection wait always matched the cut: 701 to 709 ms for yes_no, 801 for short, 1003 for amount, 1101 to 1106 for open. The extra is encoding time.

Two turns could not be classified:

- **Call 2, turn 23 (open, the longest answer, 4.5 s of continuous speech).** The audio ends while the user is still making sound at speech level: zero trailing silence under all three thresholds, and the last 200 ms sit at −29 dBFS against a −49.5 dBFS floor. The ported detector's threshold had climbed to −24 dBFS by then (it peaks around −34 to −37 on short turns): the noise estimate rises during long voiced runs (it doubles every 4 s), so quieter speech at the end of a long answer reads as silence. The live transcript and the Batch transcript end on the same words, which can be a complete sentence, and the next turn is a plain answer to the next question. **The cut came while the user was still sounding; whether words were lost cannot be told**, because the audio after the cut is not kept.
- **Call 1, turn 7 (birth year).** A 280 ms sound peaking at −26.5 dBFS; the v3.0 reading and Batch both returned no words; no resumption within the 1.2 s grace window. The bot re-asked and the user hung up. A non-speech sound, or the start of an answer that resumed after the grace window: it cannot be told.

## Latency parts (ms, microphone turns)

| Part | Pooled n | Pooled median / p90 / max | Call 1 median (n=4) | Call 2 median (n=16) |
|---|---|---|---|---|
| Detection (`eos_wait_ms`) | 20 | 1,101 / 1,104 / 1,106 | 704 | 1,101 |
| Decode + resample (ffmpeg subprocess) | 20 | 111 / 154 / 191 | 84 | 114 |
| STT primary (v3.0); API time alone | 20 | 356 / 462 / 507; 206 / – / 366 | 290 | 365 |
| STT second (v2.5) | 1 | 426 | – | 426 |
| Dialogue, word lists (≤300) | 11 | 4 / 17 / 25 | 1.6 | 4 |
| Dialogue, classifier consulted (>300, inferred) | 9 | 1,121 / 2,310 / 2,515 | – | 1,121 |
| Server total | 20 | 804 / 1,924 / 2,970 | 375 | 1,247 |
| TTS of the reply (`synth_ms`), all lines cached | 5 | 8 / 10 / 12 | – | 8 |
| TTS of the reply, some lines made on the call | 15 | 1,245 / 3,559 / 5,350 | 2,146 | 1,245 |
| Speech end to reply audio ready (modelled) | 20 | 3,441 / 5,474 / 6,665 | 3,303 | 3,441 |

The last row is modelled, not logged: max(grace, detection + server) + the reply's `synth_ms`. The phone's own `bot_start_ms` is never sent to the server. The model leaves out network time, WAV decode and output latency.

Slowest five turns (modelled total; detection / server / TTS):

- Call 2 turn 7, short: 6,665 (801 / 514 / 5,350; three lines made on the call).
- Call 2 turn 29, open: 5,803 (1,101 / 2,970 with dialogue at 2,515 / 1,732).
- Call 2 turn 19, open: 5,438 (1,103 / 2,753 with dialogue at 2,258 / 1,581).
- Call 1 turn 3, yes_no: 4,959 (701 / 382 / 3,876; four lines made).
- Call 2 turn 9, open: 4,777 (1,101 / 1,719 with dialogue at 1,121 / 1,958).

Check of an earlier pass's three figures: detection median 1,101 **reproduced** (1,100.7 pooled, n = 20). TTS median 1,074 **reproduced only on that pass's count** (1,073.7 is the median of call 2's 16 reply events; over the 20 replies to microphone turns it is 1,151). TTS max 5,350 **reproduced**. Dialogue max 2,515 **reproduced**.

## What limits each part

- **Detection is the cut setting itself.** The phone sends the take at the cut. The bot then waits for the grace window or the server, whichever finishes later. The server took longer than the grace window's leftover time (grace minus cut) in all 6 yes_no turns, in 9 of 11 open turns and on the amount turn: on those turns a shorter grace saves nothing, a shorter cut would.
- **TTS is lines missing from the cache.** 22 of 35 bot lines were made during the calls (median 1,043 ms each, max 2,127). Every line call 1 spoke was a miss; the same lines were cache hits in call 2, nine minutes later. So the pre-made cache does not hold the current wording. A reply's lines are made one after another (one request at a time on the account), so a three-line reply costs about three Timbre calls.
- **Dialogue time is the LLM turn classifier.** The log has no field saying it was consulted; it is inferred from times over 300 ms: 9 of the 11 open turns in call 2. Its wall-clock limit is 2.5 s (`TIMEOUT_S` in `samajh/dialogue/llm_fallback.py`; the settings' 3.0 s is the client's timeout). Turn 29 hit that limit and is in `degraded_turns`.
- **STT** is about 206 ms at Gnani plus about 150 ms in the client (lock, cache, ledger); decoding costs another 110 ms or so for the ffmpeg process.

## Recommendations (not applied)

1. **yes_no: try a 600 ms cut.** Basis: n = 6 short answers, longest pause under 100 ms. Against it: the TTS test in the P1 report had a 600 ms pause inside an answer. Grace does not matter here; the server finishes after it anyway.
2. **short (birth year): raise the cut to about 1,000 ms.** Basis: the one spoken year had a 620 ms pause mid-year, 180 ms under the 800 ms cut. n = 1.
3. **open: no pause came near the cut** (11 turns, longest 180 ms). A 900 ms cut would save about 200 ms per turn, but this speaker knew the script: weak evidence. The 1,800 ms grace held up the reply in 2 of 11 turns.
4. **amount: no evidence** (n = 1).
5. **Larger savings than any cut or grace change:** rebuild the fixed lines once the wording is final (`uv run python -m samajh.server.prompts build --lang hi --lang hi-en`): the 15 turns with lines made on the call would save about 1.2 to 5.3 s each. Reduce or speed up the classifier on open questions (about 1.1 s median, up to 2.5 s, on 9 turns). Look at the detector's noise creep on long answers (basis: one turn plus a Python port of `vad.js`, not tested in a browser).

## Not determined

- The real speech-end-to-bot-audio time: the phone's `bot_start_ms` is not logged on the server.
- Whether anything was said after a cut: audio past the 200 ms tail is not kept.
- Whether the classifier was consulted on fast turns (a cache hit or the word lists).
- Pause behaviour near or above each cut: no take was ever resumed, so there is no part 2 to measure.
- Push-to-talk: not used in either call.

Script: `analyse.py` in the measurement worker's scratchpad (numbers only, no audio); not in the repo.
