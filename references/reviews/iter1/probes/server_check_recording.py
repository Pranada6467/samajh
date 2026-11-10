"""Reviewer check: is a session's call.wav a valid WAV whose length and content match its log?

    uv run python references/reviews/iter1/probes/server_check_recording.py <state>/sessions/<id> [--url http://127.0.0.1:8191]

Reads only the files of one session directory (and, with --url, the same session over HTTP).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import urllib.request
import wave
from pathlib import Path


def shape(data: bytes) -> tuple[int, int, int, int, bytes]:
    with wave.open(io.BytesIO(data)) as f:
        return f.getnchannels(), f.getsampwidth(), f.getframerate(), f.getnframes(), f.readframes(f.getnframes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dir", type=Path)
    parser.add_argument("--url")
    args = parser.parse_args()
    log = json.loads((args.dir / "session.json").read_text())
    rate = log["line_rate"]
    print(f"session {log['session_id']} status={log['status']} ended_reason={log['ended_reason']} line_rate={rate}")
    print(f"stt={log['stt']} tts={log['tts']} events={len(log['events'])}")
    call = (args.dir / "call.wav").read_bytes()
    ch, width, call_rate, frames, pcm = shape(call)
    print(f"call.wav: {len(call)} bytes, channels={ch} width={width} rate={call_rate} frames={frames} "
          f"seconds={frames / call_rate:.6f} sha256={hashlib.sha256(call).hexdigest()[:16]}")
    rec = log["recording"]
    print(f"log.recording: {rec and {k: (v[:16] if k == 'sha256' else v) for k, v in rec.items()}}")
    ok = True
    gap = round(0.5 * rate)
    cursor = 0
    total_audio = 0.0
    n_audio = 0
    for e in log["events"]:
        line = f"  {e['seq']} {e['type']:8} at={e['at']:<7} audio={e['audio']} secs={e['audio_seconds']} rec={e['rec_start']}-{e['rec_end']}"
        if e["type"] == "customer":
            line += f" src={e['source']} stt={e['stt'] and (e['stt']['model'], e['stt']['params'])} text={e['transcript']!r}"
        if e["type"] == "bot":
            line += f" end_call={e['end_call']} tags={e['tags']} tts={e['tts'] and (e['tts']['model'], e['tts']['voice'], e['tts']['sample_rate'])}"
        if e["type"] == "error":
            line += f" {e['stage']} {e['status']} {e['code']}"
        print(line)
        if e["type"] == "error" or e["audio"] is None:
            continue
        clip = (args.dir / e["audio"]).read_bytes()
        cch, cw, cr, cf, cpcm = shape(clip)
        if (cch, cw, cr) != (1, 2, rate):
            print(f"    MISMATCH clip shape {(cch, cw, cr)}")
            ok = False
        if abs(cf / cr - e["audio_seconds"]) > 1e-6:
            print(f"    MISMATCH audio_seconds {e['audio_seconds']} vs file {cf / cr}")
            ok = False
        if n_audio:
            if pcm[cursor * 2 : (cursor + gap) * 2] != b"\0\0" * gap:
                print("    MISMATCH gap before this event is not digital silence")
                ok = False
            cursor += gap
        if abs(cursor / rate - e["rec_start"]) > 1e-6:
            print(f"    MISMATCH rec_start {e['rec_start']} vs offset {cursor / rate}")
            ok = False
        if pcm[cursor * 2 : (cursor + cf) * 2] != cpcm:
            print("    MISMATCH samples in call.wav at rec_start differ from the event's audio")
            ok = False
        cursor += cf
        if abs(cursor / rate - e["rec_end"]) > 1e-6:
            print(f"    MISMATCH rec_end {e['rec_end']} vs offset {cursor / rate}")
            ok = False
        total_audio += cf / cr
        n_audio += 1
    expected = total_audio + 0.5 * max(0, n_audio - 1)
    print(f"audio events={n_audio} sum of clips={total_audio:.6f}s + gaps={0.5 * max(0, n_audio - 1)}s = {expected:.6f}s; "
          f"call.wav={frames / call_rate:.6f}s; cursor end={cursor / rate:.6f}s")
    if cursor != frames or (ch, width, call_rate) != (1, 2, rate):
        print("MISMATCH call.wav length or shape")
        ok = False
    if rec and (abs(rec["seconds"] - frames / call_rate) > 1e-6 or rec["sha256"] != hashlib.sha256(call).hexdigest()):
        print("MISMATCH log.recording seconds or sha256")
        ok = False
    if args.url:
        base = f"{args.url}/api/sessions/{log['session_id']}"
        over_http = urllib.request.urlopen(f"{base}/recording.wav").read()
        print(f"GET recording.wav: {len(over_http)} bytes, same bytes as call.wav on disk: {over_http == (args.dir / 'call.wav').read_bytes()}")
        http_log = json.loads(urllib.request.urlopen(base).read())
        disk_log = json.loads((args.dir / "session.json").read_text())
        print(f"GET session log equals session.json on disk: {http_log == disk_log}")
    print("RESULT", "consistent" if ok else "INCONSISTENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
