"""Score the amounts pilot two ways.

naive : read the digit string Prisma wrote (plus a following lakh/crore word), ignore everything else.
         This is what a typical pipeline does with ITN output.
fixed : same, plus fraction words left in front of the digits (sawa/saadhe/paune/dedh/dhai,
         Tamil/Kannada 1.5 / 2.5) are applied to the number's unit.
Word-only transcripts (no digits) are marked 'words' for manual review.
"""
import json, re, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
UNIT_WORDS = {1e5: ["लाख", "lakh", "லட்சம்", "ಲಕ್ಷ"], 1e7: ["करोड़", "crore", "கோடி", "ಕೋಟಿ"], 1e3: ["हज़ार", "thousand"]}
# fraction word -> (kind, value): add = coef + v units; mult = v units (coef must be 1)
FRACTIONS = {"सवा": ("add", 0.25), "साढ़े": ("add", 0.5), "पौने": ("add", -0.25),
             "डेढ़": ("set", 1.5), "ढाई": ("set", 2.5),
             "ஒன்றரை": ("set", 1.5), "இரண்டரை": ("set", 2.5), "ಒಂದೂವರೆ": ("set", 1.5), "ಒಂದುವರೆ": ("set", 1.5), "ಎರಡೂವರೆ": ("set", 2.5)}
NUM = re.compile(r"₹?\s?(\d[\d,]*(?:\.\d+)?)")

def unit_of(n):
    for u in (1e7, 1e5, 1e3):
        if n >= u and n % u == 0:
            return u
    return 1

def parse(text, fix):
    m = NUM.search(text)
    if not m:
        return None
    n = float(m.group(1).replace(",", ""))
    after = text[m.end():m.end() + 12]
    for u, words in UNIT_WORDS.items():
        if any(after.strip().startswith(w) for w in words):
            n *= u
            break
    if fix:
        before = text[:m.start()].split()
        if before and before[-1] in FRACTIONS:
            kind, v = FRACTIONS[before[-1]]
            u = unit_of(n)
            coef = n / u
            n = (coef + v) * u if kind == "add" else v * u
    return int(round(n))

def main():
    rows = json.loads((HERE / "results.json").read_text())
    tally = defaultdict(lambda: {"n": 0, "naive": 0, "fixed": 0, "words": 0, "err": 0})
    wrong = []
    for r in rows:
        k = (r["config"], r["cond"])
        t = tally[k]; t["n"] += 1
        if r["status"] != 200:
            t["err"] += 1; continue
        text = r["transcript"] or ""
        a, b = parse(text, False), parse(text, True)
        if a is None:
            t["words"] += 1; continue
        t["naive"] += a == r["gold"]
        t["fixed"] += b == r["gold"]
        if a != r["gold"] or b != r["gold"]:
            wrong.append((r["id"], r["config"], r["cond"], r["gold"], a, b, text))
    print(f"{'config':18} {'audio':9} {'n':>3} {'digits':>6} {'naive✓':>7} {'fixed✓':>7} {'words':>6} {'err':>4}")
    for (c, cond), t in sorted(tally.items()):
        d = t["n"] - t["words"] - t["err"]
        print(f"{c:18} {cond:9} {t['n']:3} {d:6} {t['naive']:7} {t['fixed']:7} {t['words']:6} {t['err']:4}")
    print("\nMismatches (id, config, audio, gold, naive, fixed, transcript):")
    for w in wrong:
        print(" ", *w)

if __name__ == "__main__":
    main()
