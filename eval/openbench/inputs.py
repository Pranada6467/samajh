"""Write the W7 job file for a set: every audio file Prisma read in the held-out amounts evaluation.

    uv run python eval/openbench/inputs.py amounts-v2|realvoice

Condition files are keyed by a step key, not by content, so every .wav under the audio tree is hashed
and each Prisma row's audio_sha256 is looked up in that index.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import store  # noqa: E402

SOURCES = {
    "amounts-v2": (store.REPO / "eval/amounts_v2/run/stt.jsonl", store.REPO / ".samajh/evalkit/amounts-v2"),
    "realvoice": (store.REPO / ".samajh-realvoice/run/stt.jsonl", store.REPO / ".samajh-realvoice/evalkit"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(set_name: str) -> list[dict]:
    stt_path, audio_root = SOURCES[set_name]
    index: dict[str, Path] = {}
    for sub in ("clips", "conditions"):
        for wav in sorted((audio_root / sub).rglob("*.wav")):
            index.setdefault(sha256(wav), wav.resolve())
    audio_of: dict[tuple[str, str], str] = {}
    for row in store.read_jsonl(stt_path):
        key = (row["item_id"], row["condition"])
        prev = audio_of.setdefault(key, row["audio_sha256"])
        if prev != row["audio_sha256"]:
            raise SystemExit(f"{key} has two audio hashes: {prev} and {row['audio_sha256']}")
    missing = sorted(k for k, h in audio_of.items() if h not in index)
    if missing:
        raise SystemExit(f"{len(missing)} audio files not found, e.g. {missing[:5]}")
    return [
        {"set": set_name, "item_id": i, "condition": c, "audio_path": str(index[h]), "audio_sha256": h}
        for (i, c), h in sorted(audio_of.items())
    ]


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in SOURCES:
        raise SystemExit(f"usage: inputs.py {'|'.join(SOURCES)}")
    jobs = build(sys.argv[1])
    out = store.jobs_path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(j, ensure_ascii=False, sort_keys=True) + "\n" for j in jobs), encoding="utf-8")
    print(out)
    for cond, n in sorted(Counter(j["condition"] for j in jobs).items()):
        print(f"  {cond}: {n}")


if __name__ == "__main__":
    main()
