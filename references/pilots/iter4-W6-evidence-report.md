# W6 (iteration 4, wave 2): a tamper-evident evidence bundle

2026-11-14, on `dev` at abbf0cd plus uncommitted work. Orchestrated by an Opus worker. Builders: Opus at low effort, four runs: A session chain and case seal; B decisions, token and pages; C export, verify and retention; D the fix round. The independent check was one round by Opus at high effort, which wrote none of the code. No Gnani calls and no LLM calls.

The interface was written by the orchestrator before the builders started: the format contract in `samajh/evidence/__init__.py` and `samajh/evidence/digest.py` (canonical JSON, sha256, tagged digests, code version). The orchestrator also changed one assertion in `tests/server/test_casefile.py` after the fix round.

## What it gives, and what it does not

It detects a change made after the fact to any of these:
- a session log, its turn audio or `call.wav`;
- a sealed case file;
- an analysed call record;
- a recorded decision;
- an exported bundle.

The verifier names the first entry that does not match. It does **not** detect someone who also rebuilds every chain, seal, head file and manifest. Anyone with this code and write access to the files can do that. It is not a signature and not a trusted timestamp: nothing shows who wrote an entry or when. What turns "the files agree with each other" into "this is what was exported then" is the bundle's `root_sha256`, printed at export, copied somewhere else at that time.

## What was built

- **Session chain** (`samajh/evidence/session.py`, called from `SessionStore.save` in `samajh/server/sessionlog.py`).
  - Every save appends to `sessions/<id>/chain.jsonl`: one entry when the session fields change, and one for each event that is new or whose JSON or audio sha256 changed. Each entry carries the hash of the one before.
  - `session.json` gains `chain: {entries, head, seal}`. The seal covers the head and `recording.sha256`.
  - Entries hold digests only. The dialogue state is never put in the chain, only its digest. The year-of-birth reply's text is in no chain file (tested).
  - All existing fields, W2's included, are unchanged, and `LOG_VERSION` is still 2.
- **Case seal** (`samajh/evidence/case_seal.py`; `casefile.py`, `SessionStore.write_case`). `case.json` gains `seal`:
  - its inputs: the session head, entry count and seal; the recording sha256; the record digest; the extraction model and the prompt files' digest; `code_version()`, which covers the source, the `.toml` files and `data/prompts`;
  - `inputs_sha256`;
  - `content_sha256`, computed over the bytes actually written, including the app's failure path.
- **Decisions bound and chained** (`samajh/evidence/decisions.py`, `samajh/ops/store.py`, `views.py`, `model.py`).
  - Each new `dispositions.jsonl` line carries `case_digest`, `prev_sha256` and `reviewer_auth`.
  - The case page sends back the digest it showed. A case that changed since then gives 409, and nothing is recorded.
  - Head files (`dispositions.head.json`, `calls.chain.head.json`) protect the last line.
- **Call ledger** (`samajh/evidence/ledger.py`): `ops/calls.chain.jsonl` chains every `ops/calls/<id>.json` the store writes.
- **Export, verify and check** (`samajh/evidence/bundle.py`, `__main__.py`):
  - `uv run python -m samajh.evidence export --case ID --out DIR [--state S] [--with-recording]`
  - `uv run python -m samajh.evidence verify DIR`
  - `uv run python -m samajh.evidence check --state S`
  - The bundle holds: the call record and its ledger entry; the case file; the session chain, fields and events, with the year-of-birth reply only as a digest stub; quotes with clips cut sample-exact from `call.wav`; the recording's hash; this case's decision lines with the hash list of the whole log; a manifest with every file's sha256 and `root_sha256`.
  - `--with-recording` adds `call.wav` and the turn audio. It warns that `call.wav` holds the spoken year reply.
  - Export verifies the source first and verifies its own bundle afterwards. On a mismatch it refuses and writes nothing.
  - Exit codes: 0 verified, 1 mismatch, 2 usage or refused, 3 unverifiable (legacy), 4 warning (a decision made on another version of the case).
- **Hardening:**
  - Bearer token on every `/api/review/*` route. `uv run python -m samajh.ops reviewer add NAME` prints a token once and stores only its sha256. The recorded reviewer is the token's name.
  - `GET /api/review/whoami`.
  - A 16 KiB bound on the decision body (413, chunked or by Content-Length).
  - Pages: a token sign-in, no free-text name field, and playback that pauses at the quote's `end_s`.
  - `uv run python -m samajh.ops retention [--days N] [--delete]`. It is off unless `--days` or `SAMAJH_RETENTION_DAYS` is given, and without `--delete` it only lists. It keeps active sessions and the sessions of referrals with no final decision, ingested or not. Each deletion is logged to `ops/retention.jsonl`. `ops/calls` (the transcript) and the decisions are not deleted.
- **Old data:**
  - A session, case or decision dated before `EVIDENCE_EPOCH` (2026-11-14T00:00Z) with no chain or seal loads as before and is reported **unverifiable** (exit 3), not invalid.
  - The same gaps on anything dated after the epoch are a **mismatch**, so a new session cannot be made to look old.
  - An old session saved again by new code is "adopted": its chain starts there and says so.

## Measurements

- **Tests:** `uv run pytest tests/ops tests/evidence tests/server -q -m "not live" -p no:randomly` gave **967 passed, 1 deselected** (78 s, after the fix round). About 115 of these are new evidence tests, all behavioural (no snapshots), in `tests/evidence/` and four in `tests/server/test_casefile.py`.
- **Demo, re-run by the orchestrator:** `ops demo` into a new directory, then export of a referred case. Exit codes: export 0, verify 0, check 0. With one byte of `call-record.json` changed, verify exits 1, "case/call-record.json: sha256 or size does not match the manifest".
- **The independent checker's tamper table** (n = 47 tamper kinds over 4 FakeSpeech phone calls and the demo; its probes are in the scratchpad `checker/` directory).
  - **Caught before the fix:** one byte of a clip, of `call.wav` or of turn audio; reordered, renumbered or edited events; an edited quote; a decision's `case_id` changed; another case's decision copied in; a deleted middle line of a chain or decision log; an unresealed case edit; symlinks, `../` paths and extra files.
  - **Missed before the fix, then fixed and re-run** by builder D on the checker's probes:

    | Tamper | Exit and message after the fix |
    |---|---|
    | Phone bundle relabelled "simulated" | 1 |
    | Call record edited in `ops/calls` | `check` 1 and export 1, "sha256 differs from its line in calls.chain.jsonl" |
    | Downgrade to legacy (chain and seal stripped) | 1, "dated after the evidence epoch but has no chain" |
    | Last decision line deleted, moved or forged | 1, "the last line differs from dispositions.head.json" |
    | Quotes dropped, or cut to a fragment | 1 |
    | Ordinary reply replaced by a withheld stub | 1 |
    | `check` on a missing directory | 2 |
    | Malformed input that used to give tracebacks | 1, "MISMATCH … malformed" |
    | Duplicate manifest row | 1 |
    | Un-ingested referral under retention | kept |

    The re-run was done by the fix builder, not by the checker: the rules allow one check round.
- **Held up in the check:**
  - Concurrency: 6 processes × 15 decisions gave a valid chain, and 80 racing session saves still verify.
  - Floats: re-serialising `session.json` changes nothing.
  - Every token and 413 probe got the expected answer.
  - The year reply was absent from every default bundle.

## The checker's findings, in its words, and what was done

1. "Relabelling a phone bundle as `simulated` skips every phone check." **Fixed:** the source comes from the call record, and the phone files must be present exactly when the case is a phone case.
2. "The analysed call record in `ops/calls/<id>.json` has no seal." **Fixed:** the call ledger, checked by `check` and in the bundle. Export now verifies its own output. **Open:** the seal's `record_sha256` is not re-checked, because the bundle does not carry the loan record.
3. "Downgrade to 'legacy' is accepted." **Fixed** by the epoch rule. **Open:** a simulated call is dated by `batch.json` `created_at`, so editing that date and deleting the ledger still downgrades it.
4. "The last decision line is unprotected." **Fixed** with head files. Rewriting the head file too is not detected (the stated limit).
5. "`verify` does not check that the bundle is complete." **Fixed** for quotes and withheld stubs. **Open:** hiding this case's decisions by flipping the `case` flags in `decisions/chain.json`, or dropping the last decision with the manifest head rewritten, still verifies: the bundle holds other cases' lines only as hashes.
6. "A resealed case or an edited call record yields exit 3 … the same code as … a legacy case." **Fixed:** a call-record edit is now 1, and a warning is 4, apart from unverifiable (3). A fully resealed case still gives only warning 4 on a decided case and passes an undecided one (the stated limit).
7. "Retention deletes an undecided referral's session when the case is not ingested yet." **Fixed**, together with `--days` < 1 refused and a retention-aware export message.
8. "The token protects only `/api/review`." **Not fixable here:** the other routes are in `app.py`. See "Needed from others".
9. "`check --state /nonexistent/typo` exits 0." **Fixed:** it exits 2.
10. "`verify` crashes with a traceback." **Fixed.**
11. Small items:
    - Duplicate manifest rows: **fixed**.
    - `code_version` did not cover the `.toml` prompts and settings: **fixed**.
    - The seal's `extraction.model` is null with the fake LLM: **open**, not checked with the real client.
    - The `end_s` stop can overshoot by about 250 ms and was **not run in a browser**.

## Left open

- The stated limit: anyone who rebuilds every chain, seal, head and manifest. Keep a copy of `root_sha256` elsewhere.
- Without `--with-recording`, a clip changed together with its `clip_sha256` and the manifest still verifies, because the clips cannot be re-cut. With the recording it is caught.
- A withheld stub's `reply_to` and `type` are outside its digest.
- With `--with-recording`, the audio of an error event that carried the year reply is exported, as is `call.wav`.
- The pages were rendered in headless Chrome (16 renders, clean) against a review-only server. The sign-in form, posting a decision, the 409 message and the `end_s` stop were not exercised in a browser.
- In the user's state, any decision line chained before head files existed reports "dispositions.head.json is missing" until the next decision is recorded. None is expected.

## Needed from others

- **`samajh/server/app.py` owner (W5):**
  - Put these behind the review token: `GET /api/sessions/{id}/case`, the session routes, and `/api/sessions/{id}/recording.wav`. The recording holds the spoken year reply, and an `<audio>` element cannot send a header, so it needs a short-lived signed URL or a cookie.
  - `POST /api/sessions/{id}/events/{seq}/browser` lets anyone append to a decided session's chain. It shows as "changed after seal", not a mismatch.
  - Optionally, a `[retention] days` setting in `settings.toml`.
- **Documentation worker:**
  - The review pages now need `uv run python -m samajh.ops reviewer add NAME`, and the token goes into the page.
  - Document the new commands, the exit codes and the epoch rule.
  - Use the wording below. `wording.ACCESS_NOTICE` was rewritten.
- **Wording:**
  - **Allowed:** "detects a change made after the fact unless the chain heads and seals are rebuilt too"; "a default bundle carries no text of the year-of-birth reply"; "retention is off by default".
  - **Forbidden:** "tamper-proof"; "verify detects any change"; "a bundle that verifies is complete"; "the recording needs a reviewer token".

## Test command

`uv run pytest tests/ops tests/evidence tests/server -q -m "not live" -p no:randomly` gave 967 passed, 1 deselected, 0 failed (78.4 s), at the end of the fix round.
