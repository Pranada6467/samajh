"""Shared contract for W7: where jobs and transcripts live, and the row format. Standard library only,
so the local-model environment (which does not install `samajh`) can import it too.

A job is one audio file to transcribe: {"set", "item_id", "condition", "audio_path", "audio_sha256"}.
Jobs for a set are written by `inputs.py` to `.samajh/openbench/jobs/<set>.jsonl`.

A transcript row is one system's reading of one job:
  {"set", "item_id", "condition", "system", "audio_sha256", "text", "error", "compute_s", "meta"}
`text` is the system's output exactly as returned (no rewriting); `error` is null or a short string,
and a row with an error carries text "". Rows are appended; the last row for a key wins.

Transcripts of the synthetic amounts set (TTS text, ours) are kept in the repository under
`eval/openbench/runs/amounts-v2/`. Transcripts of dataset audio (public clips, FLEURS) stay outside it,
under `.samajh/openbench/runs/<set>/`: the repository holds no dataset text.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / ".samajh" / "openbench"
JOBS = ROOT / "jobs"
SETS = ("amounts-v2", "realvoice", "fleurs")


def runs_dir(set_name: str) -> Path:
    if set_name not in SETS:
        raise ValueError(f"unknown set {set_name!r}")
    if set_name == "amounts-v2":
        return REPO / "eval" / "openbench" / "runs" / "amounts-v2"
    return ROOT / "runs" / set_name


def jobs_path(set_name: str) -> Path:
    return JOBS / f"{set_name}.jsonl"


def transcripts_path(set_name: str, system: str) -> Path:
    return runs_dir(set_name) / f"{system}.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def latest(rows: list[dict]) -> dict[tuple[str, str], dict]:
    """The last row per (item_id, condition)."""
    out: dict[tuple[str, str], dict] = {}
    for row in rows:
        out[(row["item_id"], row["condition"])] = row
    return out


def done(path: Path) -> set[tuple[str, str, str]]:
    """(item_id, condition, audio_sha256) already transcribed without error."""
    return {
        (r["item_id"], r["condition"], r["audio_sha256"])
        for r in latest(read_jsonl(path)).values()
        if r.get("error") is None
    }
