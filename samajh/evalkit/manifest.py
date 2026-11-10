"""The manifest: one JSON object per line, each an utterance to voice and the gold to score against.

The format is general on purpose: the amounts set uses it now and the scenario set will later.
A manifest is frozen by its sha256 before any audio is made; `load_manifest` refuses a file whose
bytes do not match the hash the experiment names.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import Field, JsonValue, ValidationError

from samajh.types import Frozen, Language


class ManifestError(Exception):
    """The manifest is missing, malformed, or not the frozen file the experiment names."""


class Item(Frozen):
    id: str = Field(min_length=1)
    language: Language
    text: str = Field(min_length=1)
    gold: dict[str, JsonValue]
    tags: dict[str, str] = Field(default_factory=dict)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(path: Path, *, expect_sha256: str) -> tuple[Item, ...]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ManifestError(f"cannot read manifest {path}: {exc.strerror}") from None
    actual = sha256_hex(data)
    if actual != expect_sha256:
        raise ManifestError(f"{path} has sha256 {actual}, the experiment froze {expect_sha256}")
    items: list[Item] = []
    for number, line in enumerate(data.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            items.append(Item.model_validate(json.loads(line)))
        except (ValueError, ValidationError) as exc:
            raise ManifestError(f"{path}:{number}: {exc}") from None
    if not items:
        raise ManifestError(f"{path} has no items")
    ids = [item.id for item in items]
    if len(set(ids)) != len(ids):
        raise ManifestError(f"{path} has duplicate item ids")
    return tuple(items)
