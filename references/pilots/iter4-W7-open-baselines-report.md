# W7 (iteration 4): open, reproducible baselines

Full tables and caveats: `eval/openbench/REPORT.md`. Plan with every dated change, each made before the affected
output was scored: `eval/openbench/PLAN.md`. Rerun: `eval/openbench/REPRODUCE.md`.

## Verdict, quotable
- **Amounts (TTS audio, simulated 8 kHz phone, 68 skipped-group amounts and 68 matched controls, frozen 59c12d9
  parser):** Prisma v3.0 `transcribe` wrote a wrong amount for 40 of 68 skipped amounts, Whisper large-v3 for 33,
  IndicWhisper for 15 and Gemini 3 Flash (closed reference) for 8; v2.5 `transcribe` for 0. On the controls: 0, 13,
  16 and 0. Whisper and Gemini also wrote some "X lakh Y" amounts as X lakh Y thousand (10 and 5 clips), the class
  P6 left open as possibly colloquial; none of them made v3.0's other 26 errors. No open model matched v2.5.
- **Third reading:** on these sets the two-Prisma agreement rule already accepted no wrong amount (0 of 224
  synthetic, 0 of 113 public). Adding an open model as a third reading either added re-asks (all three must agree)
  or let wrong amounts through (majority of three: IndicWhisper 1 public; Whisper 10 synthetic and 1 public; Gemini
  5 and 3). Nothing measured argues for adding one.
- **FLEURS hi_in test (read speech):** on 100 seeded test clips, every system on the same audio, NFC, lower-case and
  punctuation removed, numbers not converted, WER at 16 kHz: Prisma v2.5 `verbatim` 11.6 [9.8-13.8], v3.0 12.2
  [10.2-14.6], Gemini 3 Flash 12.9, IndicWhisper 14.4 [11.3-17.7], Whisper large-v3 28.7 [26.2-31.4]; at simulated
  8 kHz phone 0.3 to 1.4 points higher. Normalisation alone moves every system by about 8 to 10 points; under the
  Whisper paper's normaliser (post hoc) our Whisper rerun gives 17.5, near OpenAI's published 17.0. Not a FLEURS test
  score (100 or 250 of 417 clips).
- **Generic LLM agent (synthetic text, 160 customers, W3's replies):** a generic agent prompted on LiveKit's
  outbound-caller example and given the record and Samajh's own outcome labels stated a record value before the
  customer did in 39 of 40 calls read by hand; with customers who never agree to what they do not know (r = 0,
  a = 0) it found 33 of 48 knowledge gaps against 45 of 48 for the Samajh call (exact McNemar p = 0.008) and referred
  59 of 80 customers with a false belief (4 more handed to a human with no report) against 80 of 80. Different
  models (qwen3-235b against Samajh's gpt-6-luna and mistral-small); text, not speech; replies set by rule.

## What was built (new directories only: `eval/openbench/`, `data/openbench/`, `tests/openbench/`)
- `store.py` (job and transcript contract), `inputs.py` (the exact P6 audio by hash), `asr_local.py` +
  `requirements-asr.txt` (Whisper large-v3 via MLX, IndicWhisper via transformers, in a throwaway environment, never
  the project venv; `pyproject.toml` not touched), `asr_gemini.py` (Gemini through `samajh/clients/llm.py` with a
  local message type carrying audio parts, since `Message.content` is text only), `asr_prisma.py` (through
  `samajh/clients/gnani`), `fleurs.py` (pinned download, safe extraction, frozen manifest
  `data/openbench/fleurs-hi-test.jsonl` with ids and hashes, no text), `wer.py`, `part_a.py`, `part_b.py`,
  `part_c_customer.py` / `part_c_agent.py` / `part_c_samajh.py` / `part_c.py`, `run.py` (one command per part).
- Outputs: synthetic transcripts and Part C calls committed under `eval/openbench/runs/`; dataset-derived transcripts
  only under `.samajh/openbench/` (gitignored).

## Measurements and how obtained
See the verdict and `eval/openbench/REPORT.md`. Spend: Gnani 117.07 estimated credits of 150 (ledger 341.87 before,
458.94 after; FLEURS pilot 1.80, run 115.28). LLM at most USD 6.64 of 12 (ledger rows since the task began for
Gemini 3.1 Pro 4.94, Gemini 3 Flash 0.34, qwen3-235b 1.06, mistral-small 0.31, the last including other workers'
classifier calls).

## Independent checker (Opus, high effort, wrote no code), in its own words, and what I did
- Strawman read of the Part C prompt (before any counted call): "As written, it leans toward losing for reasons
  unrelated to the design: model, coverage, simulator yes-bias and field naming." Done: a coverage line, stated values
  compared with the record in code, per-finding field/belief/quote schema, 30 turns, `no_report` apart, a coached B1
  arm, third-party scripts also played to Samajh. Not done: a gpt-6-luna row (budget); the confound is stated.
- Router hand-labels, blind, three rounds on fresh utterances: 12 of 60, 6 of 40, then 4 of 40 stated values
  disagreed; "Verdict: run" at 10.0% (Wilson upper bound 23.1%), reported beside every Part C figure.
- Recomputation with its own scripts: Part C "0 disagreements" (568 calls); Part A "0 disagreements"; Part B "0 disagreements" (108 rows, 15,900 per-utterance counts),
  plus its post-hoc normaliser check: "the gap between our ~29 and 17.0 is mostly the scorer's normaliser, not our
  inference setup". Done: the report now says so; my draft had blamed inference setup. It corrected its own Part C sentence ("B0 at (0,0) referred 59 of 80 … 63 counted those transfers").
- "The table's 'kind' column undercounts (ii); it should be fixed or dropped": dropped; its by-hand classification
  is in the report (Whisper 6, IndicWhisper 16, Gemini 1 wrong amounts are the right number in a form the frozen
  parser cannot read, mostly English number words in Devanagari).
- Fairness caveats it required, all in the report: B0 lists a finding on almost every field (814 `belief=false`
  findings on fields that are not false); the prompt carries Samajh's tiers (coaching that favours B0); at
  (0.5, 0.5) B0 found more knowledge gaps than Samajh (20 against 3), because Samajh hears "check your records" as a
  refusal; the third-party script is weak; Samajh's third-party calls ran on the dirty worktree (W4's uncommitted
  dialogue edits), not W3's snapshot.

## What failed or is left open
- IndicConformer not run (gated: the account is not on the authorized list). Gemini 3.1 Pro abandoned for cost after
  153 clips. Open models not run on the clean 16 kHz amounts copies, and on FLEURS only on 50 clips (this shared
  machine's swap was full: Whisper fell to about 1 clip a minute).
- Part A's open-model "wrong" counts partly measure the frozen parser (built on Prisma's style).
- A race in `eval/amounts_v2/frozen_parser.py` (two processes exporting to the same temp folder) crashed Part C cells
  2 to 4 once; my repair of the shared temp folder while they ran made it worse. Failed calls were rerun on resume;
  Part C now loads its own copy.

## Needed from others
- `samajh/clients/llm.py`: a `Message` that can carry audio parts (W7 used a local duck-typed message), and a way to
  set reasoning effort (Gemini Pro's runaway reasoning).
- `eval/amounts_v2/frozen_parser.py`: export under a lock or to a per-process folder.
- The frozen 59c12d9 parser cannot read English number words written in Devanagari; any future open-model or
  human-transcript scoring needs a parser that can (on a new frozen set, not this one).
- Dialogue owner: W3's finding that deference ("आप records में देख लीजिए") ends the call `declined` is also what
  lets the generic agent beat Samajh at a = 0.5 here.
- User: request access to `ai4bharat/indic-conformer-600m-multilingual` on Hugging Face if IndicConformer is wanted.
- Documentation worker: allowed and forbidden wording is in `eval/openbench/REPORT.md` ("Wording").

## Tests
`uv run pytest -q tests/openbench` → 36 passed in 0.21 s (2026-11-14). The whole suite was not run: other workers are mid-change in `samajh/server`, `samajh/ops` and `samajh/dialogue`.
