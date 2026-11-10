"""Reviewer probe: attack a fake-backed Samajh server over real HTTP (never Gnani).

    uv run python references/reviews/iter1/probes/server_attack.py --port 8191 --state <scratch>/state [--only SECTION]

Sections: ids, static, methods, hostorigin, json, upload, audio, after, leaks.
Every response body and header set is scanned for key material (read from .env, compared in
memory, never printed: only counts are reported) and for paths, tracebacks and header names.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import socket
import struct
import sys
import time
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
HOST = "127.0.0.1"
PORT = 8191
NEEDLES: dict[str, bytes] = {}
HITS: dict[str, list[str]] = {}
SEEN = 0


def load_needles() -> None:
    env = REPO / ".env"
    for line in env.read_text().splitlines():
        name, _, value = line.partition("=")
        value = value.strip().strip("'\"")
        if name.strip() in ("GNANI_API_KEY", "OPENROUTER_API_KEY") and len(value) >= 16:
            NEEDLES[f"{name.strip()} (full)"] = value.encode()
            NEEDLES[f"{name.strip()} (first 12)"] = value[:12].encode()
            NEEDLES[f"{name.strip()} (last 12)"] = value[-12:].encode()
    for text in ("X-API-Key-ID", "x-api-key-id", "/Users/", "/private/", "Traceback", "site-packages",
                 ".samajh", "cache_key", "vachana", "openrouter", "File \"", "SECRET-DETAIL", "gnani.lock"):
        NEEDLES[text] = text.encode()


def scan(label: str, blob: bytes) -> None:
    global SEEN
    SEEN += 1
    for name, needle in NEEDLES.items():
        if needle in blob:
            HITS.setdefault(name, []).append(label)


def raw(request: bytes, label: str, wait: float = 5.0, read_all: bool = True) -> tuple[str, dict[str, str], bytes]:
    """Send bytes on a fresh socket; return (status line, headers, body)."""
    with socket.create_connection((HOST, PORT), timeout=wait) as s:
        try:
            s.sendall(request)
        except OSError:
            pass
        s.settimeout(wait)
        data = b""
        try:
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                data += chunk
                head, sep, body = data.partition(b"\r\n\r\n")
                if sep:
                    length = None
                    for line in head.split(b"\r\n")[1:]:
                        k, _, v = line.partition(b":")
                        if k.strip().lower() == b"content-length":
                            length = int(v.strip())
                    if length is not None and len(body) >= length:
                        break
        except (TimeoutError, OSError):
            pass
    scan(label, data)
    head, _, body = data.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    headers = {}
    for line in lines[1:]:
        k, _, v = line.partition(":")
        headers[k.strip().lower()] = v.strip()
    return lines[0] if lines else "", headers, body


def req(method: str, path: str, *, headers: dict[str, str] | None = None, body: bytes | None = None,
        host: str | None = f"{HOST}:{PORT}", label: str | None = None, wait: float = 30.0,
        chunked: bool = False) -> tuple[int, dict[str, str], bytes]:
    lines = [f"{method} {path} HTTP/1.1"]
    if host is not None:
        lines.append(f"Host: {host}")
    hdrs = {"Connection": "close"} | (headers or {})
    payload = b""
    if body is not None:
        if chunked:
            hdrs["Transfer-Encoding"] = "chunked"
            step = 65536
            payload = b"".join(
                f"{len(body[i:i + step]):x}\r\n".encode() + body[i : i + step] + b"\r\n" for i in range(0, len(body), step)
            ) + b"0\r\n\r\n"
        else:
            hdrs.setdefault("Content-Length", str(len(body)))
            payload = body
    lines += [f"{k}: {v}" for k, v in hdrs.items()]
    status, rh, rb = raw("\r\n".join(lines).encode("latin-1") + b"\r\n\r\n" + payload, label or f"{method} {path[:80]}", wait)
    code = int(status.split()[1]) if len(status.split()) > 1 and status.split()[1].isdigit() else 0
    return code, rh, rb


def err(body: bytes) -> str:
    try:
        e = json.loads(body)["error"]
        return f"{e['code']}: {e['message'][:110]}"
    except Exception:
        return repr(body[:90])


def show(label: str, code: int, body: bytes, extra: str = "") -> None:
    print(f"  {code}  {label:<58} {err(body) if code >= 400 or code == 0 else 'ok ' + str(len(body)) + ' bytes'} {extra}")


def new_session(**body: object) -> dict:
    code, _, rb = req("POST", "/api/sessions", body=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    assert code == 201, (code, rb)
    return json.loads(rb)


def wav_bytes(seconds: float = 0.5, rate: int = 8000, channels: int = 1, bits: int = 16, *, tag: int = 1,
              block_align: int | None = None, byte_rate: int | None = None, declared: int | None = None,
              riff_declared: int | None = None, frames: int | None = None, pre: bytes = b"", post: bytes = b"",
              fmt_extra: bytes = b"") -> bytes:
    n = frames if frames is not None else round(seconds * rate)
    width = bits // 8
    if bits == 16:
        one = b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 220 * i / rate))) for i in range(min(n, rate)))
        pcm = b"".join(one[i : i + 2] * channels for i in range(0, len(one), 2))
        pcm = (pcm * (n // max(1, min(n, rate)) + 1))[: n * channels * width] if n else b""
    else:
        pcm = (bytes(range(256)) * (n * channels * width // 256 + 1))[: n * channels * width]
    ba = block_align if block_align is not None else channels * width
    br = (byte_rate if byte_rate is not None else rate * channels * width) & 0xFFFFFFFF
    fmt = struct.pack("<HHIIHH", tag, channels, rate, br, ba, bits) + fmt_extra
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + pre
    body += b"data" + struct.pack("<I", len(pcm) if declared is None else declared) + pcm + post
    return b"RIFF" + struct.pack("<I", len(body) if riff_declared is None else riff_declared) + body


def stdlib_wav(seconds: float, rate: int = 8000, channels: int = 1) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(b"\x10\x20" * round(seconds * rate) * channels)
    return out.getvalue()


# ---------------------------------------------------------------------------------------------


def section_ids(state: Path) -> None:
    print("== ids and traversal (raw sockets, no client-side normalisation)")
    a = new_session()
    b = new_session()
    sid, other = a["session_id"], b["session_id"]
    req("GET", a["bot"]["audio_url"])
    code, _, _ = req("POST", f"/api/sessions/{sid}/turns?source=file", body=stdlib_wav(0.5))
    planted = state.parent / "review-secret.wav"
    planted.write_bytes(b"REVIEW-PLANTED-SECRET")
    NEEDLES["planted file"] = b"REVIEW-PLANTED-SECRET"
    ids = [
        "..", "../..", "%2e%2e", "..%2f..%2f..%2freview-secret.wav", "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "/etc/passwd", "%2fetc%2fpasswd", "..%5c..%5cetc", f"{sid}%00", f"{sid}%0a", f"{sid}/", f"{sid}%2f..",
        f"..%2f{sid}", f"{sid}%2f..%2f{other}", sid.upper(), sid + "0", sid[:-1], " " + sid, "%ff%fe",
        "20261110T142233-000000000000", "x" * 300, "x" * 9000, "A" * 70000, "*", "null", "undefined", "",
    ]
    for bad in ids:
        for method, tail in (("GET", ""), ("GET", "/recording.wav"), ("GET", "/audio/bot-000.wav"),
                             ("POST", "/turns?source=none"), ("POST", "/end")):
            code, rh, rb = req(method, f"/api/sessions/{bad}{tail}", label=f"sid {bad[:40]!r}{tail}")
            interesting = code not in (404, 405) or b"session_id" in rb or b"RIFF" in rb
            if interesting or tail == "":
                show(f"{method} sessions/{bad[:44]}{tail}"[:58], code, rb, "<-- LOOK" if interesting and code < 400 else "")
    print("  -- audio names within a valid session")
    names = [
        "session.json", "..%2fsession.json", "%2e%2e%2fsession.json", "..%2f..%2f..%2freview-secret.wav", "../session.json",
        "call.wav", "..%2fcall.wav", "bot-000.wav%00", "bot-000.wav%00.json", "bot-000.wav/", "bot-000.wav%2f..%2f..%2fsession.json",
        "customer-001.wav", "customer-003.wav", "bot-002.wav", "bot-004.wav", "bot-0.wav", "bot-0000.wav", "bot--01.wav",
        "bot-٠٠٠.wav".encode().hex(), "bot-%D9%A0%D9%A0%D9%A0.wav", "BOT-000.WAV", "bot-000.wav.tmp", "/etc/passwd",
        "%2fetc%2fpasswd", "x" * 5000,
    ]
    for name in names:
        code, rh, rb = req("GET", f"/api/sessions/{sid}/audio/{name}", label=f"audio {name[:40]!r}")
        show(f"GET audio/{name[:46]}", code, rb, "<-- served" if code == 200 else "")
    print("  -- another session's audio through this session's id")
    code, _, rb = req("GET", f"/api/sessions/{other}/audio/customer-001.wav")
    show("GET other-session/audio/customer-001.wav", code, rb)
    code, _, rb = req("GET", f"/api/sessions/{other}/audio/bot-000.wav")
    show("GET other-session/audio/bot-000.wav (its own prompt)", code, rb)
    print("  -- clips")
    for name in ["..%2f..%2f..%2f..%2f.env", "%2e%2e%2f.env", "../../../../.env", ".env", "01-loan-amount.wav%00", "01-loan-amount.wav/..", "/etc/passwd", "x" * 5000 + ".wav"]:
        code, _, rb = req("GET", f"/api/clips/{name}", label=f"clip {name[:40]!r}")
        show(f"GET clips/{name[:46]}", code, rb, "<-- served" if code == 200 else "")
    code, _, rb = req("GET", "/api/clips")
    print("  clips listed:", rb.decode()[:300])
    print("  sessions dir entries:", sorted(p.name for p in (state / "sessions").iterdir())[-3:], "count", len(list((state / "sessions").iterdir())))
    print("  state parent entries:", sorted(p.name for p in state.parent.iterdir()))
    planted.unlink()


def section_static() -> None:
    print("== static mount (web/ is one level under the repo root, where .env lives)")
    paths = ["/", "/index.html", "/phone.js", "/api.js", "/vad.js", "/wav.js", "/capture-worklet.js", "/phone.css",
             "/.env", "/../.env", "/..%2f.env", "/%2e%2e/.env", "/%2e%2e%2f.env", "/..%5c.env", "//.env", "/./../.env",
             "/phone.js/../../.env", "/....//.env", "/%2e%2e/%2e%2e/etc/passwd", "/..%252f.env", "/../CLAUDE.md",
             "/..%2fCLAUDE.md", "/..%2fsamajh/server/app.py", "/..%2f.samajh/ledger.jsonl", "/%2e%2e/pyproject.toml",
             "/api", "/api/", "/api/sessions", "/api/sessions/", "/docs", "/openapi.json", "/redoc", "/favicon.ico"]
    for path in paths:
        code, rh, rb = req("GET", path, label=f"static {path}")
        print(f"  {code}  GET {path:<34} {rh.get('content-type', ''):<28} {len(rb)} bytes  {err(rb) if code >= 400 else ''}")
    for name in ("index.html", "phone.js", "api.js", "vad.js", "wav.js", "capture-worklet.js", "phone.css"):
        code, rh, rb = req("GET", f"/{name}")
        same = rb == (REPO / "web" / name).read_bytes()
        print(f"  asset {name}: {code}, identical to web/{name}: {same}, headers: " +
              ", ".join(f"{k}={v}" for k, v in rh.items() if k not in ("date", "content-length", "etag", "last-modified")))


def section_methods() -> None:
    print("== unknown routes, methods, preflight")
    sid = new_session()["session_id"]
    cases = [
        ("GET", "/api/nope", {}), ("DELETE", "/api/health", {}), ("PUT", f"/api/sessions/{sid}", {}),
        ("DELETE", f"/api/sessions/{sid}", {}), ("PATCH", f"/api/sessions/{sid}", {}), ("GET", f"/api/sessions/{sid}/turns", {}),
        ("GET", f"/api/sessions/{sid}/end", {}), ("POST", f"/api/sessions/{sid}/recording.wav", {}), ("HEAD", "/api/health", {}),
        ("HEAD", "/", {}), ("TRACE", "/api/health", {}), ("CONNECT", "/api/health", {}), ("FOO", "/api/health", {}),
        ("OPTIONS", "/api/sessions", {}),
        ("OPTIONS", "/api/sessions", {"Origin": "http://evil.example", "Access-Control-Request-Method": "POST",
                                      "Access-Control-Request-Headers": "content-type"}),
        ("OPTIONS", "/api/sessions", {"Origin": f"http://{HOST}:{PORT}", "Access-Control-Request-Method": "POST"}),
        ("GET", "/api/health", {"Origin": f"http://{HOST}:{PORT}"}),
        ("POST", "/", {}), ("POST", "/index.html", {}),
    ]
    for method, path, headers in cases:
        code, rh, rb = req(method, path, headers=headers)
        cors = {k: v for k, v in rh.items() if k.startswith("access-control") or k in ("allow", "vary")}
        print(f"  {code}  {method:<7} {path[:44]:<44} {('origin=' + headers['Origin']) if 'Origin' in headers else '':<30} {err(rb) if code >= 400 else 'ok'}  {cors or ''}")
    print("  -- malformed request lines")
    for label, blob in [
        ("no Host, HTTP/1.1", b"GET /api/health HTTP/1.1\r\n\r\n"),
        ("no Host, HTTP/1.0", b"GET /api/health HTTP/1.0\r\n\r\n"),
        ("two Host headers (local, evil)", f"GET /api/health HTTP/1.1\r\nHost: {HOST}:{PORT}\r\nHost: evil.example\r\n\r\n".encode()),
        ("two Host headers (evil, local)", f"GET /api/health HTTP/1.1\r\nHost: evil.example\r\nHost: {HOST}:{PORT}\r\n\r\n".encode()),
        ("absolute-form target to evil host", f"GET http://evil.example/api/health HTTP/1.1\r\nHost: {HOST}:{PORT}\r\nConnection: close\r\n\r\n".encode()),
        ("NUL in path", f"GET /api/sessions/a\x00b HTTP/1.1\r\nHost: {HOST}:{PORT}\r\nConnection: close\r\n\r\n".encode()),
        ("70 kB header", f"GET /api/health HTTP/1.1\r\nHost: {HOST}:{PORT}\r\nX-Pad: {'a' * 70000}\r\n\r\n".encode()),
        ("garbage", b"\x16\x03\x01\x02\x00\x01\x00\x01\xfc\x03\x03" + b"\x00" * 64),
    ]:
        status, rh, rb = raw(blob, label)
        print(f"  {status or '(no reply)':<28} {label:<36} {rb[:80]!r}")


def section_hostorigin() -> None:
    print("== Host and Origin guard")
    sid = new_session()["session_id"]
    local = f"{HOST}:{PORT}"
    hosts = ["evil.example", f"evil.example:{PORT}", f"127.0.0.1.evil.example:{PORT}", f"localhost.evil.example:{PORT}",
             f"evil.example:80@127.0.0.1:{PORT}", f"127.0.0.1:{PORT}@evil.example", f"127.0.0.1:{PORT}, evil.example",
             f"localhost:{PORT}, evil.example", f"127.0.0.1 evil.example", f"127.0.0.1:{PORT}/evil.example",
             "127.0.0.1.", "localhost.", "LOCALHOST", f"localhost:{PORT}", f"[::1]:{PORT}", "[::1]", "::1", "0.0.0.0",
             f"0.0.0.0:{PORT}", "127.1", "2130706433", "", " ", f"127.0.0.1:{PORT}\tevil", "testserver", "[::ffff:127.0.0.1]"]
    for host in hosts:
        for method, path, body in (("GET", "/api/health", None), ("POST", "/api/sessions", b"{}"), ("GET", f"/api/sessions/{sid}", None), ("GET", "/", None)):
            code, _, rb = req(method, path, host=host, body=body, label=f"host {host!r} {path}")
            if method == "GET" and path == "/api/health":
                line = f"  Host: {host!r:<42} health={code}"
            else:
                line += f" {method[0]}{path.split('/')[-1][:8] or '/'}={code}"
        print(line, "<-- ADMITTED" if "=20" in line else "")
    origins = ["http://evil.example", "https://evil.example", "null", f"http://{HOST}:9999", f"http://localhost:{PORT}",
               f"http://{local}", f"https://{local}", f"http://{local}.evil.example", f"http://evil.example@{local}",
               f"http://{local}@evil.example", f"http://{local}/", f"HTTP://{local.upper()}", f"//{local}", local,
               f"file://{local}", f"chrome-extension://{local}", f"evil://{local}", "", " ", f"http://{local} http://evil.example",
               f"http://evil.example, http://{local}"]
    for origin in origins:
        line = f"  Origin: {origin!r:<48}"
        for method, path, body in (("GET", "/api/health", None), ("POST", "/api/sessions", b"{}"), ("GET", f"/api/sessions/{sid}", None),
                                   ("GET", f"/api/sessions/{sid}/recording.wav", None), ("POST", f"/api/sessions/{sid}/turns?source=none", None)):
            code, _, rb = req(method, path, headers={"Origin": origin}, body=body)
            line += f" {method[0]}{path.split('?')[0].split('/')[-1][:9]}={code}"
        print(line, "<-- ADMITTED" if "=20" in line else "")
    print("  -- no Origin header at all (what a cross-site <img>/<audio>/navigation GET looks like)")
    for method, path, extra in (("GET", "/api/health", {}), ("GET", f"/api/sessions/{sid}", {}),
                                ("GET", f"/api/sessions/{sid}/audio/bot-000.wav", {"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "no-cors", "Sec-Fetch-Dest": "audio", "Referer": "http://evil.example/"}),
                                ("GET", f"/api/sessions/{sid}/recording.wav", {"Sec-Fetch-Site": "cross-site", "Referer": "http://evil.example/"}),
                                ("POST", "/api/sessions", {"Sec-Fetch-Site": "cross-site", "Referer": "http://evil.example/", "Content-Type": "text/plain"})):
        code, rh, rb = req(method, path, headers=extra, body=b"{}" if method == "POST" else None)
        print(f"  {code}  {method} {path[:60]:<60} {extra.get('Sec-Fetch-Site', '')} corp={rh.get('cross-origin-resource-policy')} nosniff={rh.get('x-content-type-options')}")


def section_json() -> None:
    print("== create-session bodies and content types")
    cases = [
        ("no content-type, {}", {}, b"{}"), ("text/plain, {}", {"Content-Type": "text/plain"}, b"{}"),
        ("multipart content-type, {}", {"Content-Type": "multipart/form-data; boundary=x"}, b"{}"),
        ("form-encoded body", {"Content-Type": "application/x-www-form-urlencoded"}, b"dialogue=stub"),
        ("empty body", {}, b""), ("invalid utf-8", {}, b"\xff\xfe{}"), ("NaN", {}, b'{"line_rate": NaN}'),
        ("deep nesting", {}, b"[" * 8000 + b"]" * 8000), ("huge number", {}, b'{"line_rate": 1' + b"0" * 5000 + b"}"),
        ("path in dialogue", {}, b'{"dialogue": "../../etc/passwd"}'), ("dialogue __class__", {}, b'{"dialogue": "__class__"}'),
        ("params with path", {}, b'{"params": {"scenario": "../../../etc/passwd"}}'),
        ("params value 15 kB", {}, b'{"params": {"k": "' + b"x" * 15000 + b'"}}'),
        ("16385 bytes", {}, b'{"params": {"k": "' + b"x" * 16400 + b'"}}'),
        ("duplicate keys", {}, b'{"line_rate": 8000, "line_rate": 16000}'),
        ("line_rate string", {}, b'{"line_rate": "8000"}'), ("stt_model v2", {}, b'{"stt_model": "prisma-v2.0"}'),
        ("extra key (key name reflected?)", {}, b'{"<script>alert(1)</script>": 1}'),
    ]
    for label, headers, body in cases:
        code, rh, rb = req("POST", "/api/sessions", headers=headers, body=body)
        show(label, code, rb, rb.decode()[:80] if code == 201 else "")


def section_upload(state: Path) -> None:
    print("== upload size and framing")
    sid = new_session(dialogue="count")["session_id"]
    turn = f"/api/sessions/{sid}/turns?source=mic"
    limit = 6 * 1024 * 1024
    for label, body, kwargs in [
        ("exactly 6 MiB of zeros, Content-Length", b"\0" * limit, {}),
        ("6 MiB + 1, Content-Length", b"\0" * (limit + 1), {}),
        ("6 MiB + 1, chunked", b"\0" * (limit + 1), {"chunked": True}),
        ("exactly 6 MiB, chunked", b"\0" * limit, {"chunked": True}),
        ("64 MiB, Content-Length", b"\0" * (64 * 1024 * 1024), {}),
        ("64 MiB, chunked", b"\0" * (64 * 1024 * 1024), {"chunked": True}),
    ]:
        t = time.perf_counter()
        code, rh, rb = req("POST", turn, body=body, label=label, wait=60, **kwargs)
        show(label, code, rb, f"[{time.perf_counter() - t:.2f} s]")
    print("  -- Content-Length that lies")
    good = stdlib_wav(0.5)
    t = time.perf_counter()
    code, rh, rb = req("POST", turn, body=good + b"\0" * 1000, headers={"Content-Length": str(len(good))}, label="CL smaller than body")
    show("CL = WAV length, 1000 extra bytes follow", code, rb, f"[{time.perf_counter() - t:.2f} s]")
    for label, cl in [("CL: -1", "-1"), ("CL: abc", "abc"), ("CL: 1e3", "1e3"), ("CL: 99999999999999999999", "99999999999999999999"),
                      ("CL: +44", "+44"), ("two CLs", None)]:
        if cl is None:
            blob = f"POST {turn} HTTP/1.1\r\nHost: {HOST}:{PORT}\r\nContent-Length: 5\r\nContent-Length: 50000000\r\nConnection: close\r\n\r\nhello".encode()
        else:
            blob = f"POST {turn} HTTP/1.1\r\nHost: {HOST}:{PORT}\r\nContent-Length: {cl}\r\nConnection: close\r\n\r\nhello".encode()
        status, rh, rb = raw(blob, label, wait=6)
        print(f"  {status or '(no reply in 6 s)':<26} {label:<28} {err(rb) if rb else ''}")
    code, _, rb = req("POST", turn, body=good, headers={"Transfer-Encoding": "chunked", "Content-Length": str(len(good))}, label="TE+CL")
    show("Transfer-Encoding and Content-Length together", code, rb)
    print("  -- content types (a valid 0.5 s WAV each time)")
    for ctype in (None, "audio/wav", "text/plain", "application/json", "multipart/form-data; boundary=x", "application/x-www-form-urlencoded", "audio/webm"):
        code, _, rb = req("POST", f"/api/sessions/{sid}/turns?source=file", body=stdlib_wav(0.5), headers={"Content-Type": ctype} if ctype else {})
        show(f"Content-Type: {ctype}", code, rb)
    print("  -- source=none with a body; source=mic with no body")
    code, _, rb = req("POST", f"/api/sessions/{sid}/turns?source=none", body=b"\0" * (limit + 5))
    show("source=none with a 6 MiB+5 body", code, rb)
    code, _, rb = req("POST", turn)
    show("source=mic, no body", code, rb)
    log = json.loads(req("GET", f"/api/sessions/{sid}")[2])
    print("  events after this section:", [(e["type"], e.get("code")) for e in log["events"]][:40])
    size = (state / "sessions" / sid / "session.json").stat().st_size
    print(f"  session.json size {size} bytes, audio files {len(list((state / 'sessions' / sid / 'audio').glob('*')))}")


def section_audio(state: Path) -> None:
    print("== malformed and unusual audio (dialogue 'count' never ends the call)")
    sessions = {8000: new_session(dialogue="count")["session_id"], 16000: new_session(dialogue="count", line_rate=16000)["session_id"]}
    ext_pcm = struct.pack("<HHI", 22, 16, 4) + bytes.fromhex("0100000000001000800000aa00389b71")
    ext_adpcm = struct.pack("<HHI", 22, 16, 4) + bytes.fromhex("0200000000001000800000aa00389b71")
    ext_mp3 = struct.pack("<HHI", 22, 16, 4) + bytes.fromhex("5500000000001000800000aa00389b71")
    ext_alaw = struct.pack("<HHI", 22, 8, 4) + bytes.fromhex("0600000000001000800000aa00389b71")
    ok = stdlib_wav(1.0)
    two_fmt = (b"WAVE" + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, 4000, 8000, 2, 16)
               + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, 8000, 16000, 2, 16) + b"data" + struct.pack("<I", 16000 * 20) + b"\x10\x20" * 8000 * 20)
    two_fmt = b"RIFF" + struct.pack("<I", len(two_fmt)) + two_fmt
    cases: list[tuple[str, bytes, int]] = [
        ("empty body", b"", 8000),
        ("plain text", b"hello, I am not audio\n" * 10, 8000),
        ("text with a RIFF....WAVE prefix", b"RIFF\x24\x00\x00\x00WAVE" + b"this is text pretending to be a wav file " * 4, 8000),
        ("first 20 bytes of a WAV", ok[:20], 8000),
        ("first 43 bytes of a WAV", ok[:43], 8000),
        ("header only (44 bytes, no samples)", ok[:44], 8000),
        ("header + 1 byte", ok[:45], 8000),
        ("canonical, data size 0xFFFFFFFF (streaming header)", wav_bytes(1.0, declared=0xFFFFFFFF, riff_declared=0xFFFFFFFF), 8000),
        ("canonical, data size 0 with samples after", wav_bytes(1.0, declared=0), 8000),
        ("canonical, data size says 0.1 s, 60 s of samples follow", wav_bytes(60.0, declared=1600), 8000),
        ("244-byte WAV declaring 100 MHz", wav_bytes(frames=100, rate=100_000_000), 8000),
        ("declares 0xFFFFFFFF Hz", wav_bytes(frames=100, rate=0xFFFFFFFF), 8000),
        ("declares 65535 channels", wav_bytes(frames=10, channels=1, block_align=2)[:22] + struct.pack("<H", 65535) + wav_bytes(frames=10)[24:], 8000),
        ("rate 0", wav_bytes(frames=100, rate=1)[:24] + struct.pack("<I", 0) + wav_bytes(frames=100, rate=1)[28:], 8000),
        ("fmt chunk size 0xFFFFFFF0", b"RIFF\xff\xff\xff\xffWAVEfmt \xf0\xff\xff\xff" + b"\0" * 64, 8000),
        ("ID3/MP3 bytes", b"ID3\x04\x00\x00\x00\x00\x00\x0f" + b"\xff\xfb\x90\x00" * 400, 8000),
        ("OggS bytes", b"OggS\x00\x02" + b"\0" * 400, 8000),
        ("WebM/EBML bytes (what MediaRecorder would send)", b"\x1a\x45\xdf\xa3" + b"\x42\x82\x84webm" * 50, 8000),
        ("FLAC bytes", b"fLaC\x00\x00\x00\x22" + b"\0" * 400, 8000),
        ("RF64 header", b"RF64" + ok[4:], 8000),
        ("RIFX (big-endian) header", b"RIFX" + ok[4:], 8000),
        ("AIFF bytes", b"FORM\x00\x00\x01\x00AIFF" + b"\0" * 300, 8000),
        ("tag 2 (MS ADPCM) in a WAV", wav_bytes(1.0, tag=2), 8000),
        ("tag 6 (A-law) 8-bit in a WAV", wav_bytes(1.0, bits=8, tag=6), 8000),
        ("tag 7 (mu-law) 8-bit in a WAV", wav_bytes(1.0, bits=8, tag=7), 8000),
        ("tag 0x55 (MP3) in a WAV", wav_bytes(1.0, tag=0x55), 8000),
        ("tag 0x11 (IMA ADPCM)", wav_bytes(1.0, tag=0x11), 8000),
        ("tag 0xFFFE extensible, PCM subformat, 48 kHz", wav_bytes(1.0, rate=48000, tag=0xFFFE, fmt_extra=ext_pcm), 8000),
        ("tag 0xFFFE extensible, ADPCM subformat", wav_bytes(1.0, rate=48000, tag=0xFFFE, fmt_extra=ext_adpcm), 8000),
        ("tag 0xFFFE extensible, MP3 subformat", wav_bytes(1.0, rate=48000, tag=0xFFFE, fmt_extra=ext_mp3), 8000),
        ("tag 0xFFFE extensible, A-law subformat", wav_bytes(1.0, rate=8000, bits=8, tag=0xFFFE, fmt_extra=ext_alaw), 8000),
        ("tag 3 float32 48 kHz", wav_bytes(1.0, rate=48000, bits=32, tag=3), 8000),
        ("8-bit PCM 8 kHz", wav_bytes(1.0, bits=8), 8000),
        ("24-bit PCM 48 kHz", wav_bytes(1.0, rate=48000, bits=24), 8000),
        ("30.000 s at 8 kHz (240000 frames)", stdlib_wav(30.0), 8000),
        ("30.000125 s at 8 kHz (240001 frames)", wav_bytes(frames=240001), 8000),
        ("31 s at 8 kHz", stdlib_wav(31.0), 8000),
        ("180 s at 8 kHz (2.9 MB)", stdlib_wav(180.0), 8000),
        ("30.0 s at 48 kHz stereo (5.76 MB)", stdlib_wav(30.0, 48000, 2), 8000),
        ("30.02 s at 48 kHz stereo", stdlib_wav(30.02, 48000, 2), 8000),
        ("6.29 MB of 4 kHz 8-bit mono = 26 min declared", wav_bytes(frames=6_290_000, rate=4000, bits=8), 8000),
        ("0.100 s (800 frames)", stdlib_wav(0.1), 8000),
        ("0.099875 s (799 frames)", wav_bytes(frames=799), 8000),
        ("0.1 s at 48 kHz (resampled)", stdlib_wav(0.1, 48000), 8000),
        ("0 samples at 48 kHz", wav_bytes(frames=0, rate=48000), 8000),
        ("44.1 kHz mono 1 s", stdlib_wav(1.0, 44100), 8000),
        ("11.025 kHz mono 1 s", stdlib_wav(1.0, 11025), 8000),
        ("3999 Hz", stdlib_wav(1.0, 3999), 8000),
        ("4000 Hz", stdlib_wav(1.0, 4000), 8000),
        ("192000 Hz", stdlib_wav(1.0, 192000), 8000),
        ("192001 Hz", stdlib_wav(1.0, 192001), 8000),
        ("16 kHz mono onto an 8 kHz line", stdlib_wav(1.0, 16000), 8000),
        ("8 kHz mono onto a 16 kHz line", stdlib_wav(1.0, 8000), 16000),
        ("16 kHz mono onto a 16 kHz line (canonical)", stdlib_wav(1.0, 16000), 16000),
        ("8 kHz stereo 1 s", stdlib_wav(1.0, 8000, 2), 8000),
        ("8 channels 48 kHz", stdlib_wav(1.0, 48000, 8), 8000),
        ("9 channels 48 kHz", stdlib_wav(1.0, 48000, 9), 8000),
        ("canonical fields but block_align=1 (finding 4)", wav_bytes(1.0, block_align=1), 8000),
        ("canonical fields but block_align=2000", wav_bytes(1.0, block_align=2000), 8000),
        ("60 s, block_align=4 (reads as 30 s by block count)", wav_bytes(60.0, block_align=4), 8000),
        ("canonical but byte_rate=1 (not pinned)", wav_bytes(1.0, byte_rate=1), 8000),
        ("canonical 30 s but byte_rate=1600000", wav_bytes(30.0, byte_rate=1_600_000), 8000),
        ("two fmt chunks: 4 kHz then 8 kHz, 20 s of 8 kHz samples", two_fmt, 8000),
        ("canonical with 18-byte fmt (cbSize=0)", wav_bytes(1.0, fmt_extra=b"\0\0"), 8000),
        ("canonical with a 2 MB junk chunk before data", wav_bytes(1.0, pre=b"JUNK" + struct.pack("<I", 2_000_000) + b"\0" * 2_000_000), 8000),
        ("canonical with a LIST chunk after data", wav_bytes(1.0, post=b"LIST" + struct.pack("<I", 4) + b"INFO"), 8000),
        ("canonical, odd number of data bytes", wav_bytes(1.0)[:-1], 8000),
    ]
    for label, body, line in cases:
        sid = sessions[line]
        t = time.perf_counter()
        code, _, rb = req("POST", f"/api/sessions/{sid}/turns?source=file", body=body, label=label, wait=60)
        took = time.perf_counter() - t
        if code == 200:
            c = json.loads(rb)["customer"]
            stored = (state / "sessions" / sid / "audio" / c["audio_url"].rsplit("/", 1)[1]).read_bytes()
            with wave.open(io.BytesIO(stored)) as f:
                shape = (f.getnchannels(), f.getsampwidth(), f.getframerate(), round(f.getnframes() / f.getframerate(), 4))
            same = "bytes kept" if stored == body else f"rewritten ({len(body)} -> {len(stored)} bytes)"
            print(f"  200  {label:<58} logged {c['audio_seconds']} s; stored {shape}; {same} [{took:.2f} s]")
        else:
            show(label, code, rb, f"[{took:.2f} s]")
    for line, sid in sessions.items():
        log = json.loads(req("GET", f"/api/sessions/{sid}")[2])
        kinds = [e["type"] for e in log["events"]]
        print(f"  line {line}: {kinds.count('customer')} customer, {kinds.count('error')} error, {kinds.count('bot')} bot events; seqs contiguous: {[e['seq'] for e in log['events']] == list(range(len(kinds)))}")


def section_after() -> None:
    print("== after the call has ended")
    created = new_session()
    sid = created["session_id"]
    bot = created["bot"]
    for _ in range(3):
        req("GET", bot["audio_url"])
        code, _, rb = req("POST", f"/api/sessions/{sid}/turns?source=file&reply_to={bot['seq']}", body=stdlib_wav(0.5 + 0.1 * bot["seq"]))
        bot = json.loads(rb)["bot"]
    print("  call ended by dialogue:", json.loads(rb)["ended"])
    for label, method, path, body in [
        ("turn with no reply_to", "POST", f"/api/sessions/{sid}/turns?source=file", stdlib_wav(0.5)),
        ("turn source=none", "POST", f"/api/sessions/{sid}/turns?source=none", None),
        ("turn reply_to=6 (the closing prompt)", "POST", f"/api/sessions/{sid}/turns?source=file&reply_to=6", stdlib_wav(0.5)),
        ("turn reply_to=4 again (stored reply)", "POST", f"/api/sessions/{sid}/turns?source=file&reply_to=4", b"anything at all"),
        ("turn reply_to=4 again, source=none", "POST", f"/api/sessions/{sid}/turns?source=none&reply_to=4", None),
        ("turn reply_to=5 (a customer seq)", "POST", f"/api/sessions/{sid}/turns?source=none&reply_to=5", None),
        ("turn reply_to=999", "POST", f"/api/sessions/{sid}/turns?source=none&reply_to=999", None),
        ("turn reply_to=0007", "POST", f"/api/sessions/{sid}/turns?source=none&reply_to=0007", None),
        ("turn reply_to=-1", "POST", f"/api/sessions/{sid}/turns?source=none&reply_to=-1", None),
        ("closing prompt audio after end (first fetch = TTS)", "GET", bot["audio_url"], None),
        ("end", "POST", f"/api/sessions/{sid}/end", b'{"reason":"hangup"}'),
        ("end again", "POST", f"/api/sessions/{sid}/end", b""),
        ("log", "GET", f"/api/sessions/{sid}", None),
        ("recording", "GET", f"/api/sessions/{sid}/recording.wav", None),
    ]:
        code, _, rb = req(method, path, body=body)
        extra = ""
        if code == 200 and method == "POST" and b"customer" in rb:
            extra = f"customer seq {json.loads(rb)['customer']['seq']} bot seq {json.loads(rb)['bot']['seq']}"
        elif code == 200 and path.endswith("/end"):
            extra = rb.decode()
        show(label, code, rb, extra)
    log = json.loads(req("GET", f"/api/sessions/{sid}")[2])
    print("  events:", [(e["seq"], e["type"]) for e in log["events"]], log["status"], log["ended_reason"])
    print("  -- hang-up then fetch an unspoken prompt, then turn")
    created = new_session()
    sid = created["session_id"]
    code, _, rb = req("POST", f"/api/sessions/{sid}/turns?source=file&reply_to=0", body=stdlib_wav(0.5))
    nxt = json.loads(rb)["bot"]
    req("POST", f"/api/sessions/{sid}/end", body=b"{}")
    for label, method, path, body in [("unspoken prompt after hang-up", "GET", nxt["audio_url"], None),
                                      ("first prompt (never fetched) after hang-up", "GET", created["bot"]["audio_url"], None),
                                      ("turn after hang-up", "POST", f"/api/sessions/{sid}/turns?source=none", None),
                                      ("turn reply_to=0 after hang-up (stored reply)", "POST", f"/api/sessions/{sid}/turns?source=none&reply_to=0", None),
                                      ("turn reply_to=2 after hang-up", "POST", f"/api/sessions/{sid}/turns?source=none&reply_to=2", None)]:
        code, _, rb = req(method, path, body=body)
        show(label, code, rb)


def section_leaks(state: Path) -> None:
    print("== error bodies: what a failing dialogue, STT and TTS expose")
    ctl = state.parent / "ctl"
    sid = new_session(dialogue="count", params={"boom": "1"})["session_id"]
    code, _, rb = req("POST", f"/api/sessions/{sid}/turns?source=file", body=stdlib_wav(0.5))
    print(f"  dialogue raising RuntimeError('SECRET-DETAIL /Users/secret/path token=abc123'): {code} {rb.decode()}")
    (ctl / "stt_error").write_text("1")
    code, _, rb = req("POST", f"/api/sessions/{sid}/turns?source=file", body=stdlib_wav(0.5))
    (ctl / "stt_error").unlink()
    print(f"  fake STT ServerError: {code} {rb.decode()}")
    (ctl / "tts_error").write_text("1")
    code, _, rb = req("GET", f"/api/sessions/{sid}/audio/bot-000.wav")
    (ctl / "tts_error").unlink()
    print(f"  fake TTS ServerError: {code} {rb.decode()}")
    code, _, rb = req("GET", f"/api/sessions/{sid}")
    print("  session log contains SECRET-DETAIL:", b"SECRET-DETAIL" in rb, "| events:", [(e["type"], e.get("code"), e.get("message")) for e in json.loads(rb)["events"]])
    print("  -- recording when an audio file has gone missing on disk")
    created = new_session()
    sid = created["session_id"]
    req("GET", created["bot"]["audio_url"])
    (state / "sessions" / sid / "audio" / "bot-000.wav").unlink()
    code, _, rb = req("GET", f"/api/sessions/{sid}/recording.wav")
    print(f"  recording.wav: {code} {rb.decode()[:200]}")
    code, _, rb = req("GET", created["bot"]["audio_url"])
    print(f"  that audio: {code} {rb.decode()[:200]}")
    code, _, rb = req("POST", f"/api/sessions/{sid}/end", body=b"{}")
    print(f"  end (must assemble the recording): {code} {rb.decode()[:200]}")
    code, _, rb = req("GET", f"/api/sessions/{sid}")
    print(f"  log status afterwards: {json.loads(rb)['status'] if code == 200 else code}")
    print("  -- session.json corrupted on disk, session still live in memory / unknown to memory")
    created = new_session()
    sid = created["session_id"]
    (state / "sessions" / sid / "session.json").write_text("{not json")
    code, _, rb = req("GET", f"/api/sessions/{sid}")
    print(f"  live session, corrupt file: GET log {code} (served from memory: {b'events' in rb})")


SECTIONS = {
    "ids": section_ids, "static": section_static, "methods": section_methods, "hostorigin": section_hostorigin,
    "json": section_json, "upload": section_upload, "audio": section_audio, "after": section_after, "leaks": section_leaks,
}


def main() -> int:
    global PORT
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8191)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--only", action="append")
    args = parser.parse_args()
    PORT = args.port
    load_needles()
    print(f"key needles loaded: {sum('(full)' in k for k in NEEDLES)} keys (values never printed)")
    for name, fn in SECTIONS.items():
        if args.only and name not in args.only:
            continue
        if name in ("ids", "upload", "audio", "leaks"):
            fn(args.state)
        else:
            fn()
        sys.stdout.flush()
    print(f"== scan of {SEEN} raw responses (status line, headers and body) for sensitive strings")
    for name in NEEDLES:
        found = HITS.get(name, [])
        print(f"  {name:<32} {len(found)} responses" + (f"  e.g. {sorted(set(found))[:4]}" if found else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
