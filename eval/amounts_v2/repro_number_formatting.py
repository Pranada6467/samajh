"""Reproduce Prisma v3.0 `format=transcribe` dropping a skipped zero group from spoken amounts.

Needs Python 3.9+ and nothing else (standard library only). Set the API key and run:

  export GNANI_API_KEY=...        # sent as the X-API-Key-ID header
  python3 repro_number_formatting.py [--keep-audio DIR]

For each sentence it makes one Timbre clip (16 kHz WAV), then sends that same clip three times to
POST /stt/v3: prisma-v3.0 transcribe, prisma-v3.0 verbatim, prisma-v2.5 transcribe. It prints the
amount that was spoken and the digits each transcribe output wrote. About 2.1 credits in all by
our estimates (0.002 per TTS character, 0.010 per STT audio second; 10 clips of about 55
characters, 30 STT requests of about 3.5 s). Requests go one at a time:
the API allows one active request per key and answers a second one with 429 at once.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

BASE_URL = "https://api.vachana.ai"

# (id, Timbre language, Timbre model, voice, amount spoken in rupees, sentence). The ids are items
# of our held-out set (amounts-v2); the voices are the ones that voiced them there. Eight skip a
# group in a way no listener could read differently ("one lakh three hundred" = 1,00,300); two are
# controls that skip none. "X lakh Y" phrases such as "three lakh forty" are left out: in
# colloquial Hindi they can mean X.Y lakh.
SENTENCES = [
    (
        "amt2-hi-skipped-028",
        "hi-IN",
        "timbre-v3.0",
        "Kalpana",
        2012,
        "बैंक वालों ने दो हज़ार बारह रुपये सीधे काट लिए।",
    ),
    (
        "amt2-hi-control-028",
        "hi-IN",
        "timbre-v3.0",
        "Kalpana",
        2300,
        "बैंक वालों ने दो हज़ार तीन सौ रुपये सीधे काट लिए।",
    ),
    ("amt2-hi-skipped-029", "hi-IN", "timbre-v3.0", "Vasudha", 50026000, "हाथ में पाँच करोड़ छब्बीस हज़ार आए।"),
    (
        "amt2-hi-skipped-030",
        "hi-IN",
        "timbre-v3.0",
        "Vasudha",
        10002000,
        "रसीद पर एक करोड़ दो हज़ार रुपये लिखा है।",
    ),
    (
        "amt2-hi-en-skipped-012",
        "hi-en",
        "timbre-v3.0",
        "Devansh",
        400900,
        "उन्होंने बोला था कि premium four lakh nine hundred rupees होगा।",
    ),
    (
        "amt2-hi-en-control-012",
        "hi-en",
        "timbre-v3.0",
        "Devansh",
        409000,
        "उन्होंने बोला था कि premium four lakh nine thousand rupees होगा।",
    ),
    (
        "amt2-hi-en-skipped-013",
        "hi-en",
        "timbre-v3.0",
        "Riyaa",
        100300,
        "bank वालों ने one lakh three hundred rupees सीधे deduct कर लिए।",
    ),
    (
        "amt2-hi-en-skipped-014",
        "hi-en",
        "timbre-v3.0",
        "Vasudha",
        300500,
        "उन्होंने बोला था कि premium three lakh five hundred rupees होगा।",
    ),
    (
        "amt2-hi-en-skipped-022",
        "hi-en",
        "timbre-v2.5",
        "Poorvi",
        14060,
        "loan amount में से fourteen thousand sixty rupees insurance के लिए कट गए।",
    ),
    (
        "amt2-hi-en-skipped-030",
        "hi-en",
        "timbre-v3.0",
        "Riyaa",
        40030000,
        "premium की amount four crore thirty thousand थी।",
    ),
]

STT_REQUESTS = [("prisma-v3.0", "transcribe"), ("prisma-v3.0", "verbatim"), ("prisma-v2.5", "transcribe")]


def post(path: str, body: bytes, content_type: str, key: str, attempts: int = 6) -> tuple[bytes, str]:
    """POST and return (body, content type). Retries 429 and 5xx with backoff."""
    delay = 2.0
    for attempt in range(attempts):
        request = urllib.request.Request(
            BASE_URL + path,
            data=body,
            method="POST",
            headers={"X-API-Key-ID": key, "Content-Type": content_type},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read(), response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as error:
            if (error.code == 429 or error.code >= 500) and attempt < attempts - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise SystemExit(f"{path}: HTTP {error.code}: {error.read()[:300]!r}") from None
    raise AssertionError("unreachable")


def fix_wav_sizes(wav: bytes) -> bytes:
    """Timbre's WAV header carries streaming-style placeholder sizes; write the real ones."""
    if wav[:4] != b"RIFF" or wav[8:12] != b"WAVE":
        return wav
    fixed = bytearray(wav)
    struct.pack_into("<I", fixed, 4, len(wav) - 8)
    offset = 12
    while offset + 8 <= len(wav):
        chunk, size = wav[offset : offset + 4], struct.unpack_from("<I", wav, offset + 4)[0]
        if chunk == b"data":
            struct.pack_into("<I", fixed, offset + 4, len(wav) - offset - 8)
            break
        offset += 8 + size + (size & 1)
    return bytes(fixed)


def tts(text: str, language: str, model: str, voice: str, key: str) -> bytes:
    body = {
        "text": text,
        "voice": voice,
        "model": model,
        "language": language,
        "speed": 1.0,
        "audio_config": {"sample_rate": 16000, "container": "wav"},
    }
    audio, content_type = post("/api/v1/tts/inference", json.dumps(body).encode(), "application/json", key)
    if not content_type.startswith("audio/"):
        raise SystemExit(f"TTS returned {content_type}: {audio[:200]!r}")
    return fix_wav_sizes(audio)


def stt(wav: bytes, model: str, fmt: str, key: str) -> dict:
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in (("model", model), ("language_code", "hi-IN"), ("format", fmt)):
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="audio_file"; filename="audio.wav"\r\n'
        "Content-Type: audio/wav\r\n\r\n".encode()
        + wav
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    body, _ = post("/stt/v3", b"".join(parts), f"multipart/form-data; boundary={boundary}", key)
    return json.loads(body)


def digits(text: str) -> list[int]:
    """Every digit run in the text, commas removed: what a pipeline that trusts the digits reads."""
    return [int(run.replace(",", "")) for run in re.findall(r"\d[\d,]*\d|\d", text)]


def indian(rupees: int) -> str:
    head, tail = str(rupees)[:-3], str(rupees)[-3:]
    groups = []
    while len(head) > 2:
        head, groups = head[:-2], [head[-2:], *groups]
    return ",".join([g for g in [head, *groups] if g] + [tail])


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--keep-audio", type=Path, help="write each Timbre clip here")
    args = parser.parse_args()
    key = os.environ.get("GNANI_API_KEY")
    if not key:
        raise SystemExit("set GNANI_API_KEY")
    wrong = 0
    for item, language, tts_model, voice, rupees, text in SENTENCES:
        wav = tts(text, language, tts_model, voice, key)
        if args.keep_audio:
            args.keep_audio.mkdir(parents=True, exist_ok=True)
            (args.keep_audio / f"{item}.wav").write_bytes(wav)
        print(f"\n{item}  spoken: {indian(rupees)}  ({voice}, {tts_model})")
        for model, fmt in STT_REQUESTS:
            reply = stt(wav, model, fmt, key)
            transcript = reply.get("transcript", "")
            line = f"  {model} {fmt:<10} {transcript}"
            if fmt == "transcribe":
                found = digits(transcript)
                verdict = "ok" if found == [rupees] else f"WRONG (digits {found}, spoken {rupees})"
                wrong += model == "prisma-v3.0" and found != [rupees]
                line += f"   -> {verdict}"
            print(line)
            if model == "prisma-v2.5" and (reply.get("output") or {}).get("literal"):
                print(f"  {'':11} output.literal: {reply['output']['literal']}")
    print(
        f"\nprisma-v3.0 transcribe digits differ from the spoken amount on {wrong} of {len(SENTENCES)} sentences."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
