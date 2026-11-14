"""The one way this repo turns evidence into a digest. Every chain, seal and manifest uses it.

`canonical(obj)` is JSON with sorted keys, no spaces and UTF-8 text (not \\u escapes), from a value
that is already plain JSON (`model_dump(mode="json")`, or `json.loads` of a file). A float is written
as Python's `repr` writes it, so a value read back from a file digests the same as before it was written.

A digest is the lower-case hex sha256. Each kind of digest is tagged (`tagged`), so a digest of
one kind can never be passed off as another: an entry hash is never a valid seal.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Any

GENESIS = "0" * 64  # the `prev` of the first entry of any chain
REPO = Path(__file__).resolve().parents[2]
# Everything this code writes after this instant carries its evidence (chain, seal, ledger line,
# prev_sha256). Missing evidence on something dated at or after it is a mismatch, not "legacy".
EVIDENCE_EPOCH = "2026-11-14T00:00:00Z"
_SESSION_TIME = re.compile(r"^(\d{8}T\d{6})-[0-9a-f]{12}$")


def epoch() -> datetime:
    return datetime.fromisoformat(EVIDENCE_EPOCH)


def session_time(session_id: str) -> datetime | None:
    """The UTC time in a session id (`YYYYMMDDTHHMMSS-<12 hex>`), or None for any other string."""
    m = _SESSION_TIME.match(session_id or "")
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=UTC)
    except ValueError:
        return None


def after_epoch(when: datetime | str | None) -> bool:
    """Whether a time (a datetime, an ISO string or a session id) is at or after the evidence epoch.
    An unknown or unparseable time is not after it."""
    if isinstance(when, str):
        t = session_time(when)
        if t is None:
            try:
                t = datetime.fromisoformat(when)
            except ValueError:
                return False
        when = t
    if when is None:
        return False
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return when >= epoch()


def canonical(obj: Any) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(obj: Any) -> str:
    """sha256 of `canonical(obj)`."""
    return sha256_hex(canonical(obj))


def tagged(tag: str, *parts: str) -> str:
    """sha256 of "<tag>\\n<part>\\n<part>..." : a digest of named parts, e.g.
    `tagged("samajh-session-seal-v1", head, recording_sha256)`."""
    return sha256_hex("\n".join((tag, *parts)).encode())


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


@cache
def source_sha256() -> str:
    """sha256 over every `samajh/**/*.py` file's relative path and sha256, sorted by path: the code
    that ran, whether or not it was committed."""
    root = REPO / "samajh"
    rows = sorted(
        (p.relative_to(REPO).as_posix(), file_sha256(p))
        for p in root.rglob("*.py")
        if "__pycache__" not in p.parts
    )
    return digest(rows)


@cache
def git_commit() -> str | None:
    """`git rev-parse HEAD` of the repository, or None when git or the repository is absent.
    A tree with uncommitted changes still names its last commit: `source_sha256` is the exact code."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, timeout=5, check=True
        )
    except (OSError, subprocess.SubprocessError):
        return None
    commit = out.stdout.strip()
    return commit or None


@cache
def data_sha256() -> str:
    """sha256 over every `samajh/**/*.toml` and `data/prompts/*.toml` file's relative path and
    sha256, sorted by path: the bot's lines and the server settings that ran."""
    files = [*(REPO / "samajh").rglob("*.toml"), *(REPO / "data" / "prompts").glob("*.toml")]
    rows = sorted((p.relative_to(REPO).as_posix(), file_sha256(p)) for p in files if p.is_file())
    return digest(rows)


def code_version() -> dict[str, str | None]:
    return {"source_sha256": source_sha256(), "data_sha256": data_sha256(), "git_commit": git_commit()}
