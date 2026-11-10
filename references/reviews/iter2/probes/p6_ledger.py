"""Verifier probe for P6: match run rows to the Gnani client ledger by cache key; times and credits.

  uv run python references/reviews/iter2/probes/p6_ledger.py
Prints timestamps, counts and credit sums only.
"""
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
ledger = [json.loads(line) for line in (REPO / ".samajh/ledger.jsonl").read_text().splitlines()]
gnani = [r for r in ledger if r["provider"] != "openrouter"]
print("ledger gnani rows", len(gnani), Counter(r["provider"] + "/" + r["kind"] for r in gnani))

for name, run in (("tts", REPO / "eval/amounts_v2/run"), ("realvoice", REPO / ".samajh-realvoice/run")):
    keys = {}
    for f in ("voice.jsonl", "stt.jsonl"):
        p = run / f
        if p.exists():
            for line in p.read_text().splitlines():
                r = json.loads(line)
                keys[r["cache_key"]] = f
    rows = [r for r in gnani if r["cache_key"] in keys]
    live = [r for r in rows if not r["cache_hit"]]
    print(f"\n[{name}] run keys {len(keys)}; ledger rows with those keys {len(rows)}, live {len(live)}")
    print("  first ledger ts", min(r["ts"] for r in rows), "last", max(r["ts"] for r in rows))
    print("  first live ts", min(r["ts"] for r in live))
    print("  status", Counter(r["status"] for r in rows), "errors", Counter(r["error_code"] for r in rows if r["error_code"]))
    print("  est credits live", round(sum(r["est_credits"] or 0 for r in live), 4),
          "all rows", round(sum(r["est_credits"] or 0 for r in rows), 4))
    print("  by kind", {k: round(sum(r["est_credits"] or 0 for r in live if r["kind"] == k), 3) for k in {r["kind"] for r in live}})
    print("  cache hits in run files:", Counter(json.loads(l)["cache_hit"] for f in ("voice.jsonl", "stt.jsonl") if (run / f).exists() for l in (run / f).read_text().splitlines()))
    # was any of these keys first seen before the freeze?
    first = min(r["ts"] for r in rows)
    print("  any row before 2026-11-10T06:39:21?", any(r["ts"] < "2026-11-10T06:39:21" for r in rows))

# Gnani activity in the window before the TTS freeze
win = [r for r in gnani if "2026-11-10T06:00" <= r["ts"] < "2026-11-10T06:41:37"]
print("\ngnani ledger rows 06:00-06:41:37 UTC:", len(win), Counter((r["kind"], r["ts"][:16]) for r in win).most_common(8))
