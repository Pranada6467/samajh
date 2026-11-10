# W2 clients: final report (2026-11-10)

Goal: every later Samajh component talks to Gnani and to the LLM through two clients that cannot double-fire the one Gnani key, never pay twice for the same call, and stop before the spend cap. Both clients are built, proven live, reviewed independently, and the reviewer's 13 proven findings are fixed.

## 0. Plan as built

One shared runtime, two thin typed clients on top.

```
samajh/clients/
  errors.py        typed errors (ClientError and subclasses)
  _runtime.py      state_dir, load_env, load_defaults, check_api_key, cache_key, Cache, Ledger(Entry),
                   single_flight (cross-process file lock), RetryPolicy, send_with_retry
  defaults.toml    measured config: credit rates and cap, default LLM model and USD cap
  gnani/           types.py, wav.py, client.py, __main__.py (CLI)
  llm.py           OpenRouter client
```

Every call follows one sequence: cache lookup (hit: one ledger row, no lock, no network) → `single_flight` (Gnani only) → cache lookup again → cap check → `send_with_retry` with one ledger row per attempt → parse → cache. The cache key is built from the exact dict that is sent, plus the base URL, plus a hash of the audio.

Design choices worth knowing:
- The Gnani lock is held for a whole call including its backoff sleeps, so only one process on the machine is ever talking to or retrying against the key.
- Batch takes the lock per HTTP request and sleeps between requests outside it, so a long job does not block live STT turns. A second lock per input stops two processes creating the same job.
- `format` is a required STT option. The server's default changes with model and language (v3.0 + `hi-IN` gives digits, everything else words), so the client always sends it.
- The architect skill's four-model arena was skipped: ORCHESTRATION.md fixes planning to Fable, so I sketched the runtime contract myself and builders filled it in.

## 1. What was built

- `samajh/clients/__init__.py`, `errors.py`, `_runtime.py`, `defaults.toml`, `llm.py`
- `samajh/clients/gnani/__init__.py`, `types.py`, `wav.py`, `client.py`, `__main__.py`
- `tests/clients/test_clients_runtime.py`, `test_gnani_wav.py`, `test_gnani_types.py`, `test_gnani_rest.py`, `test_gnani_batch.py`, `test_gnani_single_flight.py`, `test_gnani_cli.py`, `test_gnani_live.py`, `test_llm_client.py`, `test_llm_live.py`
- `tests/clients/probes/gnani_probe.py` (raw probe, bypasses the lock on purpose), `tests/clients/probes/llm_model_probe.py`
- `references/pilots/api-probe-iter1.md`

### Public signatures

```python
# samajh.clients.gnani
class GnaniClient:
    def __init__(self, *, api_key: str, credit_cap: float, state: Path | None = None,
                 base_url: str = "https://api.vachana.ai", http: httpx.Client | None = None,
                 retry: RetryPolicy = RetryPolicy(), timeout: float = 30.0, lock_timeout: float = 600.0,
                 sleep: Callable[[float], None] = time.sleep, rng: random.Random | None = None,
                 stt_credits_per_second: float | None = None, tts_credits_per_char: float | None = None) -> None
    @classmethod
    def from_env(cls, **overrides) -> GnaniClient      # GNANI_API_KEY, GNANI_CREDIT_CAP (else defaults.toml)
    def stt(self, audio: bytes, options: PrismaV30 | PrismaV25, *, audio_format: AudioFormat = "wav") -> Transcript
    def tts(self, text: str, options: Timbre) -> Speech
    def batch_transcribe(self, audio: bytes, options: BatchOptions, *, audio_format: AudioFormat = "wav",
                         poll_interval: float = 10.0, timeout: float = 900.0) -> BatchTranscript
    def credits_spent(self) -> float

PrismaV30(model="prisma-v3.0", language: SttLanguage | "indic-auto" | tuple[SttLanguage, ...] (1-4),
          format: "verbatim"|"transcribe"|"codemix"|"transliterate", keyterms: tuple[str, ...] = (), topic: str | None = None)
PrismaV25(model="prisma-v2.5", language: SttLanguage, format: "verbatim"|"transcribe",
          bias_list: tuple[str, ...] = (), bias_score: 0.5|1.0|1.5|2.0 | None = None)
Timbre(model: "timbre-v2.5"|"timbre-v3.0", voice: str, language: TtsLanguage,
       sample_rate: 8000|16000|22050|24000|44100|48000 = 8000, container: "wav"|"raw"|"mp3"|"ogg"|"mulaw"|"alaw" = "wav",
       speed: float = 1.0)
BatchOptions(model, language, format: "verbatim"|"transcribe"|"codemix" | None, diarize: bool = True,
             num_speakers: int | None = None, denoise: bool = False, keyterms: tuple[str, ...] = ())

CallInfo(cache_hit: bool, cache_key: str, seconds: float, est_credits: float, attempts: int)
Transcript(text, literal: str | None, model, detected_language: str | None, request_id: str | None, truncated: bool, call)
Speech(audio: bytes, content_type, container, sample_rate, audio_seconds: float | None, request_id: str | None, call)
Segment(index: int, start: float, end: float, text: str, speaker: int | None, language: str | None)
BatchTranscript(segments: tuple[Segment, ...], text, duration_seconds: float, language, model, job_id, file_id, call)
Voice(name, model, gender: "F"|"M"|None, language: TtsLanguage | None);  VOICES: dict[model, tuple[Voice, ...]]
BatchTimeout(ClientError)                        # .job_id, .status, .timeout; call again to resume
def wav_seconds(data: bytes) -> float | None
def wav_sample_rate(data: bytes) -> int | None
def fix_wav_header(data: bytes) -> bytes
def parse_error(response: httpx.Response) -> tuple[str | None, str]

# CLI
uv run python -m samajh.clients.gnani tts "TEXT" --out FILE [--model] [--voice] [--language] [--sample-rate] [--container]
uv run python -m samajh.clients.gnani stt FILE [--model] [--language] [--format] [--keyterm X ...]
uv run python -m samajh.clients.gnani batch FILE [--model] [--language] [--format] [--num-speakers N]
uv run python -m samajh.clients.gnani voices [--model]
uv run python -m samajh.clients.gnani ledger

# samajh.clients.llm
class Message(BaseModel): role: "system"|"user"|"assistant"; content: str
class LlmResult(BaseModel, Generic[T]):
    value: T; model: str; prompt_tokens: int; completion_tokens: int; usd: float; cache_hit: bool; attempts: int; generation_id: str | None
def strict_json_schema(schema: type[BaseModel]) -> dict[str, Any]
class LlmClient:
    def __init__(self, *, api_key: str, model: str, usd_cap: float, state: Path | None = None,
                 base_url: str = "https://openrouter.ai/api/v1", http: httpx.Client | None = None,
                 retry: RetryPolicy = RetryPolicy(), timeout: float = 60.0,
                 sleep: Callable[[float], None] = time.sleep, rng: random.Random | None = None) -> None
    @classmethod
    def from_env(cls, **overrides) -> LlmClient     # OPENROUTER_API_KEY; SAMAJH_LLM_MODEL, SAMAJH_LLM_USD_CAP (else defaults.toml)
    def complete(self, schema: type[T], messages: Sequence[Message], *, model: str | None = None,
                 temperature: float | None = 0.0, max_tokens: int = 1024, max_output_retries: int = 2) -> LlmResult[T]
    @property
    def spent_usd(self) -> float

# samajh.clients.errors
ClientError > ConfigError, InvalidRequest, LockTimeout, CapExceeded(unit, cap, spent, estimate), TransportError,
              BadResponse, ApiError(status, code, message, attempts) > AuthError, RateLimited, ServerError;
              LlmOutputInvalid(model, attempts, last_error)

# samajh.clients._runtime (shared; a future streaming component should take the same lock)
state_dir(), load_env(), load_defaults(), check_api_key(key, name), cache_key(namespace, params, payload),
Cache(root).get/put, Ledger(path).append/entries/total_credits/total_usd, LedgerEntry,
single_flight(lock_path, *, timeout), RetryPolicy(max_attempts=5, base_delay=1.0, max_delay=30.0), send_with_retry(...)
```

Environment: `GNANI_API_KEY`, `OPENROUTER_API_KEY`, `GNANI_CREDIT_CAP`, optional `SAMAJH_LLM_MODEL`, `SAMAJH_LLM_USD_CAP`, `SAMAJH_STATE_DIR`. The last three are not in `.env.example` (outside my lane).

## 2. Evidence

Final runs on the fixed code:

```
$ uv run pytest tests/clients -q
289 passed, 2 deselected in 14.82s
$ uv run pytest tests/clients -m live -q          (GNANI_CREDIT_CAP=40)
2 passed, 289 deselected in 2.86s
$ uv run ruff check samajh tests
All checks passed!
```

The two live tests make one real Timbre v3.0 call, one real Prisma v3.0 call and one real OpenRouter call, each with a random number in the input so it is never cached, then repeat them and assert cache hits.

**Two (three) concurrent processes are serialised.** Three CLI processes started at the same instant, two TTS and one STT on a 29 s clip:

```
a cache_hit False attempts 1 secs 1.4616
b cache_hit False attempts 1 secs 1.3761
c cache_hit False attempts 1 secs 0.726
new ledger rows:
  2026-11-09T23:15:23+00:00 tts 200 attempt 1 secs 1.4603 err None
  2026-11-09T23:15:24+00:00 tts 200 attempt 1 secs 1.3754 err None
  2026-11-09T23:15:25+00:00 stt 200 attempt 1 secs 0.7254 err None
```

All three got 200 on the first attempt with no 429. The control is the raw probe: two simultaneous requests without the lock always gave the second one a 429 (three pairs out of three). Offline, `test_gnani_single_flight.py` runs subprocesses against a local server that records requests in flight: peak 1 with a shared state dir, at least 2 in the control with separate locks. The reviewer ran 4 processes × 6 threads mixing STT, TTS and batch: 64 requests, peak in flight 1.

**A repeated call is a cache hit with zero network calls.** Call (a) repeated with every route pointed at a dead proxy:

```
{'cache_hit': True, 'cache_key': '7ea83736…', 'seconds': 0.0, 'est_credits': 0.0, 'attempts': 0}
audio identical
ledger: tts cache_hit attempt 0 est_credits 0.0
--- control, uncached text through the same dead proxy:
error: TransportError: ConnectError on all 5 attempts      (exit 1)
```

Offline tests assert the respx route was called exactly once across two identical calls, for STT, TTS, batch and LLM.

**Measured (details, n and limits in `references/pilots/api-probe-iter1.md`):**

| What | Result |
|---|---|
| STT v3.0 latency, 8 kHz clips of 1.9 to 3.6 s | n=20, median 0.197 s, p95 0.307 s |
| STT v2.5 latency | n=20, median 0.258 s, p95 0.414 s |
| TTS v3.0 latency, 23 to 50 characters | n=20, median 0.672 s, p95 0.861 s |
| TTS v2.5 latency | n=20, median 0.551 s, p95 0.857 s |
| Two simultaneous requests | second gets 429 `RATE_LIMITED` "Only 1 active request is allowed at a time…" within 0.3 s, no `Retry-After`; shared across STT and TTS |
| REST clip limit | 30.0 s accepted, 31 s rejected (`MAX_AUDIO_DURATION_EXCEEDED`), both models |
| WebSocket streaming | reachable; an open session does not take the active-request slot; two sessions opened at once |
| Batch | reachable; 13 s job done 1.2 s after start; batch routes have their own rate limit (calls under about 1 s apart get 429 "Rate limit exceeded") |

Latency is one off-peak run from one machine; p95 of 20 is the second-largest value.

**LLM model probe** (16 synthetic utterances × 4 fields, gold written before running; Tamil and Kannada rows not human-reviewed):

| Model | Schema-valid first attempt | Fields right | hi | hinglish | ta* | kn* | Quote verbatim | Median | p95 | USD |
|---|---|---|---|---|---|---|---|---|---|---|
| google/gemini-2.5-flash-lite | 16/16 | 62/64 | 15/16 | 16/16 | 15/16 | 16/16 | 11/12 | 0.98 s | 1.05 s | 0.000859 |
| openai/gpt-4.1-nano | 16/16 | 58/64 | 16/16 | 16/16 | 13/16 | 13/16 | 9/12 | 0.92 s | 1.69 s | 0.000875 |
| mistralai/mistral-small-3.2-24b-instruct | 16/16 | 62/64 | 16/16 | 15/16 | 16/16 | 15/16 | 12/12 | 1.10 s | 2.67 s | 0.000533 |

Default: `mistralai/mistral-small-3.2-24b-instruct`, in `defaults.toml`, overridable with `SAMAJH_LLM_MODEL`. It tied Gemini Flash-Lite on fields and won on cost. n=16 cannot separate them. Their errors differ in kind: Gemini's two were quote formatting, which a substring check catches; Mistral's two were meaning (`product_kind`, `paid_from_loan`), which code cannot catch. `gpt-4.1-nano` rewrote amounts in Tamil and Kannada.

**Independent review (Fable, high effort, offline, did not write the code).** No critical finding; no key leak, wrong-entry cache hit or double-fire found on the default path. It proved 15 findings with scripts; 13 were fixed, each with a test shown to fail on the old code (62 new-test failures against the pre-fix copy, 0 after):

1. LLM: an in-body error on a gzip-compressed 200 raised `httpx.DecodingError` with no retry and no ledger row. Fixed.
2. Batch: a job whose start answered 409, timed out, or was resumed left no credits in the ledger. Fixed: one `batch.billed` row per job.
3. Error codes were not redacted; Gnani truncated before redacting. Fixed in both clients and the probe.
4. A key with stray whitespace was printed in full by a chained httpx traceback. Fixed: constructors reject malformed keys, `from_env` strips.
5. TTS accepted any 200 body as audio for non-WAV containers, and a zero-sample or wrong-rate WAV. Fixed: content type, duration and sample rate are checked before caching.
6. LLM USD cap: `usd_cap=0` still sent one request; a missing `usage.cost` counted as zero. Fixed.
7. Completed batch job without a `transcript_url` forgot the job and would bill a second one. Fixed.
8. Injected `httpx.Client` could follow redirects or carry the key to the storage host. Fixed.
9. `GNANI_CREDIT_CAP=nan` disabled the guard. Fixed.
10. `httpx.DecodingError` escaped untyped. Fixed in the retry loop.
11. Cache key: `temperature=0` vs `0.0` differed; base URL was in no key. Fixed.
12. A WAV whose data size field is 0 passed the 30 s refusal; `audio_format` was unchecked at run time. Fixed.
13. Three mutations survived the test suite (batch requests without the lock, no cache re-check inside the lock, batch start without the cap). Tests added; all three are now killed.

Not fixed, by decision: `timeout` is httpx's per-read timeout, so a server that drips bytes can hold the lock longer than `timeout`; keyterms in a different order pay twice (safe direction); two threads making the same uncached LLM request both pay.

The fix round was checked by its tests, by mutation runs and by my reading. It was not put through a second independent review.

Secret scan of the working tree after all runs: 825 files outside `.env`, `.venv` and `.git`; none contains either key or its first 16 characters.

## 3. Claims

**Verified live** (all in `api-probe-iter1.md`): base URL and `X-API-Key-ID`; `POST /stt/v3` serves both models and `model` selects, default `prisma-v2.5`; `format` values per model (`codemix` and `transliterate` are v3.0 format values); `indic-auto` and comma-separated language lists on v3.0, rejected on v2.5; `keyterms` changes output; `topic` validation; 30 s limit; v2.5 `output.literal`; `POST /api/v1/tts/inference` for both Timbre versions, all six containers and their content types, 8 and 16 kHz, speed range; voice lists (13 on v3.0, 73 on v2.5); the full Batch flow with segment times and speaker ids; 404 for an unknown job and 409 for a second start; five error body shapes; no credit, usage or rate-limit header anywhere; no usage endpoint at guessed paths; OpenRouter `usage.cost`, `/key` balance, strict structured output.

**Docs and live differ** (live wins): docs say number formatting is Hindi and English only, live gives digits for Tamil and Kannada on both models; docs list 42 v2.5 voices, the API lists 73; the TTS `language` field is not validated by the server (any string returns 200); every Timbre WAV has `0xFFFFFFFF` size fields, which the client repairs; Batch speaker ids started at 1.

**Corrections to CLAUDE.md's API facts** (not edited, outside my lane): `codemix` is a `format` value on v3.0, not a separate option; v2.5 `format=transcribe` works beyond Hindi and English; a streaming session does not count as the one active request, so iteration 2's "bot audio is pre-generated so a live call only uses STT" constraint is looser than assumed if streaming is used.

**Still unverified:** the two credit rates (estimates from one dashboard reading); whether a running Batch job counts as the active request; voice gender and preferred language (docs only); `bias_list` effect; the 504 body shape; behaviour of a clip under 0.1 s; `speaker_id -1` on empty segments; the Batch 10 MB and 4 h limits; how streaming is billed.

## 4. Failures, gaps, changes from the spec

- **Changed from the spec.** `samajh/clients/gnani` is a package of four files plus the CLI, not one `gnani.py`; imports and `python -m samajh.clients.gnani` work as specified. Substitution rules, `previous_text` and `speaker_names` are not wrapped (not in the spec, not needed yet). Voices are a static table taken from the API's own error message, because there is no list endpoint.
- **True credit cost cannot be measured from the API.** Only the dashboard shows it. The guard runs on estimates rounded up from the pilot reading (STT 0.010 credits per second, TTS 0.002 per character). To replace them with measurements, read the STT and TTS totals at app.gnani.ai, subtract the pilot's 1.7 and 1.2, and divide by: STT 266.0 audio seconds over 68 calls, TTS 2,715 characters over 67 calls, Batch 25.74 seconds over 2 jobs (as of 04:46 IST; later totals from the `ledger` command).
- **Lock hold time.** At default settings one failing call can hold the Gnani lock for about 4.5 minutes (5 attempts × 30 s timeout plus backoff). The iteration 2 backend should build its client with a smaller `RetryPolicy` and `timeout` for live turns.
- **The raw probe script bypasses the lock.** Do not run `tests/clients/probes/gnani_probe.py` while anything else uses the key.
- **LLM cap is per client instance.** A script that builds a new client per call gets a fresh cap each time; the ledger total is the only cross-run number.
- **Crash windows in Batch.** A crash between the create response and writing the resume file leaves one unstarted (unbilled) job behind. A crash between the `batch.billed` row and the resume-file rewrite counts that job twice, which over-counts.
- **Cache keys changed during the fix round** (base URL added), so the 62 entries cached before it are orphaned. Re-paying them costs under 1 credit and about 0.002 USD.
- **Diarization evidence is thin.** Two TTS clips. Two similar female voices joined without a pause came back as one segment and one speaker; a female and a male voice with 0.7 s of silence came back as two segments with the boundary 0.05 s after the true change. Nothing here is on real phone audio.
- **Ledger timestamps for Gnani rows have one-second resolution.**
- The first Batch probe looked hung for 10 minutes because my probe did not retry a rate-limited start. The job itself was fine; the client retries that case.

## 5. Spend

- **Gnani:** 11.58 estimated credits in the ledger against a budget of 40. That is 2.96 measured for the earlier pilot (one imported row), 5.88 estimated for the raw probe (115 imported rows) and 2.74 estimated for calls through the client. At the unrounded pilot rates this iteration's own share is about 7.4 credits. No call returned 5xx.
- **OpenRouter:** 0.0023 USD by the ledger (51 HTTP attempts), plus about 0.00005 USD of raw parameter checks before the client existed. `/key` usage agreed with the probe's summed `usage.cost` exactly (0.002267). Budget was 1 USD.

## 6. Next iteration

1. Read the dashboard once and replace the two credit rates in `defaults.toml` with measured ones.
2. W1 amount normaliser: use v2.5's `output.literal` (words and digits from one call), and handle the forms v3.0 writes: `1.5 लाख`, `2.25 लाख`, `2.5 करोड़`, `साढ़े 3,000`, and Batch writing "loan" where REST writes "लोन".
3. W5 extractor: rerun `llm_model_probe.py`-style selection on the frozen gold set before trusting the default; a quote-is-substring check would catch the kind of error Gemini made.
4. Iteration 2 backend: a tighter `RetryPolicy` and timeout for live turns; decide whether to use streaming, which does not occupy the active-request slot; if so it should still take `single_flight` only around REST calls.
5. Test Batch diarization on a real two-party 8 kHz recording made by consenting teammates before the evidence log depends on speaker labels.
6. Add `SAMAJH_LLM_MODEL`, `SAMAJH_LLM_USD_CAP` and `SAMAJH_STATE_DIR` to `.env.example`, and correct the three CLAUDE.md API facts listed in section 3.
7. Optional hardening left open: a total per-attempt deadline, and a second independent review of the fix round.
