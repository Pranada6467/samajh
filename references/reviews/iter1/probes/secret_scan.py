"""Verifier probe: look for either API key anywhere outside .env. Prints file names and counts only,
never a key or part of one.

    uv run python references/reviews/iter1/probes/secret_scan.py

Scans the working tree, .samajh (cache, ledger, session logs, probe output), tool caches, and the
git object store read as files (loose objects inflated; pack files searched for every zlib stream,
which finds a key held in a full object or in a delta's inserted bytes; no git command is run).
Needles per key: the whole key, its first 16 and last 16 characters, its base64 and its URL-quoted form.
"""

import base64
import os
import urllib.parse
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def keys() -> dict[str, str]:
    found = {}
    for line in (ROOT / ".env").read_text().splitlines():
        name, _, value = line.partition("=")
        value = value.strip().strip("'\"")
        if name.strip() in ("GNANI_API_KEY", "OPENROUTER_API_KEY") and value:
            found[name.strip()] = value
    return found


def needles(key: str) -> list[bytes]:
    raw = key.encode()
    out = {raw, base64.b64encode(raw), urllib.parse.quote(key, safe="").encode()}
    if len(raw) >= 24:
        out |= {raw[:16], raw[-16:]}
    return [n for n in out if len(n) >= 12]


def main() -> None:
    secret = keys()
    print("keys present in .env:", sorted(secret), "lengths:", {k: len(v) for k, v in secret.items()})
    wanted = {name: needles(value) for name, value in secret.items()}
    hits: list[tuple[str, str]] = []
    scanned = scanned_bytes = 0

    def check(label: str, data: bytes) -> None:
        for name, group in wanted.items():
            if any(n in data for n in group):
                hits.append((name, label))

    skip_dirs = {".venv", "node_modules"}
    for directory, subdirs, files in os.walk(ROOT):
        subdirs[:] = [d for d in subdirs if d not in skip_dirs and not (d == ".git" and directory == str(ROOT))]
        for name in files:
            path = Path(directory) / name
            if path == ROOT / ".env" or path.is_symlink():
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            scanned += 1
            scanned_bytes += len(data)
            check(str(path.relative_to(ROOT)), data)
    print(f"working tree and .samajh: {scanned} files, {scanned_bytes / 1e6:.0f} MB")

    git = ROOT / ".git"
    loose = packs = streams = 0
    for path in git.rglob("*"):
        if not path.is_file():
            continue
        data = path.read_bytes()
        check(f".git/{path.relative_to(git)} (raw)", data)
        if path.parent.parent.name == "objects" and len(path.parent.name) == 2:
            loose += 1
            try:
                check(f".git/{path.relative_to(git)} (inflated)", zlib.decompress(data))
            except zlib.error:
                pass
        elif path.suffix == ".pack":
            packs += 1
            at = 0
            while True:
                at = data.find(b"\x78", at)
                if at < 0:
                    break
                if data[at + 1 : at + 2] in (b"\x01", b"\x5e", b"\x9c", b"\xda"):
                    try:
                        inflater = zlib.decompressobj()
                        check(f".git/{path.relative_to(git)} (stream at {at})", inflater.decompress(data[at:]))
                        streams += 1
                    except zlib.error:
                        pass
                at += 1
    print(f"git object store: {loose} loose objects inflated, {packs} pack files, {streams} zlib streams inflated")
    if hits:
        for name, label in sorted(set(hits)):
            print(f"HIT {name}: {label}")
    print(f"hits: {len(set(hits))}")


if __name__ == "__main__":
    main()
