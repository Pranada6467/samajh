"""Check that every quote in the findings files appears in a saved source.

Run from the repository root:
    python3 -I references/claims/check_quotes.py            # all groups
    python3 -I references/claims/check_quotes.py A E        # chosen groups

For each findings-<group>.md, the script takes every span between straight
double quotes of at least MIN_CHARS characters on a "Quote" line or bullet and
searches for it in the text files saved for that group. The comparison ignores
whitespace, quote marks, dash style, ligatures, letter case and the page
markers added by the PDF extraction, because extraction changes all of them.
A span joined with "..." or "[...]" is checked piece by piece.

Exit status is 1 when a quote is missing, so the check can gate the ledger.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

CLAIMS = Path(__file__).resolve().parent
REPO = CLAIMS.parent.parent
MIN_CHARS = 30
TEXT_SUFFIXES = {".txt", ".md", ".json", ".jsonl", ".html", ".py"}
EXTRA_SOURCES = {"D": [REPO / "references" / "pilots", REPO / "DESIGN.md", REPO / "IDEAS-HILLCLIMB.md"]}
DROPPED = re.compile(r"[\"'“”‘’`*\\\u00ad]|\s+")
DASHES = str.maketrans({"–": "-", "—": "-", "−": "-", "‐": "-", "‑": "-"})
PAGE_MARKER = re.compile(r"=+ page \d+ =+")
SECTION = re.compile(r"^#{2,4} +(\S+)")
END_OF_QUOTES = re.compile(
    r"^- (Notes|Outcome|Facts|Source|Status|Corrected wording|Claim as worded|Pattern|Case)\b"
)


def squash(text: str) -> str:
    text = unicodedata.normalize("NFKC", PAGE_MARKER.sub("", text)).translate(DASHES)
    return DROPPED.sub("", text).lower()


def load_corpus(group: str) -> str:
    roots = [CLAIMS / "sources" / group, *EXTRA_SOURCES.get(group, [])]
    parts = []
    for root in roots:
        files = [root] if root.is_file() else sorted(root.rglob("*"))
        for path in files:
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES and path.name != "INDEX.md":
                parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return squash("\n".join(parts))


def quoted_spans(line: str) -> list[str]:
    segments = line.split('"')
    return [segment for segment in segments[1::2] if len(segment.strip()) >= MIN_CHARS]


def pieces(span: str) -> list[str]:
    parts = re.split(r"\[\.\.\.\]|\.\.\.|…", span)
    return [part for part in parts if len(squash(part)) >= 12]


def check_group(group: str) -> tuple[int, list[tuple[str, int, str]]]:
    findings = CLAIMS / f"findings-{group}.md"
    corpus = load_corpus(group)
    checked = 0
    missing = []
    claim_id = "?"
    in_quotes = False
    for number, line in enumerate(findings.read_text(encoding="utf-8").splitlines(), 1):
        heading = SECTION.match(line)
        if heading:
            claim_id, in_quotes = heading.group(1), False
            continue
        stripped = line.strip()
        if stripped.startswith("- Quote"):
            in_quotes = True
        elif END_OF_QUOTES.match(stripped) or not stripped:
            in_quotes = False
        if not in_quotes:
            continue
        for span in quoted_spans(stripped):
            for piece in pieces(span):
                checked += 1
                if squash(piece) not in corpus:
                    missing.append((claim_id, number, piece.strip()))
    return checked, missing


def main(groups: list[str]) -> int:
    failed = False
    for group in groups or ["A", "B", "C", "D", "E"]:
        if not (CLAIMS / f"findings-{group}.md").exists():
            print(f"group {group}: findings file missing")
            failed = True
            continue
        checked, missing = check_group(group)
        print(f"group {group}: {checked} quoted spans checked, {len(missing)} not found in saved sources")
        for claim_id, number, piece in missing:
            print(f"  {claim_id} (line {number}): {piece[:160]}")
        failed = failed or bool(missing)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
