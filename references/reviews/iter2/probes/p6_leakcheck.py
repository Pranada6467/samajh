"""Verifier probe for P6: no real-voice reference or Prisma transcript text, and no dataset audio,
in any tracked or untracked-but-not-ignored file. Prints file names, ids and counts only.

  uv run python references/reviews/iter2/probes/p6_leakcheck.py
"""
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
files = subprocess.run(["git", "-C", str(REPO), "ls-files", "--cached", "--others", "--exclude-standard"],
                       capture_output=True, text=True, check=True).stdout.split("\n")
files = [f for f in files if f and (REPO / f).is_file()]
audio_ext = {".wav", ".flac", ".mp3", ".parquet", ".arrow", ".ogg", ".m4a", ".opus"}
print("files scanned", len(files), "; audio/parquet files:", [f for f in files if Path(f).suffix.lower() in audio_ext][:20])

needles = {}
for r in map(json.loads, (REPO / ".samajh-realvoice/selected.jsonl").read_text().splitlines()):
    words = r["text"].split()
    for k in range(0, max(1, len(words) - 4), 3):
        frag = " ".join(words[k:k + 5])
        if len(frag) >= 20:
            needles[frag] = ("ref", r["id"])
for r in map(json.loads, (REPO / ".samajh-realvoice/run/stt.jsonl").read_text().splitlines()):
    for t in (r["text"], r.get("literal") or ""):
        words = t.split()
        for k in range(0, max(1, len(words) - 4), 3):
            frag = " ".join(words[k:k + 5])
            if len(frag) >= 20:
                needles[frag] = ("prisma", r["item_id"])
print("needles", len(needles))
hits = {}
for f in files:
    try:
        text = (REPO / f).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    for frag, (kind, iid) in needles.items():
        if frag in text:
            hits.setdefault(f, set()).add((kind, iid))
for f, s in sorted(hits.items()):
    print("HIT", f, len(s), sorted(s)[:5])
print("files with hits:", len(hits))
