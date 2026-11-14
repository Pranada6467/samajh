"""Live probe of `samajh.clients.gnani.stream` (spends credits; run by hand only).

  uv run python tests/clients/probes/stream_live.py OUT_DIR

Streams Timbre fixture clips through the new client at real-time pace (then 300 ms of silence,
then commit), with `min_silence_ms=2000`, and compares each to REST v3.0 `transcribe` through
`GnaniClient.stt` (cached when already made). Paused clips are spliced into OUT_DIR, never the repo.
Hinglish clips are streamed three ways: `hi-IN`; `hi-IN` + `multi_lang_codes=hi-IN,en-IN`; `en-IN`.
"""

from __future__ import annotations

import io
import json
import sys
import time
import wave
from pathlib import Path

from samajh.clients.gnani import GnaniClient, PrismaStream, PrismaV30, StreamError, stream_session

ROOT = Path(__file__).resolve().parents[3]
CALLS = ROOT / "tests" / "fixtures" / "server" / "calls"
RATE = 8000


def pcm_of(path: Path) -> bytes:
    with wave.open(str(path)) as w:
        assert w.getframerate() == RATE and w.getsampwidth() == 2 and w.getnchannels() == 1
        return w.readframes(w.getnframes())


def wav_of(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(RATE)
        w.writeframes(pcm)
    return buf.getvalue()


def trim(pcm: bytes) -> bytes:
    """Cut leading and trailing quiet (10 ms frames under about -40 dBFS)."""
    import array

    s = array.array("h", pcm)
    step = RATE // 100
    loud = [i for i in range(0, len(s) - step, step) if max(abs(x) for x in s[i : i + step]) > 330]
    return pcm[loud[0] * 2 : (loud[-1] + step) * 2] if loud else pcm


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    client = GnaniClient.from_env()
    clips: list[tuple[str, str, bytes]] = []
    for name in ("hero/03", "hero/08", "hero/13"):
        clips.append((name, "hi", pcm_of(CALLS / f"{name}.wav")))
    a, b = trim(pcm_of(CALLS / "hero/06.wav")), trim(pcm_of(CALLS / "hero/07.wav"))
    for ms in (600, 1000):
        pcm = a + bytes(ms * RATE // 1000 * 2) + b
        (out / f"pause{ms}.wav").write_bytes(wav_of(pcm))
        clips.append((f"pause{ms} (hero/06+07)", "hi", pcm))
    for name in ("informed/03", "informed/09"):
        clips.append((name, "hi-en", pcm_of(CALLS / f"{name}.wav")))

    rows = []
    for label, lang, pcm in clips:
        rest_lang = ("hi-IN", "en-IN") if lang == "hi-en" else "hi-IN"
        rest = client.stt(wav_of(pcm), PrismaV30(language=rest_lang, format="transcribe")).text
        variants = {"hi-IN": PrismaStream(language="hi-IN")}
        if lang == "hi-en":
            variants["hi-IN+multi"] = PrismaStream(language="hi-IN", multi_lang=("hi-IN", "en-IN"))
            variants["en-IN"] = PrismaStream(language="en-IN")
        for vname, opts in variants.items():
            row = {"clip": label, "variant": vname, "rest_v3": rest}
            try:
                with stream_session(client, opts) as s:
                    t0 = time.monotonic()
                    chunk = 1600  # 100 ms; the session re-frames to 1,024 bytes
                    for i, off in enumerate(range(0, len(pcm), chunk)):
                        time.sleep(max(0.0, t0 + i * 0.1 - time.monotonic()))
                        s.send(pcm[off : off + chunk])
                    for _ in range(3):
                        time.sleep(0.1)
                        s.send(bytes(1600))
                    r = s.commit(timeout_s=4.0)
                row |= {
                    "text": r.text,
                    "segments": list(r.segments),
                    "split": r.split,
                    "open_ms": r.open_ms,
                    "commit_to_final_ms": r.commit_to_final_ms,
                    "audio_s": r.audio_seconds,
                }
            except StreamError as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    (out / "results.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
