"""A fake Gnani client and a small experiment for the harness tests. No network."""

from __future__ import annotations

import hashlib
import json
import math
from array import array
from pathlib import Path

from samajh.audio import Pcm, write_wav
from samajh.clients._runtime import Ledger, LedgerEntry
from samajh.clients.gnani import CallInfo, Speech, Transcript, wav_sample_rate
from samajh.evalkit.manifest import Item, load_manifest, sha256_hex
from samajh.evalkit.plan import Experiment
from samajh.evalkit.runner import Rates, RunStore

RATES = Rates(stt_credits_per_second=0.01, tts_credits_per_char=0.002)


def tone(text: str, voice: str, rate: int) -> bytes:
    """Half a second of a tone whose pitch and level depend on the text and the voice."""
    digest = hashlib.sha256(f"{voice}:{text}".encode()).hexdigest()
    hz, level = 300 + int(digest[:4], 16) % 900, 6000 + int(digest[4:8], 16) % 4000
    samples = array("h", (round(level * math.sin(2 * math.pi * hz * n / rate)) for n in range(rate // 2)))
    return write_wav(Pcm(rate, samples))


class FakeClient:
    """Answers like GnaniClient and writes the same ledger rows. The transcript names the audio it
    was given, so a test can tell which bytes reached which request."""

    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger
        self.tts_calls: list[tuple[str, str]] = []
        self.stt_calls: list[tuple[str, str]] = []
        self.fail_next: list[Exception] = []
        self.sample_rates: dict[str, int | None] = {}
        # Set to a dict to answer a repeated request the way the real client's cache does.
        self.cache: dict[str, float] | None = None

    def _row(self, kind: str, key: str, credits: float) -> CallInfo:
        if self.cache is not None:
            if key in self.cache:
                return CallInfo(cache_hit=True, cache_key=key, seconds=0.0, est_credits=0.0, attempts=0)
            self.cache[key] = credits
        self.ledger.append(
            LedgerEntry(
                ts="2026-01-01T00:00:00+00:00",
                provider="gnani",
                kind=kind,
                model="fake",
                status=200,
                attempt=1,
                seconds=0.1,
                cache_hit=False,
                cache_key=key,
                est_credits=credits,
            )
        )
        return CallInfo(cache_hit=False, cache_key=key, seconds=0.1, est_credits=credits, attempts=1)

    def tts(self, text, options):
        if self.fail_next:
            raise self.fail_next.pop(0)
        self.tts_calls.append((text, options.voice))
        audio = tone(text, options.voice, options.sample_rate)
        key = sha256_hex(f"tts:{text}:{options.model_dump_json()}".encode())
        return Speech(
            audio=audio,
            content_type="audio/wav",
            container="wav",
            sample_rate=options.sample_rate,
            audio_seconds=0.5,
            request_id=None,
            call=self._row("tts", key, len(text) * RATES.tts_credits_per_char),
        )

    def stt(self, audio, options):
        if self.fail_next:
            raise self.fail_next.pop(0)
        digest = sha256_hex(audio)
        self.stt_calls.append((digest, options.model_dump_json()))
        self.sample_rates[digest] = wav_sample_rate(audio)
        key = sha256_hex(f"stt:{digest}:{options.model_dump_json()}".encode())
        return Transcript(
            text=f"heard {digest[:12]}",
            literal="words" if options.model == "prisma-v2.5" and options.format == "transcribe" else None,
            model=options.model,
            detected_language=None,
            request_id=None,
            truncated=False,
            call=self._row("stt", key, 0.5 * RATES.stt_credits_per_second),
        )


def write_manifest(path: Path, rows: list[dict]) -> str:
    data = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows).encode()
    path.write_bytes(data)
    return sha256_hex(data)


ROWS = [
    {
        "id": f"{language}-{stratum}-{n}",
        "language": language,
        "text": f"{language} {stratum} sentence {n}",
        "gold": {"amount_inr": 1000 * (n + 1)},
        "tags": {"stratum": stratum, "fold": str(n % 2)},
    }
    for language in ("hi", "ta")
    for stratum in ("plain", "fraction")
    for n in range(4)
]


def experiment_dict(manifest: Path, digest: str) -> dict:
    return {
        "name": "test",
        "manifest": manifest,
        "manifest_sha256": digest,
        "scorer": "amount",
        "budget_credits": 100,
        "balance_by": "stratum",
        "voices": {
            "hi": [
                {"model": "timbre-v3.0", "voice": "Shivani"},
                {"model": "timbre-v3.0", "voice": "Avinash"},
            ],
            "ta": [{"model": "timbre-v3.0", "voice": "Lakshmi"}, {"model": "timbre-v2.5", "voice": "Asmita"}],
        },
        "conditions": {
            "clean16k": [],
            "phone": [{"kind": "mulaw"}],
            "babble10": [{"kind": "noise", "noise": "babble", "snr_db": 10}, {"kind": "mulaw"}],
        },
        "arms": [
            {
                "name": "core",
                "conditions": ["clean16k", "phone"],
                "stt": [
                    {"model": "prisma-v2.5", "format": "transcribe"},
                    {"model": "prisma-v3.0", "format": "transcribe"},
                ],
            },
            {
                "name": "noise",
                "where": {"fold": "0"},
                "conditions": ["phone", "babble10"],
                "stt": [{"model": "prisma-v3.0", "format": "transcribe"}],
            },
        ],
    }


class Bench:
    def __init__(self, tmp_path: Path) -> None:
        self.manifest = tmp_path / "items.jsonl"
        self.digest = write_manifest(self.manifest, ROWS)
        self.raw = experiment_dict(self.manifest, self.digest)
        self.ledger = Ledger(tmp_path / "ledger.jsonl")
        self.client = FakeClient(self.ledger)
        self.store = RunStore(tmp_path / "run")
        self.audio_root = tmp_path / "audio"

    @property
    def experiment(self) -> Experiment:
        return Experiment.model_validate(self.raw)

    @property
    def items(self) -> tuple[Item, ...]:
        return load_manifest(self.manifest, expect_sha256=self.digest)

    def run(self, **overrides):
        from samajh.evalkit.runner import run

        settings = {
            "client": self.client,
            "store": self.store,
            "audio_root": self.audio_root,
            "ledger": self.ledger,
            "rates": RATES,
            "log": lambda _line: None,
        }
        return run(self.experiment, self.items, **{**settings, **overrides})
