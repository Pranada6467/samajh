# Gnani API probe — iteration 1 (2026-11-10)

What W2 verified with live calls before and while building `samajh/clients/`. Every row below is from a real response unless it says `[docs]` (read on docs.gnani.ai on 2026-11-10, not exercised) or `[unverified]`.

- Raw probe script: `tests/clients/probes/gnani_probe.py` (bypasses the client on purpose: no lock, no cache, no retry). Each call is logged with status, headers and body to `.samajh/probe/log.jsonl` (gitignored).
- Audio: Timbre TTS only (voices Shivani v3.0, Nalini v2.5), the 20 sentences of the amounts pilot. No human speech. Clean TTS flatters STT, so nothing here is an accuracy claim.
- Probe window: 03:38 to 04:00 IST on 2026-11-10, then client tests.

## 1. Endpoints and parameters that work

Base URL `https://api.vachana.ai`. Header `X-API-Key-ID` on every request. One key serves STT, TTS and Batch.

### Prisma STT REST: `POST /stt/v3` (multipart)

The `3` in the path is not the model version. The `model` field picks the model; leaving it out gives `prisma-v2.5`.

| Field | Works | Notes |
|---|---|---|
| `audio_file` | WAV 8 kHz and 16 kHz, MP3 16 kHz | Format is taken from the file-name extension `[docs]`: wav, mp3, ogg, flac, aac, m4a. An MP3 sent as `audio.mp3` with content type `application/octet-stream` (what the client does) works |
| `model` | `prisma-v2.5`, `prisma-v3.0` | Anything else: 400 `INVALID_MODEL` |
| `language_code` | `hi-IN`, `ta-IN`, `kn-IN`, `hi-IN,en-IN` (v3.0), `indic-auto` (v3.0) | Required: missing gives 422. v2.5 rejects `indic-auto` (400, asks for `multi_lang_codes`). v3.0 rejects `as-IN` (400 `MODEL_UNSUPPORTED_LANGUAGE`) |
| `format` | v3.0: `verbatim`, `transcribe`, `codemix`, `transliterate`. v2.5: `verbatim`, `transcribe` | `codemix` is a format value, not a flag. v2.5 + `codemix`: 400 `INVALID_FORMAT` |
| `keyterms` (v3.0) | JSON array string | Changed the output: with `["EMI"]` the transcript kept `EMI` in Latin; without it, `ईएमआई` |
| `topic` (v3.0) | free text | `<|` or `|>` inside it: 400 `INVALID_CONTEXT` |
| `bias_list` + `bias_score` (v2.5) | accepted (200) | Effect not measured. Limits `[docs]`: ≤100 single letter-only words; score one of 0.5, 1.0, 1.5, 2.0; an invalid list is silently ignored |
| `enable_substitution` + `substitution_map` (v2.5) | accepted (200) | The pattern we sent did not appear in the literal text, so effect not shown. Not wrapped by the client |
| `itn_native_numerals=true` (v2.5) | works | `₹११,२००` instead of `₹11,200` |

Response, v3.0: `{"success":true,"request_id":"…","transcript":"मेरे लोन से 52,000 रुपये कटे।","model":"prisma-v3.0","processing_time":0.12,"end_to_end_latency":0.13,"detected_language_code":"hi-IN"}`.

Response, v2.5 with `format=transcribe`: the same without `detected_language_code`, plus `"output":{"literal":"मेरे लोन से बावन हज़ार रुपए कटे।"}`. **`output.literal` is the wording before number formatting, so one v2.5 call returns both the digits and the words.** It is absent with `format=verbatim`.

No confidence, no timestamps, no duration, no credit or usage field, on either model.

### Timbre TTS REST: `POST /api/v1/tts/inference` (JSON)

`{"text","voice","model","language","speed"?,"audio_config":{"sample_rate","container"}}` returns raw audio bytes. Response headers: `content-type`, `x-audio-container`, `x-api-request-id`. No credit header.

| Field | Works | Notes |
|---|---|---|
| `model` | `timbre-v2.5`, `timbre-v3.0` | Anything else: 400 |
| `voice` | see §7 | Required. A voice from the other model: 400, and the message lists the model's voices |
| `language` | `hi-IN`, `hi-en`, `ta-IN`, `kn-IN` all return 200 | **Not validated by the server:** `xx-XX` and an empty string also returned 200. Only the client's type guards it |
| `audio_config.sample_rate` | 8000, 16000 | Allowed set from the 400 message: 8000, 16000, 22050, 24000, 44100, 48000. Default 48000 |
| `audio_config.container` | `wav`, `raw`, `mp3`, `ogg`, `mulaw`, `alaw` (one call each through the client at 8000 Hz) | Content types seen: `audio/wav`, `application/octet-stream`, `audio/mpeg`, `audio/ogg`, `audio/basic`, `audio/alaw`. The client rejects a 200 whose content type does not match. `mulaw` and `alaw` are 8,000 bytes per second; `raw` is 16,000 bytes per second at 8 kHz, consistent with 16-bit mono PCM. No `audio_config` at all returns raw PCM at the 48 kHz default `[docs]` |
| `speed` | 1.15 | 3.0: 400 "Allowed range is 0.85 to 1.15" |
| empty `text` | 400 | |

**WAV header defect.** Every Timbre WAV has RIFF size and data size set to `0xFFFFFFFF` (a streaming header). Python's `wave` module reads nonsense from it (it reported 5.4 million seconds for 20 clips). ffmpeg and Prisma accept it. The client rewrites the two size fields (`fix_wav_header`), so callers always get a valid WAV.

### Prisma Batch (reachable with this key)

| Step | Call | Result |
|---|---|---|
| Create | `POST /stt/v3/batch/jobs`, multipart: part `config` (JSON, `application/json`), part `files` | 201, `status: CREATED`, `total_files_accepted: 1` |
| Start | `POST /stt/v3/batch/jobs/{job_id}/start` | 202, `status: STARTING` |
| Status | `GET /stt/v3/batch/jobs/{job_id}` | `status`, `config`, `progress{…, percent}` |
| Files | `GET /stt/v3/batch/jobs/{job_id}/files` | `data[].transcript_url` (pre-signed S3, 1 hour), `duration_seconds` as a string |
| Transcript | `GET transcript_url` with **no API key** | `segments[{segment_id,start_time,end_time,text,speaker_id,confidence:null,language_detected}]`, `full_transcript`, `duration_seconds` |
| List | `GET /stt/v3/batch/jobs?limit=5` | works |

Config used: `{"model":"prisma-v3.0","language_code":"hi-IN","format":"transcribe","with_diarization":true,"num_speakers":2}`. The server echoes the config with a field named `keywords` (the request field is `keyterms` `[docs]`; not exercised).

A 13.12 s job completed 1.2 s after its start was accepted.

**Segments and speakers, two runs (prisma-v3.0, `format=transcribe`, `num_speakers=2`).**

| Clip | Result |
|---|---|
| Six sentences alternating Shivani (v3.0) and Nalini (v2.5), both female, joined with no pause, 13.12 s | **One segment** 0 to 13.12 s, one speaker. No split at all |
| Shivani (female) 6.64 s + 0.7 s silence + Avinash (male) 5.28 s, 12.62 s, run through the client | **Two segments**: 0.0 to 7.392 s speaker 1, 7.392 to 12.62 s speaker 2. True change of speaker at 7.34 s, so the boundary is 0.05 s late and sits inside the silence |

So segment boundaries follow pauses and speaker changes, not sentences: a turn with no pause before it is not split, and a timestamp is a segment start, never a word time. n = 2 clips, TTS voices, one of them with two similar female voices; this says nothing yet about real two-party phone audio. Speaker ids were 1 and 2 (not 0 and 1 as in the docs example).

Two more things seen in Batch: (a) with `format=transcribe` it wrote "call" and "loan" in Latin script where REST `transcribe` wrote "कॉल" and "लोन" for the same audio, so anything that matches on such words must accept both; (b) in the first clip Batch wrote "सवा दो लाख" as `2,25,000` and "साढ़े तीन हज़ार" as `3,500`, both correct. REST on the same sentences (8 kHz, `transcribe`) gave `2.25 लाख` and `साढ़े 3,000` on v3.0, and `सवा 2,00,000` and `साढ़े 3,000` on v2.5. n = 1 each.

Not established: whether a running Batch job counts as the one active request (both jobs finished within 2 s of start, before a REST call could overlap; a REST STT call sent between create and start returned 200).

## 2. v2.5 vs v3.0, as observed

| | Prisma v2.5 | Prisma v3.0 |
|---|---|---|
| Selection | default when `model` is omitted | `model=prisma-v3.0` |
| `indic-auto` | rejected | works; reply has `detected_language_code` |
| Formats | verbatim, transcribe | + codemix, transliterate |
| No `format` sent | words | digits for a single `hi-IN`; words for `indic-auto` |
| Extra output | `output.literal` (words) next to the formatted transcript | `detected_language_code` |
| Rupee style | `₹52,000`, drops the word "रुपये" | `52,000 रुपये` |
| Hinglish amount "eleven thousand two hundred rupees" | `₹11,200` | `11,200 rupees` |
| "डेढ़ लाख" | left as words (`डेढ़ लाख`) | `1.5 लाख` |
| "सवा दो लाख" | `सवा 2,00,000` (wrong as a number) | `2.25 लाख` |
| "साढ़े तीन हज़ार" | `साढ़े 3,000` (wrong as a number) | `साढ़े 3,000` (wrong as a number) |
| "ढाई करोड़" | left as words | `2.5 करोड़` |
| "पौने दो लाख" | `पौने ₹2,00,000` (wrong as a number) | `1,75,000` |
| Tamil "ஒன்றரை லட்சம்" | `ஒன்றரை ₹1,00,000` (wrong as a number; the pilot's finding, reproduced) | `1,50,000` |
| Digits for Tamil and Kannada with `transcribe` | yes | yes |
| Hints | `bias_list` + `bias_score` | `keyterms`, `topic` |

For the amount normaliser: v3.0 writes some amounts as a decimal plus a unit word (`1.5 लाख`, `2.25 लाख`, `2.5 करोड़`), some as full digits, and some with the fraction word left in front of a wrong number. All of these came from the 8 kHz Timbre clips of the latency run, one clip each.

| | Timbre v2.5 | Timbre v3.0 |
|---|---|---|
| Voices | 73 accepted by the API (docs list 42), each with one preferred language `[docs]` | 13, each speaks every language `[docs]` |
| Audio tags | stripped `[docs]` | supported `[docs]` (not exercised) |

**Docs vs live.** (1) Docs say number formatting works for Hindi and English only; live, both models return digits for Tamil and Kannada. (2) Docs list 42 v2.5 voices; the API's own error message lists 73. (3) Docs give a fixed `language` list for TTS; the server accepts any string. (4) Docs do not mention the `x-api-request-id` response header on TTS, nor the `0xFFFFFFFF` WAV sizes. (5) Assamese: the generic `INVALID_LANGUAGE_CODE` message lists `as-IN` as supported, but v3.0 rejects it with `MODEL_UNSUPPORTED_LANGUAGE` (matches the docs). v2.5 with `as-IN` was not exercised. (6) The create-job message in the docs points at `/v1/jobs/…`; live it says `/stt/v3/batch/jobs/{job_id}/start`.

## 3. Latency

Wall time per request as the client sees it, from one machine in India on one keep-alive connection, sequential. 20 pilot sentences (clips of 1.9 to 3.6 s, mean 2.5 s; texts of 23 to 50 characters). 80 of 80 calls returned 200.

| Call | n | median | p95 | min | max |
|---|---|---|---|---|---|
| STT `prisma-v3.0` transcribe, 8 kHz WAV | 20 | 0.197 s | 0.307 s | 0.138 s | 0.391 s |
| STT `prisma-v2.5` transcribe, 8 kHz WAV | 20 | 0.258 s | 0.414 s | 0.183 s | 0.422 s |
| TTS `timbre-v3.0` (Shivani), 8 kHz WAV | 20 | 0.672 s | 0.861 s | 0.464 s | 0.921 s |
| TTS `timbre-v2.5` (Nalini), 8 kHz WAV | 20 | 0.551 s | 0.857 s | 0.341 s | 0.881 s |

What limits these numbers: n = 20, one run, one time of day (03:45 IST, off-peak), short clips, one network path. p95 of 20 is the second-largest value. A 29 s clip took 0.9 s and a 30 s clip 1.2 s on v3.0 (n = 1 each). The server's own `processing_time` was 0.09 to 0.28 s for these 40 STT calls, so a large share of the wall time is network and upload.

## 4. Two simultaneous requests

Two requests released at the same instant on separate connections (`burst 2 …`):

| Pair | First | Second |
|---|---|---|
| TTS + TTS | 200 after 1.56 s | **429 after 0.18 s** |
| STT + STT | 200 after 0.40 s | **429 after 0.26 s** |
| TTS + STT | TTS 200 after 2.22 s | **STT 429 after 0.32 s** |

Body of the 429, identical in all three: `{"detail":{"error_code":"RATE_LIMITED","message":"Only 1 active request is allowed at a time. Wait for your current request to finish before sending another.","status_code":429}}`. No `Retry-After` and no rate-limit header. The limit is shared across STT and TTS, and the loser is rejected at once, not queued.

A second, different 429 exists on the Batch routes: requests less than about a second apart get `{"detail":{"error_code":"RATE_LIMITED","message":"Rate limit exceeded","status_code":429}}`. Start sent 40 ms after create was rejected this way, and of six status polls sent within 0.8 s one got 200 and five got 429. Sequential STT/TTS calls back to back (80 in a row) never hit it.

## 5. WebSocket streaming (probe only; not built)

`wss://api.vachana.ai/stt/v3/stream`, config in upgrade headers (`x-api-key-id`, `model`, `language_code`, `x-sample-rate`, `format`). Raw PCM s16le mono in 1,024-byte binary frames at real-time cadence, then `{"type":"commit"}`.

- **Reachable with this key.** Opened in 0.5 s; first message `{"type":"connected", … "config":{"sample_rate":16000,"chunk_size":512,"partials_enabled":false,…,"language_code":"hi-IN","format":"transcribe"}}` (it reports 16000 although we sent `x-sample-rate: 8000`; the transcript and `audio_duration_ms: 2432` were right for the 8 kHz clip).
- Messages received: `speech_start`, then `transcript` with `text`, `audio_duration_ms`, `segment_id`, `is_final: true`, `latency: 140`, `detected_language_code`. The transcript matched REST.
- **An open session does not count as the one active request.** A REST STT call returned 200 while the session was open and idle, again mid-audio, and again after close.
- **A second session opened while the first was streaming** (both got `connected`). The per-organisation session cap is not documented and we did not look for it.
- Not checked: how streaming is billed, partial results, behaviour past a few seconds.

## 6. Maximum clip length on REST

| Clip | v3.0 | v2.5 |
|---|---|---|
| 29.0 s | 200 | |
| 30.0 s | 200 | |
| 31.0 s | 400 `MAX_AUDIO_DURATION_EXCEEDED` "Audio duration exceeds maximum allowed duration of 30 seconds" | same 400 |
| 45.0 s | same 400 | |

The limit is 30 s inclusive on both models. The client refuses a longer WAV before sending. Batch takes longer files (4 h, 10 MB per upload `[docs]`).

## 7. TTS voices

There is no list-voices endpoint (`GET /api/v1/tts/voices` is 404). The lists below are what the API itself returns in the 400 message for an unknown voice, so they are authoritative for this key today. Rerun: `uv run python tests/clients/probes/gnani_probe.py tts x.wav "नमस्ते" voice=Nobody [model=timbre-v2.5]`.

**timbre-v3.0 (13):** Avinash, Shivani, Lakshmi, Kalpana, Shubham, Prakash, Devansh, Yashraj, Chetana, Vasudha, Harshad, Riyaa, Tarika. Female `[docs]`: Shivani, Lakshmi, Kalpana, Chetana, Vasudha, Riyaa, Tarika. Male `[docs]`: Avinash, Shubham, Prakash, Devansh, Yashraj, Harshad.

**timbre-v2.5 (73):** Nalini, Bhavna, Yashvi, Urmila, Jwala, Chitra, Ambuja, Deepak, Roopesh, Vikrant, Hemraj, Jalaj, Omkar, Aarohi, Bhavini, Charvi, Eishani, Falguni, Gauri, Iravati, Janaki, Kamakshi, Madhuri, Radhika, Shweta, Tanvi, Vidya, Wamika, Yamini, Abhimanyu, Chirag, Deven, Farhan, Jatin, Kartik, Kaveri, Trupti, Devika, Pranav, Shlok, Girish, Asmita, Trisha, Brinda, Vedika, Noopur, Oviya, Parvati, Suhana, Lehara, Lavanya, Yukti, Varuni, Saanvi, Kavin, Hansika, Reshma, Riyaan, Zahira, Ishaan, Kirra, Dhruva, Damini, Urvashi, Falak, Veera, Lalita, Nayana, Gaurav, Harshit, Mehuli, Zayan, Poorvi.

Preferred language for the 42 documented v2.5 voices `[docs]`: Hindi: Nalini, Bhavna, Yashvi, Urmila, Jwala, Chitra, Ambuja, Deepak, Roopesh, Vikrant, Hemraj, Jalaj, Omkar. Hinglish: Poorvi. Tamil: Asmita, Trisha, Brinda, Vedika, Noopur. Kannada: Saanvi, Kavin. English: Kaveri, Trupti, Devika, Pranav, Shlok, Girish. Telugu: Suhana, Lehara, Lavanya, Yukti, Varuni. Malayalam: Reshma, Riyaan. Marathi: Zahira, Ishaan. Bengali: Kirra, Dhruva. Gujarati: Falak, Veera. Punjabi: Mehuli, Zayan. The other 31 have no documented language. `samajh.clients.gnani.VOICES` holds the same table.

## 8. Credits

**No API surface reports cost.** Rechecked: no credit, usage, balance or rate-limit header on any STT, TTS, Batch or 429 response (full header sets are in the probe log); no usage field in any body; the docs and the official SDK (`gnani-vachana` 0.9.0) have no usage or balance endpoint; guessed paths (`/usage`, `/credits`, `/balance`, `/api/v1/usage`, `/api/v1/credits`, `/api/v1/account`) return the gateway's catch-all 403 `SCOPE_NOT_ALLOWED`. The dashboard at app.gnani.ai is the only source of truth. Docs say STT is billed by audio duration and TTS by character, with no rate given.

**Rates the client uses (estimates).** From the pilot's dashboard reading (2.96 credits; chart split about 1.7 STT / 1.2 TTS; 78 billed STT calls over about 196 audio seconds, 20 TTS calls over 670 characters): STT ≈ 0.0087 credits per audio second (≈ 31 credits per hour), TTS ≈ 0.0018 credits per character. `samajh/clients/defaults.toml` rounds these up to 0.010 and 0.002 so the guard errs on the safe side. The split was read off a chart, so each rate could be off by 20% or more.

**How the guard works.** Every successful live call adds `est_credits` to `.samajh/ledger.jsonl`. Before a live call the client refuses (`CapExceeded`) if the ledger total plus this call's estimate would pass `GNANI_CREDIT_CAP`. Cache hits and failed attempts add nothing (the pilot's two 504s were not billed).

**What the user should read off the dashboard to turn the estimates into measurements.** The pilot left the account at 2.96 credits used. Since then:

| Since the pilot, up to 04:46 IST on 2026-11-10 | Calls that returned 2xx | Billable quantity |
|---|---|---|
| STT REST | 68 | 266.0 audio seconds (one 2.56 s MP3 included) |
| TTS REST | 67 | 2,715 characters |
| Batch | 2 jobs | 25.74 audio seconds |
| Streaming | 2 sessions | 2.43 audio seconds sent on one, none on the other |

These come from `.samajh/ledger.jsonl`, which holds every client call plus rows imported from the raw probe log and one row for the pilot's 2.96 credits. At the rounded-up rates the ledger estimates 8.62 credits for this work (11.58 with the pilot); at the unrounded pilot rates it would be about 7.4. Nothing else touched the key in that window apart from the calls counted here. For current totals at any later time: `uv run python -m samajh.clients.gnani ledger` (`audio_seconds` and `chars` there count STT, TTS and client-run Batch jobs; the two Batch jobs above predate that counter and are listed separately here).

Failed calls in the same window, for the "are failures billed" question: 3 × 429 on STT/TTS, 6 × 429 on Batch routes, about 35 other 4xx (400, 401, 403, 404, 405, 409, 422), 0 × 5xx.

Read the STT and TTS credit totals on app.gnani.ai, subtract the pilot's 1.7 and 1.2, and divide by the seconds and characters above. Put the two rates in `defaults.toml`. If the dashboard shows Batch or streaming separately, note those too: we assumed Batch bills like REST STT and did not estimate the two short streaming sessions.

## 9. Error bodies

Five shapes, all handled by one parser in the client:

| Where | Example |
|---|---|
| Gateway (401, 403, 429) | `{"detail":{"error_code":"INVALID_API_KEY","message":"Unauthorized","status_code":401}}` |
| Validation (422, 404, 405) | `{"detail":[{"type":"missing","loc":["body","language_code"],"msg":"Field required","input":null}]}`, `{"detail":"Not Found"}` |
| STT (400) | `{"success":false,"error":{"type":"INVALID_LANGUAGE_CODE","message":"…"}}` |
| TTS (400) | `{"success":false,"message":"Invalid request: Value error, … at body -> speed","status_code":400}` |
| Batch (404, 409) | `{"error":"JOB_NOT_FOUND","message":"Job … not found"}` for an unknown job id; `{"error":"JOB_ALREADY_STARTED","message":"Job cannot be restarted from state 'COMPLETED'"}` for a second start. A job id that is not a UUID gives the 422 validation shape |
| 504 `[docs]` | `{"error":"Gateway Timeout","code":"UPSTREAM_TIMEOUT","message":"…"}` (not seen in this probe; the pilot saw two 504s on v2.5 Kannada) |

Unknown paths return 403 `SCOPE_NOT_ALLOWED` ("Service 'None' not in allowed scopes"), not 404.

## 10. OpenRouter (LLM client), for completeness

Verified live with `tests/clients/probes/llm_model_probe.py` and the live test: `usage` (tokens and `cost` in USD) comes back on every non-streaming call with no extra parameter; `GET /api/v1/key` reports cumulative `usage` and its delta matched the summed `usage.cost` of the probe exactly (0.002267 USD); strict `json_schema` output with `provider.require_parameters=true` returned schema-valid JSON on the first attempt in 48 of 48 calls across three models; an invalid model id returns 400 (docs suggested 404); the same model id was served by different upstream providers on consecutive calls, so temperature 0 does not make replies reproducible and the cache is what keeps results stable.

Model probe: 16 synthetic utterances (4 each Hindi, Hinglish, Tamil, Kannada), 4 fields each, gold written by the builder before running. Tamil and Kannada rows are **not human-reviewed**.

| Model | Schema-valid first attempt | Fields right | hi | hinglish | ta* | kn* | Quote is verbatim | Median | p95 | USD for 16 calls |
|---|---|---|---|---|---|---|---|---|---|---|
| `google/gemini-2.5-flash-lite` | 16/16 | 62/64 | 15/16 | 16/16 | 15/16 | 16/16 | 11/12 | 0.98 s | 1.05 s | 0.000859 |
| `openai/gpt-4.1-nano` | 16/16 | 58/64 | 16/16 | 16/16 | 13/16 | 13/16 | 9/12 | 0.92 s | 1.69 s | 0.000875 |
| `mistralai/mistral-small-3.2-24b-instruct` | 16/16 | 62/64 | 16/16 | 15/16 | 16/16 | 15/16 | 12/12 | 1.10 s | 2.67 s | 0.000533 |

Default set to `mistralai/mistral-small-3.2-24b-instruct` (tie on fields with Gemini Flash-Lite, broken on cost). What limits this: n = 16, one run per model, one annotator who also wrote the prompt, clean typed text with no speech-to-text noise, p95 of 16 is the slowest call. It shows that `gpt-4.1-nano` rewrites amounts in Tamil and Kannada (`18000` for `18,000`, `1.5 லட்சம்` for `ஒன்றரை லட்சம்`); it cannot separate Mistral from Gemini. Their errors differ in kind: Gemini's two were quote formatting (a dropped comma, an added currency word), which a substring check catches; Mistral's two were meaning (`product_kind`, `paid_from_loan`), which code cannot catch. The extractor work package should rerun the probe on the frozen gold set before relying on the default.
