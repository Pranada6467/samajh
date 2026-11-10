"""Reviewer probe: recompute the tables of references/pilots/voice-loop-iter1.md section 3 from the
builders' raw rows (.samajh/w7/results.jsonl, read-only) and rerun web/vad.js under Node on the
20 clips (.samajh/w7/clips, read-only). Offline: no network.

    uv run python references/reviews/iter1/probes/server_w7_numbers.py
"""
from __future__ import annotations

import json
import statistics as st
import struct
import subprocess
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
rows = [json.loads(line) for line in (REPO / ".samajh/w7/results.jsonl").read_text().splitlines()]
med = lambda xs: round(st.median(xs), 3)  # noqa: E731
paused = lambda r: r["id"].startswith("pa")  # noqa: E731

print("REST")
rest = {}
for model in ("prisma-v3.0", "prisma-v2.5"):
    r = [x for x in rows if x.get("mode") == "rest" and x["model"] == model]
    rest[model] = {x["id"]: x["transcript"] for x in r}
    print(f"  {model}: n={len(r)} median stt_s={med([x['stt_s'] for x in r])} max={max(x['stt_s'] for x in r)} "
          f"amount right={sum(x['amount'] == x['gold'] for x in r)}/{len(r)} cache hits={sum(x['cache_hit'] for x in r)}")
print("STREAMING")
for mode, model in (("server", "prisma-v3.0"), ("server@1000", "prisma-v3.0"), ("commit", "prisma-v3.0"), ("commit", "prisma-v2.5"), ("commit+burst", "prisma-v3.0")):
    r = [x for x in rows if x.get("mode") == mode and x["model"] == model]
    if not r:
        continue
    t = [x["eos_to_transcript_s"] for x in r if x["eos_to_transcript_s"] is not None]
    ids = [x["id"] for x in r]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup or len(t) != len(r):
        print(f"    note: {len(r)} rows, {len(set(ids))} distinct clips, repeated ids {dup}, rows with no time {len(r) - len(t)}")
    pa = [x for x in r if paused(x)]
    same = sum(x["transcript"] == rest["prisma-v3.0"].get(x["id"]) for x in r)
    print(f"  {mode:<13} {model}: n={len(r)} median={med(t)} min={min(t)} max={max(t)} paused split={sum(x['segments'] > 1 for x in pa)}/{len(pa)} "
          f"amount right={sum(x['amount'] == x['gold'] for x in r)}/{len(r)} same text as v3.0 REST={same}/{len(r)}")
s = [x for x in rows if x.get("path") == "stream"]
print(f"  all streaming rows: n={len(s)} connect_s median={med([x['connect_s'] for x in s])} max={max(x['connect_s'] for x in s)}; "
      f"server latency ms median={st.median([v for x in s for v in x.get('server_latency_ms', [])])}; audio sent {sum(x['audio_sent_s'] for x in s):.0f} s")

print("END-OF-SPEECH DETECTOR (rerun now, web/vad.js under Node, each clip followed by 2 s of silence)")


def true_end_ms(path: Path) -> float:
    with wave.open(str(path)) as f:
        rate, n = f.getframerate(), f.getnframes()
        pcm = struct.unpack(f"<{n}h", f.readframes(n))
    frame = rate // 100
    last = 0
    for i in range(0, n - frame + 1, frame):
        rms = (sum(v * v for v in pcm[i : i + frame]) / frame) ** 0.5 / 32768
        if rms > 10 ** (-40 / 20):
            last = i + frame
    return last * 1000 / rate


clips = sorted((REPO / ".samajh/w7/clips").glob("*.wav"))
for hang in (700, 500):
    waits, cut, late = [], 0, []
    for clip in clips:
        out = json.loads(subprocess.run(["node", str(REPO / "tests/server/vad_check.mjs"), str(clip), "--tail-ms", "2000", "--hangover-ms", str(hang)],
                                        capture_output=True, text=True, check=True).stdout)
        ends = [e for e in out["events"] if e["type"] == "speech_end"]
        starts = [e for e in out["events"] if e["type"] == "speech_start"]
        if clip.name.startswith("pa") and len(ends) > 1:
            cut += 1
        waits.append(ends[-1]["atMs"] - true_end_ms(clip))
        late.append(starts[0]["atMs"])
    print(f"  hangover {hang} ms: n={len(clips)} decision after true end of speech median={st.median(waits):.0f} ms (min {min(waits):.0f}, max {max(waits):.0f}); "
          f"paused clips cut={cut}/{sum(c.name.startswith('pa') for c in clips)}")
