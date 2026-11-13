# P1 report: one real Samajh call, end to end, on the browser phone

2026-11-10. TTS audio only: no person has spoken to this phone. Artifacts: `references/pilots/p1-artifacts/`. Redacted on 2026-11-13 to the rule now in the code (P8, `samajh/server/casefile.py`): in `hero`, `informed` and `informed-run1` the reply to the year-of-birth question (customer turn 12) reads `[reply to the year-of-birth question: withheld]` in its text and readings (literal null) and carries `"withheld": true`, and the one Batch segment overlapping it keeps its timing with its text withheld; the three `*-summary.json` files and `browser/browser-hero.json` withhold the same reply's transcript and readings. Timings, audio offsets and every other field are as recorded; `third-party` never reached the question. No call was rerun.

## 1. What works

- **Protocol and adapter** (`samajh/server/dialogue.py`, `samajh_dialogue.py`; done by earlier workers, kept). A bot utterance is an ordered list of lines, each its own cached Timbre clip; a line over 600 characters is split at sentence ends. A turn carries two readings: Prisma v3.0 `transcribe` always, and v2.5 `transcribe` when the dialogue expects a figure, with a 2.5 s bound (late or failed counts as `""`, a disagreement). Registry: `samajh` is the default, `stub` stays for tests. A turn is keyed by `(reply_to, part)`: a repeated or concurrent request gets the stored reply, and the log plus the dialogue state are one atomic file, so a call resumes after a restart. The LLM fallback client has a 3 s timeout and one attempt.
- **Bot audio.** Timbre v3.0 at 8 kHz. `uv run python -m samajh.server.prompts build --lang hi --lang hi-en` made 101 fixed lines (13.06 estimated credits); read-backs are made on the call. Voice is configuration (`settings.toml [tts.voice]`): Shivani for every language, because she is the voice this project has run end to end and Batch separated her from the male customer voice in every call here. Nobody has compared voices by ear.
- **End of speech** (`web/phone.js`). Cut and grace come from the bot's `listen` kind (yes/no 700/1000 ms, short 800/1200, amount 1000/1600, open 1100/1800). At a cut the take is sent at once; if the customer resumes within the grace window the phone keeps every sample and sends the whole answer as part 2, which supersedes part 1 on the server. Push-to-talk stays. Pause statistics are logged per turn.
- **After the call** (new `samajh/server/casefile.py`; `POST`/`GET /api/sessions/{id}/case`). A background thread closes the call, then runs: transcript, recording (sha256), Prisma Batch (v3.0, 2 speakers), alignment of each customer turn to the segments it overlaps, extraction and rules (`samajh.pipeline.run_text`, parallel requests), `samajh.rules.summarise`. The case file holds the tier and summary, every flag and gap with its quote, turn id and audio offset, both readings of each figure turn and whether they agreed, every model and parameter, and per-turn latencies. A failed step is named; the case is then `failed` and the phone shows what failed, never a tier. A job left `running` by a stopped server is restarted by the next request; a failed one reruns on request.
- **Replay** (`samajh/server/replay.py`, rewritten). Drives a call from `DIR/call.json` (record, language, turn files, the line key each turn answers) to `OUT/case.json`. Resumable with `--out`; stops with `script_drift` if the bot asks something the script did not expect. `samajh/server/prepare.py` voices a persona against the dialogue as it is, with Timbre customer voices; fixtures in `tests/fixtures/server/calls/` (1.1 MB of 8 kHz WAV at the time). At the time of this report there were three personas: `hero` and `informed` (Avinash), `third-party` (Shubham). Since then (iteration 3, commit 2568759) there are four: `amount-check` (Kalpana) was added, and a persona carries its own right-party setting (`samajh.identity.IdentityPolicy`, sent as the session's `identity`): `hero`, `informed` and `third-party` run under the server's default (no second check, so no year-of-birth question is asked), and `amount-check` runs under the year of birth with one attempt, so the packaged calls exercise both settings. A loan-book loan has its own persona (`--loan`). No persona answers the direct question or the who-check, so the replays do not exercise those rules (`P2-report.md` section 8).
- **Phone**: record and language picker, takes, case panel, per-turn readings and "speech end to bot" time.

## 2. Evidence

`uv run pytest tests/server -q`: 310 passed, 1 deselected (the live test). `uv run pytest tests/server/test_live.py -m live`: 1 passed (the third-party call to a ready case file, cached). `ruff check` and `ruff format --check` on `samajh/server tests/server`: clean.

Three calls through the real HTTP API (`uv run python -m samajh.server.replay tests/fixtures/server/calls/<p> --url http://127.0.0.1:8085 --out references/pilots/p1-artifacts/<p>`), on the dialogue as committed before P2:

| Call | Language | Turns | Outcome | Case | Summary lines |
|---|---|---|---|---|---|
| hero (misled) | hi | 15 | completed | ready, **refer** | kind (FD vs insurance), no consent on record, required/no provider choice, feature (withdraw with interest); understanding gap: cancel window, cover |
| informed, run 1 | hi-en | 15 | completed | ready, **refer** | "agreed by word of mouth only", quoting "loan form पर sign किया था, insurance के लिए भी अलग से हाँ की थी" |
| informed, run 2 | hi-en | 15 | completed | ready, **clear** | none |
| third party | hi | 1 | wrong_party | ready, incomplete | undecided questions; the lender and loan were never named |

Run 1 of the informed call is an extractor reading of an ambiguous persona line ("हाँ की थी"); I changed that one line to name the form and reran. Both are kept. Every reading was a cache miss in the hero, informed run 1 and third-party calls (35 readings). In all four calls the Batch speaker with the most overlap was the customer's speaker for every customer turn; Batch segment edges fell within 0.09 s of the logged turn edges.

**Headless Chrome, whole call** (`node tests/server/browser_check.mjs ... --query "record=hero&lang=hi&mode=hands-free" --case`): the first answer came from a 48 kHz WAV as the microphone with an 860 ms pause inside ("हाँ जी, … बोल रहा हूँ"); the phone sent part 1 at the cut, heard the resumption, sent part 2, and Prisma read the whole answer. The other 14 turns were clips through the picker. The case reached `ready`, tier `refer`, same five lines as the replay. Screenshots: `p1-artifacts/browser/hero*.png`. Pause runs on the yes/no question (cut 700, grace 1000): 0 ms and 600 ms pauses whole in one take; 860 ms whole in two takes; **1300 ms lost the second half** (only "हाँ जी।" was heard), because the bot answers once the grace window passes and the phone does not listen while it speaks.

**Latency, end of customer speech to start of bot audio** (n = 31 uncached turns of the hero, informed run 1 and third-party replays, plus 4 microphone turns in Chrome):

| Part | Source | n | median | p90 | max |
|---|---|---|---|---|---|
| Detection: last voiced frame to upload | Chrome, yes/no question | 4 | 702 ms | | 704 ms |
| Bot may not start before the grace window | settings | | 1,000 ms (yes/no) to 1,800 ms (open) | | |
| STT, both readings | server log | 31 | 364 ms | 569 ms | 1,632 ms |
| Dialogue, word lists only | server log | 16 | 1 ms | 2 ms | 70 ms |
| Dialogue, LLM fallback consulted | server log | 15 | 1,398 ms | 1,753 ms | 2,237 ms |
| TTS of the reply, fixed line (cached) | server log | 29 | 3 ms | | 15 ms |
| TTS of the reply, read-back (made on the call) | server log | 2 | 1,382 ms | | 1,442 ms |
| Whole turn in Chrome, speech end to bot audio | page | 4 | 1,145 ms | | 1,254 ms |

The fallback (Mistral small, 16 uncached calls) was consulted on 15 of 31 turns, including plain answers such as "दो साल": with an open question's 1.8 s grace it hides behind the window only when it ends within about 0.7 s of the cut. The Chrome figures are yes/no turns only; no open or amount question was answered by microphone.

## 3. Not verified with a human at a microphone

Everything. No person has spoken to the phone: every customer turn is Timbre audio, the microphone turns are a WAV fed to headless Chrome, and no turn was played through a speaker into a microphone (echo, rooms, phone lines untested). The cut and grace values are guesses with per-turn pause statistics now logged so they can be set on human audio. Nobody has listened to the bot's voice or the read-back of "52,000".

## 4. Blocked on the other packages

- **P2 is mid-flight** (91 of its dialogue tests fail in the shared tree). The calls above ran on the committed dialogue. P2 adds lines (`read_back.confirm_about`, `payment_frequency.ask`, ...) and moves the read-back after the premium, so the committed `call.json` scripts will now stop with `script_drift`. When P2 lands: `uv run python -m samajh.server.prompts build --lang hi --lang hi-en` (about 1.5 credits of new lines) and `uv run python -m samajh.server.prepare <persona> tests/fixtures/server/calls/<persona>` for each persona, then rerun the replays. The adapter needed no change for P2's new keys or outcomes.
- The `tier` and `summarise` of P3a are used as published; nothing else is assumed.

## 5. Credits and spend

Gnani ledger estimate 251.54 at the start, 274.08 at the end: at most 22.5 credits, which includes other builders' calls in the same window (my own: about 13 for the bot lines, 2 for the customer voices, 5 for five Batch jobs, the rest STT). OpenRouter: below USD 0.10 for my calls (the ledger rows are shared with the amounts evaluation).

## 6. Document lines made stale

- `CLAUDE.md` line 59: "(`dialogue.py`, with a three-question `StubDialogue`)" and "**The server still runs `StubDialogue`: the adapter to `samajh.dialogue` is not written.** It is the place that must fetch ... a short timeout." The Samajh dialogue is the default; the adapter does all of that.
- `CLAUDE.md` line 59: "REST STT per turn, 700 ms end-of-speech detector in the browser" (now cut and grace per question kind, `settings.toml`).
- `CLAUDE.md` line 63: "183 offline tests and 1 live test" (310 offline, 1 live).
- `CLAUDE.md` line 64 and `README.md` line 48: `uv run python -m samajh.server.replay tests/fixtures/server/stub-call --url ...` (the stub now needs `--dialogue stub --no-case`; the Samajh call is `tests/fixtures/server/calls/hero --out OUT`).
- `README.md` lines 13 and 45 and line 85 ("not connected to the phone"); `DESIGN.md` line 406 ("Dialogue: not connected and not voiced. The phone still runs `StubDialogue`"); `DESIGN.md` lines 70 and 436 ("browser end-of-speech detector at 700 ms").
- `ORCHESTRATION.md` line 84: "Not connected to the phone, which still runs `StubDialogue`".
