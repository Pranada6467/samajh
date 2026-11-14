"""The seal of an after-call case file (format: `samajh.evidence`, "Case seal").

`new_case` fills `CaseSeal.inputs`; `seal_case` (called by `SessionStore.write_case`) sets the two
digests over the bytes actually written; `verify_case` re-checks them and, given the session
directory, that the case was made from that session's chain as it then stood.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from samajh.evidence.digest import REPO, after_epoch, digest, file_sha256
from samajh.evidence.session import chain_entries, describe_entry, session_seal

PROMPT_FILES = ("samajh/extract/_prompt.py", "samajh/extract/_wire.py")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SealInputs(_Model):
    session_head: str | None = None
    session_entries: int | None = None
    session_seal: str | None = None
    recording_sha256: str | None = None
    record_sha256: str
    extraction: dict[str, Any]  # {model, prompt_sha256}
    code: dict[str, str | None]  # digest.code_version()


class CaseSeal(_Model):
    version: Literal[1] = 1
    inputs: SealInputs
    inputs_sha256: str | None = None  # set by `seal_case` when written
    content_sha256: str | None = None


def prompt_sha256() -> str:
    """Digest over the sha256 of the extraction prompt and wire-schema source files."""
    return digest([file_sha256(REPO / p) for p in PROMPT_FILES])


def seal_case(data: bytes) -> bytes:
    """The case JSON with `seal.inputs_sha256` and `seal.content_sha256` set; unchanged (re-encoded)
    when it has no seal."""
    case = json.loads(data)
    seal = case.get("seal") if isinstance(case, dict) else None
    if not isinstance(seal, dict):
        return data
    seal["inputs_sha256"] = digest(seal["inputs"])
    seal["content_sha256"] = None
    seal["content_sha256"] = digest(case)
    return json.dumps(case, indent=2, ensure_ascii=False).encode()


@dataclass(frozen=True)
class CaseCheck:
    status: Literal["verified", "mismatch", "unverifiable"]
    problem: str | None
    changed_after_seal: list[str] = field(default_factory=list)


def verify_case(case_bytes: bytes, session_dir: Path | None = None) -> CaseCheck:
    try:
        case = json.loads(case_bytes)
    except ValueError:
        return CaseCheck("mismatch", "case.json does not parse")
    if not isinstance(case, dict):
        return CaseCheck("mismatch", "case.json is not an object")
    seal = case.get("seal")
    if not isinstance(seal, dict):
        session_id = session_dir.name if session_dir is not None else case.get("session_id")
        if isinstance(session_id, str) and after_epoch(session_id):
            return CaseCheck("mismatch", "dated after the evidence epoch but has no seal")
        return CaseCheck("unverifiable", "written before the case seal")
    content = seal.get("content_sha256")
    unsealed = {**case, "seal": {**seal, "content_sha256": None}}
    if content is None or content != digest(unsealed):
        return CaseCheck("mismatch", "content_sha256 does not match the case")
    inputs = seal.get("inputs") or {}
    if seal.get("inputs_sha256") != digest(inputs):
        return CaseCheck("mismatch", "inputs_sha256 does not match seal.inputs")
    rec = inputs.get("recording_sha256")
    case_rec = (case.get("recording") or {}).get("sha256")
    if rec is not None and case_rec is not None and rec != case_rec:
        return CaseCheck("mismatch", "seal recording_sha256 differs from the case's recording")
    if session_dir is None:
        return CaseCheck("verified", None)
    entries = chain_entries(session_dir)
    if inputs.get("session_head") is None:
        if entries:
            return CaseCheck("mismatch", "the seal names no session_head but the session has a chain")
        return CaseCheck("verified", None)
    n = inputs.get("session_entries")
    if (
        not isinstance(n, int)
        or n < 1
        or n > len(entries)
        or entries[n - 1].get("hash") != inputs["session_head"]
    ):
        return CaseCheck(
            "mismatch",
            f"session_head is not the hash of session chain entry {n - 1 if isinstance(n, int) else n}",
        )
    sealed = inputs.get("session_seal")
    if sealed is not None and (rec is None or sealed != session_seal(inputs["session_head"], rec)):
        return CaseCheck("mismatch", "session_seal does not recompute from session_head and recording_sha256")
    return CaseCheck("verified", None, [describe_entry(e) for e in entries[n:]])
