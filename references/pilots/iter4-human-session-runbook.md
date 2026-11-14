# Human sessions runbook (iteration 4, for 2026-11-15)

The commands for a day of human calls on the browser phone and a batch of WhatsApp voice notes, in order. Everything a person says stays under `.samajh-human/` (gitignored). Never copy anything from there into the repo. Cards, gold and the call log are described in `.samajh-human/cards/gold/INDEX.md`.

## 0. Before the first call (5 minutes)

```sh
uv run python -m samajh.clients.gnani ledger     # note est_credits_spent: the day's spend is the difference at the end
uv run pytest tests/server tests/human -q         # must pass
```

Start the server with the card records, on a state directory of its own for the day, so that the day's sessions sit together and inside `.samajh-human/`:

```sh
SAMAJH_RECORDS_DIR=.samajh-human/cards/records \
  uv run python -m samajh.server --port 8085 --state .samajh-human/state/2026-11-15
```

The Gnani lock, cache and ledger stay under `.samajh/` whatever `--state` is, so the one-request slot is still shared. Do not run any evaluation while a call is live.

Open `http://127.0.0.1:8085/` in Chrome, open the developer console (View → Developer → JavaScript Console) and keep it open on the first call (section 2).

## 1. Each call

1. Pick the card's record in the "Demo records" group (never a "Synthetic loan book" loan), the language the speaker will use, right-party setting None, hands-free mode.
2. Run the call. The phone builds the case file after the call by itself (Prisma Batch plus extraction: it costs credits and a little OpenRouter).
3. Copy the session id from the phone's monitor panel ("Session") into a new row of `.samajh-human/call-log.csv`: `date,time,card_id,speaker_initials,language,setup,session_id,note`. A repeat of a card is a second row with the same card id. The scorer joins calls to gold through this file only: a call with no row shows as "no card".

## 2. On the first call: three things to look at in the browser console

No agent has opened the phone in a browser since these changes, so check these by eye once:

1. After each of your answers a line `[samajh] customer N: takes=1 grace_used=false marks=K ...` appears, with K > 0 in hands-free mode, and no `[samajh] report for event N refused` or `not sent` warning. A refused report means the server rejected the phone's measurements (the call itself is unaffected).
2. When each bot reply starts, a line `[samajh] bot N: bot_start_ms=... played_ms=... completed=true talk_over=T` appears. `bot_start_ms` should be a few thousand ms (the time from the end of your speech to the bot's first sound). Stay silent through one whole bot prompt: `talk_over` should be 0. If it is above 0 while nobody spoke, the bot's own echo is being counted, and talk-over numbers from that setup must be reported as "echo included".
3. While you speak, pause once for about half a second without stopping, then finish. That turn's line should show `marks` larger than for a one-breath answer (the pause is marked), and `takes=1`. Once, on an open question (cut 1.1 s, grace 1.8 s in `settings.toml`), pause about 1.5 s mid-answer and go on: you should see `takes=2 grace_used=true`, a split utterance the scorer counts. A pause longer than the grace window ends your turn instead.

To see everything stored for a call, open `http://127.0.0.1:8085/api/sessions/<session_id>`: each customer event has `browser`, `classifier`, `state_before`, `state_after`; each bot event has `browser`.

## 3. End of the day: score the calls

```sh
uv run python -m samajh.human score \
  --sessions .samajh-human/state/2026-11-15/sessions \
  --cards .samajh-human/cards --log .samajh-human/call-log.csv \
  --out .samajh-human/reports/2026-11-15-score.md
```

What the report says, section by section:
- **Head:** how many sessions and counted turns; how many turns are mic (human speech) and file (TTS clips). Only mic turns say anything about human callers.
- **Sessions:** per call the card, outcome, tier, the card's expected outcome and tier, `match`, `void`, and the gold grounds the case's flags matched (`k of n`, the missing rule ids, rule ids in the gold that are not engine rules as `unmappable`, and flags the gold does not list as `extra`). For third-party cards, `loan named` says whether any line about the loan was spoken.
- **Counts per 100 by kind of customer:** one block per gold class, rows adding up to n, each with k/n and a 95% Wilson interval. Void sessions are left out and counted on their own. There is deliberately no pooled rate; never compute one from this table. With a handful of calls per class the intervals are wide: report them as they are.
- **Void rate:** sessions with a degraded turn (the classifier failed or ran out of time). Index rule: a void call is listed apart and never redone.
- **Latency:** median, p90 (nearest rank) and max with n for `bot_start_ms` (browser, end of speech to first bot audio), the end-of-speech wait, primary and second STT, the classifier, the dialogue, the server, and TTS per line split into pre-made lines and lines synthesised during the call. The classifier label tally follows.
- **STT health:** retried readings, failed readings by error, HTTP status per model, and the ledger's per-attempt statuses (504s) joined by `cache_key`.
- **Pauses:** pause lengths inside mic turns and file turns, and per kind of question how many turns held a pause at least as long as the current cut (`samajh/server/settings.toml`), next to the splits actually seen. This is the evidence for setting the cut and grace on human speech.
- **Talk-over:** prompts during which speech was heard on the mic (echo can count; see section 2).
- **Two readings:** on figure turns, how often v3.0 and v2.5 gave the same amount, and missing second readings.

## 4. Typed reference transcripts (optional, for word error rates)

```sh
uv run python -m samajh.human refs --sessions .samajh-human/state/2026-11-15/sessions \
  --out .samajh-human/reports/2026-11-15-refs.csv
```

Open the CSV, play each `audio` file, and type what was actually said in `reference` (words as spoken: "पचास हज़ार", not "50,000"). Leave a row empty to skip it. Year-of-birth answers are left out on purpose. Then:

```sh
uv run python -m samajh.human wer --refs .samajh-human/reports/2026-11-15-refs.csv \
  --sessions .samajh-human/state/2026-11-15/sessions --out .samajh-human/reports/2026-11-15-wer.md
```

The report gives WER and CER per reading (v3.0 text, v2.5 text, v2.5 literal) and exact-amount accuracy on rows whose reference holds one amount. `transcribe` writes digits, so its WER against a words reference counts formatting as errors; the v2.5 literal is the fairer word-level reading. WER also counts script: on Hinglish, v3.0 (`hi-IN,en-IN`) writes English words in Latin ("Yes, correct.") and v2.5 (`hi-IN` only) writes them in Devanagari ("येस करेक्ट"), so whichever script the reference uses, one model is charged for it. Type English words in Latin (as v3.0 does) and compare v2.5's Hinglish WER only with that caveat stated; on the TTS check run this one effect took v2.5 from 0.11 WER on Hindi to 0.41 on Hinglish. Rerunning `refs` keeps filled references.

## 5. Voice notes

Put the notes from WhatsApp (`.ogg`, `.opus`, `.m4a`, `.mp3`, `.wav`) in a folder under `.samajh-human/`, one folder per batch and language, then:

```sh
uv run python -m samajh.human notes --in .samajh-human/voice-notes/batch1-hi --lang hi --dry-run   # converts and estimates, no API call
uv run python -m samajh.human notes --in .samajh-human/voice-notes/batch1-hi --lang hi            # --max-credits 10 by default
```

Output goes to `.samajh-human/notes/<folder name>/`: `audio/` (16 kHz and simulated 8 kHz phone-line WAVs), `readings.jsonl` (four readings per note: v3.0 and v2.5 `transcribe`, at 16 kHz and 8 kHz) and `references.csv`. Notes over 30 s are skipped (Prisma REST limit): cut them first. The command refuses an `--out` inside the repo that git does not ignore. Fill `reference` in `references.csv`, then:

```sh
uv run python -m samajh.human wer --refs .samajh-human/notes/batch1-hi/references.csv
```

Each note costs about 0.04 estimated credits per second of audio (four readings). Rerunning is free: every reading is cached.

## 6. Close the day

```sh
uv run python -m samajh.clients.gnani ledger     # the day's spend: the difference from step 0
```

Report human numbers only from mic turns and notes, with n, never pooled across kinds of customer, and with the caveats in each report's head.
