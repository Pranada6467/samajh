# How often is Prisma's output more than one clause?

Corrected 2026-11-13. Offline, from the client's stored STT responses (`.samajh/cache/gnani/`, read only; no API call). It answers the open item in `references/reviews/iter2/verify-P3a-r3.md` (finding 2): the rules treat a one-clause reply differently from a longer one.

**What the first version got wrong.** The note of 2026-11-10 counted a "clause break" as any of `। ॥ ; ! ? …`, a newline, or a comma or full stop not between digits (`CLAUSE_END` in `samajh/amounts/_parse.py`), and reported a break in 640 of 640 v3.0 `transcribe` transcripts of more than six words. That count includes the full stop that ends a sentence. A reply with one sentence-final mark is still one clause, so the 640 of 640 did not show how often the change check could run, and it overstated it. Its rows for v3.0 `verbatim` and `codemix` and v2.5 `verbatim` used the same count and are dropped.

**Method.** The extractor's own splitter: `Reply(text).clauses()` in `samajh/extract/_ground.py` (two or more clauses that hold a word). Script: `uv run python eval/text_path/punctuation_rate.py` (cache only). Responses are matched to their requests through the run files of the three evaluations that made them (`eval/amounts/run/`, `eval/amounts_v2/run/`, `.samajh-realvoice/run/`). Hindi and Hinglish, transcripts of more than six words. The audio is Timbre TTS (the two amounts sets) or public real-voice clips (124 clips, each in a native and an 8 kHz copy); no customer speech is in the table.

| Model, format | Audio | n | Result |
|---|---|---|---|
| v2.5 `transcribe` | public real voice | 246 | one clause in 246 |
| v2.5 `transcribe` | Timbre TTS | 395 | one clause in 376 |
| v3.0 `transcribe` | public real voice | 248 | two or more clauses in 104 |
| v3.0 `transcribe` | Timbre TTS | 392 | two or more clauses in 26 |

Replies of six words or fewer on Timbre TTS: two or more clauses in 0 of 701 (v2.5 `transcribe`) and 0 of 768 (v3.0 `transcribe`); the public real-voice set has 2 such v2.5 clips and none for v3.0.

**Implication.** The text the case file reads on a figure turn is the v2.5 reading when v2.5 heard something, and that is almost always one clause: a rule that runs the change check only on a reply of two or more clauses would skip it. Since iteration 3 the check also runs on a one-clause reply that holds a take-back word (`references/pilots/P3a-report.md`, "Iteration 3 (chain)"). v3.0 text, which the case file reads on ordinary turns, has two or more clauses in 26 of 392 Timbre clips and in 104 of 248 real-voice clips. Not covered: customer speech, and speech on a phone line.
