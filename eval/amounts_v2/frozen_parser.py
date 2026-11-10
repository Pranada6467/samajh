"""The amount parser as it was at commit 59c12d9, imported under another name.

`samajh/amounts` changed after the held-out set was frozen (iteration 2, package P3a), so scoring
with the working copy would score a parser that may have been tuned on what this package found.
This module exports the parser's files at the pinned commit with `git archive` into a scratch
directory outside the repository, rewrites its absolute imports from `samajh.amounts` to
`samajh_amounts_59c12d9`, and imports it from there. `samajh.types` (outside the package) is
shared with the working copy; `git diff 59c12d9 -- samajh/types.py` should stay empty.

  from frozen_parser import load
  amounts = load()            # a module with parse_amount, Parsed, Ambiguous, ...
"""

from __future__ import annotations

import hashlib
import importlib
import io
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from types import ModuleType

COMMIT = "59c12d9"
NAME = f"samajh_amounts_{COMMIT}"
REPO = Path(__file__).resolve().parents[2]


def export(scratch: Path) -> Path:
    """Write the pinned package to `scratch/NAME/` (idempotent) and return `scratch`."""
    target = scratch / NAME
    if (target / "__init__.py").exists():
        return scratch
    archive = subprocess.run(
        ["git", "-C", str(REPO), "archive", "--format=tar", COMMIT, "samajh/amounts"],
        check=True,
        capture_output=True,
    ).stdout
    staging = scratch / f"{NAME}.partial"
    staging.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            if not member.isfile() or not member.name.endswith(".py"):
                continue
            source = tar.extractfile(member).read().decode("utf-8")
            out = staging / Path(member.name).name
            out.write_text(source.replace("samajh.amounts", NAME), encoding="utf-8")
    staging.rename(target)
    return scratch


def fingerprint(scratch: Path) -> str:
    """sha256 over the exported files (names and bytes), to name the parser in a report."""
    digest = hashlib.sha256()
    for path in sorted((scratch / NAME).glob("*.py")):
        digest.update(path.name.encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def load(scratch: Path | None = None) -> ModuleType:
    scratch = scratch or Path(tempfile.gettempdir()) / "samajh-frozen-parser"
    export(scratch)
    if str(scratch) not in sys.path:
        sys.path.insert(0, str(scratch))
    module = importlib.import_module(NAME)
    module.FINGERPRINT = fingerprint(scratch)  # type: ignore[attr-defined]
    return module
