"""Run a local open ASR model over a W7 job file. Runs in its own throwaway environment (does not import samajh):

    uv run --no-project --python 3.11 --with-requirements eval/openbench/requirements-asr.txt \
        python eval/openbench/asr_local.py --system whisper-large-v3|indicconformer|indicwhisper \
        --set amounts-v2|realvoice|fleurs [--condition C] [--limit N] [--only-field NAME | --subset-only]

Settings are fixed in PLAN.md. Resumable: jobs already transcribed without error are skipped.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import sys
import time
from importlib import metadata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import store  # noqa: E402

os.environ.setdefault("HF_HUB_CACHE", str(store.REPO / ".samajh" / "openbench" / "hf-cache"))

WHISPER_REPO = "mlx-community/whisper-large-v3-mlx"
WHISPER_REV = "49e6aa286ad60c14352c404340ded53710378a11"
WHISPER_SETTINGS = {
    "language": "hi",
    "task": "transcribe",
    "temperature": 0.0,
    "condition_on_previous_text": False,
    "initial_prompt": None,
    "decoding": "greedy, no temperature fallback",
}
CONFORMER_REPO = "ai4bharat/indic-conformer-600m-multilingual"
CONFORMER_REV = "2a77d305038dfc502fd9464e7d028b90381976cb"
CONFORMER_SETTINGS = {"language": "hi", "decodings": ["rnnt", "ctc"], "sample_rate": 16000, "device": "cpu"}
INDICWHISPER_URL = "https://indicwhisper.objectstore.e2enetworks.net/hindi_models.zip"
INDICWHISPER_DIR = store.REPO / ".samajh" / "openbench" / "indicwhisper"
INDICWHISPER_SETTINGS = {"language": "hi", "task": "transcribe", "num_beams": 1, "do_sample": False,
                         "temperature_fallback": None, "max_new_tokens": 225, "sample_rate": 16000, "dtype": "float32"}
LIBS = ("mlx", "mlx-whisper", "torch", "torchaudio", "transformers", "onnxruntime", "onnx", "soundfile", "numpy",
        "huggingface-hub")


def versions() -> dict:
    out = {"python": sys.version.split()[0], "platform": platform.platform()}
    for lib in LIBS:
        try:
            out[lib] = metadata.version(lib)
        except metadata.PackageNotFoundError:
            out[lib] = None
    return out


def write_meta(set_name: str, system: str, repo: str, revision: str, settings: dict) -> None:
    path = store.transcripts_path(set_name, system).with_suffix(".meta.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = {"system": system, "hf_repo": repo, "revision": revision, "settings": settings,
            "versions": versions(), "date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolved_snapshot(repo: str, revision: str) -> tuple[str, str]:
    from huggingface_hub import snapshot_download

    local = snapshot_download(repo, revision=revision)
    return local, Path(local).name  # snapshot dir name is the resolved commit hash


def run_whisper(set_name: str, jobs: list[dict]) -> None:
    import mlx_whisper

    system = "whisper-large-v3"
    path = store.transcripts_path(set_name, system)
    local, rev = resolved_snapshot(WHISPER_REPO, WHISPER_REV)
    write_meta(set_name, system, WHISPER_REPO, rev, WHISPER_SETTINGS)
    done = store.done(path)
    for job in jobs:
        if (job["item_id"], job["condition"], job["audio_sha256"]) in done:
            continue
        t0 = time.perf_counter()
        try:
            result = mlx_whisper.transcribe(
                job["audio_path"], path_or_hf_repo=local, language="hi", task="transcribe",
                temperature=0.0, condition_on_previous_text=False, initial_prompt=None, verbose=None)
            text, error = result["text"].strip(), None
        except Exception as exc:  # noqa: BLE001 - recorded per clip, run continues
            text, error = "", f"{type(exc).__name__}: {exc}"[:300]
        emit(path, job, system, text, error, time.perf_counter() - t0)


def load_16k(audio_path: str):
    import soundfile as sf
    import torch
    import torchaudio

    data, sr = sf.read(audio_path, dtype="float32", always_2d=True)
    wav = torch.from_numpy(data.mean(axis=1)).unsqueeze(0)
    if sr != 16000:
        wav = torchaudio.functional.resample(wav, sr, 16000)
    return wav


def run_conformer(set_name: str, jobs: list[dict]) -> None:
    import torch
    from transformers import AutoModel

    systems = {"rnnt": "indicconformer-rnnt", "ctc": "indicconformer-ctc"}
    local, rev = resolved_snapshot(CONFORMER_REPO, CONFORMER_REV)
    model = AutoModel.from_pretrained(CONFORMER_REPO, revision=CONFORMER_REV, trust_remote_code=True)
    for system in systems.values():
        write_meta(set_name, system, CONFORMER_REPO, rev, CONFORMER_SETTINGS)
    paths = {d: store.transcripts_path(set_name, s) for d, s in systems.items()}
    done = {d: store.done(p) for d, p in paths.items()}
    for job in jobs:
        key = (job["item_id"], job["condition"], job["audio_sha256"])
        todo = [d for d in systems if key not in done[d]]
        if not todo:
            continue
        try:
            wav = load_16k(job["audio_path"])
        except Exception as exc:  # noqa: BLE001
            for d in todo:
                emit(paths[d], job, systems[d], "", f"load: {type(exc).__name__}: {exc}"[:300], 0.0)
            continue
        for d in todo:
            t0 = time.perf_counter()
            try:
                with torch.inference_mode():
                    out = model(wav, "hi", d)
                text, error = (out if isinstance(out, str) else str(out)).strip(), None
            except Exception as exc:  # noqa: BLE001
                text, error = "", f"{type(exc).__name__}: {exc}"[:300]
            emit(paths[d], job, systems[d], text, error, time.perf_counter() - t0)


def _sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


INDICWHISPER_MODEL = "hindi_models/whisper-medium-hi_alldata_multigpu"


def indicwhisper_model_dir() -> Path:
    """The Vistaar Hindi Whisper-medium, extracted (inference files only) under INDICWHISPER_DIR/extracted."""
    d = INDICWHISPER_DIR / "extracted" / INDICWHISPER_MODEL
    if not (d / "config.json").exists():
        raise SystemExit(f"model not extracted at {d}")
    return d


def run_indicwhisper(set_name: str, jobs: list[dict]) -> None:
    import torch
    from transformers import WhisperForConditionalGeneration, WhisperProcessor

    system = "indicwhisper-hi"
    path = store.transcripts_path(set_name, system)
    model_dir = indicwhisper_model_dir()
    processor = WhisperProcessor.from_pretrained(model_dir)
    model = WhisperForConditionalGeneration.from_pretrained(model_dir, torch_dtype=torch.float32).eval()
    device = "cpu"
    if torch.backends.mps.is_available():
        try:
            model.to("mps")
            probe = processor(torch.zeros(16000).numpy(), sampling_rate=16000, return_tensors="pt").input_features
            model.generate(probe.to("mps"), language="hi", task="transcribe", max_new_tokens=5)
            device = "mps"
        except Exception as exc:  # noqa: BLE001 - fall back to CPU, recorded in meta
            print(f"MPS failed, using CPU: {exc}", file=sys.stderr)
            model.to("cpu")
    zip_path = INDICWHISPER_DIR / "hindi_models.zip"
    settings = dict(INDICWHISPER_SETTINGS, device=device, source_url=INDICWHISPER_URL,
                    zip_sha256=_sha256(zip_path) if zip_path.exists() else None, zip_bytes=4262614425,
                    model_dir=str(model_dir.relative_to(INDICWHISPER_DIR / "extracted")),
                    config_sha256=_sha256(model_dir / "config.json"))
    write_meta(set_name, system, "AI4Bharat/vistaar (IndicWhisper Hindi)", "hindi_models.zip", settings)
    done = store.done(path)
    for job in jobs:
        if (job["item_id"], job["condition"], job["audio_sha256"]) in done:
            continue
        t0 = time.perf_counter()
        try:
            wav = load_16k(job["audio_path"])[0].numpy()
            feats = processor(wav, sampling_rate=16000, return_tensors="pt").input_features.to(device)
            with torch.inference_mode():
                ids = model.generate(feats, language="hi", task="transcribe", num_beams=1, do_sample=False,
                                     max_new_tokens=225)
            text, error = processor.batch_decode(ids, skip_special_tokens=True)[0].strip(), None
        except Exception as exc:  # noqa: BLE001
            text, error = "", f"{type(exc).__name__}: {exc}"[:300]
        emit(path, job, system, text, error, time.perf_counter() - t0)


def emit(path: Path, job: dict, system: str, text: str, error: str | None, compute_s: float) -> None:
    store.append_row(path, {
        "set": job["set"], "item_id": job["item_id"], "condition": job["condition"], "system": system,
        "audio_sha256": job["audio_sha256"], "text": text, "error": error, "compute_s": round(compute_s, 3),
        "meta": {"audio_path": job["audio_path"]},
    })
    if error:
        print(f"ERROR {system} {job['item_id']} {job['condition']}: {error}", file=sys.stderr)
    else:
        print(f"{system} {job['item_id']} {job['condition']} {compute_s:.2f}s", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True, choices=["whisper-large-v3", "indicconformer", "indicwhisper"])
    ap.add_argument("--set", required=True, choices=store.SETS)
    ap.add_argument("--condition")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only-field", metavar="NAME", help='keep only jobs whose boolean field NAME is true')
    ap.add_argument("--subset-only", action="store_true", help="alias for --only-field subset")
    args = ap.parse_args()
    jobs = store.read_jsonl(store.jobs_path(args.set))
    if not jobs:
        raise SystemExit(f"no jobs at {store.jobs_path(args.set)}")
    if args.condition:
        jobs = [j for j in jobs if j["condition"] == args.condition]
    only = args.only_field or ("subset" if args.subset_only else None)
    if args.subset_only and args.only_field not in (None, "subset"):
        raise SystemExit("--subset-only conflicts with --only-field")
    if only:
        jobs = [j for j in jobs if j.get(only) is True]
    if args.limit is not None:
        jobs = jobs[: args.limit]
    print(f"{len(jobs)} jobs", flush=True)
    runner = {"whisper-large-v3": run_whisper, "indicconformer": run_conformer, "indicwhisper": run_indicwhisper}
    runner[args.system](args.set, jobs)


if __name__ == "__main__":
    main()
