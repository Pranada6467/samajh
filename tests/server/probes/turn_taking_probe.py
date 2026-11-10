"""Turn-taking probe: REST per turn against Prisma WebSocket streaming, on the same clips.

REST calls go through `samajh.clients.gnani` (lock, cache, ledger). Streaming is not wrapped by
the client: this script opens the socket itself, which is safe next to other workers because an
open streaming session does not take the one REST slot (api-probe-iter1.md section 5). How
streaming is billed is unknown, so every streamed second is written to the ledger at the REST
STT rate and the runs are kept short.

  uv run python tests/server/probes/turn_taking_probe.py clips
  uv run python tests/server/probes/turn_taking_probe.py rest [--model prisma-v3.0]
  uv run --with websockets python tests/server/probes/turn_taking_probe.py stream --mode server|commit
        [--model prisma-v3.0] [--min-silence-ms 500] [--only ID ...] [--burst] [--hinglish hi-IN]
  uv run --with websockets python tests/server/probes/turn_taking_probe.py edge silence|idle|abort|nolang
  uv run python tests/server/probes/turn_taking_probe.py report

Clips and results live under `.samajh/w7/` (gitignored). Each run is appended to
`results.jsonl`; `report` reads the latest row per (path, model, mode, clip).
"""

from __future__ import annotations

import argparse
import array
import asyncio
import json
import math
import os
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from samajh.amounts import Parsed, parse_amount
from samajh.clients._runtime import Ledger, LedgerEntry, load_defaults, load_env, state_dir
from samajh.clients.gnani import GnaniClient, PrismaV25, PrismaV30, Timbre, wav_seconds

ROOT = Path(__file__).resolve().parents[3]
OUT = state_dir() / "w7"
CLIPS = OUT / "clips"
RESULTS = OUT / "results.jsonl"
FIXTURES = ROOT / "tests" / "fixtures" / "server" / "stub-call"
STREAM_URL = "wss://api.vachana.ai/stt/v3/stream"
RATE = 8000
FRAME_BYTES = 1024  # [docs] every binary frame is exactly 1,024 bytes (512 samples)
FRAME_SECONDS = FRAME_BYTES / 2 / RATE

# id, TTS language, text, gold rupee amount. The first 16 are the amounts pilot's sentences.
# Tamil and Kannada text is not human-reviewed.
SINGLE = [
    ("hi01", "hi-IN", "मेरे लोन से बावन हज़ार रुपये कटे।", 52000),
    ("hi03", "hi-IN", "सवा दो लाख का लोन मिला।", 225000),
    ("hi06", "hi-IN", "पाँच लाख बीस हज़ार रुपये का लोन है।", 520000),
    ("hi08", "hi-IN", "पौने दो लाख रुपये जमा किए।", 175000),
    ("he01", "hi-en", "लोन के साथ twenty five thousand का insurance दिया।", 25000),
    ("he02", "hi-en", "प्रीमियम one point five lakh rupees था।", 150000),
    ("he03", "hi-en", "मेरी EMI eleven thousand two hundred rupees है।", 11200),
    ("he04", "hi-en", "cover ten lakh rupees का बताया।", 1000000),
    ("ta01", "ta-IN", "ஐம்பத்திரண்டாயிரம் ரூபாய் கழித்தார்கள்.", 52000),
    ("ta02", "ta-IN", "ஒன்றரை லட்சம் ரூபாய் பிரீமியம்.", 150000),
    ("ta03", "ta-IN", "மூன்று லட்சத்து இருபதாயிரம் ரூபாய் கடன்.", 320000),
    ("ta04", "ta-IN", "இரண்டரை கோடி ரூபாய் காப்பீடு.", 25000000),
    ("kn01", "kn-IN", "ಐವತ್ತೆರಡು ಸಾವಿರ ರೂಪಾಯಿ ಕಡಿತ ಮಾಡಿದರು.", 52000),
    ("kn02", "kn-IN", "ಒಂದೂವರೆ ಲಕ್ಷ ರೂಪಾಯಿ ಪ್ರೀಮಿಯಂ.", 150000),
    ("kn03", "kn-IN", "ಮೂರು ಲಕ್ಷದ ಇಪ್ಪತ್ತು ಸಾವಿರ ರೂಪಾಯಿ ಸಾಲ.", 320000),
    ("kn04", "kn-IN", "ಎರಡೂವರೆ ಕೋಟಿ ರೂಪಾಯಿ ವಿಮೆ.", 25000000),
]
# Two sentences with a silent gap spliced between them: one customer turn with a thinking pause.
PAUSED = [
    ("pa01", "hi-IN", ("बस एक एफ़डी ली थी, लोन सिक्योरिटी के लिए।", "बावन हज़ार रुपये की।"), 600, 52000),
    ("pa02", "hi-IN", ("लोन के साथ एक बीमा भी दिया था।", "उसके अड़तीस हज़ार रुपये कटे।"), 600, 38000),
    (
        "pa03",
        "hi-en",
        ("loan के साथ एक policy भी थी।", "उसका premium twenty five thousand rupees था।"),
        600,
        25000,
    ),
    ("pa04", "hi-IN", ("मुझे ठीक से याद नहीं है।", "शायद डेढ़ लाख रुपये का कवर था।"), 900, 150000),
]
STUB_ANSWERS = [
    ("01-loan-amount", "मैंने पाँच लाख रुपये का लोन लिया था।"),
    ("02-emi", "हर महीने की किस्त साढ़े ग्यारह हज़ार रुपये है।"),
    ("03-what-else", "बस एक एफ़डी ली थी, लोन सिक्योरिटी के लिए, बावन हज़ार की।"),
]
CUSTOMER_VOICES = ("Avinash", "Kalpana")  # the bot speaks as Shivani


def pcm_of(wav: bytes) -> bytes:
    return wav[wav.index(b"data") + 8 :]


def wav_of(pcm: bytes, rate: int = RATE) -> bytes:
    import io
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buffer.getvalue()


def speech_bounds(pcm: bytes, rate: int = RATE) -> tuple[float, float]:
    """(start, end) in seconds of the first and last 10 ms frame louder than -40 dBFS."""
    samples = array.array("h", pcm[: len(pcm) // 2 * 2])
    step = rate // 100
    voiced = [
        i
        for i in range(0, len(samples) - step + 1, step)
        if math.sqrt(sum(s * s for s in samples[i : i + step]) / step) > 328
    ]
    if not voiced:
        return 0.0, 0.0
    return voiced[0] / rate, (voiced[-1] + step) / rate


def stt_options(model: str, tts_language: str) -> PrismaV30 | PrismaV25:
    if model == "prisma-v2.5":
        return PrismaV25(language="hi-IN" if tts_language == "hi-en" else tts_language, format="transcribe")
    language: Any = ("hi-IN", "en-IN") if tts_language == "hi-en" else tts_language
    return PrismaV30(language=language, format="transcribe")


def language_header(model: str, tts_language: str) -> str:
    language = stt_options(model, tts_language).language
    return language if isinstance(language, str) else ",".join(language)


def amount_of(text: str) -> int | None:
    result = parse_amount(text)
    return int(result.rupees) if isinstance(result, Parsed) else None


def manifest() -> list[dict[str, Any]]:
    return json.loads((CLIPS / "manifest.json").read_text())


def record(row: dict[str, Any]) -> None:
    row["ts"] = datetime.now(UTC).isoformat(timespec="seconds")
    with RESULTS.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------ clips


def make_clips() -> None:
    client = GnaniClient.from_env()
    CLIPS.mkdir(parents=True, exist_ok=True)
    FIXTURES.mkdir(parents=True, exist_ok=True)

    def say(text: str, language: str, voice: str) -> bytes:
        options = Timbre(model="timbre-v3.0", voice=voice, language=language, sample_rate=RATE)  # type: ignore[arg-type]
        return client.tts(text, options).audio

    rows = []
    for i, (clip_id, language, text, gold) in enumerate(SINGLE):
        voice = CUSTOMER_VOICES[i % 2]
        wav = say(text, language, voice)
        (CLIPS / f"{clip_id}.wav").write_bytes(wav)
        rows.append(
            {"id": clip_id, "language": language, "text": text, "gold": gold, "voice": voice, "pause_ms": 0}
        )
    for i, (clip_id, language, parts, pause_ms, gold) in enumerate(PAUSED):
        voice = CUSTOMER_VOICES[i % 2]
        first, second = (pcm_of(say(part, language, voice)) for part in parts)
        # Trim each part to its speech so the spliced gap is exactly `pause_ms` of digital silence.
        a0, a1 = speech_bounds(first)
        b0, b1 = speech_bounds(second)
        cut = lambda pcm, s, e: pcm[int(s * RATE) * 2 : int(e * RATE) * 2]
        pcm = (
            cut(first, max(0.0, a0 - 0.05), a1)
            + bytes(pause_ms * RATE // 1000 * 2)
            + cut(second, b0, b1 + 0.05)
        )
        (CLIPS / f"{clip_id}.wav").write_bytes(wav_of(pcm))
        rows.append(
            {
                "id": clip_id,
                "language": language,
                "text": " ".join(parts),
                "gold": gold,
                "voice": voice,
                "pause_ms": pause_ms,
                "pause_at_s": round(a1 - max(0.0, a0 - 0.05), 3),
            }
        )
    for row in rows:
        wav = (CLIPS / f"{row['id']}.wav").read_bytes()
        start, end = speech_bounds(pcm_of(wav))
        row.update(
            seconds=round(wav_seconds(wav) or 0.0, 3),
            speech_start_s=round(start, 3),
            speech_end_s=round(end, 3),
        )
    (CLIPS / "manifest.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    for name, text in STUB_ANSWERS:
        (FIXTURES / f"{name}.wav").write_bytes(say(text, "hi-IN", "Avinash"))
    print(
        json.dumps(
            {
                "clips": len(rows),
                "seconds": round(sum(r["seconds"] for r in rows), 1),
                "fixtures": [n for n, _ in STUB_ANSWERS],
                "credits_spent_total": round(client.credits_spent(), 3),
            }
        )
    )


# ------------------------------------------------------------------ REST


def run_rest(model: str, only: list[str]) -> None:
    client = GnaniClient.from_env()
    for row in manifest():
        if only and row["id"] not in only:
            continue
        wav = (CLIPS / f"{row['id']}.wav").read_bytes()
        started = time.monotonic()
        result = client.stt(wav, stt_options(model, row["language"]))
        wall = time.monotonic() - started
        out = {
            "path": "rest",
            "model": model,
            "mode": "rest",
            "id": row["id"],
            "transcript": result.text,
            "amount": amount_of(result.text),
            "gold": row["gold"],
            "cache_hit": result.call.cache_hit,
            "stt_s": round(wall, 3),
            "attempts": result.call.attempts,
        }
        record(out)
        print(json.dumps(out, ensure_ascii=False))


# ------------------------------------------------------------------ streaming


def _scrub(text: str) -> str:
    return text.replace(os.environ.get("GNANI_API_KEY", "\0"), "<key>")


def _bill_stream(model: str, audio_seconds: float, wall: float) -> None:
    rate = load_defaults()["gnani"]["stt_credits_per_second"]
    Ledger(state_dir() / "ledger.jsonl").append(
        LedgerEntry(
            ts=datetime.now(UTC).isoformat(timespec="seconds"),
            provider="gnani",
            kind="stt.stream",
            model=model,
            status=101,
            attempt=1,
            seconds=round(wall, 4),
            cache_hit=False,
            cache_key="",
            est_credits=round(audio_seconds * rate, 6),
            audio_seconds=round(audio_seconds, 3),
        )
    )


class _ServerClosed(Exception):
    """The server closed the socket while audio was still being sent."""


async def stream_clip(
    pcm: bytes,
    *,
    model: str,
    language: str,
    mode: str,
    min_silence_ms: int | None,
    burst: bool = False,
    tail_seconds: float = 4.0,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Send one clip and return every server message with its arrival time on the audio clock
    (0 = the instant the first sample was "spoken")."""
    import websockets

    headers = {
        "x-api-key-id": os.environ["GNANI_API_KEY"],
        "model": model,
        "language_code": language,
        "x-sample-rate": str(RATE),
        "format": "transcribe",
        **(extra_headers or {}),
    }
    if min_silence_ms is not None:
        headers["x-min-silence-ms"] = str(min_silence_ms)
    pcm = pcm + bytes(-len(pcm) % FRAME_BYTES)
    frames = [pcm[i : i + FRAME_BYTES] for i in range(0, len(pcm), FRAME_BYTES)]
    messages: list[dict[str, Any]] = []
    opened = time.monotonic()
    sent = 0
    async with websockets.connect(STREAM_URL, additional_headers=headers, open_timeout=10) as sock:
        first = json.loads(await asyncio.wait_for(sock.recv(), 10))
        connect_s = time.monotonic() - opened
        t0 = time.monotonic()

        async def reader() -> None:
            try:
                async for raw in sock:
                    message = json.loads(raw)
                    message["_at"] = round(time.monotonic() - t0, 3)
                    messages.append(message)
            except websockets.ConnectionClosed as exc:
                messages.append(
                    {
                        "type": "_closed",
                        "_at": round(time.monotonic() - t0, 3),
                        "code": exc.rcvd.code if exc.rcvd else None,
                        "reason": _scrub(exc.rcvd.reason if exc.rcvd else ""),
                    }
                )

        task = asyncio.create_task(reader())

        async def send_paced(index: int, frame: bytes) -> None:
            nonlocal sent
            if not burst:
                # A frame can be sent only once its last sample exists, as with a live microphone.
                await asyncio.sleep(max(0.0, t0 + (index + 1) * FRAME_SECONDS - time.monotonic()))
            if task.done():
                raise _ServerClosed
            await sock.send(frame)
            sent += 1

        try:
            for i, frame in enumerate(frames):
                await send_paced(i, frame)
        except (_ServerClosed, websockets.ConnectionClosed):
            mode = "closed"
        if mode == "closed":
            commit_at = None
        elif mode == "commit":
            await sock.send(json.dumps({"type": "commit"}))
            commit_at = time.monotonic() - t0
            deadline = time.monotonic() + tail_seconds
            while time.monotonic() < deadline and not any(
                m.get("type") == "transcript" and m["_at"] >= commit_at for m in messages
            ):
                await asyncio.sleep(0.01)
        else:
            commit_at = None
            silence = bytes(FRAME_BYTES)
            index = len(frames)
            clip_end = len(frames) * FRAME_SECONDS
            # Keep the line open with silence, as an open microphone would, until the last
            # segment's transcript has arrived and 1.2 s have passed with no new segment.
            while True:
                now = time.monotonic() - t0
                finals = [m for m in messages if m.get("type") == "transcript"]
                starts = [m for m in messages if m.get("type") == "speech_start"]
                settled = finals and len(finals) >= len(starts) and now - finals[-1]["_at"] > 1.2
                if settled or now > clip_end + tail_seconds:
                    break
                try:
                    await send_paced(index, silence)
                except (_ServerClosed, websockets.ConnectionClosed):
                    break
                index += 1
        await sock.close()
        task.cancel()
    wall = time.monotonic() - opened
    audio_seconds = sent * FRAME_SECONDS
    _bill_stream(model, audio_seconds, wall)
    return {
        "connected": {k: v for k, v in first.items() if k != "timestamp"},
        "connect_s": round(connect_s, 3),
        "commit_at": None if commit_at is None else round(commit_at, 3),
        "audio_sent_s": round(audio_seconds, 3),
        "messages": messages,
    }


def run_stream(
    model: str, mode: str, min_silence_ms: int | None, only: list[str], burst: bool, hinglish: str | None
) -> None:
    load_env()
    label = mode + ("" if min_silence_ms is None else f"@{min_silence_ms}") + ("+burst" if burst else "")
    for row in manifest():
        if only and row["id"] not in only:
            continue
        pcm = pcm_of((CLIPS / f"{row['id']}.wav").read_bytes())
        language = (
            hinglish if hinglish and row["language"] == "hi-en" else language_header(model, row["language"])
        )
        try:
            got = asyncio.run(
                stream_clip(
                    pcm,
                    model=model,
                    language=language,
                    mode=mode,
                    min_silence_ms=min_silence_ms,
                    burst=burst,
                )
            )
        except Exception as exc:  # noqa: BLE001 - a probe reports whatever the server does
            print(
                json.dumps({"id": row["id"], "error": type(exc).__name__, "detail": _scrub(str(exc))[:300]})
            )
            continue
        finals = [m for m in got["messages"] if m.get("type") == "transcript"]
        text = " ".join(m.get("text", "") for m in finals).strip()
        out = {
            "path": "stream",
            "model": model,
            "mode": label,
            "id": row["id"],
            "transcript": text,
            "amount": amount_of(text),
            "gold": row["gold"],
            "segments": len(finals),
            "connect_s": got["connect_s"],
            "audio_sent_s": got["audio_sent_s"],
            "speech_end_s": row["speech_end_s"],
            # From the true end of speech in the clip to the last final transcript.
            "eos_to_transcript_s": round(finals[-1]["_at"] - row["speech_end_s"], 3) if finals else None,
            "first_final_at_s": finals[0]["_at"] if finals else None,
            "server_latency_ms": [m.get("latency") for m in finals],
            "events": [(m.get("type"), m["_at"]) for m in got["messages"]],
            "server_errors": [
                {k: v for k, v in m.items() if k != "timestamp"}
                for m in got["messages"]
                if m.get("type") in ("error", "_closed")
            ],
            "language_header": language,
        }
        record(out)
        print(json.dumps(out, ensure_ascii=False))


def run_edge(case: str) -> None:
    load_env()
    import websockets

    async def go() -> dict[str, Any]:
        if case == "silence":  # 3 s of digital silence, then commit
            got = await stream_clip(
                bytes(RATE * 2 * 3),
                model="prisma-v3.0",
                language="hi-IN",
                mode="commit",
                min_silence_ms=None,
                tail_seconds=3.0,
            )
            return {"case": case, "messages": got["messages"]}
        if case == "abort":  # half a clip, then the socket is dropped with no commit
            pcm = pcm_of((CLIPS / "hi01.wav").read_bytes())
            headers = {
                "x-api-key-id": os.environ["GNANI_API_KEY"],
                "model": "prisma-v3.0",
                "language_code": "hi-IN",
                "x-sample-rate": str(RATE),
                "format": "transcribe",
            }
            async with websockets.connect(STREAM_URL, additional_headers=headers) as sock:
                await sock.recv()
                frames = [
                    pcm[i : i + FRAME_BYTES] for i in range(0, len(pcm) // 2 - FRAME_BYTES, FRAME_BYTES)
                ]
                for frame in frames:
                    await sock.send(frame)
                    await asyncio.sleep(FRAME_SECONDS)
                sock.transport.abort()
            _bill_stream("prisma-v3.0", len(frames) * FRAME_SECONDS, 0.0)
            return {"case": case, "frames_sent": len(frames), "result": "socket aborted mid-utterance"}
        headers = {
            "x-api-key-id": os.environ["GNANI_API_KEY"],
            "model": "prisma-v3.0",
            "x-sample-rate": str(RATE),
            "format": "transcribe",
        }
        if case == "idle":  # no audio at all: how long does the server keep the session?
            headers |= {"language_code": "hi-IN", "x-idle-timeout-sec": "5"}
        seen: list[Any] = []
        started = time.monotonic()
        try:
            async with websockets.connect(STREAM_URL, additional_headers=headers, open_timeout=10) as sock:
                while time.monotonic() - started < 12:
                    raw = await asyncio.wait_for(sock.recv(), 12)
                    seen.append((round(time.monotonic() - started, 2), json.loads(raw)))
        except websockets.ConnectionClosed as exc:
            return {
                "case": case,
                "messages": seen,
                "closed_after_s": round(time.monotonic() - started, 2),
                "close_code": exc.rcvd.code if exc.rcvd else None,
                "close_reason": _scrub(exc.rcvd.reason if exc.rcvd else ""),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "case": case,
                "messages": seen,
                "error": type(exc).__name__,
                "detail": _scrub(str(exc))[:300],
            }
        return {"case": case, "messages": seen, "still_open_after_s": round(time.monotonic() - started, 2)}

    out = asyncio.run(go())
    record({"path": "edge", **out})
    print(json.dumps(out, ensure_ascii=False, default=str))


# ------------------------------------------------------------------ report


def report() -> None:
    latest: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for line in RESULTS.read_text().splitlines():
        row = json.loads(line)
        if row.get("path") in ("rest", "stream"):
            latest[(row["path"], row["model"], row["mode"], row["id"])] = row
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for (path, model, mode, _), row in sorted(latest.items()):
        groups.setdefault((path, model, mode), []).append(row)
    reference = {r["id"]: r for r in groups.get(("rest", "prisma-v3.0", "rest"), [])}
    for (path, model, mode), rows in groups.items():
        single = [r for r in rows if not r["id"].startswith("pa")]
        paused = [r for r in rows if r["id"].startswith("pa")]
        line: dict[str, Any] = {
            "path": path,
            "model": model,
            "mode": mode,
            "n": len(rows),
            "amount_right_single": f"{sum(r['amount'] == r['gold'] for r in single)}/{len(single)}",
            "amount_right_paused": f"{sum(r['amount'] == r['gold'] for r in paused)}/{len(paused)}",
        }
        if path == "rest":
            live = [r["stt_s"] for r in rows if not r["cache_hit"]]
            if live:
                line |= {
                    "stt_s_median": round(statistics.median(live), 3),
                    "stt_s_max": max(live),
                    "n_live": len(live),
                }
        else:
            lat = [r["eos_to_transcript_s"] for r in rows if r["eos_to_transcript_s"] is not None]
            line |= {
                "eos_to_transcript_median": round(statistics.median(lat), 3) if lat else None,
                "eos_min": min(lat, default=None),
                "eos_max": max(lat, default=None),
                "no_transcript": sum(r["eos_to_transcript_s"] is None for r in rows),
                "split_paused": f"{sum(r['segments'] > 1 for r in paused)}/{len(paused)}",
                "split_single": f"{sum(r['segments'] > 1 for r in single)}/{len(single)}",
                "connect_s_median": round(statistics.median(r["connect_s"] for r in rows), 3),
                "same_text_as_rest_v3": f"{sum(r['transcript'] == reference[r['id']]['transcript'] for r in rows if r['id'] in reference)}/{sum(r['id'] in reference for r in rows)}",
            }
        print(json.dumps(line, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("clips")
    rest = sub.add_parser("rest")
    stream = sub.add_parser("stream")
    stream.add_argument("--mode", choices=("server", "commit"), required=True)
    stream.add_argument("--min-silence-ms", type=int)
    stream.add_argument("--burst", action="store_true")
    stream.add_argument("--hinglish", help="language_code header to use for the hi-en clips")
    for p in (rest, stream):
        p.add_argument("--model", default="prisma-v3.0", choices=("prisma-v3.0", "prisma-v2.5"))
        p.add_argument("--only", nargs="*", default=[])
    edge = sub.add_parser("edge")
    edge.add_argument("case", choices=("silence", "idle", "abort", "nolang"))
    sub.add_parser("report")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.command == "clips":
        make_clips()
    elif args.command == "rest":
        run_rest(args.model, args.only)
    elif args.command == "stream":
        run_stream(args.model, args.mode, args.min_silence_ms, args.only, args.burst, args.hinglish)
    elif args.command == "edge":
        run_edge(args.case)
    else:
        report()


if __name__ == "__main__":
    sys.exit(main())
