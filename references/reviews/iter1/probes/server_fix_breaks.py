"""Reviewer probe: try to break the W7 review fixes. Offline: loopback sockets, ffmpeg, and a
fake-backed server on --port. Never Gnani.

    uv run python references/reviews/iter1/probes/server_fix_breaks.py --port 8191 --state <scratch>/state --ctl <scratch>/ctl [--only N ...]
"""

from __future__ import annotations

import argparse
import json
import resource
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx

from samajh.server.audio import AudioRejected, normalise_turn
from samajh.server.speech import LIVE, DeadlineTransport

REPO = Path(__file__).resolve().parents[4]


def riff(body: bytes) -> bytes:
    return b"RIFF" + struct.pack("<I", len(body)) + body


def fmt(rate: int, channels: int = 1, bits: int = 16, tag: int = 1) -> bytes:
    block = channels * bits // 8
    return b"fmt " + struct.pack("<IHHIIHH", 16, tag, channels, rate, (rate * block) & 0xFFFFFFFF, block, bits)


def data(n_bytes: int) -> bytes:
    return b"data" + struct.pack("<I", n_bytes) + (b"\x10\x20" * (n_bytes // 2 + 1))[:n_bytes]


def canonical(seconds: float, rate: int = 8000) -> bytes:
    return riff(b"WAVE" + fmt(rate) + data(round(seconds * rate) * 2))


def serve(script) -> tuple[str, socket.socket]:
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(8)

    def loop() -> None:
        while True:
            try:
                peer, _ = server.accept()
            except OSError:
                return
            threading.Thread(target=script, args=(peer,), daemon=True).start()

    threading.Thread(target=loop, daemon=True).start()
    return f"http://127.0.0.1:{server.getsockname()[1]}", server


def fix2() -> None:
    print("FIX 2. total response deadline (samajh/server/speech.py DeadlineTransport)")

    def drip_body(peer: socket.socket) -> None:
        with peer:
            try:
                peer.recv(65536)
                peer.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 100000\r\n\r\n")
                for _ in range(300):
                    peer.sendall(b" ")
                    time.sleep(0.1)
            except OSError:
                pass

    def drip_headers(peer: socket.socket) -> None:
        # One header byte every 0.3 s: 30 s of headers, never a body.
        head = b"HTTP/1.1 200 OK\r\n" + b"X-Pad: " + b"a" * 80 + b"\r\nContent-Length: 2\r\n\r\nok"
        with peer:
            try:
                peer.recv(65536)
                for i in range(len(head)):
                    peer.sendall(head[i : i + 1])
                    time.sleep(0.3)
            except OSError:
                pass

    for label, script in (("body dripped 1 byte / 0.1 s", drip_body), ("HEADERS dripped 1 byte / 0.3 s (about 33 s in all)", drip_headers)):
        url, server = serve(script)
        started = time.monotonic()
        outcome = "returned 200"
        try:
            with httpx.Client(transport=DeadlineTransport(0.5)) as http:
                outcome = f"returned {http.get(url, timeout=1.0).status_code}"
        except httpx.HTTPError as exc:
            outcome = f"raised {type(exc).__name__}"
        print(f"   deadline 0.5 s, per-read timeout 1.0 s, {label}: {outcome} after {time.monotonic() - started:.1f} s")
        server.close()
    print(f"   live profile: timeout {LIVE.timeout} s, deadline {LIVE.deadline} s, attempts {LIVE.retry.max_attempts}, lock wait {LIVE.lock_timeout} s")


def run_ffmpeg_case(label: str, wav: bytes) -> None:
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    try:
        out = normalise_turn(wav, 8000)
        outcome = f"accepted, {len(out)} bytes out"
    except AudioRejected as exc:
        outcome = f"refused {exc.code}: {exc.message}"
    took = time.monotonic() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    peak = after.ru_maxrss / (1024 * 1024) if sys.platform == "darwin" else after.ru_maxrss / 1024
    cpu = (after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime)
    print(f"   {label:<64} {len(wav):>8} bytes in -> {outcome}; wall {took:.2f} s, child cpu {cpu:.2f} s, largest child so far {peak:.0f} MiB")


def fix3_and_10(port: int) -> None:
    print("FIX 3 / 10. header checked before ffmpeg; PCM decoders only (samajh/server/audio.py)")
    print("   the server's _fmt() keeps the LAST fmt chunk; ffmpeg's WAV demuxer uses the FIRST")
    run_ffmpeg_case("control: 1 s of 48 kHz stereo", riff(b"WAVE" + fmt(48000, 2) + data(192000)))
    run_ffmpeg_case("the reviewer's case: one fmt chunk, 100 MHz", riff(b"WAVE" + fmt(100_000_000) + data(200)))
    two = riff(b"WAVE" + fmt(100_000_000) + fmt(48000) + data(200))
    run_ffmpeg_case("two fmt chunks: 100 MHz first, 48 kHz last (268 bytes)", two)
    run_ffmpeg_case("two fmt chunks: 100 MHz 8 ch first, 48 kHz last", riff(b"WAVE" + fmt(100_000_000, 8) + fmt(48000) + data(1600)))
    run_ffmpeg_case("two fmt chunks: 2 GHz first, 48 kHz last", riff(b"WAVE" + fmt(2_000_000_000) + fmt(48000) + data(200)))
    for tag, name in ((0x55, "MP3"), (2, "MS ADPCM"), (6, "A-law"), (7, "mu-law"), (0x11, "IMA ADPCM"), (0x161, "WMA2"), (0xFF, "AAC")):
        body = b"\xff\xfb\x90\x00" * 2000 if tag == 0x55 else b"\x55" * 8000
        wav = riff(b"WAVE" + fmt(8000, 1, 8, tag) + fmt(48000) + b"data" + struct.pack("<I", len(body)) + body)
        run_ffmpeg_case(f"two fmt chunks: tag {tag:#x} ({name}) first, PCM 48 kHz last", wav)
    base = f"http://127.0.0.1:{port}"
    with httpx.Client(base_url=base, timeout=120) as http:
        sid = http.post("/api/sessions", json={"dialogue": "count"}).json()["session_id"]
        started = time.monotonic()
        r = http.post(f"/api/sessions/{sid}/turns?source=file", content=two)
        print(f"   over HTTP, the 268-byte two-fmt file: {r.status_code} {r.text[:150]} [{time.monotonic() - started:.2f} s]")


def fix4() -> None:
    print("FIX 4. the pass-through pins every header field (canonical_seconds)")
    out = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("server_wav_disagreement.py")), str(Path(sys.argv[0]).parent / "_unused")],
        capture_output=True, text=True, check=False,
    )
    print("   (see server_wav_disagreement.py; run separately with a scratch dir)" if out.returncode else out.stdout)


def fix5(port: int, ctl: Path) -> None:
    print("FIX 5. a repeated TTS error is logged once (app.py _fail)")
    with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=60) as http:
        created = http.post("/api/sessions", json={"dialogue": "count"}).json()
        sid, url = created["session_id"], created["bot"]["audio_url"]
        (ctl / "tts_error").write_text("1")
        try:
            codes = [http.get(url).status_code for _ in range(20)]
            n = sum(e["type"] == "error" for e in http.get(f"/api/sessions/{sid}").json()["events"])
            print(f"   20 fetches of a failing prompt: statuses {sorted(set(codes))}, error events logged: {n}")
            for _ in range(20):
                http.get(url)
                http.post(f"/api/sessions/{sid}/turns?source=file", content=b"junk")
            n = sum(e["type"] == "error" for e in http.get(f"/api/sessions/{sid}").json()["events"])
            print(f"   20 x (failing prompt fetch, then a junk upload): error events logged: {n}")
            started = time.monotonic()
            last = None
            for i in range(1100):
                last = http.post(f"/api/sessions/{sid}/turns?source=file", content=b"junk")
                if last.status_code == 409:
                    break
            log = http.get(f"/api/sessions/{sid}").json()
            print(f"   junk uploads until refused: stopped after {i + 1} more posts with {last.status_code} {last.json()['error']['code']}; "
                  f"events in log: {len(log['events'])}; [{time.monotonic() - started:.1f} s]")
        finally:
            (ctl / "tts_error").unlink(missing_ok=True)
        real = http.post(f"/api/sessions/{sid}/turns?source=file&reply_to=0", content=canonical(0.5))
        print(f"   a genuine turn on that call now: {real.status_code} {real.text[:120]}")
        size = len(json.dumps(log))
        print(f"   log JSON is {size} bytes")


def fix6(port: int) -> None:
    print("FIX 6. one upload per call, 20 s for the body to arrive (app.py turn)")
    with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=60) as http:
        sid = http.post("/api/sessions", json={"dialogue": "count"}).json()["session_id"]
        s = socket.create_connection(("127.0.0.1", port))
        s.sendall(f"POST /api/sessions/{sid}/turns?source=mic&reply_to=0 HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Length: 500000\r\n\r\n".encode() + b"RIFF")
        started = time.monotonic()
        time.sleep(1.0)
        r = http.post(f"/api/sessions/{sid}/turns?source=mic&reply_to=0", content=canonical(0.5))
        print(f"   while another connection stalls its body: the caller's real turn gets {r.status_code} {r.json().get('error', {}).get('code')}")

        def drip() -> None:
            try:
                for _ in range(40):
                    s.sendall(b"\0")
                    time.sleep(1.0)
            except OSError:
                pass

        threading.Thread(target=drip, daemon=True).start()
        s.settimeout(40)
        reply = s.recv(65536)
        took = time.monotonic() - started
        status_line = reply.split(b"\r\n")[0].decode()
        tail = reply.split(b"\r\n\r\n")[-1][:110].decode()
        print(f"   the stalled upload (1 byte per second) was answered after {took:.1f} s: {status_line} {tail}")
        s.close()
        r = http.post(f"/api/sessions/{sid}/turns?source=mic&reply_to=0", content=canonical(0.5))
        print(f"   afterwards the caller's turn: {r.status_code}")
        events = http.get(f"/api/sessions/{sid}").json()["events"]
        print(f"   events: {[(e['type'], e.get('code')) for e in events]}")


def fix11(port: int, state: Path, ctl: Path) -> None:
    print("FIX 11. replay ends a failed call; nothing is synthesised after a hang-up")
    before = {p.name for p in (state / "sessions").iterdir()}
    (ctl / "tts_error").write_text("1")
    try:
        run = subprocess.run(
            [sys.executable, "-m", "samajh.server.replay", str(REPO / "tests/fixtures/server/stub-call"), "--url", f"http://127.0.0.1:{port}"],
            capture_output=True, text=True, check=False, cwd=REPO, env={"PATH": "/usr/bin:/bin:/opt/homebrew/bin", "GNANI_API_KEY": "", "SAMAJH_STATE_DIR": str(state)},
        )
    finally:
        (ctl / "tts_error").unlink(missing_ok=True)
    print(f"   replay while every prompt fetch fails: exit {run.returncode}; stderr {run.stderr.strip()[:230]}")
    new = sorted({p.name for p in (state / "sessions").iterdir()} - before)
    for sid in new:
        log = json.loads((state / "sessions" / sid / "session.json").read_text())
        print(f"   session {sid} left on the server: status={log['status']} ended_reason={log['ended_reason']} events={[(e['type'], e.get('code')) for e in log['events']]}")
    (ctl / "stt_error").write_text("1")
    before = {p.name for p in (state / "sessions").iterdir()}
    try:
        run = subprocess.run(
            [sys.executable, "-m", "samajh.server.replay", str(REPO / "tests/fixtures/server/stub-call"), "--url", f"http://127.0.0.1:{port}"],
            capture_output=True, text=True, check=False, cwd=REPO, env={"PATH": "/usr/bin:/bin:/opt/homebrew/bin", "GNANI_API_KEY": "", "SAMAJH_STATE_DIR": str(state)},
        )
    finally:
        (ctl / "stt_error").unlink(missing_ok=True)
    print(f"   replay while every STT call fails (the case the fix names): exit {run.returncode}; stderr {run.stderr.strip()[:200]}")
    for sid in sorted({p.name for p in (state / "sessions").iterdir()} - before):
        log = json.loads((state / "sessions" / sid / "session.json").read_text())
        print(f"   session {sid}: status={log['status']} ended_reason={log['ended_reason']} events={[(e['type'], e.get('code')) for e in log['events']]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8191)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--ctl", type=Path, required=True)
    parser.add_argument("--only", action="append")
    args = parser.parse_args()
    steps = {"2": fix2, "3": lambda: fix3_and_10(args.port), "5": lambda: fix5(args.port, args.ctl),
             "6": lambda: fix6(args.port), "11": lambda: fix11(args.port, args.state, args.ctl)}
    for name, fn in steps.items():
        if not args.only or name in args.only:
            fn()
            sys.stdout.flush()


if __name__ == "__main__":
    main()
