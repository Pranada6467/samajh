# How often does Prisma's output lack sentence punctuation?

Measured 2026-11-10, offline, from the client's stored STT responses (`.samajh/cache/gnani/`, read only; no API call). It answers the open item in `references/reviews/iter2/verify-P3a-r3.md` (finding 2): the rules treat a one-clause reply differently, and the change check never runs on one.

**Method.** The cache keeps each response body but not the requested `format`, so each response was matched to its request through the run files of the three evaluations that made them (`eval/amounts/run/`, `eval/amounts_v2/run/`, `.samajh-realvoice/run/`; 5,064 of the 5,276 STT entries). Kept: Hindi and Hinglish items, transcripts of more than six words. "Clause break" is what the rule engine splits on (`CLAUSE_END` in `samajh/amounts/_parse.py`: `। ॥ ; ! ? …`, a newline, or a comma or full stop not between digits). The plain test (any of `। , . ?`, the third column) over-counts, because `transcribe` writes amounts such as 9,400 with a comma.

| Model, format | n | any of `। , . ?` | none | clause break | no clause break |
|---|---|---|---|---|---|
| v3.0 `transcribe` | 640 | 640 | 0 | 640 | 0 |
| v3.0 `verbatim` | 845 | 844 | 1 | 844 | 1 |
| v3.0 `codemix` | 53 | 53 | 0 | 53 | 0 |
| v2.5 `transcribe` | 641 | 498 | 143 | 204 | 437 |
| v2.5 `verbatim` | 48 | 21 | 27 | 21 | 27 |

**Which audio.** Of the 5,064 matched responses 4,320 are Timbre TTS (the two amounts sets) and 744 are the public real-voice clips. In the table, 248 of the 640 v3.0 `transcribe` rows and 246 of the 641 v2.5 rows are real-voice clips (124 clips, each in a native and an 8 kHz copy), because TTS `transcribe` turns amounts into digits and many TTS transcripts fall under six words. On the real clips alone: v3.0 `transcribe` and `verbatim` had a clause break in 248 of 248 each; v2.5 `transcribe` in 1 of 246 (140 contain a comma or full stop, each only inside a number; the one clause break is a `।`). No customer speech is in the table: the 212 other STT entries (origin not established) record neither format nor language, and only 65 v3.0 and 12 v2.5 of them pass the length filter (v3.0: 63 with a clause break, 2 without; v2.5: 6 and 6).

**Implication.** Prisma v3.0, which reads every customer turn, put a clause break in 640 of 640 `transcribe` transcripts of more than six words (1,537 of 1,538 across all three formats; all 248 real-voice ones in each of `transcribe` and `verbatim`), so the one-clause gap is not a sign that v3.0 drops punctuation on longer replies (inferred: it is mostly short answers and v2.5 figure readings, which broke 1 of 246 real-voice transcripts); this does not cover replies of six words or fewer, or speech on a phone line.

Counting script not saved in the repo (a one-off read of the cache).
