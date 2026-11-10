"""Ledger rows attributable to the amounts run: spend, 504 counts, retry waits. Read-only, offline.

  uv run python references/reviews/iter1/probes/amounts_ledger.py
"""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "eval" / "amounts" / "run"


def jl(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def main() -> None:
    stt = jl(RUN / "stt.jsonl")
    voice = jl(RUN / "voice.jsonl")
    ledger = jl(ROOT / ".samajh" / "ledger.jsonl")
    keys_stt = {r["cache_key"]: r for r in stt}
    keys_voice = {r["cache_key"] for r in voice}
    mine = [e for e in ledger if e["provider"] == "gnani" and (e["cache_key"] in keys_stt or e["cache_key"] in keys_voice)]
    print(f"ledger rows {len(ledger)}; gnani rows {sum(e['provider'] == 'gnani' for e in ledger)}; rows with this run's cache keys {len(mine)}")
    print("by (kind, status, cache_hit):", dict(Counter((e["kind"], e["status"], e["cache_hit"]) for e in mine)))
    print(f"sum est_credits over those rows: {sum(e['est_credits'] for e in mine):.4f}")
    paid = [e for e in mine if e["status"] == 200 and not e["cache_hit"]]
    print(f"paid (200, not cache hit): {len(paid)}; est {sum(e['est_credits'] for e in paid):.4f}; "
          f"tts chars {sum(e['chars'] or 0 for e in paid)}; stt audio s {sum(e['audio_seconds'] or 0 for e in paid if e['kind'] != 'tts'):.1f}")
    print("credits charged on non-200 rows:", sum(e["est_credits"] for e in mine if e["status"] != 200))
    dup = Counter(e["cache_key"] for e in paid)
    print("cache keys paid more than once:", sum(v > 1 for v in dup.values()))
    ts = sorted(e["ts"] for e in paid)
    print("paid window:", ts[0], "->", ts[-1])
    whole = sum(e["est_credits"] for e in ledger if e["provider"] == "gnani")
    print(f"whole gnani ledger now: {whole:.2f} credits")

    by_key = defaultdict(list)
    for e in mine:
        by_key[e["cache_key"]].append(e)
    waits = []
    by_model = Counter()
    by_lang = Counter()
    statuses = Counter()
    for key, rows in by_key.items():
        rows.sort(key=lambda e: e["ts"])
        bad = [e for e in rows if e["status"] != 200]
        if not bad:
            continue
        for e in bad:
            statuses[e["status"], e.get("error_code")] += 1
        src = keys_stt.get(key)
        model = src["stt"]["model"] if src else "tts"
        by_model[model] += len(bad)
        if src:
            by_lang[model, src["language"]] += len(bad)
        good = [e for e in rows if e["status"] == 200]
        if good:
            t0 = datetime.fromisoformat(bad[0]["ts"])
            t1 = datetime.fromisoformat(good[0]["ts"])
            waits.append(((t1 - t0).total_seconds(), bad[0]["seconds"], good[0]["seconds"], good[0]["attempt"]))
    print("non-200 rows by (status, error_code):", dict(statuses))
    print("non-200 rows by model:", dict(by_model), "by (model, language):", dict(by_lang))
    if waits:
        gaps = [w[0] for w in waits]
        print(f"gap between the failed row's ts and the next 200 for the same key: n={len(gaps)} min {min(gaps):.1f} "
              f"median {statistics.median(gaps):.1f} max {max(gaps):.1f} s")
        print("failed-call wall seconds:", sorted(round(w[1], 2) for w in waits))
        print("attempt number of the succeeding call:", dict(Counter(w[3] for w in waits)))
    calls = Counter()
    for e in mine:
        if e["kind"] != "tts" and e["cache_key"] in keys_stt:
            calls[keys_stt[e["cache_key"]]["stt"]["model"], e["status"]] += 1
    print("stt ledger rows by (model, status):", dict(calls))
    print("429 rows among this run's keys:", sum(e["status"] == 429 for e in mine))
    window = [e for e in ledger if e["provider"] == "gnani" and ts[0] <= e["ts"] <= ts[-1]]
    print("all gnani ledger rows inside the run window:", len(window), dict(Counter(e["status"] for e in window)))


if __name__ == "__main__":
    main()
