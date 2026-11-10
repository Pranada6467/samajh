"""Steps 2 to 5 of the real-voice check. Step 1 is `realvoice_scan.py`.

  uv run python eval/amounts_v2/realvoice.py select    which utterances, and which row groups hold them
  uv run python eval/amounts_v2/realvoice.py fetch     download those row groups, keep only the chosen clips
  uv run python eval/amounts_v2/realvoice.py freeze    write the manifest (ids and gold amounts, no text)
  uv run python eval/amounts_v2/realvoice.py run       three Prisma readings of each clip, as recorded and as phone audio

Everything from the datasets (transcripts, audio, and Prisma's transcripts of that audio) stays
under `.samajh-realvoice/`, which is gitignored. The manifest that enters the repository holds an
id, the gold amount, and where the row sits in the dataset: no words of any utterance.

Which utterances (decided before any of this audio was transcribed):
  * IndicVoices Hindi, scenarios `Read` and `Extempore` only (solo recordings; `Conversation` is
    never used), and Kathbath Hindi (read speech);
  * 1 to 20 seconds long, no annotation tag ("<...>") in the transcript;
  * the reference transcript has a currency word and `samajh.amounts.parse_amount` reads exactly
    one amount above zero from it. That amount is the gold;
  * at most two utterances per speaker in each dataset.
The audio sits in parquet row groups of about 100 MB (IndicVoices) and 16 MB (Kathbath), and a
row group cannot be read in part, so the row groups are chosen to hold as many candidates as
possible: all of the IndicVoices validation split, every row group with a skipped-group amount,
then the richest ones (an amount of two or more groups counts four times). Kathbath utterances
are drawn by a seeded shuffle, amounts of two or more groups first.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
import re
import sys
from array import array
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / ".samajh-realvoice"
MANIFEST = REPO / "data" / "amounts_v2" / "realvoice-v1.jsonl"
EXPERIMENT = Path(__file__).with_name("realvoice.toml")
SEED = 20261112
CURRENCY = re.compile(r"रुपय|रुपए|रूपय|रूपए|₹|rupee|\bRs", re.IGNORECASE)
MIN_SECONDS, MAX_SECONDS = 1.0, 20.0
PER_SPEAKER = 2
INDICVOICES_TARGET, INDICVOICES_MAX_BYTES = 90, 1_900_000_000
KATHBATH_TARGET = 36
TOTAL_SECONDS = 900.0  # six requests per clip at 0.010 credits a second: about 54 credits


def _groups(rupees: int) -> int:
    crore, rest = divmod(rupees, 10_000_000)
    lakh, rest = divmod(rest, 100_000)
    thousand, rest = divmod(rest, 1_000)
    return sum(bool(part) for part in (crore, lakh, thousand, *divmod(rest, 100)))


def _shape(rupees: int) -> str:
    from samajh.evalkit.amounts.heldout import skips_a_group

    return "skipped" if skips_a_group(rupees) else "multi" if _groups(rupees) > 1 else "single"


def candidates() -> list[dict]:
    """Every utterance that meets the rule, from the scanned text columns. Holds transcripts."""
    import pyarrow.parquet as pq

    from samajh.amounts import Parsed, parse_amount

    out = []
    for source in ("IndicVoices", "Kathbath"):
        for path in sorted((ROOT / "scan" / source).glob("*.parquet")):
            for row in pq.read_table(path).to_pylist():
                text = row["text"] or ""
                if source == "IndicVoices" and row["scenario"] not in ("Read", "Extempore"):
                    continue
                if not MIN_SECONDS <= row["duration"] <= MAX_SECONDS or "<" in text:
                    continue
                if not CURRENCY.search(text):
                    continue
                reading = parse_amount(text)
                if not isinstance(reading, Parsed) or reading.rupees <= 0:
                    continue
                out.append(
                    {
                        "source": source.lower(),
                        "shard": row["shard"],
                        "row_group": row["row_group"],
                        "row_in_group": row["row_in_group"],
                        "speaker": str(row["speaker_id"]),
                        "seconds": row["duration"],
                        "style": (row.get("scenario") or "Read").lower(),
                        "task": row.get("task_name") or "read sentences",
                        "gold": reading.rupees,
                        "shape": _shape(reading.rupees),
                        "text": text,
                    }
                )
    return out


def _cap_speakers(rows: list[dict], taken: Counter) -> list[dict]:
    kept = []
    for row in rows:
        key = (row["source"], row["speaker"])
        if taken[key] < PER_SPEAKER:
            taken[key] += 1
            kept.append(row)
    return kept


def select() -> int:
    from huggingface_hub import HfApi

    rows = candidates()
    by_source = Counter(row["source"] for row in rows)
    print(f"candidates: {dict(by_source)}; shapes {dict(Counter(row['shape'] for row in rows))}")
    rng = random.Random(SEED)
    taken: Counter = Counter()
    chosen: list[dict] = []

    # IndicVoices: whole row groups, best first.
    sizes = {
        sibling.rfilename: sibling.size
        for sibling in HfApi().dataset_info("ai4bharat/IndicVoices", files_metadata=True).siblings
    }
    groups: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in rows:
        if row["source"] == "indicvoices":
            groups[row["shard"], row["row_group"]].append(row)

    def rank(item: tuple[tuple[str, int], list[dict]]) -> tuple:
        (shard, group), members = item
        weight = sum(4 if row["shape"] != "single" else 1 for row in members)
        return (
            "valid" not in shard,
            not any(row["shape"] == "skipped" for row in members),
            -weight,
            shard,
            group,
        )

    downloaded = 0
    picked_groups = []
    for (shard, group), members in sorted(groups.items(), key=rank):
        # Row group sizes are not in the scan: a shard's size over its number of row groups is close.
        size = sizes[shard] // 5
        enough = sum(row["source"] == "indicvoices" for row in chosen) >= INDICVOICES_TARGET
        must = "valid" in shard or any(row["shape"] == "skipped" for row in members)
        if not must and (enough or downloaded + size > INDICVOICES_MAX_BYTES):
            continue
        ordered = sorted(members, key=lambda row: (row["shape"] == "single", row["row_in_group"]))
        kept = _cap_speakers(ordered, taken)
        if kept:
            chosen += kept
            downloaded += size
            picked_groups.append((shard, group))

    # Kathbath: one small row group per utterance, so draw utterances, not row groups.
    kathbath = [row for row in rows if row["source"] == "kathbath"]
    rng.shuffle(kathbath)
    kathbath.sort(key=lambda row: row["shape"] == "single")
    chosen += _cap_speakers(kathbath, taken)[:KATHBATH_TARGET]

    # Trim to the audio budget: drop single-group IndicVoices utterances, longest first.
    chosen.sort(key=lambda row: (row["source"], row["shard"], row["row_group"], row["row_in_group"]))
    total = sum(row["seconds"] for row in chosen)
    droppable = sorted(
        (row for row in chosen if row["source"] == "indicvoices" and row["shape"] == "single"),
        key=lambda row: -row["seconds"],
    )
    dropped = 0
    while total > TOTAL_SECONDS and droppable:
        row = droppable.pop(0)
        chosen.remove(row)
        total -= row["seconds"]
        dropped += 1
    counters = Counter()
    for row in chosen:
        counters[row["source"]] += 1
        row["id"] = f"rv-{'iv' if row['source'] == 'indicvoices' else 'kb'}-{counters[row['source']]:03d}"
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "candidates.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    (ROOT / "selected.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in chosen), encoding="utf-8"
    )
    print(
        f"selected {len(chosen)} ({dict(Counter(row['source'] for row in chosen))}), "
        f"{total:.0f} s of audio, {dropped} dropped for the audio budget"
    )
    print(f"shapes {dict(Counter(row['shape'] for row in chosen))}")
    print(f"speakers {len({(row['source'], row['speaker']) for row in chosen})}")
    print(f"IndicVoices row groups {len(picked_groups)}, about {downloaded / 1e9:.2f} GB")
    print(
        f"Kathbath row groups {len({(r['shard'], r['row_group']) for r in chosen if r['source'] == 'kathbath'})}"
    )
    return 0


def _selected() -> list[dict]:
    return [json.loads(line) for line in (ROOT / "selected.jsonl").read_text(encoding="utf-8").splitlines()]


def _to_wav(encoded: bytes) -> tuple[bytes, int]:
    """16-bit mono PCM WAV at the recording's own sample rate."""
    import soundfile

    from samajh.audio import Pcm, write_wav

    samples, rate = soundfile.read(io.BytesIO(encoded), dtype="int16", always_2d=True)
    mono = samples[:, 0] if samples.shape[1] == 1 else samples.mean(axis=1).astype("int16")
    return write_wav(Pcm(rate, array("h", mono.tolist()))), rate


def fetch() -> int:
    import pyarrow.parquet as pq
    from huggingface_hub import HfFileSystem

    repos = {"indicvoices": "ai4bharat/IndicVoices", "kathbath": "ai4bharat/Kathbath"}
    audio_dir = ROOT / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    wanted: dict[tuple[str, str, int], list[dict]] = defaultdict(list)
    for row in _selected():
        if not (audio_dir / f"{row['id']}.wav").exists():
            wanted[row["source"], row["shard"], row["row_group"]].append(row)
    fs = HfFileSystem()
    transferred = 0
    for number, ((source, shard, group), rows) in enumerate(sorted(wanted.items()), start=1):
        with fs.open(f"datasets/{repos[source]}/{shard}", "rb", block_size=1 << 17) as f:
            parquet = pq.ParquetFile(f)
            chunk = parquet.metadata.row_group(group)
            transferred += sum(
                chunk.column(i).total_compressed_size
                for i in range(chunk.num_columns)
                if chunk.column(i).path_in_schema.startswith("audio_filepath")
            )
            column = parquet.read_row_group(group, columns=["audio_filepath"]).column("audio_filepath")
        for row in rows:
            wav, _ = _to_wav(column[row["row_in_group"]].as_py()["bytes"])
            tmp = audio_dir / f"{row['id']}.tmp"
            tmp.write_bytes(wav)
            tmp.replace(audio_dir / f"{row['id']}.wav")
        print(
            f"{number}/{len(wanted)} {shard} #{group}: {len(rows)} clips, {transferred / 1e9:.2f} GB so far"
        )
    return 0


def freeze() -> int:
    """The manifest: id, gold and dataset position. A clip recorded at 8 kHz is left out (a
    phone-line recording, which the project never uses)."""
    from samajh.audio import read_wav
    from samajh.evalkit.amounts.grammar import jsonl_bytes
    from samajh.evalkit.amounts.heldout import in_retail_band

    out = []
    skipped = Counter()
    for row in _selected():
        wav = (ROOT / "audio" / f"{row['id']}.wav").read_bytes()
        pcm = read_wav(wav)
        seconds = len(pcm.samples) / pcm.rate
        if pcm.rate < 16000:
            skipped["below 16 kHz"] += 1
            continue
        if seconds > 29.5:
            skipped["over 29.5 s"] += 1
            continue
        out.append(
            {
                "id": row["id"],
                "language": "hi",
                # The runner voices `text`; here it only names the clip to load.
                "text": row["id"],
                "gold": {"amount_inr": row["gold"]},
                "tags": {
                    "source": row["source"],
                    "split": "valid" if "valid" in row["shard"] else "train",
                    "style": row["style"],
                    "task": row["task"],
                    "shape": row["shape"],
                    "band": "retail" if in_retail_band(row["gold"]) else "outside",
                    "where": f"{row['shard']}#{row['row_group']}:{row['row_in_group']}",
                    "sample_rate": str(pcm.rate),
                    "seconds": f"{seconds:.2f}",
                    "audio_sha256": hashlib.sha256(wav).hexdigest(),
                },
            }
        )
    data = jsonl_bytes(out)
    if MANIFEST.exists() and MANIFEST.read_bytes() != data:
        print(f"{MANIFEST} exists and differs: the set is frozen.", file=sys.stderr)
        return 1
    MANIFEST.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    MANIFEST.with_suffix(".sha256").write_text(f"{digest}  {MANIFEST.name}\n", encoding="utf-8")
    print(f"{MANIFEST}: {len(out)} rows, sha256 {digest}; left out {dict(skipped)}")
    return 0


class DatasetAudio:
    """Stands in for Timbre in the runner: "voicing" an item returns its dataset recording.
    Speech-to-text goes to the real client."""

    def __init__(self, client, audio_dir: Path) -> None:
        self._client = client
        self._audio_dir = audio_dir

    def tts(self, text: str, options):
        from samajh.clients.gnani import CallInfo, Speech, wav_sample_rate, wav_seconds

        audio = (self._audio_dir / f"{text}.wav").read_bytes()
        key = f"dataset:{hashlib.sha256(audio).hexdigest()}"
        return Speech(
            audio=audio,
            content_type="audio/wav",
            container="wav",
            sample_rate=wav_sample_rate(audio),
            audio_seconds=wav_seconds(audio),
            request_id=None,
            call=CallInfo(cache_hit=True, cache_key=key, seconds=0.0, est_credits=0.0, attempts=0),
        )

    def stt(self, audio: bytes, options):
        return self._client.stt(audio, options)


def run(max_items: int | None, budget: float | None, skip: frozenset[str] = frozenset()) -> int:
    from samajh.clients._runtime import Ledger, load_defaults, state_dir
    from samajh.clients.gnani import GnaniClient
    from samajh.evalkit.manifest import load_manifest
    from samajh.evalkit.plan import load_experiment
    from samajh.evalkit.runner import Rates, RunStore
    from samajh.evalkit.runner import run as run_experiment

    experiment = load_experiment(EXPERIMENT)
    items = load_manifest(experiment.manifest, expect_sha256=experiment.manifest_sha256)
    # A clip the API's edge refuses on every attempt (an HTML 403, not a Prisma error) is left
    # out by id; the report names it.
    items = tuple(item for item in items if item.id not in skip)
    for item in items:
        wav = (ROOT / "audio" / f"{item.id}.wav").read_bytes()
        if hashlib.sha256(wav).hexdigest() != item.tags["audio_sha256"]:
            print(f"{item.id}: the local clip is not the one the manifest froze", file=sys.stderr)
            return 1
    defaults = load_defaults()["gnani"]
    summary = run_experiment(
        experiment,
        items,
        client=DatasetAudio(GnaniClient.from_env(), ROOT / "audio"),
        store=RunStore(ROOT / "run"),
        audio_root=ROOT / "evalkit",
        ledger=Ledger(state_dir() / "ledger.jsonl"),
        rates=Rates(defaults["stt_credits_per_second"], defaults["tts_credits_per_char"]),
        max_items=max_items,
        budget_credits=budget,
    )
    print(
        f"planned {summary.planned}, already done {summary.already_done}, transcribed {summary.transcribed}, "
        f"errors {summary.errors}, pending {summary.pending}, spent {summary.spent_credits:.3f} credits"
    )
    if summary.stopped:
        print(f"stopped: {summary.stopped}")
    return 0 if summary.pending == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("command", choices=["select", "fetch", "freeze", "run"])
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--budget", type=float)
    parser.add_argument("--skip", action="append", default=[], help="leave out this item id (repeatable)")
    args = parser.parse_args(argv)
    if args.command == "run":
        return run(args.max_items, args.budget, frozenset(args.skip))
    return {"select": select, "fetch": fetch, "freeze": freeze}[args.command]()


if __name__ == "__main__":
    sys.exit(main())
