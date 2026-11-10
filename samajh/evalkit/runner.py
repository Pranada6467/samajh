"""The resumable run: voice each item, derive the audio conditions offline, transcribe each cell.

What makes a rerun free:
  * every finished call is one appended line in the run store (`voice.jsonl`, `stt.jsonl`), keyed
    by a fingerprint of everything that decides the request: item id, sha256 of the text, the
    Timbre options, the condition's steps and the exact Prisma options. A cell whose fingerprint
    is already in the store is skipped without touching the client;
  * the Gnani client's own cache is the second line: a call that was paid for but whose line was
    lost in a crash comes back as a cache hit.
Changing a condition's steps or a text changes the fingerprint, so a stale line is never reused
for a different request; `current_rows` is what scoring reads.

The run stops cleanly, state on disk, when its own budget or the client's credit cap would be
crossed. The spend it reports is the ledger's: every ledger row whose cache key this run recorded.
That includes a request another worker paid for earlier with the same key, so the figure can only
err high. Not covered: a 2xx answer the client cannot parse is charged in the ledger and not
cached, so the next run pays for it again.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, TypeVar

import filelock
from pydantic import ValidationError

from samajh.audio import AudioStore, Step, ffmpeg_version
from samajh.audio import steps as audio_steps
from samajh.clients._runtime import Ledger
from samajh.clients.errors import AuthError, CapExceeded, ClientError, ConfigError, LockTimeout
from samajh.clients.gnani import CallInfo, PrismaV25, PrismaV30, Speech, Timbre, Transcript, wav_seconds
from samajh.evalkit.manifest import Item, sha256_hex
from samajh.evalkit.plan import Cell, Experiment, SttSpec, VoiceSpec, plan
from samajh.types import Frozen, Language

Row = TypeVar("Row", bound=Frozen)


class SpeechClient(Protocol):
    def tts(self, text: str, options: Timbre) -> Speech: ...

    def stt(self, audio: bytes, options: PrismaV30 | PrismaV25) -> Transcript: ...


class VoiceRow(Frozen):
    fingerprint: str
    item_id: str
    text_sha256: str
    voice: VoiceSpec
    tts: dict[str, Any]
    audio_sha256: str
    audio_seconds: float
    chars: int
    cache_key: str
    cache_hit: bool
    est_credits: float
    ts: str


class SttRow(Frozen):
    fingerprint: str
    item_id: str
    language: Language
    voice: VoiceSpec
    condition: str
    steps: list[dict[str, Any]]
    stt: SttSpec
    request: dict[str, Any]
    clip_sha256: str
    audio_sha256: str
    audio_seconds: float
    text: str
    literal: str | None
    detected_language: str | None
    request_id: str | None
    truncated: bool
    cache_key: str
    cache_hit: bool
    est_credits: float
    seconds: float
    attempts: int
    ts: str


class ErrorRow(Frozen):
    item_id: str
    stage: str
    condition: str | None
    stt: SttSpec | None
    error: str
    message: str
    ts: str


class RunRow(Frozen):
    """One invocation of `run`: when, with which tools, and what it did."""

    ts: str
    ffmpeg: str
    transform_version: int
    planned: int
    already_done: int
    transcribed: int
    voiced: int
    errors: int
    spent_credits: float
    stopped: str | None


def _fingerprint(**parts: Any) -> str:
    return sha256_hex(json.dumps(parts, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class RunStore:
    """Append-only JSONL files in one directory. A line torn by a crash is skipped on reading."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _read(self, name: str, model: type[Row]) -> list[Row]:
        try:
            lines = (self.root / name).read_bytes().splitlines()
        except FileNotFoundError:
            return []
        rows = []
        for line in lines:
            try:
                rows.append(model.model_validate_json(line))
            except ValidationError:
                continue
        return rows

    def _append(self, name: str, row: Frozen) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / name
        line = row.model_dump_json().encode("utf-8") + b"\n"
        # A crash can leave a last line without its newline: start a fresh line, or this row
        # would be glued to the torn one and lost on reading.
        try:
            with path.open("rb") as f:
                f.seek(-1, os.SEEK_END)
                torn = f.read(1) != b"\n"
        except OSError:
            torn = False
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, b"\n" + line if torn else line)
        finally:
            os.close(fd)

    def voice_rows(self) -> list[VoiceRow]:
        return self._read("voice.jsonl", VoiceRow)

    def stt_rows(self) -> list[SttRow]:
        return self._read("stt.jsonl", SttRow)

    def error_rows(self) -> list[ErrorRow]:
        return self._read("errors.jsonl", ErrorRow)

    def run_rows(self) -> list[RunRow]:
        return self._read("runs.jsonl", RunRow)

    def add(self, row: VoiceRow | SttRow | ErrorRow | RunRow) -> None:
        names = {VoiceRow: "voice.jsonl", SttRow: "stt.jsonl", ErrorRow: "errors.jsonl", RunRow: "runs.jsonl"}
        self._append(names[type(row)], row)


@dataclass(frozen=True)
class Job:
    """A cell with everything resolved: what will be sent, and the fingerprint of it."""

    cell: Cell
    item: Item
    timbre: Timbre
    steps: tuple[Step, ...]
    options: PrismaV30 | PrismaV25
    voice_fingerprint: str
    fingerprint: str


def jobs(items: tuple[Item, ...], experiment: Experiment, *, max_items: int | None = None) -> list[Job]:
    """The plan with requests resolved. `max_items` keeps the cells of the first N manifest items."""
    by_id = {item.id: item for item in items}
    keep = {item.id for item in items[:max_items]} if max_items is not None else set(by_id)
    out = []
    for cell in plan(items, experiment):
        if cell.item_id not in keep:
            continue
        item = by_id[cell.item_id]
        timbre = cell.voice.timbre(item.language, experiment.tts_sample_rate)
        steps = experiment.conditions[cell.condition]
        options = cell.stt.options(item.language)
        voiced = {
            "item_id": item.id,
            "text_sha256": sha256_hex(item.text.encode("utf-8")),
            "tts": timbre.model_dump(mode="json"),
        }
        out.append(
            Job(
                cell=cell,
                item=item,
                timbre=timbre,
                steps=steps,
                options=options,
                voice_fingerprint=_fingerprint(**voiced),
                fingerprint=_fingerprint(
                    **voiced,
                    steps=[step.model_dump(mode="json") for step in steps],
                    stt=options.model_dump(mode="json"),
                    **_transform_version(steps),
                ),
            )
        )
    return out


def _transform_version(steps: tuple[Step, ...]) -> dict[str, int]:
    """The audio transforms' version, as a fingerprint part: a bump of `audio_steps.TRANSFORM_VERSION` makes
    new audio, so the cells that use a transform must run again. Version 1 is left out because
    the first paid rows were fingerprinted before this part existed."""
    return (
        {"transform_version": audio_steps.TRANSFORM_VERSION}
        if steps and audio_steps.TRANSFORM_VERSION != 1
        else {}
    )


def current_rows(store: RunStore, planned: Iterable[Job]) -> dict[str, SttRow]:
    """The stored transcript of each planned cell, by cell key. Lines for requests the plan no
    longer makes (an edited condition, a changed text) are left out."""
    by_fingerprint = {row.fingerprint: row for row in store.stt_rows()}
    return {
        job.cell.key: by_fingerprint[job.fingerprint] for job in planned if job.fingerprint in by_fingerprint
    }


def run_spend(store: RunStore, ledger: Ledger) -> float:
    """Estimated credits the ledger holds against this run: rows whose cache key the run recorded."""
    keys = {row.cache_key for row in store.voice_rows()} | {row.cache_key for row in store.stt_rows()}
    return sum(e.est_credits for e in ledger.entries() if e.provider == "gnani" and e.cache_key in keys)


@dataclass(frozen=True)
class Rates:
    stt_credits_per_second: float
    tts_credits_per_char: float


@dataclass
class RunSummary:
    planned: int = 0
    already_done: int = 0
    transcribed: int = 0
    voiced: int = 0
    errors: int = 0
    spent_credits: float = 0.0
    stopped: str | None = None

    @property
    def pending(self) -> int:
        return self.planned - self.already_done - self.transcribed


class _Stop(Exception):
    pass


class StoreBusy(Exception):
    """Another process is running against the same run store."""


def _write_once(path: Path, data: bytes) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def run(experiment: Experiment, items: tuple[Item, ...], *, store: RunStore, **settings: Any) -> RunSummary:
    """Run the experiment against `store`, one process at a time, and log the invocation.

    Raises `StoreBusy` if another process holds the store: the budget is counted in this process,
    so two runs at once could each spend it. Settings are those of `_run`.
    """
    store.root.mkdir(parents=True, exist_ok=True)
    lock_path = store.root / ".run.lock"
    lock = filelock.FileLock(lock_path, timeout=0, thread_local=False)
    try:
        lock.acquire()
    except filelock.Timeout:
        raise StoreBusy(f"another run is using {store.root}") from None
    try:
        summary = _run(experiment, items, store=store, **settings)
        store.add(
            RunRow(
                ts=_now(),
                ffmpeg=ffmpeg_version(),
                transform_version=audio_steps.TRANSFORM_VERSION,
                planned=summary.planned,
                already_done=summary.already_done,
                transcribed=summary.transcribed,
                voiced=summary.voiced,
                errors=summary.errors,
                spent_credits=round(summary.spent_credits, 4),
                stopped=summary.stopped,
            )
        )
        return summary
    finally:
        lock.release()
        lock_path.unlink(missing_ok=True)


def _run(
    experiment: Experiment,
    items: tuple[Item, ...],
    *,
    client: SpeechClient,
    store: RunStore,
    audio_root: Path,
    ledger: Ledger,
    rates: Rates,
    max_items: int | None = None,
    budget_credits: float | None = None,
    lock_patience: int = 3,
    max_consecutive_errors: int = 8,
    log: Callable[[str], None] = print,
) -> RunSummary:
    budget = experiment.budget_credits if budget_credits is None else budget_credits
    planned = jobs(items, experiment, max_items=max_items)
    done = {row.fingerprint for row in store.stt_rows()}
    voiced = {row.fingerprint: row for row in store.voice_rows()}
    conditions = AudioStore(audio_root / "conditions")
    clips = audio_root / "clips"
    summary = RunSummary(planned=len(planned), spent_credits=run_spend(store, ledger))
    consecutive = 0

    def paid(call: CallInfo) -> None:
        # A cache hit is a call an earlier, interrupted run paid for and never recorded: only the
        # ledger knows what it cost.
        if call.cache_hit:
            summary.spent_credits = run_spend(store, ledger)
        else:
            summary.spent_credits += call.est_credits

    def guard(estimate: float) -> None:
        if summary.spent_credits + estimate > budget:
            raise _Stop(
                f"run budget: spent {summary.spent_credits:.3f} + {estimate:.3f} would cross {budget:g}"
            )

    def patiently(call: Callable[[], Any]) -> Any:
        # Other workers share the key: a lock timeout means the queue is long, not that we failed.
        for attempt in range(lock_patience):
            try:
                return call()
            except LockTimeout:
                log(f"lock busy, waiting again ({attempt + 1}/{lock_patience})")
        raise _Stop("the Gnani lock stayed busy")

    def clip(job: Job) -> tuple[bytes, str]:
        row = voiced.get(job.voice_fingerprint)
        if row is not None:
            try:
                return (clips / f"{row.audio_sha256}.wav").read_bytes(), row.audio_sha256
            except FileNotFoundError:
                pass  # the audio store was cleared: the client's cache still has the clip
        guard(len(job.item.text) * rates.tts_credits_per_char)
        speech: Speech = patiently(lambda: client.tts(job.item.text, job.timbre))
        digest = sha256_hex(speech.audio)
        _write_once(clips / f"{digest}.wav", speech.audio)
        row = VoiceRow(
            fingerprint=job.voice_fingerprint,
            item_id=job.item.id,
            text_sha256=sha256_hex(job.item.text.encode("utf-8")),
            voice=job.cell.voice,
            tts=job.timbre.model_dump(mode="json"),
            audio_sha256=digest,
            audio_seconds=speech.audio_seconds or 0.0,
            chars=len(job.item.text),
            cache_key=speech.call.cache_key,
            cache_hit=speech.call.cache_hit,
            est_credits=speech.call.est_credits,
            ts=_now(),
        )
        store.add(row)
        voiced[job.voice_fingerprint] = row
        summary.voiced += 1
        paid(speech.call)
        return speech.audio, digest

    def transcribe(job: Job) -> None:
        clip_audio, clip_sha = clip(job)
        audio = conditions.apply(clip_audio, job.steps)
        seconds = wav_seconds(audio)
        if seconds is None:
            raise ValueError(f"condition {job.cell.condition!r} did not produce a PCM WAV")
        guard(seconds * rates.stt_credits_per_second)
        transcript: Transcript = patiently(lambda: client.stt(audio, job.options))
        store.add(
            SttRow(
                fingerprint=job.fingerprint,
                item_id=job.item.id,
                language=job.item.language,
                voice=job.cell.voice,
                condition=job.cell.condition,
                steps=[step.model_dump(mode="json") for step in job.steps],
                stt=job.cell.stt,
                request=job.options.model_dump(mode="json"),
                clip_sha256=clip_sha,
                audio_sha256=sha256_hex(audio),
                audio_seconds=seconds,
                text=transcript.text,
                literal=transcript.literal,
                detected_language=transcript.detected_language,
                request_id=transcript.request_id,
                truncated=transcript.truncated,
                cache_key=transcript.call.cache_key,
                cache_hit=transcript.call.cache_hit,
                est_credits=transcript.call.est_credits,
                seconds=transcript.call.seconds,
                attempts=transcript.call.attempts,
                ts=_now(),
            )
        )
        done.add(job.fingerprint)
        summary.transcribed += 1
        paid(transcript.call)

    try:
        for number, job in enumerate(planned, start=1):
            if job.fingerprint in done:
                summary.already_done += 1
                continue
            try:
                transcribe(job)
                consecutive = 0
            except (CapExceeded, AuthError, ConfigError) as exc:
                raise _Stop(f"{type(exc).__name__}: {exc}") from None
            except (ClientError, RuntimeError, ValueError) as exc:
                summary.errors += 1
                consecutive += 1
                store.add(
                    ErrorRow(
                        item_id=job.item.id,
                        stage="cell",
                        condition=job.cell.condition,
                        stt=job.cell.stt,
                        error=type(exc).__name__,
                        message=str(exc)[:300],
                        ts=_now(),
                    )
                )
                log(f"error on {job.item.id} {job.cell.condition} {job.cell.stt.label}: {exc}")
                if consecutive >= max_consecutive_errors:
                    raise _Stop(f"{consecutive} cells failed in a row") from None
            if number % 100 == 0:
                log(f"{number}/{len(planned)} cells, spent {summary.spent_credits:.2f} credits")
    except _Stop as stop:
        summary.stopped = str(stop)
    return summary
