"""Who may sign in to the review pages: `<state>/ops/reviewers.json`.

    {"<name>": {"token_sha256": "<sha256 hex of the token>", "added_at": "<UTC ISO time>"}}

Only the token's sha256 is stored, and the file is written with mode 0600. A token is made once by
`python -m samajh.ops reviewer add NAME` and printed then; it cannot be shown again.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path

FILE = "reviewers.json"


class NoReviewers(Exception):
    """No reviewers file, or it names nobody."""


def _token_sha256(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def load(ops_root: Path) -> dict[str, dict[str, str]]:
    try:
        data = json.loads((ops_root / FILE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise TypeError(f"{ops_root / FILE} is not a JSON object")
    return data


def _save(ops_root: Path, data: dict[str, dict[str, str]]) -> None:
    ops_root.mkdir(parents=True, exist_ok=True)
    path = ops_root / FILE
    temporary = path.with_name(f".{FILE}.{os.getpid()}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def add(ops_root: Path, name: str, now: datetime | None = None) -> str:
    """Add a reviewer and return the new token (shown once). An existing name gets a new token."""
    name = name.strip()
    if not 1 <= len(name) <= 80:
        raise ValueError("a reviewer's name is 1 to 80 characters")
    token = secrets.token_urlsafe(32)
    data = load(ops_root)
    data[name] = {
        "token_sha256": _token_sha256(token),
        "added_at": (now or datetime.now(UTC)).isoformat(),
    }
    _save(ops_root, data)
    return token


def remove(ops_root: Path, name: str) -> bool:
    data = load(ops_root)
    if name not in data:
        return False
    del data[name]
    _save(ops_root, data)
    return True


def names(ops_root: Path) -> list[str]:
    return sorted(load(ops_root))


def who(ops_root: Path, token: str) -> str | None:
    """The reviewer whose token this is, or None. Raises `NoReviewers` when nobody is set up.
    Compares sha256s with `hmac.compare_digest`, over every entry."""
    data = load(ops_root)
    if not data:
        raise NoReviewers
    offered = _token_sha256(token)
    found = None
    for name, entry in data.items():
        stored = entry.get("token_sha256", "") if isinstance(entry, dict) else ""
        if hmac.compare_digest(offered.encode(), str(stored).encode()):
            found = name
    return found
