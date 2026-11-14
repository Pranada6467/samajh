# Reproducing W7 (open baselines)

One command per part, from the repository root. Every paid step goes through the project's clients (Gnani:
`samajh/clients/gnani`, one request at a time, cache, ledger, credit cap; LLMs: `samajh/clients/llm.py`, cache,
ledger, USD cap), and every step is resumable, so a rerun on a machine that holds the caches makes no new paid
call. `--offline` runs only the scoring step from stored outputs.

```
uv run python eval/openbench/run.py a [--offline]   # amounts: open models and a closed reference vs Prisma
uv run python eval/openbench/run.py b [--offline]   # FLEURS hi_in test: WER/CER
uv run python eval/openbench/run.py c [--offline]   # a generic LLM agent vs the Samajh call, on text
```

## What you need
| | Part A, synthetic | Part A, public clips | Part B | Part C |
|---|---|---|---|---|
| Public data only | yes | **no** (see below) | yes | yes |
| Gnani key (`GNANI_API_KEY`) | to regenerate the TTS audio and Prisma rows only | same | yes (about 116 estimated credits) | no |
| OpenRouter key (`OPENROUTER_API_KEY`) | Gemini row only | Gemini row only | Gemini row only | yes (about USD 1) |
| Apple-silicon Mac, ffmpeg | yes (MLX Whisper) | yes | yes | no |

- **Part A, synthetic:** the 280 sentences are `data/amounts_v2/amounts-v2.jsonl` (sha256 in `amounts-v2.sha256`).
  The audio is Gnani Timbre TTS made by `uv run python -m samajh.evalkit run eval/amounts_v2/experiment.toml`
  (stored under `.samajh/evalkit/amounts-v2/`; the Prisma transcripts are committed in `eval/amounts_v2/run/`).
  Each audio file is identified by the `audio_sha256` in those rows; `inputs.py` refuses a file whose hash differs.
  TTS output is not guaranteed byte-identical on a fresh run: a stranger regenerating it gets new audio and should
  expect small differences. The open-model and Gemini transcripts of our audio are committed in
  `eval/openbench/runs/amounts-v2/`, so the tables can be recomputed without any audio.
- **Part A, public clips:** the 124 IndicVoices and Kathbath clips stay on the author's machine
  (`.samajh-realvoice/`, gitignored; dataset licences and the project's data rule). `data/amounts_v2/realvoice-v1.jsonl`
  lists their ids, dataset row locations and audio hashes; `eval/amounts_v2/realvoice.py select|fetch` rebuilds them
  from the gated Hugging Face datasets after accepting their terms. Transcripts of these clips are not in the repo.
- **Part B:** FLEURS `google/fleurs` @ `70bb2e84b976b7e960aa89f1c648e09c59f894dd`, `hi_in` test (CC-BY-4.0).
  `fleurs.py fetch` checks `test.tar.gz` sha256 `47c238b9cf7016ba596639bb3038b0c89dc6e85759f16d09c4f58c6dfa25c65f`;
  `freeze` must reproduce `data/openbench/fleurs-hi-test.jsonl` (sha256 `5ad0bc07…c128`; ids, hashes, durations, the
  250 subset and no text). The published files are 32-bit float WAVs; `native16k` is ffmpeg's PCM16 copy (the
  published hash is kept as `original_sha256`), `phone` is that copy through the same mu-law 8 kHz step as the
  amounts sets. Transcripts of FLEURS audio stay in `.samajh/openbench/runs/fleurs/`.
- **Part C:** synthetic text only (`data/acq/`, frozen by W3). Call files are committed in `eval/openbench/runs/partc/`;
  `runs/partc/FROZEN.json` pins the harness, prompt and router, and the runner refuses a counted run on any mismatch.

## Pins
- Local models run in a throwaway environment, never the project venv:
  `uv run --no-project --python 3.11 --with-requirements eval/openbench/requirements-asr.txt python eval/openbench/asr_local.py …`
  (mlx 0.26.1, mlx-whisper 0.4.2, torch 2.5.1, transformers 4.46.3, numpy 1.26.4; macOS arm64, Python 3.11.5).
- Whisper large-v3: `mlx-community/whisper-large-v3-mlx` @ `49e6aa286ad60c14352c404340ded53710378a11` (MLX fp16
  conversion of `openai/whisper-large-v3`), `language="hi"`, transcribe, temperature 0, no fallback, greedy.
- IndicWhisper: `https://indicwhisper.objectstore.e2enetworks.net/hindi_models.zip`, 4,262,614,425 bytes, sha256
  `e409b7d56d3cf3c04d0b307347d48a96fd2c045c53ff99ed24dec5e3f80ea4c0`, directory
  `hindi_models/whisper-medium-hi_alldata_multigpu` (config sha256 `8de96b55…88b7`), transformers fp32 on MPS,
  `language="hi"`, greedy, `max_new_tokens` 225. The weights are a pickle (`pytorch_model.bin`) from a third-party zip.
- Gemini (closed reference): `google/gemini-3-flash-preview` on OpenRouter, prompt sha256 `e806b58e…2a7a`
  (text in `runs/amounts-v2/gemini-3-flash.meta.json`), `max_tokens` 4,096, temperature 0. OpenRouter routes to a
  provider; a hosted preview model can change under the same id, so a rerun months later may differ.
- Prisma: `prisma-v3.0` and `prisma-v2.5`, `verbatim` (Part B) and `transcribe` (Part A, P6's rows), `hi-IN`, via
  `POST /stt/v3`. A hosted model can change under the same name.
- Part C: agent `qwen/qwen3-235b-a22b-2507`, router `mistralai/mistral-small-3.2-24b-instruct`, temperature 0;
  modelled on `livekit-examples/outbound-caller-python` `agent.py` @ `608f4c70…ac8600` (sha256 `38366893…9871`).
- Scoring: `eval/amounts_v2/frozen_parser.py` (the amount parser at commit 59c12d9) and `eval/openbench/wer.py`
  (`normalise()`: NFC, lower-case, Unicode P* and S* to space, collapse spaces).

## Independent recomputation
The checker's own scripts (not the scorers above) recompute every figure from the raw rows; see the report.
