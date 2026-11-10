"""Trace every scored cell back to audio and the cached Prisma response. Read-only and offline.

For each of the 2,640 rows of eval/amounts/run/stt.jsonl:
  sentence (manifest) -> voice row -> clip file -> each condition step's stored output -> final audio hash
  -> client cache key recomputed from those bytes and the labelled request -> cached raw response
  -> transcript in stt.jsonl -> (scores.jsonl is checked in amounts_recompute.py)

Also measures what the uploaded audio is: WAV format tag, rate, channels, width, and whether every
sample of an 8 kHz condition lies on the G.711 mu-law decode table.

  uv run python references/reviews/iter1/probes/amounts_chain.py
"""

from __future__ import annotations

import hashlib
import json
import random
import struct
import subprocess
from collections import Counter
from pathlib import Path

from pydantic import TypeAdapter

from samajh.audio import Step, read_wav, step_key
from samajh.clients._runtime import cache_key
from samajh.clients.gnani.client import STT_PATH, _stt_fields
from samajh.evalkit.manifest import load_manifest
from samajh.evalkit.plan import SttSpec, assign_voices, load_experiment
from samajh.evalkit.runner import jobs
from samajh.types import Language

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "eval" / "amounts" / "run"
AUDIO = ROOT / ".samajh" / "evalkit" / "amounts-v1"
CACHE = ROOT / ".samajh" / "cache" / "gnani"
STEP = TypeAdapter(Step)


def jl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def mulaw_table() -> set[int]:
    raw = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "mulaw", "-ar", "8000", "-ac", "1", "-i", "pipe:0",
         "-f", "s16le", "pipe:1"],
        input=bytes(range(256)), capture_output=True, check=True,
    ).stdout
    return set(struct.unpack(f"<{len(raw) // 2}h", raw))


def wav_fmt(data: bytes) -> tuple[int, int, int, int]:
    """(format tag, channels, rate, bits) from the fmt chunk."""
    at = data.find(b"fmt ")
    tag, channels, rate, _, _, bits = struct.unpack("<HHIIHH", data[at + 8 : at + 24])
    return tag, channels, rate, bits


def main() -> None:
    experiment = load_experiment(ROOT / "eval" / "amounts" / "experiment.toml")
    items = load_manifest(experiment.manifest, expect_sha256=experiment.manifest_sha256)
    by_id = {item.id: item for item in items}
    stt = jl(RUN / "stt.jsonl")
    voice = jl(RUN / "voice.jsonl")
    planned = jobs(items, experiment)
    print(f"plan: {len(planned)} cells; stt rows {len(stt)}; voice rows {len(voice)}")

    # plan vs store
    plan_fp = {job.fingerprint: job for job in planned}
    store_fp = Counter(r["fingerprint"] for r in stt)
    print("planned fingerprints missing from stt.jsonl:", len(set(plan_fp) - set(store_fp)),
          "| stt rows not in the plan:", len(set(store_fp) - set(plan_fp)),
          "| duplicated fingerprints:", sum(v > 1 for v in store_fp.values()))
    wrong_label = 0
    for r in stt:
        job = plan_fp[r["fingerprint"]]
        same = (
            job.item.id == r["item_id"] and job.cell.condition == r["condition"]
            and job.cell.stt.model_dump(mode="json") == r["stt"]
            and job.options.model_dump(mode="json") == r["request"]
            and [s.model_dump(mode="json") for s in job.steps] == r["steps"]
            and job.cell.voice.model_dump(mode="json") == r["voice"]
        )
        wrong_label += not same
    print("stt rows whose item/condition/stt/request/steps/voice differ from the planned job with that fingerprint:", wrong_label)

    # voices
    assigned = assign_voices(items, experiment)
    vrow = {v["item_id"]: v for v in voice}
    bad_voice = sum(assigned[i].model_dump(mode="json") != vrow[i]["voice"] for i in vrow)
    bad_text = sum(sha(by_id[i].text.encode()) != vrow[i]["text_sha256"] for i in vrow)
    print(f"voice rows: items {len(vrow)}, voice != seeded assignment {bad_voice}, text hash != manifest text {bad_text}")
    per = Counter((by_id[i].language.value, v["voice"]["voice"], v["voice"]["model"]) for i, v in vrow.items())
    print("sentences per (language, voice, model):", dict(per))
    per_stratum = Counter((by_id[i].language.value, by_id[i].tags["stratum"], v["voice"]["voice"]) for i, v in vrow.items())
    print("min/max sentences of one voice inside a (language, stratum):", min(per_stratum.values()), max(per_stratum.values()))
    print("tts options seen:", dict(Counter(json.dumps({k: v for k, v in x["tts"].items() if k not in ("voice",)}, sort_keys=True) for x in voice)))

    # clips
    clip_bad = 0
    clip_fmt = Counter()
    for v in voice:
        data = (AUDIO / "clips" / f"{v['audio_sha256']}.wav").read_bytes()
        clip_bad += sha(data) != v["audio_sha256"]
        clip_fmt[wav_fmt(data)] += 1
    print(f"clip files: hash != name {clip_bad}; (format tag, channels, rate, bits): {dict(clip_fmt)}")
    print("clip files on disk not referenced by voice.jsonl:",
          len({p.stem for p in (AUDIO / 'clips').glob('*.wav')} - {v['audio_sha256'] for v in voice}))

    # chain per stt row
    table = mulaw_table()
    print("mu-law decode table size:", len(table))
    problems = Counter()
    fmt_by_condition: dict[str, Counter] = {}
    off_table = Counter()
    used_files = set()
    cached_ok = 0
    for r in stt:
        clip = (AUDIO / "clips" / f"{r['clip_sha256']}.wav").read_bytes()
        if vrow[r["item_id"]]["audio_sha256"] != r["clip_sha256"]:
            problems["clip is not the item's voiced clip"] += 1
        wav = clip
        for raw_step in r["steps"]:
            key = step_key(sha(wav), STEP.validate_python(raw_step))
            path = AUDIO / "conditions" / key[:2] / f"{key}.wav"
            if not path.exists():
                problems["step output missing from the store"] += 1
                break
            used_files.add(path)
            wav = path.read_bytes()
        if sha(wav) != r["audio_sha256"]:
            problems["final audio hash != stt row"] += 1
        fmt_by_condition.setdefault(r["condition"], Counter())[wav_fmt(wav)] += 1
        pcm = read_wav(wav)
        if abs(len(pcm.samples) / pcm.rate - r["audio_seconds"]) > 0.011:
            problems["audio_seconds differs from the file"] += 1
        if r["condition"] != "clean16k" and not set(pcm.samples) <= table:
            off_table[r["condition"]] += 1
        options = SttSpec(**r["stt"]).options(Language(r["language"]))
        key = cache_key(
            "gnani.stt.v1",
            {"base_url": "https://api.vachana.ai", "path": STT_PATH, "audio_format": "wav", "fields": _stt_fields(options)},
            wav,
        )
        if key != r["cache_key"]:
            problems["cache key recomputed from disk != stt row"] += 1
            continue
        body = CACHE / key[:2] / f"{key}.bin"
        if not body.exists():
            problems["cached response missing"] += 1
            continue
        wire = json.loads(body.read_bytes())
        if wire.get("transcript") != r["text"]:
            problems["cached transcript != stt row text"] += 1
        if wire.get("model") != r["stt"]["model"]:
            problems[f"server-reported model {wire.get('model')} != label {r['stt']['model']}"] += 1
        literal = (wire.get("output") or {}).get("literal")
        if literal != r["literal"]:
            problems["cached literal != stt row literal"] += 1
        if wire.get("request_id") != r["request_id"]:
            problems["request id differs"] += 1
        cached_ok += 1
    print("chain problems:", dict(problems) or "none")
    print("rows whose cached raw response was found and compared:", cached_ok)
    for condition, counts in sorted(fmt_by_condition.items()):
        print(f"  uploaded audio for {condition:10s}: (format tag, channels, rate, bits) {dict(counts)}")
    print("8 kHz-condition rows with a sample off the mu-law decode table:", dict(off_table) or 0)
    on_disk = set((AUDIO / "conditions").rglob("*.wav"))
    print(f"condition files on disk {len(on_disk)}, reached from stt rows {len(used_files)}, orphans {len(on_disk - used_files)}")
    print("server fields seen in one cached response:", sorted(wire))

    # five random cells, printed in full
    scores = jl(RUN / "scores.jsonl")
    rng = random.Random(20261110)
    for r in rng.sample(stt, 5):
        item = by_id[r["item_id"]]
        mine = [s for s in scores if s["item_id"] == r["item_id"] and s["condition"] == r["condition"] and s["stt"] == r["stt"]]
        print(f"\n{r['item_id']} | {r['condition']} | {r['stt']['model']} {r['stt']['format']} {r['stt']['language']}")
        print(f"  sentence: {item.text}  gold {item.gold['amount_inr']}  voice {r['voice']['voice']} ({r['voice']['model']})")
        print(f"  clip {r['clip_sha256'][:12]} -> steps {[s['kind'] for s in r['steps']]} -> audio {r['audio_sha256'][:12]} ({r['audio_seconds']} s) -> cache {r['cache_key'][:12]}")
        print(f"  transcript: {r['text']!r}  literal: {r['literal']!r}  attempts {r['attempts']}")
        for s in mine:
            print(f"    saved score: {s['output']:7s} {s['method']:6s} predicted {s['predicted']} note {s['note']!r} correct {s['correct']}")


if __name__ == "__main__":
    main()
