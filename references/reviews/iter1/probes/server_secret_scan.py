"""Reviewer probe: does anything the server sends, or anything written to disk, hold key material?

    uv run python references/reviews/iter1/probes/server_secret_scan.py --port 8191 --scratch-state <scratch>/state

The keys are read from .env into memory and compared there. Only counts and file names are
printed, never a key or any part of one. Read-only on the repo.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[4]


def needles() -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for line in (REPO / ".env").read_text().splitlines():
        name, _, value = line.partition("=")
        name, value = name.strip(), value.strip().strip("'\"")
        if name in ("GNANI_API_KEY", "OPENROUTER_API_KEY") and len(value) >= 16:
            raw = value.encode()
            out[f"{name} full"] = raw
            out[f"{name} first16"] = raw[:16]
            out[f"{name} last16"] = raw[-16:]
            out[f"{name} base64"] = base64.b64encode(raw)
            out[f"{name} sha256hex"] = hashlib.sha256(raw).hexdigest().encode()
            out[f"{name} hex"] = raw.hex().encode()
    return out


def scan_tree(label: str, root: Path, keys: dict[str, bytes]) -> None:
    files = [p for p in root.rglob("*") if p.is_file()] if root.is_dir() else []
    hits: dict[str, list[str]] = {}
    total = 0
    for path in files:
        try:
            blob = path.read_bytes()
        except OSError:
            continue
        total += len(blob)
        for name, needle in keys.items():
            if needle in blob:
                hits.setdefault(name, []).append(str(path.relative_to(root)))
    print(f"  {label:<44} {len(files):>5} files {total / 1e6:>8.2f} MB  hits: {({k: len(v) for k, v in hits.items()} or 'none')}"
          + (f"  files: {sorted({f for v in hits.values() for f in v})[:5]}" if hits else ""))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8191)
    parser.add_argument("--scratch-state", type=Path, required=True)
    args = parser.parse_args()
    keys = needles()
    print(f"needles: {len(keys)} derived from {sum(k.endswith(' full') for k in keys)} keys in .env (never printed)")
    words = {w: w.encode() for w in ("X-API-Key-ID", "x-api-key-id", "Authorization", "Bearer ", "/Users/", "/private/tmp",
                                     "cache_key", "api.vachana.ai", "openrouter", "GNANI_API_KEY", "OPENROUTER", ".env", "Traceback")}

    print("1. every response of one full stub call, plus the page and its assets")
    seen: list[tuple[str, bytes]] = []
    with httpx.Client(base_url=f"http://127.0.0.1:{args.port}", timeout=30) as http:
        def grab(method: str, url: str, **kw) -> httpx.Response:
            r = http.request(method, url, **kw)
            head = f"{r.status_code}\n" + "\n".join(f"{k}: {v}" for k, v in r.headers.items())
            seen.append((f"{method} {url.split('?')[0]}", head.encode() + b"\n\n" + r.content))
            return r

        page = grab("GET", "/").text
        assets = sorted(set(re.findall(r'(?:src|href)="([^"#]+)"', page)))
        print("   assets referenced by index.html:", assets)
        for name in [*assets, "/api.js", "/vad.js", "/wav.js", "/capture-worklet.js", "/phone.css", "/phone.js"]:
            if not name.startswith("http"):
                grab("GET", "/" + name.lstrip("./"))
        external = [a for a in assets if a.startswith(("http", "//"))]
        print("   external URLs in index.html:", external or "none")
        grab("GET", "/api/health")
        clips = grab("GET", "/api/clips").json()["clips"]
        for c in clips:
            grab("GET", f"/api/clips/{c['name']}")
        created = grab("POST", "/api/sessions", json={"dialogue": "stub", "line_rate": 8000, "stt_model": "prisma-v3.0"}).json()
        sid, bot = created["session_id"], created["bot"]
        for c in clips:
            grab("GET", bot["audio_url"])
            wav = http.get(f"/api/clips/{c['name']}").content
            turn = grab("POST", f"/api/sessions/{sid}/turns?source=file&reply_to={bot['seq']}", content=wav).json()
            grab("GET", turn["customer"]["audio_url"])
            bot = turn["bot"]
            if turn["ended"]:
                break
        grab("GET", bot["audio_url"])
        grab("POST", f"/api/sessions/{sid}/end", json={"reason": "hangup"})
        log = grab("GET", f"/api/sessions/{sid}")
        grab("GET", f"/api/sessions/{sid}/recording.wav")
    print(f"   {len(seen)} responses captured, {sum(len(b) for _, b in seen)} bytes; session {sid}")
    for name, needle in {**keys, **words}.items():
        where = sorted({label for label, blob in seen if needle in blob})
        if where or name in keys:
            print(f"   {name:<32} in {len(where)} responses {where[:6] if where else ''}")
    print("   keys of the session log JSON:", sorted(log.json()))
    event_keys = sorted({k for e in log.json()["events"] for k in e})
    print("   keys of its events:", event_keys)
    stt = next(e["stt"] for e in log.json()["events"] if e["type"] == "customer")
    tts = next(e["tts"] for e in log.json()["events"] if e["type"] == "bot")
    print("   stt object:", json.dumps(stt, ensure_ascii=False))
    print("   tts object:", json.dumps(tts, ensure_ascii=False))
    print("   response header names seen:", sorted({line.split(":")[0].lower() for _, blob in seen for line in blob.split(b"\n\n")[0].decode("latin-1").split("\n")[1:]}))

    print("2. files on disk")
    scan_tree("scratch state (this review's sessions)", args.scratch_state, keys)
    for rel in (".samajh/sessions", ".samajh/w7", "samajh/server", "web", "tests/server", "tests/fixtures/server", "references/pilots",
                "references/reviews", ".samajh"):
        scan_tree(f"repo {rel}", REPO / rel, keys)
    sessions = REPO / ".samajh" / "sessions"
    if sessions.is_dir():
        dirs = [p for p in sessions.iterdir() if p.is_dir()]
        states = {}
        for d in dirs:
            try:
                s = json.loads((d / "session.json").read_text())
                states[(s["status"], s["ended_reason"])] = states.get((s["status"], s["ended_reason"]), 0) + 1
            except (OSError, ValueError):
                states["unreadable"] = states.get("unreadable", 0) + 1
        print(f"   repo .samajh/sessions: {len(dirs)} session dirs; status counts {states}")
        bad = [d.name for d in dirs if not re.fullmatch(r"\d{8}T\d{6}-[0-9a-f]{12}", d.name)]
        print(f"   names not matching the id pattern: {bad or 'none'}")


if __name__ == "__main__":
    main()
