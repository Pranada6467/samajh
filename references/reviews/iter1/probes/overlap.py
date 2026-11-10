"""Verifier probe: how independent are the frozen replies from the development set? No network.

    uv run python references/reviews/iter1/probes/overlap.py

Counts, over replies to a checked question in the frozen set: distinct reply texts, exact
matches with a development-set reply (the builders' 70 of 1,604), and near matches (the same
text once digits and number words are masked, or a difflib ratio of 0.85 or more against some
development reply in the same language).
"""

import difflib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "eval" / "text_path"))

import devset  # noqa: E402
import scenario_sets  # noqa: E402

from samajh.amounts._text import scan  # noqa: E402
from samajh.extract import SlotKind, slots  # noqa: E402
from samajh.extract._ground import comparison_form  # noqa: E402
from samajh.types import Speaker  # noqa: E402


def masked(text: str) -> str:
    """The reply with every number token replaced by #, so templates that differ only in the amount match."""
    out, last = [], 0
    for tok in scan(text):
        if tok.kind in ("num", "bad"):
            out.append(text[last:tok.start] + "#")
            last = tok.end
    out.append(text[last:])
    return re.sub(r"(# ?)+", "# ", comparison_form("".join(out)))


def main() -> int:
    _, frozen = scenario_sets.load("frozen")
    dev = defaultdict(set)
    for s in devset.scenarios():
        for t in s.transcript.turns:
            if t.speaker is Speaker.customer and comparison_form(t.text):
                dev[s.language.value].add(t.text)
    rows = []  # (language, kind, text, scenario id)
    for s in frozen:
        for slot in slots(s.transcript, s.record):
            if slot.kind is not SlotKind.other:
                rows.append((s.language.value, slot.kind.value, slot.turn.text, s.id))
    print("frozen replies to a checked question:", len(rows))
    distinct = {(lang, text) for lang, _, text, _ in rows}
    print("distinct (language, reply text):", len(distinct), dict(Counter(lang for lang, _ in distinct)))
    print("distinct (language, question kind, reply text):", len({(a, b, c) for a, b, c, _ in rows}))
    dev_exact = {lang: {comparison_form(t) for t in texts} for lang, texts in dev.items()}
    dev_any = set().union(*dev_exact.values())
    exact = [r for r in rows if comparison_form(r[2]) in dev_any]
    print("exact match with a dev reply (any language):", len(exact), "of", len(rows),
          "| distinct texts:", len({r[2] for r in exact}))
    dev_masked = {lang: {masked(t) for t in texts} for lang, texts in dev.items()}
    near_mask = [r for r in rows if masked(r[2]) in dev_masked[r[0]]]
    print("same as a dev reply once numbers are masked (same language):", len(near_mask), "of", len(rows),
          "| distinct texts:", len({r[2] for r in near_mask}))
    cache = {}

    def close(lang: str, text: str) -> bool:
        key = (lang, text)
        if key not in cache:
            a = masked(text)
            cache[key] = any(difflib.SequenceMatcher(None, a, masked(d)).ratio() >= 0.85 for d in dev[lang])
        return cache[key]

    near = [r for r in rows if close(r[0], r[2])]
    print("difflib ratio >= 0.85 with a dev reply after masking numbers (same language):", len(near), "of", len(rows),
          "| distinct texts:", len({r[2] for r in near}), "of", len(distinct))
    print("  by language:", dict(Counter(r[0] for r in near)), "of", dict(Counter(r[0] for r in rows)))
    print("dev replies per language:", {k: len(v) for k, v in dev.items()})
    # how often is one reply text reused across the 36 base cases?
    reuse = Counter((lang, text) for lang, _, text, _ in rows)
    print("a reply text is used in this many scenarios: median", sorted(reuse.values())[len(reuse) // 2],
          "max", max(reuse.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
