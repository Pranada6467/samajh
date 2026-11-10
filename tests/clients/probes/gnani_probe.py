"""Raw Gnani API probe. Bypasses the client on purpose (no lock, no cache, no retry) so that it
shows what the server really does. Costs credits. Every call is logged to .samajh/probe/log.jsonl.

  uv run python tests/clients/probes/gnani_probe.py tts OUT.wav TEXT [k=v ...]     (JSON body fields)
  uv run python tests/clients/probes/gnani_probe.py stt FILE.wav [k=v ...]         (multipart fields)
  uv run python tests/clients/probes/gnani_probe.py get PATH
  uv run python tests/clients/probes/gnani_probe.py latency      (20 pilot sentences: 40 TTS + 40 STT)
  uv run python tests/clients/probes/gnani_probe.py batch FILE.wav MODEL [k=v ...]   (config fields)
  uv run --with websockets python tests/clients/probes/gnani_probe.py ws FILE_8k.wav
  uv run python tests/clients/probes/gnani_probe.py burst N tts|stt|mix [FILE.wav]   (N at once)
  uv run python tests/clients/probes/gnani_probe.py json PATH '{"a": 1}'
Options via env: PROBE_STT_PATH (default /stt/v3), PROBE_TTS_PATH (default /api/v1/tts/inference),
PROBE_KEY=bad sends a wrong key.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
BASE = "https://api.vachana.ai"
OUT = ROOT / ".samajh" / "probe"
OUT.mkdir(parents=True, exist_ok=True)
KEY = "not-a-real-key" if os.environ.get("PROBE_KEY") == "bad" else os.environ["GNANI_API_KEY"]
HEADERS = {"X-API-Key-ID": KEY}


def scrub(text: str) -> str:
    return text.replace(os.environ["GNANI_API_KEY"], "<KEY>")


def report(label: str, request: dict, r: httpx.Response, secs: float) -> None:
    ctype = r.headers.get("content-type", "")
    body = scrub(r.text)[:3000] if ("json" in ctype or "text" in ctype) else f"<{len(r.content)} bytes {ctype}>"
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "label": label,
        "request": request,
        "status": r.status_code,
        "secs": round(secs, 3),
        "headers": {k: scrub(v) for k, v in r.headers.items()},
        "body": body,
    }
    with (OUT / "log.jsonl").open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps({k: entry[k] for k in ("label", "status", "secs", "body")}, ensure_ascii=False))
    if os.environ.get("PROBE_HEADERS"):
        print(json.dumps(entry["headers"]))


def kv(args: list[str]) -> dict:
    out: dict = {}
    for a in args:
        k, v = a.split("=", 1)
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v
    return out


BURST_TEXT = "नमस्ते, यह कॉल आपके लोन के बारे में है। कृपया बताइए कि लोन के साथ आपने क्या-क्या लिया और कितने का।"


def burst(n: int, kind: str, wav: Path) -> None:
    """Fire n requests at the same instant on separate connections; print status, timing, body."""
    import threading

    barrier = threading.Barrier(n)
    audio = wav.read_bytes()
    t_start = time.perf_counter()

    def one(i: int) -> None:
        k = kind if kind != "mix" else ("tts" if i % 2 == 0 else "stt")
        with httpx.Client(base_url=BASE, headers=HEADERS, timeout=120) as c:
            barrier.wait()
            t0 = time.perf_counter()
            if k == "tts":
                body = {"text": f"{BURST_TEXT} {i}", "voice": "Shivani", "model": "timbre-v3.0",
                        "language": "hi-IN", "audio_config": {"sample_rate": 8000, "container": "wav"}}
                r = c.post("/api/v1/tts/inference", json=body)
            else:
                r = c.post("/stt/v3", files={"audio_file": (wav.name, audio, "audio/wav")},
                           data={"model": "prisma-v3.0", "language_code": "hi-IN", "format": "transcribe"})
            t1 = time.perf_counter()
            report(f"burst{n}-{kind}-{i}-{k} start={t0 - t_start:.3f} end={t1 - t_start:.3f}", {}, r, t1 - t0)
            extra = {h: v for h, v in r.headers.items() if h.lower() in ("retry-after",) or "ratelimit" in h.lower()}
            if extra:
                print("   headers:", extra)

    threads = [threading.Thread(target=one, args=(i,)) for i in range(n)]
    [t.start() for t in threads]
    [t.join() for t in threads]


def pilot_items() -> list[tuple[str, str, str, int]]:
    import ast

    tree = ast.parse((ROOT / "references/pilots/pilot.py").read_text())
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "ITEMS")
    return ast.literal_eval(node.value)


def latency() -> None:
    """Sequential, one keep-alive connection, wall time per request as the client sees it."""
    import statistics

    times: dict[str, list[float]] = {}
    rows = []
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=120) as c:
        c.post("/api/v1/tts/inference", json={})  # warm the connection; 4xx, not billed
        for item_id, lang, text, _gold in pilot_items():
            for model, voice in (("timbre-v3.0", "Shivani"), ("timbre-v2.5", "Nalini")):
                body = {"text": text, "voice": voice, "model": model, "language": lang,
                        "audio_config": {"sample_rate": 8000, "container": "wav"}}
                t0 = time.perf_counter()
                r = c.post("/api/v1/tts/inference", json=body)
                dt = time.perf_counter() - t0
                report(f"lat-tts-{model}-{item_id}", body, r, dt)
                if r.status_code == 200:
                    times.setdefault(f"tts {model}", []).append(dt)
                    (OUT / f"lat_{item_id}_{model}.wav").write_bytes(r.content)
            wav = OUT / f"lat_{item_id}_timbre-v3.0.wav"
            stt_lang = "hi-IN" if lang == "hi-en" else lang
            for model in ("prisma-v3.0", "prisma-v2.5"):
                data = {"model": model, "language_code": stt_lang, "format": "transcribe"}
                t0 = time.perf_counter()
                r = c.post("/stt/v3", files={"audio_file": (wav.name, wav.read_bytes(), "audio/wav")}, data=data)
                dt = time.perf_counter() - t0
                report(f"lat-stt-{model}-{item_id}", data, r, dt)
                if r.status_code == 200:
                    times.setdefault(f"stt {model}", []).append(dt)
                    rows.append((item_id, model, r.json().get("transcript")))
    for k, v in sorted(times.items()):
        v = sorted(v)
        p95 = v[min(len(v) - 1, round(0.95 * (len(v) - 1)))]
        print(f"LATENCY {k}: n={len(v)} median={statistics.median(v):.3f}s p95={p95:.3f}s min={v[0]:.3f} max={v[-1]:.3f}")


def rest_stt_status(wav: Path) -> str:
    """One plain REST STT call; used to see whether something else holds the active-request slot."""
    r = httpx.post(BASE + "/stt/v3", headers=HEADERS, timeout=60,
                   files={"audio_file": (wav.name, wav.read_bytes(), "audio/wav")},
                   data={"model": "prisma-v3.0", "language_code": "hi-IN", "format": "transcribe"})
    return f"{r.status_code} {scrub(r.text)[:160]}"


def batch(wav: Path, model: str, extra: dict) -> None:
    """Create, start, poll, list files, fetch the transcript. Prints every response."""
    config = {"model": model, "language_code": "hi-IN", **extra}
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=120) as c:
        t0 = time.perf_counter()
        r = c.post("/stt/v3/batch/jobs", data={},
                   files=[("config", (None, json.dumps(config), "application/json")),
                          ("files", (wav.name, wav.read_bytes(), "audio/wav"))])
        report("batch-create", config, r, time.perf_counter() - t0)
        if r.status_code not in (200, 201):
            return
        job = r.json()["job_id"]
        t1 = time.perf_counter()
        r = c.post(f"/stt/v3/batch/jobs/{job}/start")
        report("batch-start", {}, r, time.perf_counter() - t1)
        print("   REST STT right after start:", rest_stt_status(OUT / "p_hi_8k.wav"))
        status = ""
        while status not in ("COMPLETED", "PARTIAL_FAILURE", "FAILED", "START_FAILED", "CANCELLED"):
            time.sleep(10)
            t2 = time.perf_counter()
            r = c.get(f"/stt/v3/batch/jobs/{job}")
            report("batch-poll", {}, r, time.perf_counter() - t2)
            if r.status_code != 200:
                continue
            status = r.json().get("status", "")
            if status in ("QUEUED", "IN_PROGRESS", "STARTING"):
                print("   REST STT while", status, ":", rest_stt_status(OUT / "p_hi_8k.wav"))
            if time.perf_counter() - t0 > 600:
                print("   gave up after 600 s")
                return
        print(f"   job reached {status} after {time.perf_counter() - t0:.1f}s")
        r = c.get(f"/stt/v3/batch/jobs/{job}/files")
        report("batch-files", {}, r, 0)
        for f in r.json().get("data", []):
            if f.get("transcript_url"):
                doc = httpx.get(f["transcript_url"], timeout=60)  # presigned: no API key header
                print("   transcript status", doc.status_code, doc.headers.get("content-type"))
                (OUT / f"batch_{model}_{wav.stem}.json").write_bytes(doc.content)
                print(doc.text[:3000])


def ws(wav: Path) -> None:
    """Open a streaming STT session, send the clip at real-time cadence, and meanwhile try a REST
    call and a second session to see whether streaming holds the one active-request slot."""
    import asyncio

    import websockets

    pcm = wav.read_bytes()[44:]
    headers = {"x-api-key-id": KEY, "model": "prisma-v3.0", "language_code": "hi-IN",
               "x-sample-rate": "8000", "format": "transcribe"}

    async def run() -> None:
        url = "wss://api.vachana.ai/stt/v3/stream"
        t0 = time.perf_counter()
        async with websockets.connect(url, additional_headers=headers) as sock:
            print(f"   open after {time.perf_counter() - t0:.3f}s:", scrub(await sock.recv()))
            print("   REST STT while session open, before audio:",
                  await asyncio.to_thread(rest_stt_status, OUT / "p_hi_8k.wav"))
            frames = [pcm[i:i + 1024] for i in range(0, len(pcm) - 1023, 1024)]
            for i, frame in enumerate(frames):
                await sock.send(frame)
                await asyncio.sleep(0.064)
                if i == len(frames) // 2:
                    print("   REST STT mid-audio:", await asyncio.to_thread(rest_stt_status, OUT / "p_hi_8k.wav"))
                    try:
                        async with websockets.connect(url, additional_headers=headers) as second:
                            print("   second session opened:", scrub(await asyncio.wait_for(second.recv(), 5)))
                    except Exception as exc:  # noqa: BLE001 - probe: report whatever the server does
                        print("   second session refused:", type(exc).__name__, scrub(str(exc))[:300])
            await sock.send(json.dumps({"type": "commit"}))
            try:
                while True:
                    msg = await asyncio.wait_for(sock.recv(), 6)
                    print("   recv:", scrub(msg)[:400])
            except (TimeoutError, websockets.ConnectionClosed) as exc:
                print("   done:", type(exc).__name__)
        print("   REST STT after close:", rest_stt_status(OUT / "p_hi_8k.wav"))

    asyncio.run(run())


def main() -> None:
    mode, *rest = sys.argv[1:]
    if mode == "batch":
        batch(OUT / rest[0], rest[1], kv(rest[2:]))
        return
    if mode == "ws":
        ws(OUT / rest[0])
        return
    if mode == "latency":
        latency()
        return
    if mode == "burst":
        burst(int(rest[0]), rest[1], OUT / (rest[2] if len(rest) > 2 else "p_hi_8k.wav"))
        return
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=120) as c:
        t0 = time.perf_counter()
        if mode == "tts":
            out, text, *fields = rest
            body = {"text": text, "voice": "Shivani", "model": "timbre-v3.0", "language": "hi-IN"}
            extra = kv(fields)
            audio = {k[6:]: extra.pop(k) for k in list(extra) if k.startswith("audio.")}
            body.update(extra)
            if audio:
                body["audio_config"] = audio
            r = c.post(os.environ.get("PROBE_TTS_PATH", "/api/v1/tts/inference"), json=body)
            report("tts", body, r, time.perf_counter() - t0)
            if r.status_code == 200 and "json" not in r.headers.get("content-type", ""):
                (OUT / out).write_bytes(r.content)
        elif mode == "stt":
            path, *fields = rest
            data = {k: (json.dumps(v) if not isinstance(v, str) else v) for k, v in kv(fields).items()}
            fname = os.environ.get("PROBE_FILE_FIELD", "audio_file")
            p = Path(path) if Path(path).exists() else OUT / path
            r = c.post(
                os.environ.get("PROBE_STT_PATH", "/stt/v3"),
                files={fname: (p.name, p.read_bytes(), "audio/wav")},
                data=data,
            )
            report("stt", {"file": p.name, "bytes": p.stat().st_size, **data}, r, time.perf_counter() - t0)
        elif mode == "get":
            r = c.get(rest[0])
            report("get " + rest[0], {}, r, time.perf_counter() - t0)
        elif mode == "json":
            body = json.loads(rest[1]) if len(rest) > 1 else {}
            r = c.post(rest[0], json=body)
            report("post " + rest[0], body, r, time.perf_counter() - t0)
        else:
            raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
