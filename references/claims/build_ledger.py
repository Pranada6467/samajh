"""Regenerate the per-claim tables in claims-ledger.md from the findings files.

Run from the repository root:
    python3 -I references/claims/build_ledger.py

The findings files are the source of truth. This script rewrites only the text
between the GENERATED markers in claims-ledger.md, so the hand-written sections
of the ledger survive a rerun. Running it twice gives the same file.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

CLAIMS = Path(__file__).resolve().parent
LEDGER = CLAIMS / "claims-ledger.md"
START, END = "<!-- GENERATED:START -->", "<!-- GENERATED:END -->"
GROUPS = {
    "A": "The RBI directions",
    "B": "Ombudsman and consumer cases",
    "C": "Supporting practice and evidence",
    "D": "Statements in DESIGN.md sections 11 and 12, and measured numbers",
    "E": "Rules for an automated, recorded, AI-voiced outbound call",
    "F": "Identity on an outbound call (package P8)",
}
STATUSES = ("secondary-only", "unverifiable", "verified", "wrong")
CLAIM_ID = re.compile(r"^#{3,4} +((?:A\d+|B\d+b?|B-N\d+|C\d\.\d+|D\d\.\d+[ab]?|E\d\.\d+|F\d\.\d+))\b\s*(.*)$")
FIELD = re.compile(r"^- ([A-Z][A-Za-z /]{2,24}?)(?: \(.*?\))?:\s*(.*)$")
QUOTE_LIMIT = 420
NOT_A_DESIGN_CLAIM = re.compile(r"^(not in DESIGN\.md|requested|n/a)\b", re.IGNORECASE)
SHORT_NAMES = {
    "A": {
        "CB": "`sources/A/rbi-page-rbi-2026-27-115-commercial-banks-rbc-second-amendment.txt`",
        "NBFC": "`sources/A/rbi-page-rbi-2026-27-123-nbfc-rbc-second-amendment.txt`",
        "HFC": "`sources/A/rbi-page-rbi-2026-27-124-hfc-second-amendment.txt`",
    }
}


def parse(group: str) -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    field = None
    for line in (CLAIMS / f"findings-{group}.md").read_text(encoding="utf-8").splitlines():
        heading = CLAIM_ID.match(line)
        if heading:
            current = {"id": heading.group(1), "title": heading.group(2).strip()}
            claims.append(current)
            field = None
            continue
        if line.startswith("#"):
            current, field = None, None
            continue
        if current is None:
            continue
        match = FIELD.match(line)
        if match:
            field = match.group(1).strip()
            joiner = " / " if field in current else ""
            current[field] = current.get(field, "") + joiner + match.group(2).strip()
        elif field and line.strip():
            current[field] += " " + line.strip().lstrip(">").strip()
    return claims


def split_status(raw: str) -> tuple[str, str]:
    positions = [(raw.find(status), status) for status in STATUSES if status in raw]
    if not positions:
        return "", raw
    status = min(positions)[1]
    qualifier = raw.replace(status, "", 1).strip(" ,;.:")
    if qualifier.startswith("(") and qualifier.endswith(")") and qualifier.count("(") == 1:
        qualifier = qualifier[1:-1]
    return status, qualifier


def expand_source(group: str, source: str) -> str:
    for short, full in SHORT_NAMES.get(group, {}).items():
        source = re.sub(rf"(?<![\w/`-]){short}(?=\s*(?:[;|(]|$))", full, source)
    return source


def cell(text: str, limit: int | None = None) -> str:
    text = re.sub(r"\s+", " ", text).replace("|", "\\|").strip()
    if limit and len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + " […]"
    return text or "—"


def rows(group: str) -> tuple[list[str], Counter[str]]:
    out, counts = [], Counter()
    for claim in parse(group):
        status, qualifier = split_status(claim.get("Status", ""))
        if not status:
            continue
        counts[status] += 1
        wording = claim.get("Claim as worded") or claim["title"]
        if NOT_A_DESIGN_CLAIM.match(wording):
            wording = f"{claim['title']} (a research question; not a statement in DESIGN.md)"
        if "Case / forum" in claim:
            wording = f"{claim['title']} ({claim['Case / forum']})"
        corrected = claim.get("Corrected wording")
        if corrected is None and "Outcome" in claim:
            corrected = "Outcome in the award: " + claim["Outcome"]
        shown_status = f"**{status}**" + (f" ({qualifier})" if qualifier else "")
        out.append(
            "| {id} | {claim} | {status} | {corrected} | {source} | {quote} |".format(
                id=claim["id"],
                claim=cell(wording, 500),
                status=cell(shown_status),
                corrected=cell(corrected or "", 900),
                source=cell(expand_source(group, claim.get("Source", "")), 700),
                quote=cell(claim.get("Quote", ""), QUOTE_LIMIT),
            )
        )
    return out, counts


def generated() -> str:
    parts, totals, summary = [], Counter(), []
    for group, name in GROUPS.items():
        table, counts = rows(group)
        totals.update(counts)
        summary.append(
            f"| {group} | {name} | "
            + " | ".join(str(counts[s]) for s in STATUSES)
            + f" | {sum(counts.values())} |"
        )
        parts += [
            f"### Group {group}: {name}",
            "",
            (
                f"Full notes, complete quotes and context: `findings-{group}.md`. "
                f"A bare file name in the source column is relative to `sources/{group}/`."
            ),
            "",
            "| Id | Claim as currently worded | Status | Corrected wording | Source file and URL | Quote |",
            "|---|---|---|---|---|---|",
            *table,
            "",
        ]
    head = [
        "### Counts by status",
        "",
        "| Group | Scope | " + " | ".join(STATUSES) + " | Total |",
        "|---|---|---|---|---|---|---|",
        *summary,
        "| | **All groups** | "
        + " | ".join(str(totals[s]) for s in STATUSES)
        + f" | {sum(totals.values())} |",
        "",
    ]
    return "\n".join(head + parts).rstrip() + "\n"


def main() -> None:
    text = LEDGER.read_text(encoding="utf-8")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    LEDGER.write_text(f"{before}{START}\n{generated()}{END}{after}", encoding="utf-8")
    print(f"rewrote {LEDGER.relative_to(CLAIMS.parent.parent)}")


if __name__ == "__main__":
    main()
