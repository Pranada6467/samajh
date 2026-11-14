"""Tamper-evident evidence: a hash chain per phone session, a sealed case file, reviewer decisions
bound to the case they were made on, and an export bundle with a verifier.

What it gives: a change made after the fact to a session log, its audio, a case file or a recorded
decision is detected, and the verifier names the first entry that does not match, unless whoever made
the change also rebuilt every chain head and seal after it (anyone with this code and write access to
the files can). It is not a signature and not a trusted timestamp: nothing here proves who wrote an
entry or when, only that the files agree with each other and with the digests written down at the time.
A digest copied somewhere else when it was made (the bundle's `root_sha256`, printed by `export`) is
what turns "agrees with itself" into "is what was exported then".

All digests come from `samajh.evidence.digest` (canonical JSON, sha256 hex, tagged digests).

Evidence epoch: `digest.EVIDENCE_EPOCH` = 2026-11-14T00:00:00Z. Everything this code writes after it
carries its evidence, so missing evidence on something dated at or after the epoch is a MISMATCH
("... dated after the evidence epoch but has no chain"), never "unverifiable": a session whose id
time (`YYYYMMDDTHHMMSS-…`, UTC) is at or after it with no chain; a case.json with no seal whose
session id is; a dispositions line with `recorded_at` at or after it and no `prev_sha256`; a call
file with no ledger line whose phone session id is, or (a simulated call) whose batch's
`ops/batch.json` `created_at` is. Only things dated before it may be UNVERIFIABLE (legacy).

Formats (version 1)
-------------------

Session chain: `<state>/sessions/<id>/chain.jsonl`, appended by `SessionStore.save`, one line per entry:

    {"i": 0, "prev": GENESIS | <hash of entry i-1>, "at": "<UTC ISO time>",
     "kind": "session" | "event", "seq": <event seq> | null,
     "sha256": <digest of the session fields | of the event's JSON>,
     "audio_sha256": <sha256 of the event's audio file> | null,
     "adopted": true            (only on entry 0 of a session first saved before the chain existed)
     "hash": <digest(entry without "hash")>}

  A "session" entry is appended whenever the session-level fields change: `session_fields(log)`, every
  SessionLog field except `events`, `dialogue_state`, `dialogue_undo` and `chain`, plus
  `dialogue_state_sha256` and `dialogue_undo_sha256` (the digests of those strings, never the strings).
  An "event" entry is appended for each event that is new or whose JSON or audio changed since the
  last entry for its seq. Entries carry digests, not content: the content stays in session.json.
  session.json gains `chain: {"version": 1, "entries": n, "head": <hash of the last entry>,
  "seal": <tagged("samajh-session-seal-v1", head, recording.sha256)> | null}`; `seal` is set once
  `recording` is. A session.json with no `chain` was written before this existed: unverifiable, not invalid.

Case seal: `case.json` gains `seal: {"version": 1, "inputs": {...}, "inputs_sha256", "content_sha256"}`.
  inputs: session_head, session_entries, session_seal, recording_sha256, record_sha256 (digest of the
  record's JSON), extraction {model, prompt_sha256 (the prompt and wire-schema source files)}, code
  (`digest.code_version()`). content_sha256 = digest(case JSON with seal.content_sha256 = null).

Decisions: each line of `<state>/ops/dispositions.jsonl` written from now on carries
  `case_digest` (`case_digest()` of the case when it was decided) and `prev_sha256` (sha256 of the
  raw bytes of the previous line, without its newline; GENESIS for the first line). Older lines have
  neither: they are covered from the first new line on, as the bytes it chains to.

Head files: after each append, under the store's lock, `ops/dispositions.head.json` and
  `ops/calls.chain.head.json` are replaced atomically with `{"lines": n, "head": <sha256 of the last
  line's raw bytes>}`. A log whose line count or last line differs from its head file, a missing head
  file while chained lines exist, or a missing log while the head says lines > 0, is a mismatch.

Call ledger: `ops/calls.chain.jsonl`, one line per call file written by `OpsStore.save_call` (or
  removed by `drop_unreferenced_session_calls`, with `sha256: null`):
  `{"i", "prev", "call_id", "sha256" (of the file's bytes), "at", "hash"}`, the same chain rules as the
  session chain. `check` verifies the chain, its head file and each call file against the latest line
  for it. A call file with no line: unverifiable before the epoch, mismatch after it.

Bundle (`samajh.evidence.bundle`): the case's source is the call record's `source.kind`; a manifest
  `source` or `session_id` that disagrees is a mismatch. A phone bundle must hold `case/case.json`,
  `session/fields.json`, `session/events.json` and (unless the session predates the epoch and its
  case seal names no session head) `session/chain.jsonl`; a simulated bundle holds none of them, no
  recording and no clips. A sealed case whose seal names no session head while a chain exists is a
  mismatch. `case/call-ledger.json` = `{"entry", "head", "lines", "batch_created_at"}`: the entry must
  recompute and name call-record.json's sha256. quotes.json must hold exactly the quotes of the case
  (phone: every flag and gap quote and `also` quote of case.json `evidence`; simulated: of the call
  record's `result`). A `withheld` stub in events.json is accepted only for a customer event whose
  `reply_to` bot event is present, not withheld, and has a last line tagged `step: second_check`.
  `export` runs `verify_bundle` on what it wrote and deletes it on a mismatch.

Exit codes (`python -m samajh.evidence`): 0 verified; 1 mismatch (also malformed input: "MISMATCH:
  <file>: malformed (<ExceptionType>)", never a traceback); 2 usage, an export refused (no such case;
  the session deleted by retention) or a `--state` with neither sessions/ nor ops/; 3 unverifiable
  (legacy, before the epoch); 4 warning (a decision made on a different version of this case: an
  earlier version, or the line was moved from another case). 4 wins over 3.

Not detected (the stated limits):
- Rewriting a log and its head file together (the head files sit beside the logs, writable by the
  same hand); likewise rebuilding every chain, seal, head and the bundle manifest. Only a copy of
  `root_sha256` (or of a head) kept elsewhere at the time catches that.
- In a bundle, a decision line dropped from the end with the manifest's `decisions_head` rewritten,
  and this case's decisions hidden by flipping the `case` flags in decisions/chain.json: the bundle
  carries only this case's lines, so without the other lines' content neither can be told apart.
- A withheld stub's `reply_to` and `type` are not covered by its digest (the digest is of the real
  event, which the bundle does not hold): a stub moved onto another reply to the year question is
  not caught.
- A simulated call is dated by its batch's `created_at`: editing batch.json's date to before the
  epoch and deleting the ledger downgrades simulated calls to unverifiable.
- Who wrote anything, or when: no signature, no trusted time.
"""
