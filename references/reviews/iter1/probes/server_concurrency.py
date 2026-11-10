"""Reviewer probe: concurrent requests against a fake-backed Samajh server (never Gnani).

    uv run python references/reviews/iter1/probes/server_concurrency.py --port 8191 --state <scratch>/state --ctl <scratch>/ctl
"""

from __future__ import annotations

import argparse
import collections
import io
import json
import socket
import threading
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

BASE = ""


def wav(seconds: float, rate: int = 8000, fill: bytes = b"\x10\x20") -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(fill * round(seconds * rate))
    return out.getvalue()


def post(path: str, **kwargs) -> httpx.Response:
    with httpx.Client(base_url=BASE, timeout=60) as c:
        return c.post(path, **kwargs)


def get(path: str) -> httpx.Response:
    with httpx.Client(base_url=BASE, timeout=60) as c:
        return c.get(path)


def burst(n: int, fn) -> list[httpx.Response]:
    gate = threading.Barrier(n)

    def one(i: int) -> httpx.Response:
        gate.wait()
        return fn(i)

    with ThreadPoolExecutor(n) as pool:
        return list(pool.map(one, range(n)))


def tally(responses: list[httpx.Response]) -> str:
    counts = collections.Counter()
    for r in responses:
        code = ""
        if r.status_code >= 400:
            try:
                code = " " + r.json()["error"]["code"]
            except Exception:
                code = " " + r.text[:30]
        counts[f"{r.status_code}{code}"] += 1
    return ", ".join(f"{k} x{v}" for k, v in sorted(counts.items()))


def dialogue_calls(ctl: Path, sid: str) -> int:
    return sum(f"dialogue.next session={sid}" in line for line in (ctl / "calls.log").read_text().splitlines())


def stt_calls(ctl: Path, since: int) -> int:
    return sum(" stt " in line for line in (ctl / "calls.log").read_text().splitlines()[since:])


def lines(ctl: Path) -> int:
    return len((ctl / "calls.log").read_text().splitlines())


def describe(sid: str, state: Path) -> str:
    log = get(f"/api/sessions/{sid}").json()
    disk = json.loads((state / "sessions" / sid / "session.json").read_text())
    kinds = "".join(e["type"][0] for e in log["events"])
    seqs = [e["seq"] for e in log["events"]]
    return (f"events={kinds} seqs_contiguous={seqs == list(range(len(seqs)))} status={log['status']} "
            f"disk_equals_memory={disk == log} bot_texts={[e['text'] for e in log['events'] if e['type'] == 'bot']}")


class DiskWatcher:
    """Parses session.json over and over while a storm runs; counts reads that were not valid JSON."""

    def __init__(self, path: Path) -> None:
        self.path, self.bad, self.reads, self.stop = path, 0, 0, threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self) -> None:
        while not self.stop.is_set():
            try:
                json.loads(self.path.read_text())
                self.reads += 1
            except FileNotFoundError:
                pass
            except ValueError:
                self.bad += 1

    def __enter__(self) -> "DiskWatcher":
        self.thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop.set()
        self.thread.join()


def main() -> None:
    global BASE
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8191)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--ctl", type=Path, required=True)
    args = parser.parse_args()
    BASE = f"http://127.0.0.1:{args.port}"
    state, ctl = args.state, args.ctl
    answer = wav(0.5)

    def new(dialogue: str = "count") -> str:
        return post("/api/sessions", json={"dialogue": dialogue}).json()["session_id"]

    print("A. 10 simultaneous uploads of the same turn, reply_to=0, fake STT takes 0.5 s")
    (ctl / "stt_delay").write_text("0.5")
    sid = new()
    mark = lines(ctl)
    with DiskWatcher(state / "sessions" / sid / "session.json") as watch:
        rs = burst(10, lambda i: post(f"/api/sessions/{sid}/turns?source=mic&reply_to=0", content=answer))
    print("  ", tally(rs))
    print("  ", describe(sid, state))
    print(f"   dialogue.next calls for this session: {dialogue_calls(ctl, sid)} (1 at create + turns); STT calls: {stt_calls(ctl, mark)}; "
          f"session.json parsed {watch.reads} times during the burst, invalid {watch.bad}")
    rs = burst(10, lambda i: post(f"/api/sessions/{sid}/turns?source=mic&reply_to=0", content=answer))
    print("   the same 10 again after the turn completed:", tally(rs), "| distinct bodies:", len({r.text for r in rs}))
    print("  ", describe(sid, state))

    print("B. 10 simultaneous uploads with no reply_to (the API allows it), fake STT 0.5 s")
    sid = new()
    rs = burst(10, lambda i: post(f"/api/sessions/{sid}/turns?source=mic", content=wav(0.5 + i / 100)))
    print("  ", tally(rs))
    print("  ", describe(sid, state), "| dialogue.next calls:", dialogue_calls(ctl, sid))

    print("C. 10 uploads with no reply_to, one after another without waiting for a human (fake STT 0)")
    (ctl / "stt_delay").write_text("0")
    sid = new()
    rs = [post(f"/api/sessions/{sid}/turns?source=mic", content=answer) for _ in range(10)]
    print("  ", tally(rs))
    print("  ", describe(sid, state), "| dialogue.next calls:", dialogue_calls(ctl, sid))

    print("D. 8 simultaneous uploads with no reply_to, fake STT 0 (race on the uploading flag)")
    for attempt in range(3):
        sid = new()
        rs = burst(8, lambda i: post(f"/api/sessions/{sid}/turns?source=mic", content=wav(0.5 + i / 100)))
        print(f"   try {attempt}: {tally(rs)} | dialogue.next calls: {dialogue_calls(ctl, sid)} |", describe(sid, state)[:60])

    print("E. mixed storm on one call: turns (reply_to current), prompt fetches, log reads, recording, then end")
    (ctl / "stt_delay").write_text("0.05")
    sid = new()
    errors: list[str] = []

    def storm(i: int) -> httpx.Response:
        kind = i % 5
        if kind == 0:
            return post(f"/api/sessions/{sid}/turns?source=mic&reply_to=0", content=answer)
        if kind == 1:
            return get(f"/api/sessions/{sid}/audio/bot-000.wav")
        if kind == 2:
            return get(f"/api/sessions/{sid}")
        if kind == 3:
            return get(f"/api/sessions/{sid}/recording.wav")
        return post(f"/api/sessions/{sid}/turns?source=none&reply_to=2")

    with DiskWatcher(state / "sessions" / sid / "session.json") as watch:
        for round_ in range(4):
            rs = burst(25, storm)
            for r in rs:
                if r.status_code >= 500:
                    errors.append(f"{r.status_code} {r.text[:80]}")
            print(f"   round {round_}: {tally(rs)}")
        end = burst(5, lambda i: post(f"/api/sessions/{sid}/end", json={"reason": "hangup"}))
    print("   end x5:", tally(end), "| distinct:", len({r.text for r in end}))
    print("  ", describe(sid, state), f"| dialogue.next calls: {dialogue_calls(ctl, sid)} | invalid disk reads {watch.bad}/{watch.reads + watch.bad} | 5xx: {errors[:3]}")
    rec = get(f"/api/sessions/{sid}/recording.wav").content
    log = get(f"/api/sessions/{sid}").json()
    with wave.open(io.BytesIO(rec)) as f:
        secs = f.getnframes() / f.getframerate()
    last = max((e["rec_end"] or 0) for e in log["events"])
    print(f"   recording {secs:.3f} s; last rec_end {last}; log.recording.seconds {log['recording']['seconds']}")

    print("F. 8 simultaneous first fetches of one prompt (fake TTS 0.3 s)")
    (ctl / "tts_delay").write_text("0.3")
    sid = new()
    mark = lines(ctl)
    rs = burst(8, lambda i: get(f"/api/sessions/{sid}/audio/bot-000.wav"))
    tts = sum(" tts " in line for line in (ctl / "calls.log").read_text().splitlines()[mark:])
    print("  ", tally(rs), "| distinct bodies:", len({r.content for r in rs}), "| TTS calls:", tts)
    (ctl / "tts_delay").write_text("0")

    print("G. 150 simultaneous session creates (the live map holds 64; eviction iterates it in worker threads)")
    rs = burst(150, lambda i: post("/api/sessions", json={"dialogue": "count"}))
    print("  ", tally(rs))
    ids = [r.json()["session_id"] for r in rs if r.status_code == 201]
    print("   distinct ids:", len(set(ids)), "of", len(ids))
    alive = sum(post(f"/api/sessions/{s}/turns?source=none").status_code == 200 for s in ids)
    print(f"   sessions that still take a turn afterwards: {alive} (cap is 64)")

    print("H. an event-loop responsiveness check: GET /api/health while a turn sits in a 2 s fake STT call")
    (ctl / "stt_delay").write_text("2")
    sid = new()
    t0 = time.perf_counter()
    slow = threading.Thread(target=lambda: post(f"/api/sessions/{sid}/turns?source=mic&reply_to=0", content=answer))
    slow.start()
    time.sleep(0.3)
    t = time.perf_counter()
    code = get("/api/health").status_code
    health_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    code_log = get(f"/api/sessions/{sid}").status_code
    log_ms = (time.perf_counter() - t) * 1000
    slow.join()
    print(f"   health {code} in {health_ms:.0f} ms; GET log of the busy call {code_log} in {log_ms:.0f} ms (it waits for the call's lock); turn took {time.perf_counter() - t0:.2f} s")
    (ctl / "stt_delay").write_text("0")

    print("I. idle TCP connections against limit_concurrency=32")
    socks = []
    try:
        for _ in range(40):
            socks.append(socket.create_connection(("127.0.0.1", args.port), timeout=5))
        time.sleep(0.5)
        try:
            r = get("/api/health")
            print(f"   with 40 idle sockets open: GET /api/health -> {r.status_code} {r.text[:60]!r} content-type={r.headers.get('content-type')}")
        except httpx.HTTPError as exc:
            print(f"   with 40 idle sockets open: GET /api/health failed: {type(exc).__name__}")
        time.sleep(8)
        try:
            r = get("/api/health")
            print(f"   8 s later, sockets still open and silent: GET /api/health -> {r.status_code} {r.text[:40]!r}")
        except httpx.HTTPError as exc:
            print(f"   8 s later: failed: {type(exc).__name__}")
    finally:
        for s in socks:
            s.close()
    time.sleep(0.5)
    print("   after closing them:", get("/api/health").status_code)


if __name__ == "__main__":
    main()
