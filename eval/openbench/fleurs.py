"""FLEURS hi_in test for Part B: `uv run python eval/openbench/fleurs.py fetch|freeze|jobs [--force]`.

fetch  downloads test.tsv and audio/test.tar.gz (pinned revision) into .samajh/openbench/fleurs/, checks the
       archive hash and extracts only regular .wav members, by basename.
freeze writes data/openbench/fleurs-hi-test.jsonl (no transcript text) and its sha256.
jobs   writes the native16k and phone jobs (phone = the evalkit `{kind="mulaw"}` step via AudioStore).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import store

REV = "70bb2e84b976b7e960aa89f1c648e09c59f894dd"
BASE = f"https://huggingface.co/datasets/google/fleurs/resolve/{REV}/data/hi_in"
TAR_SHA256 = "47c238b9cf7016ba596639bb3038b0c89dc6e85759f16d09c4f58c6dfa25c65f"
DIR = store.ROOT / "fleurs"
AUDIO = DIR / "audio"
NATIVE = DIR / "native16k"  # only used if the published files need conversion
CONDITIONS = DIR / "conditions"
MANIFEST = store.REPO / "data" / "openbench" / "fleurs-hi-test.jsonl"
MANIFEST_SHA = MANIFEST.with_suffix(".sha256")
MAX_SECONDS = 30.0
SEED, SUBSET_N = 20261114, 250
GEMINI_SEED, GEMINI_N = 20261115, 100
TSV_COLS = ("tsv_id", "file", "raw transcription", "transcription", "phonemes", "num_samples", "gender")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_tsv() -> list[dict]:
    text = (DIR / "test.tsv").read_text(encoding="utf-8")
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != len(TSV_COLS):
            raise SystemExit(f"test.tsv row has {len(parts)} columns, expected {len(TSV_COLS)}: {parts[:2]}")
        rows.append(dict(zip(TSV_COLS, parts)))
    return rows


def wav_info(data: bytes) -> tuple[int, int, int, float, int]:
    """(rate, channels, bits per sample, seconds, format tag) from the RIFF header."""
    import struct

    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("not a RIFF WAVE file")
    pos, fmt, size = 12, None, None
    while pos + 8 <= len(data):
        cid, clen = data[pos : pos + 4], struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        if cid == b"fmt ":
            fmt = struct.unpack("<HHIIHH", data[pos + 8 : pos + 24])
        elif cid == b"data":
            size = min(clen, len(data) - pos - 8)
            break
        pos += 8 + clen + (clen & 1)
    if fmt is None or size is None:
        raise ValueError("wav without fmt or data chunk")
    tag, ch, rate, _, block, bits = fmt
    return rate, ch, bits, size / block / rate, tag


def _download(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"have {dest.name}")
        return
    print(f"get {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url) as r, tmp.open("wb") as fh:
        while chunk := r.read(1 << 20):
            fh.write(chunk)
    tmp.replace(dest)


def fetch() -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    _download(f"{BASE}/test.tsv", DIR / "test.tsv")
    tar = DIR / "test.tar.gz"
    _download(f"{BASE}/audio/test.tar.gz", tar)
    h = hashlib.sha256()
    with tar.open("rb") as fh:
        while chunk := fh.read(1 << 20):
            h.update(chunk)
    if h.hexdigest() != TAR_SHA256:
        raise SystemExit(f"test.tar.gz sha256 {h.hexdigest()} != {TAR_SHA256}")
    print("test.tar.gz sha256 ok")
    AUDIO.mkdir(parents=True, exist_ok=True)
    n = skipped = 0
    with tarfile.open(tar, "r:gz") as tf:
        for m in tf:
            name = Path(m.name).name
            if not m.isreg() or not name.endswith(".wav") or name in ("", ".", "..") or "/" in name:
                skipped += 1
                continue
            fh = tf.extractfile(m)
            (AUDIO / name).write_bytes(fh.read())
            n += 1
    print(f"extracted {n} wav files, skipped {skipped} other members")
    formats: dict[tuple, int] = {}
    for p in sorted(AUDIO.glob("*.wav")):
        rate, ch, bits, _, tag = wav_info(p.read_bytes())
        formats[(rate, ch, bits, tag)] = formats.get((rate, ch, bits, tag), 0) + 1
    print("wav formats (rate, channels, bits, format tag 1=PCM 3=float): count =", formats)


def _to_pcm16_mono16k(data: bytes) -> bytes:
    out = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            "-bitexact",
            "-map_metadata",
            "-1",
            "-f",
            "wav",
            "pipe:1",
        ],
        input=data,
        capture_output=True,
        check=True,
    )
    return out.stdout


def native_audio(file: str) -> tuple[Path, bytes, str]:
    """(path of the native16k file, its bytes, sha256 of the published file)."""
    path = AUDIO / file
    data = path.read_bytes()
    original = sha256(data)
    rate, ch, bits, _, tag = wav_info(data)
    if (rate, ch, bits, tag) == (16000, 1, 16, 1):
        return path, data, original
    NATIVE.mkdir(parents=True, exist_ok=True)
    conv = NATIVE / file
    if not conv.exists():
        conv.write_bytes(_to_pcm16_mono16k(data))
    return conv, conv.read_bytes(), original


def freeze(force: bool) -> None:
    rows = read_tsv()
    out, excluded = [], []
    for r in rows:
        _path, data, original = native_audio(r["file"])
        seconds = wav_info(data)[3]
        row = {
            "id": f"fleurs-hi-{r['tsv_id']}-{Path(r['file']).stem}",
            "tsv_id": r["tsv_id"],
            "file": r["file"],
            "audio_sha256": sha256(data),
            "seconds": round(seconds, 4),
            "gender": r["gender"],
        }
        if sha256(data) != original:
            row["original_sha256"] = original
        (excluded if seconds > MAX_SECONDS else out).append(row)
    ids = sorted(r["id"] for r in out)
    if len(set(ids)) != len(ids):
        raise SystemExit("duplicate ids")
    subset = set(random.Random(SEED).sample(ids, SUBSET_N))
    for r in out:
        r["subset"] = r["id"] in subset
    text = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in out)
    if MANIFEST.exists() and MANIFEST.read_text(encoding="utf-8") != text and not force:
        raise SystemExit(f"{MANIFEST} exists and differs; it is frozen (use --force)")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(text, encoding="utf-8")
    digest = sha256(text.encode())
    MANIFEST_SHA.write_text(f"{digest}  {MANIFEST.name}\n", encoding="utf-8")
    print(f"tsv rows {len(rows)}; kept {len(out)}; excluded over {MAX_SECONDS:g}s:")
    for r in excluded:
        print(f"  {r['id']} {r['seconds']:.2f}s")
    print(
        f"seconds all {sum(r['seconds'] for r in out):.1f}; subset "
        f"{sum(r['seconds'] for r in out if r['subset']):.1f} ({len(subset)} rows)"
    )
    print(f"manifest sha256 {digest}")


def load_manifest() -> list[dict]:
    text = MANIFEST.read_text(encoding="utf-8")
    want = MANIFEST_SHA.read_text(encoding="utf-8").split()[0]
    if sha256(text.encode()) != want:
        raise SystemExit("manifest does not match its sha256 file")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def gemini100(manifest: list[dict]) -> set[str]:
    """The 100 subset ids Gemini runs on, drawn from the sorted subset ids."""
    return set(random.Random(GEMINI_SEED).sample(sorted(r["id"] for r in manifest if r["subset"]), GEMINI_N))


def jobs() -> None:
    sys.path.insert(0, str(store.REPO))
    from samajh.audio import AudioStore, MuLaw

    audio_store = AudioStore(CONDITIONS)
    jobs_out = []
    manifest = load_manifest()
    gem = gemini100(manifest)
    for r in manifest:
        path, data, _ = native_audio(r["file"])
        if sha256(data) != r["audio_sha256"]:
            raise SystemExit(f"{r['id']}: audio differs from the manifest")
        base = {"set": "fleurs", "item_id": r["id"], "subset": r["subset"], "gemini100": r["id"] in gem}
        jobs_out.append(
            {**base, "condition": "native16k", "audio_path": str(path), "audio_sha256": r["audio_sha256"]}
        )
        phone = audio_store.apply(data, [MuLaw()])
        ph = sha256(phone)
        # AudioStore keeps the output at a key path; write a stable copy by hash for the job's path.
        phone_path = CONDITIONS / "phone" / f"{ph}.wav"
        if not phone_path.exists():
            phone_path.parent.mkdir(parents=True, exist_ok=True)
            phone_path.write_bytes(phone)
        jobs_out.append({**base, "condition": "phone", "audio_path": str(phone_path), "audio_sha256": ph})
    dest = store.jobs_path("fleurs")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("".join(json.dumps(j, sort_keys=True) + "\n" for j in jobs_out), encoding="utf-8")
    print(f"wrote {len(jobs_out)} jobs to {dest}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["fetch", "freeze", "jobs"])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    {"fetch": fetch, "freeze": lambda: freeze(a.force), "jobs": jobs}[a.command]()


if __name__ == "__main__":
    main()
