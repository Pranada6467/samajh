"""WhatsApp voice notes: convert, simulate the phone line, read with both Prisma models."""

from __future__ import annotations

import io
import json
import os
import subprocess
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any

from samajh.audio.steps import MuLaw, apply_step
from samajh.human.wer import _read_csv, write_csv
from samajh.server.samajh_dialogue import TTS_LANGUAGE
from samajh.server.sessionlog import SttSettings
from samajh.server.speech import stt_options
from samajh.types import Language

REPO = Path(__file__).resolve().parents[2]
SUFFIXES = {".ogg", ".opus", ".m4a", ".mp3", ".wav"}
MAX_SECONDS = 30.0  # Prisma REST limit, inclusive
CREDITS_PER_SECOND = 0.010  # samajh/clients/defaults.toml estimate
NOTE_FIELDS = ["note", "seconds", "audio_16k", "v3_0_16k", "v2_5_16k", "v3_0_8k", "v2_5_8k", "reference"]


class Refused(Exception):
    pass


def _inside(path: Path, repo: Path) -> str | None:
    """`path` relative to the repo root, spelled as the repo spells it, or None when outside.
    Walks up to the first existing ancestor and compares with `os.path.samefile`, so a
    case-insensitive filesystem's other spelling of the repo is still the repo."""
    parts: list[str] = []
    cur = path
    while True:
        if cur.exists():
            if os.path.samefile(cur, repo):
                return "/".join(reversed(parts)) or "."
            canon = cur.resolve()
            if canon != cur and canon.is_relative_to(repo):
                tail = canon.relative_to(repo).parts
                return "/".join([*tail, *reversed(parts)]) or "."
        if cur.parent == cur:
            return None
        parts.append(cur.name)
        cur = cur.parent


def check_out(out: Path, repo: Path = REPO) -> None:
    """Refuse an output path inside the repo that git does not ignore."""
    rel = _inside(out.resolve(), repo.resolve())
    if rel is None:
        return
    tracked = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--", rel], check=False, capture_output=True, text=True
    )
    ignored = subprocess.run(
        ["git", "-C", str(repo), "check-ignore", "-q", rel], check=False, capture_output=True
    )
    if tracked.stdout.strip() or ignored.returncode != 0:
        raise Refused(f"--out {out} is inside the repo and not ignored by git; voice notes must stay private")


def to_wav16(path: Path) -> bytes:
    run = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(path),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-sample_fmt",
            "s16",
            "-f",
            "wav",
            "-",
        ],
        check=False,
        capture_output=True,
    )
    if run.returncode != 0 or not run.stdout:
        raise ValueError(run.stderr.decode(errors="replace").strip()[:200] or "ffmpeg could not read it")
    return _canonical(run.stdout)


def _canonical(data: bytes) -> bytes:
    from samajh.audio.pcm import read_wav, write_wav

    return write_wav(read_wav(data))


def seconds_of(wav: bytes) -> float:
    with wave.open(io.BytesIO(wav)) as w:
        return w.getnframes() / w.getframerate()


def run_notes(
    in_dir: Path,
    lang: str,
    out: Path,
    *,
    max_credits: float,
    dry_run: bool,
    client_factory: Callable[[], Any],
    echo: Callable[[str], None] = print,
) -> int:
    check_out(out)
    language = TTS_LANGUAGE[Language(lang)]
    notes: list[tuple[str, bytes, bytes, float]] = []
    for path in sorted(p for p in in_dir.iterdir() if p.suffix.lower() in SUFFIXES):
        try:
            wav16 = to_wav16(path)
        except ValueError as e:
            echo(f"skip {path.name}: ffmpeg cannot read it ({e})")
            continue
        secs = seconds_of(wav16)
        if secs > MAX_SECONDS:
            echo(f"skip {path.name}: {secs:.1f} s is over the {MAX_SECONDS:.0f} s Prisma REST limit")
            continue
        notes.append((path.stem, wav16, apply_step(wav16, MuLaw()), secs))
    estimate = sum(CREDITS_PER_SECOND * secs * 4 for *_, secs in notes)
    echo(
        f"{len(notes)} notes, {sum(n[3] for n in notes):.1f} s; estimate {estimate:.2f} credits (4 readings each)"
    )
    if estimate > max_credits:
        raise Refused(f"estimate {estimate:.2f} credits exceeds --max-credits {max_credits}; nothing called")
    (out / "audio").mkdir(parents=True, exist_ok=True)
    for name, wav16, wav8, _ in notes:
        (out / "audio" / f"{name}.16k.wav").write_bytes(wav16)
        (out / "audio" / f"{name}.8k.wav").write_bytes(wav8)
    if dry_run:
        echo("dry run: no API call")
        return 0
    client = client_factory()
    before = _spent(client)
    options = [
        stt_options(SttSettings(), language, "primary"),
        stt_options(SttSettings(), language, "second"),
    ]
    readings, texts = [], {}
    for name, wav16, wav8, secs in notes:
        for cond, audio in (("16k", wav16), ("8k", wav8)):
            for opt in options:
                row = {
                    "note": name,
                    "condition": cond,
                    "model": opt.model,
                    "format": opt.format,
                    "text": "",
                    "literal": None,
                    "ok": True,
                    "error": None,
                    "seconds": secs,
                    "cache_hit": False,
                    "est_credits": 0.0,
                }
                try:
                    t = client.stt(audio, opt)
                    row.update(
                        text=t.text,
                        literal=t.literal,
                        cache_hit=t.call.cache_hit,
                        est_credits=t.call.est_credits,
                    )
                except Exception as e:  # noqa: BLE001  a failed reading is logged, the rest still run
                    row.update(ok=False, error=getattr(e, "code", None) or type(e).__name__)
                readings.append(row)
                texts[(name, cond, opt.model)] = row["text"]
    # Notes absent from (or unreadable in) this run keep their old readings and reference rows.
    run_names = {name for name, *_ in notes}
    old_readings = []
    if (out / "readings.jsonl").is_file():
        old_readings = [json.loads(x) for x in (out / "readings.jsonl").read_text().splitlines() if x.strip()]
    with (out / "readings.jsonl").open("w") as f:
        f.writelines(
            json.dumps(r, ensure_ascii=False) + "\n"
            for r in [*(r for r in old_readings if r.get("note") not in run_names), *readings]
        )
    old_rows = _read_csv(out / "references.csv")
    kept = {r["note"]: r.get("reference", "") for r in old_rows}
    write_csv(
        out / "references.csv",
        NOTE_FIELDS,
        [
            {
                "note": name,
                "seconds": f"{secs:.2f}",
                "audio_16k": str((out / "audio" / f"{name}.16k.wav").resolve()),
                "v3_0_16k": texts[(name, "16k", "prisma-v3.0")],
                "v2_5_16k": texts[(name, "16k", "prisma-v2.5")],
                "v3_0_8k": texts[(name, "8k", "prisma-v3.0")],
                "v2_5_8k": texts[(name, "8k", "prisma-v2.5")],
                "reference": kept.get(name, ""),
            }
            for name, _, _, secs in notes
        ]
        + [r for r in old_rows if r.get("note") not in run_names],
    )
    after = _spent(client)
    used = sum(r["est_credits"] for r in readings) if before is None or after is None else after - before
    echo(f"done: {len(readings)} readings; estimated credits used {used:.2f}")
    return 0


def _spent(client: Any) -> float | None:
    fn = getattr(client, "credits_spent", None)
    return fn() if callable(fn) else None
