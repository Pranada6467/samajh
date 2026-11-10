"""Reviewer probe: mutation testing of tests/server in a SCRATCH COPY of the repo.

    python references/reviews/iter1/probes/server_mutate.py <scratch copy of the repo> <real repo (for the uv environment)>

Refuses to run on the real repo. Each mutation is applied to the copy, `pytest tests/server -q`
runs in the copy with PYTHONPATH pointing at the copy, and the file is restored.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

COPY, REAL = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
assert COPY != REAL and REAL not in COPY.parents and "scratchpad" in str(COPY), "mutations go in the scratch copy only"
assert not (COPY / ".env").exists() and not (COPY / ".git").exists()

# (name, behaviour, file, before, after)
MUTATIONS = [
    ("M1a host guard off", "requests for another Host are refused",
     "samajh/server/app.py", "            if name not in self.hosts:", "            if False:"),
    ("M1b origin guard off", "requests from a foreign Origin are refused",
     "samajh/server/app.py", "            elif origin is not None and urlsplit(origin.decode(\"latin-1\")).netloc.lower() != host:",
     "            elif False:"),
    ("M1c origin guard only on POST", "GET requests from a foreign Origin are refused too",
     "samajh/server/app.py", "            elif origin is not None and urlsplit(",
     "            elif scope[\"method\"] != \"GET\" and origin is not None and urlsplit("),
    ("M1d origin compared without the port", "an Origin on another port of this host is refused",
     "samajh/server/app.py", "urlsplit(origin.decode(\"latin-1\")).netloc.lower() != host:",
     "(urlsplit(origin.decode(\"latin-1\")).hostname or \"\").lower() != name:"),
    ("M2a streamed size limit off", "a body over 6 MiB with no Content-Length is refused",
     "samajh/server/app.py", "        if size > limit:\n            return None", "        if False:\n            return None"),
    ("M2b declared size limit off", "a body over 6 MiB is refused from its Content-Length, before it is read",
     "samajh/server/app.py", "    if declared.isdigit() and int(declared) > limit:\n        return None", "    if False:\n        return None"),
    ("M2c 30 s limit is 300 s", "a turn longer than 30 s is refused",
     "samajh/server/audio.py", "MAX_TURN_SECONDS = 30.0  # Prisma REST limit, inclusive", "MAX_TURN_SECONDS = 300.0"),
    ("M2d 30 s limit exclusive -> 30.0 s refused", "exactly 30.0 s is accepted",
     "samajh/server/audio.py", "    if seconds > MAX_TURN_SECONDS:", "    if seconds >= MAX_TURN_SECONDS:"),
    ("M2e upload deadline off", "a turn body must arrive within 20 s",
     "samajh/server/app.py", "                    with anyio.fail_after(UPLOAD_SECONDS):", "                    with anyio.fail_after(None):"),
    ("M3a session id pattern off in the store", "a malformed session id never becomes a path",
     "samajh/server/sessionlog.py", "        if not SESSION_ID.fullmatch(session_id):\n            raise ValueError(\"malformed session id\")",
     "        if False:\n            raise ValueError(\"malformed session id\")"),
    ("M3b session id pattern off in load()", "a malformed session id loads nothing",
     "samajh/server/sessionlog.py", "        if not SESSION_ID.fullmatch(session_id):\n            return None", "        if False:\n            return None"),
    ("M3c audio served without a log reference", "audio is served only by a name the log refers to",
     "samajh/server/app.py", "        if any(e.audio == f\"audio/{name}\" for e in log.events):", "        if True:"),
    ("M3d audio name pattern off in the route", "an audio name that is not bot-NNN.wav / customer-NNN.wav is 404",
     "samajh/server/app.py", "        if not AUDIO_NAME.fullmatch(name):\n            raise _not_found(\"audio\")", "        if False:\n            raise _not_found(\"audio\")"),
    ("M4a one-upload-per-call guard off", "a second simultaneous turn on a call gets 409 turn_in_progress",
     "samajh/server/app.py", "        if live.uploading:\n            raise ApiProblem(409", "        if False:\n            raise ApiProblem(409"),
    ("M4b reply_to ignored", "a turn sent again gets the stored reply and does not advance the dialogue",
     "samajh/server/app.py", "            if reply_to != prompts[-1]:", "            if False:"),
    ("M4c session lock off for turns", "turns on one call run one at a time",
     "samajh/server/app.py",
     "            async with live.lock:\n                return await anyio.to_thread.run_sync(\n                    calls.turn, live, source, body, eos_wait_ms, received, reply_to\n                )",
     "            if True:\n                return await anyio.to_thread.run_sync(\n                    calls.turn, live, source, body, eos_wait_ms, received, reply_to\n                )"),
    ("M4d failed STT still advances", "a failed step does not advance the dialogue",
     "samajh/server/app.py", "        except Exception as exc:\n            raise self._fail(live, exc, stage, **audio) from exc\n        latency = TurnLatency(",
     "        except Exception as exc:\n            self._fail(live, exc, stage, **audio)\n            seq = len(log.events)\n            bot = self._ask(live, heard)\n            dialogue_ms = 0.0\n        latency = TurnLatency("),
    ("M5a resample to 16 kHz whatever the line", "an upload is resampled to the session's line rate",
     "samajh/server/audio.py", "\"-ar\", str(line_rate), \"-c:a\"", "\"-ar\", \"16000\", \"-c:a\""),
    ("M5b no downmix to mono", "an upload is stored mono",
     "samajh/server/audio.py", "\"-vn\", \"-ac\", \"1\", \"-ar\"", "\"-vn\", \"-ar\""),
    ("M5c header check before ffmpeg off", "an absurd declared rate is refused before ffmpeg runs",
     "samajh/server/audio.py", "        or not MIN_SOURCE_RATE <= fmt.rate <= MAX_SOURCE_RATE\n", "        or False\n"),
    ("M5d codec whitelist off", "only PCM decoders may run",
     "samajh/server/audio.py", "\"-f\", \"wav\", \"-codec_whitelist\", _PCM_DECODERS, \"-i\", \"pipe:0\",", "\"-f\", \"wav\", \"-i\", \"pipe:0\","),
    ("M5e ffmpeg slots 2 -> 1000", "at most two ffmpeg processes at once",
     "samajh/server/audio.py", "_ffmpeg_slots = threading.BoundedSemaphore(2)", "_ffmpeg_slots = threading.BoundedSemaphore(1000)"),
    ("M5f block_align not pinned", "a canonical pass-through pins block_align (finding 4)",
     "samajh/server/audio.py",
     "    if fmt is None or (fmt.tag, fmt.channels, fmt.rate, fmt.block_align, fmt.bits) != (\n        1,\n        1,\n        line_rate,\n        2,\n        16,\n    ):",
     "    if fmt is None or (fmt.tag, fmt.channels, fmt.rate, fmt.bits) != (\n        1,\n        1,\n        line_rate,\n        16,\n    ):"),
    ("M6a prompt synthesised after a hang-up", "nothing is spoken after a hang-up",
     "samajh/server/app.py", "        if live is None or live.log.ended_reason == \"hangup\":", "        if live is None:"),
    ("M6b earlier run's prompt synthesised", "only the server run that owns a call may synthesise its prompts",
     "samajh/server/app.py", "        if live is None or live.log.ended_reason == \"hangup\":\n            raise _not_active()\n        return self._speak(live, unspoken[0], name)",
     "        if live is not None and live.log.ended_reason == \"hangup\":\n            raise _not_active()\n        return self._speak(live or _Live(log, None), unspoken[0], name)"),
    ("M7a STT language fixed to hi-IN", "the reply is transcribed in the language of the prompt it answers",
     "samajh/server/app.py", "                options = stt_options(log.stt, asked.language)", "                options = stt_options(log.stt, \"hi-IN\")"),
    ("M7b dialogue error text reaches the phone", "a dialogue exception is reported by class name only",
     "samajh/server/errors.py", "    return ApiProblem(500, stage, code, type(exc).__name__)", "    return ApiProblem(500, stage, code, str(exc))"),
    ("M7c lock path reaches the phone", "the key-lock timeout message carries no path",
     "samajh/server/errors.py", "(LockTimeout, 503, \"gnani_busy\", True, \"another Gnani request is holding the key; try again\"),",
     "(LockTimeout, 503, \"gnani_busy\", True, None),"),
    ("M8a error audio enters the recording", "a failed attempt's audio stays out of the recording",
     "samajh/server/sessionlog.py", "            if isinstance(event, ErrorEvent) or event.audio is None:\n                continue\n            data = self.read_audio(",
     "            if event.audio is None:\n                continue\n            data = self.read_audio("),
    ("M8b recording gap 0.5 s -> 0", "the recording has 0.5 s of silence between events",
     "samajh/server/sessionlog.py", "        gap = b\"\\0\\0\" * round(RECORDING_GAP_SECONDS * log.line_rate)", "        gap = b\"\""),
    ("M9a limit_concurrency removed", "uvicorn refuses past 32 open requests",
     "samajh/server/__main__.py", "uvicorn.run(app, host=args.host, port=args.port, limit_concurrency=32)", "uvicorn.run(app, host=args.host, port=args.port)"),
    ("M9b --allow-host admits every host", "--allow-host adds one name; other hosts stay refused",
     "samajh/server/__main__.py", "allowed_hosts=(*LOCAL_HOSTS, *args.allow_host)", "allowed_hosts=(*LOCAL_HOSTS, *args.allow_host, \"evil.example\")"),
    ("M9c replay does not end a failed call", "replay hangs up a call whose turn failed (finding 11)",
     "samajh/server/replay.py", "            http.post(f\"{session}/end\", json={\"reason\": \"hangup\"})\n        answer", "            pass\n        answer"),
    ("M9d replay sends no reply_to", "replay names the prompt it answers",
     "samajh/server/replay.py", "params={\"source\": source, \"reply_to\": bot[\"seq\"]}", "params={\"source\": source}"),
]


def run_tests() -> tuple[str, list[str]]:
    env = {
        "PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "PYTHONPATH": str(COPY), "GNANI_API_KEY": "",
        "OPENROUTER_API_KEY": "", "SAMAJH_STATE_DIR": str(COPY.parent / "state"), "PYTHONDONTWRITEBYTECODE": "1",
    }
    done = subprocess.run(
        ["uv", "run", "--no-sync", "--project", str(REAL), "python", "-m", "pytest", "tests/server", "-q", "-p", "no:cacheprovider",
         "--tb=no"],
        cwd=COPY, env=env, capture_output=True, text=True, timeout=900, check=False,
    )
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    failed = [line.split(" - ")[0].removeprefix("FAILED ").removeprefix("ERROR ") for line in lines if line.startswith(("FAILED", "ERROR"))]
    return (lines[-1] if lines else done.stderr[-200:]), failed


def main() -> None:
    only = set(sys.argv[3:])
    check = subprocess.run(
        ["uv", "run", "--no-sync", "--project", str(REAL), "python", "-c", "import samajh.server.app as a; print(a.__file__)"],
        cwd=COPY, env={"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "PYTHONPATH": str(COPY), "GNANI_API_KEY": ""},
        capture_output=True, text=True, check=False,
    )
    print("imported module:", check.stdout.strip())
    assert check.stdout.strip().startswith(str(COPY)), "the copy is not what is imported"
    if not only:
        print("baseline:", run_tests()[0])
    for name, behaviour, rel, before, after in MUTATIONS:
        if only and name.split()[0] not in only:
            continue
        path = COPY / rel
        original = path.read_text()
        if original.count(before) != 1:
            print(f"{name}: SKIPPED, pattern found {original.count(before)} times")
            continue
        path.write_text(original.replace(before, after))
        try:
            summary, failed = run_tests()
        except subprocess.TimeoutExpired:
            summary, failed = "TIMED OUT after 900 s", ["(timeout)"]
        finally:
            path.write_text(original)
        verdict = "KILLED" if failed or "failed" in summary or "error" in summary.lower() else "SURVIVED"
        print(f"{name} | {behaviour} | {rel} | {verdict} | {summary.strip('= ')} | {', '.join(f.split('::')[-1] for f in failed[:4])}{' ...' if len(failed) > 4 else ''}")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
