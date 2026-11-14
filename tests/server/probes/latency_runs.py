"""Reply-delay runs of the browser phone: the same calls replayed through the microphone path, so a
"before" and an "after" of latency work can be compared on the phone's own `bot_start_ms`.

    uv run python tests/server/probes/latency_runs.py prepare --calls tests/fixtures/server/calls/hero ... --seed 1 --out DIR
    uv run python tests/server/probes/latency_runs.py run --manifest DIR/manifest.json --url http://127.0.0.1:8085 --label before --out RUNDIR
    uv run python tests/server/probes/latency_runs.py summarise RUNDIR ... [--ledger .samajh/ledger.jsonl]

`prepare` copies each call's turn WAVs as `<call>-s<seed>-NN.wav` with a seeded +-1 LSB change to a
few samples, so the bytes (and the Gnani STT cache key) differ per seed while the audio is the same.
The server must serve DIR as its clips dir (`SAMAJH_CLIPS_DIR=DIR`). `run` drives
tests/server/browser_calls.mjs once per call and saves its JSON and the session log. Standard library only.
"""

from __future__ import annotations

import argparse
import array
import json
import random
import statistics
import subprocess
import sys
import urllib.request
import wave
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DRIVER = REPO / "tests" / "server" / "browser_calls.mjs"
NOTE = "TTS-voiced customer clips (Timbre), not human speech."


# ---- prepare -------------------------------------------------------------------------------


def nudge_wav(src: Path, dst: Path, rng: random.Random, changes: int = 8) -> None:
    with wave.open(str(src), "rb") as f:
        params = f.getparams()
        frames = f.readframes(f.getnframes())
    if params.sampwidth != 2:
        raise SystemExit(f"{src}: only 16-bit PCM is supported")
    pcm = array.array("h", frames)
    if sys.byteorder == "big":
        pcm.byteswap()
    for i in rng.sample(range(len(pcm)), min(changes, len(pcm))):
        step = rng.choice((-1, 1))
        if not -32768 <= pcm[i] + step <= 32767:
            step = -step
        pcm[i] += step
    if sys.byteorder == "big":
        pcm.byteswap()
    with wave.open(str(dst), "wb") as f:
        f.setparams(params)
        f.writeframes(pcm.tobytes())


def prepare(calls: list[Path], seed: int, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    manifest: dict = {"seed": seed, "calls": []}
    for call in calls:
        script = json.loads((call / "call.json").read_text())
        turns, answers = [], []
        for n, turn in enumerate(script["turns"], 1):
            answers.append(turn.get("answers"))
            if not turn.get("file"):
                turns.append("none")
                continue
            name = f"{call.name}-s{seed}-{n:02d}.wav"
            nudge_wav(call / turn["file"], out / name, rng)
            turns.append(name)
        manifest["calls"].append(
            {"call": call.name, "source": str(call), "params": script.get("params", {}),
             "identity": script.get("identity"), "turns": turns, "answers": answers, "seed": seed}
        )
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    return manifest


# ---- run -----------------------------------------------------------------------------------


def phone_query(call: dict) -> str:
    p = call["params"]
    q = {"mode": "hands-free", "autoanswer": "1"}
    if "record" in p:
        q["record"] = p["record"]
    if "loan" in p:
        q["loan"] = p["loan"]
    if "language" in p:
        q["lang"] = p["language"]
    ident = call.get("identity") or {}
    if ident.get("second_check"):
        q["identity"] = ident["second_check"]
    if ident.get("attempts"):
        q["attempts"] = str(ident["attempts"])
    return "&".join(f"{k}={v}" for k, v in q.items())


def now() -> str:
    return datetime.now(UTC).isoformat()


def run(manifest: Path, url: str, label: str, out: Path, gap_ms: int, timeout: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    m = json.loads(manifest.read_text())
    windows = []
    for call in m["calls"]:
        name = f"{call['call']}-s{call['seed']}"
        start = now()
        cmd = ["node", str(DRIVER), "--url", url, "--query", phone_query(call), "--turns", ",".join(call["turns"]),
               "--gap-ms", str(gap_ms), "--timeout", str(timeout), "--out", str(out / f"{name}.phone.json")]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        end = now()
        phone = json.loads((out / f"{name}.phone.json").read_text()) if (out / f"{name}.phone.json").exists() else {}
        sid = phone.get("session_id")
        if sid:
            with urllib.request.urlopen(f"{url.rstrip('/')}/api/sessions/{sid}") as r:
                (out / f"{name}.session.json").write_bytes(r.read())
        windows.append({"call": name, "start": start, "end": end, "session_id": sid, "exit": proc.returncode,
                        "errors": phone.get("errors", [proc.stderr[-500:]])})
        print(f"{name}: exit {proc.returncode}, session {sid}, bot_start_ms {phone.get('bot_start_ms')}", flush=True)
    (out / "run.json").write_text(json.dumps({"label": label, "url": url, "manifest": str(manifest), "calls": windows}, indent=1))


# ---- summarise -----------------------------------------------------------------------------


def stats(xs: list[float]) -> str:
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return "n/a | n/a | n/a | 0"
    p90 = xs[max(0, -(-9 * len(xs) // 10) - 1)]  # nearest rank
    return f"{statistics.median(xs):.0f} | {p90:.0f} | {xs[-1]:.0f} | {len(xs)}"


def table(rows: list[tuple[str, list[float]]], head: str = "cell") -> list[str]:
    lines = [f"| {head} | median ms | p90 ms | max ms | n |", "|---|---|---|---|---|"]
    lines += [f"| {name} | {stats(xs)} |" for name, xs in rows]
    return lines + ["", NOTE, ""]


def summarise_run(rundir: Path, ledger: list[dict]) -> list[str]:
    meta = json.loads((rundir / "run.json").read_text())
    by_cell: dict[str, list[float]] = defaultdict(list)
    parts: dict[str, list[float]] = defaultdict(list)
    lines_made, lines_cached, synth = 0, 0, []
    split, transports, errors, browser_errors = [], Counter(), [], []
    for call in meta["calls"]:
        name = call["call"]
        phone_path, session_path = rundir / f"{name}.phone.json", rundir / f"{name}.session.json"
        if not phone_path.exists() or not session_path.exists():
            errors.append(f"{name}: missing phone or session log")
            continue
        phone, session = json.loads(phone_path.read_text()), json.loads(session_path.read_text())
        browser_errors += [f"{name}: {e}" for e in phone.get("errors", [])]
        events = {e["seq"]: e for e in session["events"]}
        for e in session["events"]:
            if e["type"] == "bot":
                for line in e.get("lines", []):
                    tts = line.get("tts")
                    if tts is None:
                        continue
                    if tts["cache_hit"]:
                        lines_cached += 1
                    else:
                        lines_made += 1
                        synth.append(tts.get("synth_ms"))
            elif e["type"] == "customer":
                if e.get("part", 1) > 1 or e.get("superseded"):
                    split.append(f"{name} seq {e['seq']}: part {e.get('part', 1)}, superseded {e.get('superseded')}")
                for r in e.get("readings", []):
                    transports[f"{r['role']} {r['model']} {r.get('mode', 'rest')} transport={r['params'].get('transport', '-')}"] += 1
                lat = e.get("latency") or {}
                for k in ("stt_ms", "second_stt_ms", "dialogue_ms", "server_ms"):
                    parts[f"server {k}"].append(lat.get(k))
            elif e["type"] == "error":
                errors.append(f"{name} seq {e['seq']}: {e['stage']} {e['status']} {e['code']}")
        for t in phone.get("turns", []):
            lat = t.get("latency", {})
            parts["browser eos_wait_ms"].append(lat.get("eos_wait_ms"))
            parts["browser post_ms"].append(lat.get("post_ms"))
            ms = lat.get("bot_start_ms")
            cust, bot = events.get(t["seq"], {}), events.get(t.get("botSeq"), {})
            asked = events.get(cust.get("reply_to"), {})
            reads = cust.get("readings") or []
            by_cell["all"].append(ms)
            by_cell[f"primary STT cache_hit={reads[0]['cache_hit'] if reads else 'no reading'}"].append(ms)
            made = any(ln.get("tts") and not ln["tts"]["cache_hit"] for ln in bot.get("lines", []))
            by_cell[f"reply synthesised during call={made}"].append(ms)
            by_cell[f"listen kind={asked.get('listen', '?')}"].append(ms)
            by_cell[f"source={t.get('source')}"].append(ms)
    out = [f"## Run `{meta['label']}` ({rundir})", "", "### bot_start_ms (phone: end of speech to first reply sample)", ""]
    out += table(sorted(by_cell.items(), key=lambda kv: (kv[0] != "all", kv[0])))
    out += ["### Parts of the turn", ""] + table(sorted(parts.items()), "part")
    out += ["### Bot lines", "", f"- synthesised during the call: {lines_made}; pre-made or cached: {lines_cached}",
            f"- synth_ms of the synthesised lines: median | p90 | max | n = {stats(synth)}", "", NOTE, ""]
    out += ["### Split utterances", ""] + ([f"- {s}" for s in split] or ["- none"]) + [""]
    out += ["### STT readings by role, model, mode, transport", ""] + [f"- {k}: {v}" for k, v in sorted(transports.items())] + [""]
    out += ["### Errors", ""] + ([f"- {e}" for e in errors + browser_errors] or ["- none"]) + [""]
    out += ["### Ledger rows inside each call's window", "",
            "The ledger (.samajh/ledger.jsonl) is shared with other workers and processes: rows in a window "
            "may not be this run's.", "", "| call | rows by kind/status | est_credits | 429s |", "|---|---|---|---|"]
    for call in meta["calls"]:
        rows = [r for r in ledger if call["start"] <= r.get("ts", "") <= call["end"]]
        kinds = Counter(f"{r.get('kind')}/{r.get('status')}" for r in rows)
        credits = sum(r.get("est_credits") or 0 for r in rows)
        n429 = sum(1 for r in rows if r.get("status") == 429)
        out.append(f"| {call['call']} | {dict(kinds) or '-'} | {credits:.3f} | {n429} |")
    return out + ["", NOTE, ""]


def summarise(rundirs: list[Path], ledger_path: Path) -> str:
    ledger = []
    if ledger_path.exists():
        for line in ledger_path.read_text().splitlines():
            try:
                ledger.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    out: list[str] = []
    for d in rundirs:
        out += summarise_run(d, ledger)
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--calls", nargs="+", type=Path, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    r = sub.add_parser("run")
    r.add_argument("--manifest", type=Path, required=True)
    r.add_argument("--url", required=True)
    r.add_argument("--label", required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--gap-ms", type=int, default=400)
    r.add_argument("--timeout", type=int, default=600)
    s = sub.add_parser("summarise")
    s.add_argument("rundirs", nargs="+", type=Path)
    s.add_argument("--ledger", type=Path, default=REPO / ".samajh" / "ledger.jsonl")
    a = ap.parse_args()
    if a.cmd == "prepare":
        m = prepare(a.calls, a.seed, a.out)
        print(f"{len(m['calls'])} calls, {sum(len(c['turns']) for c in m['calls'])} turns -> {a.out / 'manifest.json'}")
    elif a.cmd == "run":
        run(a.manifest, a.url, a.label, a.out, a.gap_ms, a.timeout)
    else:
        print(summarise(a.rundirs, a.ledger))


if __name__ == "__main__":
    main()
